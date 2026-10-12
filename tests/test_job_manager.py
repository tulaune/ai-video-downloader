import os
import time

import pytest

from server.app.domain.models import VideoSource
from server.app.jobs.manager import JobManager
from server.app.pipeline import PipelineCoordinator


def test_job_manager_cleans_abandoned_workspaces_by_ttl(tmp_path):
    manager = JobManager(
        PipelineCoordinator({}),
        workspace_base=tmp_path,
        workspace_ttl_seconds=10,
    )
    job = manager.enqueue(
        VideoSource(url="https://fixture.example/video/1", platform="fixture")
    )
    workspace = tmp_path / job.id
    assert workspace.is_dir()

    old = time.time() - 100
    os.utime(workspace, (old, old))

    assert manager.cleanup_stale_workspaces(now=time.time()) == 1
    assert not workspace.exists()


def test_job_manager_rejects_negative_workspace_ttl(tmp_path):
    with pytest.raises(ValueError, match="workspace_ttl_seconds must be non-negative"):
        JobManager(PipelineCoordinator({}), workspace_base=tmp_path, workspace_ttl_seconds=-1)
