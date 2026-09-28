from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.knowledge import DocumentChunk, KnowledgeDocument


def list_documents(
    db: Session,
    *,
    viewer_user_id: int,
    viewer_team_id: int | None,
    include_private_from_others: bool,
) -> list[KnowledgeDocument]:
    query = select(KnowledgeDocument)
    if not include_private_from_others:
        query = query.where(
            or_(
                KnowledgeDocument.visibility == "platform",
                KnowledgeDocument.owner_user_id == viewer_user_id,
                (
                    (KnowledgeDocument.visibility == "team_private")
                    & (KnowledgeDocument.team_id == viewer_team_id)
                )
                if viewer_team_id is not None
                else False,
            )
        )
    return list(db.scalars(query.order_by(KnowledgeDocument.created_at.desc())))


def get_document(db: Session, document_id: str) -> KnowledgeDocument | None:
    return db.scalar(
        select(KnowledgeDocument)
        .options(selectinload(KnowledgeDocument.chunks))
        .where(KnowledgeDocument.id == document_id)
    )


def replace_chunks(
    db: Session,
    document: KnowledgeDocument,
    chunks: list[dict],
) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    db.add_all(
        [
            DocumentChunk(
                document_id=document.id,
                ordinal=index,
                content=chunk["content"],
                page_number=chunk["page_number"],
                section_title=chunk["section_title"],
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
    )
    document.chunk_count = len(chunks)
