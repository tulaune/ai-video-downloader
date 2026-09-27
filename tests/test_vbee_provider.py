import asyncio

from server.app.domain.models import ArtifactType, Voice
from server.app.providers.vbee import VbeeProvider


def test_vbee_lists_normalized_registry_voices(tmp_path):
    registry = tmp_path / "vbee.csv"
    registry.write_text(
        "voice_id,name,gender,age,use_case,region,language\n"
        "voice-1,Voice One,Nữ,Thanh niên,Review,Miền Nam,Tiếng Việt\n",
        encoding="utf-8",
    )

    voices = asyncio.run(VbeeProvider(registry).list_voices())

    assert voices[0].provider == "vbee"
    assert voices[0].voice_id == "voice-1"
    assert voices[0].category == "Review"


def test_vbee_synthesize_wraps_legacy_result(monkeypatch, tmp_path):
    async def fake_run_tts(**kwargs):
        output = tmp_path / "dub.mp3"
        output.write_bytes(b"audio")
        assert kwargs["voice_code"] == "voice-1"
        return {"output_file": str(output), "bytes": 5, "mode": "sync"}

    monkeypatch.setattr("server.app.providers.vbee.run_tts", fake_run_tts)
    voice = Voice(provider="vbee", voice_id="voice-1", display_name="Voice One")
    artifact = asyncio.run(
        VbeeProvider().synthesize("Xin chào", voice, {"output": str(tmp_path / "dub.mp3")})
    )

    assert artifact.type == ArtifactType.DUBBED_AUDIO
    assert artifact.size == 5
