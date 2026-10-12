import asyncio

import pytest

from server.app.domain.models import Segment, Transcript, Voice
from server.app.providers.local import LocalMockTranslationProvider, LocalMockTtsProvider


def test_local_translation_preserves_segment_timing():
    result = asyncio.run(LocalMockTranslationProvider().translate(
        Transcript(language="en", text="hello", segments=[Segment(start=0, end=1, text="hello")]),
        "vi",
    ))
    assert result.language == "vi"
    assert result.segments[0].start == 0
    assert result.segments[0].text == "[vi] hello"


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="ffmpeg is required")
def test_local_tts_creates_audio(tmp_path):
    output = tmp_path / "dubbed.mp3"
    artifact = asyncio.run(LocalMockTtsProvider().synthesize(
        "hello", Voice(provider="local-mock-tts", voice_id="fixture", display_name="Fixture"),
        {"output": str(output)},
    ))
    assert artifact.size and output.stat().st_size == artifact.size
