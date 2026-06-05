"""
Application configuration using Pydantic BaseSettings.

Validates all environment variables at startup and fails fast
with clear error messages if required values are missing.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Server ──────────────────────────────────────────────────────────
    APP_NAME: str = "Scientific Pathfinder API"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    HOST: str = Field(default="0.0.0.0", description="Server bind host")
    PORT: int = Field(default=8000, description="Server bind port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="text", description="text | json")

    # ── CORS ────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed origins"
    )

    # ── Neo4j ───────────────────────────────────────────────────────────
    NEO4J_URI: str = Field(default="", description="Neo4j connection URI")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="", description="Neo4j password")

    # ── Groq LLM ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(default="", description="Groq API key for LLM inference")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq model name")

    # ── Semantic Scholar ────────────────────────────────────────────────
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = Field(
        default=None, description="Optional Semantic Scholar API key for higher rate limits"
    )

    # ── Security ────────────────────────────────────────────────────────
    API_KEY: Optional[str] = Field(
        default=None, description="Optional API key for endpoint protection (None = auth disabled)"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", description="Header name for API key")
    RATE_LIMIT_REQUESTS: int = Field(default=60, description="Max requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def auth_enabled(self) -> bool:
        return self.API_KEY is not None and len(self.API_KEY) > 0

    def validate_required_services(self) -> dict:
        """
        Check that required external service credentials are configured.
        Returns a dict of service -> status.
        """
        issues = {}

        if not self.GROQ_API_KEY:
            issues["groq"] = "GROQ_API_KEY is not set"

        if not self.NEO4J_URI:
            issues["neo4j_uri"] = "NEO4J_URI is not set"

        if not self.NEO4J_PASSWORD:
            issues["neo4j_password"] = "NEO4J_PASSWORD is not set"

        return issues

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# ── Singleton ───────────────────────────────────────────────────────────
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        # Try loading .env from the backend directory
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            os.environ.setdefault("ENV_FILE", str(env_path))
        _settings = Settings(_env_file=str(env_path) if env_path.exists() else None)
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing)."""
    global _settings
    _settings = None
