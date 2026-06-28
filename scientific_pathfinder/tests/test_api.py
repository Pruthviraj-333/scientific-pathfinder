from unittest.mock import patch
import pytest


def test_root_endpoint(test_client):
    """Test the root endpoint returns correct service details."""
    response = test_client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["service"] == "Scientific Pathfinder API"
    assert "version" in json_data["data"]


def test_health_live_endpoint(test_client):
    """Test the liveness check endpoint."""
    response = test_client.get("/api/v1/health/live")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "alive"


def test_health_ready_endpoint(test_client):
    """Test the readiness check endpoint."""
    response = test_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["ready"] is True


def test_health_status_endpoint(test_client):
    """Test the full health status check endpoint."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"
    assert "services" in json_data["data"]


def test_start_research_endpoint(test_client):
    """Test starting a research session successfully."""
    payload = {"topic": "Deep Learning", "max_papers": 5}
    response = test_client.post("/api/v1/research/start", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["success"] is True
    assert "session_id" in json_data["data"]
    assert json_data["data"]["status"] == "initiated"


def test_start_research_invalid_payload(test_client):
    """Test starting research with an invalid payload returns 422 error."""
    payload = {"topic": "", "max_papers": 5}  # Empty topic is invalid
    response = test_client.post("/api/v1/research/start", json=payload)
    assert response.status_code == 422


def test_get_nonexistent_research_status(test_client):
    """Test getting status of a session that does not exist."""
    response = test_client.get("/api/v1/research/nonexistent-id")
    assert response.status_code == 404
