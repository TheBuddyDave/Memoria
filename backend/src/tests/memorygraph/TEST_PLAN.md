Usage instructions:
1) make sure you use the conftest.py there since it works with the existing tests and the tests pass. windows has a known issue with async fixtures and event loops.
2) all tests assume that the dummy data is already loaded in the neo4j instance. the driver connects. 
3) when you run pytest, first activate virtual env as the instructions say and then run pytest. 
4) if you want to see how to write correct tests that work reference the existing tests in retriever_test.py.

## 3. Test Strategy Plan

**Goal:** Build a layered test suite that verifies mathematical correctness, Cypher behavior, BFS logic, and overall reasonableness using the dummy dataset in src/tests/memorygraph.

### 3.1. Test framework and setup

- Use `pytest` + `pytest-asyncio`.
- Add a `conftest.py` with:
    - `event_loop` fixture (pytest-asyncio standard).
    - `neo4j_driver` fixture using `AsyncGraphDatabase.driver` that is created once per test session and reused.
    - ensure session uses `database="testmemory"`.
- Tests should assume the dummy data is already loaded in the database. Do not reload or reset data during tests.
- Avoid concurrency in tests: no parallel AsyncSessions in the same test.
- Tests should be small and deterministic.

### 3.2. Phase 1: Unit tests for pure Python logic

Target: traversal state behavior _without the database_!

1) **Frontier selection and deduplication**
    - Arrange: build a fake frontier and a candidates_by_parent map with known transfer energies.
    - Act: call `select_next_frontier()` with `max_branches=2`.
    - Assert:
      - Only top 2 candidates selected per parent.
      - If two parents try to claim the same neighbor, only the highest energy wins.
      - Newly visited set contains the selected neighbors.

2) **Completed path logic**
    - Arrange: frontier nodes with paths, and zero candidates for a parent.
    - Act: call the update method.
    - Assert: frontier node is moved to `completed_paths` only if it has a non-empty path.

3) **Max depth completion**
    - Arrange: frontier nodes with existing paths at the end of loop.
    - Act: call `finalize_remaining()`.
    - Assert: all remaining paths are added.

#### Expanded Phase 1: Unit Tests for Pure Python Logic (Including Parsers)

Target: test traversal state, path construction, and output formatting without touching Neo4j.

A. Traversal state tests (no DB):

1) **Frontier selection and deduplication**
    - Initialize: `seed_node = GraphNode(id="S", labels=["Seed"], properties={})` and `traversal = GraphTraversalState(max_branches=2, seed_node=seed_node)`.
    - Build `frontier: list[FrontierNode]` with `FrontierNode(node_id, activation, path)` where `path` uses `GraphPath.empty()` or previously extended paths.
    - Create `candidates_by_parent` mapping with `ExpansionCandidate` objects whose `neighbor_node.id` intentionally collides across parents to validate that the highest `transfer_energy` wins the claim.
    - Assert: only top-2 per parent chosen, winners are chosen by energy, and `newly_visited` contains the selected neighbor ids.

2) **Completed path logic**
    - Setup a frontier node with a non-empty `path` and zero candidates in `candidates_by_parent`.
    - Call `select_next_frontier()` and assert the path is returned in `completed_paths`.

3) **Max depth completion**
    - Provide a remaining `frontier` with extended `GraphPath` objects and call `finalize_remaining()`.
    - Assert all non-empty paths are returned.

B. Parser output tests (no DB):

1) **`to_d3()` minimal sanity**
    - Minimal input: one seed node and one 1-hop path.
    - create a minimal input called `result` and assert the parsing logic correctly produces nodes and links with expected fields.

2) **`to_llm_context()` minimal sanity**
    - Using the same `result` above, call `to_llm_context(result)`.
    - Assertions:
      - The returned dict has a `paths` list with a string starting with `"Path 1: [Seed S1]"` and containing `"RELATES"` and `T=0.120` (approx formatting check).
      - The returned `graph` equals `to_d3(result)`.

3) **`to_debug_cypher()` minimal sanity**
    - Using the same `result`, call `to_debug_cypher(result)`.
    - Assertion: returns a list containing the exact Cypher pattern
      `MATCH p = (n0 {id: $id0})-[:RELATES]-(n1 {id: $id1}) RETURN p` (string equality) and that parameter placeholders correspond to the node ordering used in the path.

Notes for parser tests:
- Keep inputs minimal and deterministic.
- Use string comparisons for formatting checks, but prefer partial string assertions when whitespace/rounding may vary (e.g., `assert "RELATES" in s and "T=0.120" in s`).

### 3.3. Phase 2: Cypher + math validation tests (integration)

Target: validate the transfer energy and tag similarity computations.

1) **Transfer energy math check**
    - Test multiple edges across different parts of the dummy graph.
    - For each test case:
      - Choose a seed node from dummy_data_cypher.txt and assign a seed score R (e.g., 0.85).
      - Choose query tags (test input) to control tag overlap with edge tags from dummy data.
      - Extract edge weight and tags from dummy_data_cypher.txt.
      - Calculate parent degree D by counting RELATES edges in dummy data (or query the graph).
      - Compute expected T manually: $T = (R * w / \sqrt{d}) * tag\_sim$.
      - Run `expand_frontier` with the chosen seed and query tags, then match the candidate for the edge under test.
      - Assert returned `transfer_energy` equals expected using `pytest.approx`.
      - Include at least one case with a missing edge weight to confirm the default weight is applied.

2) **Tag similarity floor check**
    - Run expansion with empty query tags.
    - Assert that `tag_sim` used is exactly `1.0` (no tag filtering).
    - Run expansion with tags that do not overlap any edge tags.
    - Assert the transfer energy uses the `tag_sim_floor`.
    - Run a partial overlap case and a full overlap case to confirm the floor + Jaccard scaling.
    - Use at least two different edges with different tag sets to confirm behavior is consistent.

3) **Degree penalty check**
    - Identify multiple parent nodes with different degrees (at least three distinct degrees).
    - For each, choose edges with equal weights and comparable tag overlap.
    - Expect the higher degree parent to pass less energy (all else equal).
    - Document the degree counts directly from the dummy data and verify them manually.

4) **Minimum activation filter check**
    - Identify at least one candidate edge whose computed transfer energy is below `min_activation`.
    - Run `expand_frontier` and confirm the candidate is excluded from results.

5) **Data correctness guardrails**
    - Before asserting values, document each tested node and edge in the test docstring with the exact properties from dummy_data_cypher.txt.
    - The developer must read the dummy data carefully and confirm all expected values to avoid false failures.

#### Expanded Phase 3: BFS Logic + End-to-End Tests

- Building `GraphRetriever` in tests:
  - For DB-backed tests use `GraphRetriever(neo4j_driver, GraphRetrieverConfig(database="testmemory", max_depth=..., min_activation=..., max_branches=...))`.
  - For unit tests, inject a fake connector into a `GraphRetriever` instance: `retriever._connector = FakeConnector(...)` then call `_explore_single()` by creating a fake session or monkeypatching `self._driver.session` to return a fake session whose `execute_read(fn)` calls `fn(fake_tx)`.

- Collecting results from `explore()`:
  - `results = [r async for r in retriever.explore([seed], query_tags)]` and assert on `results[0].paths`, `max_depth_reached`, and `terminated_reason`.

- Add explicit tests for `seed_not_found`:
  - Create a fake connector that returns `SeedFetchResult(node=None, labels=[], found=False)` and assert returned `RetrievalResult.terminated_reason == "seed_not_found"`.

### 3.4. Phase 3: BFS logic + end-to-end tests

Target: end-to-end path formation is correct and results are reasonable.

1) **Single depth expansion**
    - Choose a seed node from dummy data with 3+ neighbors (e.g., T3000 has several).
    - Set query tags to match some edges (e.g., ['campaign']).
    - Run full exploration with `max_branches=2`.
    - Assert exactly 2 neighbors are expanded, ordered by descending transfer energy.
    - Verify the paths are 1-hop long.

2) **Multi-depth traversal**
    - Choose a seed node with at least 2 depth levels (e.g., T3000 can reach T3003 via T3002).
    - Set query tags to allow traversal (e.g., ['campaign']).
    - Run full exploration.
    - Assert paths end when below threshold or at max depth.
    - Validate that `max_depth_reached` equals the longest path length (e.g., 2 or 3).

3) **Cycle avoidance**
    - Identify if dummy data has cycles (e.g., check for bidirectional edges or loops).
    - If present, run exploration and assert no node ID repeats within any path.
    - If no cycles, skip or note that cycle avoidance is implicit.

### 3.5. Phase 4: Reasonableness tests (human-expected relevance)

Target: ensure the algorithm retrieves plausible memory paths given the dummy data.

1) **Expected path retrieval**
    - Define 2-3 scenarios: seed node + query tags with obvious topical matches.
    - Read dummy_data_cypher.txt to document why edges are favored (high weight, tag overlap etc).
    - Run exploration and assert the returned paths include those expected sequences. leave some flexibility tho, we are testing reasonableness, not exact matches. There are some completely unreasonable paths that should be excluded for any seed and user query. We want to make sure those are excluded while seeing if the reasonable ones are included.

2) **Unexpected path rejection**
    - Identify edges that are weakly connected or off-topic (e.g., low weight like 0.35 from T3003 to T4001).
    - Run with default thresholds and assert these paths are absent.

3) **Threshold sensitivity**
    - Pick a scenario where a path is absent at default `min_activation` (e.g., 0.005).
    - Lower the threshold (e.g., to 0.002) and rerun.
    - Assert the new path appears only with the lower threshold.

### 3.6. Test documentation requirements

- Every test must include a docstring that states:
  - Scenario
  - Expected output
  - Why it should hold (math or dummy data reasoning)
- Add inline comments only for non-obvious constants or calculations.
- make sure you carefully read graph_retriever.py, models.py, retriever_parser.py, and dummy_data_cypher.txt to avoid misreading the data. It's pivotal that the "ecpected" values in tests are correct based on the dummy data that exists. It's also pivotal that tests call the correct functions and initialize them correctly.

### 3.7. Additional Implementation Details and Parser Tests

- Best practices / gotchas:
  - Tests must avoid creating multiple concurrent `AsyncSession` objects in the same test function; share a single `neo4j_session` or use sequential `async with` blocks.
  - For unit tests that should not touch the DB, patch or inject a fake `Neo4jConnector` into `GraphRetriever` (e.g., `retriever._connector = FakeConnector(...)`) or call `GraphTraversalState` directly.
  - The `GraphRetriever.explore()` API returns an async iterator; collect results with `results = [r async for r in retriever.explore([seed], query_tags)]` or `async for r in retriever.explore(...): ...`.
  - To avoid waiting during retry tests, set `GraphRetrieverConfig(max_retries=0)`.
  - Use `pytest.approx` for floating-point comparisons.

