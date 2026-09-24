import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from app.services.goal_training import binary_metrics, manifest_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare trained goal classifiers on the same cached validation features"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def evaluate_model(torch, payload: dict, model_dir: Path) -> dict:
    artifact_path = model_dir / "classifier.pt"
    metadata_path = model_dir / "metadata.json"
    if not artifact_path.is_file() or not metadata_path.is_file():
        raise SystemExit(f"模型产物不完整：{model_dir}")

    artifact = torch.load(artifact_path, map_location="cpu", weights_only=True)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if artifact["checkpoint"] != payload["checkpoint"]:
        raise SystemExit(f"模型与特征缓存使用了不同的预训练权重：{model_dir}")

    validation_mask = torch.tensor(
        [split == "validation" for split in payload["splits"]],
        dtype=torch.bool,
    )
    features = payload["features"].float()
    labels = payload["labels"].long()
    feature_mean = artifact["feature_mean"].float()
    feature_std = artifact["feature_std"].float()
    classifier = torch.nn.Linear(feature_mean.numel(), 2)
    classifier.load_state_dict(artifact["classifier_state_dict"])
    classifier.eval()
    with torch.inference_mode():
        normalized = (features[validation_mask] - feature_mean) / feature_std
        predictions = classifier(normalized).argmax(dim=1)

    return {
        "model_version": metadata["model_version"],
        "model_dir": str(model_dir.resolve()),
        "metrics": binary_metrics(
            labels[validation_mask].tolist(),
            predictions.tolist(),
        ),
    }


def main() -> None:
    args = parse_args()
    try:
        import torch
    except ImportError as error:
        raise SystemExit(
            "缺少 AI 评估依赖，请先运行：python -m pip install -r requirements-ml.txt"
        ) from error

    manifest_path = args.manifest.resolve()
    feature_cache = manifest_path.parent / "features" / "videomae-small.pt"
    if not manifest_path.is_file():
        raise SystemExit(f"数据集清单不存在：{manifest_path}")
    if not feature_cache.is_file():
        raise SystemExit(f"特征缓存不存在：{feature_cache}")

    payload = torch.load(feature_cache, map_location="cpu", weights_only=True)
    results = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha256(manifest_path),
        "validation_sample_count": sum(
            split == "validation" for split in payload["splits"]
        ),
        "models": [
            evaluate_model(torch, payload, model_dir.resolve())
            for model_dir in args.model_dir
        ],
    }
    rendered = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"Saved comparison: {output_path}")
    print(rendered, end="")


if __name__ == "__main__":
    main()
