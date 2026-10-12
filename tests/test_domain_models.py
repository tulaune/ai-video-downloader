from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from server.app.domain.models import (
    Artifact,
    ArtifactType,
    Job,
    JobStage,
    JobState,
    Segment,
    Transcript,
    VideoSource,
)


def test_transcript_preserves_normalized_segments():
    transcript = Transcript(
        language="zh",
        language_probability=0.98,
        text="你好",
        segments=[Segment(start=0, end=1.2, text="你好")],
    )

    assert transcript.segments[0].model_dump() == {"start": 0, "end": 1.2, "text": "你好"}


def test_video_source_rejects_non_http_url():
    with pytest.raises(ValidationError):
        VideoSource(url="file:///tmp/video.mp4")


def test_job_has_stable_state_and_stage_values():
    now = datetime.now(timezone.utc)
    job = Job(
        id="job-1",
        current_stage=JobStage.TRANSCRIBING,
        state=JobState.RUNNING,
        created_at=now,
        updated_at=now,
    )

    assert job.state.value == "running"
    assert job.current_stage.value == "transcribing"


def test_artifact_rejects_negative_size():
    with pytest.raises(ValidationError):
        Artifact(
            id="artifact-1",
            type=ArtifactType.SOURCE_VIDEO,
            reference="/tmp/source.mp4",
            size=-1,
            created_at=datetime.now(timezone.utc),
        )
