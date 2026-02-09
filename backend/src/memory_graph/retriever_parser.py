"""Output parsing and formatting helpers for graph retrieval."""

from __future__ import annotations

from typing import Any

from .models import GraphNode, GraphStep, RetrievalResult


def to_d3(result: RetrievalResult) -> dict[str, Any]:
	nodes_by_id: dict[str, dict[str, Any]] = {}
	links_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
	activation_by_id: dict[str, float] = {}

	if result.seed_node is not None:
		nodes_by_id[result.seed_node.id] = {
			"id": result.seed_node.id,
			"labels": list(result.seed_node.labels),
			"properties": dict(result.seed_node.properties),
			"activation": result.seed.score,
			"score": result.seed.score,
		}
		activation_by_id[result.seed_node.id] = result.seed.score

	for path in result.paths:
		for step in path.steps:
			for node in (step.from_node, step.to_node):
				if node.id not in nodes_by_id:
					nodes_by_id[node.id] = {
						"id": node.id,
						"labels": list(node.labels),
						"properties": dict(node.properties),
						"activation": None,
						"score": None,
					}
			activation_by_id[step.to_node.id] = max(
				activation_by_id.get(step.to_node.id, 0.0),
				step.transfer_energy,
			)

			edge_key = (step.edge.source_id, step.edge.target_id, step.edge.type)
			if edge_key not in links_by_key:
				links_by_key[edge_key] = {
					"source": step.edge.source_id,
					"target": step.edge.target_id,
					"type": step.edge.type,
					"weight": step.edge.weight,
					"tags": list(step.edge.tags),
					"transfer_energy": step.transfer_energy,
					"properties": dict(step.edge.properties),
				}
			else:
				links_by_key[edge_key]["transfer_energy"] = max(
					links_by_key[edge_key].get("transfer_energy", 0.0),
					step.transfer_energy,
				)

	for node_id, activation in activation_by_id.items():
		if node_id in nodes_by_id:
			nodes_by_id[node_id]["activation"] = activation

	return {
		"nodes": list(nodes_by_id.values()),
		"links": list(links_by_key.values()),
	}


def to_llm_context(result: RetrievalResult) -> dict[str, Any]:
	path_strings: list[str] = []
	for idx, path in enumerate(result.paths, start=1):
		parts: list[str] = []
		seed_node = result.seed_node
		if seed_node is not None:
			parts.append(_format_seed(seed_node))
		else:
			parts.append(f"[Seed {result.seed.node_id}]")
		for step in path.steps:
			parts.append(_format_edge(step))
			parts.append(_format_node(step.to_node))
		path_strings.append(f"Path {idx}: " + " -> ".join(parts))

	return {
		"paths": path_strings,
		"graph": to_d3(result),
	}


def to_debug_cypher(result: RetrievalResult) -> list[str]:
	queries: list[str] = []
	for path in result.paths:
		node_ids: list[str] = []
		if result.seed_node is not None:
			node_ids.append(result.seed_node.id)
		else:
			node_ids.append(result.seed.node_id)
		node_ids.extend(step.to_node.id for step in path.steps)

		pattern_parts = []
		for idx, node_id in enumerate(node_ids):
			param_key = f"id{idx}"
			pattern_parts.append(f"(n{idx} {{id: ${param_key}}})")
		pattern = "-[:RELATES]-".join(pattern_parts)
		queries.append(f"MATCH p = {pattern} RETURN p")
	return queries


def _format_seed(node: GraphNode) -> str:
	label = node.labels[0] if node.labels else "Node"
	text = _pick_text(node.properties)
	if text:
		return f"[Seed {node.id}] ({label}: \"{text}\")"
	return f"[Seed {node.id}] ({label})"


def _format_node(node: GraphNode) -> str:
	label = node.labels[0] if node.labels else "Node"
	text = _pick_text(node.properties)
	if text:
		return f"({label}: \"{text}\")"
	return f"({label} {node.id})"


def _format_edge(step: GraphStep) -> str:
	weight = step.edge.weight
	if weight is None:
		return f"[{step.edge.type} T={step.transfer_energy:.3f}]"
	return f"[{step.edge.type} w={weight:.3f} T={step.transfer_energy:.3f}]"


def _pick_text(properties: dict[str, Any]) -> str | None:
	for key in ("title", "name", "text", "summary", "description"):
		value = properties.get(key)
		if isinstance(value, str) and value.strip():
			return _truncate(value.strip(), 140)
	return None


def _truncate(value: str, limit: int) -> str:
	if len(value) <= limit:
		return value
	return value[: limit - 3].rstrip() + "..."
