from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


LABELS = {0: "non_goal", 1: "goal"}


class GoalTrainingError(Exception):
    pass


@dataclass(frozen=True)
class TrainingSample:
    sample_id: str
    split: str
    label: str
    label_id: int
    clip_path: Path


def load_training_samples(manifest_path: Path) -> list[TrainingSample]:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise GoalTrainingError(f"数据集清单不存在：{manifest_path}")

    samples: list[TrainingSample] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            sample_id = str(item["sample_id"])
            split = str(item["split"])
            label = str(item["label"])
            label_id = int(item["label_id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise GoalTrainingError(f"清单第 {line_number} 行格式错误。") from error
        if sample_id in seen_ids:
            raise GoalTrainingError(f"样本 ID 重复：{sample_id}")
        if split not in {"train", "validation"}:
            raise GoalTrainingError(f"未知数据集分区：{split}")
        if LABELS.get(label_id) != label:
            raise GoalTrainingError(f"样本 {sample_id} 的标签与 label_id 不一致。")
        clip_path = manifest_path.parent / "clips" / split / label / f"{sample_id}.mp4"
        if not clip_path.is_file() or clip_path.stat().st_size == 0:
            raise GoalTrainingError(f"样本视频不存在：{clip_path}")
        samples.append(
            TrainingSample(
                sample_id=sample_id,
                split=split,
                label=label,
                label_id=label_id,
                clip_path=clip_path,
            )
        )
        seen_ids.add(sample_id)

    for split in ("train", "validation"):
        split_labels = {sample.label_id for sample in samples if sample.split == split}
        if split_labels != set(LABELS):
            raise GoalTrainingError(f"{split} 分区必须同时包含进球和非进球样本。")
    return samples


def manifest_sha256(manifest_path: Path) -> str:
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float | int]:
    if len(labels) != len(predictions) or not labels:
        raise GoalTrainingError("真实标签和预测结果必须非空且数量相同。")
    true_positive = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    true_negative = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    false_positive = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    false_negative = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    accuracy = (true_positive + true_negative) / len(labels)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }
