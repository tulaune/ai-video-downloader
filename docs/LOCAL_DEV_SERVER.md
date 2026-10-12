# Local Mac development server

The FastAPI backend can run on the owner's Mac before any Cloud Run billing
is available. This is a development/demo server, not a production deployment.

## Start

From the repository root:

```bash
./scripts/run_local_server.sh
```

For a repeatable agent/local verification pass, run:

```bash
./scripts/check_phase0_local.sh
```

This runs the test suite, Python compilation, `git diff --check`, Graft
freshness, and a loopback health/OpenAPI smoke. It does not claim a real phone,
provider credential, or Cloud Run result.

The default bind is `0.0.0.0:8080`, so the server is reachable from another
device on the same trusted LAN. A local-only run can use:

```bash
VELINGO_HOST=127.0.0.1 ./scripts/run_local_server.sh
```

Check it from the Mac:

```bash
curl http://127.0.0.1:8080/health
```

For a phone test, find the Mac's LAN address (for example with
`ipconfig getifaddr en0`) and configure the mobile development build to use
`http://MAC_LAN_IP:8080`. Both devices must remain on the same Wi-Fi network,
and macOS Firewall must allow the Python process to accept connections.

## Mobile API base URL contract

The mobile development build should configure one replaceable base URL:

```text
http://MAC_LAN_IP:8080
```

The initial Phase 0 contract is:

| Operation | Method | Path |
| --- | --- | --- |
| Health | GET | `/health` |
| Analyze public source | POST | `/v1/sources/analyze` |
| Create job | POST | `/v1/jobs` |
| Poll job | GET | `/v1/jobs/{job_id}` |
| Cancel job | POST | `/v1/jobs/{job_id}/cancel` |
| List artifacts | GET | `/v1/jobs/{job_id}/artifacts` |

The mobile client must treat the base URL as development configuration, not
hard-code the Mac's address into production code. A future remotely deployed
server can replace the base URL and use HTTPS without changing these paths.

## Request and response contract

Analyze:

```http
POST /v1/sources/analyze
Content-Type: application/json

{"url":"https://www.youtube.com/watch?v=PERMITTED_PUBLIC_VIDEO"}
```

The response contains `source` (`url`, `platform`, optional `source_id`,
title/author/duration) and `capabilities`. The server only accepts the
configured public-platform host allowlist; it does not fetch arbitrary LAN or
private URLs.

Create a full local-first job without provider credentials:

```http
POST /v1/jobs
Content-Type: application/json

{
  "source": {"url":"https://www.youtube.com/watch?v=PERMITTED_PUBLIC_VIDEO", "platform":"youtube"},
  "target_language":"vi"
}
```

Without `credentials`, Phase 0 uses `faster-whisper` model `tiny`, the
deterministic local translation seam, and a local FFmpeg-generated TTS fixture.
With request-scoped provider credentials, the configured real provider path is
used; credentials are never returned in job responses or artifact responses.

Poll `GET /v1/jobs/{job_id}` until `state` is `completed`, `failed`, or
`cancelled`. `progress` is a number from `0` to `1`; `current_stage` is one of:

```text
acquiring, extracting_audio, transcribing, translating,
generating_subtitle, generating_tts, merging, finalizing
```

Public errors have `stage`, `error_code`, `user_message`, and `retryable`.
Retry only when `retryable` is true; never use `technical_message` because it
is intentionally not part of the public response. `GET /v1/jobs/{job_id}/artifacts`
returns artifact `id`, `type`, MIME type, byte size, and expiry metadata —
never a local filesystem path.

The Mac must stay awake while a job runs. Phase 0 generic acquisition is
limited to an explicit public-platform host allowlist; it does not accept
arbitrary direct HTTP URLs. Do not expose this development server directly
to the public internet or place production credentials in its environment.
A tunnel, if needed for a temporary demo, is a separate authenticated setup
and is not part of the Phase 0 default.

## Mac LAN checklist

- Start with `./scripts/run_local_server.sh` and keep the Mac awake.
- Find the address with `ipconfig getifaddr en0` (or the active interface).
- Put the phone and Mac on the same trusted Wi-Fi network.
- Allow incoming connections for Python/Uvicorn in macOS Firewall.
- Use plain HTTP only for local development; do not expose this server to the
  public Internet and do not put production credentials in its environment.
