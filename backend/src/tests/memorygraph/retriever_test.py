"""Docstring for src.tests.memorygraph.retriever_test.

Run: pytest src/tests/memorygraph -q
"""

from __future__ import annotations

import math
from typing import Any, TypedDict
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
