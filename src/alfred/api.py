"""
FastAPI app — HTTP interface for Alfred.

Five endpoints mirror the orchestrator's control surface. Handlers raise
NotImplementedError; Phase 4 wires them to the orchestrator and tools.
No auth, middleware, or CORS here — that belongs in Phase 7.
"""
from fastapi import FastAPI

app = FastAPI(title="Alfred")


@app.post("/generate")
def generate():
    """Trigger handover generation from current board state."""
    raise NotImplementedError


@app.post("/evaluate")
def evaluate():
    """Evaluate a checkpoint given executor output and checkpoint definition."""
    raise NotImplementedError


@app.post("/approve")
def approve():
    """HITL approval gate — approve or reject a pending action."""
    raise NotImplementedError


@app.post("/retrospective")
def retrospective():
    """Trigger retrospective analysis for a sprint."""
    raise NotImplementedError


@app.get("/dashboard")
def dashboard():
    """Read-only sprint state, quality scores, velocity."""
    raise NotImplementedError
