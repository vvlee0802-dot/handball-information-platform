from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.clip_export import ClipExport, ClipExportEvent
from app.models.event import Event
from app.models.video import Video


EVENT_LEAD_SECONDS = 8.0
EVENT_TRAIL_SECONDS = 5.0


class ClipExportError(Exception):
    pass


def delete_clip_export_output(clip_export: ClipExport) -> None:
    if clip_export.storage_key is None:
        return
    stored_path = settings.video_storage_path / clip_export.storage_key
    try:
        stored_path.unlink(missing_ok=True)
    except OSError as error:
        raise ClipExportError("无法删除已生成的视频文件，请稍后重试。") from error


def calculate_clip_bounds(
    timestamp_seconds: float,
    video_duration_seconds: float | None,
) -> tuple[float, float]:
    start = max(0.0, timestamp_seconds - EVENT_LEAD_SECONDS)
    requested_end = timestamp_seconds + EVENT_TRAIL_SECONDS
    end = (
        min(requested_end, video_duration_seconds)
        if video_duration_seconds is not None
        else requested_end
    )
    if end <= start:
        raise ClipExportError("事件位置无法生成有效的视频片段。")
    return start, end


def get_ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:
        raise ClipExportError("FFmpeg 不可用，请重新安装后端依赖后重试。") from error


def run_ffmpeg(arguments: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(
        [get_ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        reason = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "未知错误"
        raise ClipExportError(f"视频片段处理失败：{reason}"[:1000])


def render_segment(source_path: Path, output_path: Path, start: float, end: float) -> None:
    run_ffmpeg(
        [
            "-ss",
            f"{start:.3f}",
            "-i",
            str(source_path),
            "-t",
            f"{end - start:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def concatenate_segments(segment_paths: list[Path], output_path: Path, work_dir: Path) -> None:
    if len(segment_paths) == 1:
        shutil.move(segment_paths[0], output_path)
        return
    manifest_path = work_dir / "segments.txt"
    manifest_path.write_text(
        "".join(f"file '{path.name}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            manifest_path.name,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        cwd=work_dir,
    )


def process_clip_export(clip_export_id: int, bind: Engine) -> None:
    with Session(bind=bind) as db:
        clip_export = db.get(ClipExport, clip_export_id)
        if clip_export is None:
            return

        clip_export.status = "processing"
        clip_export.failure_reason = None
        clip_export.processing_started_at = datetime.now(UTC)
        clip_export.processing_completed_at = None
        db.commit()

        work_dir = settings.video_storage_path / ".clip-work" / str(clip_export.id)
        final_key = f"clips/{clip_export.match_id}/{uuid4().hex}.mp4"
        final_path = settings.video_storage_path / final_key
        temporary_output = work_dir / "combined.mp4"
        try:
            event_ids = list(
                db.scalars(
                    select(ClipExportEvent.event_id)
                    .where(ClipExportEvent.clip_export_id == clip_export.id)
                    .order_by(ClipExportEvent.sequence)
                )
            )
            if not event_ids:
                raise ClipExportError("导出任务中没有可处理的事件。")

            work_dir.mkdir(parents=True, exist_ok=True)
            segment_paths: list[Path] = []
            total_duration = 0.0
            for index, event_id in enumerate(event_ids):
                event = db.get(Event, event_id)
                if event is None or event.deleted_at is not None or event.status != "verified":
                    raise ClipExportError("导出任务包含未确认或已删除的事件。")
                video = db.get(Video, event.video_id)
                if video is None or video.deleted_at is not None:
                    raise ClipExportError("事件关联的视频不存在。")
                source_path = settings.video_storage_path / video.storage_key
                if not source_path.is_file():
                    raise ClipExportError("事件关联的视频文件不存在。")
                start, end = calculate_clip_bounds(
                    event.timestamp_seconds, video.duration_seconds
                )
                segment_path = work_dir / f"segment-{index:03d}.mp4"
                render_segment(source_path, segment_path, start, end)
                segment_paths.append(segment_path)
                total_duration += end - start

            concatenate_segments(segment_paths, temporary_output, work_dir)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(temporary_output, final_path)
            clip_export.storage_key = final_key
            clip_export.size_bytes = final_path.stat().st_size
            clip_export.duration_seconds = total_duration
            clip_export.status = "completed"
            clip_export.processing_completed_at = datetime.now(UTC)
            db.commit()
        except (ClipExportError, OSError) as error:
            final_path.unlink(missing_ok=True)
            clip_export.status = "failed"
            clip_export.failure_reason = str(error)[:1000]
            clip_export.processing_completed_at = datetime.now(UTC)
            db.commit()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
