from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Text, Index
)
from sqlalchemy.orm import relationship
from .db import Base

def utcnow():
    return datetime.utcnow()

class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    WAITING_RETRY = "WAITING_RETRY"
    CANCELED = "CANCELED"

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    definition_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(Integer, primary_key=True)
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.PENDING)
    input_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, nullable=False)

    definition = relationship("WorkflowDefinition")
    steps = relationship("StepRun", back_populates="run")

class StepRun(Base):
    __tablename__ = "step_runs"
    id = Column(Integer, primary_key=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=False)
    step_name = Column(String, nullable=False)
    step_type = Column(String, nullable=False)  # "transform" / "http_request" later
    status = Column(Enum(StepStatus), nullable=False, default=StepStatus.PENDING)

    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    next_run_at = Column(DateTime, nullable=False, default=utcnow)

    idempotency_key = Column(String, nullable=True)

    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String, nullable=True)

    input_json = Column(JSON, nullable=False, default=dict)
    output_json = Column(JSON, nullable=True)
    error_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, nullable=False)

    run = relationship("WorkflowRun", back_populates="steps")

Index("idx_step_runnable", StepRun.status, StepRun.next_run_at)