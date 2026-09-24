import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import random
import re

from app.services.goal_training import (
    GoalTrainingError,
    binary_metrics,
    load_training_samples,
    manifest_sha256,
)


DEFAULT_CHECKPOINT = "MCG-NJU/videomae-small-finetuned-kinetics"
DEFAULT_MODEL_VERSION = "goal-detector-v1"
FRAME_COUNT = 16
SEED = 42


def default_output_dir(model_version: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", model_version):
        raise argparse.ArgumentTypeError(
            "模型版本只能包含小写字母、数字、点、下划线和连字符。"
        )
    directory_name = model_version.removeprefix("goal-detector-")
    return Path("model_artifacts") / "goal_detector" / directory_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a goal/non-goal classifier on cached VideoMAE features"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    parser.add_argument("--model-version", default=DEFAULT_MODEL_VERSION)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--rebuild-features", action="store_true")
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Load the pretrained checkpoint from the local Hugging Face cache only.",
    )
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    return parser.parse_args()


def select_device(torch_module, requested: str) -> str:
    if requested == "mps":
        if not torch_module.backends.mps.is_available():
            raise GoalTrainingError("当前 PyTorch 不可用 MPS。")
        return "mps"
    if requested == "cpu":
        return "cpu"
    return "mps" if torch_module.backends.mps.is_available() else "cpu"


def decode_uniform_frames(path: Path, frame_count: int):
    import av
    import numpy as np

    with av.open(str(path)) as container:
        frames = [frame.to_ndarray(format="rgb24") for frame in container.decode(video=0)]
    if not frames:
        raise GoalTrainingError(f"无法从样本中解码画面：{path}")
    indices = np.linspace(0, len(frames) - 1, num=frame_count).round().astype(int)
    return [frames[index] for index in indices]


def extract_features(
    samples,
    checkpoint: str,
    device: str,
    cache_path: Path,
    local_files_only: bool,
):
    import torch
    from transformers import AutoImageProcessor, AutoModelForVideoClassification

    print(f"Loading pretrained checkpoint: {checkpoint}", flush=True)
    processor = AutoImageProcessor.from_pretrained(
        checkpoint,
        use_fast=False,
        local_files_only=local_files_only,
    )
    pretrained_model = AutoModelForVideoClassification.from_pretrained(
        checkpoint,
        local_files_only=local_files_only,
    )
    encoder = pretrained_model.videomae.to(device).eval()
    features = []
    with torch.inference_mode():
        for index, sample in enumerate(samples, start=1):
            frames = decode_uniform_frames(sample.clip_path, FRAME_COUNT)
            inputs = processor(frames, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(device)
            hidden_state = encoder(pixel_values=pixel_values).last_hidden_state
            pooled = hidden_state.mean(dim=1).squeeze(0).cpu()
            features.append(pooled)
            print(f"Feature {index}/{len(samples)}: {sample.sample_id}", flush=True)
    payload = {
        "checkpoint": checkpoint,
        "frame_count": FRAME_COUNT,
        "sample_ids": [sample.sample_id for sample in samples],
        "features": torch.stack(features),
        "labels": torch.tensor([sample.label_id for sample in samples], dtype=torch.long),
        "splits": [sample.split for sample in samples],
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, cache_path)
    return payload


def load_or_extract_features(
    samples,
    checkpoint: str,
    device: str,
    cache_path: Path,
    rebuild: bool,
    local_files_only: bool,
):
    import torch

    expected_ids = [sample.sample_id for sample in samples]
    if cache_path.is_file() and not rebuild:
        payload = torch.load(cache_path, map_location="cpu", weights_only=True)
        if payload.get("checkpoint") == checkpoint and payload.get("sample_ids") == expected_ids:
            print(f"Reusing feature cache: {cache_path}", flush=True)
            return payload
        print("Feature cache does not match this dataset; rebuilding.", flush=True)
    return extract_features(samples, checkpoint, device, cache_path, local_files_only)


def train_classifier(payload, epochs: int, learning_rate: float):
    import torch

    if epochs <= 0 or learning_rate <= 0:
        raise GoalTrainingError("训练轮数和学习率必须大于 0。")
    torch.manual_seed(SEED)
    features = payload["features"].float()
    labels = payload["labels"].long()
    train_mask = torch.tensor([split == "train" for split in payload["splits"]])
    validation_mask = ~train_mask
    train_features = features[train_mask]
    feature_mean = train_features.mean(dim=0)
    feature_std = train_features.std(dim=0).clamp_min(1e-6)
    normalized = (features - feature_mean) / feature_std

    classifier = torch.nn.Linear(features.shape[1], 2)
    optimizer = torch.optim.AdamW(classifier.parameters(), lr=learning_rate, weight_decay=0.01)
    loss_function = torch.nn.CrossEntropyLoss()
    best_state = None
    best_f1 = -1.0
    best_epoch = 0
    for epoch in range(1, epochs + 1):
        classifier.train()
        optimizer.zero_grad()
        logits = classifier(normalized[train_mask])
        loss = loss_function(logits, labels[train_mask])
        loss.backward()
        optimizer.step()

        classifier.eval()
        with torch.inference_mode():
            predictions = classifier(normalized[validation_mask]).argmax(dim=1)
        metrics = binary_metrics(labels[validation_mask].tolist(), predictions.tolist())
        if float(metrics["f1"]) > best_f1:
            best_f1 = float(metrics["f1"])
            best_epoch = epoch
            best_state = {key: value.detach().clone() for key, value in classifier.state_dict().items()}
        if epoch == 1 or epoch % 50 == 0 or epoch == epochs:
            print(
                f"Epoch {epoch:03d}/{epochs}: loss={loss.item():.4f}, "
                f"validation_f1={float(metrics['f1']):.4f}",
                flush=True,
            )

    if best_state is None:
        raise GoalTrainingError("未能保存有效的分类器参数。")
    classifier.load_state_dict(best_state)
    classifier.eval()
    with torch.inference_mode():
        train_predictions = classifier(normalized[train_mask]).argmax(dim=1)
        validation_predictions = classifier(normalized[validation_mask]).argmax(dim=1)
    return {
        "classifier": classifier,
        "feature_mean": feature_mean,
        "feature_std": feature_std,
        "best_epoch": best_epoch,
        "train_metrics": binary_metrics(labels[train_mask].tolist(), train_predictions.tolist()),
        "validation_metrics": binary_metrics(
            labels[validation_mask].tolist(), validation_predictions.tolist()
        ),
    }


def main() -> None:
    args = parse_args()
    random.seed(SEED)
    try:
        import torch
    except ImportError as error:
        raise SystemExit(
            "缺少 AI 训练依赖，请先运行：python -m pip install -r requirements-ml.txt"
        ) from error

    manifest_path = args.manifest.resolve()
    try:
        output_dir = (args.output_dir or default_output_dir(args.model_version)).resolve()
    except argparse.ArgumentTypeError as error:
        raise SystemExit(str(error)) from error
    try:
        samples = load_training_samples(manifest_path)
        device = select_device(torch, args.device)
        cache_path = manifest_path.parent / "features" / "videomae-small.pt"
        payload = load_or_extract_features(
            samples,
            args.checkpoint,
            device,
            cache_path,
            args.rebuild_features,
            args.local_files_only,
        )
        result = train_classifier(payload, args.epochs, args.learning_rate)
    except GoalTrainingError as error:
        raise SystemExit(str(error)) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "classifier.pt"
    torch.save(
        {
            "classifier_state_dict": result["classifier"].state_dict(),
            "feature_mean": result["feature_mean"],
            "feature_std": result["feature_std"],
            "checkpoint": args.checkpoint,
            "frame_count": FRAME_COUNT,
            "labels": {0: "non_goal", 1: "goal"},
            "decision_threshold": 0.5,
        },
        model_path,
    )
    metadata = {
        "model_version": args.model_version,
        "created_at": datetime.now(UTC).isoformat(),
        "method": "frozen_videomae_features_with_linear_classifier",
        "pretrained_checkpoint": args.checkpoint,
        "pretrained_checkpoint_license": "CC-BY-NC-4.0",
        "manifest_sha256": manifest_sha256(manifest_path),
        "sample_count": len(samples),
        "frame_count": FRAME_COUNT,
        "device_used_for_feature_extraction": device,
        "epochs": args.epochs,
        "best_epoch": result["best_epoch"],
        "learning_rate": args.learning_rate,
        "decision_threshold": 0.5,
        "train_metrics": result["train_metrics"],
        "validation_metrics": result["validation_metrics"],
        "limitations": [
            "Training and validation samples currently come from the same match.",
            "Validation results do not yet demonstrate cross-match generalization.",
            "The pretrained checkpoint is licensed for non-commercial use.",
        ],
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved classifier: {model_path}")
    print(f"Saved metadata: {metadata_path}")
    print(json.dumps(metadata["validation_metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
