import json
import socket

import pytest

from server.app.security import ProviderCredentials, ServiceError, redact_secrets, validate_public_http_url


def test_provider_credentials_are_masked_until_explicitly_read():
    credentials = ProviderCredentials(provider="vbee", fields={"token": "secret-token"})

    assert credentials.secret("token") == "secret-token"
    assert credentials.redacted() == {"token": "[REDACTED]"}
    assert "secret-token" not in repr(credentials)


def test_redact_secrets_handles_nested_payloads_without_mutating_input():
    payload = {"token": "secret", "nested": [{"api_key": "key", "value": 1}]}
    redacted = redact_secrets(payload)

    assert json.dumps(redacted) == '{"token": "[REDACTED]", "nested": [{"api_key": "[REDACTED]", "value": 1}]}'
    assert payload["token"] == "secret"


@pytest.mark.parametrize("url", ["file:///tmp/a.mp4", "ftp://example.com/a", "http://127.0.0.1:8000"])
def test_validate_public_http_url_rejects_unsafe_urls(url):
    with pytest.raises(ServiceError) as exc_info:
        validate_public_http_url(url)
    assert exc_info.value.error_code in {"invalid_url", "private_url_not_allowed"}


def test_validate_public_http_url_accepts_supported_public_url():
    assert validate_public_http_url("https://www.douyin.com/video/123") == "https://www.douyin.com/video/123"


def test_validate_public_http_url_rejects_hostname_resolving_private(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))],
    )

    with pytest.raises(ServiceError) as exc_info:
        validate_public_http_url("https://video.example.test/source")
    assert exc_info.value.error_code == "private_url_not_allowed"
