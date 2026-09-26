from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.authorization import UserRole
from app.models.event import Event
from app.models.match_report import MatchReportImport, OfficialPlayerMatchStat
from tests.conftest import TestingSessionLocal
from tests.test_events import create_match_and_player, create_video
from tests.test_videos import replace_login


def create_event(
    client: TestClient,
    match_id: int,
    video_id: int,
    player_id: int,
    event_type: str,
    timestamp: float,
) -> None:
    response = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": event_type,
            "timestamp_seconds": timestamp,
            "player_id": player_id,
        },
    )
    assert response.status_code == 201


def create_official_goal_stat(
    *,
    match_id: int,
    team_id: int,
    player_id: int,
    user_id: int,
    goals: int,
) -> str:
    report_id = str(uuid4())
    with TestingSessionLocal() as db:
        db.add(
            MatchReportImport(
                id=report_id,
                match_id=match_id,
                uploaded_by_user_id=user_id,
                original_filename="official-report.pdf",
                storage_key=f"tests/{report_id}.pdf",
                content_type="application/pdf",
                size_bytes=128,
                checksum_sha256=uuid4().hex * 2,
                parser_name="test-parser",
                status="imported",
                parsed_data={},
                conflicts=[],
                team_a_team_id=team_id,
                imported_at=datetime.now(UTC),
            )
        )
        db.add(
            OfficialPlayerMatchStat(
                report_import_id=report_id,
                match_id=match_id,
                team_id=team_id,
                player_id=player_id,
                player_name="测试左边锋",
                number=7,
                goals=goals,
                yellow_cards=0,
                suspensions_2min=0,
                red_cards=0,
                blue_cards=0,
            )
        )
        db.commit()
    return report_id


def test_player_stats_use_official_report_instead_of_manual_events(client: TestClient) -> None:
    match_id, home_id, _, player_id = create_match_and_player(client)
    coach = replace_login(client, email="stats-coach@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)

    for index, event_type in enumerate(
        ["goal", "goal", "shot", "shot", "save", "turnover", "fast_break"],
        start=1,
    ):
        create_event(client, match_id, video_id, player_id, event_type, index * 10)

    with TestingSessionLocal() as db:
        ignored = Event(
            match_id=match_id,
            video_id=video_id,
            event_type="goal",
            timestamp_seconds=90,
            player_id=player_id,
            source="ai",
            status="draft",
            created_by_user_id=coach.id,
            updated_by_user_id=coach.id,
        )
        db.add(ignored)
        db.commit()

    report_id = create_official_goal_stat(
        match_id=match_id,
        team_id=home_id,
        player_id=player_id,
        user_id=coach.id,
        goals=6,
    )

    response = client.get(f"/api/matches/{match_id}/player-stats")

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == match_id
    assert body["goal_source"] == "official_report"
    assert body["official_report_id"] == report_id
    assert len(body["players"]) == 1
    row = body["players"][0]
    assert row["player_id"] == player_id
    assert row["goals"] == 6
    assert row["shots"] == 0
    assert row["saves"] == 0
    assert row["turnovers"] == 0
    assert row["fast_breaks"] == 0
    assert row["shooting_percentage"] is None


def test_player_stats_return_zeroes_without_inventing_percentage(client: TestClient) -> None:
    match_id, _, _, player_id = create_match_and_player(client)
    replace_login(client, email="empty-stats@example.com", role=UserRole.COACH_ANALYST)

    response = client.get(f"/api/matches/{match_id}/player-stats")

    assert response.status_code == 200
    body = response.json()
    assert body["goal_source"] == "unavailable"
    assert body["official_report_id"] is None
    row = body["players"][0]
    assert row["player_id"] == player_id
    assert row["goals"] == 0
    assert row["shots"] == 0
    assert row["saves"] == 0
    assert row["turnovers"] == 0
    assert row["fast_breaks"] == 0
    assert row["shooting_percentage"] is None


def test_player_stats_require_video_view_permission(
    client: TestClient,
    anonymous_client: TestClient,
) -> None:
    match_id, _, _, _ = create_match_and_player(client)

    response = anonymous_client.get(f"/api/matches/{match_id}/player-stats")

    assert response.status_code == 401


def test_metric_events_include_only_verified_matching_player_events(client: TestClient) -> None:
    match_id, _, _, player_id = create_match_and_player(client)
    coach = replace_login(client, email="metric-events@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    create_event(client, match_id, video_id, player_id, "goal", 20)
    create_event(client, match_id, video_id, player_id, "shot", 10)
    create_event(client, match_id, video_id, player_id, "save", 30)
    deleted = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "goal",
            "timestamp_seconds": 5,
            "player_id": player_id,
        },
    ).json()
    assert client.delete(f"/api/matches/{match_id}/events/{deleted['id']}").status_code == 204

    shots = client.get(
        f"/api/matches/{match_id}/player-stats/{player_id}/events?metric=shots"
    )
    goals = client.get(
        f"/api/matches/{match_id}/player-stats/{player_id}/events?metric=goals"
    )

    assert shots.status_code == 200
    assert [event["event_type"] for event in shots.json()] == ["shot", "goal"]
    assert [event["timestamp_seconds"] for event in shots.json()] == [10, 20]
    assert [event["event_type"] for event in goals.json()] == ["goal"]


def test_batch_player_reassignment_updates_stats_and_creates_audit(client: TestClient) -> None:
    match_id, home_id, _, original_player_id = create_match_and_player(client)
    replacement_response = client.post(
        "/api/players",
        json={
            "name": "替补球员",
            "number": 8,
            "position": "RW",
            "team_id": home_id,
            "birth_date": "2001-02-03",
            "description": None,
        },
    )
    replacement_player_id = replacement_response.json()["id"]
    coach = replace_login(client, email="assignment-coach@example.com", role=UserRole.COACH_ANALYST)
    video_id = create_video(match_id, coach.id)
    first_event = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "goal",
            "timestamp_seconds": 12,
            "player_id": original_player_id,
        },
    ).json()
    second_event = client.post(
        f"/api/matches/{match_id}/events",
        json={
            "video_id": video_id,
            "event_type": "shot",
            "timestamp_seconds": 16,
            "player_id": original_player_id,
        },
    ).json()

    updated = client.post(
        f"/api/matches/{match_id}/player-stats/player-assignment",
        json={
            "event_ids": [first_event["id"], second_event["id"]],
            "player_id": replacement_player_id,
        },
    )
    stats = client.get(f"/api/matches/{match_id}/player-stats").json()["players"]

    assert updated.status_code == 200
    assert updated.json()["requested_count"] == 2
    assert updated.json()["affected_count"] == 2
    assert {event["player_id"] for event in updated.json()["events"]} == {replacement_player_id}
    original = next(row for row in stats if row["player_id"] == original_player_id)
    replacement = next(row for row in stats if row["player_id"] == replacement_player_id)
    assert original["goals"] == 0
    assert replacement["goals"] == 0
    assert replacement["shots"] == 0

    replace_login(client, email="assignment-admin@example.com", role=UserRole.COMPETITION_ADMIN)
    audits = client.get(f"/api/matches/{match_id}/player-stats/player-assignment/audits")
    assert audits.status_code == 200
    assert len(audits.json()) == 2
    assert {audit["old_player_id"] for audit in audits.json()} == {original_player_id}
    assert {audit["new_player_id"] for audit in audits.json()} == {replacement_player_id}
    assert all(audit["changed_by_user_id"] == coach.id for audit in audits.json())
    assert all(audit["changed_by_user_name"] == "assignment-coach" for audit in audits.json())
