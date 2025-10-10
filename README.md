# Memoria

Long-term memory database and reasoning pipeline that grounds LLM outputs with citations while giving users full control over their memories.

## Run with Docker

1. **Start the services**:
   ```bash
   docker compose up --build
   ```

API available at `http://localhost:8000` with automatic docs at `http://localhost:8000/docs`.

If using Docker, an `ollama` service is included and exposed on `http://localhost:11434`. The backend defaults to `LLM_PROVIDER=ollama` and `LLM_MODEL=llama3.2:3b-instruct`.

Frontend dev server:

```bash
cd frontend && npm install && npm run dev
```

## Python environment

Python will be primarily used for evaluations.  Recommended python version is `3.13.7`, but `>=3.9.x` may also work.

Use a virtual environment and install the necessary packages;
```
conda create -n memoria python=3.13
conda activate memoria
pip install requirements.txt
```

## Backend endpoints

- Health
  - GET `/health/`

- Memories
  - GET `/memories/users`
  - POST `/memories/`
  - GET `/memories/?user_id=...`
  - PATCH `/memories/{memory_id}`
  - DELETE `/memories/{memory_id}`
  - GET `/memories/search-by-entity?entity_name=...&user_id=...&limit=...`
  - GET `/memories/graph?user_id=...&limit=...`
  - POST `/memories/links`

- Retrieval
  - POST `/retrieve/`

- Ask (orchestration)
  - POST `/ask/`

- Feedback
  - POST `/feedback/`

- Temporal
  - GET `/temporal/boosted-memories?user_id=...&limit=...`
  - GET `/temporal/decaying-memories?user_id=...&limit=...`
  - GET `/temporal/temporal-scores?user_id=...&limit=...`
  - GET `/temporal/memory-insights?user_id=...`

- Verification
  - POST `/verification/verify-answer`
  - GET `/verification/verification-stats?user_id=...`
  - GET `/verification/test-verification?user_id=...`
  - GET `/verification/verification-health`

## Database schema (pgvector + graph)
See `backend/app/db/schema.sql`. Uses `memories`, `entities`, and `memory_links` with `VECTOR(1536)`.

## Project structure
- `backend/` FastAPI app, services for indexer, retriever, memory manager
- `frontend/` Next.js app with basic UI skeleton
- `docker-compose.yml` brings up Postgres (pgvector) and Redis

## Orchestration and proactive retrieval

When you call `POST /ask`, the system now recalls relevant memories even for long, multi-part questions:

1. Intent extraction: detect entities/temporal hints.
2. Retrieval:
   - Hybrid search over the raw question.
   - Keyword-rewritten query search for long/complex inputs.
   - Entity-based search if entities are detected.
   - Merge and deduplicate results by memory id, apply temporal scoring.
3. Rerank: cross-encoder reranking to pick the most useful memories.
4. Ground+Answer: construct a grounded prompt and generate an answer with citations.
5. Verify (optional): post-generation verification to adjust confidence.

### Example

```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "<YOUR-USER-ID>",
    "question": "I talked to Alex last month about the Q3 launch timeline and some blockers around the API quota. Given the status today, what did I decide about the rollout sequence?"
  }'
```

The system will rewrite to keywords, expand by entities like "Alex", "Q3 launch", and recall the relevant memories to answer with citations.

## Configuration

Environment variables (with typical defaults in Docker):

- `DATABASE_URL` — Postgres with pgvector
- `LLM_PROVIDER` — `ollama` (default), `openai`, etc.
- `LLM_MODEL` — e.g., `llama3.2:3b-instruct`
- `VECTOR_DIM` — embedding dimension (defaults to 1536 in code)

Set these in `docker-compose.yml` or your environment before starting services.
