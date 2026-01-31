from fastapi import APIRouter, WebSocket, status
from fastapi.responses import JSONResponse
from uuid import uuid4
from src.api.schemas import ExecuteWorkflowRequest, AiAnswerRequest

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/execute", status_code=status.HTTP_201_CREATED)
async def execute_workflow(
    request_data: ExecuteWorkflowRequest
) -> JSONResponse:
    """
    Execute a workflow step or start a new conversation when no workflow_id is provided.
    The same endpoint accepts clarification answers as user input.
    """
    workflow_id = request_data.workflow_id or str(uuid4())
    message_id = str(uuid4())

    response = {
        "workflow_id": workflow_id,
        "message_id": message_id,
        "status": "started",
        "workflow_status": "running",
        "clarification_question": None
    }

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
        while True:
            await websocket.send_json({"message": "Workflow update placeholder"})
    except Exception:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@router.post("/ai-answer", status_code=status.HTTP_200_OK)
async def ai_answer(
    request_data: AiAnswerRequest
) -> JSONResponse:
    """
    Record the AI agent's final response and reasoning for a workflow message.
    """
    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)
