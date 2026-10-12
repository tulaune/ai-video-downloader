from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr


class ProviderCredentials(BaseModel):
    """Request-scoped credentials; never attach this model to a Job."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    fields: dict[str, SecretStr]

    def secret(self, name: str) -> str:
        value = self.fields.get(name)
        if value is None:
            raise KeyError(name)
        return value.get_secret_value()

    def redacted(self) -> dict[str, str]:
        return {name: "[REDACTED]" for name in self.fields}


def redact_secrets(value: Any, sensitive_keys: set[str] | None = None) -> Any:
    """Return a log-safe copy of nested mappings/lists without mutating input."""

    keys = sensitive_keys or {
        "api_key",
        "app_id",
        "authorization",
        "password",
        "secret",
        "token",
    }
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in keys else redact_secrets(item, keys)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item, keys) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item, keys) for item in value)
    return value
