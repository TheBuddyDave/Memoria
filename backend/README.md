# Backend - AI Research Analyst

This is the backend server for the AI Research Analyst project. It implements the complete workflow for query processing, memory retrieval, and memory updates.

## Architecture

The backend implements a 5-step workflow:

1. **User Query** - Receives question from frontend
2. **Query Generation** - LLM generates sub-queries for memory retrieval (iterative)
3. **Database Retrieval** - Searches Neo4j (graph) and Milvus (vectors) for relevant memories
4. **Agent Reasoning** - Synthesizes retrieved memories into a response
5. **Memory Updates** - Decides and executes database modifications (add/update/delete)

## Project Structure

```
backend/
├── main.py                 # FastAPI server with REST endpoints
├── workflow.py             # Main workflow orchestration
├── llm_placeholders.py     # Placeholder LLMs (Query Generator & Memory Updater)
├── database.py             # Database retrieval functions (placeholder)
├── sample_data.py          # Sample memory data for demo
├── models.py               # Pydantic models for request/response validation
└── requirements.txt        # Python dependencies
```

## Components

### `main.py`
FastAPI server with the following endpoints:
- `GET /` - Health check
- `POST /api/query` - Main query endpoint (executes full workflow)
- `GET /api/conversations` - List recent conversations
- `GET /api/conversation/{id}` - Get specific conversation details
- `GET /api/stats` - System statistics

### `workflow.py`
Orchestrates the complete workflow:
- Manages iterative query generation and memory retrieval
- Coordinates agent reasoning
- Handles memory updates

### `llm_placeholders.py`
Contains placeholder functions for:
- **Query Generator LLM**: Generates sub-queries based on user question and conversation history
- **Memory Updater LLM**: Decides what memory updates to make based on the interaction

In production, these would call actual LLM APIs (OpenAI, Anthropic, etc.).

### `database.py`
Handles database operations (currently in placeholder mode):
- Memory retrieval (semantic + keyword search)
- Memory addition (nodes, edges, reasoning entries)
- Memory updates and deletions

In production, this would connect to:
- **Neo4j** for graph storage (nodes and edges)
- **Milvus** for vector storage (ReasoningBank)

### `sample_data.py`
Provides sample memory data for demonstration:
- 6 graph memories (nodes and paths)
- 3 reasoning bank entries
- Simple keyword-based search function

### `models.py`
Pydantic models for type safety:
- `Message` - Chat message
- `Memory` - Retrieved memory
- `SubQuery` - Generated sub-query
- `AgentResponse` - Agent's response
- `MemoryUpdate` - Memory update action
- `QueryRequest/Response` - API request/response models

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

### Option 1: Direct Python
```bash
python main.py
```

### Option 2: Using uvicorn
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing the API

### Using curl:
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the performance of the transformer model?",
    "conversation_history": []
  }'
```

### Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "question": "What is the performance of the transformer model?",
        "conversation_history": []
    }
)

print(response.json())
```

## Demo Mode vs Production

### Current Demo Mode
- Uses placeholder LLM functions with hardcoded logic
- Uses simple keyword matching for memory retrieval
- No actual database connections

### Production Requirements
To use in production, you'll need to:

1. **Implement Real LLMs**:
   - Replace placeholder functions in `llm_placeholders.py`
   - Add OpenAI/Anthropic API calls with proper prompting
   - Implement conversation context management

2. **Connect to Databases**:
   - Set up Neo4j instance (see `data/neo4j/README.md`)
   - Set up Milvus/Zilliz Cloud (see `data/milvus/`)
   - Update `database.py` with real connections
   - Implement semantic search with embeddings

3. **Add Authentication**:
   - Implement user authentication
   - Add API key management
   - Secure endpoints

4. **Add Monitoring**:
   - Logging (structured logging)
   - Error tracking (Sentry, etc.)
   - Performance monitoring
   - Database query optimization

## Environment Variables

For production, create a `.env` file:

```env
# LLM Configuration
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Milvus Configuration
MILVUS_URI=your_milvus_uri
MILVUS_TOKEN=your_token

# Server Configuration
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Next Steps

1. Replace placeholder LLMs with real implementations
2. Connect to Neo4j and Milvus databases
3. Add proper error handling and logging
4. Implement authentication and rate limiting
5. Add unit and integration tests
6. Deploy to production (AWS, GCP, Azure, etc.)

## Sample Queries to Try

- "What is the performance of the transformer model?"
- "Tell me about training data quality issues"
- "How should I present results in a research paper?"
- "What methodology should I use for model evaluation?"
- "Show me benchmark performance data"

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Module Not Found
Make sure you're in the backend directory and have activated the virtual environment.

### CORS Errors
Check that the frontend URL is included in the `allow_origins` list in `main.py`.

