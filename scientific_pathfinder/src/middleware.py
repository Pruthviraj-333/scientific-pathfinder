"""
FastAPI middleware for security, rate limiting, and request tracking.
"""

import time
import uuid
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Request ID Middleware ───────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request for log correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── Security Headers Middleware ─────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


# ── Rate Limiting Middleware ────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding window rate limiter.

    NOTE: This is per-process. For multi-process deployments,
    use Redis-based rate limiting instead.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from IP or forwarded header."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, client_id: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > cutoff
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and WebSocket upgrades
        if request.url.path.startswith("/api/v1/health") or request.url.path.startswith("/ws"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        now = time.time()

        self._cleanup_old_requests(client_id, now)

        if len(self._requests[client_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "data": None,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._requests[client_id].append(now)

        response = await call_next(request)
        remaining = self.max_requests - len(self._requests[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response


# ── Request Logging Middleware ──────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs all incoming requests with timing information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Store timing for metrics
        request.state.start_time = start_time

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        request_id = getattr(request.state, "request_id", "-")

        # Skip logging for health checks in production
        if not request.url.path.startswith("/api/v1/health"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)",
                extra={"request_id": request_id},
            )

        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response


# ── API Key Authentication ──────────────────────────────────────────────

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Optional API key authentication middleware.

    Skips authentication for:
    - Health check endpoints
    - WebSocket connections (auth handled separately)
    - Root endpoint
    - OPTIONS requests (CORS preflight)
    """

    def __init__(self, app, api_key: str, header_name: str = "X-API-Key"):
        super().__init__(app)
        self.api_key = api_key
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for certain paths
        skip_paths = ["/", "/api/v1/health", "/docs", "/openapi.json", "/redoc"]
        if (
            request.method == "OPTIONS"
            or request.url.path in skip_paths
            or request.url.path.startswith("/api/v1/health/")
            or request.url.path.startswith("/ws")
        ):
            return await call_next(request)

        # Check API key
        provided_key = request.headers.get(self.header_name)
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "Invalid or missing API key",
                    "data": None,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )

        return await call_next(request)
