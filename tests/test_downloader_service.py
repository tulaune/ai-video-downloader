import asyncio

from server.app.domain.models import ArtifactType, VideoSource
from server.app.downloader import SingleVideoDownloader
from server.app.jobs import JobWorkspace
from server.app.downloader import service as downloader_service


def test_single_video_downloader_wraps_legacy_output_as_artifact(tmp_path):
    async def fake_downloader(videos, output_dir, concurrency):
        assert videos[0]["aweme_id"] == "123"
        assert concurrency == 1
        output = tmp_path / "job" / "creator__title__123" / "index.mp4"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"mp4")
        assert output_dir == str(tmp_path / "job")
        return 1, 0

    workspace = JobWorkspace.create(tmp_path, job_id="job")
    try:
        source = VideoSource(
            url="https://www.douyin.com/video/123",
            platform="douyin",
            source_id="123",
            title="Title",
            author="Creator",
            metadata={"download_url": "https://cdn.example/video.mp4"},
        )
        artifact = asyncio.run(
            SingleVideoDownloader().acquire(source, workspace, downloader=fake_downloader)
        )
    finally:
        workspace.cleanup()

    assert artifact.type == ArtifactType.SOURCE_VIDEO
    assert artifact.mime_type == "video/mp4"
    assert artifact.size == 3


def test_single_video_downloader_uses_generic_adapter_for_non_douyin(tmp_path, monkeypatch):
    async def fake_download(self, source, workspace):
        output = workspace.path("source.mp4")
        output.write_bytes(b"generic-mp4")
        from datetime import datetime, timezone
        from server.app.domain.models import Artifact

        return Artifact(
            id="source-video-123",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(output),
            mime_type="video/mp4",
            size=output.stat().st_size,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(downloader_service.YtDlpAdapter, "download", fake_download)
    workspace = JobWorkspace.create(tmp_path, job_id="generic-job")
    try:
        source = VideoSource(
            url="https://www.youtube.com/watch?v=123",
            platform="youtube",
            source_id="123",
            title="Foreign video",
        )
        artifact = asyncio.run(SingleVideoDownloader().acquire(source, workspace))
    finally:
        workspace.cleanup()

    assert artifact.type == ArtifactType.SOURCE_VIDEO
    assert artifact.mime_type == "video/mp4"
    assert artifact.size == len(b"generic-mp4")


def test_generic_adapter_rejects_unlisted_host():
    from server.app.downloader.yt_dlp import YtDlpAdapter

    assert YtDlpAdapter.supports_url("https://www.youtube.com/watch?v=123")
    assert not YtDlpAdapter.supports_url("https://example.com/video.mp4")
    assert not YtDlpAdapter.supports_url("https://notfacebook.com/reel/123")
