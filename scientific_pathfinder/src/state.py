"""
State management for the Scientific Pathfinder LangGraph workflow.

This module defines the state structure that gets passed between nodes
in the LangGraph, tracking the research journey from initial query to hypothesis.
"""

from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
import operator


class PaperMetadata(TypedDict):
    """Structure for individual paper information."""
    paper_id: str
    title: str
    abstract: str
    authors: List[str]
    year: Optional[int]
    citation_count: int
    url: str


class GraphEntity(TypedDict):
    """Structured entity extracted from papers for Neo4j."""
    entity_type: str  # 'Paper', 'Author', 'Method', 'Dataset', 'Metric'
    name: str
    properties: Dict[str, Any]
    relationships: List[Dict[str, str]]  # [{"type": "USES", "target": "BERT"}]


class ResearchGap(TypedDict):
    """Identified gap in the knowledge graph."""
    gap_type: str  # e.g., 'isolated_method', 'unexplored_combination'
    description: str
    entities_involved: List[str]
    reasoning: str


class GraphState(TypedDict):
    """
    Main state object for the Scientific Pathfinder workflow.
    
    This state is passed through all nodes in the LangGraph and accumulates
    information as the agent progresses through its research pipeline.
    """
    
    # Input Configuration
    research_topic: str
    max_papers: int
    
    # Librarian Output
    papers_found: Annotated[List[PaperMetadata], operator.add]
    search_complete: bool
    search_error: Optional[str]
    
    # Cartographer Output
    entities_extracted: Annotated[List[GraphEntity], operator.add]
    graph_updated: bool
    cypher_queries_executed: Annotated[List[str], operator.add]
    graph_stats: Optional[Dict[str, int]]  # Node/relationship counts
    
    # Scientist Output
    gaps_identified: Annotated[List[ResearchGap], operator.add]
    final_hypothesis: Optional[str]
    hypothesis_reasoning: Optional[str]
    validation_script: Optional[str]  # Python code to test hypothesis
    
    # Workflow Control
    current_step: str  # 'librarian', 'cartographer', 'scientist', 'complete'
    errors: Annotated[List[str], operator.add]
    
    # Metadata
    agent_messages: Annotated[List[Dict[str, str]], operator.add]  # Conversation log


def create_initial_state(
    research_topic: str,
    max_papers: int = 10
) -> GraphState:
    """
    Factory function to create a clean initial state.
    
    Args:
        research_topic: The research question or topic to investigate
        max_papers: Maximum number of papers to fetch from Semantic Scholar
    
    Returns:
        A fully initialized GraphState ready for the workflow
    """
    return GraphState(
        # Input
        research_topic=research_topic,
        max_papers=max_papers,
        
        # Librarian
        papers_found=[],
        search_complete=False,
        search_error=None,
        
        # Cartographer
        entities_extracted=[],
        graph_updated=False,
        cypher_queries_executed=[],
        graph_stats=None,
        
        # Scientist
        gaps_identified=[],
        final_hypothesis=None,
        hypothesis_reasoning=None,
        validation_script=None,
        
        # Workflow
        current_step='librarian',
        errors=[],
        agent_messages=[]
    )


# Type aliases for cleaner code
StateUpdate = Dict[str, Any]