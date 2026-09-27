from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from backend.crawler import crawl_single_url
from server.app.domain.models import VideoSource
from server.app.security import ServiceError, validate_public_http_url

router = APIRouter(prefix="/v1/sources", tags=["sources"])


class AnalyzeSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class AnalyzeSourceResponse(BaseModel):
    source: VideoSource
    capabilities: list[str]


Crawler = Callable[..., Awaitable[dict[str, Any] | None]]


async def analyze_source(url: str, crawler: Crawler | None = None) -> AnalyzeSourceResponse:
    crawler = crawler or crawl_single_url
    validate_public_http_url(url)
    parsed = urlsplit(url)
    if parsed.hostname not in {"douyin.com", "www.douyin.com"}:
        raise ServiceError(
            stage="analyzing",
            error_code="unsupported_platform",
            user_message="Nguồn video này chưa được hỗ trợ trong Phase 0.",
        )

    result = await crawler(url=url, headless=True)
    if not result:
        raise ServiceError(
            stage="analyzing",
            error_code="source_not_found",
            user_message="Không lấy được thông tin video từ nguồn này.",
            retryable=True,
        )

    source_id = str(result.get("aweme_id")) if result.get("aweme_id") else None
    source = VideoSource(
        url=url,
        platform="douyin",
        source_id=source_id,
        title=result.get("title"),
        author=result.get("author"),
        metadata={
            "download_url": result.get("download_url"),
            "detail_url": f"https://www.douyin.com/video/{source_id}" if source_id else url,
        },
    )
    return AnalyzeSourceResponse(source=source, capabilities=["download", "transcribe"])


@router.post("/analyze", response_model=AnalyzeSourceResponse)
async def analyze(request: AnalyzeSourceRequest) -> AnalyzeSourceResponse:
    try:
        return await analyze_source(request.url)
    except ServiceError as error:
        raise HTTPException(status_code=400, detail=error.public_dict()) from error
