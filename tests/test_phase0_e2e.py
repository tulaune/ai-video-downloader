import asyncio
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from server.app.domain.models import Artifact, ArtifactType, JobStage, Segment, Transcript, VideoSource, Voice
from server.app.jobs import JobWorkspace
from server.app.media import extract_audio
from server.app.pipeline import PipelineCoordinator
from server.app.pipeline.stages import Phase0StageServices, build_phase0_handlers
from server.app.providers import FasterWhisperProvider, LocalMockTranslationProvider, LocalMockTtsProvider


pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required")


def _make_video(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=12",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
            "-t", "0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class FixtureDownloader:
    def __init__(self, source_path: Path):
        self.source_path = source_path

    async def acquire(self, source, workspace):
        destination = workspace.path("source.mp4")
        shutil.copyfile(self.source_path, destination)
        return Artifact(
            id="source-video-fixture",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(destination),
            mime_type="video/mp4",
            size=destination.stat().st_size,
            created_at=datetime.now(timezone.utc),
        )


class FixtureTranscriber:
    async def transcribe(self, artifact, options=None):
        return Transcript(
            language="en",
            text="Hello fixture",
            segments=[Segment(start=0, end=0.5, text="Hello fixture")],
        )


class FixtureTranslator:
    async def translate(self, transcript, target_language, options=None):
        return Transcript(
            language=target_language,
            text="Xin chào fixture",
            segments=[Segment(start=0, end=0.5, text="Xin chào fixture")],
        )


class FixtureTts:
    async def synthesize(self, text, voice, options=None):
        output = Path(options["output"]).with_suffix(".wav")
        await extract_audio(options["source_video"], output)
        return Artifact(
            id="dubbed-audio-fixture",
            type=ArtifactType.DUBBED_AUDIO,
            reference=str(output),
            mime_type="audio/wav",
            size=output.stat().st_size,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )


def test_local_pipeline_runs_without_claude_or_network(tmp_path):
    source_path = tmp_path / "fixture.mp4"
    _make_video(source_path)

    # This fixture TTS needs the acquired source path; keep that detail local
    # to the test while exercising the real stage coordinator and FFmpeg.
    class TestTts(FixtureTts):
        async def synthesize(self, text, voice, options=None):
            options = dict(options or {})
            options["source_video"] = str(options["output"]).replace("dubbed.mp3", "source.mp4")
            return await super().synthesize(text, voice, options)

    workspace = JobWorkspace.create(tmp_path, job_id="e2e-job")
    try:
        services = Phase0StageServices(
            downloader=FixtureDownloader(source_path),
            transcriber=FixtureTranscriber(),
            translator=FixtureTranslator(),
            tts=TestTts(),
            voice=Voice(provider="fixture", voice_id="fixture", display_name="Fixture"),
        )
        result = asyncio.run(
            PipelineCoordinator(build_phase0_handlers(services)).run(
                VideoSource(
                    url="https://fixture.example/video/1",
                    platform="fixture",
                    source_id="fixture",
                ),
                workspace,
                requested_stages=(
                    JobStage.ACQUIRING,
                    JobStage.EXTRACTING_AUDIO,
                    JobStage.TRANSCRIBING,
                    JobStage.TRANSLATING,
                    JobStage.GENERATING_SUBTITLE,
                    JobStage.GENERATING_TTS,
                    JobStage.MERGING,
                    JobStage.FINALIZING,
                ),
            )
        )
        final_artifact = next(a for a in result.job.artifacts if a.type == ArtifactType.FINAL_VIDEO)
        assert result.job.state.value == "completed"
        assert Path(final_artifact.reference).is_file()
        assert Path(final_artifact.reference).stat().st_size > 0
        assert any(a.type == ArtifactType.SOURCE_AUDIO and a.size and a.size > 0 for a in result.job.artifacts)
        assert (workspace.root / "subtitle.srt").read_text(encoding="utf-8").startswith("1\n")
    finally:
        workspace.cleanup()


def test_local_pipeline_runs_real_tiny_whisper_with_mock_providers(tmp_path):
    source_path = tmp_path / "real-whisper-fixture.mp4"
    _make_video(source_path)
    workspace = JobWorkspace.create(tmp_path, job_id="real-whisper-job")
    try:
        services = Phase0StageServices(
            downloader=FixtureDownloader(source_path),
            transcriber=FasterWhisperProvider(model="tiny"),
            translator=LocalMockTranslationProvider(),
            tts=LocalMockTtsProvider(),
            voice=Voice(provider="local-mock-tts", voice_id="fixture", display_name="Fixture"),
        )
        result = asyncio.run(PipelineCoordinator(build_phase0_handlers(services)).run(
            VideoSource(url="https://fixture.example/video/real-whisper", platform="fixture", source_id="fixture"),
            workspace,
            requested_stages=(
                JobStage.ACQUIRING, JobStage.EXTRACTING_AUDIO, JobStage.TRANSCRIBING,
                JobStage.TRANSLATING, JobStage.GENERATING_SUBTITLE,
                JobStage.GENERATING_TTS, JobStage.MERGING, JobStage.FINALIZING,
            ),
        ))
        assert result.job.state.value == "completed"
        assert {artifact.type for artifact in result.job.artifacts} >= {
            ArtifactType.SOURCE_VIDEO, ArtifactType.SOURCE_AUDIO,
            ArtifactType.SOURCE_TRANSCRIPT, ArtifactType.TRANSLATED_TRANSCRIPT,
            ArtifactType.SUBTITLE, ArtifactType.DUBBED_AUDIO, ArtifactType.FINAL_VIDEO,
        }
        assert all(artifact.size is not None and Path(artifact.reference).is_file() for artifact in result.job.artifacts)
        assert all(
            artifact.size and Path(artifact.reference).is_file()
            for artifact in result.job.artifacts
            if artifact.type in {ArtifactType.SOURCE_VIDEO, ArtifactType.SOURCE_AUDIO, ArtifactType.DUBBED_AUDIO, ArtifactType.FINAL_VIDEO}
        )
    finally:
        workspace.cleanup()
