FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    JOB_WORKSPACE_BASE=/tmp/jobs

WORKDIR /app

ARG INSTALL_PLAYWRIGHT_BROWSER=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt \
    && if [ "$INSTALL_PLAYWRIGHT_BROWSER" = "true" ]; then \
         playwright install --with-deps chromium; \
       fi

COPY backend /app/backend
COPY server /app/server
COPY voice /app/voice

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/jobs \
    && chown -R appuser:appuser /app /tmp/jobs

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health')"

CMD ["sh", "-c", "exec uvicorn server.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
