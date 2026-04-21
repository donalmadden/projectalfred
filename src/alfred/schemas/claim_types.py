"""Shared grounding taxonomy surfaced to both planner and validator."""
from __future__ import annotations

import enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from alfred.schemas.repo_conventions import infer_repo_growth_facts


class ClaimCategory(str, enum.Enum):
    METADATA = "METADATA"
    REFERENCE_DOC = "REFERENCE_DOC"
    CURRENT_PATH = "CURRENT_PATH"
    CURRENT_TOPOLOGY = "CURRENT_TOPOLOGY"
    CURRENT_TOOLING = "CURRENT_TOOLING"
    PARTIAL_STATE = "PARTIAL_STATE"
    PYPROJECT_STATE = "PYPROJECT_STATE"
    PLACEMENT = "PLACEMENT"
    HARD_RULE = "HARD_RULE"
    TASK_GRANULARITY = "TASK_GRANULARITY"


class TypedClaim(BaseModel):
    category: ClaimCategory
    claim_text: str
    context: str
    section: str
    examples: list[str] = Field(default_factory=list)


_CLAIM_TAXONOMY: tuple[TypedClaim, ...] = (
    TypedClaim(
        category=ClaimCategory.METADATA,
        claim_text="Document id/date/previous_handover must match supplied metadata and file identity.",
        context="Identity and chronology grounding",
        section="## CONTEXT — READ THIS FIRST",
        examples=["`ALFRED_HANDOVER_6`", "`2026-04-20`"],
    ),
    TypedClaim(
        category=ClaimCategory.REFERENCE_DOC,
        claim_text="Reference documents must be real `docs/*.md` files with usable metadata when they are handovers.",
        context="Reference hygiene",
        section="## CONTEXT — READ THIS FIRST or `## WHAT EXISTS TODAY`",
        examples=["`docs/architecture.md`", "`docs/ALFRED_HANDOVER_5.md`"],
    ),
    TypedClaim(
        category=ClaimCategory.CURRENT_PATH,
        claim_text="Backtick-quoted local paths in current-state sections must exist in the workspace today.",
        context="Present-tense file/module claims",
        section="## WHAT EXISTS TODAY",
        examples=["`src/alfred/api.py`", "`scripts/validate_alfred_planning_facts.py`"],
    ),
    TypedClaim(
        category=ClaimCategory.CURRENT_TOPOLOGY,
        claim_text="Current architecture claims must match the real module layout, agent roster, and API surface.",
        context="Repo topology grounding",
        section="## WHAT EXISTS TODAY",
        examples=["FastAPI lives in `src/alfred/api.py`", "real agent roster under `src/alfred/agents/`"],
    ),
    TypedClaim(
        category=ClaimCategory.CURRENT_TOOLING,
        claim_text="Current toolchain claims must reflect the real repo configuration.",
        context="Tooling grounding",
        section="## WHAT EXISTS TODAY",
        examples=["`pyright` is in use", "`mypy` is not in use"],
    ),
    TypedClaim(
        category=ClaimCategory.PARTIAL_STATE,
        claim_text="Declared-but-missing artifacts need explicit partial-state vocabulary rather than flat existence/absence language.",
        context="Repo has planned or declared items that are not implemented yet",
        section="## WHAT EXISTS TODAY",
        examples=["declared but unimplemented", "proposed for Phase 7"],
    ),
    TypedClaim(
        category=ClaimCategory.PYPROJECT_STATE,
        claim_text="`pyproject.toml` claims must distinguish present-but-incomplete from absent.",
        context="Packaging state grounding",
        section="## WHAT EXISTS TODAY",
        examples=["`[project]` exists", "`[project.scripts]` exists"],
    ),
    TypedClaim(
        category=ClaimCategory.PLACEMENT,
        claim_text="Future files must land in canonical repo locations that match existing layout conventions.",
        context="Future-task realism",
        section="## TASK OVERVIEW or future-task sections",
        examples=["workflows in `.github/workflows/`", "schemas in `src/alfred/schemas/`"],
    ),
    TypedClaim(
        category=ClaimCategory.HARD_RULE,
        claim_text="Future tasks must obey non-negotiable repo rules even when the proposal is otherwise plausible.",
        context="Phase constraints and house rules",
        section="## HARD RULES or future-task sections",
        examples=["no `mypy`", "no Docker before the allowed phase"],
    ),
    TypedClaim(
        category=ClaimCategory.TASK_GRANULARITY,
        claim_text="Tasks should name concrete files and verification hooks rather than vague intent-only work items.",
        context="Execution realism",
        section="## TASK OVERVIEW and per-task sections",
        examples=["quote target file paths", "include tests/validation commands"],
    ),
)


def claim_taxonomy() -> list[TypedClaim]:
    """Return the shared claim taxonomy in stable prompt order."""
    return [claim.model_copy(deep=True) for claim in _CLAIM_TAXONOMY]


def format_claim_taxonomy_for_prompt() -> str:
    """Render the taxonomy in a planner-friendly form."""
    lines = []
    for claim in claim_taxonomy():
        examples = ", ".join(claim.examples)
        lines.append(
            f"- `{claim.category.value}`: {claim.claim_text} "
            f"(context: {claim.context}; section: {claim.section}; examples: {examples})"
        )
    return "\n".join(lines)


def format_placement_rules_for_prompt(repo_root: Optional[Path] = None) -> str:
    """Render only the placement subset of repo-growth rules."""
    facts = infer_repo_growth_facts(repo_root)
    lines = []
    for rule in facts.placement_rules:
        examples = ", ".join(f"`{example}`" for example in rule.examples[:2])
        line = (
            f"- `{rule.artifact_type}` files belong under `{rule.canonical_root}` "
            f"using `{rule.pattern}`"
        )
        if examples:
            line += f"; examples: {examples}"
        if rule.exceptions:
            line += f"; exception: {rule.exceptions}"
        lines.append(line)
    return "\n".join(lines)
