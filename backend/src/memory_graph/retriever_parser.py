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
	"""Format retrieval result for LLM consumption with simplified paths and attributes."""
	path_strings: list[str] = []
	seed_id = result.seed_node.id if result.seed_node is not None else result.seed.node_id
	
	for idx, path in enumerate(result.paths, start=1):
		parts: list[str] = []
		# Build path with [SEED] marker on seed node
		for step in path.steps:
			# If first step, add from_node with [SEED] if it's the seed
			if not parts:
				is_seed = (step.from_node.id == seed_id)
				parts.append(_format_node_for_llm(step.from_node, is_seed=is_seed))
			# Add edge and to_node
			parts.append(_format_edge_for_llm(step))
			parts.append(_format_node_for_llm(step.to_node, is_seed=False))
		
		if parts:
			path_strings.append(f"Path {idx}: " + " -> ".join(parts))

	# Build node and edge attributes
	nodes_data = _build_nodes_for_llm(result)
	edges_data = _build_edges_for_llm(result)

	return {
		"paths": path_strings,
		"node_and_edge_attributes": {
			"nodes": nodes_data,
			"edges": edges_data,
		},
	}


def to_debug_cypher(result: RetrievalResult) -> dict[str, Any]:
	"""
 		Builds cypher pattern to visualize the retrieved paths in Neo4j Browser.
		Returns a dict with two keys:
		- "paths_combined": A single cypher query that shows the full branched single path from the seed node.
		- "individual_paths": A list of cypher queries, one for each path starting from seed node.
 	"""
	seed_id = result.seed_node.id if result.seed_node is not None else result.seed.node_id
	path_patterns: list[str] = []
	for path_idx, path in enumerate(result.paths):
		node_ids = [seed_id]
		node_ids.extend(step.to_node.id for step in path.steps)
		node_patterns = [
			_cypher_node_pattern(f"n{path_idx}_{node_idx}", node_id)
			for node_idx, node_id in enumerate(node_ids)
		]
		path_patterns.append("-[:RELATES]-".join(node_patterns))

	individual_paths = [
		f"MATCH p{idx} = {pattern} RETURN p{idx}"
		for idx, pattern in enumerate(path_patterns)
	]
	if path_patterns:
		combined = (
			"MATCH "
			+ ", ".join(f"p{idx} = {pattern}" for idx, pattern in enumerate(path_patterns))
			+ " RETURN "
			+ ", ".join(f"p{idx}" for idx in range(len(path_patterns)))
		)
	else:
		combined = ""

	return {
		"paths_combined": combined,
		"individual_paths": individual_paths,
	}


def _format_node_for_llm(node: GraphNode, is_seed: bool = False) -> str:
	"""Format node for path display: [SEED] (Label ID: first 12 words...)."""
	label = node.labels[0] if node.labels else "Node"
	text = _pick_text(node.properties)
	seed_marker = "[SEED] " if is_seed else ""
	
	if text:
		text = _clean_unicode_escapes(text)
		short_text = _first_n_words(text, 12)
		ellipsis = "..." if len(text.split()) > 12 else ""
		return f"{seed_marker}({label} {node.id}: \"{short_text}{ellipsis}\")"
	return f"{seed_marker}({label} {node.id})"


def _format_edge_for_llm(step: GraphStep) -> str:
	"""Format edge for path display: [EdgeID: full text weight=X activation_score=Y]."""
	edge_id = step.edge.properties.get("id", "")
	edge_text = step.edge.properties.get("text", "")
	weight = step.edge.weight
	
	parts = []
	if edge_id:
		parts.append(edge_id)
	
	if edge_text:
		# Clean unicode escapes but don't truncate edge text
		cleaned_text = _clean_unicode_escapes(edge_text)
		parts.append(f"\"{cleaned_text}\"")
	
	if weight is not None:
		parts.append(f"weight={weight:.3f}")
	
	parts.append(f"activation_score={step.transfer_energy:.3f}")
	
	return "[" + " ".join(parts) + "]"


def _first_n_words(text: str, n: int) -> str:
	"""Return first n words of text."""
	words = text.split()
	if len(words) <= n:
		return text
	return " ".join(words[:n])


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


def _cypher_node_pattern(alias: str, node_id: str) -> str:
	escaped = _quote_cypher_literal(node_id)
	return f"({alias} {{id: {escaped}}})"


def _quote_cypher_literal(value: str) -> str:
	escaped = value.replace("\\", "\\\\").replace('"', '\\"')
	return f'"{escaped}"'


def _clean_unicode_escapes(text: str) -> str:
	"""Clean unicode escape sequences from text for better readability."""
	# Replace common unicode escapes that cause rendering issues
	if isinstance(text, str):
		text = text.replace('\\u2013', '-')  # en dash
		text = text.replace('\\u2014', '--')  # em dash
		text = text.replace('\\u2019', "'")  # right single quote
		text = text.replace('\\u201c', '"')  # left double quote
		text = text.replace('\\u201d', '"')  # right double quote
	return text


def _build_nodes_for_llm(result: RetrievalResult) -> list[dict[str, Any]]:
	"""Build flattened node data optimized for LLM consumption."""
	nodes_by_id: dict[str, GraphNode] = {}
	activation_by_id: dict[str, float] = {}

	# Collect seed node
	if result.seed_node is not None:
		nodes_by_id[result.seed_node.id] = result.seed_node
		activation_by_id[result.seed_node.id] = result.seed.score

	# Collect all nodes from paths
	for path in result.paths:
		for step in path.steps:
			for node in (step.from_node, step.to_node):
				if node.id not in nodes_by_id:
					nodes_by_id[node.id] = node
			# Track max activation for to_node
			activation_by_id[step.to_node.id] = max(
				activation_by_id.get(step.to_node.id, 0.0),
				step.transfer_energy,
			)

	# Build flattened node objects
	nodes_list = []
	for node_id, node in nodes_by_id.items():
		node_data = _flatten_node_properties(node, activation_by_id.get(node_id))
		nodes_list.append(node_data)

	return nodes_list


def _flatten_node_properties(node: GraphNode, activation: float | None) -> dict[str, Any]:
	"""Flatten node properties with short fields first, text last."""
	props = dict(node.properties)
	
	# Start with basic fields (short first)
	flattened: dict[str, Any] = {
		"id": node.id,
		"label": node.labels[0] if node.labels else "Node",
	}

	# Add special fields based on node type (these come early)
	special_fields = [
		"parameter_field", "analysis_types", "metrics",  # AgentAction, AgentAnswer
		"doc_pointer", "source_type", "relevant_parts",  # DataSource, Event
		"start_date", "end_date",  # Event
		"user_role", "user_id",  # UserRequest
		"preference_type",  # UserPreference
	]
	for field in special_fields:
		if field in props:
			flattened[field] = props[field]

	# Add common short fields
	for field in ["conv_id", "status"]:
		if field in props:
			flattened[field] = props[field]

	# Add tags
	if "tags" in props:
		flattened["tags"] = props["tags"]

	# Add retrieval activation
	if activation is not None:
		flattened["retrieval_activation"] = round(activation, 3)

	# Add timestamp fields
	for field in ["update_time", "ingestion_time", "created_time"]:
		if field in props:
			flattened[field] = props[field]

	# Add text last (longest field) - clean unicode escapes
	if "text" in props:
		flattened["text"] = _clean_unicode_escapes(props["text"])

	return flattened


def _build_edges_for_llm(result: RetrievalResult) -> list[dict[str, Any]]:
	"""Build simplified edge data optimized for LLM consumption."""
	edges_by_id: dict[str, dict[str, Any]] = {}

	for path in result.paths:
		for step in path.steps:
			edge_id = step.edge.properties.get("id")
			if not edge_id:
				continue

			if edge_id in edges_by_id:
				# Track max transfer_energy if duplicate
				edges_by_id[edge_id]["transfer_energy"] = max(
					edges_by_id[edge_id]["transfer_energy"],
					round(step.transfer_energy, 3),
				)
				continue

			# Build simplified edge object
			edge_data: dict[str, Any] = {
				"edge_id": edge_id,
				"source_node_id": step.edge.source_id,
				"target_node_id": step.edge.target_id,
				"transfer_energy": round(step.transfer_energy, 3),
			}

			# Add weight if present
			if step.edge.weight is not None:
				edge_data["weight"] = round(step.edge.weight, 2)

			# Add tags if present
			if "tags" in step.edge.properties:
				edge_data["tags"] = step.edge.properties["tags"]

			# Add created_time if present
			if "created_time" in step.edge.properties:
				edge_data["created_time"] = step.edge.properties["created_time"]

			# Add text last - clean unicode escapes
			if "text" in step.edge.properties:
				edge_data["text"] = _clean_unicode_escapes(step.edge.properties["text"])

			edges_by_id[edge_id] = edge_data

	return list(edges_by_id.values())
