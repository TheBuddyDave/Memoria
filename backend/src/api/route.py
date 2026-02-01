"""
API Routes for Memoria Workflow Engine.

Endpoints:
- POST /workflow/execute  - Start new workflow or continue existing conversation
- WS   /workflow/ws/{id}  - Stream workflow events in real-time
- POST /workflow/ai-answer - Store AI agent's final response

See API_DOCS.md for full documentation.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from fastapi.responses import JSONResponse
from uuid import uuid4
from typing import Optional
from src.api.schemas import (
    ExecuteWorkflowRequest, 
    ExecuteWorkflowResponse,
    AiAnswerRequest, 
    AiAnswerResponse,
    WorkflowStatusEnum
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/execute", status_code=status.HTTP_201_CREATED, response_model=ExecuteWorkflowResponse)
async def execute_workflow(request_data: ExecuteWorkflowRequest) -> JSONResponse:
    """
    Execute a workflow step or start a new conversation.
    
    Decision Logic:
    1. No workflow_id provided → New conversation, create workflow + run
    2. workflow_id provided, current_run.status = waiting_for_input → Clarification answer
    3. workflow_id provided, current_run.status = completed → New turn in existing conversation
    
    Database Interactions:
    - New conversation: INSERT workflows, INSERT workflow_runs
    - Clarification: UPDATE workflow_runs.state (add answer), SET status=running
    - New turn: INSERT workflow_runs (new run for same workflow)
    
    Returns immediately; client should connect to WebSocket for streaming updates.
    """
    # TODO: Implement logic
    
    is_new_conversation = request_data.workflow_id is None
    workflow_id = request_data.workflow_id or str(uuid4())
    message_id = str(uuid4())

    response = ExecuteWorkflowResponse(
        workflow_id=workflow_id,
        message_id=message_id,
        status=WorkflowStatusEnum.running,
        clarification_question=None,  # Set if subquery gen needs clarification
        message="Workflow started" if is_new_conversation else "Continuing workflow"
    )

    return JSONResponse(content=response.model_dump(), status_code=status.HTTP_201_CREATED)


@router.websocket("/ws/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket, 
    workflow_id: str,
    cursor: Optional[int] = Query(None, description="Event cursor to resume from"),
    final_only: bool = Query(False, description="If true, skip streaming and wait for final memories")
):
    """
    WebSocket endpoint for streaming workflow events.
    
    Query Parameters:
    - cursor: Optional event ID to resume from (omit to get all events from start)
    - final_only: If true, only sends the final memories event (skips progress updates)
    
    Server → Client Events (JSON):
    - {"type": "progress", "message": "Processing...", "timestamp": "..."}
    - {"type": "memories", "data": {"memories": [...], "reasoningbank_hits": [...]}}
    - {"type": "error", "message": "...", "data": {"code": "..."}}
    - {"type": "complete", "message": "Workflow finished"}
    
    Client → Server Commands (JSON):
    - {"command": "get_final"} - Skip to final answer
    - {"command": "cancel"} - Cancel workflow
    
    Database Interaction:
    - Polls workflow_events WHERE workflow_id = ? AND id > cursor
    - For final_only: queries WHERE is_final = true
    """
    await websocket.accept()
    
    # TODO: Implement actual event streaming logic
    # This is the stub implementation
    
    try:
        # In real implementation:
        # 1. If final_only, just wait for final event and send it
        # 2. Otherwise, poll workflow_events table for new events
        # 3. Handle client commands (get_final, cancel)
        
        if final_only:
            # Wait for final event and send it
            # SELECT * FROM workflow_events WHERE workflow_id = ? AND is_final = true
            await websocket.send_json({
                "type": "memories",
                "message": "Final memories retrieved",
                "data": {"memories": [], "reasoningbank_hits": []},
            })
            await websocket.send_json({"type": "complete", "message": "Workflow finished"})
        else:
            # Stream all events starting from cursor
            # SELECT * FROM workflow_events WHERE workflow_id = ? AND id > cursor ORDER BY id
            await websocket.send_json({
                "type": "progress", 
                "message": "Workflow streaming placeholder"
            })
            
            # Listen for client commands while streaming
            while True:
                data = await websocket.receive_json()
                command = data.get("command")
                
                if command == "get_final":
                    # Skip to final
                    await websocket.send_json({
                        "type": "memories",
                        "data": {"memories": []},
                    })
                    break
                elif command == "cancel":
                    await websocket.send_json({
                        "type": "status", 
                        "message": "Workflow cancelled"
                    })
                    break
                    
    except WebSocketDisconnect:
        # Client disconnected - cleanup if needed
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
            "data": {"code": "INTERNAL_ERROR"}
        })
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@router.post("/ai-answer", status_code=status.HTTP_200_OK, response_model=AiAnswerResponse)
async def ai_answer(request_data: AiAnswerRequest) -> JSONResponse:
    """
    Store the AI agent's final response for a conversation turn.
    
    This endpoint completes a conversation turn by adding the AI's response component.
    Should be called by the AI agent after it has:
    1. Received our memories via WebSocket
    2. Generated a response to show the human user
    
    Database Interactions:
    1. Find ConversationTurn by message_id
    2. UPDATE conversation_turns SET ai_answer=?, ai_reasoning=?, ai_tool_calls=?
    3. UPDATE workflow_runs SET status='completed'
    
    If ConversationTurn doesn't exist yet (memories still being retrieved),
    the AI response is stored in WorkflowRun.state until the turn is finalized.
    """
    # TODO: Implement actual database logic
    
    return JSONResponse(
        content=AiAnswerResponse(status="ok", message="AI answer recorded").model_dump(), 
        status_code=status.HTTP_200_OK
    )
