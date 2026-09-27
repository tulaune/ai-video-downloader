import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from server.app.domain.models import Artifact, Job, JobStage, JobState, Transcript, VideoSource
from server.app.jobs import JobWorkspace
from server.app.security import ProviderCredentials, ServiceError


DEFAULT_PIPELINE_STAGES = (
    JobStage.ACQUIRING,
    JobStage.TRANSCRIBING,
    JobStage.TRANSLATING,
    JobStage.GENERATING_SUBTITLE,
    JobStage.GENERATING_TTS,
    JobStage.MERGING,
    JobStage.FINALIZING,
)

StageHandler = Callable[["PipelineContext"], Awaitable[None]]


@dataclass
class PipelineContext:
    source: VideoSource
    workspace: JobWorkspace
    target_language: str = "vi"
    credentials: ProviderCredentials | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    transcript: Transcript | None = None
    translated_transcript: Transcript | None = None

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts.append(artifact)


@dataclass(frozen=True)
class PipelineResult:
    job: Job
    context: PipelineContext


class PipelineCoordinator:
    """Run explicit, individually addressable stages with progress state."""

    def __init__(self, handlers: dict[JobStage, StageHandler]):
        self._handlers = dict(handlers)

    async def run(
        self,
        source: VideoSource,
        workspace: JobWorkspace,
        *,
        requested_stages: tuple[JobStage, ...] = DEFAULT_PIPELINE_STAGES,
        target_language: str = "vi",
        credentials: ProviderCredentials | None = None,
        job_id: str | None = None,
    ) -> PipelineResult:
        stages = self._validate_stages(requested_stages)
        now = datetime.now(timezone.utc)
        job = Job(
            id=job_id or secrets.token_urlsafe(18),
            state=JobState.QUEUED,
            created_at=now,
            updated_at=now,
        )
        context = PipelineContext(
            source=source,
            workspace=workspace,
            target_language=target_language,
            credentials=credentials,
        )
        if not stages:
            return self._failed(job, context, ServiceError(
                stage="pipeline",
                error_code="empty_pipeline",
                user_message="Pipeline không có stage nào để chạy.",
            ))

        for index, stage in enumerate(stages):
            job = job.model_copy(update={
                "state": JobState.RUNNING,
                "current_stage": stage,
                "progress": index / len(stages),
                "updated_at": datetime.now(timezone.utc),
                "artifacts": context.artifacts,
            })
            handler = self._handlers.get(stage)
            if handler is None:
                return self._failed(job, context, ServiceError(
                    stage=stage.value,
                    error_code="stage_not_implemented",
                    user_message=f"Stage {stage.value} chưa được triển khai.",
                ))
            try:
                await handler(context)
            except ServiceError as error:
                return self._failed(job, context, error)
            except Exception as error:
                return self._failed(job, context, ServiceError(
                    stage=stage.value,
                    error_code="stage_failed",
                    user_message="Một bước xử lý gặp lỗi.",
                    technical_message=str(error),
                    retryable=True,
                ))

        now = datetime.now(timezone.utc)
        job = job.model_copy(update={
            "state": JobState.COMPLETED,
            "current_stage": JobStage.FINALIZING,
            "progress": 1,
            "updated_at": now,
            "artifacts": context.artifacts,
            "error": None,
        })
        return PipelineResult(job=job, context=context)

    @staticmethod
    def _validate_stages(stages: tuple[JobStage, ...]) -> tuple[JobStage, ...]:
        if len(set(stages)) != len(stages):
            raise ValueError("Pipeline stages must be unique")
        return stages

    @staticmethod
    def _failed(job: Job, context: PipelineContext, error: ServiceError) -> PipelineResult:
        failed = job.model_copy(update={
            "state": JobState.FAILED,
            "updated_at": datetime.now(timezone.utc),
            "error": error.public_dict(),
            "artifacts": context.artifacts,
        })
        return PipelineResult(job=failed, context=context)
