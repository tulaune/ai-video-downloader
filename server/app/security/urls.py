import ipaddress
from urllib.parse import urlsplit

from .errors import ServiceError

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}


def validate_public_http_url(value: str) -> str:
    """Validate a URL before any downloader/provider performs network I/O."""

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ServiceError(
            stage="analyzing",
            error_code="invalid_url",
            user_message="URL không hợp lệ hoặc không được hỗ trợ.",
        )
    if parsed.username or parsed.password:
        raise ServiceError(
            stage="analyzing",
            error_code="url_credentials_not_allowed",
            user_message="URL chứa thông tin đăng nhập không được hỗ trợ.",
        )

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTNAMES:
        raise ServiceError(
            stage="analyzing",
            error_code="private_url_not_allowed",
            user_message="URL nội bộ không được phép.",
        )
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ServiceError(
            stage="analyzing",
            error_code="private_url_not_allowed",
            user_message="URL nội bộ không được phép.",
        )
    return value
