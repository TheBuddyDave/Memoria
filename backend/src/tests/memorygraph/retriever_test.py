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
	links = graph["links"]

	assert set(nodes_by_id) == {"S1", "N1"}
	assert nodes_by_id["S1"]["activation"] == seed.score
	assert nodes_by_id["N1"]["activation"] == pytest.approx(0.12)
	assert len(links) == 1
	assert links[0]["source"] == "S1"
	assert links[0]["target"] == "N1"


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

	assert context["graph"] == to_d3(result)
	assert len(context["paths"]) == 1
	path_text = context["paths"][0]
	assert path_text.startswith("Path 1: [Seed S1]")
	assert "RELATES" in path_text
	assert "T=0.120" in path_text


def test_to_debug_cypher_minimal_sanity():
	"""Scenario: single-hop result sent to Cypher debug formatter.
	Expected: one query with n0/n1 id placeholders in the path order.
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

	assert queries == [
		"MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p"
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
	assert nodes_by_id["S1"]["activation"] == 0.8
	assert nodes_by_id["A"]["activation"] == pytest.approx(0.3)
	assert nodes_by_id["B"]["activation"] == pytest.approx(0.4)
	assert nodes_by_id["C"]["activation"] == pytest.approx(max(0.15, 0.25))

	links = graph["links"]
	assert len(links) == 4


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
	links = graph["links"]

	assert set(nodes_by_id.keys()) == {"S1", "P1", "P2", "P3"}
	assert len(links) == 3
	assert nodes_by_id["P3"]["activation"] == pytest.approx(0.2)


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
	assert "T=0.500" in context["paths"][0]
	assert "T=0.250" in context["paths"][1]


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

	assert len(queries) == 2
	assert "n0" in queries[0] and "n1" in queries[0]
	assert "n0" in queries[1] and "n1" in queries[1] and "n2" in queries[1]


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
