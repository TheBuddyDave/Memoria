"""
Pydantic schemas for API request/response validation.

These schemas define the contract between the client (AI agent) and our backend.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class WorkflowStatusEnum(str, Enum):
    """Workflow status returned to client."""
    running = "running"
    waiting_for_input = "waiting_for_input"
    completed = "completed"
    failed = "failed"


# =============================================================================
# Execute Workflow Endpoint
# =============================================================================

class ExecuteWorkflowRequest(BaseModel):
    """
    Request to start a new workflow or continue an existing one.
    
    Scenarios:
    1. New conversation: omit workflow_id
    2. New turn in existing conversation: include workflow_id
    3. Clarification answer: include workflow_id (backend detects paused state)
    """
    user_input: str = Field(..., description="The user's message or clarification answer")
    workflow_id: Optional[str] = Field(
        None, 
        description="Omit for new conversation, include for existing conversation"
    )
    ask_clarifications: bool = Field(
        True, 
        description="Whether the subquery generator should ask clarifying questions"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional client preferences (verbosity, domains, etc.)"
    )


class ExecuteWorkflowResponse(BaseModel):
    """
    Response from the execute endpoint.
    
    The client uses workflow_id and message_id for subsequent requests.
    If clarification_question is present, the workflow is paused and waiting for an answer.
    """
    workflow_id: str = Field(..., description="UUID to use for all subsequent requests")
    message_id: str = Field(..., description="UUID identifying this specific message/turn")
    status: WorkflowStatusEnum = Field(..., description="Current processing status")
    clarification_question: Optional[str] = Field(
        None, 
        description="If present, workflow is paused waiting for this clarification"
    )
    message: Optional[str] = Field(None, description="Human-readable status message")


# =============================================================================
# AI Answer Endpoint
# =============================================================================

class AiAnswerRequest(BaseModel):
    """
    Request to store the AI agent's final response.
    
    This completes a conversation turn by adding the AI's response component.
    Should be called after the AI agent has processed our memories and generated a response.
    """
    workflow_id: str = Field(..., description="The workflow this answer belongs to")
    message_id: str = Field(..., description="The message_id from the execute response")
    response: str = Field(..., description="The AI agent's final response to the user")
    reasoning: Optional[str] = Field(None, description="AI reasoning tokens/trace")
    tool_calls: Optional[str] = Field(None, description="History of tool calls made by AI")


class AiAnswerResponse(BaseModel):
    """Response confirming the AI answer was stored."""
    status: str = Field(default="ok")
    message: Optional[str] = None


# =============================================================================
# WebSocket Event Schemas
# =============================================================================

class WSEventType(str, Enum):
    """Types of events streamed over WebSocket."""
    progress = "progress"      # Workflow progress update
    status = "status"          # Status change notification
    memories = "memories"      # Final memories payload
    error = "error"            # Error occurred
    complete = "complete"      # Workflow finished


class WSEvent(BaseModel):
    """
    Event streamed to client over WebSocket.
    
    The payload structure varies by type:
    - progress: {"message": "Processing subqueries..."}
    - memories: {"memories": [...], "reasoningbank_hits": [...]}
    - error: {"error": "...", "code": "..."}
    - complete: {"message": "Done"}
    """
    type: WSEventType
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class WSClientMessage(BaseModel):
    """
    Message from client to server over WebSocket.
    
    Commands:
    - get_final: Skip streaming, just send final memories when ready
    - cancel: Cancel the workflow
    """
    command: str = Field(..., description="Command: 'get_final' or 'cancel'")
    cursor: Optional[int] = Field(
        None, 
        description="Optional event cursor for resuming stream (omit to get all events)"
    )