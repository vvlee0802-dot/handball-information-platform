from fastapi.testclient import TestClient


def test_request_id_is_returned_and_invalid_value_is_replaced(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/health/live",
        headers={"X-Request-ID": "invalid request id"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid request id"
    assert len(response.headers["X-Request-ID"]) == 32


def test_prometheus_metrics_include_api_and_dependency_series(
    client: TestClient,
) -> None:
    client.get("/api/health/live", headers={"X-Request-ID": "metrics-test"})

    response = client.get("/internal/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "handball_http_requests_total" in response.text
    assert 'dependency="database"' in response.text
    assert 'dependency="redis"' in response.text
