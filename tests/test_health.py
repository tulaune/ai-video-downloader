from fastapi.testclient import TestClient

from server.app.main import app


def test_health_endpoint_returns_service_status():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "velingo-api",
        "version": "0.1.0-dev",
    }
