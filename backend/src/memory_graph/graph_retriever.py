"""
GraphRetriever: Activation Energy algorithm for graph-based memory retrieval.

Implements concurrent multi-path graph explorations from seed nodes. 

> See GRAPH_RETRIEVAL.md for detailed algorithm documentation.

"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import LiteralString, Any

from neo4j import AsyncDriver, AsyncManagedTransaction

from .models import (
    ExpansionCandidate,
    FrontierInput,
    FrontierNode,
    FrontierUpdateResult,
    GraphEdge,
    GraphNode,
    GraphPath,
    GraphRetrieverConfig,
    GraphStep,
    RetrievalResult,
    SeedFetchResult,
    SeedInput,
)

# ─── Cypher Queries ──────────────────────────────────────────────────────────

_SEED_QUERY: LiteralString = """
MATCH (n {id: $node_id})
RETURN properties(n) AS data, labels(n) AS labels
"""

_EXPAND_QUERY: LiteralString = """
UNWIND $frontier AS f
MATCH (current {id: f.node_id})
WITH current, f.node_id AS parent_id, f.activation AS activation,
     COUNT { (current)-[:RELATES]-() } AS degree

MATCH (current)-[r:RELATES]-(neighbor)
WHERE NOT neighbor.id IN $visited_ids

WITH parent_id, r, neighbor, activation, degree,
     coalesce(r.tags, []) AS eTags
WITH parent_id, r, neighbor, activation, degree, eTags,
     size([t IN eTags WHERE t IN $query_tags]) AS inter_count
WITH parent_id, r, neighbor, activation, degree, eTags, inter_count,
     CASE
         WHEN $query_tags_count = 0 THEN 1.0
         WHEN size(eTags) = 0       THEN $tag_sim_floor
         ELSE $tag_sim_floor
              + (1.0 - $tag_sim_floor)
              * toFloat(inter_count)
              / (size(eTags) + $query_tags_count - inter_count)
     END AS tag_sim

WITH parent_id, r, neighbor,
     (activation * coalesce(r.weight, 0.01) / sqrt(toFloat(degree))) * tag_sim
         AS transfer_energy

WHERE transfer_energy > $min_threshold

RETURN parent_id,
       properties(neighbor)  AS neighbor_data,
       labels(neighbor)       AS neighbor_labels,
       neighbor.id            AS neighbor_id,
       properties(r)          AS edge_data,
       transfer_energy
ORDER BY parent_id, transfer_energy DESC
"""


# ─── Connector ───────────────────────────────────────────────────────────────

class Neo4jConnector:
    """Execute Cypher queries and parse results into dataclasses."""

    __slots__ = ("_tag_sim_floor", "_min_activation")

    def __init__(self, tag_sim_floor: float, min_activation: float) -> None:
        self._tag_sim_floor = tag_sim_floor
        self._min_activation = min_activation

    async def fetch_seed(
        self,
        tx: AsyncManagedTransaction,
        node_id: str,
    ) -> SeedFetchResult:
        seed_cursor = await tx.run(_SEED_QUERY, node_id=node_id)
        seed_record = await seed_cursor.single()

        if seed_record is None:
            return SeedFetchResult(node=None, labels=[], found=False)

        seed_data: dict[str, Any] = dict(seed_record["data"])
        seed_labels: list[str] = list(seed_record["labels"])
        seed_node = GraphNode(
            id=str(seed_data.get("id", node_id)),
            labels=seed_labels,
            properties=seed_data,
        )
        return SeedFetchResult(node=seed_node, labels=seed_labels, found=True)

    async def expand_frontier(
        self,
        tx: AsyncManagedTransaction,
        frontier: list[FrontierInput],
        visited_ids: set[str],
        query_tags: list[str],
    ) -> list[ExpansionCandidate]:
        frontier_param = [
            {"node_id": f.node_id, "activation": f.activation} for f in frontier
        ]
        expand_cursor = await tx.run(
            _EXPAND_QUERY,
            frontier=frontier_param,
            visited_ids=list(visited_ids),
            query_tags=query_tags,
            query_tags_count=len(query_tags),
            tag_sim_floor=self._tag_sim_floor,
            min_threshold=self._min_activation,
        )
        records = [record async for record in expand_cursor]

        candidates: list[ExpansionCandidate] = []
        for rec in records:
            parent_id = rec["parent_id"]
            neighbor_id = rec["neighbor_id"]
            neighbor_node = GraphNode(
                id=str(neighbor_id),
                labels=list(rec["neighbor_labels"]),
                properties=dict(rec["neighbor_data"]),
            )

            edge_properties = dict(rec["edge_data"])
            edge_tags = edge_properties.get("tags") or []
            if not isinstance(edge_tags, list):
                edge_tags = list(edge_tags)
            edge_weight = edge_properties.get("weight")
            if edge_weight is not None:
                edge_weight = float(edge_weight)
            edge = GraphEdge(
                source_id=str(parent_id),
                target_id=str(neighbor_id),
                type="RELATES",
                properties=edge_properties,
                weight=edge_weight,
                tags=list(edge_tags),
            )

            candidates.append(
                ExpansionCandidate(
                    parent_id=str(parent_id),
                    neighbor_node=neighbor_node,
                    edge=edge,
                    transfer_energy=float(rec["transfer_energy"]),
                )
            )

        return candidates


# ─── Traversal State ─────────────────────────────────────────────────────────

class GraphTraversalState:
    """Manage BFS traversal state and path construction."""

    __slots__ = ("_max_branches", "_frontier", "_seed_node")

    def __init__(self, max_branches: int, seed_node: GraphNode) -> None:
        self._max_branches = max_branches
        self._seed_node = seed_node
        self._frontier: list[FrontierNode] = []

    def set_frontier(self, frontier: list[FrontierNode]) -> None:
        self._frontier = frontier

    def build_frontier_inputs(self, frontier: list[FrontierNode]) -> list[FrontierInput]:
        return [FrontierInput(node_id=f.node_id, activation=f.activation) for f in frontier]

    def select_next_frontier(
        self,
        candidates_by_parent: dict[str, list[ExpansionCandidate]],
    ) -> FrontierUpdateResult:
        next_frontier: list[FrontierNode] = []
        newly_visited: set[str] = set()
        completed_paths: list[GraphPath] = []

        for f_node in self._frontier:
            candidates = candidates_by_parent.get(f_node.node_id, [])
            branch_count = 0

            for cand in candidates:
                if branch_count >= self._max_branches:
                    break
                neighbor_id = cand.neighbor_node.id
                if neighbor_id in newly_visited:
                    continue
                branch_count += 1
                newly_visited.add(neighbor_id)

                from_node = self._resolve_from_node(f_node)
                step = GraphStep(
                    from_node=from_node,
                    edge=cand.edge,
                    to_node=cand.neighbor_node,
                    transfer_energy=cand.transfer_energy,
                )
                extended_path = f_node.path.with_step(step)
                next_frontier.append(
                    FrontierNode(
                        node_id=neighbor_id,
                        activation=cand.transfer_energy,
                        path=extended_path,
                    )
                )

            if branch_count == 0 and f_node.path.steps:
                completed_paths.append(f_node.path)

        return FrontierUpdateResult(
            next_frontier=next_frontier,
            completed_paths=completed_paths,
            newly_visited=newly_visited,
        )

    def finalize_remaining(self, frontier: list[FrontierNode]) -> list[GraphPath]:
        return [f_node.path for f_node in frontier if f_node.path.steps]

    def _resolve_from_node(self, f_node: FrontierNode) -> GraphNode:
        if f_node.path.steps:
            return f_node.path.steps[-1].to_node
        return self._seed_node


# ─── GraphRetriever ──────────────────────────────────────────────────────────

class GraphRetriever:
    """Concurrent multi-path Activation-Energy graph explorer.

    Receives a shared, long-lived async Neo4j driver and exposes
    method `explore` which launches independent, concurrent graph explorations
    from a list of seed nodes.  Results are yielded as each exploration
    completes (streamed via ``asyncio.as_completed``).

    Args:
        neo4j_driver: An already-created ``AsyncDriver`` (shared app-wide).
        config:        ``GraphRetrieverConfig``.
    """

    __slots__ = (
        "_driver",
        "_config",
        "_connector",
    )

    def __init__(self, neo4j_driver: AsyncDriver, config: GraphRetrieverConfig) -> None:
        self._driver = neo4j_driver
        self._config = config
        self._connector = Neo4jConnector(
            tag_sim_floor=config.tag_sim_floor,
            min_activation=config.min_activation,
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def explore(
        self,
        seeds: list[SeedInput],
        query_tags: list[str],
    ):
        """Run concurrent multi-path graph explorations from all seeds.

        Results are yielded **as each exploration finishes** an early
        finisher is surfaced immediately while others are still running.

        Args:
            seeds:       List of ``SeedInput`` (node_id + score).
            query_tags:  Tags extracted from the user query.

        Yields:
            ``RetrievalResult`` with paths and metadata.
        """
        if not seeds:
            return

        tasks: list[asyncio.Task[RetrievalResult]] = [
            asyncio.create_task(
                self._explore_with_retry(seed, query_tags),
                name=f"graph-explore-{seed.node_id}",
            )
            for seed in seeds
        ]

        try:
            for future in asyncio.as_completed(tasks):
                try:
                    yield await future
                except Exception:
                    print("Graph exploration failed after all retries")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Internal: retry wrapper ───────────────────────────────────────────

    async def _explore_with_retry(
        self,
        seed: SeedInput,
        query_tags: list[str],
    ) -> RetrievalResult:
        """Run a single exploration with automatic retry + exponential backoff."""
        last_exc: BaseException | None = None
        max_retries = self._config.max_retries
        for attempt in range(max_retries + 1):
            try:
                return await self._explore_single(seed, query_tags)
            except Exception as exc:
                last_exc = exc
                print(
                    "Exploration from seed %s — attempt %d/%d failed: %s",
                    seed.node_id,
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.05 * (2 ** attempt))
        raise last_exc  # type: ignore[misc]

    # ── Internal: single multi-path exploration ───────────────────────────

    async def _explore_single(
        self,
        seed: SeedInput,
        query_tags: list[str],
    ) -> RetrievalResult:
        """Execute one full multi-path BFS exploration from *seed*.

        Opens its own ``AsyncSession`` (lightweight, from the driver pool)
        and runs inside ``session.execute_read`` for automatic transient-error
        retries and consistent read snapshot.
        """
        max_depth = self._config.max_depth
        max_branches = self._config.max_branches

        async def _run(tx: AsyncManagedTransaction) -> RetrievalResult:
            seed_result = await self._connector.fetch_seed(tx, seed.node_id)

            if not seed_result.found or seed_result.node is None:
                print("Seed node %s not found in graph", seed.node_id)
                return RetrievalResult(
                    seed=seed,
                    seed_node=None,
                    paths=[],
                    max_depth_reached=0,
                    terminated_reason="seed_not_found",
                )

            traversal = GraphTraversalState(max_branches=max_branches, seed_node=seed_result.node)

            frontier: list[FrontierNode] = [
                FrontierNode(
                    node_id=seed.node_id,
                    activation=seed.score,
                    path=GraphPath.empty(),
                )
            ]
            visited: set[str] = {seed.node_id}
            completed_paths: list[GraphPath] = []

            for _depth in range(max_depth):
                if not frontier:
                    break

                frontier_inputs = traversal.build_frontier_inputs(frontier)
                candidates = await self._connector.expand_frontier(
                    tx,
                    frontier=frontier_inputs,
                    visited_ids=visited,
                    query_tags=query_tags,
                )

                candidates_by_parent: dict[str, list[ExpansionCandidate]] = defaultdict(list)
                for cand in candidates:
                    candidates_by_parent[cand.parent_id].append(cand)

                traversal.set_frontier(frontier)
                update = traversal.select_next_frontier(candidates_by_parent)
                completed_paths.extend(update.completed_paths)
                visited.update(update.newly_visited)
                frontier = update.next_frontier

            completed_paths.extend(traversal.finalize_remaining(frontier))

            max_depth_reached = max(
                (len(p.steps) for p in completed_paths),
                default=0,
            )

            return RetrievalResult(
                seed=seed,
                seed_node=seed_result.node,
                paths=completed_paths,
                max_depth_reached=max_depth_reached,
                terminated_reason="complete",
            )

        # Open a dedicated session for this exploration.
        async with self._driver.session(database=self._config.database) as session:
            return await session.execute_read(_run)
