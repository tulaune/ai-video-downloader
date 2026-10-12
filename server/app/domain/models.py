from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Segment(_StrictModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str


class VideoSource(_StrictModel):
    url: HttpUrl
    platform: str | None = None
    source_id: str | None = None
    title: str | None = None
    author: str | None = None
    duration: float | None = Field(default=None, ge=0)
    thumbnail_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Transcript(_StrictModel):
    language: str
    language_probability: float | None = Field(default=None, ge=0, le=1)
    text: str
    segments: list[Segment] = Field(default_factory=list)


class Voice(_StrictModel):
    provider: str
    voice_id: str
    display_name: str
    language: str | None = None
    region: str | None = None
    gender: str | None = None
    age_group: str | None = None
    category: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactType(str, Enum):
    SOURCE_VIDEO = "source_video"
    SOURCE_AUDIO = "source_audio"
    SOURCE_TRANSCRIPT = "source_transcript"
    TRANSLATED_TRANSCRIPT = "translated_transcript"
    SUBTITLE = "subtitle"
    DUBBED_AUDIO = "dubbed_audio"
    FINAL_VIDEO = "final_video"
    METADATA = "metadata"


class Artifact(_StrictModel):
    id: str
    type: ArtifactType
    reference: str
    mime_type: str | None = None
    size: int | None = Field(default=None, ge=0)
    created_at: datetime
    expires_at: datetime | None = None


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    ANALYZING = "analyzing"
    ACQUIRING = "acquiring"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    GENERATING_SUBTITLE = "generating_subtitle"
    GENERATING_TTS = "generating_tts"
    MERGING = "merging"
    FINALIZING = "finalizing"


class Job(_StrictModel):
    id: str
    state: JobState = JobState.QUEUED
    current_stage: JobStage | None = None
    progress: float = Field(default=0, ge=0, le=1)
    created_at: datetime
    updated_at: datetime
    error: dict[str, Any] | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
