## Nodes: The Core Memories

Each node is a "snapshot" of a piece of information.

### Node Types (Labels)

**⭐ WHY 6 labels?**: By dividing into labels instead of having 2-3 very broad meaningless categories, we ensure that each node is categorized correctly and can be easily retrieved based on its type. For example, if we are concerned with a temporal questions we know it must involve a `Event` node while if we are concerned with a past action related to a specific document we know it must involve a `DataSource` node and an `AgentAction` node.

We use 6 specific node labels. A node can only have **one** of these labels.

  * **`UserRequest`**
      * **Represents:** The literal prompt or question a user asked.
      * **Thought Process:** We save the *user intent* itself. This helps the agent understand patterns in *what* users ask for, not just the answers it gave.
  * **`UserPreference`**
      * **Represents:** An extracted rule about a user's style, (e.g., "VP Digital prefers tables, not pie charts").
      * **Thought Process:** This is the key to personalization. By storing preferences explicitly, the agent can tailor its final output (reports, visuals) to the stakeholder.
  * **`AgentAnswer`**
      * **Represents:** A final conclusion, recommendation, or summary delivered by the agent.
      * **Thought Process:** This is one of the most important node types. These are the reusable "conclusions" from prior work. A new query can find a past `AgentAnswer` and use it as a starting point, saving re-work.
  * **`AgentAction`**
      * **Represents:** A "how-to" guide. It's a specific, methodological step the agent took (e.g., "Merged dataset A and B on `join_key`").
      * **Thought Process:** This captures the *process* (the "how"), not just the result. It's a "methodology anchor" that lets the agent learn *how* to perform complex tasks like data joins, model validation, or filtering.
  * **`Event`**
      * **Represents:** A temporal data point. It's anything from a data quality incident ("Bot traffic spike") to a business-rhythm meeting ("Q4 QBR").
      * **Thought Process:** Events give the graph context in time. They allow the agent to reason about "why did metrics change in July?" by linking to an `Event` that also happened in July.
  * **`DataSource`**
      * **Represents:** The "evidence." This is a specific document, file, or dashboard (e.g., "Q3\_Sales\_Data.csv" or "Predictive PBI Dashboard").
      * **Thought Process:** This provides grounding by allowing the agent (and the user) to trace an answer back to its source material.

### Common Node Schema (All Nodes)

Every single node in our graph has these fields.

| Field | Example | Purpose & Thought Process |
| :--- | :--- | :--- |
| `id` | `"N1001"` | **(Primary Key)** The unique ID for the node. |
| `conv_id` | `"2025-09-12_Kia_Q4Budget_01"` | Groups nodes from the same conversation. This helps us see the "snapshot" of a single interaction anytime. Can help with many features including audit and safety. |
| `text` | `"Concluded CPA rise linked to supply volatility..."` | The main, human-readable content of the node. This is what the LLM reads to understand the node and put together meaning of paths. |
| `ingestion_time` | `datetime("2025-09-12T...")` | When this memory was created. |
| `update_time` | `datetime("2025-09-12T...")` |  When this memory was last modified. |
| `embedding_id` | `"emb_N1001"` | A pointer to the vector embedding of the `text` field in our vector DB. This is how we find nodes via semantic search. |
| `tags` | `["answer", "roi", "rundown", "ev"]` | These are query-relevant keywords. We use them for fast, precise filtering *before* or *after* doing similarity search. |
| `reasoning_pointer_ids` | `["RB-01", "RB-07"]` | A list of `rb_id`s (mostly empty). This connects the "fact" (this node) to the "wisdom" (the lessons in the ReasoningBank). |

### Special Node Schema (Per-Type)

These fields are added *in addition* to the common schema, depending on the node's type.

| Node Type | Special Fields | Purpose & Thought Process |
| :--- | :--- | :--- |
| **`UserRequest`** | `user_role`, `user_id` | Tracks *who* is asking. This allows reasoning based on role (e.g., "The CFO's office asks about this often"). |
| **`UserPreference`** | `preference_type` | Categorizes the preference (e.g., `"report_style"`, `"granularity"`). |
| **`AgentAnswer`** | `analysis_types`, `metrics` | We know *what kind* of analysis it was (`["attribution_modeling"]`) and *what KPIs* it involved (`["roi", "cpa"]`). |
| **`AgentAction`** | `status`, `parameter_field` | Tracks execution. `status: "complete"` shows it worked. `parameter_field` stores the *exact* which maybe SQL code or API request parameters or other relevant details. |
| **`Event`** | `source_type`, `start_date`, `end_date` |  `source_type` ("System Incident", "Calendar") explains *what* generated the event, and dates provide the time window. |
| **`DataSource`** | `source_type`, `doc_pointer`, `relevant_parts` | Provides precise grounding. `source_type` ("pbi", "csv"), `doc_pointer` (the file path), and `relevant_parts` ("Slide 4") tell the agent *exactly* where to look. |

---

## Edges: The Contextual Glue

Edges provide the **contextual relationship** that links two memories together. Nodes connected by edges form paths which are true "memories" the agent can traverse to reason about complex scenarios.

### Edge Schema

All edges follow this:

| Field | Example | Purpose & Thought Process |
| :--- | :--- | :--- |
| `id` | `"E3001"` | **(Primary Key)** The unique ID for the edge. |
| `text` | `"Provides the predictive, scenario-tested *solution* for..."` | **(Core Content / The "Why")** We do *not* use generic labels like `[:RELATED_TO]`. We use a specific, human-readable sentence that explains *why* and *how* these two nodes are connected. This is fully interpretable by an LLM. |
| `weight` | `0.85` | **(Contextual Strength)** How strong is this connection at time of creation? This is key for reasoning. <br> • **0.85–1.0:** Direct, causal, or core logic (e.g., a Request *triggers* an Action). <br> • **0.55–0.75:** Strong bridge (e.g., a *solution* links to a *problem*). <br> • **0.25–0.45:** Weak topical bridge (e.g., two nodes that mention "EV9" but aren't directly related). |
| `tags` | `["bridge", "solution", "rundown", "roi"]` |  Query-relevant keywords for the *relationship itself*. This lets us find *types* of connections (e.g., "find all `solution` bridges"). |
| `created_time` | `datetime("2025-09-12T...")` | When this relationship was created. |

> **Key Points on Edges:**
>
> 1.  **Natural Language is the Type:** Our "edge type" is the `text` field. This is a deliberate design choice. It's far more expressive for an LLM to read a full sentences instead of cryptic labels like `[:RELATES_TO]`. For visualization, we still give labels. But for reasoning, the `text` is what matters.
> 2.  **Context is Everything:** An edge turns two isolated facts into a story. `(Node A) -[explains]-> (Node B)`. Without the edge's `text`, the agent wouldn't know *why* A and B are linked.
> 3.  **Weights Guide Reasoning:** The `weight` allows us to prioritize certain paths during traversal. Stronger edges indicate more relevant or causal relationships. 


