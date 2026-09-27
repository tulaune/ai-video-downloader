import asyncio

import pytest

from backend.voices import omnivoice, vbee


def test_vbee_headers_require_both_credentials(monkeypatch):
    monkeypatch.delenv("VBEE_TOKEN", raising=False)
    monkeypatch.delenv("VBEE_APP_ID", raising=False)

    with pytest.raises(EnvironmentError):
        vbee._headers()


def test_vbee_cli_parser_extracts_options():
    parsed = vbee._parse_cli(["Xin", "chào", "--mode", "sync", "--voice", "voice-1", "-o", "out.mp3"])

    assert parsed == {
        "text": "Xin chào",
        "mode": "sync",
        "output": "out.mp3",
        "voice": "voice-1",
        "speed": None,
    }


def test_omnivoice_rejects_empty_text():
    with pytest.raises(ValueError, match="text is required"):
        asyncio.run(omnivoice.run_tts(""))
