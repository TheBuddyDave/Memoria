from pydantic import BaseModel
from typing import Optional, Dict, Any


class ExecuteWorkflowRequest(BaseModel):
    user_input: str
    workflow_id: Optional[str] = None
    ask_clarifications: Optional[bool] = True
    preferences: Optional[Dict[str, Any]] = None


class AiAnswerRequest(BaseModel):
    workflow_id: str
    message_id: str
    response: str
    reasoning: Optional[str] = None
    tool_calls: Optional[str] = None