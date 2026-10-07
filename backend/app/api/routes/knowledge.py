from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.api.dependencies.auth import DatabaseSession, ManageKnowledgeBaseUser
from app.core.authorization import UserRole
from app.core.config import settings
from app.models.knowledge import KnowledgeDocument
from app.models.team import Team
from app.models.user import User
from app.repositories import knowledge as knowledge_documents
from app.schemas.knowledge import KnowledgeDocumentDetail, KnowledgeDocumentRead
from app.services.knowledge_document import (
    PARSER_VERSION,
    KnowledgeDocumentParseError,
    build_chunks,
    extract_document_pages,
)

router = APIRouter(prefix="/api/knowledge/documents", tags=["knowledge base"])
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}
SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}
VISIBILITIES = {"platform", "team_private", "owner_private"}


def _filename(raw: str | None) -> str:
    filename = Path(unquote(raw or "")).name.strip()
    if not filename:
        raise HTTPException(status_code=422, detail="请选择 PDF、TXT 或 Markdown 文档。")
    if len(filename) > 255:
        raise HTTPException(status_code=422, detail="文件名过长。")
    if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=415, detail="当前只支持 PDF、TXT 和 Markdown 文档。")
    return filename


def _can_manage(document: KnowledgeDocument, user: User) -> bool:
    return document.owner_user_id == user.id or user.role in {
        UserRole.COMPETITION_ADMIN.value,
        UserRole.SYSTEM_ADMIN.value,
    }


def _get_allowed_document(
    db: DatabaseSession,
    document_id: str,
    user: User,
) -> KnowledgeDocument:
    document = knowledge_documents.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    is_admin = user.role in {
        UserRole.COMPETITION_ADMIN.value,
        UserRole.SYSTEM_ADMIN.value,
    }
    can_read = (
        document.visibility == "platform"
        or document.owner_user_id == user.id
        or is_admin
        or (
            document.visibility == "team_private"
            and user.team_id is not None
            and document.team_id == user.team_id
        )
    )
    if not can_read:
        raise HTTPException(
            status_code=403, detail="You do not have access to this knowledge document"
        )
    return document


def _owner_name(db: DatabaseSession, document: KnowledgeDocument) -> str:
    owner = db.get(User, document.owner_user_id)
    return owner.display_name if owner is not None else "未知用户"


def _read(db: DatabaseSession, document: KnowledgeDocument) -> KnowledgeDocumentRead:
    team = db.get(Team, document.team_id) if document.team_id is not None else None
    return KnowledgeDocumentRead(
        id=document.id,
        owner_user_id=document.owner_user_id,
        owner_name=_owner_name(db, document),
        team_id=document.team_id,
        team_name=team.name if team is not None else None,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        visibility=document.visibility,
        status=document.status,
        parser_name=document.parser_name,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _detail(db: DatabaseSession, document: KnowledgeDocument) -> KnowledgeDocumentDetail:
    return KnowledgeDocumentDetail(
        **_read(db, document).model_dump(),
        chunks=[
            {
                "id": chunk.id,
                "ordinal": chunk.ordinal,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "indexed": chunk.embedding is not None,
            }
            for chunk in document.chunks
        ],
    )


def _storage_path(document: KnowledgeDocument) -> Path:
    return settings.knowledge_document_storage_path / document.storage_key


def _process_document(db: DatabaseSession, document: KnowledgeDocument) -> KnowledgeDocument:
    try:
        content = _storage_path(document).read_bytes()
        pages = extract_document_pages(
            content,
            content_type=document.content_type,
            suffix=Path(document.original_filename).suffix.lower(),
        )
        chunks = build_chunks(pages)
        knowledge_documents.replace_chunks(db, document, chunks)
        document.page_count = len(pages)
        document.status = "ready"
        document.error_message = None
    except (KnowledgeDocumentParseError, OSError) as exc:
        knowledge_documents.replace_chunks(db, document, [])
        document.page_count = 0
        document.status = "failed"
        document.error_message = str(exc)[:2000]
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    return knowledge_documents.get_document(db, document.id) or document


@router.get("", response_model=list[KnowledgeDocumentRead])
def list_knowledge_documents(
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> list[KnowledgeDocumentRead]:
    include_private = current_user.role in {
        UserRole.COMPETITION_ADMIN.value,
        UserRole.SYSTEM_ADMIN.value,
    }
    return [
        _read(db, document)
        for document in knowledge_documents.list_documents(
            db,
            viewer_user_id=current_user.id,
            viewer_team_id=current_user.team_id,
            include_private_from_others=include_private,
        )
    ]


@router.post("", response_model=KnowledgeDocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    request: Request,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
    x_original_filename: Annotated[str | None, Header()] = None,
    x_knowledge_visibility: Annotated[str, Header()] = "platform",
    x_knowledge_team_id: Annotated[int | None, Header()] = None,
) -> KnowledgeDocumentDetail:
    filename = _filename(x_original_filename)
    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="文档 Content-Type 不受支持。")
    if x_knowledge_visibility not in VISIBILITIES:
        raise HTTPException(status_code=422, detail="知识文档可见范围无效。")
    team_id = None
    if x_knowledge_visibility == "team_private":
        team_id = x_knowledge_team_id or current_user.team_id
        if team_id is None or db.get(Team, team_id) is None:
            raise HTTPException(status_code=422, detail="球队私有文档必须关联有效球队。")
        is_admin = current_user.role in {
            UserRole.COMPETITION_ADMIN.value,
            UserRole.SYSTEM_ADMIN.value,
        }
        if not is_admin and current_user.team_id != team_id:
            raise HTTPException(status_code=403, detail="不能向其他球队的私有知识库上传文档。")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="文档内容为空。")
    if len(content) > settings.knowledge_document_max_bytes:
        raise HTTPException(status_code=413, detail="文档超过允许的文件大小。")

    document_id = str(uuid4())
    suffix = Path(filename).suffix.lower()
    storage_key = f"{document_id}{suffix}"
    document = KnowledgeDocument(
        id=document_id,
        owner_user_id=current_user.id,
        team_id=team_id,
        original_filename=filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=sha256(content).hexdigest(),
        visibility=x_knowledge_visibility,
        status="processing",
        parser_name=PARSER_VERSION,
    )
    db.add(document)
    db.commit()

    try:
        settings.knowledge_document_storage_path.mkdir(parents=True, exist_ok=True)
        _storage_path(document).write_bytes(content)
    except OSError as exc:
        document.status = "failed"
        document.error_message = f"文件保存失败：{exc}"[:2000]
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _detail(db, knowledge_documents.get_document(db, document.id) or document)

    processed = _process_document(db, document)
    return _detail(db, processed)


@router.get("/{document_id}", response_model=KnowledgeDocumentDetail)
def get_knowledge_document(
    document_id: str,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> KnowledgeDocumentDetail:
    return _detail(db, _get_allowed_document(db, document_id, current_user))


@router.post("/{document_id}/retry", response_model=KnowledgeDocumentDetail)
def retry_knowledge_document(
    document_id: str,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> KnowledgeDocumentDetail:
    document = _get_allowed_document(db, document_id, current_user)
    if not _can_manage(document, current_user):
        raise HTTPException(status_code=403, detail="Only the owner or an administrator can retry")
    document.status = "processing"
    document.error_message = None
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _detail(db, _process_document(db, document))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_document(
    document_id: str,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> Response:
    document = _get_allowed_document(db, document_id, current_user)
    if not _can_manage(document, current_user):
        raise HTTPException(status_code=403, detail="Only the owner or an administrator can delete")
    path = _storage_path(document)
    db.delete(document)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
