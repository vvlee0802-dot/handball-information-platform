from fastapi.testclient import TestClient

from app.models.user import User
from app.models.video import Video
from tests.conftest import TestingSessionLocal
from tests.test_matches import setup_references
from tests.test_players import TEAM_DATA


def create_match(client: TestClient) -> tuple[int, int, int, int, int]:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    match = client.post(
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
    ).json()
    return match["id"], competition_id, home_id, away_id, venue_id


def test_delete_independent_competition_team_player_and_venue(client: TestClient) -> None:
    competition_id = client.post(
        "/api/competitions",
        json={"name": "可删除赛事", "season": "2026", "status": "draft"},
    ).json()["id"]
    team_id = client.post("/api/teams", json=TEAM_DATA).json()["id"]
    player_id = client.post(
        "/api/players",
        json={
            "name": "可删除球员",
            "number": 9,
            "position": "中卫",
            "team_id": team_id,
            "birth_date": "2000-01-01",
        },
    ).json()["id"]
    venue_id = client.post(
        "/api/venues",
        json={"name": "可删除场馆", "city": "北京", "address": "测试地址", "capacity": 1000},
    ).json()["id"]

    assert client.delete(f"/api/players/{player_id}").status_code == 204
    assert client.delete(f"/api/teams/{team_id}").status_code == 204
    assert client.delete(f"/api/venues/{venue_id}").status_code == 204
    assert client.delete(f"/api/competitions/{competition_id}").status_code == 204
    assert client.get(f"/api/players/{player_id}").status_code == 404
    assert client.get(f"/api/teams/{team_id}").status_code == 404
    assert client.get(f"/api/venues/{venue_id}").status_code == 404
    assert client.get(f"/api/competitions/{competition_id}").status_code == 404


def test_referenced_entities_are_blocked_until_match_is_deleted(client: TestClient) -> None:
    match_id, competition_id, home_id, away_id, venue_id = create_match(client)

    competition_response = client.delete(f"/api/competitions/{competition_id}")
    home_response = client.delete(f"/api/teams/{home_id}")
    venue_response = client.delete(f"/api/venues/{venue_id}")

    assert competition_response.status_code == 409
    assert "关联比赛" in competition_response.json()["detail"]
    assert home_response.status_code == 409
    assert "关联球员或比赛" in home_response.json()["detail"]
    assert venue_response.status_code == 409
    assert "关联比赛" in venue_response.json()["detail"]
    assert client.delete(f"/api/matches/{match_id}").status_code == 204
    assert client.delete(f"/api/competitions/{competition_id}").status_code == 204
    assert client.delete(f"/api/teams/{home_id}").status_code == 204
    assert client.delete(f"/api/teams/{away_id}").status_code == 204
    assert client.delete(f"/api/venues/{venue_id}").status_code == 204


def test_match_with_video_cannot_be_deleted(
    client: TestClient,
    registered_user: User,
) -> None:
    match_id, *_ = create_match(client)
    with TestingSessionLocal() as db:
        db.add(
            Video(
                match_id=match_id,
                uploaded_by_user_id=registered_user.id,
                original_filename="linked.mp4",
                storage_key=f"{match_id}/linked.mp4",
                content_type="video/mp4",
                size_bytes=128,
                status="uploaded",
                processing_status="completed",
                processing_progress=100,
            )
        )
        db.commit()

    response = client.delete(f"/api/matches/{match_id}")

    assert response.status_code == 409
    assert "关联视频" in response.json()["detail"]
