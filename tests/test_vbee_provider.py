import asyncio

import pytest

from server.app.domain.models import ArtifactType, Voice
from server.app.providers.vbee import VbeeProvider
from server.app.security import ProviderCredentials
from server.app.security.errors import ServiceError


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
        assert kwargs["credentials"] == {"token": "token", "app_id": "app"}
        return {"output_file": str(output), "bytes": 5, "mode": "sync"}

    monkeypatch.setattr("server.app.providers.vbee.run_tts", fake_run_tts)
    voice = Voice(provider="vbee", voice_id="voice-1", display_name="Voice One")
    artifact = asyncio.run(
        VbeeProvider(
            credentials=ProviderCredentials(
                provider="vbee",
                fields={"token": "token", "app_id": "app"},
            )
        ).synthesize("Xin chào", voice, {"output": str(tmp_path / "dub.mp3")})
    )

    assert artifact.type == ArtifactType.DUBBED_AUDIO
    assert artifact.size == 5


def test_vbee_synthesize_requires_request_credentials(tmp_path):
    voice = Voice(provider="vbee", voice_id="voice-1", display_name="Voice One")

    with pytest.raises(ServiceError, match="Vbee credentials are required") as error:
        asyncio.run(VbeeProvider().synthesize("Xin chào", voice, {"output": str(tmp_path / "dub.mp3")}))
    assert error.value.error_code == "provider_credentials_missing"
