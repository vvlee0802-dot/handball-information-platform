from fastapi import APIRouter, HTTPException

from app.api.dependencies.auth import DatabaseSession, QueryKnowledgeBaseUser
from app.core.authorization import UserRole
from app.core.config import settings
from app.repositories import knowledge as knowledge_documents
from app.schemas.knowledge import KnowledgeAnswer, KnowledgeQuestion
from app.services.knowledge_rag import (
    KnowledgeRagError,
    answer_with_chunks,
    embed_texts,
    ensure_chunk_embeddings,
    insufficient_answer,
    rank_chunks,
)


router = APIRouter(prefix="/api/knowledge", tags=["knowledge question answering"])


@router.post("/ask", response_model=KnowledgeAnswer)
def ask_knowledge_base(
    payload: KnowledgeQuestion,
    db: DatabaseSession,
    current_user: QueryKnowledgeBaseUser,
) -> KnowledgeAnswer:
    include_private = current_user.role in {
        UserRole.COMPETITION_ADMIN.value,
        UserRole.SYSTEM_ADMIN.value,
    }
    documents = [
        document
        for document in knowledge_documents.list_documents(
            db,
            viewer_user_id=current_user.id,
            viewer_team_id=current_user.team_id,
            include_private_from_others=include_private,
        )
        if document.status == "ready"
    ]
    chunks = [chunk for document in documents for chunk in document.chunks]
    if not chunks:
        return insufficient_answer()
    try:
        ensure_chunk_embeddings(db, chunks)
        query_embedding = embed_texts([payload.question])[0]
        ranked = rank_chunks(
            chunks,
            query_embedding,
            top_k=max(1, settings.knowledge_retrieval_top_k),
        )
        return answer_with_chunks(
            payload.question,
            ranked,
            documents={document.id: document for document in documents},
        )
    except KnowledgeRagError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
