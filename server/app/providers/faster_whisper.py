from typing import Any, Mapping

from backend.transcribe import transcribe_video
from server.app.domain.models import Artifact, Transcript


class FasterWhisperProvider:
    """Normalize the existing Faster Whisper implementation into a provider."""

    name = "faster-whisper"

    def __init__(self, model: str = "base", language: str | None = None):
        self.model = model
        self.language = language

    async def transcribe(
        self,
        input_artifact: Artifact,
        options: Mapping[str, Any] | None = None,
    ) -> Transcript:
        values = dict(options or {})
        result = await transcribe_video(
            video_path=input_artifact.reference,
            model=str(values.get("model", self.model)),
            language=values.get("language", self.language),
            aweme_id=values.get("source_id"),
        )
        return Transcript.model_validate(result)
