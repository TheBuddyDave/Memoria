"""
Milvus Hybrid Search: https://milvus.io/docs/hybrid_search_with_milvus.md

"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Sequence
from pymilvus import AnnSearchRequest, WeightedRanker

from src.config.milvus_client import get_milvus_client
from src.config.llm_clients.openai_client import get_openai_client


@dataclass(frozen=True)
class ReasoningBankHit:
    rb_id: int
    score: float
    key_lesson: str
    context_to_prefer: str
    link_nodes: Optional[list[str]] = None


class ReasoningBankRetriever:
    """
    Hybrid retriever for the `reasoningbank` collection:
      - BM25 full-text retrieval over `context_to_prefer` via `context_sparse_vector`
      - Dense semantic retrieval over `key_lesson` via `key_lesson_vector`
      - Weighted fusion via WeightedRanker(bm25_weight, dense_weight)

    Make sure the following are configured on milvus collection:
      - collection_name = "reasoningbank"
      - dense field = "key_lesson_vector" (FLOAT_VECTOR, dim=1536, metric=COSINE)
      - sparse field = "context_sparse_vector" (SPARSE_FLOAT_VECTOR, BM25 function output)
    """

    COLLECTION_NAME = "reasoningbank"
    DENSE_FIELD = "key_lesson_vector"
    SPARSE_FIELD = "context_sparse_vector"
    MIN_SCORE = 0.7

    # this is what we want to retrieve from the collection for each hit
    DEFAULT_OUTPUT_FIELDS = ["rb_id", "key_lesson", "context_to_prefer", "link_nodes"]

    def __init__(self, bm25_weight: float, dense_weight: float):
        """
        Initializes the ReasoningBankRetriever with specified BM25 and dense weights.
        
        Args:
            bm25_weight (float): Weight for BM25 search. Between 0.0 and 1.0.
            dense_weight (float): Weight for similarity search. Between 0.0 and 1.0.
        """
        self.bm25_weight = float(bm25_weight)
        self.dense_weight = float(dense_weight)
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validate that weights are between 0 and 1, and at least one is > 0."""
        for name, w in (("bm25_weight", self.bm25_weight), ("dense_weight", self.dense_weight)):
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1. Got {w}.")
        if self.bm25_weight == 0.0 and self.dense_weight == 0.0:
            raise ValueError("Both weights are zero which is invalid. At least one of bm25_weight or dense_weight must be > 0.")

    async def create_embedding(self, text: str) -> list[float]:
        """
        Create a 1536-dim embedding for the given text using OpenAI text-embedding-3-small
        Must return a 1536-dim embedding compatible with the collection schema:
        """
        async with get_openai_client() as client:
            try:
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    dimensions=1536,
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                raise RuntimeError(f"Failed to create embedding for user query: {e}") from e

    async def retrieve(
        self,
        user_query: str,
        *,
        limit: int = 5,
        candidate_multiplier: int = 5,
        expr: str = "",
        output_fields: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
    ) -> list[ReasoningBankHit]:
        """
        Runs hybrid search and returns top hits.

        candidate_multiplier:
          per-request candidate_k = limit * candidate_multiplier.
          This improves recall because hybrid reranking only considers returned candidates from each AnnSearchRequest.
        """
        if not user_query or not user_query.strip():
            return []

        if limit <= 0:
            return []

        # candidate_k: candidates per ANN request before fusion; higher than limit improves recall
        # as reranking only sees these, not full collection
        candidate_k = max(limit, limit * max(1, candidate_multiplier))
        fields = list(output_fields) if output_fields is not None else list(self.DEFAULT_OUTPUT_FIELDS)

        # 1) Create dense embedding for user query
        dense_vec = await self.create_embedding(user_query)

        # 2) Build per-field ANN requests.
        # BM25: sparse search; Milvus handles tokenization for keyword matching
        bm25_req_kwargs: dict[str, Any] = {
            "data": [user_query],
            "anns_field": self.SPARSE_FIELD,
            "param": {},
            "limit": candidate_k,
        }
        if expr:
            bm25_req_kwargs["expr"] = expr
        bm25_req = AnnSearchRequest(**bm25_req_kwargs)

        # Dense: semantic search with cosine similarity
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

        # Weight order matches reqs: BM25 first, dense second
        reqs = [bm25_req, dense_req]
        ranker = WeightedRanker(self.bm25_weight, self.dense_weight)

        # 3) Hybrid search
        async with get_milvus_client() as milvus_client:
            res = await milvus_client.hybrid_search(
                collection_name=self.COLLECTION_NAME,
                reqs=reqs,
                ranker=ranker,
                limit=limit,
                output_fields=fields,
                timeout=timeout,
            )

        # # 4) parse
        if not res:
            return []

        # Output is a tuple: data: [ [ {hit}, {hit}, ... ] ], {meta...}
        # So res[0] will give us first element: list of hits lists (for every query vector there is a hits list - but we only had one query vector)
        hits_list = res[0]
        if not hits_list:
            return []
        hits = hits_list[0] if isinstance(hits_list[0], list) else hits_list

        # parse and fill the pydantic model and only retain entries with score >= MIN_SCORE
        parsed_and_filtered: list[ReasoningBankHit] = []
        for h in hits:
            entity = h.get("entity", {}) or {}
            # MIN_SCORE filters low-relevance hits to focus on high-confidence matches
            if float(h["distance"]) >= self.MIN_SCORE:
                parsed_and_filtered.append(
                    ReasoningBankHit(
                        rb_id=int(h["primary_key"]),
                        score=float(h["distance"]),
                        key_lesson=str(entity.get("key_lesson", "")),
                        context_to_prefer=str(entity.get("context_to_prefer", "")),
                    link_nodes=entity.get("link_nodes"),  
                )
            )

        return parsed_and_filtered

