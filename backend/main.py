import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# route imports
from src.api.route import router as workflow_router

# Initialize FastAPI application
app = FastAPI(
    title="Memoria API",
    description="Long-term memory for AI Agents",
    version="0.1.0"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(workflow_router)

if __name__ == "__main__":
    # Start uvicorn server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True  # Disable in production
    )
