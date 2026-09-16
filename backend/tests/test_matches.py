from fastapi.testclient import TestClient


def setup_references(client: TestClient) -> tuple[int, int, int, int]:
    competition_id = client.post("/api/competitions", json={"name": "测试赛事", "season": "2026", "status": "active"}).json()["id"]
    team = {"short_name": "测试", "city": "北京", "country": "中国", "gender": "men"}
    home_id = client.post("/api/teams", json={**team, "name": "主队"}).json()["id"]
    away_id = client.post("/api/teams", json={**team, "name": "客队"}).json()["id"]
    venue_id = client.post("/api/venues", json={"name": "测试场馆", "city": "北京", "address": "测试地址", "capacity": 1000}).json()["id"]
    return competition_id, home_id, away_id, venue_id


def test_create_get_list_and_update_match(client: TestClient) -> None:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    data = {"competition_id": competition_id, "home_team_id": home_id, "away_team_id": away_id, "venue_id": venue_id, "match_date": "2026-10-01", "start_time": "19:30", "stage": "小组赛", "status": "scheduled"}
    response = client.post("/api/matches", json=data)
    assert response.status_code == 201
    created = response.json()
    assert client.get("/api/matches").json() == [created]
    assert client.get(f"/api/matches/{created['id']}").json() == created
    updated = client.patch(f"/api/matches/{created['id']}", json={"status": "completed", "home_score": 30, "away_score": 28})
    assert updated.status_code == 200
    assert updated.json()["home_score"] == 30


def test_match_validates_teams_scores_and_references(client: TestClient) -> None:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    base = {"competition_id": competition_id, "home_team_id": home_id, "away_team_id": away_id, "venue_id": venue_id, "match_date": "2026-10-01", "start_time": "19:30", "stage": "小组赛"}
    assert client.post("/api/matches", json={**base, "away_team_id": home_id}).status_code == 422
    assert client.post("/api/matches", json={**base, "competition_id": 9999}).json() == {"detail": "Referenced competition not found"}
    assert client.post("/api/matches", json={**base, "status": "completed"}).status_code == 422
