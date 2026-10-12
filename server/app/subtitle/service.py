from server.app.domain.models import Transcript


def format_srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("timestamp cannot be negative")
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def generate_srt(transcript: Transcript) -> str:
    entries: list[str] = []
    sequence = 1
    for segment in transcript.segments:
        text = segment.text.strip()
        if not text:
            continue
        if segment.end < segment.start:
            raise ValueError("segment end cannot be before start")
        entries.append(
            "\n".join([
                str(sequence),
                f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                text,
            ])
        )
        sequence += 1
    return "\n\n".join(entries) + ("\n" if entries else "")
