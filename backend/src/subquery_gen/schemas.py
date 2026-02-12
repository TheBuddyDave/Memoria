from typing import Optional
from pydantic import BaseModel, Field

class GraphSubquery(BaseModel):
    query: str= Field(
        description=(
            "A concrete independent subquery."
            "Each sub-query should retrieve the best nodes for the query"
        )
    )
    bm25_weight: float = Field(
        default=0.5,
        description="Weight for BM25 retrieval when combining with vector DB results. Between 0.0 and 1.0",
        le=1.0, ge=0.0
    )
    similarity_search_weight: float = Field(
        default=0.5,
        description="Weight for similarity search (vector DB) retrieval when combining with BM25 results. Between 0.0 and 1.0",
        le=1.0, ge=0.0
    )
    
    query_tags: list[str] = Field(
        description="Tags that go along with the query to help with filtering retrieved nodes and edges. Choose from the set of tags provided to you, do not provide new tags or make them up on your own. Give maximum of 7 tags and minimum of 3 tags from the list."
    )
    
class ReasoningBankSubquery(BaseModel):
    query: str = Field(
        description=(
            "A list of concrete, independent, self-contained sub-queries for BM25 + vector DB retrieval of past lessons in reasoning bank. None if clarifications are still needed"
        )
    )
    bm25_weight: float = Field(
        default=0.5,
        description="Weight for BM25 retrieval when combining with vector DB results. Between 0.0 and 1.0",
        le=1.0, ge=0.0
    )
    similarity_search_weight: float = Field(
        default=0.5,
        description="Weight for similarity search (vector DB) retrieval when combining with BM25 results. Between 0.0 and 1.0",
        le=1.0, ge=0.0
    )
    
class OutputModel(BaseModel):
    clarification_question: Optional[str] = Field(
        default=None,
        description=(
            "A single, concise clarification question to ask the user in order to decompose the user query better"
        ),
    )

    graph_subqueries: Optional[list[GraphSubquery]] = Field(
        description= "List of concrete, independent sub-queries for graph retrieval. Together they should cover all aspects of the user query. Set it to None if asking clarifications."
    )
    
    reasoningbank_subqueries: Optional[list[ReasoningBankSubquery]] = Field(
        description= "List of concrete, independent sub-queries for reasoning bank retrieval. Together they should cover all aspects of the user query. Set it to None if asking clarifications."
    )