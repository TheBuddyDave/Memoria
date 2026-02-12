"""
Run python -m src.tests.reasoningbank_retriever.reasoningbank_retriever_test
"""

import asyncio
from pathlib import Path
from pprint import pformat
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
        
        dump = pformat(results, width=140)
        
        # Write to file
        out_path = Path(__file__).with_name("rb_output.txt")
        out_path.write_text(dump, encoding="utf-8")
        print(f"Wrote output to: {out_path}")
        
    except Exception as e:
        error_content = f"ERROR while retrieving: {type(e).__name__}: {e}\n"
        out_path = Path(__file__).with_name("rb_output.txt")
        out_path.write_text(error_content, encoding="utf-8")
        print(f"Wrote error to: {out_path}")
        raise


if __name__ == "__main__":
    asyncio.run(test_reasoningbank_retriever())
