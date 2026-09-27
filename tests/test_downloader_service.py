import asyncio

from server.app.domain.models import ArtifactType, VideoSource
from server.app.downloader import SingleVideoDownloader
from server.app.jobs import JobWorkspace


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
