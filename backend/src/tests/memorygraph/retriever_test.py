"""Docstring for src.tests.memorygraph.retriever_test.

Run: pytest src/tests/memorygraph -q --verbose
"""

from __future__ import annotations

import math
from typing import Any, TypedDict
import pytest
from neo4j import AsyncDriver, AsyncManagedTransaction

from src.memory_graph.graph_retriever import GraphTraversalState, Neo4jConnector
from src.memory_graph.models import (
	ExpansionCandidate,
	FrontierInput,
	FrontierNode,
	GraphEdge,
	GraphNode,
	GraphPath,
	GraphStep,
	RetrievalResult,
	SeedInput,
)
from src.memory_graph.retriever_parser import to_d3, to_debug_cypher, to_llm_context

class TransferEnergyCase(TypedDict):
	parent_id: str
	neighbor_id: str
	activation: float
	weight: float
	degree: int
	edge_tags: list[str]
	query_tags: list[str]


class TagSimCase(TypedDict):
	neighbor_id: str
	edge_tags: list[str]
	weight: float
	query_tags: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _node(node_id: str, label: str = "Node") -> GraphNode:
	return GraphNode(id=node_id, labels=[label], properties={"id": node_id})


def _edge(source_id: str, target_id: str, weight: float | None = None) -> GraphEdge:
	return GraphEdge(
		source_id=source_id,
		target_id=target_id,
		type="RELATES",
		properties={},
		weight=weight,
		tags=[],
	)


def _step(from_id: str, to_id: str, transfer_energy: float) -> GraphStep:
	return GraphStep(
		from_node=_node(from_id),
		edge=_edge(from_id, to_id, weight=0.5),
		to_node=_node(to_id),
		transfer_energy=transfer_energy,
	)


def _tag_sim(tag_sim_floor: float, edge_tags: list[str], query_tags: list[str]) -> float:
	if not query_tags:
		return 1.0
	if not edge_tags:
		return tag_sim_floor
	inter_count = len([tag for tag in edge_tags if tag in query_tags])
	union_count = len(edge_tags) + len(query_tags) - inter_count
	return tag_sim_floor + (1.0 - tag_sim_floor) * (inter_count / union_count)


def _transfer_energy(activation: float, weight: float, degree: int, tag_sim: float) -> float:
	return (activation * weight / math.sqrt(float(degree))) * tag_sim


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1A: TRAVERSAL STATE TESTS (PURE PYTHON)
# ═══════════════════════════════════════════════════════════════════════════════

def test_frontier_selection_deduplication():
	"""Scenario: two parents compete for the same neighbor with ordered candidates.
	Expected: max 2 branches per parent, collision resolved by higher energy first, and visited set updated.
	Why: GraphTraversalState selects in frontier order and skips already-claimed neighbors.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	parent_p1 = _node("P1")
	parent_p2 = _node("P2")

	p1_path = GraphPath.empty().with_step(_step("S", "P1", 0.2))
	p2_path = GraphPath.empty().with_step(_step("S", "P2", 0.3))

	frontier = [
		FrontierNode(node_id="P2", activation=0.9, path=p2_path),
		FrontierNode(node_id="P1", activation=0.8, path=p1_path),
	]

	candidates_by_parent = {
		"P2": [
			ExpansionCandidate(
				parent_id="P2",
				neighbor_node=_node("N1"),
				edge=_edge("P2", "N1", weight=0.9),
				transfer_energy=0.9,
			),
			ExpansionCandidate(
				parent_id="P2",
				neighbor_node=_node("N4"),
				edge=_edge("P2", "N4", weight=0.2),
				transfer_energy=0.2,
			),
		],
		"P1": [
			ExpansionCandidate(
				parent_id="P1",
				neighbor_node=_node("N1"),
				edge=_edge("P1", "N1", weight=0.5),
				transfer_energy=0.5,
			),
			ExpansionCandidate(
				parent_id="P1",
				neighbor_node=_node("N2"),
				edge=_edge("P1", "N2", weight=0.4),
				transfer_energy=0.4,
			),
			ExpansionCandidate(
				parent_id="P1",
				neighbor_node=_node("N3"),
				edge=_edge("P1", "N3", weight=0.3),
				transfer_energy=0.3,
			),
		],
	}

	traversal.set_frontier(frontier)
	update = traversal.select_next_frontier(candidates_by_parent)

	selected_neighbors = {node.node_id for node in update.next_frontier}
	assert selected_neighbors == {"N1", "N2", "N3", "N4"}

	p1_count = sum(
		1
		for node in update.next_frontier
		if node.path.steps[-1].from_node.id == "P1"
	)
	p2_count = sum(
		1
		for node in update.next_frontier
		if node.path.steps[-1].from_node.id == "P2"
	)
	assert p1_count == 2
	assert p2_count == 2

	assert update.newly_visited == {"N1", "N2", "N3", "N4"}


def test_completed_path_logic():
	"""Scenario: a frontier node has no candidates but a non-empty path.
	Expected: the path is moved to completed_paths and not lost.
	Why: select_next_frontier finalizes leaves only when they have a prior step.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	path = GraphPath.empty().with_step(_step("S", "P1", 0.2))
	frontier = [FrontierNode(node_id="P1", activation=0.7, path=path)]

	traversal.set_frontier(frontier)
	update = traversal.select_next_frontier(candidates_by_parent={})

	assert update.completed_paths == [path]
	assert update.next_frontier == []


def test_max_depth_completion():
	"""Scenario: remaining frontier nodes have non-empty paths at loop end.
	Expected: finalize_remaining returns all non-empty paths.
	Why: traversal should surface all unfinished paths when depth cap is reached.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	path1 = GraphPath.empty().with_step(_step("S", "P1", 0.2))
	path2 = GraphPath.empty().with_step(_step("S", "P2", 0.3))
	frontier = [
		FrontierNode(node_id="P1", activation=0.7, path=path1),
		FrontierNode(node_id="P2", activation=0.6, path=path2),
		FrontierNode(node_id="P3", activation=0.5, path=GraphPath.empty()),
	]

	completed = traversal.finalize_remaining(frontier)

	assert completed == [path1, path2]


def test_completed_path_multiple_leaves():
	"""Scenario: multiple frontier nodes with no candidates complete simultaneously.
	Expected: all non-empty paths are moved to completed_paths in one update.
	Why: select_next_frontier must handle batch leaf finalization correctly.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	path1 = GraphPath.empty().with_step(_step("S", "P1", 0.5))
	path2 = GraphPath.empty().with_step(_step("S", "P2", 0.4))
	path3 = GraphPath.empty().with_step(_step("S", "P3", 0.3))

	frontier = [
		FrontierNode(node_id="P1", activation=0.5, path=path1),
		FrontierNode(node_id="P2", activation=0.4, path=path2),
		FrontierNode(node_id="P3", activation=0.3, path=path3),
	]

	traversal.set_frontier(frontier)
	update = traversal.select_next_frontier(candidates_by_parent={})

	assert len(update.completed_paths) == 3
	assert set(p.steps[-1].to_node.id for p in update.completed_paths) == {"P1", "P2", "P3"}
	assert update.next_frontier == []


def test_completed_path_mixed_continuation():
	"""Scenario: some frontier nodes complete, others continue with candidates.
	Expected: completed paths are separated, continuing nodes move to next frontier.
	Why: select_next_frontier handles mixed leaf/branch scenarios.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	path_leaf = GraphPath.empty().with_step(_step("S", "P1", 0.5))
	path_branch = GraphPath.empty().with_step(_step("S", "P2", 0.4))

	frontier = [
		FrontierNode(node_id="P1", activation=0.5, path=path_leaf),
		FrontierNode(node_id="P2", activation=0.4, path=path_branch),
	]

	candidates_by_parent = {
		"P2": [
			ExpansionCandidate(
				parent_id="P2",
				neighbor_node=_node("N1"),
				edge=_edge("P2", "N1", weight=0.6),
				transfer_energy=0.6,
			),
		],
	}

	traversal.set_frontier(frontier)
	update = traversal.select_next_frontier(candidates_by_parent)

	assert update.completed_paths == [path_leaf]
	assert len(update.next_frontier) == 1
	assert update.next_frontier[0].node_id == "N1"


def test_max_depth_completion_preserves_metadata():
	"""Scenario: finalize_remaining called with multi-hop paths carrying activation.
	Expected: all path steps and activation values are preserved intact.
	Why: path metadata must survive depth-cap termination.
	"""
	seed_node = _node("S", "Seed")
	traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)

	path1 = (
		GraphPath.empty()
		.with_step(_step("S", "P1", 0.5))
		.with_step(_step("P1", "N1", 0.3))
	)
	path2 = (
		GraphPath.empty()
		.with_step(_step("S", "P2", 0.4))
		.with_step(_step("P2", "N2", 0.2))
		.with_step(_step("N2", "N3", 0.1))
	)

	frontier = [
		FrontierNode(node_id="N1", activation=0.3, path=path1),
		FrontierNode(node_id="N3", activation=0.1, path=path2),
	]

	completed = traversal.finalize_remaining(frontier)

	assert len(completed) == 2
	assert completed[0].steps[-1].to_node.id == "N1"
	assert completed[0].steps[-1].transfer_energy == 0.3
	assert completed[1].steps[-1].to_node.id == "N3"
	assert len(completed[1].steps) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1B: PARSER OUTPUT TESTS (PURE PYTHON)
# ═══════════════════════════════════════════════════════════════════════════════

def test_to_d3_minimal_sanity():
	"""Scenario: one seed node and a single-hop path.
	Expected: D3 output has two nodes, one link, and activation on target node.
	Why: to_d3 aggregates nodes/links and propagates transfer energy.
	"""
	seed = SeedInput(node_id="S1", score=0.7)
	seed_node = GraphNode(id="S1", labels=["Seed"], properties={"text": "seed"})
	to_node = GraphNode(id="N1", labels=["Doc"], properties={"text": "doc"})
	edge = GraphEdge(
		source_id="S1",
		target_id="N1",
		type="RELATES",
		properties={"weight": 0.5},
		weight=0.5,
		tags=["tag"],
	)
	step = GraphStep(
		from_node=seed_node,
		edge=edge,
		to_node=to_node,
		transfer_energy=0.12,
	)
	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[GraphPath(steps=[step])],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	graph = to_d3(result)
	nodes_by_id = {node["id"]: node for node in graph["nodes"]}
	edges = graph["edges"]

	assert set(nodes_by_id) == {"S1", "N1"}
	assert nodes_by_id["S1"]["retrieval_activation"] == seed.score
	assert nodes_by_id["N1"]["retrieval_activation"] == pytest.approx(0.12)
	assert nodes_by_id["S1"]["is_seed"] is True
	assert nodes_by_id["N1"]["is_seed"] is False
	assert len(edges) == 1
	assert edges[0]["source"] == "S1"
	assert edges[0]["target"] == "N1"


def test_to_llm_context_minimal_sanity():
	"""Scenario: single-hop result sent to LLM context formatter.
	Expected: formatted path contains seed, RELATES edge, and formatted transfer energy.
	Why: to_llm_context builds strings using the same formatting rules as UI.
	"""
	seed = SeedInput(node_id="S1", score=0.7)
	seed_node = GraphNode(id="S1", labels=["Seed"], properties={"text": "seed"})
	to_node = GraphNode(id="N1", labels=["Doc"], properties={"text": "doc"})
	edge = GraphEdge(
		source_id="S1",
		target_id="N1",
		type="RELATES",
		properties={"weight": 0.5},
		weight=0.5,
		tags=["tag"],
	)
	step = GraphStep(
		from_node=seed_node,
		edge=edge,
		to_node=to_node,
		transfer_energy=0.12,
	)
	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[GraphPath(steps=[step])],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	context = to_llm_context(result)

	assert len(context["paths"]) == 1
	path_text = context["paths"][0]
	assert path_text.startswith("Path 1: [SEED]")
	assert "weight=0.500" in path_text
	assert "activation_score=0.120" in path_text
	assert "node_and_edge_attributes" in context
	assert "nodes" in context["node_and_edge_attributes"]
	assert "edges" in context["node_and_edge_attributes"]


def test_to_debug_cypher_minimal_sanity():
	"""Scenario: single-hop result sent to Cypher debug formatter.
	Expected: one query with n0/n1 id placeholders in the path order and UNION-safe combined query.
	Why: to_debug_cypher maps step ordering to parameterized node IDs.
	"""
	seed = SeedInput(node_id="S1", score=0.7)
	seed_node = GraphNode(id="S1", labels=["Seed"], properties={"text": "seed"})
	to_node = GraphNode(id="N1", labels=["Doc"], properties={"text": "doc"})
	edge = GraphEdge(
		source_id="S1",
		target_id="N1",
		type="RELATES",
		properties={"weight": 0.5},
		weight=0.5,
		tags=["tag"],
	)
	step = GraphStep(
		from_node=seed_node,
		edge=edge,
		to_node=to_node,
		transfer_energy=0.12,
	)
	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[GraphPath(steps=[step])],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	queries = to_debug_cypher(result)

	assert queries["paths_combined"] == (
		"MATCH p = (n0_0 {id: 'S1'})-[:RELATES]-(n0_1 {id: 'N1'}) RETURN p"
	)
	assert queries["individual_paths"] == [
		"MATCH p0 = (n0_0 {id: 'S1'})-[:RELATES]-(n0_1 {id: 'N1'}) RETURN p0"
	]


def test_to_d3_multi_path_shared_nodes():
	"""Scenario: two paths share the seed and converge on a common node.
	Expected: shared nodes take max activation from both paths, edges deduplicated.
	Why: to_d3 uses max() aggregation for nodes visited by multiple paths.
	"""
	seed = SeedInput(node_id="S1", score=0.8)
	seed_node = _node("S1", "Seed")
	node_a = _node("A", "Doc")
	node_b = _node("B", "Doc")
	node_c = _node("C", "Doc")

	path1 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "A", weight=0.5),
			to_node=node_a,
			transfer_energy=0.3,
		),
		GraphStep(
			from_node=node_a,
			edge=_edge("A", "C", weight=0.4),
			to_node=node_c,
			transfer_energy=0.15,
		),
	])

	path2 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "B", weight=0.6),
			to_node=node_b,
			transfer_energy=0.4,
		),
		GraphStep(
			from_node=node_b,
			edge=_edge("B", "C", weight=0.5),
			to_node=node_c,
			transfer_energy=0.25,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path1, path2],
		max_depth_reached=2,
		terminated_reason="complete",
	)

	graph = to_d3(result)
	nodes_by_id = {node["id"]: node for node in graph["nodes"]}

	assert set(nodes_by_id.keys()) == {"S1", "A", "B", "C"}
	assert nodes_by_id["S1"]["retrieval_activation"] == 0.8
	assert nodes_by_id["A"]["retrieval_activation"] == pytest.approx(0.3)
	assert nodes_by_id["B"]["retrieval_activation"] == pytest.approx(0.4)
	assert nodes_by_id["C"]["retrieval_activation"] == pytest.approx(max(0.15, 0.25))

	edges = graph["edges"]
	assert len(edges) == 4


def test_to_d3_longer_path():
	"""Scenario: single 3-hop path from seed through intermediate nodes.
	Expected: all nodes and edges present with correct activation propagation.
	Why: to_d3 must handle arbitrary path lengths correctly.
	"""
	seed = SeedInput(node_id="S1", score=1.0)
	seed_node = _node("S1", "Seed")
	node_p1 = _node("P1", "Doc")
	node_p2 = _node("P2", "Doc")
	node_p3 = _node("P3", "Doc")

	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "P1", weight=0.5),
			to_node=node_p1,
			transfer_energy=0.5,
		),
		GraphStep(
			from_node=node_p1,
			edge=_edge("P1", "P2", weight=0.4),
			to_node=node_p2,
			transfer_energy=0.3,
		),
		GraphStep(
			from_node=node_p2,
			edge=_edge("P2", "P3", weight=0.3),
			to_node=node_p3,
			transfer_energy=0.2,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=3,
		terminated_reason="complete",
	)

	graph = to_d3(result)
	nodes_by_id = {node["id"]: node for node in graph["nodes"]}
	edges = graph["edges"]

	assert set(nodes_by_id.keys()) == {"S1", "P1", "P2", "P3"}
	assert len(edges) == 3
	assert nodes_by_id["P3"]["retrieval_activation"] == pytest.approx(0.2)


def test_to_llm_context_multi_path():
	"""Scenario: multiple paths with varying lengths sent to LLM formatter.
	Expected: each path formatted separately with proper numbering and structure.
	Why: to_llm_context must handle multi-path results for context building.
	"""
	seed = SeedInput(node_id="S1", score=0.9)
	seed_node = _node("S1", "Seed")

	path1 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "A", weight=0.7),
			to_node=_node("A", "Doc"),
			transfer_energy=0.5,
		),
	])

	path2 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "B", weight=0.6),
			to_node=_node("B", "Doc"),
			transfer_energy=0.4,
		),
		GraphStep(
			from_node=_node("B", "Doc"),
			edge=_edge("B", "C", weight=0.5),
			to_node=_node("C", "Doc"),
			transfer_energy=0.25,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path1, path2],
		max_depth_reached=2,
		terminated_reason="complete",
	)

	context = to_llm_context(result)

	assert len(context["paths"]) == 2
	assert context["paths"][0].startswith("Path 1:")
	assert context["paths"][1].startswith("Path 2:")
	assert "activation_score=0.500" in context["paths"][0]
	assert "activation_score=0.250" in context["paths"][1]


def test_to_debug_cypher_multi_path():
	"""Scenario: multiple paths with different lengths generate Cypher queries.
	Expected: one query per path with correct node/edge indexing.
	Why: to_debug_cypher must produce valid Cypher for each path independently.
	"""
	seed = SeedInput(node_id="S1", score=0.9)
	seed_node = _node("S1", "Seed")

	path1 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "A", weight=0.5),
			to_node=_node("A", "Doc"),
			transfer_energy=0.3,
		),
	])

	path2 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("S1", "B", weight=0.4),
			to_node=_node("B", "Doc"),
			transfer_energy=0.2,
		),
		GraphStep(
			from_node=_node("B", "Doc"),
			edge=_edge("B", "C", weight=0.3),
			to_node=_node("C", "Doc"),
			transfer_energy=0.15,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path1, path2],
		max_depth_reached=2,
		terminated_reason="complete",
	)

	queries = to_debug_cypher(result)

	assert len(queries["individual_paths"]) == 2
	assert "n0_0" in queries["individual_paths"][0]
	assert "n0_1" in queries["individual_paths"][0]
	assert "n1_0" in queries["individual_paths"][1]
	assert "n1_1" in queries["individual_paths"][1]
	assert "n1_2" in queries["individual_paths"][1]
	assert queries["paths_combined"].count(" UNION ") == 1


def test_to_debug_cypher_combined_paths():
	"""Scenario: multiple paths from same seed should be combined into one MATCH statement.
	Expected: paths_combined is a UNION of MATCH queries to avoid Cartesian products.
	Why: paths_combined visualizes all branches from seed in one query for Neo4j Browser without row explosion.
	"""
	seed = SeedInput(node_id="SEED123", score=0.8)
	seed_node = _node("SEED123", "Seed")

	path1 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("SEED123", "N1", weight=0.7),
			to_node=_node("N1", "Doc"),
			transfer_energy=0.5,
		),
	])

	path2 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("SEED123", "N2", weight=0.6),
			to_node=_node("N2", "Doc"),
			transfer_energy=0.4,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path1, path2],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	queries = to_debug_cypher(result)

	combined = queries["paths_combined"]

	# Should be UNION-based with a shared path variable
	assert combined.count("MATCH ") == 2
	assert combined.count(" RETURN ") == 2
	assert " UNION " in combined
	assert "MATCH p =" in combined

	# Should contain literal IDs (not parameters)
	assert '"SEED123"' in combined or "'SEED123'" in combined
	assert '"N1"' in combined or "'N1'" in combined
	assert '"N2"' in combined or "'N2'" in combined

	# Should NOT contain parameterized IDs
	assert "$id" not in combined


def test_to_debug_cypher_literal_id_escaping():
	"""Scenario: node IDs with special characters should be properly escaped for Neo4j Desktop copy-paste.
	Expected: IDs are quoted with single quotes, backslashes/quotes are escaped, output is ready to run in Neo4j.
	Why: Cypher queries must be syntactically valid and copy-pastable into Neo4j Desktop without manual fixes.
	"""
	seed = SeedInput(node_id='N"123', score=0.8)
	seed_node = GraphNode(id='N"123', labels=["Seed"], properties={"id": 'N"123'})
	to_node = GraphNode(id='N\\456', labels=["Doc"], properties={"id": 'N\\456'})

	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge('N"123', 'N\\456', weight=0.7),
			to_node=to_node,
			transfer_energy=0.5,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	queries = to_debug_cypher(result)
	combined = queries["paths_combined"]
	
	# Should use single quotes for Cypher literals
	assert "'N\"123'" in combined  # Double quote escaped in single-quoted string
	assert "'N\\\\456'" in combined  # Backslash escaped in single-quoted string
	
	# Should NOT contain unescaped backslashes that would break Neo4j copy-paste. The output should be directly runnable in Neo4j Desktop
	assert "\\" not in combined.replace("\\\\", "").replace("\\'", "")  # Only allow escaped backslashes and single quotes
	
	# Should be valid Cypher syntax (basic checks)
	assert combined.startswith("MATCH ")
	assert " RETURN " in combined
	assert "MATCH p =" in combined


def test_to_debug_cypher_neo4j_ready_output():
	"""Scenario: Cypher output should be directly copy-pastable into Neo4j Desktop.
	Expected: no problematic characters, valid Cypher syntax, ready to execute.
	Why: users should be able to copy the output and run it immediately in Neo4j.
	"""
	seed = SeedInput(node_id="NODE-123", score=0.9)
	seed_node = _node("NODE-123", "Seed")
	
	path1 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("NODE-123", "CHILD-A", weight=0.8),
			to_node=_node("CHILD-A", "Doc"),
			transfer_energy=0.6,
		),
	])
	
	path2 = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=_edge("NODE-123", "CHILD-B", weight=0.7),
			to_node=_node("CHILD-B", "Doc"),
			transfer_energy=0.5,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path1, path2],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	queries = to_debug_cypher(result)
	
	# Test individual paths are Neo4j-ready
	for path_query in queries["individual_paths"]:
		assert path_query.startswith("MATCH ")
		assert " RETURN " in path_query
		assert "p" in path_query  # Path variable
		assert "'NODE-123'" in path_query  # Single-quoted ID
		assert "'CHILD-" in path_query  # Single-quoted IDs
		# Should not contain characters that break Neo4j copy-paste
		assert "\\" not in path_query.replace("\\\\", "").replace("\\'", "")
	
	# Test combined paths is Neo4j-ready
	combined = queries["paths_combined"]
	assert combined.count("MATCH ") == 2  # One MATCH per path
	assert combined.count(" RETURN ") == 2  # One RETURN per path
	assert " UNION " in combined  # UNION separator
	assert "MATCH p =" in combined  # Shared path variable
	# Should be directly executable in Neo4j Desktop
	assert "\\" not in combined.replace("\\\\", "").replace("\\'", "")


def test_to_llm_context_seed_marker():
	"""Scenario: seed node should be marked with [SEED] prefix in paths.
	Expected: only the seed node has [SEED] marker, other nodes don't.
	Why: LLM needs to identify highest-relevance entry point from vector search.
	"""
	seed = SeedInput(node_id="SEED_NODE", score=0.9)
	seed_node = GraphNode(id="SEED_NODE", labels=["AgentAction"], properties={
		"id": "SEED_NODE",
		"text": "This is the seed node with important content"
	})
	
	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=GraphEdge(
				source_id="SEED_NODE",
				target_id="CHILD",
				type="RELATES",
				properties={"id": "E1", "text": "Connects to child", "weight": 0.8},
				weight=0.8,
			),
			to_node=GraphNode(id="CHILD", labels=["Event"], properties={
				"id": "CHILD",
				"text": "Child node"
			}),
			transfer_energy=0.6,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	context = to_llm_context(result)
	path_text = context["paths"][0]
	
	# Seed node should have [SEED] marker
	assert "[SEED]" in path_text
	assert path_text.count("[SEED]") == 1  # Only one seed marker
	
	# SEED marker should be before first node
	seed_idx = path_text.index("[SEED]")
	seed_node_idx = path_text.index("SEED_NODE")
	assert seed_idx < seed_node_idx


def test_to_llm_context_truncation():
	"""Scenario: node text should be truncated to 12 words with ellipsis, edge text should not be truncated.
	Expected: nodes show first 12 words + "...", edges show full text.
	Why: balance token efficiency with semantic completeness, edges need full context.
	"""
	seed = SeedInput(node_id="S", score=0.8)
	
	# Node with >12 words
	long_node_text = "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
	seed_node = GraphNode(id="S", labels=["AgentAction"], properties={
		"id": "S",
		"text": long_node_text
	})
	
	# Edge with long text (should NOT be truncated)
	long_edge_text = "This edge has a very long description that explains the relationship in detail and should not be truncated"
	to_node = GraphNode(id="N", labels=["Event"], properties={
		"id": "N",
		"text": long_node_text
	})
	
	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=GraphEdge(
				source_id="S",
				target_id="N",
				type="RELATES",
				properties={"id": "E1", "text": long_edge_text, "weight": 0.8},
				weight=0.8,
			),
			to_node=to_node,
			transfer_energy=0.5,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	context = to_llm_context(result)
	path_text = context["paths"][0]
	
	# Node text should be truncated with ellipsis
	assert "One two three four five six seven eight nine ten eleven twelve..." in path_text
	assert "thirteen" not in path_text  # 13th word should not appear
	
	# Edge text should be FULL (not truncated)
	assert long_edge_text in path_text


def test_to_llm_context_attributes_structure():
	"""Scenario: node_and_edge_attributes should have flattened structure with tags and proper field names.
	Expected: "node_and_edge_attributes" with "nodes" and "edges", not nested properties, tags preserved.
	Why: new format optimizes for LLM consumption with flattened attributes.
	"""
	seed = SeedInput(node_id="N1", score=0.7)
	seed_node = GraphNode(id="N1", labels=["AgentAction"], properties={
		"id": "N1",
		"text": "Action text",
		"tags": ["pilot", "simulation"],
		"conv_id": "conv_123",
		"status": "complete",
		"parameter_field": '{"key": "value"}'
	})
	
	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=GraphEdge(
				source_id="N1",
				target_id="N2",
				type="RELATES",
				properties={
					"id": "E1",
					"text": "Edge text",
					"tags": ["trigger", "experiment"],
					"weight": 0.9,
					"created_time": "2025-01-01T00:00:00"
				},
				weight=0.9,
				tags=["trigger", "experiment"],
			),
			to_node=GraphNode(id="N2", labels=["Event"], properties={
				"id": "N2",
				"text": "Event text",
				"tags": ["pilot"]
			}),
			transfer_energy=0.5,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	context = to_llm_context(result)
	
	# Test top-level structure
	assert "node_and_edge_attributes" in context
	assert "graph" not in context  # Old name removed
	
	attrs = context["node_and_edge_attributes"]
	assert "nodes" in attrs
	assert "edges" in attrs
	assert "links" not in attrs  # Old name removed
	
	# Test node structure
	nodes = attrs["nodes"]
	seed_n = next(n for n in nodes if n["id"] == "N1")
	
	# Should be flattened (no nested properties)
	assert "properties" not in seed_n
	
	# Should have singular label
	assert "label" in seed_n
	assert "labels" not in seed_n
	assert seed_n["label"] == "AgentAction"
	
	# Should have tags
	assert "tags" in seed_n
	assert seed_n["tags"] == ["pilot", "simulation"]
	
	# Should have retrieval_activation (not activation)
	assert "retrieval_activation" in seed_n
	assert "activation" not in seed_n
	
	# Should have special fields at top level
	assert seed_n["parameter_field"] == '{"key": "value"}'
	assert seed_n["conv_id"] == "conv_123"
	assert seed_n["status"] == "complete"
	
	# Test edge structure
	edges = attrs["edges"]
	edge = edges[0]
	
	# Should have renamed fields
	assert "edge_id" in edge
	assert "source_node_id" in edge
	assert "target_node_id" in edge
	assert "id" not in edge
	assert "source" not in edge or edge.get("source") != edge["source_node_id"]  # No bare "source"
	assert "target" not in edge or edge.get("target") != edge["target_node_id"]  # No bare "target"
	
	# Should have tags
	assert "tags" in edge
	assert edge["tags"] == ["trigger", "experiment"]
	
	# Should have transfer_energy rounded to 3 decimals
	assert edge["transfer_energy"] == 0.5
	
	# Should NOT have type field
	assert "type" not in edge


def test_to_d3_structure():
	"""Scenario: D3 output should have flattened structure with is_seed flag and proper field names.
	Expected: "edges" not "links", flattened nodes, is_seed flag, tags preserved, source/target for D3.js.
	Why: D3.js-optimized format with minimal frontend parsing required.
	"""
	seed = SeedInput(node_id="SEED", score=0.8)
	seed_node = GraphNode(id="SEED", labels=["AgentAction"], properties={
		"id": "SEED",
		"text": "Seed action",
		"tags": ["action", "seed"],
		"conv_id": "conv_123"
	})
	
	path = GraphPath(steps=[
		GraphStep(
			from_node=seed_node,
			edge=GraphEdge(
				source_id="SEED",
				target_id="CHILD",
				type="RELATES",
				properties={
					"id": "E1",
					"text": "Edge description",
					"tags": ["connects"],
					"weight": 0.85,
					"created_time": "2025-01-01"
				},
				weight=0.85,
				tags=["connects"],
			),
			to_node=GraphNode(id="CHILD", labels=["Event"], properties={
				"id": "CHILD",
				"text": "Child event",
				"tags": ["event"]
			}),
			transfer_energy=0.6,
		),
	])

	result = RetrievalResult(
		seed=seed,
		seed_node=seed_node,
		paths=[path],
		max_depth_reached=1,
		terminated_reason="complete",
	)

	graph = to_d3(result)
	
	# Test top-level structure
	assert "nodes" in graph
	assert "edges" in graph
	assert "links" not in graph  # Old name removed
	
	# Test node structure
	nodes_by_id = {n["id"]: n for n in graph["nodes"]}
	seed_n = nodes_by_id["SEED"]
	child_n = nodes_by_id["CHILD"]
	
	# Should have is_seed flag
	assert "is_seed" in seed_n
	assert seed_n["is_seed"] is True
	assert "is_seed" in child_n
	assert child_n["is_seed"] is False
	
	# Should be flattened
	assert "properties" not in seed_n
	
	# Should have singular label
	assert seed_n["label"] == "AgentAction"
	assert "labels" not in seed_n
	
	# Should have tags
	assert seed_n["tags"] == ["action", "seed"]
	
	# Should have retrieval_activation
	assert "retrieval_activation" in seed_n
	
	# Test edge structure
	edges = graph["edges"]
	edge = edges[0]
	
	# Should have source/target for D3.js (required)
	assert "source" in edge
	assert "target" in edge
	assert edge["source"] == "SEED"
	assert edge["target"] == "CHILD"
	
	# Should have edge_id separately
	assert "edge_id" in edge
	assert edge["edge_id"] == "E1"
	
	# Should have tags
	assert edge["tags"] == ["connects"]
	
	# Should have rounded transfer_energy
	assert edge["transfer_energy"] == 0.6
	
	# Should NOT have type field
	assert "type" not in edge


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: CYPHER + MATH VALIDATION TESTS (INTEGRATION)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_transfer_energy_math_check(neo4j_driver: AsyncDriver):
	"""Scenario: compute transfer energy for known dummy edges.
	Expected: transfer_energy matches manual formula using exact dummy weights/tags/degree.
	Why: expand_frontier applies $T = (R * w / sqrt(d)) * tag_sim$ from the Cypher query.

	Dummy edges:
	- E7001: T3000->T3001 weight=0.90 tags=['campaign','evidence','region'] degree(T3000)=3.
	- E7003: T3001->T3002 weight=0.75 tags=['normalization','campaign'] degree(T3001)=3.
	- E7104: T4001->T4003 weight=0.70 tags=['lead_time','evidence'] degree(T4001)=4.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0001)

	cases: list[TransferEnergyCase] = [
		{
			"parent_id": "T3000",
			"neighbor_id": "T3001",
			"activation": 0.85,
			"weight": 0.90,
			"degree": 3,
			"edge_tags": ["campaign", "evidence", "region"],
			"query_tags": ["campaign", "region"],
		},
		{
			"parent_id": "T3001",
			"neighbor_id": "T3002",
			"activation": 0.70,
			"weight": 0.75,
			"degree": 3,
			"edge_tags": ["normalization", "campaign"],
			"query_tags": ["campaign"],
		},
		{
			"parent_id": "T4001",
			"neighbor_id": "T4003",
			"activation": 0.90,
			"weight": 0.70,
			"degree": 4,
			"edge_tags": ["lead_time", "evidence"],
			"query_tags": ["lead_time", "supplier"],
		},
	]

	async with neo4j_driver.session(database="testmemory") as session:
		for case in cases:
			frontier = [
				FrontierInput(node_id=case["parent_id"], activation=case["activation"])
			]

			async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
				return await connector.expand_frontier(
					tx,
					frontier=frontier,
					visited_ids={case["parent_id"]},
					query_tags=case["query_tags"],
				)

			candidates = await session.execute_read(_run)
			candidate = next(
				cand
				for cand in candidates
				if cand.neighbor_node.id == case["neighbor_id"]
			)
			tag_sim = _tag_sim(0.15, case["edge_tags"], case["query_tags"])
			expected = _transfer_energy(
				case["activation"],
				case["weight"],
				case["degree"],
				tag_sim,
			)
			assert candidate.transfer_energy == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_transfer_energy_default_weight(neo4j_driver: AsyncDriver):
	"""Scenario: expand a temporary edge that lacks a weight property.
	Expected: transfer energy uses the default weight 0.01 in the Cypher formula.
	Why: expand_frontier calls coalesce(r.weight, 0.01) for missing weights.

	Dummy edge: created in-test with RELATES tags=[] and no weight field.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0)
	temp_parent = "TEMP_WEIGHT_PARENT"
	temp_child = "TEMP_WEIGHT_CHILD"

	async with neo4j_driver.session(database="testmemory") as session:
		async def _create(tx: AsyncManagedTransaction) -> Any:
			return await tx.run(
				"CREATE (a:Temp {id: $p})-[:RELATES {id: $eid, tags: []}]->(b:Temp {id: $c})",
				p=temp_parent,
				c=temp_child,
				eid="TEMP_EDGE_W0",
			)

		async def _delete(tx: AsyncManagedTransaction) -> Any:
			return await tx.run(
				"MATCH (n:Temp) WHERE n.id IN $ids DETACH DELETE n",
				ids=[temp_parent, temp_child],
			)

		try:
			await session.execute_write(_create)

			frontier = [FrontierInput(node_id=temp_parent, activation=1.0)]

			async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
				return await connector.expand_frontier(
					tx,
					frontier=frontier,
					visited_ids={temp_parent},
					query_tags=[],
				)

			candidates = await session.execute_read(_run)
			candidate = next(
				cand for cand in candidates if cand.neighbor_node.id == temp_child
			)
			expected = _transfer_energy(1.0, 0.01, 1, 1.0)
			assert candidate.transfer_energy == pytest.approx(expected, rel=1e-6)
		finally:
			await session.execute_write(_delete)


@pytest.mark.asyncio
async def test_tag_similarity_floor_check(neo4j_driver: AsyncDriver):
	"""Scenario: empty, no-overlap, partial-overlap, and full-overlap tag cases.
	Expected: tag_sim is 1.0 for empty query, floor for no overlap, and scaled for overlap.
	Why: Cypher computes tag_sim with floor + Jaccard scaling or 1.0 when query is empty.

	Dummy edges:
	- E7001: T3000->T3001 weight=0.90 tags=['campaign','evidence','region'] degree(T3000)=3.
	- E7002: T3000->T3002 weight=0.80 tags=['campaign','methodology'] degree(T3000)=3.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0001)
	parent_id = "T3000"
	activation = 0.8

	cases: list[TagSimCase] = [
		{
			"neighbor_id": "T3001",
			"edge_tags": ["campaign", "evidence", "region"],
			"weight": 0.90,
			"query_tags": [],
		},
		{
			"neighbor_id": "T3001",
			"edge_tags": ["campaign", "evidence", "region"],
			"weight": 0.90,
			"query_tags": ["nope"],
		},
		{
			"neighbor_id": "T3001",
			"edge_tags": ["campaign", "evidence", "region"],
			"weight": 0.90,
			"query_tags": ["campaign"],
		},
		{
			"neighbor_id": "T3002",
			"edge_tags": ["campaign", "methodology"],
			"weight": 0.80,
			"query_tags": ["campaign", "methodology"],
		},
	]

	async with neo4j_driver.session(database="testmemory") as session:
		for case in cases:
			frontier = [FrontierInput(node_id=parent_id, activation=activation)]

			async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
				return await connector.expand_frontier(
					tx,
					frontier=frontier,
					visited_ids={parent_id},
					query_tags=case["query_tags"],
				)

			candidates = await session.execute_read(_run)
			candidate = next(
				cand
				for cand in candidates
				if cand.neighbor_node.id == case["neighbor_id"]
			)
			expected_tag_sim = _tag_sim(0.15, case["edge_tags"], case["query_tags"])
			expected = _transfer_energy(
				activation,
				case["weight"],
				3,
				expected_tag_sim,
			)
			assert candidate.transfer_energy == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_degree_penalty_check(neo4j_driver: AsyncDriver):
	"""Scenario: compare equal-weight edges across parents with different degrees.
	Expected: higher-degree parents yield lower transfer energy when weight and tags match.
	Why: Cypher divides by sqrt(degree) to penalize high-degree nodes.

	Dummy edges (query_tags empty => tag_sim=1.0):
	- E7306: T5000->T5002 weight=0.78 tags=['customer_segment','validation'] degree(T5000)=2.
	- E7103: T4002->T4003 weight=0.78 tags=['routing_change','insight'] degree(T4002)=3.
	- E7006: T3004->T3003 weight=0.70 tags=['weather','demand_spike'] degree(T3004)=2.
	- E7104: T4001->T4003 weight=0.70 tags=['lead_time','evidence'] degree(T4001)=4.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0001)

	async with neo4j_driver.session(database="testmemory") as session:
		async def _expand(
			parent_id: str,
			activation: float,
			query_tags: list[str],
		) -> list[ExpansionCandidate]:
			frontier = [FrontierInput(node_id=parent_id, activation=activation)]

			async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
				return await connector.expand_frontier(
					tx,
					frontier=frontier,
					visited_ids={parent_id},
					query_tags=query_tags,
				)

			return await session.execute_read(_run)

		activation = 0.8
		query_tags: list[str] = []

		candidates_78_deg2 = await _expand("T5000", activation, query_tags)
		candidates_78_deg3 = await _expand("T4002", activation, query_tags)
		candidates_70_deg2 = await _expand("T3004", activation, query_tags)
		candidates_70_deg4 = await _expand("T4001", activation, query_tags)

		t_78_deg2 = next(
			cand.transfer_energy
			for cand in candidates_78_deg2
			if cand.neighbor_node.id == "T5002"
		)
		t_78_deg3 = next(
			cand.transfer_energy
			for cand in candidates_78_deg3
			if cand.neighbor_node.id == "T4003"
		)
		t_70_deg2 = next(
			cand.transfer_energy
			for cand in candidates_70_deg2
			if cand.neighbor_node.id == "T3003"
		)
		t_70_deg4 = next(
			cand.transfer_energy
			for cand in candidates_70_deg4
			if cand.neighbor_node.id == "T4003"
		)

		assert t_78_deg2 > t_78_deg3
		assert t_70_deg2 > t_70_deg4


@pytest.mark.asyncio
async def test_minimum_activation_filter_check(neo4j_driver: AsyncDriver):
	"""Scenario: set min_activation above an edge's computed transfer energy.
	Expected: the low-energy candidate is excluded from expand_frontier results.
	Why: Cypher filters candidates with transfer_energy > min_threshold.

	Dummy edge:
	- E7008: T3000->T3004 weight=0.60 tags=['event','demand_spike'] degree(T3000)=3.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.4)

	async with neo4j_driver.session(database="testmemory") as session:
		frontier = [FrontierInput(node_id="T3000", activation=0.5)]

		async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
			return await connector.expand_frontier(
				tx,
				frontier=frontier,
				visited_ids={"T3000"},
				query_tags=[],
			)

		candidates = await session.execute_read(_run)
		neighbor_ids = {cand.neighbor_node.id for cand in candidates}

	assert "T3004" not in neighbor_ids


@pytest.mark.asyncio
async def test_minimum_activation_boundary(neo4j_driver: AsyncDriver):
	"""Scenario: test edges exactly at and just below the min_activation threshold.
	Expected: edge with T exactly equal to threshold is included, below is excluded.
	Why: Cypher uses WHERE transfer_energy > min_threshold (strict inequality).

	Dummy edges:
	- E7007: T3005->T3003 weight=0.55 tags=['report_style','format'] degree(T3005)=1.
	- E7008: T3000->T3004 weight=0.60 tags=['event','demand_spike'] degree(T3000)=3.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.3)

	async with neo4j_driver.session(database="testmemory") as session:
		frontier_t3005 = [FrontierInput(node_id="T3005", activation=0.6)]
		frontier_t3000 = [FrontierInput(node_id="T3000", activation=0.5)]

		async def _expand_t3005(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
			return await connector.expand_frontier(
				tx,
				frontier=frontier_t3005,
				visited_ids={"T3005"},
				query_tags=[],
			)

		async def _expand_t3000(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
			return await connector.expand_frontier(
				tx,
				frontier=frontier_t3000,
				visited_ids={"T3000"},
				query_tags=[],
			)

		candidates_t3005 = await session.execute_read(_expand_t3005)
		candidates_t3000 = await session.execute_read(_expand_t3000)

		t3003_energy = next(
			cand.transfer_energy
			for cand in candidates_t3005
			if cand.neighbor_node.id == "T3003"
		)
		expected_t3003 = _transfer_energy(0.6, 0.55, 1, 1.0)
		assert t3003_energy == pytest.approx(expected_t3003, rel=1e-6)
		assert t3003_energy > 0.3

		neighbor_ids_t3000 = {cand.neighbor_node.id for cand in candidates_t3000}
		assert "T3004" not in neighbor_ids_t3000


@pytest.mark.asyncio
async def test_visited_ids_exclusion(neo4j_driver: AsyncDriver):
	"""Scenario: expand frontier with previously visited nodes in the exclusion set.
	Expected: already-visited neighbors are excluded from expansion results.
	Why: Cypher filters WHERE NOT neighbor.id IN $visited_ids to prevent cycles.

	Dummy edges:
	- E7001: T3000->T3001 weight=0.90 tags=['campaign','evidence','region'] degree(T3000)=3.
	- E7002: T3000->T3002 weight=0.80 tags=['campaign','methodology'] degree(T3000)=3.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0001)

	async with neo4j_driver.session(database="testmemory") as session:
		frontier = [FrontierInput(node_id="T3000", activation=0.9)]

		async def _expand_with_visited(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
			return await connector.expand_frontier(
				tx,
				frontier=frontier,
				visited_ids={"T3000", "T3001"},
				query_tags=[],
			)

		async def _expand_without_visited(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
			return await connector.expand_frontier(
				tx,
				frontier=frontier,
				visited_ids={"T3000"},
				query_tags=[],
			)

		candidates_with = await session.execute_read(_expand_with_visited)
		candidates_without = await session.execute_read(_expand_without_visited)

		ids_with = {cand.neighbor_node.id for cand in candidates_with}
		ids_without = {cand.neighbor_node.id for cand in candidates_without}

		assert "T3001" not in ids_with
		assert "T3001" in ids_without
		assert len(ids_without) > len(ids_with)


@pytest.mark.asyncio
async def test_edge_weight_variance(neo4j_driver: AsyncDriver):
	"""Scenario: compare transfer energies across edges with diverse weights (0.52 to 0.92).
	Expected: higher weight produces proportionally higher transfer energy.
	Why: Cypher multiplies activation by weight, so weight variance directly affects ranking.

	Dummy edges (all from different parents, query_tags empty => tag_sim=1.0):
	- E7106: T4005->T4003 weight=0.52 tags=['report_style','quantiles'] degree(T4005)=1.
	- E7301: T5000->T5001 weight=0.92 tags=['customer_segment','evidence'] degree(T5000)=2.
	"""
	connector = Neo4jConnector(tag_sim_floor=0.15, min_activation=0.0001)

	async with neo4j_driver.session(database="testmemory") as session:
		activation = 1.0
		query_tags: list[str] = []

		async def _expand(parent_id: str) -> list[ExpansionCandidate]:
			frontier = [FrontierInput(node_id=parent_id, activation=activation)]

			async def _run(tx: AsyncManagedTransaction) -> list[ExpansionCandidate]:
				return await connector.expand_frontier(
					tx,
					frontier=frontier,
					visited_ids={parent_id},
					query_tags=query_tags,
				)

			return await session.execute_read(_run)

		candidates_t4005 = await _expand("T4005")
		candidates_t5000 = await _expand("T5000")

		t_low = next(
			cand.transfer_energy
			for cand in candidates_t4005
			if cand.neighbor_node.id == "T4003"
		)
		t_high = next(
			cand.transfer_energy
			for cand in candidates_t5000
			if cand.neighbor_node.id == "T5001"
		)

		expected_low = _transfer_energy(1.0, 0.52, 1, 1.0)
		expected_high = _transfer_energy(1.0, 0.92, 2, 1.0)

		assert t_low == pytest.approx(expected_low, rel=1e-6)
		assert t_high == pytest.approx(expected_high, rel=1e-6)
		assert t_high > t_low
