import os

from fastapi import FastAPI

from server.app.api.sources import router as sources_router
from server.app.api.jobs import router as jobs_router

SERVICE_VERSION = os.environ.get("VELINGO_VERSION", "0.1.0-dev")

app = FastAPI(
    title="Velingo API",
    version=SERVICE_VERSION,
    description="Backend foundation for Velingo media processing jobs.",
)
app.include_router(sources_router)
app.include_router(jobs_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "velingo-api",
        "version": SERVICE_VERSION,
    }
