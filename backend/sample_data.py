"""
Sample memory data for demonstration purposes.
This simulates what would be retrieved from Neo4j and Milvus.
"""
from typing import List, Dict
from models import Memory


# Sample graph memories (from Neo4j)
SAMPLE_GRAPH_MEMORIES: List[Dict] = [
    {
        "id": "N1001",
        "type": "node",
        "node_type": "AgentAnswer",
        "content": "Transformer-based language model shows strong performance with 15% improvement over baseline. Accuracy improved by 8% after adjusting for data leakage.",
        "tags": ["transformer", "language_model", "performance", "accuracy", "benchmark"],
        "metadata": {
            "conv_id": "2025-09-12_Model_Evaluation_01",
            "ingestion_time": "2025-09-12T10:30:00Z",
            "metrics": ["accuracy", "performance_improvement"]
        }
    },
    {
        "id": "N1002",
        "type": "node",
        "node_type": "UserPreference",
        "content": "Research team prefers clear visualizations with detailed methodology sections in paper presentations.",
        "tags": ["preference", "visualization", "research", "presentation"],
        "metadata": {
            "user_role": "Research Team",
            "preference_type": "presentation_style"
        }
    },
    {
        "id": "N1003",
        "type": "node",
        "node_type": "AgentAction",
        "content": "Merged training dataset with validation set using 'sample_id' as the join key. Filtered out contaminated samples before evaluation.",
        "tags": ["methodology", "data_merge", "evaluation"],
        "metadata": {
            "status": "complete",
            "parameter_field": "SELECT * FROM training JOIN validation ON training.sample_id = validation.sample_id WHERE is_contaminated = false"
        }
    },
    {
        "id": "N1004",
        "type": "node",
        "node_type": "Event",
        "content": "Dataset quality issue affected model training between July-August 2025, causing a 12% reduction in accuracy due to label noise.",
        "tags": ["event", "dataset", "quality", "training"],
        "metadata": {
            "source_type": "Data Quality Issue",
            "start_date": "2025-07-15",
            "end_date": "2025-08-20"
        }
    },
    {
        "id": "N1005",
        "type": "node",
        "node_type": "DataSource",
        "content": "GLUE Benchmark Results Dashboard - contains evaluation metrics and performance comparisons for transformer models.",
        "tags": ["datasource", "benchmark", "glue", "evaluation"],
        "metadata": {
            "source_type": "benchmark",
            "doc_pointer": "/benchmarks/glue_results_2025.json",
            "relevant_parts": "Performance Metrics Tab, Section 4-7"
        }
    },
    {
        "id": "P2001",
        "type": "path",
        "content": "User asked about model performance → Agent retrieved benchmark data → Merged with training data using sample_id → Concluded accuracy improved after filtering contaminated samples",
        "tags": ["performance", "analysis", "methodology"],
        "metadata": {
            "nodes": ["N1001", "N1003"],
            "edge_text": "Used methodology to arrive at conclusion"
        }
    }
]


# Sample reasoning bank memories (from Milvus)
SAMPLE_REASONING_MEMORIES: List[Dict] = [
    {
        "id": "RB-01",
        "type": "reasoning",
        "content": "Never evaluate model performance without first adjusting for data leakage and test set contamination. These factors can skew metrics by 8-15%.",
        "context": "Tasks that involve model performance evaluation, especially for language models and transformer architectures.",
        "tags": ["performance", "methodology", "data_leakage", "evaluation"],
        "metadata": {
            "link_nodes": ["N1001", "N1003"]
        }
    },
    {
        "id": "RB-02",
        "type": "reasoning",
        "content": "When analyzing model performance, always consider external factors like dataset quality issues, distribution shifts, and evaluation methodology differences.",
        "context": "Model performance analysis, benchmark comparisons, and accuracy assessment for AI models.",
        "tags": ["performance", "dataset", "external_factors"],
        "metadata": {
            "link_nodes": ["N1004"]
        }
    },
    {
        "id": "RB-03",
        "type": "reasoning",
        "content": "For research paper presentations, use clear visualizations with detailed methodology sections. Focus on reproducibility and provide comprehensive experimental details.",
        "context": "Research paper preparation and presentation for academic audiences and research teams.",
        "tags": ["reporting", "stakeholder", "visualization", "research"],
        "metadata": {
            "link_nodes": ["N1002"]
        }
    }
]


def search_memories(query: str, memory_type: str = "all") -> List[Memory]:
    """
    Placeholder function to simulate memory retrieval from the database.
    In production, this would query Neo4j and Milvus with semantic search.
    
    Args:
        query: The search query
        memory_type: Type of memory to search ('graph', 'reasoning', or 'all')
    
    Returns:
        List of relevant Memory objects
    """
    results = []
    
    # Simple keyword matching for demonstration
    query_lower = query.lower()
    
    if memory_type in ["graph", "all"]:
        for mem in SAMPLE_GRAPH_MEMORIES:
            # Check if any query words appear in tags or content
            relevance = 0.0
            for word in query_lower.split():
                if word in mem["content"].lower():
                    relevance += 0.3
                if word in " ".join(mem["tags"]):
                    relevance += 0.2
            
            if relevance > 0:
                results.append(Memory(
                    id=mem["id"],
                    type=mem["type"],
                    content=mem["content"],
                    relevance_score=min(relevance, 1.0),
                    metadata=mem.get("metadata", {})
                ))
    
    if memory_type in ["reasoning", "all"]:
        for mem in SAMPLE_REASONING_MEMORIES:
            relevance = 0.0
            for word in query_lower.split():
                if word in mem["content"].lower():
                    relevance += 0.3
                if word in mem.get("context", "").lower():
                    relevance += 0.2
                if word in " ".join(mem["tags"]):
                    relevance += 0.2
            
            if relevance > 0:
                results.append(Memory(
                    id=mem["id"],
                    type=mem["type"],
                    content=mem["content"],
                    relevance_score=min(relevance, 1.0),
                    metadata=mem.get("metadata", {})
                ))
    
    # Sort by relevance score
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    # Return top 5 results
    return results[:5]

