import asyncio
import shutil
import subprocess
from datetime import datetime, timezone

import pytest

from server.app.domain.models import Artifact, ArtifactType, JobStage, VideoSource
from server.app.jobs import JobWorkspace
from server.app.media import extract_audio
from server.app.pipeline import PipelineCoordinator
from server.app.pipeline.stages import Phase0StageServices, build_phase0_handlers


pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required")


def _make_fixture(path):
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


class UnusedService:
    async def acquire(self, source, workspace):
        raise AssertionError("acquisition should not run when reusing artifacts")

    async def transcribe(self, artifact, options=None):
        raise AssertionError("transcription should not run when reusing artifacts")

    async def translate(self, transcript, target_language, options=None):
        raise AssertionError("translation should not run when reusing artifacts")

    async def synthesize(self, text, voice, options=None):
        raise AssertionError("TTS should not run when reusing artifacts")


def test_pipeline_reuses_existing_media_artifacts_for_downstream_stage(tmp_path):
    source_path = tmp_path / "source.mp4"
    dubbed_path = tmp_path / "dubbed.wav"
    _make_fixture(source_path)
    asyncio.run(extract_audio(source_path, dubbed_path))

    workspace = JobWorkspace.create(tmp_path, job_id="reuse-job")
    try:
        # Move controlled fixture files into the isolated job workspace so the
        # coordinator can verify containment before reusing them.
        workspace_source = workspace.path("source.mp4")
        workspace_dubbed = workspace.path("dubbed.wav")
        shutil.copyfile(source_path, workspace_source)
        shutil.copyfile(dubbed_path, workspace_dubbed)
        created_at = datetime.now(timezone.utc)
        existing = (
            Artifact(
                id="source-video-existing",
                type=ArtifactType.SOURCE_VIDEO,
                reference=str(workspace_source),
                mime_type="video/mp4",
                size=workspace_source.stat().st_size,
                created_at=created_at,
            ),
            Artifact(
                id="dubbed-audio-existing",
                type=ArtifactType.DUBBED_AUDIO,
                reference=str(workspace_dubbed),
                mime_type="audio/wav",
                size=workspace_dubbed.stat().st_size,
                created_at=created_at,
            ),
        )
        services = UnusedService()
        result = asyncio.run(
            PipelineCoordinator(
                build_phase0_handlers(
                    Phase0StageServices(
                        downloader=services,
                        transcriber=services,
                        translator=services,
                        tts=services,
                    )
                )
            ).run(
                VideoSource(url="https://fixture.example/video/1", platform="fixture", source_id="1"),
                workspace,
                requested_stages=(JobStage.MERGING, JobStage.FINALIZING),
                existing_artifacts=existing,
            )
        )
    finally:
        workspace.cleanup()

    assert result.job.state.value == "completed"
    assert any(artifact.type == ArtifactType.FINAL_VIDEO for artifact in result.job.artifacts)


def test_pipeline_rejects_existing_artifact_outside_workspace(tmp_path):
    workspace = JobWorkspace.create(tmp_path, job_id="invalid-reuse")
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"not allowed")
    artifact = Artifact(
        id="outside",
        type=ArtifactType.SOURCE_VIDEO,
        reference=str(outside),
        created_at=datetime.now(timezone.utc),
    )
    try:
        result = asyncio.run(
            PipelineCoordinator({}).run(
                VideoSource(url="https://fixture.example/video/1", platform="fixture"),
                workspace,
                requested_stages=(JobStage.FINALIZING,),
                existing_artifacts=(artifact,),
            )
        )
    finally:
        workspace.cleanup()

    assert result.job.state.value == "failed"
    assert result.job.error["error_code"] == "invalid_existing_artifact"
