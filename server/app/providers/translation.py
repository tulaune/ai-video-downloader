import json
from typing import Any, Mapping

import httpx
from pydantic import BaseModel, ConfigDict

from server.app.domain.models import Segment, Transcript
from server.app.security import ProviderCredentials, ServiceError


class _TranslatedSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    text: str


class _TranslatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    text: str
    segments: list[_TranslatedSegment]


class OpenAICompatibleTranslationProvider:
    """BYOK translation adapter using a structured Chat Completions response."""

    name = "openai-compatible"

    def __init__(
        self,
        credentials: ProviderCredentials,
        *,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    async def translate(
        self,
        transcript: Transcript,
        target_language: str,
        options: Mapping[str, Any] | None = None,
    ) -> Transcript:
        values = dict(options or {})
        try:
            api_key = self.credentials.secret("api_key")
        except KeyError as error:
            raise ServiceError(
                stage="translating",
                error_code="provider_credential_missing",
                user_message="Thiếu API key cho translation provider.",
            ) from error

        expected = [
            {"id": index, "start": segment.start, "end": segment.end, "text": segment.text}
            for index, segment in enumerate(transcript.segments)
        ]
        request = {
            "model": str(values.get("model", self.model)),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Translate every transcript segment into the requested language. "
                        "Return JSON only with language, text, and segments. "
                        "Each segment must contain the original numeric id and translated text."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_language": target_language,
                            "source_language": transcript.language,
                            "segments": expected,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=request)
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ServiceError(
                stage="translating",
                error_code="provider_http_error",
                user_message="Translation provider trả về lỗi.",
                technical_message=f"status={error.response.status_code}",
                retryable=error.response.status_code >= 500,
            ) from error
        except httpx.HTTPError as error:
            raise ServiceError(
                stage="translating",
                error_code="provider_network_error",
                user_message="Không kết nối được translation provider.",
                technical_message=type(error).__name__,
                retryable=True,
            ) from error

        try:
            content = response.json()["choices"][0]["message"]["content"]
            payload = _TranslatedPayload.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ServiceError(
                stage="translating",
                error_code="provider_malformed_response",
                user_message="Translation provider trả về dữ liệu không hợp lệ.",
            ) from error

        if len(payload.segments) != len(transcript.segments):
            raise ServiceError(
                stage="translating",
                error_code="translation_segment_count_mismatch",
                user_message="Bản dịch không khớp số lượng segment gốc.",
            )
        ids = [segment.id for segment in payload.segments]
        if ids != list(range(len(transcript.segments))):
            raise ServiceError(
                stage="translating",
                error_code="translation_segment_id_mismatch",
                user_message="Bản dịch không khớp thứ tự segment gốc.",
            )

        translated_segments = [
            Segment(start=source.start, end=source.end, text=translated.text)
            for source, translated in zip(transcript.segments, payload.segments)
        ]
        return Transcript(
            language=payload.language,
            language_probability=transcript.language_probability,
            text=payload.text,
            segments=translated_segments,
        )
