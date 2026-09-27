from fastapi.testclient import TestClient

from server.app.api import sources
from server.app.main import app


def test_analyze_douyin_source_returns_normalized_metadata(monkeypatch):
    async def fake_crawler(*, url: str, headless: bool):
        assert url == "https://www.douyin.com/video/123"
        assert headless is True
        return {
            "aweme_id": "123",
            "title": "Street food",
            "author": "Creator",
            "download_url": "https://cdn.example/video.mp4",
        }

    monkeypatch.setattr(sources, "crawl_single_url", fake_crawler)
    response = TestClient(app).post(
        "/v1/sources/analyze",
        json={"url": "https://www.douyin.com/video/123"},
    )

    assert response.status_code == 200
    assert response.json()["source"]["source_id"] == "123"
    assert response.json()["source"]["title"] == "Street food"
    assert response.json()["capabilities"] == ["download", "transcribe"]


def test_analyze_rejects_unsupported_platform():
    response = TestClient(app).post(
        "/v1/sources/analyze",
        json={"url": "https://www.youtube.com/watch?v=123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "unsupported_platform"


def test_analyze_rejects_extra_request_fields():
    response = TestClient(app).post(
        "/v1/sources/analyze",
        json={"url": "https://www.douyin.com/video/123", "token": "secret"},
    )

    assert response.status_code == 422
