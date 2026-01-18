# Agent State DB (PostgreSQL) — Memoria (SQLAlchemy Async)

> This is how we enable **multi-session** conversations with **live progress**.

This database stores **runtime state** for workflows (conversations) so the backend can **pause/resume/cancel** and stream **progress updates** to clients.  
It does **not** store long-term “memories” (those live in Neo4j + Milvus).

## Core Design Choices ( for MVP)

#### 1) 3-table schema (minimal relationships)
We intentionally avoid many tables/relationships to reduce ORM loading complexity and allow rapid iteration.

Tables:
- `workflows` - one conversation corresponds to one row in this table.
- `workflow_runs` - one execution with "/workflow/start" corresponds to one row here.
- `workflow_events` - one row per progress update (append-only log) connected with a workflow_run. Can be deleted after run completion if desired.

#### 2) JSONB for flexibility (with change tracking)
Flexible key-values can be stored in JSONB. All mutable JSONB columns are defined using:

- `MutableDict.as_mutable(JSONB)`

This is required so SQLAlchemy detects in-place changes (e.g. `context["meta"]["next_seq"] += 1`).

#### 3) Events table behaves like a per-workflow queue
WebSocket reads are the hottest path. We treat `workflow_events` as an append-only log with a monotonic `id` cursor.

#### 4) Expected evolution of schema 
As we build more, I expect the schema to evolve. For example, if a JSONB field becomes complex and frequently queried, we may extract it into its own table or columns.


## Tables

### `workflows`
**1 row = 1 conversation thread (`workflow_id`)**

Purpose:
- Holds the durable “conversation so far” context.
- Holds persistent preferences that apply across future runs.
- Holds “important_steps” useful for future workflow runs.
- Stores a pointer to the most recent run.

Key columns:
- `id` (UUID)
- `status` (workflow-level): `active | paused | cancelled | error`
- `context` (JSONB): conversation summary + tail messages + meta
- `preferences` (JSONB): conversation-level configuration that persists across runs
- `important_steps` (JSONB): high-signal step digests (not stored in events)
- `most_recent_run_id` (UUID nullable): pointer to latest run
- `error` (JSONB nullable): workflow-level error (rare; run errors typically live on runs)

Expected use:
- `/workflow/start` loads workflow context and appends new user message.
- Engine may update `important_steps` when something is worth retaining across runs.
- `most_recent_run_id` is set whenever a new run is created.

### `workflow_runs`
**1 row = 1 execution turn (one `/workflow/start` call)**

Purpose:
- Stores run-scoped configuration (e.g. ask_clarifications).
- Stores compact resumability state needed to pause/resume deterministically.
- Stores final output for clients that only care about the final answer.

Key columns:
- `id` (UUID)
- `workflow_id` (UUID FK)
- `status` (run-level): `running | waiting_for_input | completed | failed | cancelled`
- `user_input` (TEXT): triggering human message for this run
- `ask_clarifications` (BOOL): run-scoped
- `state` (JSONB): compact engine checkpoint (phase/subqueries/pending_input/etc.)
- `final_output` (JSONB nullable): run-scoped final answer payload
- `error` (JSONB nullable): run-scoped error payload

Expected use:
- `/workflow/start` creates a new run in `running` state.
- If clarification is needed, set `status=waiting_for_input` and store pending question in `state.pending_input`.
- `/workflow/input/{workflow_id}` finds the latest waiting run (usually via `most_recent_run_id`) and resumes it.
- When run finishes, set `final_output` and `status=completed` (and optionally append assistant message to workflow context).



### `workflow_events`
**1 row = 1 progress update (append-only)**

Purpose:
- Provides fast WebSocket streaming of human-readable progress updates.
- Treated as a queue: client reads “events after cursor”.

Key columns:
- `id` (BIGINT PK, monotonic cursor)
- `workflow_id` (UUID FK)
- `run_id` (UUID nullable FK): associates updates to a specific run
- `kind` (STRING): `progress | status | warning | error | final`
- `text` (TEXT): human-readable update string
- `payload` (JSONB): optional structured info

Expected use:
- Engine inserts events frequently (cheap inserts).
- WebSocket endpoint queries by `(workflow_id, id > cursor)` and returns ordered results.
- Events can be safely pruned after run completion if desired.

