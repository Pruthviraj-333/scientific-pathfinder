"""
Neo4j database lifecycle management.

Provides a singleton database connection with proper startup/shutdown
lifecycle integration with FastAPI.
"""

from typing import Optional
from src.graph_db import Neo4jGraphDB
from src.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages the Neo4j database connection lifecycle."""

    def __init__(self):
        self._db: Optional[Neo4jGraphDB] = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._db is not None

    def connect(self, uri: str, username: str, password: str) -> bool:
        if self._connected and self._db is not None:
            return True
        
        import time
        max_retries = 5
        retry_delay = 3.0
        
        for attempt in range(max_retries):
            try:
                self._db = Neo4jGraphDB(uri, username, password)
                if self._db.connect():
                    self._connected = True
                    logger.info("Database connection established")
                    return True
                self._db = None
            except Exception as e:
                logger.error(f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                self._db = None
                
            if attempt < max_retries - 1:
                logger.info(f"Retrying database connection in {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                
        return False

    def disconnect(self) -> None:
        if self._db is not None:
            try:
                self._db.close()
            except Exception as e:
                logger.warning(f"Error closing database: {e}")
            finally:
                self._db = None
                self._connected = False

    def get_db(self) -> Neo4jGraphDB:
        if not self.is_connected or self._db is None:
            raise RuntimeError("Database not connected")
        return self._db

    def health_check(self) -> dict:
        if not self.is_connected or self._db is None:
            return {"status": "disconnected"}
        try:
            with self._db.driver.session() as session:
                session.run("RETURN 1").consume()
            return {"status": "connected"}
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}


db_manager = DatabaseManager()

def get_db() -> Neo4jGraphDB:
    """FastAPI dependency for database access."""
    return db_manager.get_db()
