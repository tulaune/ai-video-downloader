import pytest

from server.app.domain.models import Segment, Transcript
from server.app.subtitle import format_srt_timestamp, generate_srt


def test_format_srt_timestamp_handles_rollover():
    assert format_srt_timestamp(3661.2346) == "01:01:01,235"


def test_generate_srt_preserves_unicode_and_skips_empty_segments():
    transcript = Transcript(
        language="vi",
        text="Xin chào",
        segments=[
            Segment(start=0, end=1.25, text="  Xin chào, thế giới!  "),
            Segment(start=1.5, end=2, text="   "),
            Segment(start=2, end=3, text="Dòng hai"),
        ],
    )

    assert generate_srt(transcript) == (
        "1\n00:00:00,000 --> 00:00:01,250\nXin chào, thế giới!\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\nDòng hai\n"
    )


def test_generate_srt_rejects_reversed_segment():
    transcript = Transcript(
        language="en",
        text="bad",
        segments=[Segment(start=2, end=1, text="bad")],
    )

    with pytest.raises(ValueError, match="before start"):
        generate_srt(transcript)
