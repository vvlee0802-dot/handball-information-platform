from pathlib import Path
from typing import Annotated
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import UploadVideoUser, ViewAuthorizedVideoUser
from app.core.config import settings
from app.db.session import get_db
from app.repositories import match as matches
from app.repositories import video as videos
from app.schemas.video import VideoRead, VideoUploadPolicy


router = APIRouter(tags=["videos"])
DatabaseSession = Annotated[Session, Depends(get_db)]
ACCEPTED_CONTENT_TYPES = {"video/mp4", "application/mp4"}
ACCEPTED_EXTENSIONS = {".mp4"}


def validate_match_exists(db: Session, match_id: int) -> None:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")


def read_filename(raw_filename: str | None) -> str:
    filename = Path(unquote(raw_filename or "")).name.strip()
    if not filename:
        raise HTTPException(status_code=422, detail="Original filename is required")
    if len(filename) > 255:
        raise HTTPException(status_code=422, detail="Filename is too long")
    if Path(filename).suffix.lower() not in ACCEPTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only MP4 video files are supported")
    return filename


@router.get("/api/videos/upload-policy", response_model=VideoUploadPolicy)
def get_upload_policy(_current_user: UploadVideoUser) -> VideoUploadPolicy:
    return VideoUploadPolicy(
        accepted_extensions=sorted(ACCEPTED_EXTENSIONS),
        accepted_content_types=sorted(ACCEPTED_CONTENT_TYPES),
        max_size_bytes=settings.video_upload_max_bytes,
    )


@router.get("/api/matches/{match_id}/videos", response_model=list[VideoRead])
def list_match_videos(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> list[VideoRead]:
    validate_match_exists(db, match_id)
    return videos.list_match_videos(db, match_id)


@router.put(
    "/api/matches/{match_id}/videos",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_match_video(
    match_id: int,
    request: Request,
    db: DatabaseSession,
    current_user: UploadVideoUser,
    x_original_filename: Annotated[str | None, Header()] = None,
) -> VideoRead:
    validate_match_exists(db, match_id)
    filename = read_filename(x_original_filename)
    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only MP4 video files are supported")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from error
        if declared_size > settings.video_upload_max_bytes:
            raise HTTPException(status_code=413, detail="Video exceeds the configured upload limit")

    storage_key = f"{match_id}/{uuid4().hex}.mp4"
    final_path = settings.video_storage_path / storage_key
    temporary_path = final_path.with_suffix(".mp4.part")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    header_sample = bytearray()

    try:
        with temporary_path.open("wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > settings.video_upload_max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds the configured upload limit",
                    )
                if len(header_sample) < 64:
                    header_sample.extend(chunk[: 64 - len(header_sample)])
                output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=422, detail="Video file is empty")
        if b"ftyp" not in bytes(header_sample[:32]):
            raise HTTPException(status_code=415, detail="File content is not a valid MP4 container")

        temporary_path.replace(final_path)
        try:
            return videos.create_video(
                db,
                match_id=match_id,
                uploaded_by_user_id=current_user.id,
                original_filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=total_bytes,
            )
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
