"""Opt-in Phase 0 integration checks for real providers.

These tests are skipped by default and must only run with credentials already
configured in the local environment. Never paste provider secrets into this
file, a command line, or a commit.
"""

import asyncio
import os
import shutil
import subprocess
from datetime import datetime, timezone

import pytest

from server.app.domain.models import Artifact, ArtifactType, Voice
from server.app.providers.faster_whisper import FasterWhisperProvider
from server.app.providers.vbee import VbeeProvider
from server.app.security import ProviderCredentials


pytestmark = pytest.mark.skipif(
    os.environ.get("VELINGO_RUN_REAL_PROVIDER_TESTS") != "1",
    reason="set VELINGO_RUN_REAL_PROVIDER_TESTS=1 to run opt-in provider checks",
)


def _make_fixture(path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=160x90:r=12",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
            "-t", "0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_real_faster_whisper_tiny_fixture(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.mp4"
    _make_fixture(fixture)

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr("backend.transcribe.upsert_caption", noop)
    artifact = Artifact(
        id="whisper-fixture",
        type=ArtifactType.SOURCE_VIDEO,
        reference=str(fixture),
        created_at=datetime.now(timezone.utc),
    )

    transcript = asyncio.run(FasterWhisperProvider(model="tiny").transcribe(artifact))

    assert transcript.language
    assert all(segment.end >= segment.start for segment in transcript.segments)


def test_real_vbee_tts_with_opt_in_credentials(tmp_path):
    token = os.environ.get("VBEE_TOKEN")
    app_id = os.environ.get("VBEE_APP_ID")
    if not token or not app_id:
        pytest.skip("VBEE_TOKEN and VBEE_APP_ID are required for the opt-in TTS check")

    output = tmp_path / "vbee-fixture.mp3"
    artifact = asyncio.run(
        VbeeProvider(
            credentials=ProviderCredentials(
                provider="vbee",
                fields={"token": token, "app_id": app_id},
            )
        ).synthesize(
            "Đây là bài kiểm tra ngắn cho Phase 0.",
            Voice(provider="vbee", voice_id=os.environ.get("VBEE_VOICE_CODE", ""), display_name="Phase 0"),
            {"output": str(output), "mode": "sync"},
        )
    )

    assert artifact.type == ArtifactType.DUBBED_AUDIO
    assert output.is_file()
    assert output.stat().st_size > 0
