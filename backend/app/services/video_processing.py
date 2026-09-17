from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video import Video


class VideoProcessingError(Exception):
    pass


def update_progress(db: Session, video: Video, progress: int) -> None:
    video.processing_progress = progress
    db.commit()


def calculate_checksum(db: Session, video: Video, path: Path) -> str:
    digest = sha256()
    bytes_read = 0
    last_progress = video.processing_progress

    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
            bytes_read += len(chunk)
            progress = min(95, 10 + int((bytes_read / video.size_bytes) * 85))
            if progress >= last_progress + 5:
                update_progress(db, video, progress)
                last_progress = progress

    if bytes_read != video.size_bytes:
        raise VideoProcessingError("视频文件大小与上传记录不一致，请重新上传。")
    return digest.hexdigest()


def process_video(video_id: int, bind: Engine) -> None:
    with Session(bind=bind) as db:
        video = db.get(Video, video_id)
        if video is None:
            return

        video.processing_status = "processing"
        video.processing_progress = 5
        video.processing_attempts += 1
        video.failure_reason = None
        video.processing_started_at = datetime.now(UTC)
        video.processing_completed_at = None
        db.commit()

        try:
            path = settings.video_storage_path / video.storage_key
            if not path.is_file():
                raise VideoProcessingError("找不到已上传的视频文件，请确认存储目录后重试。")

            with path.open("rb") as source:
                header = source.read(32)
            if b"ftyp" not in header:
                raise VideoProcessingError("视频文件不是有效的 MP4 容器，请重新上传。")

            video.checksum_sha256 = calculate_checksum(db, video, path)
            video.processing_status = "completed"
            video.processing_progress = 100
            video.processing_completed_at = datetime.now(UTC)
            db.commit()
        except VideoProcessingError as error:
            video.processing_status = "failed"
            video.failure_reason = str(error)
            video.processing_completed_at = datetime.now(UTC)
            db.commit()
        except OSError:
            video.processing_status = "failed"
            video.failure_reason = "读取视频文件失败，请检查存储空间和文件权限后重试。"
            video.processing_completed_at = datetime.now(UTC)
            db.commit()
