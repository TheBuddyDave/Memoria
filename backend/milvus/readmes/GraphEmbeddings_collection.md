#  GraphEmbeddings Collection

The **GraphEmbeddings** collection stores vector embeddings for all memory nodes in graph. It’s designed purely as an embedding lookup and retrieval layer - all node metadata continues to live in the graph itself. 

Each entry points back to its originating node via `pointer_to_node`.

---

### Collection Details

**Collection Name:** `graphembeddings`

**Description:** `embedding storage of all graph nodes. embeddings, text, and pointers.`

#### Schema

| Field             | Type                  | Limits           | Description                                                                                               |
| ----------------- | --------------------- | ---------------- | --------------------------------------------------------------------------------------------------------- |
| `id`              | `INT64`               | Auto ID, PK      | Automatically assigned ID for each stored embedding.                                                      |
| `dense_vector`    | `FLOAT_VECTOR(3072)`  | —                | 3072-dimensional dense embedding (OpenAI `text-embedding-3-large`) for semantic similarity.               |
| `sparse_vector`   | `SPARSE_FLOAT_VECTOR` | —                | BM25-based sparse embedding automatically generated from the text field.    |
| `text`            | `VARCHAR(65535)`      | Max 65,535 chars | Raw text representation of the graph node. Basis for both embedding generation and BM25 search.           |
| `pointer_to_node` | `VARCHAR(65535)`      | Max 65,535 chars | ID reference linking this embedding entry back to its corresponding graph node. |

---

### Index Configuration

| Field             | Metric | Index Build Level | Purpose                                                                      |
| ----------------- | ------ | ----------------- | ---------------------------------------------------------------------------- |
| `dense_vector`    | Cosine | Balanced          | Balances speed and precision for general semantic search across graph nodes. |
| `sparse_vector`   | BM25   | —                 | Enables keyword-based retrieval using sparse vector scoring.         |
| `pointer_to_node` | —      | Scalar Index      | Supports direct filtering and linking to graph nodes.                        |

---

### Full-Text Search Function

Configured under **Advanced Settings** using the same setup as ReasoningBank:

* **Function:** `sparse_vector_function`
* **Input Field:** `text`
* **Analyzer:** Standard Analyzer (tokenization + stop-word removal)
* **Function Type:** BM25
* **Output Field:** `sparse_vector`

This setup allows hybrid search — combining BM25 for keyword-level matching with cosine-based dense retrieval for semantic relevance.

---

### Additional Notes

* **Embedding Model:** `text-embedding-3-large (3072-dim)` 
* **Dynamic Fields:** Enabled for future additions.
* **Shards/Partitions:** Defaults used.


