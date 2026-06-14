"""Middleware — rate limiting and request size protection."""
from __future__ import annotations
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jose import jwt, JWTError

from config import (
    JWT_SECRET, JWT_ALGORITHM,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SEC,
    MAX_UPLOAD_SIZE_BYTES,
)

logger = logging.getLogger(__name__)

# ── Rate Limiter ──────────────────────────────────────────────────


def _rate_key_func(request: Request) -> str:
    """Extract user identity for per-user rate limiting.

    Priority: JWT user_id → client IP.
    This ensures authenticated users are tracked individually while
    unauthenticated clients fall back to IP-based limiting.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            pass  # fall through to IP-based key
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_rate_key_func,
    default_limits=[f"{RATE_LIMIT_REQUESTS}/minute"],
    storage_uri="memory://",
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for 429 Too Many Requests."""
    logger.warning(
        "Rate limit exceeded — key=%s path=%s",
        _rate_key_func(request),
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "请求过于频繁，请稍后重试。",
            "detail": f"限制: {RATE_LIMIT_REQUESTS} 次 / {RATE_LIMIT_WINDOW_SEC} 秒",
        },
    )


# ── Request Body Size Limiter ─────────────────────────────────────


class MaxBodySizeMiddleware:
    """ASGI middleware that rejects requests exceeding MAX_UPLOAD_SIZE_BYTES.

    Checks Content-Length header before reading the body. If Content-Length
    is absent, falls through (FastAPI will enforce via UploadFile internally).
    """

    def __init__(self, app, max_size: int = MAX_UPLOAD_SIZE_BYTES):
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check Content-Length header
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"content-length":
                try:
                    content_length = int(header_value.decode())
                    if content_length > self.max_size:
                        logger.warning(
                            "Request body too large — %d bytes (limit: %d) path=%s",
                            content_length,
                            self.max_size,
                            scope.get("path", ""),
                        )
                        response = JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={
                                "error": "请求体过大。",
                                "detail": f"最大允许: {self.max_size // (1024 * 1024)} MB",
                            },
                        )
                        await response(scope, receive, send)
                        return
                except ValueError:
                    pass
                break  # only one content-length header

        await self.app(scope, receive, send)
