from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.authorization import UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.video import Video
from tests.conftest import TestingSessionLocal
from tests.test_matches import setup_references


VALID_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"video-data"


def create_match(client: TestClient) -> int:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    response = client.post(
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
    assert response.status_code == 201
    return response.json()["id"]


def replace_login(client: TestClient, *, email: str, role: UserRole) -> User:
    client.post("/api/auth/logout")
    with TestingSessionLocal() as session:
        user = User(
            email=email,
            display_name=email.split("@", maxsplit=1)[0],
            password_hash=hash_password("correct-password"),
            role=role.value,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert response.status_code == 200
    return user


def test_coach_uploads_mp4_and_video_remains_linked_after_refresh(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    coach = replace_login(
        client,
        email="video-coach@example.com",
        role=UserRole.COACH_ANALYST,
    )
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)

    policy_response = client.get("/api/videos/upload-policy")
    upload_response = client.put(
        f"/api/matches/{match_id}/videos",
        content=VALID_MP4,
        headers={
            "Content-Type": "video/mp4",
            "X-Original-Filename": "full-match.mp4",
        },
    )

    assert policy_response.status_code == 200
    assert policy_response.json()["max_size_bytes"] == 10 * 1024**3
    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["match_id"] == match_id
    assert uploaded["uploaded_by_user_id"] == coach.id
    assert uploaded["original_filename"] == "full-match.mp4"
    assert uploaded["size_bytes"] == len(VALID_MP4)
    assert uploaded["status"] == "uploaded"
    assert uploaded["processing_status"] == "queued"
    assert uploaded["processing_progress"] == 0

    refreshed = client.get(f"/api/matches/{match_id}/videos")
    assert refreshed.status_code == 200
    processed = refreshed.json()[0]
    assert processed["processing_status"] == "completed"
    assert processed["processing_progress"] == 100
    assert processed["processing_attempts"] == 1
    assert processed["failure_reason"] is None
    assert processed["checksum_sha256"] == sha256(VALID_MP4).hexdigest()
    stored_files = list(tmp_path.rglob("*.mp4"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == VALID_MP4


def test_frontend_cannot_bypass_backend_format_and_size_validation(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="validator@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)

    wrong_extension = client.put(
        f"/api/matches/{match_id}/videos",
        content=VALID_MP4,
        headers={"Content-Type": "video/mp4", "X-Original-Filename": "match.mov"},
    )
    fake_mp4 = client.put(
        f"/api/matches/{match_id}/videos",
        content=b"not-an-mp4",
        headers={"Content-Type": "video/mp4", "X-Original-Filename": "match.mp4"},
    )
    monkeypatch.setattr(settings, "video_upload_max_bytes", 16)
    oversized = client.put(
        f"/api/matches/{match_id}/videos",
        content=VALID_MP4,
        headers={"Content-Type": "video/mp4", "X-Original-Filename": "match.mp4"},
    )

    assert wrong_extension.status_code == 415
    assert fake_mp4.status_code == 415
    assert oversized.status_code == 413
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []


def test_athlete_cannot_upload_video(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="athlete-video@example.com", role=UserRole.ATHLETE)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)

    response = client.put(
        f"/api/matches/{match_id}/videos",
        content=VALID_MP4,
        headers={"Content-Type": "video/mp4", "X-Original-Filename": "match.mp4"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_failed_processing_shows_reason_and_can_be_retried(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="retry-coach@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    upload_response = client.put(
        f"/api/matches/{match_id}/videos",
        content=VALID_MP4,
        headers={"Content-Type": "video/mp4", "X-Original-Filename": "retry.mp4"},
    )
    video_id = upload_response.json()["id"]

    conflict = client.post(f"/api/videos/{video_id}/retry")
    assert conflict.status_code == 409

    with TestingSessionLocal() as db:
        video = db.get(Video, video_id)
        assert video is not None
        (tmp_path / video.storage_key).unlink()
        video.processing_status = "failed"
        video.failure_reason = "测试失败"
        db.commit()

    retry_response = client.post(f"/api/videos/{video_id}/retry")
    assert retry_response.status_code == 202
    assert retry_response.json()["processing_status"] == "queued"

    refreshed = client.get(f"/api/matches/{match_id}/videos").json()[0]
    assert refreshed["processing_status"] == "failed"
    assert refreshed["processing_progress"] == 5
    assert refreshed["processing_attempts"] == 2
    assert refreshed["failure_reason"] == "找不到已上传的视频文件，请确认存储目录后重试。"
