from fastapi.testclient import TestClient


COMPETITION_DATA = {
    "name": "全国大学生手球锦标赛",
    "season": "2026",
    "stage": "小组赛",
    "status": "active",
}


def test_create_and_list_competitions(client: TestClient) -> None:
    create_response = client.post(
        "/api/competitions",
        json=COMPETITION_DATA,
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1
    assert created["name"] == COMPETITION_DATA["name"]
    assert created["created_at"]

    list_response = client.get("/api/competitions")

    assert list_response.status_code == 200
    assert list_response.json() == [created]


def test_get_and_update_competition(client: TestClient) -> None:
    created = client.post(
        "/api/competitions",
        json=COMPETITION_DATA,
    ).json()

    detail_response = client.get(f"/api/competitions/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json() == created

    update_response = client.patch(
        f"/api/competitions/{created['id']}",
        json={"stage": "淘汰赛"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["stage"] == "淘汰赛"
    assert update_response.json()["name"] == COMPETITION_DATA["name"]


def test_missing_competition_returns_404(client: TestClient) -> None:
    response = client.get("/api/competitions/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Competition not found"}


def test_invalid_competition_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/competitions",
        json={
            "name": "",
            "season": "2026",
            "status": "unknown",
        },
    )

    assert response.status_code == 422
