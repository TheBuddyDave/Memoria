from pydantic import BaseModel
from typing import Optional, Dict, Any


class StartWorkflowRequest(BaseModel):
    user_input: str
    workflow_id: Optional[str] = None
    ask_clarifications: Optional[bool] = True
    preferences: Optional[Dict[str, Any]] = None


class SubmitClarificationRequest(BaseModel):
    workflow_id: str
    clarification_answer: str