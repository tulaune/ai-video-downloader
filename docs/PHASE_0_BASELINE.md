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
