import os

from fastapi import FastAPI


SERVICE_VERSION = os.environ.get("VELINGO_VERSION", "0.1.0-dev")

app = FastAPI(
    title="Velingo API",
    version=SERVICE_VERSION,
    description="Backend foundation for Velingo media processing jobs.",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "velingo-api",
        "version": SERVICE_VERSION,
    }
