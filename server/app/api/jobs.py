from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from server.app.domain.models import Artifact, Job, JobStage, JobState, VideoSource
from server.app.jobs.manager import JobManager
from server.app.pipeline import DEFAULT_PIPELINE_STAGES, PipelineCoordinator

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])
job_manager = JobManager(PipelineCoordinator({}))


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: VideoSource
    requested_stages: list[JobStage] = Field(default_factory=lambda: list(DEFAULT_PIPELINE_STAGES))
    target_language: str = "vi"


class ArtifactSummary(BaseModel):
    id: str
    type: str
    mime_type: str | None = None
    size: int | None = None
    created_at: datetime
    expires_at: datetime | None = None


class JobSummary(BaseModel):
    id: str
    state: JobState
    current_stage: JobStage | None
    progress: float
    created_at: datetime
    updated_at: datetime
    error: dict[str, Any] | None
    artifacts: list[ArtifactSummary]


def _artifact_summary(artifact: Artifact) -> ArtifactSummary:
    return ArtifactSummary(
        id=artifact.id,
        type=artifact.type.value,
        mime_type=artifact.mime_type,
        size=artifact.size,
        created_at=artifact.created_at,
        expires_at=artifact.expires_at,
    )


def _summary(job: Job) -> JobSummary:
    return JobSummary(
        id=job.id,
        state=job.state,
        current_stage=job.current_stage,
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
        artifacts=[_artifact_summary(artifact) for artifact in job.artifacts],
    )


@router.post("", response_model=JobSummary, status_code=202)
async def create_job(request: CreateJobRequest, background_tasks: BackgroundTasks) -> JobSummary:
    job = job_manager.enqueue(
        request.source,
        tuple(request.requested_stages),
        request.target_language,
    )
    background_tasks.add_task(job_manager.run, job.id)
    return _summary(job)


@router.get("/{job_id}", response_model=JobSummary)
async def get_job(job_id: str) -> JobSummary:
    job = job_manager.repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return _summary(job)


@router.post("/{job_id}/cancel", response_model=JobSummary)
async def cancel_job(job_id: str) -> JobSummary:
    job = job_manager.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return _summary(job)


@router.get("/{job_id}/artifacts", response_model=list[ArtifactSummary])
async def get_artifacts(job_id: str) -> list[ArtifactSummary]:
    job = job_manager.repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return [_artifact_summary(artifact) for artifact in job.artifacts]
