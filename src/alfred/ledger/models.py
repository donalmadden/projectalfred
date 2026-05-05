"""Phase Ledger Pydantic models.

The ledger is a derived, additive scaffold — a mechanical view of canonical
handovers. Authority flows handover → ledger, never the reverse.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TaskSeed(BaseModel):
    id: str
    title: str
    intent: str


class Brief(BaseModel):
    """Human-authored editorial seed for a planning phase."""

    title: str
    goal: str
    hard_rules: list[str] = Field(default_factory=list)
    tasks: list[TaskSeed] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    followups_from_prior_phase: list[str] = Field(default_factory=list)


PhaseStatus = Literal["ratified", "planning"]


class Phase(BaseModel):
    id: int
    title: str
    status: PhaseStatus
    handover_id: str | None = None
    scope_sources: list[str] = Field(default_factory=list)
    scope_carry_forward: list[int] = Field(default_factory=list)
    brief: Brief | None = None

    @model_validator(mode="after")
    def _check_ratified_constraints(self) -> "Phase":
        if self.status == "ratified" and self.handover_id is None:
            raise ValueError(
                f"Phase {self.id}: ratified phases must have a handover_id"
            )
        if self.status == "ratified" and self.brief is not None:
            raise ValueError(
                f"Phase {self.id}: ratified phases must not have a brief"
                " (brief is for unratified/planning phases only)"
            )
        return self


class PhaseLedger(BaseModel):
    project: str
    plan_path: str | None = None
    phases: list[Phase]

    @model_validator(mode="after")
    def _check_unique_phase_ids(self) -> "PhaseLedger":
        seen: set[int] = set()
        for phase in self.phases:
            if phase.id in seen:
                raise ValueError(f"Duplicate phase id: {phase.id}")
            seen.add(phase.id)
        return self
