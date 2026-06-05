"""
Custom exception hierarchy for the Scientific Pathfinder.

Provides structured, user-friendly error responses while keeping
internal error details out of API responses.
"""

from typing import Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        detail: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail  # Internal detail, not exposed to client
        super().__init__(self.message)


class ConfigurationError(AppException):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str = "Service configuration error", detail: Optional[str] = None):
        super().__init__(message=message, status_code=503, detail=detail)


class DatabaseError(AppException):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database operation failed", detail: Optional[str] = None):
        super().__init__(message=message, status_code=503, detail=detail)


class ExternalServiceError(AppException):
    """Raised when an external API call fails (Groq, Semantic Scholar)."""

    def __init__(self, service: str = "external", message: Optional[str] = None, detail: Optional[str] = None):
        msg = message or f"{service} service is unavailable"
        super().__init__(message=msg, status_code=502, detail=detail)


class SessionNotFoundError(AppException):
    """Raised when a research session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Research session '{session_id}' not found",
            status_code=404,
        )


class RateLimitExceededError(AppException):
    """Raised when request rate limit is exceeded."""

    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
        )


class AuthenticationError(AppException):
    """Raised when API key authentication fails."""

    def __init__(self):
        super().__init__(
            message="Invalid or missing API key",
            status_code=401,
        )


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message=message, status_code=422)
