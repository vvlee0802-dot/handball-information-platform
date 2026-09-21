from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes import analysis_tasks as analysis_task_routes
from app.core.authorization import UserRole
from app.core.config import settings
from app.models.analysis_task import AnalysisTask
from app.models.video import Video
from app.services import analysis_task as analysis_task_service
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
    assert refreshed.json()["stage"] == "completed"
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
