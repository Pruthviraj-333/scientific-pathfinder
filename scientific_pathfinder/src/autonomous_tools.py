"""
Autonomous Tools for Scientific Pathfinder Agents

These tools are available to autonomous agents who decide which ones to use
based on the research context and their reasoning.
"""

from langchain.tools import tool
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# SEARCH TOOLS - Multiple sources for agent to choose from
# ============================================================================

@tool
def search_semantic_scholar(query: str, max_results: int = 10) -> List[Dict]:
    """Search Semantic Scholar for academic papers.
    
    Use this tool when you need peer-reviewed academic papers from any field.
    Semantic Scholar has broad coverage across all disciplines.
    
    Args:
        query: Research topic or keywords to search for
        max_results: Maximum number of papers to return (default 10)
    
    Returns:
        List of papers with title, abstract, authors, year, citations, url
    """
    from src.tools import SemanticScholarTool
    
    logger.info(f"🔍 Tool: search_semantic_scholar(query='{query}', max={max_results})")
    
    try:
        tool = SemanticScholarTool()
        papers = tool.search_papers(query, limit=max_results)
        
        logger.info(f"✓ Found {len(papers)} papers from Semantic Scholar")
        return papers
    
    except Exception as e:
        logger.error(f"✗ Semantic Scholar search failed: {e}")
        return []


@tool
def search_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search arXiv for preprint papers.
    
    Use this tool for cutting-edge research in physics, math, CS, and related fields.
    arXiv has the latest preprints before formal publication.
    
    Args:
        query: Research topic or keywords to search for
        max_results: Maximum number of papers to return (default 10)
    
    Returns:
        List of papers with title, abstract, authors, year, url
    """
    import arxiv
    
    logger.info(f"🔍 Tool: search_arxiv(query='{query}', max={max_results})")
    
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        papers = []
        for result in search.results():
            papers.append({
                'paper_id': result.entry_id.split('/')[-1],
                'title': result.title,
                'abstract': result.summary,
                'authors': [author.name for author in result.authors],
                'year': result.published.year,
                'citation_count': 0,  # arXiv doesn't provide citations
                'url': result.entry_id,
                'venue': 'arXiv',
                'source': 'arxiv'
            })
        
        logger.info(f"✓ Found {len(papers)} papers from arXiv")
        return papers
    
    except Exception as e:
        logger.error(f"✗ arXiv search failed: {e}")
        return []


@tool
def validate_paper_quality(paper: Dict, min_citations: int = 5, min_year: int = 2015) -> bool:
    """Validate if a paper meets quality standards.
    
    Use this tool to filter out low-quality or outdated papers before processing.
    Saves time by not extracting entities from poor papers.
    
    Args:
        paper: Paper dictionary with metadata
        min_citations: Minimum citation count required (default 5)
        min_year: Papers must be from this year or later (default 2015)
    
    Returns:
        True if paper passes quality check, False otherwise
    """
    logger.info(f"🔍 Tool: validate_paper_quality('{paper.get('title', 'Unknown')[:50]}...')")
    
    try:
        # Check year
        year = paper.get('year', 0)
        if year < min_year:
            logger.info(f"✗ Paper too old: {year} < {min_year}")
            return False
        
        # Check citations (skip for very recent papers)
        citations = paper.get('citation_count', 0)
        current_year = datetime.now().year
        
        if year < current_year - 1:  # Not brand new
            if citations < min_citations:
                logger.info(f"✗ Low citations: {citations} < {min_citations}")
                return False
        
        # Check has abstract
        if not paper.get('abstract'):
            logger.info(f"✗ No abstract available")
            return False
        
        logger.info(f"✓ Paper passed quality check")
        return True
    
    except Exception as e:
        logger.error(f"✗ Validation error: {e}")
        return False


# ============================================================================
# ENTITY EXTRACTION TOOLS
# ============================================================================

@tool
def extract_entities_from_paper(paper_text: str, paper_title: str = "") -> Dict:
    """Extract methods, datasets, and metrics from paper text using LLM.
    
    Use this tool to identify key entities (methods, datasets, metrics) from a paper.
    This is essential for building the knowledge graph.
    
    Args:
        paper_text: Abstract or full text of the paper
        paper_title: Title of the paper (helps with context)
    
    Returns:
        Dictionary with 'methods', 'datasets', 'metrics' lists
    """
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, SystemMessage
    import os
    import json
    
    logger.info(f"🔍 Tool: extract_entities_from_paper('{paper_title[:50]}...')")
    
    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )
        
        prompt = f"""Extract key entities from this research paper.

Title: {paper_title}

Abstract/Text:
{paper_text}

Return a JSON object with these fields:
- methods: List of AI/ML methods, algorithms, architectures mentioned
- datasets: List of datasets, benchmarks, data sources used
- metrics: List of evaluation metrics, performance measures

Be comprehensive but precise. Only include clearly mentioned items.

Return ONLY valid JSON, no explanation."""

        response = llm.invoke([
            SystemMessage(content="You are a research paper analyzer. Extract entities as JSON."),
            HumanMessage(content=prompt)
        ])
        
        # Parse JSON response
        content = response.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        
        entities = json.loads(content.strip())
        
        logger.info(f"✓ Extracted: {len(entities.get('methods', []))} methods, "
                   f"{len(entities.get('datasets', []))} datasets, "
                   f"{len(entities.get('metrics', []))} metrics")
        
        return entities
    
    except Exception as e:
        logger.error(f"✗ Entity extraction failed: {e}")
        return {'methods': [], 'datasets': [], 'metrics': []}


# ============================================================================
# KNOWLEDGE GRAPH TOOLS
# ============================================================================

@tool
def insert_paper_to_graph(paper: Dict, entities: Dict, session_id: str = "") -> str:
    """Insert a paper and its entities into the Neo4j knowledge graph.
    
    Use this tool after extracting entities to build the knowledge graph.
    Creates paper node and relationships to methods, datasets, metrics.
    
    Args:
        paper: Paper metadata dictionary
        entities: Extracted entities (methods, datasets, metrics)
        session_id: Optional session identifier
    
    Returns:
        Success message with paper ID
    """
    from src.graph_db import Neo4jGraphDB
    import os
    
    logger.info(f"🔍 Tool: insert_paper_to_graph('{paper.get('title', '')[:50]}...')")
    
    try:
        # Connect to Neo4j
        db = Neo4jGraphDB(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        
        if not db.connect():
            return "Failed to connect to Neo4j"
        
        # Insert paper
        paper_id = db.upsert_paper(paper)
        
        # Insert entities and relationships
        for method in entities.get('methods', []):
            db.upsert_method(method, paper_id)
        
        for dataset in entities.get('datasets', []):
            db.upsert_dataset(dataset, paper_id)
        
        for metric in entities.get('metrics', []):
            db.upsert_metric(metric, paper_id)
        
        db.close()
        
        logger.info(f"✓ Inserted paper {paper_id} with entities to graph")
        return f"Successfully inserted paper: {paper_id}"
    
    except Exception as e:
        logger.error(f"✗ Graph insertion failed: {e}")
        return f"Failed to insert paper: {str(e)}"


@tool
def query_graph_for_gaps(analysis_type: str = "rare_combinations") -> List[Dict]:
    """Query the knowledge graph to find research gaps.
    
    Use this tool to analyze the knowledge graph for unexplored areas.
    Different analysis types reveal different kinds of gaps.
    
    Args:
        analysis_type: Type of analysis - 'rare_combinations', 'isolated_nodes', 
                      'emerging_topics', or 'citation_patterns'
    
    Returns:
        List of identified gaps with details
    """
    from src.graph_db import Neo4jGraphDB
    import os
    
    logger.info(f"🔍 Tool: query_graph_for_gaps(type='{analysis_type}')")
    
    try:
        db = Neo4jGraphDB(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        
        if not db.connect():
            return []
        
        if analysis_type == "rare_combinations":
            gaps = db.find_rare_combinations(limit=15)
        elif analysis_type == "isolated_nodes":
            gaps = db.find_isolated_nodes('Method')
        else:
            gaps = db.find_rare_combinations(limit=15)  # Default
        
        db.close()
        
        logger.info(f"✓ Found {len(gaps)} gaps using {analysis_type}")
        return gaps
    
    except Exception as e:
        logger.error(f"✗ Gap analysis failed: {e}")
        return []


@tool
def get_graph_statistics() -> Dict:
    """Get current knowledge graph statistics.
    
    Use this tool to understand the current state of the knowledge graph
    before deciding on analysis strategy.
    
    Returns:
        Dictionary with counts of papers, methods, datasets, metrics, relationships
    """
    from src.graph_db import Neo4jGraphDB
    import os
    
    logger.info(f"🔍 Tool: get_graph_statistics()")
    
    try:
        db = Neo4jGraphDB(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        
        if not db.connect():
            return {}
        
        stats = db.get_graph_stats()
        db.close()
        
        logger.info(f"✓ Graph stats: {stats.get('paper_count', 0)} papers, "
                   f"{stats.get('method_count', 0)} methods")
        
        return stats
    
    except Exception as e:
        logger.error(f"✗ Stats retrieval failed: {e}")
        return {}


# ============================================================================
# HYPOTHESIS GENERATION TOOLS
# ============================================================================

@tool
def generate_research_hypothesis(gaps: List[Dict], research_topic: str, context: str = "") -> Dict:
    """Generate a research hypothesis based on identified gaps.
    
    Use this tool to create a novel, testable hypothesis from research gaps.
    The LLM will reason about the gaps and propose innovative research directions.
    
    Args:
        gaps: List of identified research gaps
        research_topic: Original research topic
        context: Additional context about the research domain
    
    Returns:
        Dictionary with 'hypothesis' and 'reasoning' fields
    """
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, SystemMessage
    import os
    import json
    
    logger.info(f"🔍 Tool: generate_research_hypothesis(gaps={len(gaps)})")
    
    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )
        
        gaps_text = json.dumps(gaps[:10], indent=2)
        
        prompt = f"""Based on the research gaps identified, generate a novel research hypothesis.

Research Topic: {research_topic}

Identified Gaps:
{gaps_text}

{context}

Generate a hypothesis that:
1. Is novel and unexplored based on the gaps
2. Is testable and feasible
3. Has potential for significant impact
4. Combines existing methods/datasets in new ways

Return a JSON object with:
- hypothesis: The research hypothesis (2-3 sentences)
- reasoning: Why this hypothesis is valuable and feasible (3-4 sentences)

Return ONLY valid JSON."""

        response = llm.invoke([
            SystemMessage(content="You are an expert research scientist proposing novel hypotheses."),
            HumanMessage(content=prompt)
        ])
        
        content = response.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        
        result = json.loads(content.strip())
        
        logger.info(f"✓ Generated hypothesis: {result.get('hypothesis', '')[:100]}...")
        return result
    
    except Exception as e:
        logger.error(f"✗ Hypothesis generation failed: {e}")
        return {
            'hypothesis': 'Failed to generate hypothesis',
            'reasoning': str(e)
        }


@tool  
def create_validation_script(hypothesis: str, research_topic: str) -> str:
    """Create a Python validation script to test the hypothesis.
    
    Use this tool to generate executable code that researchers can use
    to validate the proposed hypothesis.
    
    Args:
        hypothesis: The research hypothesis to validate
        research_topic: Original research topic for context
    
    Returns:
        Python script as a string
    """
    logger.info(f"🔍 Tool: create_validation_script()")
    
    template = f'''"""
Validation Script for Research Hypothesis
Generated by Scientific Pathfinder - Autonomous Agent System

Research Topic: {research_topic}
Hypothesis: {hypothesis}
Generated: {datetime.now().isoformat()}
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

# TODO: Implement the hypothesis validation experiments
# This is a template - customize based on your specific hypothesis

def validate_hypothesis():
    """
    Main validation function.
    
    Steps:
    1. Load the datasets mentioned in the hypothesis
    2. Implement or load the methods/models
    3. Run experiments with proper train/test splits
    4. Collect and analyze metrics
    5. Compare with baseline approaches
    """
    print("="*60)
    print("Hypothesis Validation Experiment")
    print("="*60)
    print(f"Topic: {research_topic}")
    print(f"Hypothesis: {hypothesis}")
    print("="*60)
    
    # TODO: Load your dataset here
    # dataset = load_dataset(...)
    
    # TODO: Initialize your model/method
    # model = YourModel(...)
    
    # TODO: Training loop
    # for epoch in range(num_epochs):
    #     train(model, train_loader)
    #     evaluate(model, val_loader)
    
    # TODO: Final evaluation
    # results = test(model, test_loader)
    
    print("Validation complete!")
    return None

if __name__ == "__main__":
    validate_hypothesis()
'''
    
    logger.info(f"✓ Created validation script template")
    return template


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@tool
def merge_paper_lists(paper_lists: List[List[Dict]], max_total: int = 10) -> List[Dict]:
    """Merge multiple paper lists, removing duplicates and limiting total count.
    
    Use this tool when you've searched multiple sources and need to combine results.
    
    Args:
        paper_lists: List of paper lists from different sources
        max_total: Maximum total papers to return
    
    Returns:
        Merged list of unique papers
    """
    logger.info(f"🔍 Tool: merge_paper_lists(lists={len(paper_lists)}, max={max_total})")
    
    seen = set()
    merged = []
    
    for papers in paper_lists:
        for paper in papers:
            paper_id = paper.get('paper_id', paper.get('title', ''))
            if paper_id and paper_id not in seen:
                seen.add(paper_id)
                merged.append(paper)
                
                if len(merged) >= max_total:
                    logger.info(f"✓ Merged {len(merged)} unique papers")
                    return merged
    
    logger.info(f"✓ Merged {len(merged)} unique papers")
    return merged


# Export all tools
ALL_TOOLS = [
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
]