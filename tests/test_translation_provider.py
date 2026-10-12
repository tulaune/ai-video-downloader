import asyncio
import json

import httpx
import pytest

from server.app.domain.models import Segment, Transcript
from server.app.providers.translation import OpenAICompatibleTranslationProvider
from server.app.security import ProviderCredentials, ServiceError


def _transcript():
    return Transcript(
        language="en",
        language_probability=0.9,
        text="Hello world",
        segments=[Segment(start=0, end=1.2, text="Hello world")],
    )


def test_translation_provider_preserves_segment_timing_and_uses_request_key():
    def handler(request: httpx.Request):
        assert request.headers["authorization"] == "Bearer test-secret"
        body = json.loads(request.content)
        assert body["temperature"] == 0
        content = json.dumps({
            "language": "vi",
            "text": "Xin chào thế giới",
            "segments": [{"id": 0, "text": "Xin chào thế giới"}],
        })
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
            request=request,
        )

    provider = OpenAICompatibleTranslationProvider(
        ProviderCredentials(provider="test", fields={"api_key": "test-secret"}),
        base_url="https://provider.test/v1",
        transport=httpx.MockTransport(handler),
    )
    translated = asyncio.run(provider.translate(_transcript(), "vi"))

    assert translated.language == "vi"
    assert translated.segments[0].start == 0
    assert translated.segments[0].end == 1.2
    assert translated.segments[0].text == "Xin chào thế giới"


def test_translation_provider_rejects_segment_count_mismatch():
    def handler(request: httpx.Request):
        content = json.dumps({"language": "vi", "text": "", "segments": []})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]}, request=request)

    provider = OpenAICompatibleTranslationProvider(
        ProviderCredentials(provider="test", fields={"api_key": "secret"}),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ServiceError, match="khớp số lượng"):
        asyncio.run(provider.translate(_transcript(), "vi"))


def test_translation_provider_requires_api_key():
    provider = OpenAICompatibleTranslationProvider(
        ProviderCredentials(provider="test", fields={"other": "secret"}),
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    with pytest.raises(ServiceError) as exc_info:
        asyncio.run(provider.translate(_transcript(), "vi"))
    assert exc_info.value.error_code == "provider_credential_missing"
