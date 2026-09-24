from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.api.routes import analysis_tasks as analysis_task_routes
from app.core.authorization import UserRole
from app.core.config import settings
from app.models.analysis_task import AnalysisTask
from app.models.match import Match
from app.models.video import Video
from app.services import analysis_task as analysis_task_service
from app.services.goal_detection import GoalCandidatePrediction, GoalDetectionResult
from tests.conftest import TestingSessionLocal
from tests.test_events import create_match_and_player, create_video
from tests.test_videos import replace_login


def prepare_video_file(tmp_path: Path, storage_key: str) -> None:
    stored_path = tmp_path / storage_key
    stored_path.parent.mkdir(parents=True)
    stored_path.write_bytes(b"video-for-ai-scan")


def test_analysis_task_returns_id_and_persists_progress_after_refresh(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-coach@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    storage_key = "analysis/full-match.mp4"
    prepare_video_file(tmp_path, storage_key)
    video_id = create_video(match_id, coach.id, storage_key=storage_key)
    monkeypatch.setattr(settings, "goal_model_dir", tmp_path / "missing-model")

    def fake_scan(_path: Path, _duration: float | None, on_progress) -> None:
        on_progress(45)
        on_progress(90)

    monkeypatch.setattr(analysis_task_service, "scan_video_frames", fake_scan)

    created = client.post(f"/api/videos/{video_id}/analysis-tasks")
    task_id = created.json()["id"]
    refreshed = client.get(f"/api/analysis-tasks/{task_id}")
    listing = client.get(f"/api/matches/{match_id}/analysis-tasks")

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["progress"] == 0
    assert created.json()["reused"] is False
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "completed"
    assert refreshed.json()["progress"] == 100
    assert refreshed.json()["stage"] == "completed_no_model"
    assert refreshed.json()["candidate_count"] == 0
    assert refreshed.json()["model_version"] is None
    assert refreshed.json()["processing_started_at"] is not None
    assert refreshed.json()["processing_completed_at"] is not None
    assert [task["id"] for task in listing.json()] == [task_id]


def test_running_video_analysis_is_reused_instead_of_duplicated(
    client: TestClient,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-deduplicate@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    monkeypatch.setattr(analysis_task_routes, "process_analysis_task", lambda *_args: None)

    first = client.post(f"/api/videos/{video_id}/analysis-tasks")
    second = client.post(f"/api/videos/{video_id}/analysis-tasks")

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["reused"] is True
    with TestingSessionLocal() as db:
        task_count = db.scalar(select(func.count()).select_from(AnalysisTask))
        assert task_count == 1
    deletion = client.delete(f"/api/videos/{video_id}")
    assert deletion.status_code == 409
    assert deletion.json()["detail"] == (
        "Video cannot be deleted while an AI analysis task is active"
    )


def test_model_candidates_are_sorted_deduplicated_and_enter_manual_review(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-candidates@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    storage_key = "analysis/candidates.mp4"
    prepare_video_file(tmp_path, storage_key)
    video_id = create_video(match_id, coach.id, storage_key=storage_key)

    def fake_detector(_path: Path, _duration: float | None, on_progress) -> GoalDetectionResult:
        on_progress(70)
        return GoalDetectionResult(
            model_version="handball-goal-test-v1",
            candidates=[
                GoalCandidatePrediction(timestamp_seconds=80, confidence=0.82),
                GoalCandidatePrediction(timestamp_seconds=20, confidence=0.76),
                GoalCandidatePrediction(timestamp_seconds=21, confidence=0.91),
                GoalCandidatePrediction(timestamp_seconds=4000, confidence=0.99),
                GoalCandidatePrediction(timestamp_seconds=100, confidence=1.2),
            ],
        )

    monkeypatch.setattr(analysis_task_service, "detect_goal_candidates", fake_detector)

    created = client.post(f"/api/videos/{video_id}/analysis-tasks")
    task = client.get(f"/api/analysis-tasks/{created.json()['id']}").json()
    candidates = client.get(f"/api/matches/{match_id}/events").json()

    assert task["status"] == "completed"
    assert task["stage"] == "completed"
    assert task["candidate_count"] == 2
    assert task["model_version"] == "handball-goal-test-v1"
    assert [candidate["timestamp_seconds"] for candidate in candidates] == [21, 80]
    assert all(candidate["source"] == "ai" for candidate in candidates)
    assert all(candidate["status"] == "draft" for candidate in candidates)
    assert [candidate["confidence"] for candidate in candidates] == [0.91, 0.82]
    assert all(candidate["model_version"] == "handball-goal-test-v1" for candidate in candidates)
    assert all(candidate["analysis_task_id"] == task["id"] for candidate in candidates)

    verified = client.post(f"/api/matches/{match_id}/events/{candidates[0]['id']}/verify")
    updated = client.patch(
        f"/api/matches/{match_id}/events/{candidates[1]['id']}",
        json={"timestamp_seconds": 81, "note": "人工调整候选时间"},
    )
    deleted = client.delete(f"/api/matches/{match_id}/events/{candidates[1]['id']}")

    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"
    assert updated.status_code == 200
    assert updated.json()["timestamp_seconds"] == 81
    assert updated.json()["source"] == "ai"
    assert updated.json()["status"] == "draft"
    assert updated.json()["confidence"] == 0.82
    assert deleted.status_code == 204


def test_complete_manual_goals_trigger_evaluation_without_duplicate_events(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-evaluation@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    storage_key = "analysis/evaluation.mp4"
    prepare_video_file(tmp_path, storage_key)
    video_id = create_video(match_id, coach.id, storage_key=storage_key)
    with TestingSessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        match.home_score = 2
        match.away_score = 1
        db.commit()
    for timestamp in (10, 20, 40):
        response = client.post(
            f"/api/matches/{match_id}/events",
            json={
                "video_id": video_id,
                "event_type": "goal",
                "timestamp_seconds": timestamp,
                "team_id": None,
                "player_id": None,
                "note": None,
            },
        )
        assert response.status_code == 201

    def fake_detector(_path: Path, _duration: float | None, on_progress) -> GoalDetectionResult:
        on_progress(80)
        return GoalDetectionResult(
            model_version="handball-goal-test-v1",
            candidates=[
                GoalCandidatePrediction(timestamp_seconds=11, confidence=0.95),
                GoalCandidatePrediction(timestamp_seconds=22, confidence=0.85),
                GoalCandidatePrediction(timestamp_seconds=100, confidence=0.75),
            ],
        )

    monkeypatch.setattr(analysis_task_service, "detect_goal_candidates", fake_detector)

    created = client.post(f"/api/videos/{video_id}/analysis-tasks")
    task = client.get(f"/api/analysis-tasks/{created.json()['id']}").json()
    timeline = client.get(f"/api/matches/{match_id}/events").json()
    details = client.get(f"/api/analysis-tasks/{task['id']}/predictions")

    assert task["stage"] == "completed_evaluation"
    assert task["evaluation_mode"] is True
    assert task["candidate_count"] == 3
    assert task["ground_truth_count"] == 3
    assert task["true_positive_count"] == 2
    assert task["false_positive_count"] == 1
    assert task["false_negative_count"] == 1
    assert task["precision"] == pytest.approx(2 / 3)
    assert task["recall"] == pytest.approx(2 / 3)
    assert task["f1"] == pytest.approx(2 / 3)
    assert task["mean_absolute_error_seconds"] == 1.5
    assert len(timeline) == 3
    assert all(event["source"] == "manual" for event in timeline)
    assert details.status_code == 200
    assert len(details.json()) == 4
    assert sorted(item["outcome"] for item in details.json()) == [
        "false_negative",
        "false_positive",
        "true_positive",
        "true_positive",
    ]
    false_positive = next(
        item for item in details.json() if item["outcome"] == "false_positive"
    )
    reviewed = client.post(
        f"/api/analysis-predictions/{false_positive['id']}/review",
        json={"decision": "include"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["training_decision"] == "include"
    assert reviewed.json()["reviewed_by_user_id"] == coach.id


def test_analysis_requires_completed_video_processing(client: TestClient) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-video-state@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    with TestingSessionLocal() as db:
        video = db.get(Video, video_id)
        assert video is not None
        video.processing_status = "processing"
        db.commit()

    response = client.post(f"/api/videos/{video_id}/analysis-tasks")

    assert response.status_code == 409
    assert response.json()["detail"] == "Video processing must complete before AI analysis"


def test_athlete_can_view_but_cannot_start_analysis(client: TestClient) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="ai-owner@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    replace_login(client, email="ai-athlete@example.com", role=UserRole.ATHLETE)

    listing = client.get(f"/api/matches/{match_id}/analysis-tasks")
    creation = client.post(f"/api/videos/{video_id}/analysis-tasks")

    assert listing.status_code == 200
    assert creation.status_code == 403
