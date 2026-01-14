from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from uuid import uuid4
from typing import Any, Dict, Optional

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_workflow(
    # TODO: Add proper Pydantic request model here
    request_data: Dict[str, Any]
) -> JSONResponse:
    """
    Start a new workflow instance.
    """
    # Generate unique workflow ID
    workflow_id = str(uuid4())
    
    # TODO: Extract parameters from request_data
    # user_input = request_data.get("user_input")
    # ask_clarifications = request_data.get("ask_clarifications", False)
    
    # TODO: Start the workflow function (to be defined elsewhere)
    # This function will receive an emit function that writes to PostgreSQL
    # await start_workflow_process(workflow_id, user_input, emit_function, ...)
    
    response = {
        "workflow_id": workflow_id,
        "status": "started",
        "clarification_question": None  # Will be populated if ask_clarifications=True
    }
    
    # TODO: Check if clarifications are needed and populate clarification_question
    
    return JSONResponse(content=response, status_code=status.HTTP_201_CREATED)


@router.websocket("/ws/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for streaming workflow updates and receiving client input.
    
    Connection behavior:
    - If client disconnects, workflow is stopped
    - If final answer is requested and available, skip remaining events
    """
    await websocket.accept()
    
    try:
        # TODO: Set up database connection to read events for this workflow_id
        
        # TODO: Start streaming events from PostgreSQL
        # This should be a loop that:
        # 1. Reads events from DB for this workflow_id
        # 2. Sends them to the client via websocket.send_json()
        # 3. Listens for client messages via websocket.receive_json()
        
        while True:
            # for now just emit a dummy message
            await websocket.send_json({"message": "Workflow update placeholder"})
                
    except Exception as e:
        # TODO: Add proper error handling and logging
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        # TODO: Cleanup resources (close DB connection, etc.)
        pass


@router.post("/input/{workflow_id}")
async def submit_clarification(
    workflow_id: str,
    # TODO: Add proper Pydantic request model here
    request_data: Dict[str, Any]
) -> JSONResponse:
    """
    Submit clarification answer for a workflow.
    
    Used when ask_clarifications=True in start_workflow and the workflow has asked a clarification question.
    """
    # TODO: Validate workflow_id exists
    # workflow_exists = await check_workflow_exists(workflow_id)
    # if not workflow_exists:
    #     return JSONResponse(
    #         content={"error": "Workflow not found"},
    #         status_code=status.HTTP_404_NOT_FOUND
    #     )
    
    # TODO: Extract clarification answer from request_data
    # clarification_answer = request_data.get("clarification_answer")
    
    # TODO: Send clarification to workflow process
    # This may trigger another clarification question or allow workflow to proceed
    # result = await process_clarification(workflow_id, clarification_answer)
    
    response = {
        "workflow_id": workflow_id,
        "status": "ok",  # or "needs_clarification"
        "clarification_question": None,  # Populate if another clarification is needed
        "workflow_status": "running"
    }
    
    return JSONResponse(content=response)
