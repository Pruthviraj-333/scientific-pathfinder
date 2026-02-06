# 🔬 Scientific Pathfinder

> An autonomous research agent that discovers hidden connections in scientific literature using Knowledge Graphs and LLMs.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0+-red.svg)](https://neo4j.com/)

## 📋 Overview

The Scientific Pathfinder is an agentic AI system that:

1. **🔍 Searches** scientific papers on Semantic Scholar
2. **🗺️ Maps** research into a Neo4j Knowledge Graph
3. **💡 Discovers** structural holes and research gaps
4. **🧪 Proposes** novel, testable hypotheses

### The Three Agents

```
┌─────────────┐      ┌──────────────┐      ┌──────────┐
│  Librarian  │ ───▶ │ Cartographer │ ───▶ │ Scientist│
└─────────────┘      └──────────────┘      └──────────┘
  Search Papers        Build Graph         Find Gaps
  Extract Entities     Structure Data      Create Hypothesis
```

- **Librarian**: Searches Semantic Scholar, extracts Methods/Datasets/Metrics using Groq's Llama 3.3
- **Cartographer**: Constructs a Neo4j Knowledge Graph with papers, authors, and relationships
- **Scientist**: Performs GraphRAG to identify research gaps and generate novel hypotheses

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Groq API (`llama-3.3-70b-versatile`) |
| **Orchestration** | LangGraph (stateful workflows) |
| **Database** | Neo4j (Aura Free Tier) |
| **Data Source** | Semantic Scholar API |
| **Language** | Python 3.10+ |

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [Groq API key](https://console.groq.com/keys) (free tier available)
- [Neo4j Aura](https://neo4j.com/cloud/aura/) account (free tier available)
- (Optional) [Semantic Scholar API key](https://www.semanticscholar.org/product/api)

### Installation

1. **Clone and navigate to the project:**
```bash
cd scientific_pathfinder
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.template .env
# Edit .env with your actual API keys
```

Your `.env` should look like:
```ini
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
SEMANTIC_SCHOLAR_API_KEY=optional_key
```

### Running the Agent

```bash
python main.py
```

This will:
1. Search for papers on "vision transformers for medical image classification"
2. Extract entities and build a knowledge graph
3. Identify research gaps
4. Generate a hypothesis with validation code

## 📁 Project Structure

```
scientific_pathfinder/
├── .env                      # API keys (DO NOT COMMIT)
├── .env.template             # Template for environment variables
├── main.py                   # Entry point - LangGraph orchestrator
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── src/
│   ├── __init__.py
│   ├── state.py              # GraphState definition (TypedDict)
│   ├── agents.py             # Librarian, Cartographer, Scientist
│   ├── graph_db.py           # Neo4j connection & Cypher queries
│   └── tools.py              # Semantic Scholar integration
│
└── prompts/
    ├── __init__.py
    └── system_prompts.py     # LLM prompts for each agent
```

## 🔧 Usage Examples

### Basic Usage

```python
from main import ScientificPathfinder
from dotenv import load_dotenv
import os

load_dotenv()

pathfinder = ScientificPathfinder(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    neo4j_uri=os.getenv("NEO4J_URI"),
    neo4j_username=os.getenv("NEO4J_USERNAME"),
    neo4j_password=os.getenv("NEO4J_PASSWORD")
)

# Run research
final_state = pathfinder.run(
    research_topic="graph neural networks for drug discovery",
    max_papers=15,
    save_script=True
)

# Access results
print(final_state['final_hypothesis'])
print(final_state['validation_script'])
```

### Customizing the Workflow

Modify `main.py` to change research topics:

```python
research_topics = [
    "vision transformers for medical imaging",
    "reinforcement learning for robot manipulation",
    "few-shot learning with large language models"
]
```

### Querying the Knowledge Graph

```python
from src.graph_db import get_neo4j_client

db = get_neo4j_client()

# Find isolated methods
isolated = db.find_isolated_nodes('Method')
print(f"Found {len(isolated)} unused methods")

# Find rare combinations
gaps = db.find_rare_combinations()
for gap in gaps:
    print(f"{gap['method']} + {gap['dataset']}: used {gap['usage_count']} times")

# Get statistics
stats = db.get_graph_stats()
print(stats)
```

## 🧠 How It Works

### 1. The Librarian Agent

```python
# Searches Semantic Scholar
papers = search_tool.search_papers(
    query="vision transformers",
    limit=10
)

# Extracts entities with Groq LLM
entities = llm.invoke([
    SystemMessage(LIBRARIAN_SYSTEM_PROMPT),
    HumanMessage(f"Extract methods/datasets from: {abstract}")
])
# Returns: {"methods": ["ViT", "BERT"], "datasets": ["ImageNet"], ...}
```

### 2. The Cartographer Agent

```python
# Builds Neo4j graph
MERGE (p:Paper {paper_id: $paper_id})
SET p.title = $title, p.abstract = $abstract

MERGE (m:Method {name: $method})
MERGE (p)-[:USES_METHOD]->(m)

MERGE (d:Dataset {name: $dataset})
MERGE (p)-[:USES_DATASET]->(d)
```

### 3. The Scientist Agent

```python
# Finds structural holes
isolated_nodes = db.find_isolated_nodes('Method')
rare_combos = db.find_rare_combinations()

# Generates hypothesis with LLM
hypothesis = llm.invoke([
    SystemMessage(SCIENTIST_SYSTEM_PROMPT),
    HumanMessage(f"Analyze these gaps: {gaps}")
])

# Creates validation script
script = llm.invoke([
    HumanMessage(f"Generate Python code to test: {hypothesis}")
])
```

## 📊 Example Output

```
🔬 RESEARCH TOPIC: vision transformers for medical image classification
====================================================================

📚 Papers analyzed: 10
🗺️  Graph statistics:
   - Papers: 10
   - Authors: 47
   - Methods: 12
   - Datasets: 8
   - Metrics: 15
   - Relationships: 145

🔍 Research gaps found: 5

💡 HYPOTHESIS:
Vision Transformers (ViT) show strong performance on natural images but remain 
underexplored on medical imaging datasets like ChestX-ray14 and PatchCamelyon. 
Given ViT's attention mechanism can capture long-range dependencies, applying 
it to histopathology images could improve cancer detection accuracy compared 
to traditional CNNs.

📝 REASONING:
The knowledge graph reveals that while ViT is frequently tested on ImageNet, 
only 1 paper in our corpus applies it to medical imaging. This represents a 
significant research gap, as medical images have unique characteristics 
(grayscale, high resolution, subtle features) that could benefit from 
transformer architectures.

✅ Validation script saved to: validation_vision_transformers_for_.py
```

## 🐛 Troubleshooting

### "Failed to connect to Neo4j"
- Ensure your Neo4j Aura instance is running
- Check that `NEO4J_URI` starts with `neo4j+s://` (not `bolt://`)
- Verify credentials in `.env`

### "Rate limit exceeded" on Semantic Scholar
- Add `SEMANTIC_SCHOLAR_API_KEY` to `.env` for higher limits
- Reduce `max_papers` parameter

### "Groq API error"
- Check your API key is valid
- Ensure you have quota remaining (free tier: 30 requests/minute)

## 🔒 Security Notes

- **Never commit `.env` to version control**
- Add `.env` to your `.gitignore`
- Rotate API keys if accidentally exposed

## 📚 Advanced Features

### Custom Agents

Add new agents by subclassing and registering in the graph:

```python
class ReviewerAgent:
    def __call__(self, state: GraphState) -> StateUpdate:
        # Your logic here
        return {'current_step': 'next_agent'}

workflow.add_node("reviewer", ReviewerAgent())
workflow.add_edge("scientist", "reviewer")
```

### Custom Gap Analysis

Extend `Neo4jGraphDB` with custom queries:

```python
def find_trending_methods(self) -> List[Dict]:
    cypher = """
    MATCH (p:Paper)-[:USES_METHOD]->(m:Method)
    WHERE p.year >= 2023
    RETURN m.name, COUNT(p) as usage
    ORDER BY usage DESC
    LIMIT 10
    """
    return self.execute_cypher(cypher)
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional data sources (arXiv, PubMed)
- More sophisticated gap analysis algorithms
- Hypothesis validation pipeline
- Web interface for exploration

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [Semantic Scholar](https://www.semanticscholar.org/) for paper data
- [Groq](https://groq.com/) for ultra-fast LLM inference
- [Neo4j](https://neo4j.com/) for graph database
- [LangChain](https://www.langchain.com/) for LangGraph framework

---

**Built with ❤️ for researchers exploring the frontiers of science**