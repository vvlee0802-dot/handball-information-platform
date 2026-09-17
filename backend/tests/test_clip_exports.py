from pathlib import Path

from fastapi.testclient import TestClient

from app.core.authorization import UserRole
from app.core.config import settings
from app.services import clip_export as clip_export_service
from tests.test_events import create_match_and_player, create_video
from tests.test_videos import replace_login


def create_event(
    client: TestClient,
    match_id: int,
    video_id: int,
    timestamp_seconds: float,
) -> int:
    response = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "goal",
            "timestamp_seconds": timestamp_seconds,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_only_verified_events_can_create_clip_export(client: TestClient) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="clip-draft@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    event_id = create_event(client, match_id, video_id, 30)

    response = client.post(
        f"/api/matches/{match_id}/clip-exports",
        json={"event_ids": [event_id]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only verified events can be exported"


def test_clip_export_clamps_boundaries_persists_status_and_downloads_mp4(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="clip-coach@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    storage_key = "source/full-match.mp4"
    source_path = tmp_path / storage_key
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source-video")
    video_id = create_video(match_id, coach.id, storage_key=storage_key)
    first_event_id = create_event(client, match_id, video_id, 3)
    last_event_id = create_event(client, match_id, video_id, 3598)
    client.post(f"/api/matches/{match_id}/events/{first_event_id}/verify")
    client.post(f"/api/matches/{match_id}/events/{last_event_id}/verify")

    rendered_bounds: list[tuple[float, float]] = []

    def fake_render(_source: Path, output: Path, start: float, end: float) -> None:
        rendered_bounds.append((start, end))
        output.write_bytes(b"segment")

    def fake_concatenate(_segments: list[Path], output: Path, _work_dir: Path) -> None:
        output.write_bytes(b"combined-mp4")

    monkeypatch.setattr(clip_export_service, "render_segment", fake_render)
    monkeypatch.setattr(clip_export_service, "concatenate_segments", fake_concatenate)

    created = client.post(
        f"/api/matches/{match_id}/clip-exports",
        json={"event_ids": [last_event_id, first_event_id]},
    )
    listing = client.get(f"/api/matches/{match_id}/clip-exports")

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["event_ids"] == [first_event_id, last_event_id]
    assert rendered_bounds == [(0.0, 8.0), (3590.0, 3600)]
    assert listing.status_code == 200
    task = listing.json()[0]
    assert task["status"] == "completed"
    assert task["duration_seconds"] == 18.0
    assert task["size_bytes"] == len(b"combined-mp4")
    assert task["failure_reason"] is None

    preview = client.get(f"/api/clip-exports/{task['id']}/content")
    download = client.get(f"/api/clip-exports/{task['id']}/content?download=true")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("video/mp4")
    assert preview.content == b"combined-mp4"
    assert "inline" in preview.headers["content-disposition"]
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]
    assert task["filename"] in download.headers["content-disposition"]


def test_athlete_can_view_but_cannot_create_clip_export(client: TestClient) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="clip-owner@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    event_id = create_event(client, match_id, video_id, 40)
    client.post(f"/api/matches/{match_id}/events/{event_id}/verify")
    replace_login(client, email="clip-athlete@example.com", role=UserRole.ATHLETE)

    listing = client.get(f"/api/matches/{match_id}/clip-exports")
    creation = client.post(
        f"/api/matches/{match_id}/clip-exports",
        json={"event_ids": [event_id]},
    )

    assert listing.status_code == 200
    assert creation.status_code == 403
