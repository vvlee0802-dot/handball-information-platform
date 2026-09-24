from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Callable

from app.core.config import settings
from app.services.clip_export import get_ffmpeg_executable


SCAN_FPS = 2
WINDOW_SECONDS = 13
WINDOW_FRAME_COUNT = SCAN_FPS * WINDOW_SECONDS
MODEL_FRAME_COUNT = 16
MODEL_FRAME_SIZE = 256
STRIDE_SECONDS = 5
STRIDE_FRAME_COUNT = SCAN_FPS * STRIDE_SECONDS
DEFAULT_GOAL_THRESHOLD = 0.50


def model_scan_filter() -> str:
    return (
        f"fps={SCAN_FPS},scale=-2:{MODEL_FRAME_SIZE},"
        f"crop={MODEL_FRAME_SIZE}:{MODEL_FRAME_SIZE}"
    )


@dataclass(frozen=True)
class GoalCandidatePrediction:
    timestamp_seconds: float
    confidence: float


@dataclass(frozen=True)
class GoalDetectionResult:
    model_version: str | None
    candidates: list[GoalCandidatePrediction]


def collapse_positive_windows(
    windows: list[GoalCandidatePrediction],
    maximum_gap_seconds: float = STRIDE_SECONDS + 0.1,
) -> list[GoalCandidatePrediction]:
    """Keep the strongest prediction from each consecutive positive run."""
    if not windows:
        return []
    ordered = sorted(windows, key=lambda item: item.timestamp_seconds)
    groups: list[list[GoalCandidatePrediction]] = [[ordered[0]]]
    for prediction in ordered[1:]:
        if prediction.timestamp_seconds - groups[-1][-1].timestamp_seconds <= maximum_gap_seconds:
            groups[-1].append(prediction)
        else:
            groups.append([prediction])
    return [max(group, key=lambda item: item.confidence) for group in groups]


def _load_model(model_dir: Path):
    try:
        import torch
        from transformers import AutoImageProcessor, AutoModelForVideoClassification
    except ImportError as error:
        raise RuntimeError(
            "AI 模型已配置，但缺少训练/推理依赖；请安装 requirements-ml.txt。"
        ) from error

    artifact_path = model_dir / "classifier.pt"
    metadata_path = model_dir / "metadata.json"
    if not artifact_path.is_file() or not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    artifact = torch.load(artifact_path, map_location="cpu", weights_only=True)
    checkpoint = artifact["checkpoint"]
    processor = AutoImageProcessor.from_pretrained(
        checkpoint,
        use_fast=False,
        local_files_only=True,
    )
    pretrained_model = AutoModelForVideoClassification.from_pretrained(
        checkpoint,
        local_files_only=True,
    )
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    encoder = pretrained_model.videomae.to(device).eval()
    feature_mean = artifact["feature_mean"].float().to(device)
    feature_std = artifact["feature_std"].float().to(device)
    classifier = torch.nn.Linear(feature_mean.numel(), 2)
    classifier.load_state_dict(artifact["classifier_state_dict"])
    classifier = classifier.to(device).eval()
    return {
        "torch": torch,
        "processor": processor,
        "encoder": encoder,
        "classifier": classifier,
        "feature_mean": feature_mean,
        "feature_std": feature_std,
        "device": device,
        "model_version": metadata["model_version"],
        "decision_threshold": float(artifact.get("decision_threshold", DEFAULT_GOAL_THRESHOLD)),
    }


def _predict_window(model, frames) -> float:
    import numpy as np

    indices = np.linspace(0, len(frames) - 1, num=MODEL_FRAME_COUNT).round().astype(int)
    selected_frames = [frames[index] for index in indices]
    inputs = model["processor"](selected_frames, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(model["device"])
    torch = model["torch"]
    with torch.inference_mode():
        hidden_state = model["encoder"](pixel_values=pixel_values).last_hidden_state
        feature = hidden_state.mean(dim=1)
        normalized = (feature - model["feature_mean"]) / model["feature_std"]
        probability = torch.softmax(model["classifier"](normalized), dim=1)[0, 1]
    return float(probability.cpu().item())


def _scan_with_model(
    path: Path,
    duration_seconds: float,
    on_progress: Callable[[int], None],
    model,
) -> list[GoalCandidatePrediction]:
    import numpy as np

    width = MODEL_FRAME_SIZE
    height = MODEL_FRAME_SIZE
    frame_bytes = width * height * 3
    command = [
        get_ffmpeg_executable(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        model_scan_filter(),
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.stdout is None:
        process.kill()
        raise RuntimeError("无法读取视频分析画面。")
    frame_buffer = deque(maxlen=WINDOW_FRAME_COUNT)
    frame_index = 0
    positive_windows: list[GoalCandidatePrediction] = []
    last_progress = 10
    while True:
        raw_frame = process.stdout.read(frame_bytes)
        if not raw_frame:
            break
        if len(raw_frame) != frame_bytes:
            process.kill()
            raise RuntimeError("视频分析读取到不完整画面。")
        frame_buffer.append(
            np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3)).copy()
        )
        frame_index += 1
        if (
            len(frame_buffer) == WINDOW_FRAME_COUNT
            and (frame_index - WINDOW_FRAME_COUNT) % STRIDE_FRAME_COUNT == 0
        ):
            window_end = frame_index / SCAN_FPS
            event_timestamp = window_end - 5
            confidence = _predict_window(model, list(frame_buffer))
            if confidence >= model["decision_threshold"]:
                positive_windows.append(
                    GoalCandidatePrediction(
                        timestamp_seconds=round(event_timestamp, 3),
                        confidence=round(confidence, 4),
                    )
                )
            progress = min(95, 10 + int((window_end / duration_seconds) * 85))
            if progress >= last_progress + 2:
                on_progress(progress)
                last_progress = progress

    stderr = process.stderr.read().decode("utf-8", errors="replace").strip() if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        detail = stderr.splitlines()[-1] if stderr else "未知视频解码错误"
        raise RuntimeError(f"视频分析失败：{detail}"[:1000])
    return collapse_positive_windows(positive_windows)


def detect_goal_candidates(
    path: Path,
    duration_seconds: float | None,
    on_progress: Callable[[int], None],
) -> GoalDetectionResult:
    """Scan a match with the trained local classifier, or safely fall back to US5.1."""
    model = _load_model(settings.goal_model_path)
    if model is None:
        from app.services.analysis_task import scan_video_frames

        scan_video_frames(path, duration_seconds, on_progress)
        return GoalDetectionResult(model_version=None, candidates=[])
    if duration_seconds is None or duration_seconds <= WINDOW_SECONDS:
        raise RuntimeError("视频时长不足或缺失，无法启动进球检测。")
    candidates = _scan_with_model(path, duration_seconds, on_progress, model)
    return GoalDetectionResult(
        model_version=model["model_version"],
        candidates=candidates,
    )
