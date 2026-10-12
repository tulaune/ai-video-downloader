import ipaddress
import socket
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
    addresses = [address] if address else []
    if not address:
        try:
            addresses = [
                ipaddress.ip_address(info[4][0])
                for info in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            ]
        except socket.gaierror as error:
            raise ServiceError(
                stage="analyzing",
                error_code="host_resolution_failed",
                user_message="Không thể xác minh nguồn video.",
                retryable=True,
            ) from error
    if any(
        item.is_private or item.is_loopback or item.is_link_local or item.is_reserved
        for item in addresses
    ):
        raise ServiceError(
            stage="analyzing",
            error_code="private_url_not_allowed",
            user_message="URL nội bộ không được phép.",
        )
    return value
