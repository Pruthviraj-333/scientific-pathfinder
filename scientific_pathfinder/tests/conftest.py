"""
Shared test fixtures for the Scientific Pathfinder test suite.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "development"
os.environ["GROQ_API_KEY"] = "test_groq_key"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword"


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings singleton between tests."""
    from config import reset_settings
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def mock_neo4j_db():
    """Create a mock Neo4j database client."""
    mock_db = MagicMock()
    mock_db.connect.return_value = True
    mock_db.close.return_value = None
    mock_db.create_schema.return_value = None
    mock_db.get_graph_stats.return_value = {
        "paper_count": 5,
        "author_count": 10,
        "method_count": 3,
        "dataset_count": 2,
        "metric_count": 4,
        "relationship_count": 20,
    }
    mock_db.find_isolated_nodes.return_value = []
    mock_db.find_rare_combinations.return_value = []

    # Mock the driver session context manager
    mock_session = MagicMock()
    mock_db.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=False)

    return mock_db


@pytest.fixture
def test_client(mock_neo4j_db):
    """Create a FastAPI test client with mocked dependencies."""
    from config import reset_settings
    reset_settings()

    with patch("src.database.db_manager") as mock_db_manager:
        mock_db_manager.is_connected = True
        mock_db_manager.get_db.return_value = mock_neo4j_db
        mock_db_manager.health_check.return_value = {"status": "connected"}
        mock_db_manager.connect.return_value = True

        from fastapi.testclient import TestClient
        from api import app
        client = TestClient(app)
        yield client
