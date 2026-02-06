"""
Neo4j Knowledge Graph Database Interface.

This module handles all interactions with the Neo4j database, including:
- Connection management
- Schema creation
- Paper/entity upsertion
- Gap analysis queries
"""

import os
import ssl
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, exceptions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jGraphDB:
    """
    Handles all Neo4j database operations for the Scientific Pathfinder.
    """
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)
            username: Database username
            password: Database password
        """
        self.original_uri = uri
        self.username = username
        self.password = password
        self.driver = None
        
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database with SSL fallback.
        
        Returns:
            True if connection successful, False otherwise
        """
        uri = self.original_uri
        
        # Remove /neo4j suffix if present
        if uri.endswith("/neo4j"):
            uri = uri.rstrip("/neo4j")
        
        # If using bolt:// (plain), we need to enable encryption manually with SSL context
        if uri.startswith("bolt://"):
            logger.info(f"Detected bolt:// URI, using encrypted connection with SSL workaround...")
            
            try:
                # Create SSL context that doesn't verify certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                self.driver = GraphDatabase.driver(
                    uri,
                    auth=(self.username, self.password),
                    encrypted=True,  # Enable encryption
                    ssl_context=ssl_context,  # Custom SSL context
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50
                )
                
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1").consume()
                
                logger.info(f"✓ Connected to Neo4j at {uri}")
                logger.info(f"  Using SSL workaround for Windows certificate issues")
                return True
                
            except Exception as e:
                logger.error(f"✗ Failed to connect with bolt:// + SSL: {e}")
                self.driver = None
                return False
        
        # For neo4j+s:// or bolt+s://, try standard connection first
        try:
            logger.info(f"Attempting connection to {uri}...")
            self.driver = GraphDatabase.driver(
                uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=120
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1").consume()
            logger.info(f"✓ Connected to Neo4j at {uri}")
            return True
            
        except (exceptions.ServiceUnavailable, ssl.SSLError, OSError) as e:
            error_msg = str(e).lower()
            
            # Check if it's an SSL certificate issue
            if 'ssl' in error_msg or 'certificate' in error_msg or 'cert' in error_msg:
                logger.warning(f"⚠ SSL certificate verification failed, trying workaround...")
                
                try:
                    # Convert to bolt:// (not bolt+s://) to allow custom SSL
                    bolt_uri = uri.replace("bolt+s://", "bolt://").replace("neo4j+s://", "bolt://")
                    logger.info(f"Using bolt:// with custom SSL context: {bolt_uri}")
                    
                    # Create SSL context that doesn't verify certificates
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    self.driver = GraphDatabase.driver(
                        bolt_uri,
                        auth=(self.username, self.password),
                        encrypted=True,  # Enable encryption
                        ssl_context=ssl_context,  # Custom SSL context
                        max_connection_lifetime=3600,
                        max_connection_pool_size=50
                    )
                    
                    # Test connection
                    with self.driver.session() as session:
                        session.run("RETURN 1").consume()
                    
                    logger.info(f"✓ Connected to Neo4j with SSL workaround")
                    logger.info(f"  Note: Using unverified SSL (OK for development/Aura)")
                    return True
                    
                except Exception as ssl_error:
                    logger.error(f"✗ SSL workaround also failed: {ssl_error}")
                    self.driver = None
                    return False
            else:
                logger.error(f"✗ Failed to connect to Neo4j: {e}")
                logger.error(f"   Troubleshooting:")
                logger.error(f"   1. Check your Neo4j instance is running in Aura console")
                logger.error(f"   2. Verify password is correct")
                logger.error(f"   3. Try pausing and resuming the instance")
            logger.error(f"   4. Check firewall/network connectivity")
            return False
        except exceptions.AuthError as e:
            logger.error(f"✗ Neo4j authentication failed: {e}")
            logger.error(f"   Check your NEO4J_USERNAME and NEO4J_PASSWORD in .env")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error connecting to Neo4j: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_schema(self):
        """
        Create indexes and constraints for optimal performance.
        """
        schema_queries = [
            # Unique constraints (also create indexes)
            "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
            "CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT metric_name IF NOT EXISTS FOR (mt:Metric) REQUIRE mt.name IS UNIQUE",
            
            # Additional indexes for common queries
            "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
            "CREATE INDEX paper_citations IF NOT EXISTS FOR (p:Paper) ON (p.citation_count)",
        ]
        
        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    logger.info(f"✓ Executed: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Schema query warning: {e}")
    
    def upsert_paper_to_graph(self, paper_data: Dict[str, Any]) -> bool:
        """
        Insert or update a paper and its related entities in the graph.
        
        Expected paper_data structure:
        {
            "paper_id": "abc123",
            "title": "Paper Title",
            "abstract": "Abstract text...",
            "authors": ["Author 1", "Author 2"],
            "year": 2023,
            "citation_count": 42,
            "url": "https://...",
            "entities": {
                "methods": ["BERT", "Transformer"],
                "datasets": ["ImageNet", "COCO"],
                "metrics": ["Accuracy", "F1-Score"]
            }
        }
        
        Args:
            paper_data: Structured paper information with entities
            
        Returns:
            True if successful, False otherwise
        """
        cypher = """
        // Create Paper node
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title,
            p.abstract = $abstract,
            p.year = $year,
            p.citation_count = $citation_count,
            p.url = $url,
            p.updated_at = datetime()
        
        // Create Author nodes and relationships
        WITH p
        UNWIND $authors AS author_name
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:AUTHORED]->(p)
        
        // Create Method nodes and relationships
        WITH p
        UNWIND $methods AS method_name
        MERGE (m:Method {name: method_name})
        MERGE (p)-[:USES_METHOD]->(m)
        
        // Create Dataset nodes and relationships
        WITH p
        UNWIND $datasets AS dataset_name
        MERGE (d:Dataset {name: dataset_name})
        MERGE (p)-[:USES_DATASET]->(d)
        
        // Create Metric nodes and relationships
        WITH p
        UNWIND $metrics AS metric_name
        MERGE (mt:Metric {name: metric_name})
        MERGE (p)-[:MEASURES_WITH]->(mt)
        
        RETURN p.paper_id as inserted_paper
        """
        
        params = {
            "paper_id": paper_data.get("paper_id", "unknown"),
            "title": paper_data.get("title", "Untitled"),
            "abstract": paper_data.get("abstract", "")[:5000],  # Limit length
            "year": paper_data.get("year"),
            "citation_count": paper_data.get("citation_count", 0),
            "url": paper_data.get("url", ""),
            "authors": paper_data.get("authors", []),
            "methods": paper_data.get("entities", {}).get("methods", []),
            "datasets": paper_data.get("entities", {}).get("datasets", []),
            "metrics": paper_data.get("entities", {}).get("metrics", []),
        }
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params)
                record = result.single()
                if record:
                    logger.info(f"✓ Upserted paper: {params['title'][:50]}...")
                    return True
                return False
        except Exception as e:
            logger.error(f"✗ Failed to upsert paper: {e}")
            return False
    
    def execute_cypher(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a raw Cypher query.
        
        Args:
            query: Cypher query string
            params: Optional parameters for the query
            
        Returns:
            List of result records as dictionaries
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"✗ Cypher execution failed: {e}")
            return []
    
    def find_isolated_nodes(self, node_type: str = "Method") -> List[Dict[str, Any]]:
        """
        Find nodes with no incoming or outgoing relationships (structural holes).
        
        Args:
            node_type: The type of node to search for (Method, Dataset, Metric)
            
        Returns:
            List of isolated nodes with their properties
        """
        cypher = f"""
        MATCH (n:{node_type})
        WHERE NOT (n)--()
        RETURN n.name as name, labels(n) as type, properties(n) as props
        LIMIT 20
        """
        return self.execute_cypher(cypher)
    
    def find_rare_combinations(self) -> List[Dict[str, Any]]:
        """
        Find methods that are rarely combined with certain datasets.
        This identifies potential research gaps.
        
        Returns:
            List of underexplored method-dataset combinations
        """
        cypher = """
        // Find all possible method-dataset pairs
        MATCH (m:Method), (d:Dataset)
        OPTIONAL MATCH path = (p:Paper)-[:USES_METHOD]->(m)
        WITH m, d, 
             SIZE([(p)-[:USES_METHOD]->(m) WHERE (p)-[:USES_DATASET]->(d) | p]) as usage_count
        WHERE usage_count <= 1
        RETURN m.name as method, 
               d.name as dataset, 
               usage_count,
               'rare_combination' as gap_type
        ORDER BY usage_count ASC
        LIMIT 15
        """
        return self.execute_cypher(cypher)
    
    def find_disconnected_communities(self) -> List[Dict[str, Any]]:
        """
        Find clusters of papers that don't cite each other or share entities.
        
        Returns:
            List of disconnected research communities
        """
        cypher = """
        MATCH (p1:Paper)-[:USES_METHOD]->(m:Method)<-[:USES_METHOD]-(p2:Paper)
        WHERE p1 <> p2
        WITH m.name as method, 
             COUNT(DISTINCT p1) as paper_count,
             COLLECT(DISTINCT p1.title)[0..3] as sample_papers
        WHERE paper_count >= 2
        RETURN method, paper_count, sample_papers
        ORDER BY paper_count DESC
        LIMIT 10
        """
        return self.execute_cypher(cypher)
    
    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get overall statistics about the knowledge graph.
        
        Returns:
            Dictionary with node and relationship counts
        """
        stats = {}
        
        # Count nodes by type
        node_types = ["Paper", "Author", "Method", "Dataset", "Metric"]
        for node_type in node_types:
            result = self.execute_cypher(f"MATCH (n:{node_type}) RETURN COUNT(n) as count")
            stats[f"{node_type.lower()}_count"] = result[0]["count"] if result else 0
        
        # Count relationships
        rel_query = "MATCH ()-[r]->() RETURN COUNT(r) as count"
        result = self.execute_cypher(rel_query)
        stats["relationship_count"] = result[0]["count"] if result else 0
        
        return stats
    
    def clear_database(self):
        """
        WARNING: Delete all nodes and relationships. Use only for testing.
        """
        cypher = "MATCH (n) DETACH DELETE n"
        try:
            with self.driver.session() as session:
                session.run(cypher)
                logger.warning("⚠ Database cleared!")
        except Exception as e:
            logger.error(f"✗ Failed to clear database: {e}")


def get_neo4j_client() -> Neo4jGraphDB:
    """
    Factory function to create a Neo4j client from environment variables.
    
    Returns:
        Connected Neo4jGraphDB instance
    """
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not all([uri, password]):
        raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set in .env")
    
    client = Neo4jGraphDB(uri, username, password)
    if not client.connect():
        raise ConnectionError("Failed to connect to Neo4j")
    
    return client