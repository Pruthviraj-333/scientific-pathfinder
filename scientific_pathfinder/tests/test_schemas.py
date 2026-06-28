import pytest
from pydantic import ValidationError
from src.schemas import ResearchStartRequest


def test_research_start_request_valid():
    """Test that a valid ResearchStartRequest is accepted."""
    req = ResearchStartRequest(topic="Machine Learning", max_papers=10)
    assert req.topic == "Machine Learning"
    assert req.max_papers == 10


def test_research_start_request_validation():
    """Test validations for ResearchStartRequest."""
    # Empty topic
    with pytest.raises(ValidationError):
        ResearchStartRequest(topic="", max_papers=10)

    # Max papers too low
    with pytest.raises(ValidationError):
        ResearchStartRequest(topic="Test", max_papers=0)

    # Max papers too high
    with pytest.raises(ValidationError):
        ResearchStartRequest(topic="Test", max_papers=101)


def test_api_response_formatting():
    """Test APIResponse helper functions."""
    from src.schemas import success_response, error_response

    success = success_response(data={"key": "value"})
    assert success["success"] is True
    assert success["data"] == {"key": "value"}
    assert "timestamp" in success

    error = error_response(error="Test error")
    assert error["success"] is False
    assert error["error"] == "Test error"
    assert error["data"] is None
    assert "timestamp" in error
