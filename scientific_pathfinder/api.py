"""
FastAPI Backend for Scientific Pathfinder.

Provides REST API and WebSocket endpoints for the frontend.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging
import os
from datetime import datetime
import uuid
from pathlib import Path

# Load environment variables from parent directory
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Import your existing Scientific Pathfinder
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.graph_db import Neo4jGraphDB
from src.agents import LibrarianAgent, CartographerAgent, ScientistAgent
from src.state import GraphState
from langgraph.graph import StateGraph, END

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Scientific Pathfinder API",
    description="AI-powered research gap discovery system",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ResearchRequest(BaseModel):
    topic: str
    max_papers: int = 10

class ResearchResponse(BaseModel):
    session_id: str
    status: str
    message: str

# In-memory storage (use Redis in production)
active_sessions: Dict[str, Dict[str, Any]] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

manager = ConnectionManager()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Scientific Pathfinder API",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    try:
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        groq_key = os.getenv("GROQ_API_KEY")
        s2_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        
        services = {
            "neo4j": "missing" if not neo4j_uri else "configured",
            "groq": "configured" if groq_key else "missing",
            "semantic_scholar": "configured" if s2_key else "public_limits"
        }
        
        # Try to connect to Neo4j if configured
        if neo4j_uri and neo4j_pass:
            try:
                db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
                neo4j_status = db.connect()
                if neo4j_status:
                    db.close()
                    services["neo4j"] = "connected"
                else:
                    services["neo4j"] = "connection_failed"
            except Exception as e:
                services["neo4j"] = f"error: {str(e)[:50]}"
        
        return {
            "status": "healthy",
            "services": services,
            "env_file": str(env_path),
            "env_loaded": env_path.exists()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/api/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    """Start a new research analysis session."""
    session_id = str(uuid.uuid4())
    
    active_sessions[session_id] = {
        "topic": request.topic,
        "max_papers": request.max_papers,
        "status": "initiated",
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Session {session_id} created for: {request.topic}")
    
    return ResearchResponse(
        session_id=session_id,
        status="initiated",
        message=f"Connect to /ws/{session_id} for updates"
    )

@app.get("/api/research/{session_id}")
async def get_research_status(session_id: str):
    """Get session status."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return active_sessions[session_id]

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time progress updates."""
    await manager.connect(session_id, websocket)
    
    if session_id not in active_sessions:
        await websocket.send_json({"type": "error", "message": "Invalid session"})
        await websocket.close()
        return
    
    try:
        session = active_sessions[session_id]
        
        # Send initialization message
        await manager.send_message(session_id, {
            "type": "status",
            "agent": "system",
            "message": "Initializing..."
        })
        
        # Get environment variables
        groq_key = os.getenv("GROQ_API_KEY")
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        
        # Validate configuration
        if not groq_key:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "GROQ_API_KEY not configured. Check .env file."
            })
            return
        
        if not neo4j_uri or not neo4j_pass:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Neo4j credentials not configured. Check .env file."
            })
            return
        
        # Initialize components
        db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
        if not db.connect():
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Neo4j connection failed"
            })
            return
        
        # Create agents
        librarian = LibrarianAgent(groq_key)
        cartographer = CartographerAgent(db)
        scientist = ScientistAgent(groq_key, db)
        
        await manager.send_message(session_id, {
            "type": "status",
            "agent": "system",
            "message": "Agents ready"
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
            "papers_found": [],
            "entities_extracted": [],
            "graph_updated": False,
            "gaps_identified": [],
            "final_hypothesis": "",
            "validation_script": "",
            "current_step": "librarian",
            "errors": [],
            "agent_messages": []
        }
        
        # Run workflow with updates
        await manager.send_message(session_id, {
            "type": "progress",
            "step": "librarian",
            "message": "Searching papers..."
        })
        
        for event in pathfinder.stream(state):
            for node_name, node_output in event.items():
                await manager.send_message(session_id, {
                    "type": "progress",
                    "step": node_name,
                    "message": f"{node_name.capitalize()} processing..."
                })
                
                if node_name == "librarian":
                    papers_count = len(node_output.get("papers_found", []))
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "librarian",
                        "message": f"Found {papers_count} papers"
                    })
                
                elif node_name == "cartographer":
                    stats = node_output.get("graph_stats", {})
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "cartographer",
                        "message": f"Graph: {stats.get('paper_count', 0)} papers"
                    })
                
                elif node_name == "scientist":
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "scientist",
                        "message": "Hypothesis generated"
                    })
        
        # Send final result
        result = {
            "session_id": session_id,
            "topic": session["topic"],
            "papers": len(state.get("papers_found", [])),
            "graph_stats": state.get("graph_stats", {}),
            "gaps": len(state.get("gaps_identified", [])),
            "hypothesis": state.get("final_hypothesis", ""),
            "reasoning": state.get("reasoning", ""),
        }
        
        active_sessions[session_id]["result"] = result
        active_sessions[session_id]["status"] = "completed"
        
        await manager.send_message(session_id, {
            "type": "complete",
            "data": result
        })
        
        db.close()
        
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await manager.send_message(session_id, {
            "type": "error",
            "message": str(e)
        })
    finally:
        manager.disconnect(session_id)

if __name__ == "__main__":
    import uvicorn
    
    # Print configuration info
    print("=" * 60)
    print("🚀 Scientific Pathfinder API")
    print("=" * 60)
    print(f"Env file: {env_path}")
    print(f"Env exists: {env_path.exists()}")
    print(f"GROQ_API_KEY: {'✓ Set' if os.getenv('GROQ_API_KEY') else '✗ Missing'}")
    print(f"NEO4J_URI: {os.getenv('NEO4J_URI') or '✗ Missing'}")
    print("=" * 60)
    print()
    
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)


# Initialize FastAPI
app = FastAPI(
    title="Scientific Pathfinder API",
    description="AI-powered research gap discovery system",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ResearchRequest(BaseModel):
    topic: str
    max_papers: int = 10

class ResearchResponse(BaseModel):
    session_id: str
    status: str
    message: str

# In-memory storage (use Redis in production)
active_sessions: Dict[str, Dict[str, Any]] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

manager = ConnectionManager()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Scientific Pathfinder API",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    try:
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        
        db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
        neo4j_status = db.connect()
        if neo4j_status:
            db.close()
        
        return {
            "status": "healthy",
            "services": {
                "neo4j": "connected" if neo4j_status else "disconnected",
                "groq": "configured" if os.getenv("GROQ_API_KEY") else "missing",
                "semantic_scholar": "configured" if os.getenv("SEMANTIC_SCHOLAR_API_KEY") else "public_limits"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/api/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    """Start a new research analysis session."""
    session_id = str(uuid.uuid4())
    
    active_sessions[session_id] = {
        "topic": request.topic,
        "max_papers": request.max_papers,
        "status": "initiated",
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Session {session_id} created for: {request.topic}")
    
    return ResearchResponse(
        session_id=session_id,
        status="initiated",
        message=f"Connect to /ws/{session_id} for updates"
    )

@app.get("/api/research/{session_id}")
async def get_research_status(session_id: str):
    """Get session status."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return active_sessions[session_id]

@app.get("/api/graph/{session_id}")
async def get_graph_visualization(session_id: str):
    """Get graph data for D3.js visualization."""
    try:
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        
        if not neo4j_uri or not neo4j_pass:
            raise HTTPException(status_code=503, detail="Neo4j not configured")
        
        db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
        if not db.connect():
            raise HTTPException(status_code=503, detail="Cannot connect to Neo4j")
        
        # Query for graph data
        with db.driver.session() as neo4j_session:
            # Get nodes with consistent IDs
            nodes_query = """
            MATCH (n)
            WHERE n:Paper OR n:Method OR n:Dataset OR n:Metric
            WITH n, id(n) as node_id
            RETURN node_id as id, 
                   labels(n)[0] as type, 
                   COALESCE(n.title, n.name, 'Unknown') as label,
                   properties(n) as properties
            LIMIT 100
            """
            nodes_result = neo4j_session.run(nodes_query)
            nodes = []
            node_ids = set()
            
            for record in nodes_result:
                node_id = str(record["id"])
                node_ids.add(node_id)
                label = record["label"]
                if len(label) > 40:
                    label = label[:37] + "..."
                    
                nodes.append({
                    "id": node_id,
                    "label": label,
                    "type": record["type"].lower() if record["type"] else "unknown",
                    "properties": dict(record["properties"]) if record["properties"] else {}
                })
            
            # Get relationships only between existing nodes
            links_query = """
            MATCH (a)-[r]->(b)
            WHERE (a:Paper OR a:Method OR a:Dataset OR a:Metric)
              AND (b:Paper OR b:Method OR b:Dataset OR b:Metric)
            RETURN id(a) as source, id(b) as target, type(r) as type
            LIMIT 200
            """
            links_result = neo4j_session.run(links_query)
            links = []
            
            for record in links_result:
                source_id = str(record["source"])
                target_id = str(record["target"])
                
                # Only include links where both nodes exist
                if source_id in node_ids and target_id in node_ids:
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": record["type"]
                    })
        
        db.close()
        
        logger.info(f"Returning {len(nodes)} nodes and {len(links)} links for visualization")
        
        return {"nodes": nodes, "links": links}
    
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/data")
async def get_graph_data(session_id: Optional[str] = None):
    """Get graph data for D3.js visualization."""
    try:
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        
        if not neo4j_uri or not neo4j_pass:
            raise HTTPException(status_code=503, detail="Neo4j not configured")
        
        db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
        if not db.connect():
            raise HTTPException(status_code=503, detail="Cannot connect to Neo4j")
        
        # Query for graph data
        with db.driver.session() as session_db:
            # Get nodes (limit for performance)
            nodes_query = """
            MATCH (n)
            WHERE n:Paper OR n:Method OR n:Dataset OR n:Metric
            RETURN id(n) as id, labels(n)[0] as type, 
                   COALESCE(n.title, n.name) as label,
                   properties(n) as properties
            LIMIT 100
            """
            nodes_result = session_db.run(nodes_query)
            nodes = []
            for record in nodes_result:
                nodes.append({
                    "id": str(record["id"]),
                    "label": (record["label"][:50] + "...") if len(record["label"]) > 50 else record["label"],
                    "type": record["type"].lower(),
                    "properties": dict(record["properties"])
                })
            
            # Get relationships
            links_query = """
            MATCH (a)-[r]->(b)
            WHERE (a:Paper OR a:Method OR a:Dataset OR a:Metric)
              AND (b:Paper OR b:Method OR b:Dataset OR b:Metric)
            RETURN id(a) as source, id(b) as target, type(r) as type
            LIMIT 200
            """
            links_result = session_db.run(links_query)
            links = []
            for record in links_result:
                links.append({
                    "source": str(record["source"]),
                    "target": str(record["target"]),
                    "type": record["type"]
                })
        
        db.close()
        
        return {"nodes": nodes, "links": links}
    
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time progress updates."""
    await manager.connect(session_id, websocket)
    
    if session_id not in active_sessions:
        await websocket.send_json({"type": "error", "message": "Invalid session"})
        await websocket.close()
        return
    
    try:
        session = active_sessions[session_id]
        
        # Send initialization message
        await manager.send_message(session_id, {
            "type": "status",
            "agent": "system",
            "message": "Initializing..."
        })
        
        # Initialize components
        groq_key = os.getenv("GROQ_API_KEY")
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        
        db = Neo4jGraphDB(neo4j_uri, neo4j_user, neo4j_pass)
        if not db.connect():
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Neo4j connection failed"
            })
            return
        
        # Create agents
        librarian = LibrarianAgent(groq_key)
        cartographer = CartographerAgent(db)
        scientist = ScientistAgent(groq_key, db)
        
        await manager.send_message(session_id, {
            "type": "status",
            "agent": "system",
            "message": "Agents ready"
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
            "papers_found": [],
            "entities_extracted": [],
            "graph_updated": False,
            "gaps_identified": [],
            "final_hypothesis": "",
            "validation_script": "",
            "current_step": "librarian",
            "errors": [],
            "agent_messages": []
        }
        
        # Run workflow with updates
        await manager.send_message(session_id, {
            "type": "progress",
            "step": "librarian",
            "message": "Searching papers..."
        })
        
        for event in pathfinder.stream(state):
            for node_name, node_output in event.items():
                state.update(node_output)
                await manager.send_message(session_id, {
                    "type": "progress",
                    "step": node_name,
                    "message": f"{node_name.capitalize()} processing..."
                })
                
                if node_name == "librarian":
                    papers_count = len(node_output.get("papers_found", []))
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "librarian",
                        "message": f"Found {papers_count} papers"
                    })
                
                elif node_name == "cartographer":
                    stats = node_output.get("graph_stats", {})
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "cartographer",
                        "message": f"Graph: {stats.get('paper_count', 0)} papers"
                    })
                
                elif node_name == "scientist":
                    await manager.send_message(session_id, {
                        "type": "status",
                        "agent": "scientist",
                        "message": "Hypothesis generated"
                    })
        
        # Send final result
        logger.info(f"Final state keys: {list(state.keys())}")
        logger.info(f"Papers found: {len(state.get('papers_found', []))}")
        logger.info(f"Hypothesis length: {len(state.get('final_hypothesis', ''))}")

        result = {
            "session_id": session_id,
            "topic": session["topic"],
            "papers": len(state.get("papers_found", [])),
            "graph_stats": state.get("graph_stats", {}),
            "gaps": len(state.get("gaps_identified", [])),
            "hypothesis": state.get("final_hypothesis", ""),
            "reasoning": state.get("hypothesis_reasoning", ""),  # FIX: Changed from 'reasoning'
        }

        logger.info(f"Sending result - Papers: {result['papers']}, Hypothesis: {len(result['hypothesis'])} chars")
        
        active_sessions[session_id]["result"] = result
        active_sessions[session_id]["status"] = "completed"
        
        await manager.send_message(session_id, {
            "type": "complete",
            "data": result
        })
        
        db.close()
        
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await manager.send_message(session_id, {
            "type": "error",
            "message": str(e)
        })
    finally:
        manager.disconnect(session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)