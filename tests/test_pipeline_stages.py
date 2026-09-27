import asyncio
from datetime import datetime, timezone

from server.app.domain.models import Artifact, ArtifactType, Segment, Transcript, VideoSource, Voice
from server.app.jobs import JobWorkspace
from server.app.pipeline import PipelineCoordinator
from server.app.pipeline.stages import Phase0StageServices, build_phase0_handlers


class FakeDownloader:
    async def acquire(self, source, workspace):
        path = workspace.path("source.mp4")
        path.write_bytes(b"video")
        return Artifact(
            id="source-video-1",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(path),
            mime_type="video/mp4",
            size=5,
            created_at=datetime.now(timezone.utc),
        )


class FakeTranscriber:
    async def transcribe(self, artifact, options=None):
        return Transcript(
            language="en",
            text="Hello world",
            segments=[Segment(start=0, end=1, text="Hello world")],
        )


class FakeTranslator:
    async def translate(self, transcript, target_language, options=None):
        return Transcript(
            language=target_language,
            text="Xin chào thế giới",
            segments=[Segment(start=0, end=1, text="Xin chào thế giới")],
        )


class FakeTts:
    async def synthesize(self, text, voice, options=None):
        path = options["output"]
        with open(path, "wb") as handle:
            handle.write(b"audio")
        return Artifact(
            id="dubbed-audio-1",
            type=ArtifactType.DUBBED_AUDIO,
            reference=path,
            mime_type="audio/mpeg",
            size=5,
            created_at=datetime.now(timezone.utc),
        )


def test_phase0_handlers_create_transcript_translation_and_subtitle_artifacts(tmp_path):
    source = VideoSource(
        url="https://www.douyin.com/video/1",
        platform="douyin",
        source_id="1",
    )
    services = Phase0StageServices(
        downloader=FakeDownloader(),
        transcriber=FakeTranscriber(),
        translator=FakeTranslator(),
        tts=FakeTts(),
        voice=Voice(provider="test", voice_id="v1", display_name="Test"),
    )
    workspace = JobWorkspace.create(tmp_path)
    try:
        result = asyncio.run(
            PipelineCoordinator(build_phase0_handlers(services)).run(
                source,
                workspace,
                requested_stages=(
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.ACQUIRING,
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.TRANSCRIBING,
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.TRANSLATING,
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.GENERATING_SUBTITLE,
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.GENERATING_TTS,
                    __import__("server.app.domain.models", fromlist=["JobStage"]).JobStage.FINALIZING,
                ),
            )
        )
    finally:
        workspace.cleanup()

    assert result.job.state.value == "completed"
    assert {artifact.type for artifact in result.job.artifacts} == {
        ArtifactType.SOURCE_VIDEO,
        ArtifactType.SOURCE_TRANSCRIPT,
        ArtifactType.TRANSLATED_TRANSCRIPT,
        ArtifactType.SUBTITLE,
        ArtifactType.DUBBED_AUDIO,
    }
