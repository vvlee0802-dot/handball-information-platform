from pathlib import Path

from fastapi.testclient import TestClient

from app.core.authorization import UserRole
from app.core.config import settings
from app.models.video import Video
from tests.conftest import TestingSessionLocal
from tests.test_matches import setup_references
from tests.test_videos import replace_login


def create_match_and_player(client: TestClient) -> tuple[int, int, int, int]:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    match_response = client.post(
        "/api/matches",
        json={
            "competition_id": competition_id,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "venue_id": venue_id,
            "match_date": "2026-10-01",
            "start_time": "19:30",
            "stage": "小组赛",
            "status": "scheduled",
        },
    )
    player_response = client.post(
        "/api/players",
        json={
            "name": "测试左边锋",
            "number": 7,
            "position": "LW",
            "team_id": home_id,
            "birth_date": "2000-01-02",
            "description": None,
        },
    )
    assert match_response.status_code == 201
    assert player_response.status_code == 201
    return match_response.json()["id"], home_id, away_id, player_response.json()["id"]


def create_video(match_id: int, user_id: int, *, storage_key: str = "events/match.mp4") -> int:
    with TestingSessionLocal() as db:
        video = Video(
            match_id=match_id,
            uploaded_by_user_id=user_id,
            original_filename="match.mp4",
            storage_key=storage_key,
            content_type="video/mp4",
            size_bytes=32,
            duration_seconds=3600,
            video_type="original",
            status="uploaded",
            processing_status="completed",
            processing_progress=100,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video.id


def test_coach_creates_manual_events_and_refresh_returns_timeline_order(
    client: TestClient,
) -> None:
    match_id, home_id, _, player_id = create_match_and_player(client)
    coach = replace_login(client, email="event-coach@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)

    later = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "shot",
            "timestamp_seconds": 82.5,
            "team_id": home_id,
            "player_id": player_id,
            "note": "右侧突破射门",
        },
    )
    earlier = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "goal",
            "timestamp_seconds": 15.25,
            "team_id": None,
            "player_id": player_id,
            "note": None,
        },
    )

    assert later.status_code == 201
    assert earlier.status_code == 201
    assert earlier.json()["team_id"] == home_id
    assert earlier.json()["source"] == "manual"
    assert earlier.json()["status"] == "draft"
    assert earlier.json()["created_by_user_id"] == coach.id

    refreshed = client.get(f"/api/matches/{match_id}/events")
    assert refreshed.status_code == 200
    assert [item["timestamp_seconds"] for item in refreshed.json()] == [15.25, 82.5]


def test_event_relations_and_video_duration_are_validated(client: TestClient) -> None:
    match_id, _, away_id, player_id = create_match_and_player(client)
    coach = replace_login(client, email="event-validator@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)

    wrong_team = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "foul",
            "timestamp_seconds": 10,
            "team_id": away_id,
            "player_id": player_id,
        },
    )
    outside_video = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "timeout",
            "timestamp_seconds": 3601,
        },
    )

    assert wrong_team.status_code == 422
    assert wrong_team.json()["detail"] == "Player does not belong to the selected team"
    assert outside_video.status_code == 422
    assert outside_video.json()["detail"] == "Event timestamp exceeds video duration"


def test_athlete_can_view_but_cannot_create_manual_events(client: TestClient) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="event-owner@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    replace_login(client, email="event-athlete@example.com", role=UserRole.ATHLETE)

    listing = client.get(f"/api/matches/{match_id}/events")
    creation = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "goal",
            "timestamp_seconds": 12,
        },
    )

    assert listing.status_code == 200
    assert creation.status_code == 403
    assert creation.json() == {"detail": "Insufficient permissions"}


def test_authorized_user_streams_video_for_browser_playback(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)
    coach = replace_login(client, email="stream-coach@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    storage_key = "events/stream.mp4"
    stored_path = tmp_path / storage_key
    stored_path.parent.mkdir(parents=True)
    stored_path.write_bytes(b"video-for-streaming")
    video_id = create_video(match_id, coach.id, storage_key=storage_key)

    response = client.get(f"/api/videos/{video_id}/content")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.content == b"video-for-streaming"


def test_event_relations_protect_player_and_video_from_deletion(client: TestClient) -> None:
    match_id, home_id, _, player_id = create_match_and_player(client)
    coach = replace_login(client, email="event-protection@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    created = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "save",
            "timestamp_seconds": 28,
            "team_id": home_id,
            "player_id": player_id,
        },
    )

    assert created.status_code == 201
    assert client.delete(f"/api/videos/{video_id}").status_code == 409

    replace_login(client, email="event-admin@example.com", role=UserRole.SYSTEM_ADMIN)
    player_deletion = client.delete(f"/api/players/{player_id}")
    assert player_deletion.status_code == 409
    assert player_deletion.json()["detail"] == "该球员仍有关联比赛事件，请先处理相关事件。"
