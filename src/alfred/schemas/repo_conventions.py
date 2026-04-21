"""Typed repository-growth conventions and partial-state facts."""
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[3]


class PlacementRule(BaseModel):
    artifact_type: str
    canonical_root: str
    pattern: str
    examples: list[str] = Field(default_factory=list)
    exceptions: Optional[str] = None


class NamingConvention(BaseModel):
    artifact_type: str
    pattern: str
    examples: list[str] = Field(default_factory=list)


class StructuralRule(BaseModel):
    artifact_type: str
    required_shape: str
    forbidden_shape: str
    examples: list[str] = Field(default_factory=list)


class RepoGrowthFacts(BaseModel):
    placement_rules: list[PlacementRule] = Field(default_factory=list)
    naming_conventions: list[NamingConvention] = Field(default_factory=list)
    structural_rules: list[StructuralRule] = Field(default_factory=list)


class PartialStateType(str, Enum):
    CLI = "CLI"
    WORKFLOW = "WORKFLOW"
    SCHEMA = "SCHEMA"
    DOC = "DOC"
    ENTRY_POINT = "ENTRY_POINT"


class PartialStateFact(BaseModel):
    state_key: str
    state_type: PartialStateType
    label: str
    is_declared: bool
    is_implemented: bool
    declared_location: str
    implementation_location: str
    description: str
    expected_vocabulary: str
    aliases: list[str] = Field(default_factory=list)


def _relative_examples(
    repo_root: Path,
    pattern: str,
    *,
    exclude_stems: set[str] | None = None,
    limit: int = 3,
) -> list[str]:
    exclude_stems = exclude_stems or set()
    examples: list[str] = []
    for path in sorted(repo_root.glob(pattern)):
        if not path.is_file():
            continue
        if path.stem in exclude_stems:
            continue
        examples.append(path.relative_to(repo_root).as_posix())
        if len(examples) >= limit:
            break
    return examples


def _handover_examples(repo_root: Path) -> list[str]:
    docs = sorted((repo_root / "docs").glob("ALFRED_HANDOVER_*.md"))
    examples = [
        path.relative_to(repo_root).as_posix()
        for path in docs
        if "_DRAFT" not in path.stem
    ]
    return examples[:3]


def infer_repo_growth_facts(repo_root: Optional[Path] = None) -> RepoGrowthFacts:
    """Infer stable placement, naming, and structural rules from the repo."""
    root = repo_root or _REPO_ROOT

    workflow_examples = _relative_examples(root, ".github/workflows/*.y*ml", limit=2)
    if not workflow_examples:
        workflow_examples = [".github/workflows/ci.yml", ".github/workflows/release.yml"]

    schema_examples = _relative_examples(
        root,
        "src/alfred/schemas/*.py",
        exclude_stems={"__init__"},
        limit=3,
    )
    if not schema_examples:
        schema_examples = [
            "src/alfred/schemas/checkpoint.py",
            "src/alfred/schemas/handover.py",
            "src/alfred/schemas/health.py",
        ]

    agent_examples = _relative_examples(
        root,
        "src/alfred/agents/*.py",
        exclude_stems={"__init__"},
        limit=3,
    )
    tool_examples = _relative_examples(
        root,
        "src/alfred/tools/*.py",
        exclude_stems={"__init__"},
        limit=3,
    )
    test_examples = _relative_examples(root, "tests/test_*/*.py", limit=3)
    if not test_examples:
        test_examples = _relative_examples(root, "tests/**/*.py", limit=3)

    docs_examples = _relative_examples(root, "docs/*.md", limit=3)
    handover_examples = _handover_examples(root) or [
        "docs/ALFRED_HANDOVER_6.md",
        "docs/ALFRED_HANDOVER_4_OUTPUT_HARDENING.md",
    ]

    placement_rules = [
        PlacementRule(
            artifact_type="workflow",
            canonical_root=".github/workflows/",
            pattern="*.yml or *.yaml",
            examples=workflow_examples,
        ),
        PlacementRule(
            artifact_type="schema",
            canonical_root="src/alfred/schemas/",
            pattern="{name}.py",
            examples=schema_examples,
            exceptions="Package marker `src/alfred/schemas/__init__.py` is allowed.",
        ),
        PlacementRule(
            artifact_type="agent",
            canonical_root="src/alfred/agents/",
            pattern="{name}.py",
            examples=agent_examples or [
                "src/alfred/agents/planner.py",
                "src/alfred/agents/quality_judge.py",
            ],
        ),
        PlacementRule(
            artifact_type="tool",
            canonical_root="src/alfred/tools/",
            pattern="{name}.py",
            examples=tool_examples or [
                "src/alfred/tools/repo_facts.py",
                "src/alfred/tools/llm.py",
            ],
        ),
        PlacementRule(
            artifact_type="test",
            canonical_root="tests/",
            pattern="test_*.py",
            examples=test_examples or [
                "tests/test_agents/test_planner.py",
                "tests/test_tools/test_repo_facts.py",
            ],
        ),
        PlacementRule(
            artifact_type="doc",
            canonical_root="docs/",
            pattern="*.md",
            examples=docs_examples or [
                "docs/architecture.md",
                "docs/ALFRED_HANDOVER_6.md",
            ],
        ),
        PlacementRule(
            artifact_type="script",
            canonical_root="scripts/",
            pattern="*.py",
            examples=_relative_examples(root, "scripts/*.py", limit=3)
            or ["scripts/generate_phase7.py", "scripts/validate_alfred_planning_facts.py"],
        ),
    ]

    naming_conventions = [
        NamingConvention(
            artifact_type="handover_doc",
            pattern=r"ALFRED_HANDOVER_\d+(_[A-Z0-9_]+)?\.md",
            examples=handover_examples,
        ),
        NamingConvention(
            artifact_type="workflow",
            pattern="kebab-case filename ending in .yml/.yaml",
            examples=workflow_examples,
        ),
        NamingConvention(
            artifact_type="test_module",
            pattern="test_{subject}.py",
            examples=test_examples or ["tests/test_api.py", "tests/test_orchestrator.py"],
        ),
        NamingConvention(
            artifact_type="schema_module",
            pattern="snake_case module name under src/alfred/schemas/",
            examples=schema_examples,
        ),
    ]

    structural_rules = [
        StructuralRule(
            artifact_type="api",
            required_shape="single module at `src/alfred/api.py`",
            forbidden_shape="subpackage such as `src/alfred/api/` or `src/alfred/api/main.py`",
            examples=["src/alfred/api.py"],
        ),
        StructuralRule(
            artifact_type="schema",
            required_shape="one module per schema concern inside `src/alfred/schemas/`",
            forbidden_shape="single catch-all file `src/alfred/schemas.py`",
            examples=schema_examples,
        ),
        StructuralRule(
            artifact_type="agent",
            required_shape="module in `src/alfred/agents/` with mirrored tests in `tests/test_agents/`",
            forbidden_shape="class-based runtime agent hierarchy or misplaced tests",
            examples=agent_examples[:2]
            + ([example for example in test_examples if "/test_agents/" in example][:1]),
        ),
        StructuralRule(
            artifact_type="tool",
            required_shape="module in `src/alfred/tools/` with mirrored tests in `tests/test_tools/`",
            forbidden_shape="top-level helper scripts imported as tool modules",
            examples=tool_examples[:2]
            + ([example for example in test_examples if "/test_tools/" in example][:1]),
        ),
    ]

    return RepoGrowthFacts(
        placement_rules=placement_rules,
        naming_conventions=naming_conventions,
        structural_rules=structural_rules,
    )


def format_repo_growth_facts_for_prompt(
    facts: Optional[RepoGrowthFacts] = None,
    *,
    repo_root: Optional[Path] = None,
) -> str:
    """Render repo-growth conventions for direct prompt injection."""
    resolved = facts or infer_repo_growth_facts(repo_root)
    lines: list[str] = ["Placement rules:"]
    for rule in resolved.placement_rules:
        example_text = ", ".join(f"`{example}`" for example in rule.examples[:2])
        line = (
            f"- `{rule.artifact_type}` -> place under `{rule.canonical_root}` using "
            f"`{rule.pattern}`"
        )
        if example_text:
            line += f"; examples: {example_text}"
        if rule.exceptions:
            line += f"; exception: {rule.exceptions}"
        lines.append(line)

    lines.append("")
    lines.append("Naming conventions:")
    for rule in resolved.naming_conventions:
        example_text = ", ".join(f"`{example}`" for example in rule.examples[:2])
        line = f"- `{rule.artifact_type}` -> `{rule.pattern}`"
        if example_text:
            line += f"; examples: {example_text}"
        lines.append(line)

    lines.append("")
    lines.append("Structural rules:")
    for rule in resolved.structural_rules:
        example_text = ", ".join(f"`{example}`" for example in rule.examples[:2])
        line = (
            f"- `{rule.artifact_type}` -> required: {rule.required_shape}; "
            f"forbidden: {rule.forbidden_shape}"
        )
        if example_text:
            line += f"; examples: {example_text}"
        lines.append(line)

    return "\n".join(lines)


def phase_label_from_handover_text(text: str) -> str:
    """Extract a stable phase label from a handover doc when available."""
    match = re.search(r"\bPhase\s+(\d+)\b", text)
    if match:
        return f"Phase {match.group(1)}"
    return "the latest handover phase"
