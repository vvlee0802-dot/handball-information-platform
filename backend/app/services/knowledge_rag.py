import json
import math
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeAnswer, KnowledgeCitation


class KnowledgeRagError(RuntimeError):
    pass


class RagModelAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
    citation_ids: list[int] = Field(default_factory=list)
    insufficient_evidence: bool = False


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not (
        settings.match_report_llm_base_url
        and settings.match_report_llm_api_key
        and settings.knowledge_embedding_model
    ):
        raise KnowledgeRagError(
            "尚未配置知识库 Embedding。请检查百炼 Base URL、API Key 和 KNOWLEDGE_EMBEDDING_MODEL。"
        )
    try:
        response = httpx.post(
            f"{settings.match_report_llm_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.match_report_llm_api_key}"},
            json={"model": settings.knowledge_embedding_model, "input": texts},
            timeout=settings.match_report_llm_timeout_seconds,
        )
        response.raise_for_status()
        records = sorted(response.json()["data"], key=lambda item: item["index"])
        embeddings = [record["embedding"] for record in records]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise KnowledgeRagError(f"知识向量生成失败：{exc}") from exc
    if len(embeddings) != len(texts) or any(not embedding for embedding in embeddings):
        raise KnowledgeRagError("Embedding 服务返回的向量数量不完整。")
    return embeddings


def ensure_chunk_embeddings(db: Session, chunks: list[DocumentChunk]) -> None:
    missing = [
        chunk
        for chunk in chunks
        if chunk.embedding is None or chunk.embedding_model != settings.knowledge_embedding_model
    ]
    for start in range(0, len(missing), 10):
        batch = missing[start : start + 10]
        vectors = embed_texts([chunk.content for chunk in batch])
        for chunk, vector in zip(batch, vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_model = settings.knowledge_embedding_model
            chunk.embedded_at = datetime.now(timezone.utc)
    if missing:
        db.commit()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if denominator == 0:
        return -1.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator


def rank_chunks(
    chunks: list[DocumentChunk],
    query_embedding: list[float],
    *,
    top_k: int,
) -> list[tuple[DocumentChunk, float]]:
    ranked = [
        (chunk, cosine_similarity(query_embedding, chunk.embedding or [])) for chunk in chunks
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def insufficient_answer() -> KnowledgeAnswer:
    return KnowledgeAnswer(
        answer="当前知识库中没有找到足够可靠的依据。请补充相关规则或战术文档后再提问。",
        citations=[],
        insufficient_evidence=True,
        answer_model=settings.match_report_llm_model,
        embedding_model=settings.knowledge_embedding_model,
        prompt_version=settings.knowledge_rag_prompt_version,
    )


def answer_with_chunks(
    question: str,
    ranked_chunks: list[tuple[DocumentChunk, float]],
    *,
    documents: dict[str, KnowledgeDocument],
) -> KnowledgeAnswer:
    relevant = [
        (chunk, score)
        for chunk, score in ranked_chunks
        if score >= settings.knowledge_relevance_threshold
    ]
    if not relevant:
        return insufficient_answer()
    if not (
        settings.match_report_llm_base_url
        and settings.match_report_llm_api_key
        and settings.match_report_llm_model
    ):
        raise KnowledgeRagError("尚未配置知识库问答模型。")

    sources = [
        {
            "chunk_id": chunk.id,
            "document": documents[chunk.document_id].original_filename,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
            "content": chunk.content,
        }
        for chunk, _score in relevant
    ]
    try:
        response = httpx.post(
            f"{settings.match_report_llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.match_report_llm_api_key}"},
            json={
                "model": settings.match_report_llm_model,
                "temperature": 0.1,
                "enable_thinking": settings.match_report_llm_enable_thinking,
                "max_tokens": min(settings.match_report_llm_max_tokens, 1800),
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是手球知识库助手。只能根据 sources 回答，不得使用模型记忆补充事实。"
                            "回答中的每个主要结论必须引用 chunk_id。依据不足时将 "
                            "insufficient_evidence 设为 true。返回 JSON：answer、citation_ids、"
                            "insufficient_evidence。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"question": question, "sources": sources}, ensure_ascii=False
                        ),
                    },
                ],
            },
            timeout=settings.match_report_llm_timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        model_answer = RagModelAnswer.model_validate_json(raw)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
        raise KnowledgeRagError(f"知识库回答生成失败：{exc}") from exc

    by_id = {chunk.id: (chunk, score) for chunk, score in relevant}
    unknown = set(model_answer.citation_ids) - set(by_id)
    if unknown:
        raise KnowledgeRagError(
            f"模型引用了未检索到的知识分块：{', '.join(map(str, sorted(unknown)))}"
        )
    if model_answer.insufficient_evidence:
        return insufficient_answer()
    if not model_answer.citation_ids:
        raise KnowledgeRagError("模型回答没有提供可追溯的知识来源。")

    citations = []
    for chunk_id in dict.fromkeys(model_answer.citation_ids):
        chunk, score = by_id[chunk_id]
        document = documents[chunk.document_id]
        citations.append(
            KnowledgeCitation(
                chunk_id=chunk.id,
                document_id=document.id,
                document_name=document.original_filename,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                excerpt=chunk.content[:500],
                score=round(score, 4),
            )
        )
    return KnowledgeAnswer(
        answer=model_answer.answer,
        citations=citations,
        insufficient_evidence=False,
        answer_model=settings.match_report_llm_model,
        embedding_model=settings.knowledge_embedding_model,
        prompt_version=settings.knowledge_rag_prompt_version,
    )
