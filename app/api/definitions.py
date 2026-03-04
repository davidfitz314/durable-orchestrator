from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import WorkflowDefinition
from app.schemas import DefinitionCreate, DefinitionOut

router = APIRouter()

@router.post("", response_model=DefinitionOut)
def create_definition(payload: DefinitionCreate, db: Session = Depends(get_db)):
    d = WorkflowDefinition(
        name=payload.name,
        version=payload.version,
        definition_json=payload.definition_json,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

@router.get("/{definition_id}", response_model=DefinitionOut)
def get_definition(definition_id: int, db: Session = Depends(get_db)):
    return db.get(WorkflowDefinition, definition_id)