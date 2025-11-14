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
| `dense_vector`    | `FLOAT_VECTOR(1536)`  | —                | small-dimensional dense embedding (OpenAI `text-embedding-3-small`) for semantic similarity.               |
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

Configure the Single Analyzer with following jsonLine:

```json
{
    "tokenizer": "standard",
    "filter": [
        "lowercase",
        {
          "type": "stop",
          "stop_words": ["_english_"]
        }
    ]
}
```

**Format to configure single-analyzer with stop-word removal:**
```json
{
    "tokenizer": "standard",
    "filter": [
        "lowercase",
        {
            "type": "stop",
            "stop_words": ["_english_"]
        }
    ]
}
```

---

### Additional Notes

* **Embedding Model:** `text-embedding-3-small (1536-dim)` 
* **Dynamic Fields:** Enabled for future additions.
* **Shards/Partitions:** Defaults used.


**JSON configuration to insert to GraphEmbeddings Collection:**
```json
{
  "collectionName": "GraphEmbeddings",
  "data": [
    {
      "text": "i8ko1g942z",
      "pointer_to_node": "3vkfdgs9ekq",
      "dense_vector": [
        *3072 dim embedding vector*
      ]
    }
  ]
}
```


