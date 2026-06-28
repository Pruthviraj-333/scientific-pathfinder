"""
The three core agents of the Scientific Pathfinder workflow.

Each agent is implemented as a LangGraph node that:
1. Receives the current state
2. Performs its specialized task
3. Returns state updates
"""

import json
import logging
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from src.state import GraphState, StateUpdate, GraphEntity, ResearchGap
from src.tools import SemanticScholarTool, validate_paper_metadata
from src.graph_db import Neo4jGraphDB
from prompts.system_prompts import (
    LIBRARIAN_SYSTEM_PROMPT,
    SCIENTIST_SYSTEM_PROMPT,
    ENTITY_EXTRACTION_PROMPT_TEMPLATE,
    GAP_ANALYSIS_PROMPT_TEMPLATE,
    VALIDATION_SCRIPT_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)


class LibrarianAgent:
    """
    The Librarian searches for papers and extracts structured entities.
    
    Responsibilities:
    1. Search Semantic Scholar for relevant papers
    2. Extract entities (Methods, Datasets, Metrics) from abstracts using Groq
    3. Update state with papers and extracted entities
    """
    
    def __init__(self, groq_api_key: str):
        """Initialize the Librarian with Groq LLM."""
        try:
            # Try newer version with api_key parameter
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=groq_api_key,
                temperature=0.1,
                max_tokens=2048
            )
        except TypeError:
            # Fall back to older version with groq_api_key parameter
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=groq_api_key,
                temperature=0.1,
                max_tokens=2048
            )
        self.search_tool = SemanticScholarTool()
        logger.info("✓ Librarian initialized")
    
    def __call__(self, state: GraphState) -> StateUpdate:
        """
        Execute the Librarian's workflow.
        
        Args:
            state: Current graph state
            
        Returns:
            State updates with papers and entities
        """
        logger.info("📚 LIBRARIAN: Starting paper search...")
        
        try:
            # Step 1: Search for papers
            papers = self.search_tool.search_papers(
                query=state['research_topic'],
                limit=state['max_papers']
            )
            
            if not papers:
                return {
                    'search_complete': True,
                    'search_error': 'No papers found with abstracts',
                    'current_step': 'complete',
                    'errors': ['No papers found for the given topic'],
                    'agent_messages': [{
                        'agent': 'librarian',
                        'message': 'Search completed but no papers found'
                    }]
                }
            
            logger.info(f"📚 LIBRARIAN: Found {len(papers)} papers")
            
            # Step 2: Extract entities from each paper
            papers_with_entities = []
            all_entities = []
            
            for i, paper in enumerate(papers, 1):
                logger.info(f"📚 LIBRARIAN: Processing paper {i}/{len(papers)}")
                
                if not validate_paper_metadata(paper):
                    logger.warning(f"Skipping invalid paper: {paper.get('title', 'Unknown')}")
                    continue
                
                # Extract entities using LLM
                entities = self._extract_entities(paper)
                
                if entities:
                    paper['entities'] = entities
                    papers_with_entities.append(paper)
                    
                    # Convert to GraphEntity format for state
                    for method in entities.get('methods', []):
                        all_entities.append(GraphEntity(
                            entity_type='Method',
                            name=method,
                            properties={},
                            relationships=[{'type': 'USES_METHOD', 'target': paper['paper_id']}]
                        ))
                    
                    for dataset in entities.get('datasets', []):
                        all_entities.append(GraphEntity(
                            entity_type='Dataset',
                            name=dataset,
                            properties={},
                            relationships=[{'type': 'USES_DATASET', 'target': paper['paper_id']}]
                        ))
                    
                    for metric in entities.get('metrics', []):
                        all_entities.append(GraphEntity(
                            entity_type='Metric',
                            name=metric,
                            properties={},
                            relationships=[{'type': 'MEASURES_WITH', 'target': paper['paper_id']}]
                        ))
            
            logger.info(f"✓ LIBRARIAN: Extracted entities from {len(papers_with_entities)} papers")
            
            return {
                'papers_found': papers_with_entities,
                'entities_extracted': all_entities,
                'search_complete': True,
                'current_step': 'cartographer',
                'agent_messages': [{
                    'agent': 'librarian',
                    'message': f'Found {len(papers_with_entities)} papers with {len(all_entities)} entities'
                }]
            }
            
        except Exception as e:
            logger.error(f"✗ LIBRARIAN ERROR: {e}")
            return {
                'search_complete': True,
                'search_error': str(e),
                'current_step': 'complete',
                'errors': [f'Librarian error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'librarian',
                    'message': f'Failed with error: {str(e)}'
                }]
            }
    
    def _extract_entities(self, paper: Dict[str, Any]) -> Dict[str, list]:
        """
        Use Groq LLM to extract entities from a paper's abstract.
        
        Args:
            paper: Paper metadata with abstract
            
        Returns:
            Dictionary with methods, datasets, and metrics lists
        """
        prompt = ENTITY_EXTRACTION_PROMPT_TEMPLATE.format(
            title=paper['title'],
            abstract=paper['abstract']
        )
        
        try:
            messages = [
                SystemMessage(content=LIBRARIAN_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Handle empty response
            if not content:
                logger.warning(f"Empty response from LLM for paper: {paper['title'][:50]}")
                return {'methods': [], 'datasets': [], 'metrics': []}
            
            # Remove markdown code fences if present
            if content.startswith('```'):
                # Remove ```json or ``` at start
                content = content.split('\n', 1)[1] if '\n' in content else content[3:]
                # Remove ``` at end
                if content.endswith('```'):
                    content = content.rsplit('```', 1)[0]
                content = content.strip()
            
            # Try to parse JSON
            try:
                entities = json.loads(content)
            except json.JSONDecodeError:
                # If still fails, log the actual response for debugging
                logger.warning(f"Could not parse response: {content[:200]}")
                return {'methods': [], 'datasets': [], 'metrics': []}
            
            # Validate structure
            if not all(k in entities for k in ['methods', 'datasets', 'metrics']):
                logger.warning(f"Invalid entity structure for paper: {paper['title'][:50]}")
                return {'methods': [], 'datasets': [], 'metrics': []}
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return {'methods': [], 'datasets': [], 'metrics': []}
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {'methods': [], 'datasets': [], 'metrics': []}


class CartographerAgent:
    """
    The Cartographer builds the Knowledge Graph in Neo4j.
    
    Responsibilities:
    1. Take papers with extracted entities
    2. Insert them into Neo4j using structured Cypher queries
    3. Update state with graph statistics
    """
    
    def __init__(self, neo4j_client: Neo4jGraphDB):
        """Initialize the Cartographer with Neo4j connection."""
        self.db = neo4j_client
        logger.info("✓ Cartographer initialized")
    
    def __call__(self, state: GraphState) -> StateUpdate:
        """
        Execute the Cartographer's workflow.
        
        Args:
            state: Current graph state
            
        Returns:
            State updates with graph statistics
        """
        logger.info("🗺️  CARTOGRAPHER: Building knowledge graph...")
        
        try:
            # Ensure schema exists
            self.db.create_schema()
            
            papers = state.get('papers_found', [])
            
            if not papers:
                return {
                    'graph_updated': False,
                    'current_step': 'complete',
                    'errors': ['No papers to process'],
                    'agent_messages': [{
                        'agent': 'cartographer',
                        'message': 'No papers available for graph construction'
                    }]
                }
            
            # Insert papers into graph
            successful_inserts = 0
            cypher_queries = []
            
            for i, paper in enumerate(papers, 1):
                logger.info(f"🗺️  CARTOGRAPHER: Inserting paper {i}/{len(papers)}")
                
                success = self.db.upsert_paper_to_graph(paper)
                
                if success:
                    successful_inserts += 1
                    # Record that we executed a cypher query (simplified)
                    cypher_queries.append(f"UPSERT paper: {paper['paper_id']}")
            
            # Get graph statistics
            stats = self.db.get_graph_stats()
            
            logger.info(f"✓ CARTOGRAPHER: Inserted {successful_inserts}/{len(papers)} papers")
            logger.info(f"📊 Graph stats: {stats}")
            
            return {
                'graph_updated': True,
                'cypher_queries_executed': cypher_queries,
                'graph_stats': stats,
                'current_step': 'scientist',
                'agent_messages': [{
                    'agent': 'cartographer',
                    'message': f'Built graph with {stats.get("paper_count", 0)} papers, '
                               f'{stats.get("method_count", 0)} methods, '
                               f'{stats.get("dataset_count", 0)} datasets'
                }]
            }
            
        except Exception as e:
            logger.error(f"✗ CARTOGRAPHER ERROR: {e}")
            return {
                'graph_updated': False,
                'current_step': 'complete',
                'errors': [f'Cartographer error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'cartographer',
                    'message': f'Failed with error: {str(e)}'
                }]
            }


class ScientistAgent:
    """
    The Scientist discovers research gaps and proposes novel hypotheses.
    
    Responsibilities:
    1. Query Neo4j for structural holes and patterns
    2. Analyze gaps using Groq LLM
    3. Generate a testable hypothesis
    4. Create a validation script
    """
    
    def __init__(self, groq_api_key: str, neo4j_client: Neo4jGraphDB):
        """Initialize the Scientist with LLM and graph access."""
        try:
            # Try newer version with api_key parameter
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=groq_api_key,
                temperature=0.7,
                max_tokens=4096
            )
        except TypeError:
            # Fall back to older version with groq_api_key parameter
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=groq_api_key,
                temperature=0.7,
                max_tokens=4096
            )
        self.db = neo4j_client
        logger.info("✓ Scientist initialized")
    
    def __call__(self, state: GraphState) -> StateUpdate:
        """
        Execute the Scientist's workflow.
        
        Args:
            state: Current graph state
            
        Returns:
            State updates with hypothesis and validation script
        """
        logger.info("🔬 SCIENTIST: Analyzing knowledge graph for gaps...")
        
        try:
            # Step 1: Query graph for gaps
            isolated_nodes = self.db.find_isolated_nodes('Method')
            rare_combos = self.db.find_rare_combinations()
            graph_stats = state.get('graph_stats', {})
            
            logger.info(f"🔬 SCIENTIST: Found {len(isolated_nodes)} isolated nodes")
            logger.info(f"🔬 SCIENTIST: Found {len(rare_combos)} rare combinations")
            
            # Step 2: Generate hypothesis using LLM
            hypothesis_data = self._generate_hypothesis(
                graph_stats=graph_stats,
                isolated_nodes=isolated_nodes,
                rare_combinations=rare_combos,
                research_topic=state['research_topic']
            )
            
            if not hypothesis_data:
                return {
                    'current_step': 'complete',
                    'errors': ['Failed to generate hypothesis'],
                    'agent_messages': [{
                        'agent': 'scientist',
                        'message': 'Could not identify promising research gaps'
                    }]
                }
            
            # Step 3: Generate validation script
            validation_script = self._generate_validation_script(
                hypothesis_data['hypothesis']
            )
            
            # Convert gaps to ResearchGap format
            gaps = []
            for combo in rare_combos[:5]:  # Top 5 gaps
                gaps.append(ResearchGap(
                    gap_type=combo.get('gap_type', 'rare_combination'),
                    description=f"{combo.get('method', 'Unknown')} + {combo.get('dataset', 'Unknown')}",
                    entities_involved=[combo.get('method', ''), combo.get('dataset', '')],
                    reasoning=f"Used in {combo.get('usage_count', 0)} papers - underexplored"
                ))
            
            logger.info("✓ SCIENTIST: Hypothesis generated successfully")
            
            return {
                'gaps_identified': gaps,
                'final_hypothesis': hypothesis_data['hypothesis'],
                'hypothesis_reasoning': hypothesis_data['reasoning'],
                'validation_script': validation_script,
                'current_step': 'complete',
                'agent_messages': [{
                    'agent': 'scientist',
                    'message': f'Proposed hypothesis: {hypothesis_data["hypothesis"][:100]}...'
                }]
            }
            
        except Exception as e:
            logger.error(f"✗ SCIENTIST ERROR: {e}")
            return {
                'current_step': 'complete',
                'errors': [f'Scientist error: {str(e)}'],
                'agent_messages': [{
                    'agent': 'scientist',
                    'message': f'Failed with error: {str(e)}'
                }]
            }
    
    def _generate_hypothesis(
        self,
        graph_stats: Dict,
        isolated_nodes: list,
        rare_combinations: list,
        research_topic: str
    ) -> Dict[str, str]:
        """
        Use LLM to analyze gaps and generate hypothesis.
        
        Returns:
            Dictionary with 'hypothesis' and 'reasoning' keys
        """
        prompt = GAP_ANALYSIS_PROMPT_TEMPLATE.format(
            graph_stats=json.dumps(graph_stats, indent=2),
            isolated_nodes=json.dumps(isolated_nodes[:10], indent=2),
            rare_combinations=json.dumps(rare_combinations[:10], indent=2),
            research_topic=research_topic
        )
        
        try:
            messages = [
                SystemMessage(content=SCIENTIST_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Parse the response to extract hypothesis and reasoning
            lines = content.split('\n')
            hypothesis = ""
            reasoning = ""
            
            # Simple parsing (you can make this more sophisticated)
            in_hypothesis = False
            in_reasoning = False
            
            for line in lines:
                if 'hypothesis:' in line.lower():
                    in_hypothesis = True
                    in_reasoning = False
                    hypothesis = line.split(':', 1)[1].strip() if ':' in line else ""
                elif 'reasoning:' in line.lower():
                    in_reasoning = True
                    in_hypothesis = False
                    reasoning = line.split(':', 1)[1].strip() if ':' in line else ""
                elif in_hypothesis and line.strip():
                    hypothesis += " " + line.strip()
                elif in_reasoning and line.strip():
                    reasoning += " " + line.strip()
            
            # If parsing failed, use the whole response as hypothesis
            if not hypothesis:
                hypothesis = content[:500]  # First 500 chars
                reasoning = "See full analysis above"
            
            return {
                'hypothesis': hypothesis.strip(),
                'reasoning': reasoning.strip() or content
            }
            
        except Exception as e:
            logger.error(f"Hypothesis generation error: {e}")
            return None
    
    def _generate_validation_script(self, hypothesis: str) -> str:
        """
        Generate Python code to validate the hypothesis.
        
        Args:
            hypothesis: The research hypothesis to test
            
        Returns:
            Python script as string
        """
        prompt = VALIDATION_SCRIPT_PROMPT_TEMPLATE.format(
            hypothesis=hypothesis
        )
        
        try:
            messages = [
                SystemMessage(content="You are an expert Python developer specializing in ML experimentation."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            script = response.content.strip()
            
            # Clean up markdown code fences if present
            if script.startswith('```python'):
                script = script.split('```python')[1]
            if script.endswith('```'):
                script = script.rsplit('```', 1)[0]
            
            return script.strip()
            
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return f"# Error generating validation script: {e}\n# Hypothesis: {hypothesis}"