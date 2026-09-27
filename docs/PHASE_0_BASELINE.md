# Phase 0 Baseline

> Source commit: `4237af33893b6a426d6e0c4b3cc37508aadbf4ec`
>
> Branch: `feat/mobile-backend-phase0`

## Local runtime

- Python: `3.11.16`
- Virtual environment: `backend/.venv`
- FFmpeg: `9.0.2`
- yt-dlp: `2026.08.19`
- Playwright Chromium: installed and headless launch verified

## Reproducible checks

These checks pass locally:

```bash
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -c 'import backend, dotenv, httpx'
backend/.venv/bin/python -m backend --help
backend/.venv/bin/python -m compileall -q backend
backend/.venv/bin/playwright install chromium
```

The CLI exposes these current commands:

```text
python -m backend dl URL
python -m backend jingxuan
python -m backend user URL
python -m backend transcribe VIDEO_PATH
```

## Controlled media fixture

A two-second synthetic MP4 was generated at
`/tmp/velingo-phase0-fixture.mp4` for local media checks. It contains:

- H.264 video at 320x180
- AAC audio at 16 kHz
- Duration: 2 seconds
- Size: 72,189 bytes

The fixture is intentionally not an AI end-to-end proof. Whisper model
quality, provider credentials, translation, TTS, and a real supported
source remain separate Phase 0 tasks.

## Findings captured for migration

- The current Python package imports successfully only after declaring
  `httpx` and `python-dotenv`.
- Translation, SRT generation, and final FFmpeg composition still live in
  `.claude/skills/voice-over/SKILL.md` rather than reusable Python services.
- Generic URL download is implemented by the Claude skill through yt-dlp;
  the Python backend currently focuses on Douyin crawling/downloading.
- The Poetry script points to `main:cli`, while the CLI is in
  `backend/cli.py`; this needs correction before relying on the package
  entrypoint.
- No live Douyin/provider request was run in this baseline because it would
  require external access, cookies, or provider credentials.

## Phase 0 implementation evidence

The Phase 0 branch now contains the FastAPI service, normalized domain and
provider contracts, isolated job workspaces, stage-aware pipeline, Dockerfile,
and Cloud Run experiment template. The local suite has 57 passing tests; two
real-provider checks are opt-in and skipped by default.

Verified locally after the Phase 0 implementation:

- `backend/.venv/bin/python -m pytest -q`: 57 passed, 2 skipped, 1 known
  Starlette/httpx deprecation warning.
- A real `FasterWhisperProvider(model="tiny")` run completed against a
  0.5-second generated fixture without Claude orchestration or provider keys.
- Uvicorn smoke: `/health` returned 200 and `/openapi.json` exposed the six
  expected Phase 0 routes.
- Artifact reuse was exercised by rerunning the merge stage from contained
  existing source/audio artifacts.

Still pending before the Phase 0 gate:

- Run the opt-in Vbee integration check with owner-configured credentials.
- Build and run the Docker image; Docker/Podman is not installed on the local
  host used for this audit.
- Deploy the Cloud Run experiment and record the benchmark; this requires the
  owner checkpoint for project, billing, APIs, and credentials.
