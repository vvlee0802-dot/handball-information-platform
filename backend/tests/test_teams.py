from fastapi.testclient import TestClient


TEAM_DATA = {
    "name": "中国男子手球队",
    "short_name": "中国",
    "city": "北京",
    "country": "中国",
    "gender": "men",
    "description": "国家男子手球队",
}


def test_create_list_get_and_update_team(client: TestClient) -> None:
    create_response = client.post("/api/teams", json=TEAM_DATA)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1

    assert client.get("/api/teams").json() == [created]
    assert client.get("/api/teams/1").json() == created

    update_response = client.patch("/api/teams/1", json={"city": "上海"})
    assert update_response.status_code == 200
    assert update_response.json()["city"] == "上海"


def test_team_validation_and_missing_record(client: TestClient) -> None:
    invalid_response = client.post("/api/teams", json={**TEAM_DATA, "gender": "unknown"})
    assert invalid_response.status_code == 422

    missing_response = client.get("/api/teams/9999")
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Team not found"}
