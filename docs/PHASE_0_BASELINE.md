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
- The legacy CLI still focuses on Douyin crawling/downloading, while the
  FastAPI backend now has a generic yt-dlp source adapter for public
  single-video analysis and acquisition. The Claude skill remains preserved
  as a separate orchestration path.
- A local Mac development server can be started with
  `./scripts/run_local_server.sh`; this does not require Cloud Run billing.
- The default API job now runs the complete local-first stage chain:
  acquire → extract audio → Faster Whisper `tiny` → local mock translation →
  deterministic SRT → local FFmpeg TTS fixture → FFmpeg merge. Real provider
  credentials remain request-scoped and opt-in.
- The Poetry script points to `main:cli`, while the CLI is in
  `backend/cli.py`; this needs correction before relying on the package
  entrypoint.
- No live Douyin/provider request was run in this baseline because it would
  require external access, cookies, or provider credentials.

## Phase 0 implementation evidence

The Phase 0 branch now contains the FastAPI service, normalized domain and
provider contracts, isolated job workspaces, stage-aware pipeline, Dockerfile,
and Cloud Run experiment template. The local suite has 63 passing tests; two
real-provider checks are opt-in and skipped by default.

Verified locally after the Phase 0 implementation:

- `backend/.venv/bin/python -m pytest -q`: 63 passed, 2 skipped, 1 known
  Starlette/httpx deprecation warning.
- `./scripts/check_phase0_local.sh`: repeatable local audit passed, including
  tests, compilation, diff check, Graft freshness, health, and OpenAPI smoke.
- A real `FasterWhisperProvider(model="tiny")` run completed against a
  0.5-second generated fixture without Claude orchestration or provider keys.
- The explicit `extracting_audio` artifact is now passed into the Whisper
  provider, avoiding the legacy transcript/index side effects for API jobs.
- Uvicorn smoke: `/health` returned 200 and `/openapi.json` exposed the six
  expected Phase 0 routes.
- Artifact reuse was exercised by rerunning the merge stage from contained
  existing source/audio artifacts.
- Default container verification passed with Podman rootful AppleHV: image
  digest `bed4643bbc5804ce8ad7a3e632c614726c4784e3331e5680d6d002322a62839f`,
  image size `1,131,101,602` bytes, `/health` HTTP 200, OpenAPI route smoke,
  and a job POST/GET smoke with secret-free response and logs.

Still pending before the Phase 0 gate:

- Run the opt-in Vbee integration check with owner-configured credentials.
- Deploy the Cloud Run experiment and record the benchmark; this requires the
  owner checkpoint for project, billing, APIs, and credentials.

Container runtime attempt:

- Podman 6.1.2 was installed successfully.
- The rootless AppleHV machine entered guest emergency mode at
  `ignition-files.service`; a rootful AppleHV retry booted briefly but exited
  before exposing a working Podman socket.
- Docker Desktop installation was also attempted, but Homebrew received a
  corrupt/truncated Docker archive. No image build result is claimed from
  these runtime failures.
- A crawler-enabled Chromium build previously reached the Playwright browser
  layer but exhausted host disk. The default non-Chromium image now builds and
  runs successfully; the temporary VM/container were removed after smoke.
- The Dockerfile now makes the optional Chromium download explicit through
  `INSTALL_PLAYWRIGHT_BROWSER=true`; the default API image keeps the Python
  Playwright seam without forcing the crawler browser layer.
