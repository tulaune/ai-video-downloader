from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from backend.downloader import download_videos
from server.app.domain.models import Artifact, ArtifactType, VideoSource
from server.app.jobs import JobWorkspace
from server.app.security import ServiceError


DownloadFunction = Callable[..., Awaitable[tuple[int, int]]]


class SingleVideoDownloader:
    """Adapter from the normalized source contract to the legacy downloader."""

    async def acquire(
        self,
        source: VideoSource,
        workspace: JobWorkspace,
        downloader: DownloadFunction | None = None,
    ) -> Artifact:
        if source.platform != "douyin":
            raise ServiceError(
                stage="acquiring",
                error_code="unsupported_platform",
                user_message="Nguồn video này chưa được hỗ trợ tải ở Phase 0.",
            )
        download_url = source.metadata.get("download_url")
        if not source.source_id or not isinstance(download_url, str) or not download_url:
            raise ServiceError(
                stage="acquiring",
                error_code="source_download_url_missing",
                user_message="Nguồn video chưa có URL tải hợp lệ.",
            )

        run_downloader = downloader or download_videos
        videos = [
            {
                "aweme_id": source.source_id,
                "author": source.author or "unknown",
                "title": source.title or source.source_id,
                "download_url": download_url,
            }
        ]
        success, _ = await run_downloader(videos, output_dir=str(workspace.root), concurrency=1)
        if success != 1:
            raise ServiceError(
                stage="acquiring",
                error_code="download_failed",
                user_message="Không tải được video nguồn.",
                retryable=True,
            )

        matches = list(workspace.root.rglob("index.mp4"))
        if len(matches) != 1:
            raise ServiceError(
                stage="acquiring",
                error_code="download_artifact_missing",
                user_message="Video tải xong nhưng không tìm thấy artifact đầu ra.",
            )
        path = matches[0]
        return Artifact(
            id=f"source-video-{source.source_id}",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(path),
            mime_type="video/mp4",
            size=path.stat().st_size,
            created_at=datetime.now(timezone.utc),
        )
