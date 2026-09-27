import asyncio
import secrets
from datetime import datetime, timezone
from pathlib import Path

from server.app.domain.models import Job, JobStage, JobState, VideoSource
from server.app.jobs import JobRepository, JobWorkspace
from server.app.pipeline import DEFAULT_PIPELINE_STAGES, PipelineCoordinator, PipelineResult


class JobManager:
    def __init__(
        self,
        coordinator: PipelineCoordinator,
        *,
        repository: JobRepository | None = None,
        workspace_base: Path | str = "/tmp/jobs",
    ):
        self.repository = repository or JobRepository()
        self.coordinator = coordinator
        self.workspace_base = Path(workspace_base)
        self._pending: dict[str, tuple[VideoSource, JobWorkspace, tuple[JobStage, ...], str]] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def enqueue(
        self,
        source: VideoSource,
        requested_stages: tuple[JobStage, ...] = DEFAULT_PIPELINE_STAGES,
        target_language: str = "vi",
    ) -> Job:
        job_id = secrets.token_urlsafe(18)
        now = datetime.now(timezone.utc)
        job = Job(id=job_id, created_at=now, updated_at=now)
        workspace = JobWorkspace.create(self.workspace_base, job_id=job_id)
        self.repository.save(job)
        self._pending[job_id] = (source, workspace, requested_stages, target_language)
        self._cancel_events[job_id] = asyncio.Event()
        return job

    async def run(self, job_id: str) -> Job:
        pending = self._pending.get(job_id)
        if pending is None:
            raise KeyError(job_id)
        source, workspace, stages, target_language = pending
        result: PipelineResult = await self.coordinator.run(
            source,
            workspace,
            requested_stages=stages,
            target_language=target_language,
            job_id=job_id,
            cancel_event=self._cancel_events[job_id],
        )
        current = self.repository.get(job_id)
        if current and current.state == JobState.CANCELLED:
            result = PipelineResult(
                job=result.job.model_copy(update={"state": JobState.CANCELLED}),
                context=result.context,
            )
        self.repository.update(result.job)
        return result.job

    def cancel(self, job_id: str) -> Job | None:
        event = self._cancel_events.get(job_id)
        if event:
            event.set()
        return self.repository.cancel(job_id)
