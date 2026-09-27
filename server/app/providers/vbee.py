import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.voices.vbee import run_tts
from server.app.domain.models import Artifact, ArtifactType, Voice


class VbeeProvider:
    name = "vbee"

    def __init__(self, registry_path: str | Path | None = None):
        self.registry_path = Path(registry_path or Path(__file__).parents[3] / "voice" / "vbee.csv")

    async def list_voices(self) -> Sequence[Voice]:
        if not self.registry_path.exists():
            return []
        with self.registry_path.open(encoding="utf-8", newline="") as handle:
            return [
                Voice(
                    provider=self.name,
                    voice_id=row["voice_id"],
                    display_name=row.get("name") or row["voice_id"],
                    language=row.get("language"),
                    region=row.get("region"),
                    gender=row.get("gender"),
                    age_group=row.get("age"),
                    category=row.get("use_case"),
                )
                for row in csv.DictReader(handle)
            ]

    async def synthesize(
        self,
        text: str,
        voice: Voice,
        options: Mapping[str, Any] | None = None,
    ) -> Artifact:
        values = dict(options or {})
        output = Path(str(values.get("output", "dub.mp3")))
        result = await run_tts(
            text=text,
            mode=str(values.get("mode", "async")),
            output=str(output),
            voice_code=voice.voice_id,
            speed=values.get("speed"),
        )
        return Artifact(
            id=f"dubbed-audio-{voice.voice_id}",
            type=ArtifactType.DUBBED_AUDIO,
            reference=str(result["output_file"]),
            mime_type="audio/mpeg",
            size=int(result["bytes"]),
            created_at=datetime.now(timezone.utc),
        )
