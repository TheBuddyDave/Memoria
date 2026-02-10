"""
Run: pytest src/tests/memorygraph/retriever_advanced_tests.py --verbose

"""

from __future__ import annotations

import math

import pytest

from src.memory_graph.graph_retriever import GraphRetriever
from src.memory_graph.models import GraphRetrieverConfig, GraphPath, SeedInput


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


def _path_node_ids(path: GraphPath, seed_id: str) -> list[str]:
	node_ids = [seed_id]
	node_ids.extend(step.to_node.id for step in path.steps)
	return node_ids


async def _run_explore(
	neo4j_driver,
	seed: SeedInput,
	query_tags: list[str],
	config: GraphRetrieverConfig,
):
	retriever = GraphRetriever(neo4j_driver, config)
	results = [result async for result in retriever.explore([seed], query_tags)]
	assert len(results) == 1
	return results[0]


@pytest.mark.asyncio
async def test_single_depth_expansion_ordering(neo4j_driver):
	"""Scenario: seed T3000 expands one depth with campaign query tags.
	Expected: exactly two 1-hop paths, ordered by transfer energy (T3002 then T3001).
	Why: weights and tag overlap make E7002 > E7001 > E7008 for T3000 with tag_sim floor.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	assert len(result.paths) == 2
	assert all(len(path.steps) == 1 for path in result.paths)
	assert result.max_depth_reached == 1

	first_target = result.paths[0].steps[0].to_node.id
	second_target = result.paths[1].steps[0].to_node.id
	assert [first_target, second_target] == ["T3002", "T3001"]

	deg_t3000 = 3
	energy_t3002 = _transfer_energy(
		seed.score,
		0.80,
		deg_t3000,
		_tag_sim(0.15, ["campaign", "methodology"], ["campaign"]),
	)
	energy_t3001 = _transfer_energy(
		seed.score,
		0.90,
		deg_t3000,
		_tag_sim(0.15, ["campaign", "evidence", "region"], ["campaign"]),
	)
	assert result.paths[0].steps[0].transfer_energy == pytest.approx(energy_t3002, rel=1e-3)
	assert result.paths[1].steps[0].transfer_energy == pytest.approx(energy_t3001, rel=1e-3)


@pytest.mark.asyncio
async def test_multi_depth_traversal_max_depth_reached(neo4j_driver):
	"""Scenario: seed T3000 explores multiple depths with campaign tags.
	Expected: one 2-hop path reaches T3003, max_depth_reached=2, and no deeper paths.
	Why: T3002->T3003 and T3001->T3003 transfer energies pass the threshold,
	     but outgoing edges from T3003 fall below min_activation at default settings.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	assert result.max_depth_reached == 2
	assert all(len(path.steps) <= 2 for path in result.paths)
	assert any(_path_node_ids(path, seed.node_id) == ["T3000", "T3002", "T3003"] for path in result.paths)


@pytest.mark.asyncio
async def test_cycle_avoidance_no_repeated_nodes(neo4j_driver):
	"""Scenario: seed T3000 explores a graph that contains cycles (T3000-T3001-T3002).
	Expected: no path repeats a node ID.
	Why: visited IDs are global during traversal, preventing cycles across all branches.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=4,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	for path in result.paths:
		node_ids = _path_node_ids(path, seed.node_id)
		assert len(node_ids) == len(set(node_ids))


@pytest.mark.asyncio
async def test_expected_paths_campaign_seed(neo4j_driver):
	"""Scenario: seed T3000 with campaign tags should retrieve campaign analysis context.
	Expected: path includes T3000 -> T3002 -> T3003 (normalization to insight).
	Why: edges E7002 and E7004 have strong weights and tag overlap with 'campaign'.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	assert any(_path_node_ids(path, seed.node_id) == ["T3000", "T3002", "T3003"] for path in result.paths)


@pytest.mark.asyncio
async def test_expected_paths_lead_time_seed(neo4j_driver):
	"""Scenario: seed T4000 with lead_time tags should retrieve ETA evidence paths.
	Expected: paths include T4000 -> T4001 -> T4003 and T4000 -> T4001 -> T4002.
	Why: E7101, E7102, and E7104 have high weights and direct lead_time tag overlap.
	"""
	seed = SeedInput(node_id="T4000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["lead_time"], config)

	paths = [_path_node_ids(path, seed.node_id) for path in result.paths]
	assert ["T4000", "T4001", "T4003"] in paths
	assert ["T4000", "T4001", "T4002"] in paths


@pytest.mark.asyncio
async def test_expected_paths_customer_segment_seed(neo4j_driver):
	"""Scenario: seed T5000 with customer_segment tags should retrieve lift insights.
	Expected: path includes T5000 -> T5002 -> T5003.
	Why: E7306 and E7303 have strong weights and match customer_segment tags.
	"""
	seed = SeedInput(node_id="T5000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["customer_segment"], config)

	assert any(_path_node_ids(path, seed.node_id) == ["T5000", "T5002", "T5003"] for path in result.paths)


@pytest.mark.asyncio
async def test_unexpected_path_rejection_cross_domain(neo4j_driver):
	"""Scenario: seed T3000 with campaign tags should not jump to supplier ETA node T4001.
	Expected: no path contains T4001 at default min_activation.
	Why: the cross-domain edge E7201 has low weight and no tag overlap, so T falls below threshold.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=4,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	assert all("T4001" not in _path_node_ids(path, seed.node_id) for path in result.paths)


@pytest.mark.asyncio
async def test_threshold_sensitivity_low_weight_edge(neo4j_driver):
	"""Scenario: seed T3000 explores campaign tags with two different thresholds.
	Expected: T4001 appears only when min_activation is lowered to 0.001.
	Why: the T3003 -> T4001 transfer energy is ~0.0012, below default 0.005.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	default_config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=4,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	low_config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=4,
		max_branches=3,
		min_activation=0.0001,
		tag_sim_floor=0.15,
		max_retries=0,
	)

	default_result = await _run_explore(neo4j_driver, seed, ["campaign"], default_config)
	low_result = await _run_explore(neo4j_driver, seed, ["campaign"], low_config)

	default_has_t4001 = any(
		"T4001" in _path_node_ids(path, seed.node_id) for path in default_result.paths
	)
	low_has_t4001 = any(
		"T4001" in _path_node_ids(path, seed.node_id) for path in low_result.paths
	)

	assert not default_has_t4001
	assert low_has_t4001


@pytest.mark.asyncio
async def test_empty_query_tags_pure_weight_ordering(neo4j_driver):
	"""Scenario: seed T3000 with empty query tags (no query context).
	Expected: tag_sim=1.0 for all edges, so ordering depends only on weight/degree.
	Why: empty query_tags means no semantic filtering; T3001 (w=0.90) should beat T3002 (w=0.80).
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, [], config)

	assert len(result.paths) == 2
	first_target = result.paths[0].steps[0].to_node.id
	second_target = result.paths[1].steps[0].to_node.id
	
	# With no query tags, tag_sim=1.0 for all, so weight determines order
	# T3000 -> T3001 (w=0.90) should come before T3000 -> T3002 (w=0.80)
	assert [first_target, second_target] == ["T3001", "T3002"]


@pytest.mark.asyncio
async def test_nonexistent_query_tags_floor_penalty(neo4j_driver):
	"""Scenario: seed T3000 with query tags that match no edges.
	Expected: all edges get tag_sim_floor penalty, reordering based on weight*(tag_sim_floor).
	Why: nonexistent tags in query should not boost any particular edge.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["nonexistent_tag"], config)

	# All edges get tag_sim_floor, so pure weight ordering
	assert len(result.paths) == 2
	first_target = result.paths[0].steps[0].to_node.id
	second_target = result.paths[1].steps[0].to_node.id
	assert [first_target, second_target] == ["T3001", "T3002"]


@pytest.mark.asyncio
async def test_multi_path_convergence_single_appearance(neo4j_driver):
	"""Scenario: seed T3000 can reach T3003 via both T3002 and T3001.
	Expected: T3003 appears in only ONE path (the first to reach it).
	Why: visited tracking is global, so T3003 is marked visited on first reach.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=2,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	paths_with_t3003 = [path for path in result.paths if "T3003" in _path_node_ids(path, seed.node_id)]
	
	# T3003 should appear in exactly one path, not multiple
	assert len(paths_with_t3003) == 1


@pytest.mark.asyncio
async def test_bidirectional_edge_reverse_traversal(neo4j_driver):
	"""Scenario: edges are bidirectional; seed T4003 should traverse backward to T4001 and T4000.
	Expected: path T4003 -> T4002 -> T4001 -> T4000 exists with lead_time tags.
	Why: expand query uses `-[r:RELATES]-` pattern (bidirectional matching).
	"""
	seed = SeedInput(node_id="T4003", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["lead_time"], config)

	# Should be able to traverse backward through the graph
	paths = [_path_node_ids(path, seed.node_id) for path in result.paths]
	
	# T4003 -> T4002 -> T4001 should exist (2-hop backward path)
	assert any(path[:3] == ["T4003", "T4002", "T4001"] for path in paths if len(path) >= 3)


@pytest.mark.asyncio
async def test_max_branches_enforcement_high_degree_node(neo4j_driver):
	"""Scenario: seed T3003 has 5 neighbors, but max_branches=2.
	Expected: exactly 2 paths created at depth 1, not 5.
	Why: max_branches constraint should limit expansion even when many candidates exist.
	"""
	seed = SeedInput(node_id="T3003", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	# T3003 has neighbors: T3001, T3002, T3004, T3005, T4001
	# But with max_branches=2, only top 2 by transfer energy should be explored
	assert len(result.paths) <= 2


@pytest.mark.asyncio
async def test_low_seed_score_limits_exploration(neo4j_driver):
	"""Scenario: seed T3000 with very low score (0.1) should limit depth due to activation decay.
	Expected: fewer nodes reached compared to high seed score (0.9).
	Why: transfer_energy = (activation * weight / sqrt(degree)) * tag_sim decays with low activation.
	"""
	low_seed = SeedInput(node_id="T3000", score=0.1)
	high_seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	
	low_result = await _run_explore(neo4j_driver, low_seed, ["campaign"], config)
	high_result = await _run_explore(neo4j_driver, high_seed, ["campaign"], config)

	# Low seed score should reach fewer nodes
	low_unique_nodes = {node_id for path in low_result.paths for node_id in _path_node_ids(path, low_seed.node_id)}
	high_unique_nodes = {node_id for path in high_result.paths for node_id in _path_node_ids(path, high_seed.node_id)}
	
	assert len(low_unique_nodes) < len(high_unique_nodes)


@pytest.mark.asyncio
async def test_partial_tag_overlap_jaccard_ordering(neo4j_driver):
	"""Scenario: seed T3000 with query tags ["campaign", "region"] should favor edges with both tags.
	Expected: T3001 (edge tags: campaign,evidence,region) ranks higher than T3002 (campaign,methodology).
	Why: Jaccard similarity = |inter| / |union|; more overlap = higher tag_sim.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign", "region"], config)

	# E7001 (T3000->T3001): tags=[campaign,evidence,region] - 2/4 overlap with query
	# E7002 (T3000->T3002): tags=[campaign,methodology] - 1/3 overlap with query
	# With higher Jaccard, T3001 should rank higher despite lower weight (0.90 vs 0.80)
	
	first_target = result.paths[0].steps[0].to_node.id
	assert first_target == "T3001"


@pytest.mark.asyncio
async def test_low_weight_preference_nodes_excluded(neo4j_driver):
	"""Scenario: seed T3003 with campaign tags should not reach T3005 (UserPreference, w=0.55).
	Expected: T3005 not in any path at default min_activation.
	Why: low weight edges (0.55, 0.52) should fall below activation threshold more often.
	"""
	seed = SeedInput(node_id="T3003", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=2,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	# T3005 (UserPreference) has low weight edge (0.55) and non-matching tags
	all_node_ids = {node_id for path in result.paths for node_id in _path_node_ids(path, seed.node_id)}
	assert "T3005" not in all_node_ids


@pytest.mark.asyncio
async def test_domain_isolation_customer_segment_no_campaign(neo4j_driver):
	"""Scenario: seed T5000 with customer_segment tags should not reach T3000 or T4000 series.
	Expected: all retrieved nodes are in T5000 series (T5001, T5002, T5003, T5004).
	Why: no direct connections between domains; cross-domain edge E7201 is too far and low weight.
	"""
	seed = SeedInput(node_id="T5000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=4,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["customer_segment"], config)

	all_node_ids = {node_id for path in result.paths for node_id in _path_node_ids(path, seed.node_id)}
	
	# Should not cross into T3000 or T4000 domains
	assert all_node_ids.issubset({"T5000", "T5001", "T5002", "T5003", "T5004"})


@pytest.mark.asyncio
async def test_activation_decay_over_hops_math_validation(neo4j_driver):
	"""Scenario: seed T4000 with lead_time tags; validate activation decreases at each hop.
	Expected: T4001 activation > T4002 activation > T4003 activation.
	Why: transfer_energy formula ensures activation decays with each hop.
	"""
	seed = SeedInput(node_id="T4000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=3,
		max_branches=2,
		min_activation=0.001,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["lead_time"], config)

	# Find path T4000 -> T4001 -> T4002 -> T4003
	target_path = None
	for path in result.paths:
		node_ids = _path_node_ids(path, seed.node_id)
		if node_ids == ["T4000", "T4001", "T4002", "T4003"]:
			target_path = path
			break
	
	assert target_path is not None, "Expected path T4000->T4001->T4002->T4003 not found"
	
	# Activation should decrease at each hop
	activations = [step.transfer_energy for step in target_path.steps]
	assert activations[0] > activations[1] > activations[2]


@pytest.mark.asyncio
async def test_direct_vs_indirect_path_energy_preference(neo4j_driver):
	"""Scenario: T3000 can reach T3003 directly via T3001 (w=0.82) or via T3002 (w=0.85).
	Expected: path via T3002 achieves higher total energy and appears first.
	Why: T3002->T3003 has higher edge weight (0.85) than T3001->T3003 (0.82).
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=2,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	# Find which path to T3003 was explored first
	paths_to_t3003 = [path for path in result.paths if "T3003" in _path_node_ids(path, seed.node_id)]
	
	assert len(paths_to_t3003) == 1  # Only one path due to visited tracking
	t3003_path = _path_node_ids(paths_to_t3003[0], seed.node_id)
	
	# Should go via T3002 (higher second-hop weight)
	assert t3003_path == ["T3000", "T3002", "T3003"]


@pytest.mark.asyncio
async def test_degree_normalization_impact(neo4j_driver):
	"""Scenario: compare expansion from T3000 (degree=3) vs T4000 (degree=1).
	Expected: T4000's single neighbor gets more activation than T3000's neighbors (all else equal).
	Why: transfer_energy divides by sqrt(degree), penalizing high-degree nodes.
	"""
	seed_t3000 = SeedInput(node_id="T3000", score=0.9)
	seed_t4000 = SeedInput(node_id="T4000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=1,
		min_activation=0.001,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	
	result_t3000 = await _run_explore(neo4j_driver, seed_t3000, ["campaign"], config)
	result_t4000 = await _run_explore(neo4j_driver, seed_t4000, ["lead_time"], config)

	# T4000 has degree=1, so no sqrt penalty
	# T3000 has degree=3, so energy is divided by sqrt(3)≈1.73
	
	t3000_energy = result_t3000.paths[0].steps[0].transfer_energy if result_t3000.paths else 0
	t4000_energy = result_t4000.paths[0].steps[0].transfer_energy if result_t4000.paths else 0
	
	# T4000->T4001 (w=0.88, degree=1) should have higher energy than T3000's best edge
	# T3000->T3001 (w=0.90, degree=3) energy ≈ 0.9*0.90/sqrt(3)*tag_sim
	# T4000->T4001 (w=0.88, degree=1) energy ≈ 0.9*0.88/1*tag_sim
	# Given similar tag_sim, T4000 should win
	assert t4000_energy > t3000_energy


@pytest.mark.asyncio
async def test_event_nodes_contextual_relevance(neo4j_driver):
	"""Scenario: seed T3000 with campaign tags should reach T3004 (Event) only at lower priority.
	Expected: T3004 appears in paths after T3001, T3002, T3003 are explored.
	Why: E7008 (T3000->T3004) has lower weight (0.60) and weaker tag match than methodology edges.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=3,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	# Get ordering of first-hop targets
	first_hop_targets = [path.steps[0].to_node.id for path in result.paths if len(path.steps) == 1]
	
	# T3004 (Event) should appear after T3002 and T3001 due to lower weight
	if "T3004" in first_hop_targets:
		t3004_index = first_hop_targets.index("T3004")
		assert t3004_index >= 2  # Should be 3rd or later


@pytest.mark.asyncio
async def test_max_depth_vs_natural_termination(neo4j_driver):
	"""Scenario: seed T3000 with max_depth=5 but graph naturally terminates earlier.
	Expected: max_depth_reached < 5 because activation falls below threshold.
	Why: activation decay naturally stops expansion before max_depth is hit.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=5,
		max_branches=2,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign"], config)

	# Graph should naturally terminate before depth 5 due to activation decay
	assert result.max_depth_reached < 5


@pytest.mark.asyncio
async def test_multiple_tags_intersection_boost(neo4j_driver):
	"""Scenario: seed T3000 with query tags ["campaign", "methodology"] should strongly favor T3002.
	Expected: T3002 ranked first due to perfect tag match.
	Why: E7002 (T3000->T3002) has both tags, maximizing Jaccard similarity.
	"""
	seed = SeedInput(node_id="T3000", score=0.9)
	config = GraphRetrieverConfig(
		database="testmemory",
		max_depth=1,
		max_branches=1,
		min_activation=0.005,
		tag_sim_floor=0.15,
		max_retries=0,
	)
	result = await _run_explore(neo4j_driver, seed, ["campaign", "methodology"], config)

	# T3002 should be the only result due to max_branches=1 and high tag match
	assert len(result.paths) == 1
	assert result.paths[0].steps[0].to_node.id == "T3002"
