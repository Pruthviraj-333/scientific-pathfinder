"""
Scientific Pathfinder — Production FastAPI Backend.

Provides REST API and WebSocket endpoints for the research agent frontend.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from src.logging_config import setup_logging, get_logger
from src.database import db_manager
from src.schemas import (
    APIResponse, ResearchStartRequest, ResearchStartResponse,
    GraphData, GraphNode, GraphLink, GraphClearResponse,
    HealthCheckResponse, ServiceStatus,
    success_response, error_response,
)
from src.exceptions import (
    AppException, ConfigurationError, DatabaseError,
    SessionNotFoundError, ExternalServiceError,
)
from src.middleware import (
    RequestIDMiddleware, SecurityHeadersMiddleware,
    RateLimitMiddleware, RequestLoggingMiddleware, APIKeyMiddleware,
)
from src.metrics import metrics
from src.agents import LibrarianAgent, CartographerAgent, ScientistAgent
from src.state import GraphState
from langgraph.graph import StateGraph, END

# ── Application Lifecycle ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    settings = get_settings()

    # Startup
    setup_logging(level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger = get_logger(__name__)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Validate required services
    issues = settings.validate_required_services()
    if issues:
        for svc, msg in issues.items():
            logger.warning(f"Service config issue: {msg}")

    # Connect to Neo4j
    if settings.NEO4J_URI and settings.NEO4J_PASSWORD:
        connected = db_manager.connect(
            settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD
        )
        if not connected:
            logger.warning("Neo4j connection failed — some features will be unavailable")
    else:
        logger.warning("Neo4j credentials not configured")

    if settings.auth_enabled:
        logger.info("API key authentication is ENABLED")
    else:
        logger.info("API key authentication is DISABLED")

    logger.info(f"Server ready on {settings.HOST}:{settings.PORT}")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down...")
    db_manager.disconnect()
    logger.info("Shutdown complete")


# ── FastAPI App ─────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Scientific Pathfinder API",
    description="AI-powered research gap discovery system",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── Middleware Stack (order matters — last added = first executed) ──────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
)
app.add_middleware(RequestIDMiddleware)

# Optional API key authentication
if settings.auth_enabled:
    app.add_middleware(
        APIKeyMiddleware,
        api_key=settings.API_KEY,
        header_name=settings.API_KEY_HEADER,
    )


# ── Global Exception Handler ───────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger = get_logger(__name__)
    if exc.detail:
        logger.error(f"AppException: {exc.message} | Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger = get_logger(__name__)
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=error_response("An internal server error occurred"),
    )


# ── In-Memory Session Storage ──────────────────────────────────────────

active_sessions: Dict[str, Dict[str, Any]] = {}


# ── WebSocket Connection Manager ───────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        metrics.active_websockets += 1

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            metrics.active_websockets = max(0, metrics.active_websockets - 1)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception:
                pass  # Client disconnected

manager = ConnectionManager()


# ════════════════════════════════════════════════════════════════════════
#  API ROUTES — v1
# ════════════════════════════════════════════════════════════════════════

# ── Root ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint — basic service info."""
    return success_response({
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.is_development else None,
    })


# ── Health Checks ──────────────────────────────────────────────────────

@app.get("/api/v1/health")
async def health_check():
    """Comprehensive health check with dependency status."""
    logger = get_logger(__name__)
    services = {}

    # Neo4j
    db_health = db_manager.health_check()
    services["neo4j"] = ServiceStatus(status=db_health["status"],
        message=db_health.get("message"))

    # Groq
    groq_status = "configured" if settings.GROQ_API_KEY else "missing"
    services["groq"] = ServiceStatus(status=groq_status)

    # Semantic Scholar
    s2_status = "configured" if settings.SEMANTIC_SCHOLAR_API_KEY else "public_limits"
    services["semantic_scholar"] = ServiceStatus(status=s2_status)

    overall = "healthy"
    if services["neo4j"].status != "connected":
        overall = "degraded"
    if services["groq"].status == "missing":
        overall = "unhealthy"

    health = HealthCheckResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services={k: v.model_dump() for k, v in services.items()},
    )
    status_code = 200 if overall != "unhealthy" else 503
    return JSONResponse(
        status_code=status_code,
        content=success_response(health.model_dump()),
    )


@app.get("/api/v1/health/live")
async def liveness():
    """Liveness probe — is the process alive?"""
    return success_response({"status": "alive"})


@app.get("/api/v1/health/ready")
async def readiness():
    """Readiness probe — can the service handle requests?"""
    db_health = db_manager.health_check()
    ready = db_health["status"] == "connected" and bool(settings.GROQ_API_KEY)
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content=success_response({"ready": ready, "neo4j": db_health["status"]}),
    )


# ── Metrics ─────────────────────────────────────────────────────────────

@app.get("/api/v1/metrics")
async def get_metrics():
    """API metrics endpoint."""
    metrics.active_sessions = len(active_sessions)
    return success_response(metrics.to_dict())


# ── Research ────────────────────────────────────────────────────────────

@app.post("/api/v1/research/start", status_code=201)
async def start_research(request: ResearchStartRequest):
    """Start a new research analysis session."""
    logger = get_logger(__name__)
    session_id = str(uuid.uuid4())

    # Auto-clear Neo4j before new research
    if db_manager.is_connected:
        try:
            db = db_manager.get_db()
            with db.driver.session() as neo4j_session:
                result = neo4j_session.run("MATCH (n) DETACH DELETE n")
                summary = result.consume()
            logger.info(
                f"Database cleared: {summary.counters.nodes_deleted} nodes, "
                f"{summary.counters.relationships_deleted} rels deleted"
            )
        except Exception as e:
            logger.warning(f"Auto-clear failed (non-fatal): {e}")

    active_sessions[session_id] = {
        "topic": request.topic,
        "max_papers": request.max_papers,
        "status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Session {session_id[:8]} created for: {request.topic}")

    return success_response(
        ResearchStartResponse(
            session_id=session_id,
            status="initiated",
            message=f"Connect to /ws/{session_id} for real-time updates",
        ).model_dump()
    )


@app.get("/api/v1/research/{session_id}")
async def get_research_status(session_id: str):
    """Get the current status of a research session."""
    if session_id not in active_sessions:
        raise SessionNotFoundError(session_id)
    return success_response(active_sessions[session_id])


# ── Graph ───────────────────────────────────────────────────────────────

@app.post("/api/v1/graph/clear")
async def clear_graph():
    """Clear all data from the Neo4j database."""
    if not db_manager.is_connected:
        raise DatabaseError("Neo4j is not connected")

    db = db_manager.get_db()
    try:
        with db.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n")
            summary = result.consume()
        return success_response(
            GraphClearResponse(
                nodes_deleted=summary.counters.nodes_deleted,
                relationships_deleted=summary.counters.relationships_deleted,
            ).model_dump()
        )
    except Exception as e:
        raise DatabaseError(detail=str(e))


@app.get("/api/v1/graph/{session_id}")
async def get_graph_visualization(session_id: str):
    """Get graph data for D3.js visualization."""
    if not db_manager.is_connected:
        raise DatabaseError("Neo4j is not connected")

    db = db_manager.get_db()
    try:
        with db.driver.session() as neo4j_session:
            nodes_result = neo4j_session.run("""
                MATCH (n) WHERE n:Paper OR n:Method OR n:Dataset OR n:Metric
                WITH n, id(n) as node_id
                RETURN node_id as id, labels(n)[0] as type,
                       COALESCE(n.title, n.name, 'Unknown') as label,
                       properties(n) as properties
                LIMIT 100
            """)
            nodes = []
            node_ids = set()
            for record in nodes_result:
                nid = str(record["id"])
                node_ids.add(nid)
                label = record["label"]
                if len(label) > 40:
                    label = label[:37] + "..."
                nodes.append(GraphNode(
                    id=nid, label=label,
                    type=record["type"].lower() if record["type"] else "unknown",
                    properties=dict(record["properties"]) if record["properties"] else {},
                ).model_dump())

            links_result = neo4j_session.run("""
                MATCH (a)-[r]->(b)
                WHERE (a:Paper OR a:Method OR a:Dataset OR a:Metric)
                  AND (b:Paper OR b:Method OR b:Dataset OR b:Metric)
                RETURN id(a) as source, id(b) as target, type(r) as type
                LIMIT 200
            """)
            links = []
            for record in links_result:
                src, tgt = str(record["source"]), str(record["target"])
                if src in node_ids and tgt in node_ids:
                    links.append(GraphLink(
                        source=src, target=tgt, type=record["type"]
                    ).model_dump())

        return success_response({"nodes": nodes, "links": links})
    except Exception as e:
        raise DatabaseError(detail=str(e))


@app.get("/api/v1/graph/data")
async def get_graph_data():
    """Get all graph data (session-independent)."""
    if not db_manager.is_connected:
        raise DatabaseError("Neo4j is not connected")

    db = db_manager.get_db()
    try:
        with db.driver.session() as sdb:
            nr = sdb.run("""
                MATCH (n) WHERE n:Paper OR n:Method OR n:Dataset OR n:Metric
                RETURN id(n) as id, labels(n)[0] as type,
                       COALESCE(n.title, n.name) as label,
                       properties(n) as properties LIMIT 100
            """)
            nodes = []
            for r in nr:
                lbl = r["label"]
                if lbl and len(lbl) > 50:
                    lbl = lbl[:47] + "..."
                nodes.append({"id": str(r["id"]), "label": lbl,
                    "type": r["type"].lower(), "properties": dict(r["properties"])})

            lr = sdb.run("""
                MATCH (a)-[r]->(b)
                WHERE (a:Paper OR a:Method OR a:Dataset OR a:Metric)
                  AND (b:Paper OR b:Method OR b:Dataset OR b:Metric)
                RETURN id(a) as source, id(b) as target, type(r) as type
                LIMIT 200
            """)
            links = [{"source": str(r["source"]), "target": str(r["target"]),
                       "type": r["type"]} for r in lr]

        return success_response({"nodes": nodes, "links": links})
    except Exception as e:
        raise DatabaseError(detail=str(e))


# ── Legacy API Compatibility Routes ─────────────────────────────────────
# Keep old paths working so nothing breaks during migration

@app.get("/api/health")
async def legacy_health():
    return await health_check()

@app.post("/api/research/start", status_code=201)
async def legacy_start(request: ResearchStartRequest):
    return await start_research(request)

@app.get("/api/research/{session_id}")
async def legacy_status(session_id: str):
    return await get_research_status(session_id)

@app.post("/api/graph/clear")
async def legacy_clear():
    return await clear_graph()

@app.get("/api/graph/{session_id}")
async def legacy_graph(session_id: str):
    return await get_graph_visualization(session_id)

@app.get("/api/graph/data")
async def legacy_graph_data():
    return await get_graph_data()


# ── WebSocket ──────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time research progress updates."""
    logger = get_logger(__name__)
    await manager.connect(session_id, websocket)

    if session_id not in active_sessions:
        await websocket.send_json({"type": "error", "message": "Invalid session"})
        await websocket.close()
        manager.disconnect(session_id)
        return

    try:
        session = active_sessions[session_id]

        await manager.send_message(session_id, {
            "type": "status", "agent": "system", "message": "Initializing..."
        })

        # Validate services
        if not settings.GROQ_API_KEY:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "GROQ_API_KEY not configured. Check .env file."
            })
            return

        if not db_manager.is_connected:
            await manager.send_message(session_id, {
                "type": "error", "message": "Neo4j is not connected"
            })
            return

        db = db_manager.get_db()

        # Create agents
        librarian = LibrarianAgent(settings.GROQ_API_KEY)
        cartographer = CartographerAgent(db)
        scientist = ScientistAgent(settings.GROQ_API_KEY, db)

        await manager.send_message(session_id, {
            "type": "status", "agent": "system", "message": "Agents ready"
        })

        # Build workflow
        workflow = StateGraph(GraphState)
        workflow.add_node("librarian", librarian)
        workflow.add_node("cartographer", cartographer)
        workflow.add_node("scientist", scientist)
        workflow.set_entry_point("librarian")
        workflow.add_edge("librarian", "cartographer")
        workflow.add_edge("cartographer", "scientist")
        workflow.add_edge("scientist", END)
        pathfinder = workflow.compile()

        # Initial state
        state = {
            "research_topic": session["topic"],
            "max_papers": session["max_papers"],
            "papers_found": [], "entities_extracted": [],
            "graph_updated": False, "gaps_identified": [],
            "final_hypothesis": "", "validation_script": "",
            "current_step": "librarian", "errors": [],
            "agent_messages": [],
        }

        await manager.send_message(session_id, {
            "type": "progress", "step": "librarian",
            "message": "Searching papers..."
        })

        # Run workflow — use run_in_executor to avoid blocking event loop
        loop = asyncio.get_event_loop()

        def run_stream():
            results = []
            for event in pathfinder.stream(state):
                results.append(event)
            return results

        events = await loop.run_in_executor(None, run_stream)

        for event in events:
            for node_name, node_output in event.items():
                state.update(node_output)
                await manager.send_message(session_id, {
                    "type": "progress", "step": node_name,
                    "message": f"{node_name.capitalize()} processing..."
                })

                if node_name == "librarian":
                    cnt = len(node_output.get("papers_found", []))
                    await manager.send_message(session_id, {
                        "type": "status", "agent": "librarian",
                        "message": f"Found {cnt} papers"
                    })
                elif node_name == "cartographer":
                    stats = node_output.get("graph_stats", {})
                    await manager.send_message(session_id, {
                        "type": "status", "agent": "cartographer",
                        "message": f"Graph: {stats.get('paper_count', 0)} papers"
                    })
                elif node_name == "scientist":
                    await manager.send_message(session_id, {
                        "type": "status", "agent": "scientist",
                        "message": "Hypothesis generated"
                    })

        # Final result
        result = {
            "session_id": session_id,
            "topic": session["topic"],
            "papers": len(state.get("papers_found", [])),
            "graph_stats": state.get("graph_stats", {}),
            "gaps": len(state.get("gaps_identified", [])),
            "hypothesis": state.get("final_hypothesis", ""),
            "reasoning": state.get("hypothesis_reasoning", ""),
        }

        active_sessions[session_id]["result"] = result
        active_sessions[session_id]["status"] = "completed"

        await manager.send_message(session_id, {
            "type": "complete", "data": result
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await manager.send_message(session_id, {
            "type": "error", "message": "An error occurred during analysis"
        })
    finally:
        manager.disconnect(session_id)


# ── Main Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    print(f"{'='*60}")
    print(f"  Scientific Pathfinder API v{s.APP_VERSION}")
    print(f"  Environment: {s.ENVIRONMENT}")
    print(f"  GROQ_API_KEY: {'Set' if s.GROQ_API_KEY else 'MISSING'}")
    print(f"  NEO4J_URI: {s.NEO4J_URI or 'MISSING'}")
    print(f"  Auth: {'Enabled' if s.auth_enabled else 'Disabled'}")
    print(f"{'='*60}")

    uvicorn.run(
        "api:app",
        host=s.HOST,
        port=s.PORT,
        reload=s.is_development,
    )