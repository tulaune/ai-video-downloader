import asyncio
import secrets
from datetime import datetime, timezone
from pathlib import Path

from server.app.domain.models import Job, JobStage, JobState, VideoSource
from server.app.jobs import JobRepository, JobWorkspace
from server.app.pipeline import DEFAULT_PIPELINE_STAGES, PipelineCoordinator, PipelineResult
from server.app.security import ProviderCredentials
from server.app.domain.models import Voice


class JobManager:
    def __init__(
        self,
        coordinator: PipelineCoordinator | None = None,
        *,
        coordinator_factory=None,
        repository: JobRepository | None = None,
        workspace_base: Path | str = "/tmp/jobs",
        workspace_ttl_seconds: float = 3600,
    ):
        self.repository = repository or JobRepository()
        if coordinator is None and coordinator_factory is None:
            raise ValueError("coordinator or coordinator_factory is required")
        self.coordinator = coordinator
        self.coordinator_factory = coordinator_factory
        self.workspace_base = Path(workspace_base)
        if workspace_ttl_seconds < 0:
            raise ValueError("workspace_ttl_seconds must be non-negative")
        self.workspace_ttl_seconds = workspace_ttl_seconds
        self._pending: dict[str, tuple[VideoSource, JobWorkspace, tuple[JobStage, ...], str, PipelineCoordinator, ProviderCredentials | None, Voice | None, dict]] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def enqueue(
        self,
        source: VideoSource,
        requested_stages: tuple[JobStage, ...] = DEFAULT_PIPELINE_STAGES,
        target_language: str = "vi",
        credentials: ProviderCredentials | None = None,
        voice: Voice | None = None,
        options: dict | None = None,
    ) -> Job:
        JobWorkspace.cleanup_stale(
            self.workspace_base,
            ttl_seconds=self.workspace_ttl_seconds,
        )
        job_id = secrets.token_urlsafe(18)
        now = datetime.now(timezone.utc)
        job = Job(id=job_id, created_at=now, updated_at=now)
        workspace = JobWorkspace.create(self.workspace_base, job_id=job_id)
        self.repository.save(job)
        coordinator = (
            self.coordinator_factory(credentials)
            if self.coordinator_factory
            else self.coordinator
        )
        self._pending[job_id] = (
            source,
            workspace,
            requested_stages,
            target_language,
            coordinator,
            credentials,
            voice,
            dict(options or {}),
        )
        self._cancel_events[job_id] = asyncio.Event()
        return job

    def cleanup_stale_workspaces(self, *, now: float | None = None) -> int:
        """Remove abandoned job workspaces while preserving recent artifacts."""

        return JobWorkspace.cleanup_stale(
            self.workspace_base,
            ttl_seconds=self.workspace_ttl_seconds,
            now=now,
        )

    async def run(self, job_id: str) -> Job:
        pending = self._pending.get(job_id)
        if pending is None:
            raise KeyError(job_id)
        source, workspace, stages, target_language, coordinator, credentials, voice, options = pending
        try:
            result: PipelineResult = await coordinator.run(
                source,
                workspace,
                requested_stages=stages,
                target_language=target_language,
                credentials=credentials,
                voice=voice,
                options=options,
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
        finally:
            self._pending.pop(job_id, None)
            self._cancel_events.pop(job_id, None)

    def cancel(self, job_id: str) -> Job | None:
        event = self._cancel_events.get(job_id)
        if event:
            event.set()
        return self.repository.cancel(job_id)
