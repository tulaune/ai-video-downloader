import os
import time
from pathlib import Path

import pytest

from server.app.jobs import JobWorkspace


def test_job_workspace_is_private_and_safely_names_artifacts(tmp_path):
    workspace = JobWorkspace.create(tmp_path, job_id="job-123")
    try:
        assert workspace.root == (tmp_path / "job-123").resolve()
        assert workspace.root.stat().st_mode & 0o777 == 0o700
        assert workspace.path("../source.mp4") == workspace.root / "source.mp4"
    finally:
        workspace.cleanup()
    assert not workspace.root.exists()


def test_job_workspace_rejects_collisions(tmp_path):
    first = JobWorkspace.create(tmp_path, job_id="job-123")
    try:
        with pytest.raises(ValueError):
            JobWorkspace.create(tmp_path, job_id="job-123")
    finally:
        first.cleanup()


def test_job_workspace_path_is_inside_root(tmp_path):
    workspace = JobWorkspace.create(tmp_path)
    try:
        assert Path(workspace.path("video.mp4")).parent == workspace.root
    finally:
        workspace.cleanup()


def test_job_workspace_accounts_bytes_and_cleans_stale_children(tmp_path):
    workspace = JobWorkspace.create(tmp_path, job_id="old-job")
    artifact = workspace.path("source.mp4")
    artifact.write_bytes(b"12345")
    assert workspace.artifact_size(artifact) == 5
    assert workspace.size_bytes() == 5
    os.utime(workspace.root, (time.time() - 100, time.time() - 100))

    assert JobWorkspace.cleanup_stale(tmp_path, ttl_seconds=10) == 1
    assert not workspace.root.exists()
