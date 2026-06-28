import pytest
from pydantic import ValidationError
from config import Settings


def test_default_settings():
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert settings.APP_NAME == "Scientific Pathfinder API"
    assert settings.APP_VERSION == "2.0.0"
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000
    assert settings.LOG_LEVEL in ["INFO", "DEBUG"]
    assert settings.LOG_FORMAT in ["text", "json"]


def test_invalid_environment():
    """Test that validation fails for an invalid environment name."""
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="invalid_env")


def test_invalid_log_level():
    """Test that validation fails for an invalid log level."""
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="INVALID_LEVEL")


def test_cors_origins_parsing():
    """Test that CORS_ORIGINS string is correctly parsed into a list."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000, http://localhost:5173 ")
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_required_services_validation():
    """Test required services validator detects missing credentials."""
    # All set
    settings = Settings(
        GROQ_API_KEY="test_key",
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_PASSWORD="password",
    )
    assert len(settings.validate_required_services()) == 0

    # Missing all
    empty_settings = Settings(
        GROQ_API_KEY="",
        NEO4J_URI="",
        NEO4J_PASSWORD="",
    )
    issues = empty_settings.validate_required_services()
    assert "groq" in issues
    assert "neo4j_uri" in issues
    assert "neo4j_password" in issues
