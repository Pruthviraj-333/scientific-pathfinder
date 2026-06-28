"""
Scientific Pathfinder - Main Entry Point

This module orchestrates the entire research agent workflow using LangGraph.
It connects the Librarian, Cartographer, and Scientist in a stateful graph.
"""

import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import Dict, Any

from src.state import GraphState, create_initial_state
from src.agents import LibrarianAgent, CartographerAgent, ScientistAgent
from src.tools import CodeExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScientificPathfinder:
    """
    The main orchestrator for the Scientific Pathfinder agent system.
    
    This class builds and executes a LangGraph workflow that:
    1. Searches for papers (Librarian)
    2. Builds a knowledge graph (Cartographer)
    3. Discovers research gaps and proposes hypotheses (Scientist)
    """
    
    def __init__(
        self,
        groq_api_key: str,
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str
    ):
        """
        Initialize the Scientific Pathfinder with all required connections.
        
        Args:
            groq_api_key: API key for Groq LLM
            neo4j_uri: Neo4j database URI
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
        """
        logger.info("🚀 Initializing Scientific Pathfinder...")
        
        # Initialize Neo4j connection
        from src.graph_db import Neo4jGraphDB
        self.neo4j_client = Neo4jGraphDB(neo4j_uri, neo4j_username, neo4j_password)
        if not self.neo4j_client.connect():
            raise ConnectionError("Failed to connect to Neo4j database")
        
        # Initialize agents
        self.librarian = LibrarianAgent(groq_api_key)
        self.cartographer = CartographerAgent(self.neo4j_client)
        self.scientist = ScientistAgent(groq_api_key, self.neo4j_client)
        
        # Build the workflow graph
        self.graph = self._build_graph()
        
        logger.info("✓ Scientific Pathfinder initialized successfully")
    
    def _build_graph(self) -> StateGraph:
        """
        Construct the LangGraph workflow.
        
        The workflow follows this path:
        START -> Librarian -> Cartographer -> Scientist -> END
        
        Returns:
            Compiled StateGraph ready for execution
        """
        logger.info("🔧 Building LangGraph workflow...")
        
        # Create the graph with our state schema
        workflow = StateGraph(GraphState)
        
        # Add nodes (agents)
        workflow.add_node("librarian", self.librarian)
        workflow.add_node("cartographer", self.cartographer)
        workflow.add_node("scientist", self.scientist)
        
        # Define edges (workflow transitions)
        workflow.set_entry_point("librarian")
        
        # Librarian -> Cartographer (if papers found)
        workflow.add_edge("librarian", "cartographer")
        
        # Cartographer -> Scientist (if graph built)
        workflow.add_edge("cartographer", "scientist")
        
        # Scientist -> END (workflow complete)
        workflow.add_edge("scientist", END)
        
        # Compile the graph
        app = workflow.compile()
        
        logger.info("✓ LangGraph workflow built successfully")
        return app
    
    def run(
        self,
        research_topic: str,
        max_papers: int = 10,
        save_script: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the complete research workflow.
        
        Args:
            research_topic: The research question or topic to investigate
            max_papers: Maximum number of papers to analyze
            save_script: Whether to save the validation script to disk
            
        Returns:
            Final state dictionary with hypothesis and results
        """
        logger.info(f"🔬 Starting research on: '{research_topic}'")
        logger.info(f"📊 Parameters: max_papers={max_papers}")
        
        # Create initial state
        initial_state = create_initial_state(
            research_topic=research_topic,
            max_papers=max_papers
        )
        
        try:
            # Execute the workflow
            final_state = self.graph.invoke(initial_state)
            
            # Log results
            self._log_results(final_state)
            
            # Save validation script if requested
            if save_script and final_state.get('validation_script'):
                script_path = CodeExecutor.save_script(
                    final_state['validation_script'],
                    filename=f"validation_{research_topic[:20].replace(' ', '_')}.py"
                )
                final_state['script_path'] = script_path
            
            return final_state
            
        except Exception as e:
            logger.error(f"✗ Workflow execution failed: {e}")
            raise
    
    def _log_results(self, state: Dict[str, Any]):
        """
        Log a summary of the workflow results.
        
        Args:
            state: Final state after workflow completion
        """
        logger.info("\n" + "="*70)
        logger.info("📊 WORKFLOW RESULTS")
        logger.info("="*70)
        
        # Papers found
        papers = state.get('papers_found', [])
        logger.info(f"📚 Papers analyzed: {len(papers)}")
        
        # Graph stats
        stats = state.get('graph_stats', {})
        if stats:
            logger.info("🗺️  Graph statistics:")
            logger.info(f"   - Papers: {stats.get('paper_count', 0)}")
            logger.info(f"   - Authors: {stats.get('author_count', 0)}")
            logger.info(f"   - Methods: {stats.get('method_count', 0)}")
            logger.info(f"   - Datasets: {stats.get('dataset_count', 0)}")
            logger.info(f"   - Metrics: {stats.get('metric_count', 0)}")
            logger.info(f"   - Relationships: {stats.get('relationship_count', 0)}")
        
        # Gaps identified
        gaps = state.get('gaps_identified', [])
        logger.info(f"🔍 Research gaps found: {len(gaps)}")
        
        # Hypothesis
        hypothesis = state.get('final_hypothesis')
        if hypothesis:
            logger.info(f"\n💡 HYPOTHESIS:\n{hypothesis}\n")
        
        # Reasoning
        reasoning = state.get('hypothesis_reasoning')
        if reasoning:
            logger.info(f"📝 REASONING:\n{reasoning}\n")
        
        # Errors
        errors = state.get('errors', [])
        if errors:
            logger.warning(f"⚠️  Errors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"   - {error}")
        
        logger.info("="*70 + "\n")
    
    def cleanup(self):
        """Close all connections."""
        if self.neo4j_client:
            self.neo4j_client.close()
        logger.info("✓ Cleanup complete")


def main():
    """
    Main entry point for the Scientific Pathfinder.
    
    Loads environment variables and runs the research workflow.
    """
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    groq_api_key = os.getenv("GROQ_API_KEY")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    # Validate configuration
    if not all([groq_api_key, neo4j_uri, neo4j_password]):
        logger.error("❌ Missing required environment variables!")
        logger.error("Please ensure .env contains: GROQ_API_KEY, NEO4J_URI, NEO4J_PASSWORD")
        return
    
    # Example research topics (you can modify this)
    research_topics = [
        #"graph neural networks drug discovery", 
        "vision transformers for medical image classification",
        # "reinforcement learning for robotics manipulation"
    ]
    
    # Initialize the pathfinder
    pathfinder = ScientificPathfinder(
        groq_api_key=groq_api_key,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_username,
        neo4j_password=neo4j_password
    )
    
    try:
        # Run research for each topic
        for topic in research_topics:
            logger.info(f"\n{'='*70}")
            logger.info(f"🔬 RESEARCH TOPIC: {topic}")
            logger.info(f"{'='*70}\n")
            
            final_state = pathfinder.run(
                research_topic=topic,
                max_papers=15,
                save_script=True
            )
            
            # Print final hypothesis in a nice format
            if final_state.get('final_hypothesis'):
                print("\n" + "🎯 " * 35)
                print("\n💡 FINAL HYPOTHESIS:")
                print("-" * 70)
                print(final_state['final_hypothesis'])
                print("-" * 70)
                
                if final_state.get('hypothesis_reasoning'):
                    print("\n📝 REASONING:")
                    print("-" * 70)
                    print(final_state['hypothesis_reasoning'])
                    print("-" * 70)
                
                if final_state.get('script_path'):
                    print(f"\n✅ Validation script saved to: {final_state['script_path']}")
                
                print("\n" + "🎯 " * 35 + "\n")
    
    finally:
        # Cleanup
        pathfinder.cleanup()


if __name__ == "__main__":
    main()