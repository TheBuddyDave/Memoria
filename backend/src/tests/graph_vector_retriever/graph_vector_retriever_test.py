
"""Run python -m src.tests.graph_vector_retriever.graph_vector_retriever_test

Temporary script to inspect the raw Milvus hybrid_search response produced by
`GraphVectorRetriever` before we write any parsing logic.

This writes a text dump next to this file:
`src/tests/graph_vector_retriever_output.txt`
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from pprint import pformat

from src.memory_graph.graph_vector_retriever import GraphVectorRetriever


QUERY = (
	"How should we aim for discount A/B pilot window for different cluster-levels. "
	"focus on low income geographies"
)


async def test_graph_vector_retriever_raw_dump() -> None:
	print("Initializing GraphVectorRetriever...")
	retriever = GraphVectorRetriever(bm25_weight=0.5, dense_weight=0.5)

	print("Running hybrid search...")
	res = None
	dump = ""
	try:
		res = await retriever.retrieve(user_query=QUERY, limit=3)
		dump = pformat(res, width=140)
	except Exception as e:
		res = None
		dump = f"ERROR while retrieving: {type(e).__name__}: {e}\n"
		raise
	finally:
		out_path = Path(__file__).with_name("graph_vector_retriever_output.txt")
		out_path.write_text(dump, encoding="utf-8")
		print(f"Wrote output to: {out_path}")

	print("\nRetriever output:\n")
	print(dump)
	assert res is not None


if __name__ == "__main__":
	asyncio.run(test_graph_vector_retriever_raw_dump())

