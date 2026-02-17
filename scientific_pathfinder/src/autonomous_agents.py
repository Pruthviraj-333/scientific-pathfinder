"""
Autonomous Agents for Scientific Pathfinder

These agents use LLM reasoning to decide which tools to use and how to accomplish their goals.
Unlike the hardcoded agents, these agents are truly autonomous and adaptive.
"""

from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from typing import Dict, List
import logging
import os

from src.autonomous_tools import (
    search_semantic_scholar,
    search_arxiv,
    validate_paper_quality,
    extract_entities_from_paper,
    insert_paper_to_graph,
    query_graph_for_gaps,
    get_graph_statistics,
    generate_research_hypothesis,
    create_validation_script,
    merge_paper_lists,
)

logger = logging.getLogger(__name__)


class AutonomousLibrarianAgent:
    """
    Autonomous research librarian that decides its own search and processing strategy.
    
    The agent has access to multiple tools and uses LLM reasoning to:
    - Choose appropriate data sources based on research topic
    - Validate paper quality before processing
    - Extract entities strategically
    - Build knowledge graph incrementally
    - Adapt strategy based on results
    """
    
    def __init__(self, groq_api_key: str):
        """Initialize the autonomous librarian agent."""
        logger.info("🤖 Initializing Autonomous Librarian Agent...")
        
        # Initialize LLM with tool calling capability
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            temperature=0.3,  # Lower temp for more consistent tool use
            max_tokens=4096
        )
        
        # Define available tools
        self.tools = [
            search_semantic_scholar,
            search_arxiv,
            validate_paper_quality,
            extract_entities_from_paper,
            insert_paper_to_graph,
            merge_paper_lists,
        ]
        
        # Create agent prompt with clear instructions
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research librarian AI agent with autonomous decision-making capabilities.

Your Goal: Find high-quality academic papers on the research topic and build a knowledge graph.

Available Tools:
- search_semantic_scholar: Broad academic search across all disciplines
- search_arxiv: Preprint papers in physics, math, CS, AI
- validate_paper_quality: Check if papers meet quality standards (citations, year, etc.)
- extract_entities_from_paper: Extract methods, datasets, metrics using LLM
- insert_paper_to_graph: Add paper and entities to Neo4j knowledge graph
- merge_paper_lists: Combine and deduplicate papers from multiple sources

Strategic Guidelines:
1. CHOOSE SOURCES: Decide which search sources are most appropriate for the topic
   - Computer Science/AI/Physics → Use arXiv + Semantic Scholar
   - Medical/Biology → Use Semantic Scholar only (PubMed not available yet)
   - General topics → Use Semantic Scholar
   
2. VALIDATE QUALITY: Always validate paper quality before extracting entities
   - Skip low-quality papers (< 5 citations, too old)
   - For very recent papers (2024+), citation count is less important
   
3. BE EFFICIENT: 
   - You don't need to process ALL papers if you get good ones early
   - If first source gives excellent papers, you can stop
   - Extract entities only from validated papers
   
4. BUILD INCREMENTALLY: Insert papers to graph as you process them

5. ADAPT: If a search fails or gives poor results, try a different approach

Think step-by-step and explain your reasoning before each action.
Be strategic and efficient - quality over quantity!"""),
            ("user", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Create the tool-calling agent
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=20,  # Allow multiple tool calls
            handle_parsing_errors=True,
            return_intermediate_steps=True,  # Track agent's actions
        )
        
        logger.info("✓ Autonomous Librarian Agent initialized with {} tools".format(len(self.tools)))
    
    def __call__(self, state: Dict) -> Dict:
        """
        Execute autonomous research workflow.
        
        The agent will decide:
        - Which sources to search
        - How many papers to process
        - Which papers to validate
        - When to stop
        """
        research_topic = state.get('research_topic', '')
        max_papers = state.get('max_papers', 10)
        
        logger.info(f"🚀 Autonomous Librarian starting for topic: '{research_topic}'")
        
        # Prepare input for the agent
        agent_input = f"""Research Topic: "{research_topic}"
Target: Find and process up to {max_papers} high-quality papers

Your Task:
1. Search for relevant papers using appropriate sources
2. Validate paper quality
3. Extract entities (methods, datasets, metrics) from good papers
4. Insert papers and entities into the knowledge graph
5. Report your findings

Be strategic - choose the best tools for this specific topic!"""
        
        try:
            # Let the agent execute autonomously
            result = self.executor.invoke({"input": agent_input})
            
            # Extract information from agent's actions
            output = result.get('output', '')
            intermediate_steps = result.get('intermediate_steps', [])
            
            # Count processed papers from tool calls
            papers_inserted = 0
            for action, observation in intermediate_steps:
                if action.tool == 'insert_paper_to_graph':
                    papers_inserted += 1
            
            logger.info(f"✓ Autonomous Librarian completed: {papers_inserted} papers inserted")
            logger.info(f"Agent's final output: {output[:200]}...")
            
            # Return state updates
            return {
                'papers_found': [],  # Will be in Neo4j
                'search_complete': True,
                'autonomous_agent_output': output,
                'agent_actions': [
                    {
                        'tool': action.tool,
                        'input': str(action.tool_input)[:100],
                        'output': str(observation)[:100]
                    }
                    for action, observation in intermediate_steps
                ],
                'papers_processed': papers_inserted,
                'agent_messages': [{
                    'agent': 'autonomous_librarian',
                    'message': f'Processed {papers_inserted} papers autonomously',
                    'reasoning': output
                }]
            }
        
        except Exception as e:
            logger.error(f"✗ Autonomous Librarian error: {e}", exc_info=True)
            return {
                'search_complete': True,
                'errors': [f'Autonomous agent error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'autonomous_librarian',
                    'message': f'Failed: {str(e)}'
                }]
            }


class AutonomousScientistAgent:
    """
    Autonomous research scientist that decides its own analysis strategy.
    
    The agent has access to analysis tools and uses LLM reasoning to:
    - Choose appropriate gap analysis methods
    - Prioritize impactful gaps
    - Generate novel hypotheses
    - Create validation scripts
    """
    
    def __init__(self, groq_api_key: str, neo4j_client=None):
        """Initialize the autonomous scientist agent.
        
        Args:
            groq_api_key: Groq API key for LLM
            neo4j_client: Optional Neo4j client (not used, for compatibility)
        """
        logger.info("🤖 Initializing Autonomous Scientist Agent...")
        
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            temperature=0.7,  # Higher temp for creative hypothesis generation
            max_tokens=4096
        )
        
        # Define available tools
        self.tools = [
            query_graph_for_gaps,
            get_graph_statistics,
            generate_research_hypothesis,
            create_validation_script,
        ]
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research scientist AI agent with autonomous decision-making capabilities.

Your Goal: Analyze the knowledge graph to find valuable research gaps and generate novel hypotheses.

Available Tools:
- query_graph_for_gaps: Find gaps in knowledge graph (rare_combinations, isolated_nodes, etc.)
- get_graph_statistics: Get current graph statistics to understand scope
- generate_research_hypothesis: Create novel hypothesis based on gaps
- create_validation_script: Generate Python code to test the hypothesis

Strategic Guidelines:
1. UNDERSTAND CONTEXT: Start by getting graph statistics to understand what data you have

2. CHOOSE ANALYSIS: Decide which gap analysis is most appropriate
   - rare_combinations: Find method-dataset pairs rarely used together
   - isolated_nodes: Find methods/datasets not well connected
   - Choose based on graph size and research domain

3. PRIORITIZE QUALITY: Focus on impactful gaps, not just any gap
   - Gaps that combine proven methods with new datasets
   - Gaps in actively researched areas
   - Feasible and testable gaps

4. GENERATE HYPOTHESIS: Create a novel, testable hypothesis
   - Must be specific and actionable
   - Should combine existing work in new ways
   - Should have clear validation path

5. CREATE VALIDATION: Provide concrete validation script

Think strategically about which analysis will yield the most valuable insights!"""),
            ("user", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=15,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )
        
        logger.info("✓ Autonomous Scientist Agent initialized with {} tools".format(len(self.tools)))
    
    def __call__(self, state: Dict) -> Dict:
        """Execute autonomous gap analysis and hypothesis generation."""
        
        research_topic = state.get('research_topic', '')
        
        logger.info(f"🚀 Autonomous Scientist starting for topic: '{research_topic}'")
        
        agent_input = f"""Research Topic: "{research_topic}"

Your Task:
1. Get graph statistics to understand the knowledge base
2. Analyze the graph for research gaps
3. Generate a novel, testable hypothesis based on the most promising gaps
4. Create a validation script

Focus on finding truly valuable and feasible research opportunities!"""
        
        try:
            result = self.executor.invoke({"input": agent_input})
            
            output = result.get('output', '')
            intermediate_steps = result.get('intermediate_steps', [])
            
            # Extract hypothesis and script from agent's actions
            hypothesis = ""
            reasoning = ""
            validation_script = ""
            gaps_found = []
            
            for action, observation in intermediate_steps:
                if action.tool == 'generate_research_hypothesis':
                    if isinstance(observation, dict):
                        hypothesis = observation.get('hypothesis', '')
                        reasoning = observation.get('reasoning', '')
                
                elif action.tool == 'create_validation_script':
                    validation_script = str(observation)
                
                elif action.tool == 'query_graph_for_gaps':
                    if isinstance(observation, list):
                        gaps_found = observation
            
            logger.info(f"✓ Autonomous Scientist completed")
            logger.info(f"Hypothesis: {hypothesis[:100]}...")
            
            return {
                'gaps_identified': gaps_found,
                'final_hypothesis': hypothesis or output,
                'hypothesis_reasoning': reasoning or "Generated by autonomous agent",
                'validation_script': validation_script,
                'current_step': 'complete',
                'autonomous_agent_output': output,
                'agent_actions': [
                    {
                        'tool': action.tool,
                        'input': str(action.tool_input)[:100]
                    }
                    for action, observation in intermediate_steps
                ],
                'agent_messages': [{
                    'agent': 'autonomous_scientist',
                    'message': f'Generated hypothesis autonomously',
                    'reasoning': output
                }]
            }
        
        except Exception as e:
            logger.error(f"✗ Autonomous Scientist error: {e}", exc_info=True)
            return {
                'current_step': 'complete',
                'errors': [f'Autonomous agent error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'autonomous_scientist',
                    'message': f'Failed: {str(e)}'
                }]
            }


# Simple wrapper for Cartographer (stays mostly the same)
class AutonomousCartographerAgent:
    """
    Cartographer agent - adapted for autonomous workflow.
    Since autonomous librarian inserts papers directly via tools,
    cartographer just validates and gets stats.
    """
    
    def __init__(self, neo4j_client):
        """Initialize cartographer."""
        self.db = neo4j_client
        logger.info("✓ Autonomous Cartographer initialized (validates graph and gets stats)")
    
    def __call__(self, state: Dict) -> Dict:
        """Validate graph and get statistics."""
        logger.info("🗺️  CARTOGRAPHER: Validating knowledge graph...")
        
        try:
            # Ensure schema exists
            self.db.create_schema()
            
            # Get graph statistics
            stats = self.db.get_graph_stats()
            
            logger.info(f"✓ CARTOGRAPHER: Graph stats: {stats}")
            
            return {
                'graph_updated': True,
                'graph_stats': stats,
                'current_step': 'complete',
                'agent_messages': [{
                    'agent': 'cartographer',
                    'message': f'Graph validated: {stats.get("paper_count", 0)} papers'
                }]
            }
        
        except Exception as e:
            logger.error(f"✗ CARTOGRAPHER ERROR: {e}")
            return {
                'current_step': 'complete',
                'errors': [f'Cartographer error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'cartographer',
                    'message': f'Failed: {str(e)}'
                }]
            }