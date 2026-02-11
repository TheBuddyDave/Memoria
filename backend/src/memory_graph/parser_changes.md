## Parser Output Changes

### `to_debug_cypher()` - BREAKING CHANGE

#### Old Output Format
Returns a `list[str]` of individual Cypher queries with parameterized IDs:
```python
[
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p",
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p",
  "MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1})-[:RELATES]-(n2 {id: $id2}) RETURN p",
]
```

#### New Output Format
Returns a `dict[str, Any]` with **literal embedded IDs** and both individual + combined queries:
```python
{
  "paths_combined": "MATCH p0 = (n0_0 {id: \"N3204\"})-[:RELATES]-(n0_1 {id: \"N5001\"}), p1 = (n1_0 {id: \"N3204\"})-[:RELATES]-(n1_1 {id: \"N5002\"}) RETURN p0, p1",
  "individual_paths": [
    "MATCH p0 = (n0_0 {id: \"N3204\"})-[:RELATES]-(n0_1 {id: \"N5001\"}) RETURN p0",
    "MATCH p1 = (n1_0 {id: \"N3204\"})-[:RELATES]-(n1_1 {id: \"N5002\"}) RETURN p1",
  ]
}
```

#### Key Changes
1. **Literal IDs**: IDs are now embedded directly in the query strings (no `$id0` parameters). This makes queries executable without parameter binding.
2. **Return type**: Changed from `list[str]` to `dict[str, Any]`.
3. **Two query variants**:
   - `individual_paths`: List of standalone Cypher queries, one per branch (for debugging single paths)
   - `paths_combined`: A single multi-MATCH statement showing all branches connected to the same seed node (for visualizing the algorithm's full exploration)
4. **Node aliases**: Each path gets unique node aliases (`n{path_idx}_{node_idx}`) to avoid collisions when running the combined query.
5. **ID escaping**: Literal strings are properly escaped (backslash and quote handling) to ensure valid Cypher syntax.

#### Test Migration Guide
- Any tests expecting `list[str]` must be updated to expect `dict[str, Any]`.
- Update assertions to check `result["individual_paths"]` for single-path queries.
- Update assertions to check `result["paths_combined"]` for multi-path graph visualization.
- Tests should verify that IDs are literal strings (e.g., `"N3204"`) rather than parameterized (`$id0`).

---

### `to_llm_context()` - BREAKING CHANGE

#### Purpose
Formats retrieval results for LLM consumption with minimal token overhead. Provides high-level path structure and detailed attributes separately for efficient context utilization.

#### Old Output Format
```python
{
  "paths": [
    "Path 1: [Seed N3204] (AgentAction: \"Design targeted 5% discount pilot on high-sensitivity segments; simulate redemption/lift (P10–P90)...\") -> [RELATES w=0.910 T=0.041] -> (Event: \"Targeted discount A/B pilot...\")\"
  ],
  "graph": {
    "nodes": [...],  # Full to_d3() output with nested properties
    "links": [...]
  }
}
```

#### New Output Format
Returns a `dict[str, Any]` with simplified paths and flattened attributes:
```python
{
  "paths": [
    "Path 1: [SEED] (AgentAction N3204: \"Design targeted 5% discount pilot on high-sensitivity segments; simulate redemption/lift...\") -> [E3423 \"Pilot window triggers experimental design and simulation.\" weight=0.910 activation_score=0.041] -> (Event N3201: \"Targeted discount A/B pilot window with cluster-level randomization; objective: revenue-neutral lift...\")"
  ],
  "node_and_edge_attributes": {
    "nodes": [
      {
        "id": "N3204",
        "label": "AgentAction",
        "parameter_field": "{\"discount_pct\":0.05, \"analysis\":[\"CUPED\",\"FE\"], \"clusters\":64}",
        "conv_id": "2025-11-12_WMT_P3_C32",
        "status": "complete",
        "tags": ["pilot_design", "simulation", "revenue_neutrality"],
        "retrieval_activation": 0.73,
        "update_time": "2025-11-12T16:43:10-05:00",
        "ingestion_time": "2025-11-12T16:43:10-05:00",
        "text": "Design targeted 5% discount pilot..."
      }
    ],
    "edges": [
      {
        "edge_id": "E3423",
        "source_node_id": "N3204",
        "target_node_id": "N3201",
        "transfer_energy": 0.041,
        "weight": 0.91,
        "tags": ["trigger", "experiment"],
        "created_time": "2025-11-12T16:43:25-05:00",
        "text": "Pilot window triggers experimental design and simulation."
      }
    ]
  }
}
```

#### Key Changes: Paths

1. **Added `[SEED]` marker**: Seed node (highest vector search relevance) is explicitly marked for clarity
2. **Node format**: `(Label ID: "first 12 words...")` 
   - Added node IDs for reference
   - Truncated text to first 12 words with "..." to preserve semantic meaning while keeping tokens manageable
   - Full text available in `node_and_edge_attributes`
3. **Edge format**: `[EdgeID "full edge text" weight=X activation_score=Y]` 
   - Shows edge ID for reference
   - Shows **full edge text** (no truncation) - critical for understanding relationship semantics
   - Changed `w=` → `weight=`, `T=` → `activation_score=` for clarity
4. **Clean text rendering**: Fixed unicode escape sequences (e.g., `\u2013` → `-`) for better readability

#### Key Changes: Node & Edge Attributes

**Structure:**
- Renamed `"graph"` → `"node_and_edge_attributes"` for clarity
- Renamed `"links"` → `"edges"` for consistency
- **Flattened all structures**: No nested `"properties"` dict

**Nodes:**
1. **Label singular**: `"label": "AgentAction"` instead of `"labels": ["AgentAction"]`
2. **Flattened properties**: All node attributes at top level (no nesting)
3. **Field ordering**: Short fields first (id, label, special fields, conv_id, status, tags), timestamps next, text last
4. **Special fields by node type**: Included early in the dict
   - AgentAction: `parameter_field`, `status`
   - AgentAnswer: `analysis_types`, `metrics`
   - DataSource: `doc_pointer`, `source_type`, `relevant_parts`
   - Event: `source_type`, `start_date`, `end_date`
   - UserRequest: `user_role`, `user_id`
   - UserPreference: `preference_type`
5. **Renamed activation**: `"activation"` → `"retrieval_activation"` for clarity
6. **Tags preserved**: `"tags"` field included for semantic categorization and quick filtering
7. **Removed fields**: `embedding_id`, `reasoning_pointer_ids`, `score` (internal/redundant)
8. **Text cleaning**: Only unicode escape sequences cleaned (e.g., `\u2013` → `-`); other fields kept as-is for accuracy

**Edges:**
1. **Renamed fields for clarity**:
   - `"id"` → `"edge_id"` 
   - `"source"` → `"source_node_id"`
   - `"target"` → `"target_node_id"`
2. **Rounded precision**: `transfer_energy` rounded to 3 decimals, `weight` to 2 decimals
3. **Tags preserved**: `"tags"` field included for relationship categorization
4. **Removed fields**: `"type"` (always "RELATES")
5. **Flattened**: All edge attributes at top level
6. **Field ordering**: Short fields first (IDs, numbers), tags and timestamps next, text last
7. **Text cleaning**: Only unicode escape sequences cleaned; otherwise kept as-is for accuracy

#### Design Rationale

**Paths**: Provides high-level graph structure for LLM to understand relationships and traversal paths. The `[SEED]` marker identifies the highest-relevance entry point from vector search. Node text truncated to 12 words with "..." balances semantic clarity with token efficiency. **Edge text is NOT truncated** because relationship semantics are critical for understanding graph connectivity - destroying edge context would undermine the value of graph traversal. Full details available in `node_and_edge_attributes`.

**Node & Edge Attributes**: Provides complete details for any node/edge the LLM wants to examine. Flattened structure reduces parsing complexity. Field ordering optimizes for quick scanning (short identifiers first, long text content last). **Tags are preserved** because they provide dense semantic categorization that aids filtering and understanding. **Data accuracy prioritized**: Only text fields have unicode escapes cleaned; all other fields (e.g., `parameter_field`) maintain original formatting for programmatic parsability.

**Token Efficiency**: Removed truly redundant information (embedding IDs, reasoning pointers) that don't aid LLM reasoning. Kept semantically valuable data (tags, full edge text, accurate field values) even at modest token cost.

#### Test Migration Guide
- Update assertions to expect `"paths"` with `[SEED]` marker on seed nodes
- Expect node format: `[SEED] (Label NodeID: "first 12 words...")` or `(Label NodeID: "first 12 words...")`
- Expect edge format: `[EdgeID "full edge text" weight=X activation_score=Y]` (edges NOT truncated)
- Replace `result["graph"]` → `result["node_and_edge_attributes"]`
- Replace `result["graph"]["links"]` → `result["node_and_edge_attributes"]["edges"]`
- Update node assertions to expect flat structure with `"label"` (singular) instead of `"labels"` (array)
- Update node assertions to expect `"retrieval_activation"` instead of `"activation"`
- Update node assertions to expect `"tags"` field preserved
- Update edge assertions to expect `"edge_id"`, `"source_node_id"`, `"target_node_id"` instead of `"id"`, `"source"`, `"target"`
- Update edge assertions to expect `"tags"` field preserved
- Verify `transfer_energy` has 3 decimal places, `weight` has 2 decimal places
- Verify text fields have unicode escapes cleaned (e.g., `\u2013` → `-`)