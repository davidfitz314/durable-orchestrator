from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import WorkflowDefinition, WorkflowRun, StepRun, RunStatus
from app.schemas import RunCreate, RunOut

router = APIRouter()

@router.post("", response_model=RunOut)
def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    definition = db.get(WorkflowDefinition, payload.workflow_definition_id)
    if not definition:
        raise HTTPException(404, "workflow definition not found")

    run = WorkflowRun(
        workflow_definition_id=definition.id,
        status=RunStatus.PENDING,
        input_json=payload.input_json,
        updated_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()  # get run.id without commit

    # MVP: assume definition_json has steps like:
    # {"steps":[{"name":"step1","type":"transform","max_attempts":3}]}
    steps = definition.definition_json.get("steps", [])
    if not isinstance(steps, list) or len(steps) == 0:
        raise HTTPException(400, "definition_json.steps must be a non-empty list")

    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            raise HTTPException(400, f"definition_json.steps[{i}] must be an object")
        if "name" not in s:
            raise HTTPException(400, f"definition_json.steps[{i}].name is required")

        step = StepRun(
            workflow_run_id=run.id,
            step_name=s["name"],
            step_type=s.get("type", "transform"),
            max_attempts=int(s.get("max_attempts", 3)),
            input_json=payload.input_json,
            updated_at=datetime.utcnow(),
        )
        db.add(step)

    db.commit()
    db.refresh(run)

    # Ensure steps are loaded before returning (avoids lazy-load serialization crashes)
    _ = run.steps

    return run

@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    _ = run.steps  # ensure relationship loaded
    return run