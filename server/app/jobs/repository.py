from server.app.domain.models import Job, JobState


class JobRepository:
    """Small in-memory Phase 0 repository; replaceable before public scale."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def save(self, job: Job) -> Job:
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job: Job) -> Job:
        if job.id not in self._jobs:
            raise KeyError(job.id)
        self._jobs[job.id] = job
        return job

    def cancel(self, job_id: str) -> Job | None:
        job = self._jobs.get(job_id)
        if job is None or job.state in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            return job
        cancelled = job.model_copy(update={"state": JobState.CANCELLED})
        self._jobs[job_id] = cancelled
        return cancelled
