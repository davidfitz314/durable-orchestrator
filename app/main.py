from fastapi import FastAPI
from app.api.definitions import router as definitions_router
from app.api.runs import router as runs_router

app = FastAPI(title="Durable Orchestrator")

app.include_router(definitions_router, prefix="/definitions", tags=["definitions"])
app.include_router(runs_router, prefix="/runs", tags=["runs"])