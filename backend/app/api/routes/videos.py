from hashlib import sha256
from math import ceil
from pathlib import Path
import re
import shutil
from typing import Annotated
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import UploadVideoUser, ViewAuthorizedVideoUser
from app.core.config import settings
from app.db.session import get_db
from app.models.video_upload import VideoUploadPart, VideoUploadSession
from app.repositories import match as matches
from app.repositories import video as videos
from app.repositories import video_upload as video_uploads
from app.schemas.video import VideoRead, VideoUploadPolicy
from app.schemas.video_upload import (
    VideoUploadCreate,
    VideoUploadPartRead,
    VideoUploadSessionRead,
)
from app.services.video_processing import process_video


router = APIRouter(tags=["videos"])
DatabaseSession = Annotated[Session, Depends(get_db)]
ACCEPTED_CONTENT_TYPES = {"video/mp4", "application/mp4"}
ACCEPTED_EXTENSIONS = {".mp4"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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


def upload_directory(upload_id: str) -> Path:
    return settings.video_storage_path / ".uploads" / upload_id


def ensure_upload_owner(session: VideoUploadSession | None, user_id: int) -> VideoUploadSession:
    if session is None:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="This upload belongs to another user")
    return session


def serialize_upload_session(db: Session, session: VideoUploadSession) -> VideoUploadSessionRead:
    parts = video_uploads.list_parts(db, session.id)
    return VideoUploadSessionRead(
        id=session.id,
        match_id=session.match_id,
        original_filename=session.original_filename,
        total_size=session.total_size,
        chunk_size=session.chunk_size,
        total_parts=session.total_parts,
        status=session.status,
        uploaded_parts=[
            VideoUploadPartRead(
                part_number=part.part_number,
                size_bytes=part.size_bytes,
                checksum_sha256=part.checksum_sha256,
            )
            for part in parts
        ],
        video_id=session.video_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/api/videos/upload-policy", response_model=VideoUploadPolicy)
def get_upload_policy(_current_user: UploadVideoUser) -> VideoUploadPolicy:
    return VideoUploadPolicy(
        accepted_extensions=sorted(ACCEPTED_EXTENSIONS),
        accepted_content_types=sorted(ACCEPTED_CONTENT_TYPES),
        max_size_bytes=settings.video_upload_max_bytes,
        chunk_size_bytes=settings.video_upload_chunk_bytes,
    )


@router.post(
    "/api/matches/{match_id}/video-uploads",
    response_model=VideoUploadSessionRead,
)
def create_or_resume_video_upload(
    match_id: int,
    payload: VideoUploadCreate,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> VideoUploadSessionRead:
    validate_match_exists(db, match_id)
    filename = read_filename(payload.original_filename)
    content_type = payload.content_type.split(";", maxsplit=1)[0].lower()
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only MP4 video files are supported")
    if payload.total_size > settings.video_upload_max_bytes:
        raise HTTPException(status_code=413, detail="Video exceeds the configured upload limit")

    existing = video_uploads.find_resumable_session(
        db,
        match_id=match_id,
        user_id=current_user.id,
        fingerprint=payload.fingerprint,
        original_filename=filename,
        content_type=content_type,
        total_size=payload.total_size,
    )
    if existing is not None:
        if existing.status == "failed":
            existing.status = "uploading"
            existing.failure_reason = None
            db.commit()
            db.refresh(existing)
        return serialize_upload_session(db, existing)

    chunk_size = settings.video_upload_chunk_bytes
    session = VideoUploadSession(
        id=str(uuid4()),
        match_id=match_id,
        user_id=current_user.id,
        fingerprint=payload.fingerprint,
        original_filename=filename,
        content_type=content_type,
        total_size=payload.total_size,
        chunk_size=chunk_size,
        total_parts=ceil(payload.total_size / chunk_size),
        status="uploading",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return serialize_upload_session(db, session)


@router.put(
    "/api/video-uploads/{upload_id}/parts/{part_number}",
    response_model=VideoUploadPartRead,
)
async def upload_video_part(
    upload_id: str,
    part_number: int,
    request: Request,
    db: DatabaseSession,
    current_user: UploadVideoUser,
    x_chunk_sha256: Annotated[str | None, Header()] = None,
) -> VideoUploadPartRead:
    session = ensure_upload_owner(db.get(VideoUploadSession, upload_id), current_user.id)
    if session.status not in {"uploading", "failed"}:
        raise HTTPException(status_code=409, detail="Upload session is not accepting parts")
    if part_number < 1 or part_number > session.total_parts:
        raise HTTPException(status_code=422, detail="Part number is outside the upload range")
    checksum = (x_chunk_sha256 or "").lower()
    if SHA256_PATTERN.fullmatch(checksum) is None:
        raise HTTPException(status_code=422, detail="A valid X-Chunk-SHA256 header is required")

    expected_size = session.chunk_size
    if part_number == session.total_parts:
        expected_size = session.total_size - session.chunk_size * (session.total_parts - 1)
    existing = video_uploads.get_part(db, upload_id, part_number)
    existing_path = settings.video_storage_path / existing.storage_key if existing else None
    if (
        existing is not None
        and existing.size_bytes == expected_size
        and existing.checksum_sha256 == checksum
        and existing_path is not None
        and existing_path.exists()
    ):
        return VideoUploadPartRead(
            part_number=existing.part_number,
            size_bytes=existing.size_bytes,
            checksum_sha256=existing.checksum_sha256,
        )

    part_dir = upload_directory(upload_id)
    part_dir.mkdir(parents=True, exist_ok=True)
    part_path = part_dir / f"{part_number:06d}.part"
    temporary_path = part_path.with_suffix(".tmp")
    digest = sha256()
    total_bytes = 0
    try:
        with temporary_path.open("wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > expected_size:
                    raise HTTPException(status_code=422, detail="Part is larger than expected")
                digest.update(chunk)
                output.write(chunk)
        if total_bytes != expected_size:
            raise HTTPException(status_code=422, detail="Part size does not match the upload plan")
        if digest.hexdigest() != checksum:
            raise HTTPException(status_code=422, detail="Part checksum does not match its content")
        temporary_path.replace(part_path)

        storage_key = str(part_path.relative_to(settings.video_storage_path))
        if existing is None:
            existing = VideoUploadPart(
                upload_id=upload_id,
                part_number=part_number,
                size_bytes=total_bytes,
                checksum_sha256=checksum,
                storage_key=storage_key,
            )
            db.add(existing)
        else:
            existing.size_bytes = total_bytes
            existing.checksum_sha256 = checksum
            existing.storage_key = storage_key
        session.status = "uploading"
        session.failure_reason = None
        db.commit()
        return VideoUploadPartRead(
            part_number=part_number,
            size_bytes=total_bytes,
            checksum_sha256=checksum,
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


@router.post(
    "/api/video-uploads/{upload_id}/complete",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
)
def complete_video_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> VideoRead:
    session = ensure_upload_owner(db.get(VideoUploadSession, upload_id), current_user.id)
    if session.status == "completed" and session.video_id is not None:
        completed_video = videos.get_video(db, session.video_id)
        if completed_video is not None:
            return completed_video
    if session.status not in {"uploading", "failed"}:
        raise HTTPException(status_code=409, detail="Upload session cannot be completed")

    parts = video_uploads.list_parts(db, upload_id)
    received_numbers = {part.part_number for part in parts}
    missing = [number for number in range(1, session.total_parts + 1) if number not in received_numbers]
    if missing:
        raise HTTPException(status_code=409, detail=f"Upload is missing {len(missing)} part(s)")

    session.status = "assembling"
    session.failure_reason = None
    db.commit()
    storage_key = f"{session.match_id}/{uuid4().hex}.mp4"
    final_path = settings.video_storage_path / storage_key
    temporary_path = final_path.with_suffix(".mp4.part")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    header_sample = bytearray()
    try:
        with temporary_path.open("wb") as output:
            for part in parts:
                part_path = settings.video_storage_path / part.storage_key
                if not part_path.exists():
                    raise ValueError(f"Uploaded part {part.part_number} is missing from storage")
                with part_path.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        total_bytes += len(chunk)
                        if len(header_sample) < 64:
                            header_sample.extend(chunk[: 64 - len(header_sample)])
                        output.write(chunk)
        if total_bytes != session.total_size:
            raise ValueError("Assembled video size does not match the upload session")
        if b"ftyp" not in bytes(header_sample[:32]):
            raise ValueError("Assembled file is not a valid MP4 container")
        temporary_path.replace(final_path)
        video = videos.create_video(
            db,
            match_id=session.match_id,
            uploaded_by_user_id=current_user.id,
            original_filename=session.original_filename,
            storage_key=storage_key,
            content_type=session.content_type,
            size_bytes=total_bytes,
        )
        session = db.get(VideoUploadSession, upload_id)
        if session is None:
            raise RuntimeError("Upload session disappeared during assembly")
        session.status = "completed"
        session.video_id = video.id
        session.failure_reason = None
        video_uploads.delete_parts(db, upload_id)
        db.commit()
        shutil.rmtree(upload_directory(upload_id), ignore_errors=True)
        background_tasks.add_task(process_video, video.id, db.get_bind())
        return video
    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        session = db.get(VideoUploadSession, upload_id)
        if session is not None:
            session.status = "failed"
            session.failure_reason = str(error)[:500]
            db.commit()
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Video parts could not be assembled") from error


@router.delete(
    "/api/video-uploads/{upload_id}",
    response_model=VideoUploadSessionRead,
)
def cancel_video_upload(
    upload_id: str,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> VideoUploadSessionRead:
    session = ensure_upload_owner(db.get(VideoUploadSession, upload_id), current_user.id)
    if session.status == "completed":
        raise HTTPException(status_code=409, detail="A completed upload cannot be cancelled")
    video_uploads.delete_parts(db, upload_id)
    session.status = "cancelled"
    session.failure_reason = None
    db.commit()
    db.refresh(session)
    shutil.rmtree(upload_directory(upload_id), ignore_errors=True)
    return serialize_upload_session(db, session)


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
    background_tasks: BackgroundTasks,
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
            video = videos.create_video(
                db,
                match_id=match_id,
                uploaded_by_user_id=current_user.id,
                original_filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=total_bytes,
            )
            background_tasks.add_task(process_video, video.id, db.get_bind())
            return video
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


@router.post(
    "/api/videos/{video_id}/retry",
    response_model=VideoRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_video_processing(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    _current_user: UploadVideoUser,
) -> VideoRead:
    video = videos.get_video(db, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.processing_status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed video processing tasks can be retried",
        )

    queued_video = videos.queue_video_for_retry(db, video)
    background_tasks.add_task(process_video, queued_video.id, db.get_bind())
    return queued_video
