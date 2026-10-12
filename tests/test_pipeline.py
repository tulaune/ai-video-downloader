import asyncio
from datetime import datetime, timezone

from server.app.domain.models import Artifact, ArtifactType, JobStage, JobState, VideoSource
from server.app.jobs import JobWorkspace
from server.app.pipeline import PipelineCoordinator


def _source() -> VideoSource:
    return VideoSource(url="https://www.douyin.com/video/123", platform="douyin", source_id="123")


def test_pipeline_runs_requested_stages_in_order_and_tracks_progress(tmp_path):
    events = []

    async def acquire(context):
        events.append(JobStage.ACQUIRING)

    async def transcribe(context):
        events.append(JobStage.TRANSCRIBING)

    workspace = JobWorkspace.create(tmp_path)
    try:
        result = asyncio.run(
            PipelineCoordinator({
                JobStage.ACQUIRING: acquire,
                JobStage.TRANSCRIBING: transcribe,
            }).run(
                _source(),
                workspace,
                requested_stages=(JobStage.ACQUIRING, JobStage.TRANSCRIBING),
            )
        )
    finally:
        workspace.cleanup()

    assert events == [JobStage.ACQUIRING, JobStage.TRANSCRIBING]
    assert result.job.state == JobState.COMPLETED
    assert result.job.progress == 1
    assert result.job.current_stage == JobStage.FINALIZING


def test_pipeline_preserves_completed_artifacts_when_a_later_stage_fails(tmp_path):
    async def acquire(context):
        context.add_artifact(Artifact(
            id="source-123",
            type=ArtifactType.SOURCE_VIDEO,
            reference=str(context.workspace.path("source.mp4")),
            created_at=datetime.now(timezone.utc),
        ))

    async def fail_translation(context):
        from server.app.security import ServiceError
        raise ServiceError(
            stage="translating",
            error_code="provider_unavailable",
            user_message="Provider tạm thời không khả dụng.",
            retryable=True,
        )

    workspace = JobWorkspace.create(tmp_path)
    try:
        result = asyncio.run(
            PipelineCoordinator({
                JobStage.ACQUIRING: acquire,
                JobStage.TRANSLATING: fail_translation,
            }).run(
                _source(),
                workspace,
                requested_stages=(JobStage.ACQUIRING, JobStage.TRANSLATING),
            )
        )
    finally:
        workspace.cleanup()

    assert result.job.state == JobState.FAILED
    assert result.job.error["retryable"] is True
    assert [artifact.id for artifact in result.job.artifacts] == ["source-123"]


def test_pipeline_marks_unimplemented_stage_without_stack_trace(tmp_path):
    workspace = JobWorkspace.create(tmp_path)
    try:
        result = asyncio.run(
            PipelineCoordinator({}).run(
                _source(),
                workspace,
                requested_stages=(JobStage.MERGING,),
            )
        )
    finally:
        workspace.cleanup()

    assert result.job.state == JobState.FAILED
    assert result.job.error == {
        "stage": "merging",
        "error_code": "stage_not_implemented",
        "user_message": "Stage merging chưa được triển khai.",
        "retryable": False,
    }


def test_pipeline_honors_cancellation_between_stages(tmp_path):
    import asyncio

    cancel_event = asyncio.Event()
    events = []

    async def acquire(context):
        events.append(JobStage.ACQUIRING)
        cancel_event.set()

    async def transcribe(context):
        events.append(JobStage.TRANSCRIBING)

    workspace = JobWorkspace.create(tmp_path)
    try:
        result = asyncio.run(
            PipelineCoordinator({
                JobStage.ACQUIRING: acquire,
                JobStage.TRANSCRIBING: transcribe,
            }).run(
                _source(),
                workspace,
                requested_stages=(JobStage.ACQUIRING, JobStage.TRANSCRIBING),
                cancel_event=cancel_event,
            )
        )
    finally:
        workspace.cleanup()

    assert events == [JobStage.ACQUIRING]
    assert result.job.state == JobState.CANCELLED
