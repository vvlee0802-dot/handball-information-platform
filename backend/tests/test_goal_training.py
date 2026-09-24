import json
from pathlib import Path

import pytest

from app.scripts.train_goal_model import default_output_dir
from app.scripts.compare_goal_models import evaluate_model
from app.services.goal_training import (
    GoalTrainingError,
    binary_metrics,
    load_training_samples,
)


def test_model_version_selects_separate_output_directory():
    assert default_output_dir("goal-detector-v2") == Path("model_artifacts/goal_detector/v2")


def test_model_version_rejects_unsafe_directory_name():
    with pytest.raises(Exception, match="模型版本"):
        default_output_dir("../v2")


def test_compare_model_uses_only_shared_validation_features(tmp_path):
    torch = pytest.importorskip("torch")
    model_dir = tmp_path / "v2"
    model_dir.mkdir()
    classifier = torch.nn.Linear(2, 2)
    classifier.load_state_dict(
        {
            "weight": torch.tensor([[-1.0, 0.0], [1.0, 0.0]]),
            "bias": torch.tensor([0.0, 0.0]),
        }
    )
    torch.save(
        {
            "classifier_state_dict": classifier.state_dict(),
            "feature_mean": torch.zeros(2),
            "feature_std": torch.ones(2),
            "checkpoint": "test-checkpoint",
        },
        model_dir / "classifier.pt",
    )
    (model_dir / "metadata.json").write_text(
        json.dumps({"model_version": "goal-detector-v2"}),
        encoding="utf-8",
    )
    payload = {
        "checkpoint": "test-checkpoint",
        "features": torch.tensor([[1.0, 0.0], [-1.0, 0.0], [-1.0, 0.0]]),
        "labels": torch.tensor([1, 0, 1]),
        "splits": ["validation", "validation", "train"],
    }

    result = evaluate_model(torch, payload, model_dir)

    assert result["model_version"] == "goal-detector-v2"
    assert result["metrics"]["accuracy"] == 1.0


def write_sample(manifest, clips, sample_id, split, label, label_id):
    clip = clips / split / label / f"{sample_id}.mp4"
    clip.parent.mkdir(parents=True, exist_ok=True)
    clip.write_bytes(b"video")
    with manifest.open("a", encoding="utf-8") as output:
        output.write(
            json.dumps(
                {
                    "sample_id": sample_id,
                    "split": split,
                    "label": label,
                    "label_id": label_id,
                }
            )
            + "\n"
        )


def test_load_training_samples_checks_clips_and_both_labels(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    clips = tmp_path / "clips"
    write_sample(manifest, clips, "train-goal", "train", "goal", 1)
    write_sample(manifest, clips, "train-no", "train", "non_goal", 0)
    write_sample(manifest, clips, "validation-goal", "validation", "goal", 1)
    write_sample(manifest, clips, "validation-no", "validation", "non_goal", 0)

    samples = load_training_samples(manifest)

    assert len(samples) == 4
    assert samples[0].clip_path.is_file()


def test_load_training_samples_rejects_inconsistent_label(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    clip = tmp_path / "clips" / "train" / "goal" / "bad.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"video")
    manifest.write_text(
        json.dumps(
            {"sample_id": "bad", "split": "train", "label": "goal", "label_id": 0}
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GoalTrainingError, match="label_id"):
        load_training_samples(manifest)


def test_binary_metrics_reports_confusion_matrix():
    metrics = binary_metrics([1, 1, 0, 0], [1, 0, 1, 0])

    assert metrics == {
        "accuracy": 0.5,
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "true_positive": 1,
        "true_negative": 1,
        "false_positive": 1,
        "false_negative": 1,
    }
