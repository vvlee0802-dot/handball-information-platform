from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.event import Event
from app.models.video import Video
from app.services.match_report_parser import parse_official_match_report_pdf
from tests.conftest import TestingSessionLocal


def setup_match(client: TestClient) -> tuple[int, int, int]:
    competition_id = client.post(
        "/api/competitions",
        json={"name": "Paris 2024", "season": "2024", "status": "completed"},
    ).json()["id"]
    team_base = {"city": "Test", "gender": "men", "description": None}
    germany_id = client.post(
        "/api/teams",
        json={
            **team_base,
            "name": "德国",
            "short_name": "德国",
            "country": "德国",
        },
    ).json()["id"]
    denmark_id = client.post(
        "/api/teams",
        json={
            **team_base,
            "name": "丹麦",
            "short_name": "丹麦",
            "country": "丹麦",
        },
    ).json()["id"]
    venue_id = client.post(
        "/api/venues",
        json={
            "name": "Pierre Mauroy Stadium",
            "city": "Lille",
            "address": "Test",
            "capacity": 27328,
        },
    ).json()["id"]
    match_id = client.post(
        "/api/matches",
        json={
            "competition_id": competition_id,
            "home_team_id": denmark_id,
            "away_team_id": germany_id,
            "venue_id": venue_id,
            "match_date": "2024-08-11",
            "start_time": "13:30",
            "stage": "Gold Medal Match",
            "status": "scheduled",
        },
    ).json()["id"]
    client.post(
        "/api/players",
        json={
            "name": "GOLLA Johannes",
            "number": 4,
            "position": "Pivot",
            "team_id": germany_id,
            "birth_date": "1997-11-05",
            "description": None,
        },
    )
    return match_id, germany_id, denmark_id


def parsed_report() -> dict:
    def player(number: int, name: str, goals: int) -> dict:
        return {
            "number": number,
            "name": name,
            "goals": goals,
            "yellow_cards": 0,
            "suspensions_2min": 0,
            "red_cards": 0,
            "blue_cards": 0,
        }

    return {
        "report_type": "paris-2024-ihf-match-report-v1",
        "match_number": 38,
        "competition_stage": "Gold Medal Match",
        "match_date": "11 Aug 2024",
        "start_time": "13:30",
        "venue": "Pierre Mauroy Stadium",
        "team_a": {
            "side": "A",
            "code": "GER",
            "name": "Germany",
            "half_time_score": 12,
            "final_score": 26,
            "seven_meter_goals": 2,
            "seven_meter_attempts": 3,
            "timeouts": ["12:16", "25:22", "36:15"],
            "players": [player(4, "GOLLA Johannes", 1), player(7, "WITZKE Luca", 25)],
        },
        "team_b": {
            "side": "B",
            "code": "DEN",
            "name": "Denmark",
            "half_time_score": 21,
            "final_score": 39,
            "seven_meter_goals": 2,
            "seven_meter_attempts": 2,
            "timeouts": ["27:14"],
            "players": [player(19, "GIDSEL Mathias", 39)],
        },
    }


def test_parser_reads_supported_ihf_text_pdf_structure(monkeypatch) -> None:
    text = """Pierre Mauroy Stadium Handball
SUN 11 AUG 2024 Gold Medal Match
Start Time 13:30
Match Report
Match 38 Team A Team B
A GER - Germany B DEN - Denmark
Half-time (30’) End of playing time
12 21 26 39
Number of 7m 2/3 1 2 3 1 2 3 2/2 Number of 7m
12:16 25:22 36:15 27:14
No. Team A G YC 2' RC BC No. Team B G YC 2' RC BC
"""
    header = [None] * 24
    header[0], header[2], header[13] = "No.", "Team A", "Team B"
    player = [None] * 24
    player[0], player[2], player[7] = "4", "GOLLA Johannes (C)", "1"
    player[12], player[13], player[18] = "19", "GIDSEL Mathias", "11"

    class FakePage:
        def extract_text(self) -> str:
            return text

        def extract_tables(self) -> list:
            return [[header, player]]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    monkeypatch.setattr(
        "app.services.match_report_parser.pdfplumber.open", lambda _stream: FakePdf()
    )
    parsed = parse_official_match_report_pdf(b"%PDF-1.7 fake")
    assert parsed["team_a"]["name"] == "Germany"
    assert parsed["team_b"]["name"] == "Denmark"
    assert parsed["team_a"]["players"][0]["name"] == "GOLLA Johannes"
    assert parsed["team_b"]["players"][0]["goals"] == 11
    assert (parsed["team_a"]["final_score"], parsed["team_b"]["final_score"]) == (26, 39)


def test_preview_confirm_and_deduplicate_official_report(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    match_id, germany_id, denmark_id = setup_match(client)
    current_user = client.get("/api/auth/me").json()
    with TestingSessionLocal() as db:
        video = Video(
            match_id=match_id,
            uploaded_by_user_id=current_user["id"],
            original_filename="match.mp4",
            storage_key="reports/match.mp4",
            content_type="video/mp4",
            size_bytes=32,
            duration_seconds=3600,
            video_type="original",
            status="uploaded",
            processing_status="completed",
            processing_progress=100,
        )
        db.add(video)
        db.flush()
        db.add(
            Event(
                match_id=match_id,
                video_id=video.id,
                event_type="goal",
                timestamp_seconds=42,
                team_id=denmark_id,
                player_id=None,
                note="德国4号射门得分",
                source="manual",
                status="verified",
                created_by_user_id=current_user["id"],
                updated_by_user_id=current_user["id"],
                verified_by_user_id=current_user["id"],
            )
        )
        db.commit()
    monkeypatch.setattr(settings, "match_report_dir", tmp_path)
    monkeypatch.setattr(
        "app.api.routes.match_reports.parse_official_match_report_pdf",
        lambda _content: parsed_report(),
    )
    content = b"%PDF-1.7 fake report for route test"
    headers = {
        "Content-Type": "application/pdf",
        "X-Original-Filename": "match-report.pdf",
    }

    preview_response = client.post(
        f"/api/matches/{match_id}/official-reports/preview",
        content=content,
        headers=headers,
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["duplicate"] is False
    assert preview["conflicts"] == []
    assert preview["suggested_team_a_team_id"] == germany_id
    assert preview["suggested_team_b_team_id"] == denmark_id

    duplicate = client.post(
        f"/api/matches/{match_id}/official-reports/preview",
        content=content,
        headers=headers,
    ).json()
    assert duplicate["id"] == preview["id"]
    assert duplicate["duplicate"] is True

    imported_response = client.post(
        f"/api/matches/{match_id}/official-reports/{preview['id']}/confirm",
        json={
            "team_a_team_id": germany_id,
            "team_b_team_id": denmark_id,
            "accept_conflicts": False,
        },
    )
    assert imported_response.status_code == 200
    imported = imported_response.json()
    assert imported["status"] == "imported"
    assert len(imported["team_stats"]) == 2
    assert len(imported["player_stats"]) == 3
    linked = next(record for record in imported["player_stats"] if record["number"] == 4)
    imported_player = next(record for record in imported["player_stats"] if record["number"] == 7)
    assert linked["player_id"] is not None
    assert imported_player["player_id"] is not None

    linked_event = client.get(f"/api/matches/{match_id}/events").json()[0]
    assert linked_event["team_id"] == germany_id
    assert linked_event["player_id"] == linked["player_id"]
    audits = client.get(f"/api/matches/{match_id}/player-stats/player-assignment/audits").json()
    assert audits[0]["event_id"] == linked_event["id"]
    assert audits[0]["new_player_id"] == linked["player_id"]

    players = client.get("/api/players").json()
    assert len(players) == 3
    provisional = next(player for player in players if player["number"] == 7)
    assert provisional["name"] == "WITZKE Luca"
    assert provisional["team_id"] == germany_id
    assert provisional["position"] is None
    assert provisional["birth_date"] is None

    match = client.get(f"/api/matches/{match_id}").json()
    assert match["status"] == "completed"
    assert (match["home_team_id"], match["away_team_id"]) == (germany_id, denmark_id)
    assert (match["home_score"], match["away_score"]) == (26, 39)

    # Reapplying an already imported report repairs an older/reversed match record
    # without inserting duplicate official statistics.
    client.patch(
        f"/api/matches/{match_id}",
        json={
            "home_team_id": denmark_id,
            "away_team_id": germany_id,
            "home_score": 39,
            "away_score": 26,
        },
    )
    reapplied = client.post(
        f"/api/matches/{match_id}/official-reports/{preview['id']}/confirm",
        json={
            "team_a_team_id": germany_id,
            "team_b_team_id": denmark_id,
            "accept_conflicts": True,
        },
    )
    assert reapplied.status_code == 200
    assert len(reapplied.json()["player_stats"]) == 3
    assert len(client.get("/api/players").json()) == 3
    repaired_match = client.get(f"/api/matches/{match_id}").json()
    assert (repaired_match["home_team_id"], repaired_match["away_team_id"]) == (
        germany_id,
        denmark_id,
    )
    assert (repaired_match["home_score"], repaired_match["away_score"]) == (26, 39)
    latest = client.get(f"/api/matches/{match_id}/official-reports/latest").json()
    assert latest["id"] == preview["id"]


def test_report_conflict_requires_explicit_acceptance(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    match_id, germany_id, denmark_id = setup_match(client)
    client.patch(
        f"/api/matches/{match_id}",
        json={"status": "completed", "home_score": 25, "away_score": 39},
    )
    monkeypatch.setattr(settings, "match_report_dir", tmp_path)
    monkeypatch.setattr(
        "app.api.routes.match_reports.parse_official_match_report_pdf",
        lambda _content: parsed_report(),
    )
    preview = client.post(
        f"/api/matches/{match_id}/official-reports/preview",
        content=b"%PDF-1.7 conflict test",
        headers={"Content-Type": "application/pdf", "X-Original-Filename": "report.pdf"},
    ).json()
    assert preview["conflicts"]
    rejected = client.post(
        f"/api/matches/{match_id}/official-reports/{preview['id']}/confirm",
        json={
            "team_a_team_id": germany_id,
            "team_b_team_id": denmark_id,
            "accept_conflicts": False,
        },
    )
    assert rejected.status_code == 409


def test_report_rejects_non_pdf(client: TestClient) -> None:
    match_id, _, _ = setup_match(client)
    response = client.post(
        f"/api/matches/{match_id}/official-reports/preview",
        content=b"not a pdf",
        headers={"Content-Type": "text/plain", "X-Original-Filename": "report.txt"},
    )
    assert response.status_code == 415
