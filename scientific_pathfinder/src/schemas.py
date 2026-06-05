"""
Pydantic schemas for API request/response validation.

All API responses follow a consistent envelope format:
{
    "success": true/false,
    "data": { ... },
    "error": null or "error message",
    "timestamp": "ISO-8601"
}
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


# ── Response Envelope ───────────────────────────────────────────────────

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Research Schemas ────────────────────────────────────────────────────

class ResearchStartRequest(BaseModel):
    """Request body for starting a research session."""
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic to investigate")
    max_papers: int = Field(default=10, ge=5, le=50, description="Maximum papers to analyze")

    @field_validator("topic")
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        """Basic input sanitization."""
        return v.strip()


class ResearchStartResponse(BaseModel):
    """Response data for a newly created research session."""
    session_id: str
    status: str
    message: str


class ResearchSessionStatus(BaseModel):
    """Current status of a research session."""
    session_id: str
    topic: str
    max_papers: int
    status: str
    created_at: str
    result: Optional[Dict[str, Any]] = None


# ── Graph Schemas ───────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the knowledge graph visualization."""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphLink(BaseModel):
    """A relationship in the knowledge graph visualization."""
    source: str
    target: str
    type: str


class GraphData(BaseModel):
    """Graph data for D3.js visualization."""
    nodes: List[GraphNode]
    links: List[GraphLink]


class GraphClearResponse(BaseModel):
    """Response after clearing the graph database."""
    nodes_deleted: int
    relationships_deleted: int


# ── Health Check Schemas ────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    """Status of an individual service dependency."""
    status: str  # "connected", "configured", "missing", "error"
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Detailed health check response."""
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    services: Dict[str, ServiceStatus]


class MetricsResponse(BaseModel):
    """API metrics response."""
    uptime_seconds: float
    total_requests: int
    total_errors: int
    active_websockets: int
    active_sessions: int
    requests_by_endpoint: Dict[str, int]
    avg_response_time_ms: float


# ── Helper Functions ────────────────────────────────────────────────────

def success_response(data: Any = None, message: Optional[str] = None) -> dict:
    """Create a standardized success response."""
    response = APIResponse(success=True, data=data)
    return response.model_dump()


def error_response(error: str, data: Any = None) -> dict:
    """Create a standardized error response."""
    response = APIResponse(success=False, error=error, data=data)
    return response.model_dump()
