from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.authorization import UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.video import Video
from app.models.video_upload import VideoUploadPart, VideoUploadSession
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


def start_chunked_upload(client: TestClient, match_id: int) -> dict:
    response = client.post(
        f"/api/matches/{match_id}/video-uploads",
        json={
            "original_filename": "full-match.mp4",
            "content_type": "video/mp4",
            "total_size": len(VALID_MP4),
            "fingerprint": f"full-match.mp4:{len(VALID_MP4)}:123456",
        },
    )
    assert response.status_code == 200
    return response.json()


def upload_part(client: TestClient, upload_id: str, part_number: int, content: bytes):
    return client.put(
        f"/api/video-uploads/{upload_id}/parts/{part_number}",
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Chunk-SHA256": sha256(content).hexdigest(),
        },
    )


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


def test_reselecting_same_file_resumes_without_reuploading_completed_parts(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="resume@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    monkeypatch.setattr(settings, "video_upload_chunk_bytes", 16)
    session = start_chunked_upload(client, match_id)
    first_chunk = VALID_MP4[:16]

    first_upload = upload_part(client, session["id"], 1, first_chunk)
    resumed = start_chunked_upload(client, match_id)

    assert first_upload.status_code == 200
    assert resumed["id"] == session["id"]
    assert resumed["uploaded_parts"] == [
        {
            "part_number": 1,
            "size_bytes": 16,
            "checksum_sha256": sha256(first_chunk).hexdigest(),
        }
    ]


def test_chunk_retry_is_idempotent_and_complete_assembles_one_video(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="chunks@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    monkeypatch.setattr(settings, "video_upload_chunk_bytes", 16)
    session = start_chunked_upload(client, match_id)
    chunks = [VALID_MP4[index : index + 16] for index in range(0, len(VALID_MP4), 16)]

    assert upload_part(client, session["id"], 1, chunks[0]).status_code == 200
    assert upload_part(client, session["id"], 1, chunks[0]).status_code == 200
    for number, chunk in enumerate(chunks[1:], start=2):
        assert upload_part(client, session["id"], number, chunk).status_code == 200

    with TestingSessionLocal() as db:
        part_count = db.scalar(
            select(func.count(VideoUploadPart.id)).where(
                VideoUploadPart.upload_id == session["id"]
            )
        )
        assert part_count == len(chunks)

    completed = client.post(f"/api/video-uploads/{session['id']}/complete")
    assert completed.status_code == 201
    assert completed.json()["size_bytes"] == len(VALID_MP4)
    assert completed.json()["processing_status"] == "queued"
    stored_files = list(tmp_path.glob(f"{match_id}/*.mp4"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == VALID_MP4
    assert not (tmp_path / ".uploads" / session["id"]).exists()

    with TestingSessionLocal() as db:
        upload_session = db.get(VideoUploadSession, session["id"])
        assert upload_session is not None
        assert upload_session.status == "completed"
        assert upload_session.video_id == completed.json()["id"]
        assert db.scalar(
            select(func.count(VideoUploadPart.id)).where(
                VideoUploadPart.upload_id == session["id"]
            )
        ) == 0


def test_cancelling_upload_marks_session_and_cleans_temporary_parts(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    match_id = create_match(client)
    replace_login(client, email="cancel@example.com", role=UserRole.COACH_ANALYST)
    monkeypatch.setattr(settings, "video_upload_dir", tmp_path)
    monkeypatch.setattr(settings, "video_upload_chunk_bytes", 16)
    session = start_chunked_upload(client, match_id)
    assert upload_part(client, session["id"], 1, VALID_MP4[:16]).status_code == 200

    cancelled = client.delete(f"/api/video-uploads/{session['id']}")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["uploaded_parts"] == []
    assert not (tmp_path / ".uploads" / session["id"]).exists()
    with TestingSessionLocal() as db:
        upload_session = db.get(VideoUploadSession, session["id"])
        assert upload_session is not None
        assert upload_session.status == "cancelled"
        assert db.scalar(
            select(func.count(VideoUploadPart.id)).where(
                VideoUploadPart.upload_id == session["id"]
            )
        ) == 0
