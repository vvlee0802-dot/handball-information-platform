from fastapi.testclient import TestClient


TEAM_DATA = {
    "name": "中国男子手球队",
    "short_name": "中国",
    "city": "北京",
    "country": "中国",
    "gender": "men",
    "description": None,
}


def create_team(client: TestClient) -> int:
    return client.post("/api/teams", json=TEAM_DATA).json()["id"]


def test_create_list_get_and_update_player(client: TestClient) -> None:
    team_id = create_team(client)
    player_data = {
        "name": "测试球员",
        "number": 7,
        "position": "中卫",
        "team_id": team_id,
        "birth_date": "2000-01-01",
        "description": "测试资料",
    }

    create_response = client.post("/api/players", json=player_data)
    assert create_response.status_code == 201
    created = create_response.json()

    assert client.get(f"/api/players?team_id={team_id}").json() == [created]
    assert client.get(f"/api/players/{created['id']}").json() == created

    update_response = client.patch(
        f"/api/players/{created['id']}",
        json={"position": "左后卫"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["position"] == "左后卫"


def test_player_rejects_missing_team_and_invalid_data(client: TestClient) -> None:
    response = client.post(
        "/api/players",
        json={
            "name": "测试球员",
            "number": 100,
            "position": "中卫",
            "team_id": 9999,
            "birth_date": "2000-01-01",
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/players",
        json={
            "name": "测试球员",
            "number": 7,
            "position": "中卫",
            "team_id": 9999,
            "birth_date": "2000-01-01",
        },
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Referenced team not found"}
