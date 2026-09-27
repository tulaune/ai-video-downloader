import asyncio
import shutil
import subprocess

import pytest

from server.app.media import extract_audio, merge_audio


pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required")


def _make_fixture(path):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=12",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
            "-t", "0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_extract_and_merge_validate_real_ffmpeg_outputs(tmp_path):
    source = tmp_path / "source.mp4"
    extracted = tmp_path / "source.wav"
    output = tmp_path / "merged.mp4"
    _make_fixture(source)

    asyncio.run(extract_audio(source, extracted))
    asyncio.run(merge_audio(source, extracted, output))

    assert extracted.stat().st_size > 0
    assert output.stat().st_size > 0
