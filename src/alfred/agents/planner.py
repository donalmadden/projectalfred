"""
Planner — reads board and corpus context, produces draft handovers and sprint plans.

Phase 4 implementation will:
- Assemble PlannerInput from board state, velocity history, and RAG retrieval
- Invoke the LLM adapter with the planner prompt
- Return a validated PlannerOutput; drafts require human approval before use
"""
from alfred.schemas.agent import PlannerInput, PlannerOutput


def run_planner(input: PlannerInput) -> PlannerOutput:
    """Produce a draft handover and optional sprint plan. Drafts only — never writes to the board."""
    raise NotImplementedError
