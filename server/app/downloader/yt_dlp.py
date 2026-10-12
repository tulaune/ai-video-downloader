import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from server.app.domain.models import Artifact, ArtifactType, VideoSource
from server.app.jobs import JobWorkspace
from server.app.security import ServiceError, validate_public_http_url


class YtDlpAdapter:
    """Generic public-source adapter backed by the installed yt-dlp package."""

    name = "yt-dlp"
    _timeout_seconds = 180
    _supported_hosts = {
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "facebook.com",
        "fb.watch",
        "instagram.com",
        "vimeo.com",
        "x.com",
        "twitter.com",
        "bilibili.com",
    }

    @classmethod
    def supports_url(cls, url: str) -> bool:
        hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
        return any(hostname == host or hostname.endswith(f".{host}") for host in cls._supported_hosts)

    async def _run(self, *args: str, stage: str) -> tuple[str, str]:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "yt_dlp",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout_seconds
            )
        except asyncio.TimeoutError as error:
            process.kill()
            await process.wait()
            raise ServiceError(
                stage=stage,
                error_code="source_timeout",
                user_message="Nguồn video xử lý quá lâu.",
                retryable=True,
            ) from error

        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        if process.returncode != 0:
            raise ServiceError(
                stage=stage,
                error_code="source_extractor_failed",
                user_message="Không thể đọc hoặc tải nguồn video này.",
                technical_message=err[-2_000:],
                retryable=True,
            )
        return out, err

    async def analyze(self, url: str) -> VideoSource:
        if not self.supports_url(url):
            raise ServiceError(
                stage="analyzing",
                error_code="unsupported_platform",
                user_message="Nền tảng video này chưa được hỗ trợ trong Phase 0.",
            )
        output, _ = await self._run(
            "--dump-single-json",
            "--no-playlist",
            "--skip-download",
            "--quiet",
            "--no-warnings",
            url,
            stage="analyzing",
        )
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            raise ServiceError(
                stage="analyzing",
                error_code="source_metadata_invalid",
                user_message="Nguồn video trả về metadata không hợp lệ.",
            ) from error

        if payload.get("_type") in {"playlist", "multi_video"}:
            raise ServiceError(
                stage="analyzing",
                error_code="playlist_not_supported",
                user_message="Phase 0 chỉ xử lý một video mỗi job.",
            )

        source_url = str(payload.get("webpage_url") or url)
        hostname = (urlsplit(source_url).hostname or "").lower()
        extractor = str(payload.get("extractor_key") or payload.get("extractor") or "unknown")
        source_id = payload.get("id") or payload.get("display_id")
        thumbnail = payload.get("thumbnail")
        return VideoSource(
            url=url,
            platform=extractor.lower(),
            source_id=str(source_id) if source_id else None,
            title=payload.get("title"),
            author=payload.get("uploader") or payload.get("channel"),
            duration=payload.get("duration"),
            thumbnail_url=thumbnail,
            metadata={
                "extractor": extractor,
                "hostname": hostname,
                "webpage_url": source_url,
            },
        )

    async def download(self, source: VideoSource, workspace: JobWorkspace) -> Artifact:
        validate_public_http_url(str(source.url))
        if not self.supports_url(str(source.url)):
            raise ServiceError(
                stage="acquiring",
                error_code="unsupported_platform",
                user_message="Nền tảng video này chưa được hỗ trợ trong Phase 0.",
            )
        # The template token must reach yt-dlp unchanged; JobWorkspace.path()
        # intentionally sanitizes '%' for user-controlled filenames.
        output_template = str(workspace.root / "source.%(ext)s")
        output, _ = await self._run(
            "--no-playlist",
            "--format",
            "bestvideo*+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "--output",
            output_template,
            "--print",
            "after_move:filepath",
            "--quiet",
            "--no-warnings",
            str(source.url),
            stage="acquiring",
        )
        candidates = [Path(line) for line in output.splitlines() if line.strip()]
        candidates = [
            candidate.resolve()
            for candidate in candidates
            if candidate.resolve().parent == workspace.root and candidate.is_file()
        ]
        if len(candidates) != 1:
            candidates = [
                candidate
                for candidate in workspace.root.iterdir()
                if candidate.is_file() and candidate.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            ]
        if len(candidates) != 1 or candidates[0].stat().st_size == 0:
            raise ServiceError(
                stage="acquiring",
                error_code="download_artifact_missing",
                user_message="Tải xong nhưng không tìm thấy video đầu ra.",
            )

        path = candidates[0]
        return Artifact(
            id=f"source-video-{source.source_id or source.url.host}",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(path),
            mime_type="video/mp4" if path.suffix.lower() == ".mp4" else None,
            size=path.stat().st_size,
            created_at=datetime.now(timezone.utc),
        )
