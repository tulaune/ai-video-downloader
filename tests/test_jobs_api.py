from fastapi.testclient import TestClient

from server.app.api import jobs
from server.app.jobs.manager import JobManager
from server.app.main import app
from server.app.pipeline import PipelineCoordinator


def test_job_api_returns_queued_job_and_hides_artifact_references(tmp_path, monkeypatch):
    manager = JobManager(PipelineCoordinator({}), workspace_base=tmp_path)
    monkeypatch.setattr(jobs, "job_manager", manager)
    response = TestClient(app).post(
        "/v1/jobs",
        json={
            "source": {
                "url": "https://www.douyin.com/video/123",
                "platform": "douyin",
                "source_id": "123",
                "metadata": {"download_url": "https://cdn.example/video.mp4"},
            },
            "requested_stages": ["acquiring"],
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "queued"
    assert "reference" not in body


def test_job_api_returns_404_for_unknown_job(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "job_manager", JobManager(PipelineCoordinator({}), workspace_base=tmp_path))
    response = TestClient(app).get("/v1/jobs/does-not-exist")

    assert response.status_code == 404


def test_cancel_sets_cancel_event_and_public_state(monkeypatch, tmp_path):
    manager = JobManager(PipelineCoordinator({}), workspace_base=tmp_path)
    monkeypatch.setattr(jobs, "job_manager", manager)
    queued = manager.enqueue(
        __import__("server.app.domain.models", fromlist=["VideoSource"]).VideoSource(
            url="https://www.douyin.com/video/123", platform="douyin", source_id="123"
        ),
    )

    response = TestClient(app).post(f"/v1/jobs/{queued.id}/cancel")

    assert response.status_code == 200
    assert response.json()["state"] == "cancelled"
