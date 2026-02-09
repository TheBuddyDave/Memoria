"""
Run python -m src.tests.reasoningbank_retriever_test
"""

import asyncio
from src.subquery_gen.reasoningbank_retriever import ReasoningBankRetriever


async def test_reasoningbank_retriever():
    """
    Simple test to verify ReasoningBankRetriever functionality.
    """
    print("Initializing ReasoningBankRetriever...")
    
    # Initialize retriever with example weights
    # bm25_weight=0.7 for keyword matching, dense_weight=0.3 for semantic search
    retriever = ReasoningBankRetriever(bm25_weight=0.7, dense_weight=0.3)
    
    # Test query
    user_query = "give me the cheapest suppliers with best service levels and low price"
    
    try:
        # Retrieve results
        results = await retriever.retrieve(
            user_query=user_query,
            limit=5,
        )
        
        print(f"Retrieved {len(results)} results:\n")
        print("=" * 80)
        # print the objects nicely
        for idx, hit in enumerate(results, start=1):
            print(f"\nResult {idx}:")
            print(f"  ID: {hit.rb_id}")
            print(f"  Score: {hit.score}")
            print(f"  Key Lesson: {hit.key_lesson}")
            print(f"  Context to Prefer: {hit.context_to_prefer}")
            print(f"  Link Nodes: {hit.link_nodes}")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error during retrieval: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_reasoningbank_retriever())
