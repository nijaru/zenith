"""
HTTP utilities for Zenith framework.

Provides HTTP client management with connection pooling.
"""

from .client import (
    HTTPClientMixin,
    close_client,
    get_client,
    http_client,
    init_client,
)

__all__ = [
    "HTTPClientMixin",
    "close_client",
    "get_client",
    "http_client",
    "init_client",
]
