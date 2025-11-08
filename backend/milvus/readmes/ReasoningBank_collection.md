## 📘 ReasoningBank Collection in Milvus

The **ReasoningBank** collection in Zilliz Cloud (Milvus). Optimized for **hybrid retrieval** - semantic similarity and BM25 (full-text search in milvus)

---

### Collection Details

**Collection Name:** `reasoningbank`

**Description:** `agent reasoning lessons and wisdom`

#### Schema Overview

| Field                      | Type                     | Limits             | Description                                                                       |
| -------------------------- | ------------------------ | ------------------ | --------------------------------------------------------------------------------- |
| `rb_id`                    | `INT64`                  | Auto ID, PK        | Auto-generated ID for each entry.                                                 |
| `key_lesson_vector`        | `FLOAT_VECTOR(3072)`     | —                  | Dense embedding of `key_lesson` using `text-embedding-3-large`.                   |
| `key_lesson`               | `VARCHAR(65535)`         | Max 65,535 chars   | Raw lesson text for readability or re-embedding.                                  |
| `context_to_prefer_vector` | `FLOAT_VECTOR(3072)`     | —                  | Dense embedding of contextual guidance.                                           |
| `context_to_prefer`        | `VARCHAR(65535)`         | Max 65,535 chars   | Natural language context describing applicability.                                |
| `context_sparse_vector`    | `SPARSE_FLOAT_VECTOR`    | —                  | BM25 sparse vector generated from `context_to_prefer`. Enables lexical retrieval. |
| `tags`                     | `ARRAY / VARCHAR(65535)` | Max 4,096 elements | Topic tags for filtering and classification.                                      |
| `link_nodes`               | `ARRAY / VARCHAR(65535)` | Max 4,096 elements | Graph node provenance. Nullable.                                                  |

---

### Index Configuration
Following indexes were created for performance enhancement (though at the scale we are working in currently this won't matter much)

| Field                      | Metric | Index Build Level | Purpose                                                                   |
| -------------------------- | ------ | ----------------- | ------------------------------------------------------------------------- |
| `key_lesson_vector`        | Cosine | Precision-first   | Prioritizes semantic accuracy over speed; ideal for small-scale datasets. |
| `context_to_prefer_vector` | Cosine | Precision-first   | Same configuration for context vectors.                                   |
| `context_sparse_vector`    | BM25   | —                 | Sparse inverted index for keyword-based full-text retrieval.              |
| `tags`, `link_nodes`       | —      | Scalar Index      | Optimized for quick filtering by topic or provenance.                     |

> Precision-first indexing: was chosen because the collection is small (a few thousand records in the future), so prioritizing retrieval accuracy.

---

### Full-Text Search Function

Configured in **Advanced Settings**:

Documentation: https://docs.zilliz.com/docs/full-text-search

* **Input Field:** `context_to_prefer`
* **Analyzer:** Standard Analyzer (English tokenization + stop-word removal)
* **Function Type:** BM25
* **Output Field:** `context_sparse_vector`

This automatically generates sparse BM25 representations, allowing hybrid search across dense and sparse representations.

---

### Advanced Settings

* **Dynamic Fields:** Enabled for future metadata extensions.
* **Embedding Model:** OpenAI `text-embedding-3-large` (3072 dimensions). Need to use the same for query embeddings. No need to have a separate BM25 model since Milvus handles sparse vectors internally.


