"""
FastAPI server for the AI Research Analyst backend.
Provides REST API endpoints for the frontend to interact with the agent.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid
from datetime import datetime

from models import QueryRequest, QueryResponse, Message
from workflow import AIResearchAnalystWorkflow

# Initialize FastAPI app
app = FastAPI(
    title="AI Research Analyst API",
    description="Backend API for AI research analyst with long-term memory",
    version="0.1.0"
)

# Configure CORS to allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow
workflow = AIResearchAnalystWorkflow()

# Store conversations in memory (in production, this would be in a database)
conversations = {}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Research Analyst API",
        "version": "0.1.0"
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Main endpoint to query the AI research analyst agent.
    
    Workflow:
    1. Receives user question and conversation history
    2. Runs through Query Generator → Database Retrieval loop
    3. Agent reasons and generates response
    4. Memory Updater decides on database modifications
    5. Returns response with all intermediate steps
    """
    try:
        print(f"\n{'='*80}")
        print(f"Received query: '{request.question}'")
        print(f"{'='*80}")
        
        # Process the query through the workflow
        agent_response, sub_queries, memory_updates = workflow.process_user_query(
            request.question,
            request.conversation_history
        )
        
        # Generate a conversation ID if this is a new conversation
        conv_id = str(uuid.uuid4())[:8]
        
        # Store conversation (in production, save to database)
        conversations[conv_id] = {
            "question": request.question,
            "response": agent_response.response,
            "timestamp": datetime.now()
        }
        
        # Build the response
        response = QueryResponse(
            response=agent_response.response,
            reasoning=agent_response.reasoning,
            memories_used=agent_response.memories_used,
            sub_queries_generated=sub_queries,
            memory_updates=memory_updates,
            conversation_id=conv_id
        )
        
        return response
        
    except Exception as e:
        print(f"ERROR: Failed to process query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def get_conversations():
    """
    Get list of recent conversations.
    In production, this would query the database.
    """
    return {
        "conversations": [
            {
                "id": conv_id,
                "question": data["question"][:100],
                "timestamp": data["timestamp"].isoformat()
            }
            for conv_id, data in conversations.items()
        ]
    }


@app.get("/api/conversation/{conv_id}")
async def get_conversation(conv_id: str):
    """
    Get details of a specific conversation.
    """
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversations[conv_id]


@app.get("/api/stats")
async def get_stats():
    """
    Get system statistics.
    In production, this would query the databases for real stats.
    """
    return {
        "total_conversations": len(conversations),
        "total_graph_nodes": 6,  # From sample data
        "total_reasoning_entries": 3,  # From sample data
        "database_status": {
            "neo4j": "placeholder mode",
            "milvus": "placeholder mode"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print("AI Research Analyst Backend Server")
    print("="*80)
    print("Server running at: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    print("="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

