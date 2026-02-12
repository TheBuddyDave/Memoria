"""Milvus hybrid retriever for seeding graph traversal.

This module performs a hybrid (BM25 sparse + dense semantic) search against the
`graphembeddings` Milvus collection.

For now, `retrieve()` returns the raw Milvus `hybrid_search` response so we can
inspect its structure before writing robust parsing to `SeedInput`.

Collection schema reference: `milvus/readmes/GraphEmbeddings_collection.md`
"""

from __future__ import annotations

from typing import Optional, Sequence, Any

from pymilvus import AnnSearchRequest, WeightedRanker

from src.config.llm_clients.openai_client import get_openai_client
from src.config.milvus_client import get_milvus_client
from src.memory_graph.models import SeedInput


class GraphVectorRetriever:
	"""Hybrid retriever for the `graphembeddings` Milvus collection.

	- BM25 full-text retrieval over `text` via `sparse_vector`
	- Dense semantic retrieval over `text` via `dense_vector`
	- Weighted fusion via `WeightedRanker(bm25_weight, dense_weight)`

	Note: `retrieve()` currently returns raw Milvus output (no parsing).
	"""

	COLLECTION_NAME = "graphembeddings"
	DENSE_FIELD = "dense_vector"
	SPARSE_FIELD = "sparse_vector"

	DEFAULT_OUTPUT_FIELDS = ["pointer_to_node"]

	def __init__(self, bm25_weight: float, dense_weight: float) -> None:
		"""Initialize retriever with weights for BM25 and dense search fusion.

		Args:
			bm25_weight: Weight for BM25 sparse search (0.0 to 1.0).
			dense_weight: Weight for dense semantic search (0.0 to 1.0).
		"""
		self.bm25_weight = float(bm25_weight)
		self.dense_weight = float(dense_weight)
		self._validate_weights()

	def _validate_weights(self) -> None:
		for name, w in (("bm25_weight", self.bm25_weight), ("dense_weight", self.dense_weight)):
			if not (0.0 <= w <= 1.0):
				raise ValueError(f"{name} must be between 0 and 1. Got {w}.")
		if self.bm25_weight == 0.0 and self.dense_weight == 0.0:
			raise ValueError(
				"Both weights are zero which is invalid. At least one of bm25_weight or dense_weight must be > 0."
			)

	async def create_embedding(self, text: str) -> list[float]:
		"""Create a 1536-dim embedding for the given text using OpenAI."""
		async with get_openai_client() as client:
			try:
				response = await client.embeddings.create(
					model="text-embedding-3-small",
					dimensions=1536,
					input=text,
				)
				return response.data[0].embedding
			except Exception as e:  # pragma: no cover
				raise RuntimeError(f"Failed to create embedding for user query: {e}") from e

	async def retrieve(
		self,
		user_query: str,
		*,
		limit: int = 3,
		candidate_multiplier: int = 5,
		expr: str = "",
		output_fields: Optional[Sequence[str]] = None,
		timeout: Optional[float] = None,
	) -> list[SeedInput]:
		"""Run hybrid search over `graphembeddings` and return parsed seed inputs.

		Args:
			user_query: Required query string.
			limit: Number of final seeds to return.
			candidate_multiplier: Per-request candidate_k = limit * candidate_multiplier.
			expr: Optional Milvus boolean expression for filtering.
			output_fields: Optional override of returned fields (defaults to pointer_to_node).
			timeout: Optional Milvus request timeout.
		"""
		if not user_query or not user_query.strip():
			return []
		if limit <= 0:
			return []

		# candidate_k: number of candidates per ANN request before fusion; set higher than limit for better recall
		# since hybrid reranking only considers these initial candidates, not the entire collection
		candidate_k = max(limit, limit * max(1, candidate_multiplier))
		fields = list(output_fields) if output_fields is not None else list(self.DEFAULT_OUTPUT_FIELDS)

		dense_vec = await self.create_embedding(user_query)

		# BM25 request: sparse search on text field; Milvus tokenizes query internally for keyword matching
		bm25_req_kwargs: dict[str, Any] = {
			"data": [user_query],
			"anns_field": self.SPARSE_FIELD,
			"param": {},
			"limit": candidate_k,
		}
		if expr:
			bm25_req_kwargs["expr"] = expr
		bm25_req = AnnSearchRequest(**bm25_req_kwargs)

		# Dense request: semantic search using cosine similarity on embeddings
		dense_req_kwargs: dict[str, Any] = {
			"data": [dense_vec],
			"anns_field": self.DENSE_FIELD,
			"param": {
				"metric_type": "COSINE",
				"params": {},
			},
			"limit": candidate_k,
		}
		if expr:
			dense_req_kwargs["expr"] = expr
		dense_req = AnnSearchRequest(**dense_req_kwargs)

		# reqs order must match WeightedRanker weights: BM25 first, dense second
		reqs = [bm25_req, dense_req]
		ranker = WeightedRanker(self.bm25_weight, self.dense_weight)

		async with get_milvus_client() as milvus_client:
			# Perform hybrid search: combines BM25 and dense results
			res = await milvus_client.hybrid_search(
				collection_name=self.COLLECTION_NAME,
				reqs=reqs,
				ranker=ranker,
				limit=limit,
				output_fields=fields,
				timeout=timeout,
			)

		# Parse Milvus response: res is tuple (data, metadata)
		# data is [[{hit}, {hit}, ...]] - list of hits lists (one per query vector)
		hits_list = res[0]
		if not hits_list:
			return []
		hits = hits_list[0] if isinstance(hits_list[0], list) else hits_list

		# Extract node_id and score from each hit
		seeds: list[SeedInput] = []
		for h in hits:
			entity = h.get("entity", {}) or {}
			node_id = entity.get("pointer_to_node", "")
			if node_id:  # Only include hits with valid node_id
				seeds.append(
					SeedInput(
						node_id=str(node_id),
						score=float(h["distance"]),
					)
				)

		return seeds

