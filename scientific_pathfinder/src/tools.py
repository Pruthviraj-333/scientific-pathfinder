"""
External tools and utilities for the Scientific Pathfinder.

This module provides:
- Semantic Scholar API integration for paper search (using requests)
- Code execution utilities (if needed)
- Helper functions for data processing
"""

import os
import logging
import requests
import time
from typing import List, Dict, Any, Optional
import tempfile
import pathlib
logger = logging.getLogger(__name__)


class SemanticScholarTool:
    """
    Wrapper for the Semantic Scholar API using direct HTTP requests.
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Semantic Scholar client.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip('"\'')
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})
        self.session.headers.update({"User-Agent": "ScientificPathfinder/1.0"})
        logger.info("✓ Semantic Scholar client initialized")
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        """Helper to make HTTP GET requests with exponential backoff on 429 rate limit."""
        max_retries = 5
        backoff = 4.0
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        sleep_time = backoff * (2.0 ** attempt)
                        logger.warning(f"⚠ Semantic Scholar rate limit hit (429). Retrying in {sleep_time:.1f}s (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(sleep_time)
                        continue
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                # If it's a 429 status inside an exception, retry it
                if e.response is not None and e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        sleep_time = backoff * (2.0 ** attempt)
                        logger.warning(f"⚠ Semantic Scholar rate limit hit (429 exception). Retrying in {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                        continue
                raise e
        
        # If we exhausted retries and still get 429, raise it
        raise requests.exceptions.HTTPError("Exhausted retries for Semantic Scholar 429 Rate Limit")
    
    def search_papers(
        self, 
        query: str, 
        limit: int = 10,
        year_range: Optional[str] = None,
        fields_of_study: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for papers on Semantic Scholar using direct API calls.
        
        Args:
            query: Search query string
            limit: Maximum number of papers to return
            year_range: Optional year filter (e.g., "2020-2023")
            fields_of_study: Optional filter by field (e.g., ["Computer Science"])
            
        Returns:
            List of paper metadata dictionaries
        """
        try:
            logger.info(f"🔍 Searching Semantic Scholar for: '{query}'")
            
            # Build API request
            url = f"{self.BASE_URL}/paper/search"
            params = {
                'query': query,
                'limit': min(limit * 2, 100),  # Request more to filter for abstracts
                'fields': 'paperId,title,abstract,year,authors,citationCount,url,venue,publicationDate'
            }
            
            # Make request with retry helper
            response = self._make_request(url, params=params)
            
            data = response.json()
            results = data.get('data', [])
            
            papers = []
            for paper in results:
                # Skip papers without abstracts
                abstract = paper.get('abstract', '')
                if not abstract or len(abstract.strip()) < 50:
                    continue
                
                # Extract author names
                authors = []
                if paper.get('authors'):
                    authors = [author.get('name', 'Unknown') for author in paper['authors']]
                
                paper_data = {
                    'paper_id': paper.get('paperId', f"unknown_{len(papers)}"),
                    'title': paper.get('title', 'Untitled'),
                    'abstract': abstract,
                    'authors': authors[:5],  # Limit to first 5 authors
                    'year': paper.get('year'),
                    'citation_count': paper.get('citationCount', 0),
                    'url': paper.get('url', f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"),
                    'venue': paper.get('venue'),
                    'publication_date': paper.get('publicationDate')
                }
                
                papers.append(paper_data)
                
                # Stop if we have enough papers with abstracts
                if len(papers) >= limit:
                    break
            
            logger.info(f"✓ Found {len(papers)} papers with abstracts")
            return papers
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e).lower()
            if '403' in error_msg or 'forbidden' in error_msg:
                logger.error("✗ Semantic Scholar API key is invalid or not activated (403 Forbidden)")
                logger.error("   Please check SEMANTIC_SCHOLAR_API_KEY in .env or clear it to use rate-limited public access.")
            elif '429' in error_msg or 'rate limit' in error_msg or 'exhausted retries' in error_msg:
                logger.error("✗ Semantic Scholar rate limit exceeded")
                logger.error("   Solutions:")
                logger.error("   1. Wait 60 seconds and try again")
                logger.error("   2. Add SEMANTIC_SCHOLAR_API_KEY to .env for higher limits")
                logger.error("   3. Reduce max_papers in your query")
            else:
                logger.error(f"✗ API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"✗ Unexpected error during search: {e}")
            return []
    
    def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information about a specific paper using direct API call.
        
        Args:
            paper_id: Semantic Scholar paper ID
            
        Returns:
            Paper metadata dictionary or None if not found
        """
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}"
            params = {
                'fields': 'paperId,title,abstract,year,authors,citationCount,url,venue,referenceCount,citationCount'
            }
            
            response = self._make_request(url, params=params)
            
            paper = response.json()
            
            if not paper:
                return None
            
            authors = []
            if paper.get('authors'):
                authors = [author.get('name', 'Unknown') for author in paper['authors']]
            
            return {
                'paper_id': paper.get('paperId'),
                'title': paper.get('title'),
                'abstract': paper.get('abstract'),
                'authors': authors,
                'year': paper.get('year'),
                'citation_count': paper.get('citationCount', 0),
                'url': paper.get('url'),
                'venue': paper.get('venue'),
                'reference_count': paper.get('referenceCount', 0),
                'citation_count_incoming': paper.get('citationCount', 0)
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.warning(f"Paper {paper_id} not found")
            else:
                logger.error(f"Error fetching paper {paper_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching paper {paper_id}: {e}")
            return None


def format_paper_for_display(paper: Dict[str, Any]) -> str:
    """
    Format a paper dictionary for human-readable display.
    
    Args:
        paper: Paper metadata dictionary
        
    Returns:
        Formatted string representation
    """
    authors_str = ", ".join(paper['authors'][:3])
    if len(paper['authors']) > 3:
        authors_str += f" et al. ({len(paper['authors'])} authors)"
    
    return f"""
📄 {paper['title']}
👥 Authors: {authors_str}
📅 Year: {paper.get('year', 'N/A')}
📊 Citations: {paper.get('citation_count', 0)}
🔗 {paper.get('url', '')}

Abstract (first 200 chars):
{paper['abstract'][:200]}...
""".strip()


def extract_keywords_from_abstract(abstract: str) -> List[str]:
    """
    Simple keyword extraction from abstract using common ML terms.
    This is a fallback if the LLM extraction fails.
    
    Args:
        abstract: Paper abstract text
        
    Returns:
        List of potential keywords found
    """
    # Common ML/AI keywords to look for
    method_keywords = [
        'transformer', 'bert', 'gpt', 'lstm', 'cnn', 'resnet', 'vit',
        'attention', 'gan', 'vae', 'diffusion', 'reinforcement learning',
        'neural network', 'deep learning', 'machine learning'
    ]
    
    dataset_keywords = [
        'imagenet', 'coco', 'mnist', 'cifar', 'glue', 'squad', 'wikitext',
        'openwebtext', 'conceptual captions', 'laion'
    ]
    
    metric_keywords = [
        'accuracy', 'precision', 'recall', 'f1', 'auc', 'bleu', 'rouge',
        'perplexity', 'loss', 'error rate', 'map', 'iou'
    ]
    
    abstract_lower = abstract.lower()
    
    found_keywords = []
    for keyword in method_keywords + dataset_keywords + metric_keywords:
        if keyword in abstract_lower:
            found_keywords.append(keyword.title())
    
    return list(set(found_keywords))  # Remove duplicates


def validate_paper_metadata(paper: Dict[str, Any]) -> bool:
    """
    Check if paper metadata has minimum required fields.
    
    Args:
        paper: Paper metadata dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['paper_id', 'title', 'abstract']
    
    for field in required_fields:
        if field not in paper or not paper[field]:
            logger.warning(f"Paper missing required field: {field}")
            return False
    
    # Check abstract length
    if len(paper['abstract'].strip()) < 50:
        logger.warning("Abstract too short (< 50 characters)")
        return False
    
    return True


class CodeExecutor:
    """
    Utility for safely executing generated Python code.
    NOTE: This is a placeholder. In production, use sandboxed execution.
    """
    
    @staticmethod
    def save_script(code: str, filename: str = "hypothesis_validation.py") -> str:
        """
        Save generated code to a file.
        
        Args:
            code: Python code to save
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        # Use current directory or temp directory that works cross-platform
        
        
        # Try current directory first
        try:
            output_path = pathlib.Path.cwd() / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.info(f"✓ Script saved to {output_path}")
            return str(output_path)
        except Exception:
            # Fallback to temp directory
            try:
                temp_dir = pathlib.Path(tempfile.gettempdir())
                output_path = temp_dir / filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                logger.info(f"✓ Script saved to {output_path}")
                return str(output_path)
            except Exception as e2:
                logger.error(f"✗ Failed to save script: {e2}")
                return ""
    
    @staticmethod
    def validate_syntax(code: str) -> tuple[bool, str]:
        """
        Check if Python code has valid syntax.
        
        Args:
            code: Python code to validate
            
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            compile(code, '<string>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"