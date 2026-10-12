import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from server.app.domain.models import Artifact, ArtifactType, Segment, Transcript, Voice
from server.app.security import ServiceError


class LocalMockTranslationProvider:
    """Deterministic offline translation seam for Phase 0 local runs."""

    name = "local-mock-translation"

    async def translate(self, transcript: Transcript, target_language: str, options: Mapping[str, Any] | None = None) -> Transcript:
        segments = [
            Segment(start=item.start, end=item.end, text=f"[{target_language}] {item.text}")
            for item in transcript.segments
        ]
        return Transcript(
            language=target_language,
            language_probability=transcript.language_probability,
            text=" ".join(item.text for item in segments),
            segments=segments,
        )


class LocalMockTtsProvider:
    """Offline TTS substitute that creates a valid short MP3 with FFmpeg."""

    name = "local-mock-tts"

    async def list_voices(self) -> Sequence[Voice]:
        return [Voice(provider=self.name, voice_id="fixture", display_name="Local fixture")]

    async def synthesize(self, text: str, voice: Voice, options: Mapping[str, Any] | None = None) -> Artifact:
        output = Path(str(dict(options or {}).get("output", "dubbed.mp3")))
        if shutil.which("ffmpeg") is None:
            raise ServiceError("generating_tts", "ffmpeg_missing", "Media processor chưa được cài đặt.")
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.5, min(30.0, 0.08 * max(1, len(text))))
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
            "-t", f"{duration:.2f}", "-q:a", "5", str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            raise ServiceError(
                "generating_tts", "local_tts_failed", "Không tạo được audio local.",
                technical_message=stderr.decode(errors="replace")[-1000:], retryable=True,
            )
        return Artifact(
            id="dubbed-audio-local-mock", type=ArtifactType.DUBBED_AUDIO,
            reference=str(output), mime_type="audio/mpeg", size=output.stat().st_size,
            created_at=datetime.now(timezone.utc),
        )
