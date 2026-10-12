import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.app.domain.models import Artifact, ArtifactType, JobStage, Transcript, Voice
from server.app.downloader import SingleVideoDownloader
from server.app.media import extract_audio, merge_audio
from server.app.pipeline.coordinator import PipelineContext, StageHandler
from server.app.providers.contracts import TranscriptionProvider, TranslationProvider, TtsProvider
from server.app.subtitle import generate_srt
from server.app.security import ServiceError


@dataclass(frozen=True)
class Phase0StageServices:
    downloader: SingleVideoDownloader
    transcriber: TranscriptionProvider
    translator: TranslationProvider
    tts: TtsProvider
    voice: Voice | None = None


def _find_artifact(context: PipelineContext, artifact_type: ArtifactType) -> Artifact | None:
    return next((artifact for artifact in reversed(context.artifacts) if artifact.type == artifact_type), None)


def _json_artifact(context: PipelineContext, artifact_type: ArtifactType, filename: str, payload: Any) -> Artifact:
    path = context.workspace.path(filename)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return Artifact(
        id=f"{artifact_type.value}-{context.source.source_id or context.source.url.host}",
        type=artifact_type,
        reference=str(path),
        mime_type="application/json",
        size=path.stat().st_size,
        created_at=datetime.now(timezone.utc),
    )


def build_phase0_handlers(services: Phase0StageServices) -> dict[JobStage, StageHandler]:
    async def acquire(context: PipelineContext) -> None:
        artifact = await services.downloader.acquire(context.source, context.workspace)
        context.add_artifact(artifact)

    async def transcribe(context: PipelineContext) -> None:
        source = _find_artifact(context, ArtifactType.SOURCE_AUDIO)
        if source is None:
            source = _find_artifact(context, ArtifactType.SOURCE_VIDEO)
        if source is None:
            raise ServiceError("transcribing", "source_artifact_missing", "Thiếu video nguồn để transcribe.")
        transcript = await services.transcriber.transcribe(source, context.options)
        context.transcript = transcript
        context.add_artifact(_json_artifact(
            context,
            ArtifactType.SOURCE_TRANSCRIPT,
            "transcript.json",
            transcript.model_dump(mode="json"),
        ))

    async def extract(context: PipelineContext) -> None:
        source = _find_artifact(context, ArtifactType.SOURCE_VIDEO)
        if source is None:
            raise ServiceError("extracting_audio", "source_artifact_missing", "Thiếu video nguồn để extract audio.")
        path = context.workspace.path("source.wav")
        await extract_audio(source.reference, path)
        context.add_artifact(Artifact(
            id=f"source-audio-{context.source.source_id or 'job'}",
            type=ArtifactType.SOURCE_AUDIO, reference=str(path), mime_type="audio/wav",
            size=path.stat().st_size, created_at=datetime.now(timezone.utc),
        ))

    async def translate(context: PipelineContext) -> None:
        if context.transcript is None:
            raise ServiceError("translating", "transcript_missing", "Thiếu transcript để dịch.")
        translated = await services.translator.translate(
            context.transcript,
            context.target_language,
            context.options,
        )
        context.translated_transcript = translated
        context.add_artifact(_json_artifact(
            context,
            ArtifactType.TRANSLATED_TRANSCRIPT,
            "translated.json",
            translated.model_dump(mode="json"),
        ))

    async def subtitle(context: PipelineContext) -> None:
        transcript = context.translated_transcript or context.transcript
        if transcript is None:
            raise ServiceError("generating_subtitle", "transcript_missing", "Thiếu transcript để tạo subtitle.")
        path = context.workspace.path("subtitle.srt")
        path.write_text(generate_srt(transcript), encoding="utf-8")
        context.add_artifact(Artifact(
            id=f"subtitle-{context.source.source_id or 'job'}",
            type=ArtifactType.SUBTITLE,
            reference=str(path),
            mime_type="application/x-subrip",
            size=path.stat().st_size,
            created_at=datetime.now(timezone.utc),
        ))

    async def tts(context: PipelineContext) -> None:
        transcript = context.translated_transcript or context.transcript
        voice = context.voice or services.voice
        if transcript is None:
            raise ServiceError("generating_tts", "transcript_missing", "Thiếu transcript để tạo voice.")
        if voice is None:
            raise ServiceError("generating_tts", "voice_missing", "Chưa chọn voice cho TTS.")
        artifact = await services.tts.synthesize(
            transcript.text,
            voice,
            {"output": str(context.workspace.path("dubbed.mp3")), **context.options},
        )
        context.add_artifact(artifact)

    async def merge(context: PipelineContext) -> None:
        source = _find_artifact(context, ArtifactType.SOURCE_VIDEO)
        dubbed = _find_artifact(context, ArtifactType.DUBBED_AUDIO)
        if source is None or dubbed is None:
            raise ServiceError("merging", "merge_artifact_missing", "Thiếu video hoặc dubbed audio để ghép.")
        output = context.workspace.path("output.mp4")
        await merge_audio(source.reference, dubbed.reference, output)
        context.add_artifact(Artifact(
            id=f"final-video-{context.source.source_id or 'job'}",
            type=ArtifactType.FINAL_VIDEO,
            reference=str(output),
            mime_type="video/mp4",
            size=output.stat().st_size,
            created_at=datetime.now(timezone.utc),
        ))

    async def finalize(context: PipelineContext) -> None:
        if not context.artifacts:
            raise ServiceError("finalizing", "no_artifacts", "Pipeline không tạo được artifact nào.")

    return {
        JobStage.ACQUIRING: acquire,
        JobStage.EXTRACTING_AUDIO: extract,
        JobStage.TRANSCRIBING: transcribe,
        JobStage.TRANSLATING: translate,
        JobStage.GENERATING_SUBTITLE: subtitle,
        JobStage.GENERATING_TTS: tts,
        JobStage.MERGING: merge,
        JobStage.FINALIZING: finalize,
    }
