import asyncio

from server.app.domain.models import Artifact, ArtifactType
from server.app.providers.faster_whisper import FasterWhisperProvider


def test_faster_whisper_provider_normalizes_legacy_result(monkeypatch, tmp_path):
    calls = {}

    async def fake_transcribe_video(**kwargs):
        calls.update(kwargs)
        return {
            "language": "zh",
            "language_probability": 0.91,
            "text": "你好",
            "segments": [{"start": 0, "end": 1, "text": "你好"}],
        }

    monkeypatch.setattr(
        "server.app.providers.faster_whisper.transcribe_video",
        fake_transcribe_video,
    )
    artifact = Artifact(
        id="source-1",
        type=ArtifactType.SOURCE_VIDEO,
        reference=str(tmp_path / "source.mp4"),
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    transcript = asyncio.run(
        FasterWhisperProvider(model="small", language="zh").transcribe(
            artifact,
            {"source_id": "1"},
        )
    )

    assert transcript.language == "zh"
    assert transcript.segments[0].text == "你好"
    assert calls == {
        "video_path": str(tmp_path / "source.mp4"),
        "model": "small",
        "language": "zh",
        "aweme_id": "1",
    }
