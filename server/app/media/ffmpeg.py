import asyncio
import shutil
from pathlib import Path

from server.app.security import ServiceError

FFMPEG_TIMEOUT_SECONDS = 600


async def _run_ffmpeg(args: list[str], output_path: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        raise ServiceError(
            stage="media",
            error_code="ffmpeg_missing",
            user_message="Media processor chưa được cài đặt.",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=FFMPEG_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as error:
        process.kill()
        await process.wait()
        raise ServiceError(
            stage="media",
            error_code="ffmpeg_timeout",
            user_message="Xử lý media mất quá nhiều thời gian.",
            retryable=True,
        ) from error
    if process.returncode != 0:
        technical = stderr.decode(errors="replace")[-2_000:]
        raise ServiceError(
            stage="media",
            error_code="ffmpeg_failed",
            user_message="Không thể xử lý media.",
            technical_message=technical,
            retryable=True,
        )
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ServiceError(
            stage="media",
            error_code="media_output_missing",
            user_message="Media processor không tạo được file đầu ra.",
        )
    return output_path


async def extract_audio(video_path: str | Path, audio_path: str | Path) -> Path:
    source = Path(video_path)
    output = Path(audio_path)
    if not source.is_file():
        raise ServiceError(
            stage="extracting_audio",
            error_code="source_media_missing",
            user_message="Không tìm thấy video nguồn.",
        )
    return await _run_ffmpeg(
        ["-y", "-i", str(source), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(output)],
        output,
    )


async def merge_audio(
    video_path: str | Path,
    dubbed_audio_path: str | Path,
    output_path: str | Path,
    *,
    original_volume: float = 0.1,
    dubbed_volume: float = 1.0,
) -> Path:
    source = Path(video_path)
    dubbed = Path(dubbed_audio_path)
    output = Path(output_path)
    if not source.is_file() or not dubbed.is_file():
        raise ServiceError(
            stage="merging",
            error_code="merge_input_missing",
            user_message="Thiếu video hoặc audio để ghép.",
        )
    filter_graph = (
        f"[0:a]volume={original_volume}[orig];"
        f"[1:a]volume={dubbed_volume}[dub];"
        "[orig][dub]amix=inputs=2:normalize=0[mix]"
    )
    return await _run_ffmpeg(
        [
            "-y",
            "-i",
            str(source),
            "-i",
            str(dubbed),
            "-filter_complex",
            filter_graph,
            "-map",
            "0:v",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output),
        ],
        output,
    )
