"""Shared models for graph retrieval and exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GraphRetrieverConfig:
	"""Configuration for graph retrieval."""

	max_depth: int = 5
	min_activation: float = 0.005
	tag_sim_floor: float = 0.15
	max_branches: int = 3
	max_retries: int = 2
	database: str = "memorygraph"


@dataclass(frozen=True, slots=True)
class SeedInput:
	"""Seed input from vector search."""

	node_id: str
	score: float


@dataclass(frozen=True, slots=True)
class GraphNode:
	"""A graph node with labels and properties."""

	id: str
	labels: list[str]
	properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SeedFetchResult:
	"""Result of fetching a seed node."""

	node: GraphNode | None
	labels: list[str]
	found: bool


@dataclass(frozen=True, slots=True)
class GraphEdge:
	"""A directed edge representation of a RELATES relationship."""

	source_id: str
	target_id: str
	type: str
	properties: dict[str, Any] = field(default_factory=dict)
	weight: float | None = None
	tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GraphStep:
	"""A directed hop with transfer energy."""

	from_node: GraphNode
	edge: GraphEdge
	to_node: GraphNode
	transfer_energy: float


@dataclass(frozen=True, slots=True)
class GraphPath:
	"""A complete path from seed to a leaf."""

	steps: list[GraphStep] = field(default_factory=list)

	@classmethod
	def empty(cls) -> "GraphPath":
		return cls(steps=[])

	def with_step(self, step: GraphStep) -> "GraphPath":
		return GraphPath(steps=self.steps + [step])


@dataclass(frozen=True, slots=True)
class FrontierNode:
	"""Tracks one active branch during BFS expansion."""

	node_id: str
	activation: float
	path: GraphPath


@dataclass(frozen=True, slots=True)
class FrontierInput:
	"""Input to Cypher expansion query."""

	node_id: str
	activation: float


@dataclass(frozen=True, slots=True)
class ExpansionCandidate:
	"""Candidate expansion result from Cypher."""

	parent_id: str
	neighbor_node: GraphNode
	edge: GraphEdge
	transfer_energy: float


@dataclass(frozen=True, slots=True)
class FrontierUpdateResult:
	"""State update after selecting next frontier."""

	next_frontier: list[FrontierNode]
	completed_paths: list[GraphPath]
	newly_visited: set[str]


@dataclass(frozen=True, slots=True)
class RetrievalResult:
	"""Final output per seed."""

	seed: SeedInput
	seed_node: GraphNode | None
	paths: list[GraphPath]
	max_depth_reached: int
	terminated_reason: str
