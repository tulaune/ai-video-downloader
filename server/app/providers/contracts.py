from typing import Any, Mapping, Protocol, Sequence

from server.app.domain.models import Artifact, Transcript, Voice


class TranscriptionProvider(Protocol):
    name: str

    async def transcribe(
        self,
        input_artifact: Artifact,
        options: Mapping[str, Any] | None = None,
    ) -> Transcript: ...


class TranslationProvider(Protocol):
    name: str

    async def translate(
        self,
        transcript: Transcript,
        target_language: str,
        options: Mapping[str, Any] | None = None,
    ) -> Transcript: ...


class TtsProvider(Protocol):
    name: str

    async def list_voices(self) -> Sequence[Voice]: ...

    async def synthesize(
        self,
        text: str,
        voice: Voice,
        options: Mapping[str, Any] | None = None,
    ) -> Artifact: ...
