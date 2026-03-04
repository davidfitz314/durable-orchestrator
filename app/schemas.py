from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

class DefinitionCreate(BaseModel):
    name: str
    version: int = 1
    definition_json: Dict[str, Any]

class DefinitionOut(BaseModel):
    id: int
    name: str
    version: int
    definition_json: Dict[str, Any]

    class Config:
        from_attributes = True

class RunCreate(BaseModel):
    workflow_definition_id: int
    input_json: Dict[str, Any] = {}

class StepOut(BaseModel):
    id: int
    step_name: str
    step_type: str
    status: str
    attempt_count: int
    max_attempts: int
    next_run_at: datetime
    output_json: Optional[Dict[str, Any]] = None
    error_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class RunOut(BaseModel):
    id: int
    workflow_definition_id: int
    status: str
    input_json: Dict[str, Any]
    steps: List[StepOut]

    class Config:
        from_attributes = True