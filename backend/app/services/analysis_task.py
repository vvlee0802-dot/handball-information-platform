from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Callable

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_task import AnalysisTask
from app.models.video import Video
from app.services.clip_export import get_ffmpeg_executable


class AnalysisTaskError(Exception):
    pass


def scan_video_frames(
    path: Path,
    duration_seconds: float | None,
    on_progress: Callable[[int], None],
) -> None:
    command = [
        get_ffmpeg_executable(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-vf",
        "fps=1/5",
        "-an",
        "-f",
        "null",
        "-",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    last_progress = 10
    if process.stdout is None:
        process.kill()
        raise AnalysisTaskError("无法读取视频分析进度。")

    for line in process.stdout:
        key, separator, raw_value = line.strip().partition("=")
        if separator == "" or key not in {"out_time_ms", "out_time_us"}:
            continue
        if duration_seconds is None or duration_seconds <= 0:
            continue
        try:
            analyzed_seconds = int(raw_value) / 1_000_000
        except ValueError:
            continue
        progress = min(95, 10 + int((analyzed_seconds / duration_seconds) * 85))
        if progress >= last_progress + 5:
            on_progress(progress)
            last_progress = progress

    stderr = process.stderr.read().strip() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code != 0:
        detail = stderr.splitlines()[-1] if stderr else "未知视频解码错误"
        raise AnalysisTaskError(f"视频分析失败：{detail}"[:1000])


def process_analysis_task(task_id: str, bind: Engine) -> None:
    with Session(bind=bind) as db:
        task = db.get(AnalysisTask, task_id)
        if task is None or task.status != "queued":
            return

        task.status = "running"
        task.stage = "preparing"
        task.progress = 5
        task.failure_reason = None
        task.processing_started_at = datetime.now(UTC)
        task.processing_completed_at = None
        db.commit()

        try:
            video = db.get(Video, task.video_id)
            if video is None or video.deleted_at is not None:
                raise AnalysisTaskError("分析任务关联的视频不存在。")
            source_path = settings.video_storage_path / video.storage_key
            if not source_path.is_file():
                raise AnalysisTaskError("找不到视频文件，请确认存储目录后重试。")

            task.stage = "scanning_frames"
            task.progress = 10
            db.commit()

            def update_progress(progress: int) -> None:
                task.progress = progress
                db.commit()

            scan_video_frames(source_path, video.duration_seconds, update_progress)
            task.status = "completed"
            task.stage = "completed"
            task.progress = 100
            task.processing_completed_at = datetime.now(UTC)
            db.commit()
        except (AnalysisTaskError, OSError) as error:
            task.status = "failed"
            task.stage = "failed"
            task.failure_reason = str(error)[:1000]
            task.processing_completed_at = datetime.now(UTC)
            db.commit()
