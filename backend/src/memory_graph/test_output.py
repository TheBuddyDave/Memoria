"""
Test script to run GraphRetriever and output results.
Run: python -m src.memory_graph.test_output
"""

import asyncio
import json
from neo4j import AsyncGraphDatabase

from src.config.settings import get_settings
from src.memory_graph.graph_retriever import GraphRetriever
from src.memory_graph.models import GraphRetrieverConfig, SeedInput
from src.memory_graph.retriever_parser import to_d3, to_llm_context, to_debug_cypher


async def main():
    """Run graph retrieval and write parser output."""
    # Get settings
    settings = get_settings()
    
    # Create Neo4j driver
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    
    try:
        # Create retriever with default config
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(neo4j_driver=driver, config=config)
        
        # Prepare seeds
        seeds = [
            SeedInput(node_id="N3204", score=0.73),
            SeedInput(node_id="N3301", score=0.45),
            SeedInput(node_id="N5024", score=0.85),
        ]
        
        # Prepare query tags
        query_tags = [
            "sustainability",
            "co2",
            "competitor",
            "solution",
            "plan",
            "simulation_feedback",
            "guardrails",
        ]
        
        # Collect all results
        results = []
        async for result in retriever.explore(seeds=seeds, query_tags=query_tags):
            results.append(result)
        
        # Write parser outputs
        with open("src/memory_graph/retriever_sample_output.txt", "w", encoding="utf-8") as f:
            for idx, result in enumerate(results, start=1):
                f.write(f"{'='*80}\n")
                f.write(f"RESULT {idx}: Seed {result.seed.node_id} (initial seed score: {result.seed.score})\n")
                f.write(f"{'='*80}\n\n")
                
                # D3 output
                f.write("to_d3() output:\n")
                f.write(json.dumps(to_d3(result), indent=2))
                f.write("\n\n")
                
                # LLM context output
                f.write("to_llm_context() output:\n")
                f.write(json.dumps(to_llm_context(result), indent=2))
                f.write("\n\n")
                
                # Cypher debug output
                f.write("to_debug_cypher() output:\n")
                f.write(json.dumps(to_debug_cypher(result), indent=2))
                f.write("\n\n\n")
        
        print(f"✓ Output written to src/memory_graph/retriever_sample_output.txt")
        print(f"✓ Total results: {len(results)}")
        
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
