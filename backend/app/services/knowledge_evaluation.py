from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import KnowledgeDocument, RagEvaluationCase, RagEvaluationRun
from app.services.knowledge_rag import (
    answer_with_chunks,
    embed_texts,
    ensure_chunk_embeddings,
    rank_chunks,
)


def run_rag_evaluation(
    db: Session,
    *,
    cases: list[RagEvaluationCase],
    documents: list[KnowledgeDocument],
    run_by_user_id: int,
    team_id: int | None,
) -> RagEvaluationRun:
    document_map = {document.id: document for document in documents}
    chunks = [chunk for document in documents for chunk in document.chunks]
    ensure_chunk_embeddings(db, chunks)
    question_vectors = embed_texts([case.question for case in cases])
    top_k = max(1, settings.knowledge_retrieval_top_k)

    details: list[dict] = []
    recall_total = 0.0
    citation_hits = 0
    citation_total = 0
    ungrounded_total = 0

    for case, query_vector in zip(cases, question_vectors, strict=True):
        ranked = rank_chunks(chunks, query_vector, top_k=top_k)
        answer = answer_with_chunks(case.question, ranked, documents=document_map)
        expected_ids = set(case.expected_document_ids)
        retrieved_ids = {chunk.document_id for chunk, _score in ranked}
        recall = len(expected_ids & retrieved_ids) / len(expected_ids)
        cited_ids = [citation.document_id for citation in answer.citations]
        case_citation_hits = sum(document_id in expected_ids for document_id in cited_ids)
        case_citation_rate = case_citation_hits / len(cited_ids) if cited_ids else 0.0
        ungrounded = not answer.insufficient_evidence and (
            not cited_ids or any(document_id not in expected_ids for document_id in cited_ids)
        )

        recall_total += recall
        citation_hits += case_citation_hits
        citation_total += len(cited_ids)
        ungrounded_total += int(ungrounded)
        details.append(
            {
                "case_id": case.id,
                "question": case.question,
                "expected_document_ids": case.expected_document_ids,
                "retrieved_chunks": [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title,
                        "score": round(score, 4),
                    }
                    for chunk, score in ranked
                ],
                "answer": answer.answer,
                "insufficient_evidence": answer.insufficient_evidence,
                "citation_chunk_ids": [citation.chunk_id for citation in answer.citations],
                "citation_document_ids": cited_ids,
                "recall_at_k": round(recall, 4),
                "citation_hit_rate": round(case_citation_rate, 4),
                "ungrounded": ungrounded,
            }
        )

    case_count = len(cases)
    run = RagEvaluationRun(
        id=str(uuid4()),
        run_by_user_id=run_by_user_id,
        team_id=team_id,
        embedding_model=settings.knowledge_embedding_model,
        answer_model=settings.match_report_llm_model,
        prompt_version=settings.knowledge_rag_prompt_version,
        top_k=top_k,
        relevance_threshold=settings.knowledge_relevance_threshold,
        case_count=case_count,
        recall_at_k=round(recall_total / case_count, 4),
        citation_hit_rate=round(citation_hits / citation_total, 4) if citation_total else 0.0,
        ungrounded_answer_rate=round(ungrounded_total / case_count, 4),
        details=details,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
