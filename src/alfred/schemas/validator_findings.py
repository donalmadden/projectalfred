"""Typed deterministic validator findings shared across planner and validators."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from alfred.schemas.claim_types import ClaimCategory
from alfred.schemas.repo_conventions import PartialStateType


class MetadataFinding(BaseModel):
    finding_type: Literal["metadata"] = "metadata"
    field_name: str
    actual_value: str
    expected_value: str


class PathFinding(BaseModel):
    finding_type: Literal["path"] = "path"
    path: str
    expected_state: str


class TopologyFinding(BaseModel):
    finding_type: Literal["topology"] = "topology"
    claimed_value: str
    canonical_value: str


class ToolingFinding(BaseModel):
    finding_type: Literal["tooling"] = "tooling"
    claimed_tool: str
    allowed_tool: str


class PyprojectFinding(BaseModel):
    finding_type: Literal["pyproject"] = "pyproject"
    claimed_state: str
    actual_state: str


class PlacementFinding(BaseModel):
    finding_type: Literal["placement"] = "placement"
    artifact_type: str
    proposed_location: str
    canonical_location: str
    rule: str


class HardRuleFinding(BaseModel):
    finding_type: Literal["hard_rule"] = "hard_rule"
    rule_name: str
    violation: str
    constraint: str
    phase_allowed: str | None = None


class PartialStateFinding(BaseModel):
    finding_type: Literal["partial_state"] = "partial_state"
    state_type: PartialStateType
    subject: str
    incorrect_phrasing: str
    correct_vocabulary: str
    declared_location: str
    implementation_location: str


class ReferenceDocFinding(BaseModel):
    finding_type: Literal["reference_doc"] = "reference_doc"
    doc_path: str
    issue_type: str
    expected_state: str
    actual_state: str | None = None


class StructuralFinding(BaseModel):
    finding_type: Literal["structural"] = "structural"
    artifact_type: str
    proposed_shape: str
    required_shape: str
    rule: str


class TaskGranularityFinding(BaseModel):
    finding_type: Literal["task_granularity"] = "task_granularity"
    task_heading: str
    missing_requirement: str


FindingPayload = Annotated[
    MetadataFinding
    | PathFinding
    | TopologyFinding
    | ToolingFinding
    | PyprojectFinding
    | PlacementFinding
    | HardRuleFinding
    | PartialStateFinding
    | ReferenceDocFinding
    | StructuralFinding
    | TaskGranularityFinding,
    Field(discriminator="finding_type"),
]


class FormattedFinding(BaseModel):
    category: ClaimCategory
    severity: Literal["error", "warning"]
    human_message: str
    evidence: str
    section: str
    finding_object: FindingPayload

    @property
    def message(self) -> str:
        return self.human_message

    def format(self) -> str:
        return (
            f"[{self.severity.upper()}][{self.category.value}] "
            f"{self.evidence} — {self.human_message}"
        )
