from fastapi.testclient import TestClient


VENUE_DATA = {
    "name": "国家体育馆",
    "city": "北京",
    "address": "北京市朝阳区",
    "capacity": 18000,
    "description": "手球比赛场馆",
}


def test_create_list_get_and_update_venue(client: TestClient) -> None:
    create_response = client.post("/api/venues", json=VENUE_DATA)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1

    assert client.get("/api/venues").json() == [created]
    assert client.get("/api/venues/1").json() == created

    update_response = client.patch("/api/venues/1", json={"capacity": 20000})
    assert update_response.status_code == 200
    assert update_response.json()["capacity"] == 20000


def test_venue_validation_and_missing_record(client: TestClient) -> None:
    invalid_response = client.post("/api/venues", json={**VENUE_DATA, "capacity": -1})
    assert invalid_response.status_code == 422

    missing_response = client.get("/api/venues/9999")
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Venue not found"}
