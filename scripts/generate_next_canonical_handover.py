"""Generate the canonical handover that plans Phase 3 of the blank-project kickoff demo.

Follows the same validated canonical-generation path as the prior Phase 2
generator, but the planner is now grounded on the live demo plan, the
Phase 1 frozen specs (charter, demo-project layout, kickoff handover
outline), and the Phase 2 canonical handover (`docs/canonical/ALFRED_HANDOVER_9.md`)
which documents the now-shipped execution harness Phase 3 must persist around
— and seeded with the previous canonical handover as continuity context
only. The target output is `docs/canonical/ALFRED_HANDOVER_10.md`,
written only after the structural and grounding validators pass.

Scope of the generated handover: Phase 3 of the demo plan only — carry
proposed stories as first-class runtime state so they survive the
approval gate without regeneration. Phase 2's harness already captures a
structured ``StoryGeneratorOutput`` at the gate via the
``set_agent_runner`` side-channel; Phase 3 must lift that into a durable
schema (proposal records linked to handover+task+approval) so the gate
review and the eventual Phase 4 board write read from the same source of
truth. Phases 4–5 (GitHub write path, rehearsal runbook) are explicitly
out of scope.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

from alfred.schemas.config import AlfredConfig
from alfred.tools.docs_policy import load_docs_policy_entries, resolve_policy_entry
from alfred.tools.handover_authoring_context import (
    AuthoringContextPacket,
    DocumentSelectionSpec,
    SectionSelector,
    build_authoring_context_packet,
)
from alfred.tools.rag import index_corpus

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "default.yaml"

_DOC_REF_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.(?:md|pdf))`")
_LOCAL_PATH_RE = re.compile(
    r"`(?P<path>(?:docs|src|scripts|tests|configs|evals|\.github)/[A-Za-z0-9_./\-]+)`"
)

EXPECTED_HANDOVER_ID = "ALFRED_HANDOVER_10"
EXPECTED_PREVIOUS_HANDOVER = "ALFRED_HANDOVER_9"
DISPLAY_TITLE = "Demo Plan Phase 3 — Carry Proposed Stories As First-Class Runtime State"
SOURCE_FILENAME = f"{EXPECTED_PREVIOUS_HANDOVER}.md"
FAILED_FILENAME = f"{EXPECTED_HANDOVER_ID}_FAILED_CANDIDATE.md"
DEFAULT_CONTEXT_CHARS = 6000

DEMO_PLAN_PATH = REPO_ROOT / "docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md"
DEMO_PHASE1_FROZEN_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md",
    REPO_ROOT / "docs/active/DEMO_PROJECT_LAYOUT.md",
    REPO_ROOT / "docs/active/KICKOFF_HANDOVER_OUTLINE.md",
)
# Phase 2 canonical: documents the just-shipped execution harness (init +
# run scripts, set_agent_runner capture pattern, verbatim approval gate)
# that Phase 3 must persist around. Treated as authoritative scope —
# Phase 3 cannot revisit Phase 2's harness shape, only durably persist
# the StoryProposal items that harness already surfaces at the gate.
DEMO_PHASE2_CANONICAL_PATH: Path = REPO_ROOT / "docs/canonical/ALFRED_HANDOVER_9.md"
AUTHORITATIVE_SCOPE_SELECTION_SPECS: tuple[DocumentSelectionSpec, ...] = (
    DocumentSelectionSpec(
        source_path=DEMO_PLAN_PATH,
        selectors=(
            SectionSelector("Demo Outcome We Are Building Toward", "narrative arc"),
            SectionSelector("Hard Rules", "locked constraints", render_mode="verbatim_only"),
            SectionSelector("Out Of Scope", "locked boundaries"),
            SectionSelector(
                "Minimal Viable Demo Slice",
                "critical path",
                render_mode="verbatim_only",
            ),
            SectionSelector("Required Functional Capabilities", "runtime obligations"),
            SectionSelector(
                "Phase Plan > Phase 3 — Carry Proposed Stories As First-Class Runtime State",
                "active phase scope",
            ),
            SectionSelector(
                "Phase Plan > Phase 4 — Close The HITL Gate Into GitHub Board Writes",
                "next-phase boundary",
            ),
            SectionSelector("Definition Of Demo-Done", "observable completion evidence"),
            SectionSelector("Definition Of Failure", "failure boundaries"),
            SectionSelector("Final Guidance", "demo framing"),
        ),
    ),
    DocumentSelectionSpec(
        source_path=DEMO_PLAN_PATH.parent / "CUSTOMER_ONBOARDING_PORTAL_CHARTER.md",
        selectors=(
            SectionSelector("Business Context", "domain context"),
            SectionSelector("Primary User", "primary user constraints"),
            SectionSelector("Success Metric", "success target"),
            SectionSelector("Known Constraints", "charter constraints"),
            SectionSelector("Explicit Non-Goals", "charter boundaries"),
        ),
    ),
    DocumentSelectionSpec(
        source_path=DEMO_PLAN_PATH.parent / "DEMO_PROJECT_LAYOUT.md",
        selectors=(
            SectionSelector("Frozen Layout", "workspace shape"),
            SectionSelector("File And Directory Purposes", "workspace semantics"),
            SectionSelector("CHARTER.md Source", "charter copy rule", render_mode="verbatim_only"),
            SectionSelector("Directory Decisions", "layout constraints"),
        ),
    ),
    DocumentSelectionSpec(
        source_path=DEMO_PLAN_PATH.parent / "KICKOFF_HANDOVER_OUTLINE.md",
        selectors=(
            SectionSelector("CONTEXT - READ THIS FIRST", "kickoff framing"),
            SectionSelector("WHAT EXISTS TODAY", "kickoff starting state"),
            SectionSelector("KICKOFF GOALS", "kickoff goals"),
            SectionSelector("PROPOSED BACKLOG - CUSTOMER ONBOARDING PORTAL", "benchmark backlog"),
            SectionSelector("BOARD-SEEDING TASK", "task contract", render_mode="verbatim_only"),
            SectionSelector("APPROVAL GATE", "approval wording", render_mode="verbatim_only"),
            SectionSelector("WHAT NOT TO DO", "kickoff guardrails"),
            SectionSelector("POST-MORTEM", "required executor close-out"),
        ),
    ),
    DocumentSelectionSpec(
        source_path=DEMO_PHASE2_CANONICAL_PATH,
        selectors=(
            SectionSelector(
                "WHAT EXISTS TODAY > Module & Agent Inventory",
                "runtime inventory",
            ),
            SectionSelector(
                "WHAT EXISTS TODAY > Phase 1 Deliverables Inherited (Do Not Revisit)",
                "inherited deliverables",
            ),
            SectionSelector(
                "WHAT EXISTS TODAY > Key Design Decisions Inherited (Do Not Revisit)",
                "inherited design decisions",
            ),
            SectionSelector("HARD RULES", "phase 2 hard constraints"),
            SectionSelector("WHAT THIS PHASE PRODUCES", "phase 2 outputs"),
            SectionSelector("TASK OVERVIEW", "task map"),
            SectionSelector(
                "TASK 2 — Demo Execution Harness > Implementation",
                "execution harness shape",
            ),
            SectionSelector(
                "TASK 2 — Demo Execution Harness > Implementation Notes on the Orchestrator Interface",
                "orchestrator interface details",
                render_mode="verbatim_only",
            ),
            SectionSelector("WHAT NOT TO DO", "phase 2 guardrails"),
            SectionSelector("POST-MORTEM", "phase 3 carry-forward"),
        ),
    ),
)


def _resolve_manifest_doc_path(
    filename: str,
    *,
    lifecycle_status: Optional[str] = None,
    kind: Optional[str] = None,
    fallback_relative_path: Path,
) -> Path:
    """Return a docs path from the manifest, falling back to a stable location."""
    for entry in load_docs_policy_entries(REPO_ROOT):
        if Path(entry.current_path).name != filename:
            continue
        if lifecycle_status is not None and entry.lifecycle_status != lifecycle_status:
            continue
        if kind is not None and entry.kind != kind:
            continue
        return REPO_ROOT / entry.current_path
    return REPO_ROOT / fallback_relative_path


SOURCE_PATH = _resolve_manifest_doc_path(
    SOURCE_FILENAME,
    lifecycle_status="canonical",
    kind="canonical_handover",
    fallback_relative_path=Path("docs/canonical") / SOURCE_FILENAME,
)
OUTPUT_PATH = _resolve_manifest_doc_path(
    f"{EXPECTED_HANDOVER_ID}.md",
    lifecycle_status="canonical",
    kind="canonical_handover",
    fallback_relative_path=Path("docs/canonical") / f"{EXPECTED_HANDOVER_ID}.md",
)
FAILED_OUTPUT_PATH = _resolve_manifest_doc_path(
    FAILED_FILENAME,
    lifecycle_status="archive",
    kind="failed_candidate",
    fallback_relative_path=Path("docs/archive") / FAILED_FILENAME,
)
_DOC_PATH_OVERRIDES = {
    f"docs/{EXPECTED_PREVIOUS_HANDOVER}.md": SOURCE_PATH.relative_to(REPO_ROOT).as_posix(),
    f"docs/{EXPECTED_HANDOVER_ID}.md": OUTPUT_PATH.relative_to(REPO_ROOT).as_posix(),
    f"docs/{FAILED_FILENAME}": FAILED_OUTPUT_PATH.relative_to(REPO_ROOT).as_posix(),
}

SPRINT_GOAL = (
    "Generate the canonical handover that plans Phase 3 of the blank-project "
    "kickoff demo plan. Phase 0 (scenario freeze), Phase 1 (kickoff "
    "handover shape, demo-project layout, charter content, board-seeding "
    "task spec, approval-gate wording), and Phase 2 (execution harness — "
    "`scripts/init_demo_workspace.py`, `scripts/run_kickoff_demo.py`, the "
    "`set_agent_runner` story-capture pattern, and the verbatim approval "
    "gate) are already frozen and ratified. This handover must execute "
    "Phase 3 only: carry proposed stories as first-class runtime state so "
    "the approval gate review and the eventual Phase 4 board write read "
    "the same persisted `StoryProposal` records, with no regeneration "
    "between gate and write. Those persisted records are runtime execution "
    "state for continuity across the gate and into Phase 4; they do not "
    "replace the demo project's docs surface or the handover artifact as "
    "Alfred's protocol source of truth. Concretely the handover must specify: "
    "(a) the persistence schema for `StoryProposal` records (Pydantic "
    "model + SQLite table) including linkage back to the source "
    "handover_id and task_id and forward to an approval verdict slot, "
    "(b) where the persistence write happens in the harness flow — Phase "
    "2's `set_agent_runner` capture is the natural insertion point and "
    "should be lifted from a side-channel into a durable write, (c) how "
    "the gate review surfaces the persisted records (CLI listing, API "
    "endpoint, or both) without regenerating stories, (d) how the records "
    "carry approval state (pending → approved → written) through the "
    "Phase 4 boundary without leaking write intent into Phase 3, and "
    "(e) what observable evidence proves Phase 3 is complete prior to "
    "Phase 4 (e.g. inspect persisted rows after a harness run; re-run "
    "the gate listing without re-invoking the story generator). The "
    "handover must also retire two Phase 2 follow-ups now that the "
    "schema layer is open: the orchestrator's `_story_runner` should "
    "persist structured output back onto `TaskResult` so consumers don't "
    "need the `set_agent_runner` side-channel, and `AlfredConfig` should "
    "fail fast when an LLM-dependent path runs with an empty model "
    "string. Phase 4 (GitHub Project V2 write path) and Phase 5 "
    "(rehearsal runbook) deliverables are explicitly out of scope."
)

DEMO_PLAN_GROUNDING = (
    "Authoritative scope sources for this handover (structured facts and "
    "selected verbatim sections included below in the planner context):\n"
    "- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — multi-phase "
    "build plan; this handover plans Phase 3 only.\n"
    "- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — frozen Phase 1 "
    "charter content the harness feeds into Alfred at runtime.\n"
    "- `docs/active/DEMO_PROJECT_LAYOUT.md` — frozen Phase 1 spec for the "
    "demo project's initial filesystem shape; the harness initialises the "
    "workspace to this layout exactly (Phase 2 deliverable shipped).\n"
    "- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — frozen Phase 1 spec for "
    "the kickoff handover the harness produces, including the "
    "board-seeding task (`TASK-SEED-BOARD-001`, `story_generator`) and the "
    "verbatim approval-gate wording.\n"
    "- `docs/canonical/ALFRED_HANDOVER_9.md` — Phase 2 canonical handover "
    "(ratified). Documents the shipped execution harness "
    "(`scripts/init_demo_workspace.py`, `scripts/run_kickoff_demo.py`), "
    "the `set_agent_runner` story-capture pattern, and the live-run "
    "evidence at the approval gate. Phase 3 builds the persistence layer "
    "around this harness; the harness shape itself is locked.\n"
    "Reference-doc rule for the generated canonical: cite every "
    "authoritative source doc that materially constrains the phase. If the "
    "phase still relies directly on the frozen charter or frozen layout, "
    "name those docs directly in `Reference Documents` instead of collapsing "
    "them only into `docs/canonical/ALFRED_HANDOVER_9.md`.\n"
    "Source-of-truth rule for Phase 3: the persisted proposal store is "
    "runtime execution state used to survive the approval gate and support "
    "the later Phase 4 write. It must not be described as replacing the "
    "project docs surface or the handover artifact as Alfred's protocol "
    "source of truth unless a source document explicitly redefines that.\n"
    "Treat the contents of those docs as the source of truth for scope. "
    "Do not invent deliverables outside Phase 3. Do not revisit Phase 0 "
    "freeze decisions, Phase 1 frozen specs, or Phase 2's harness shape. "
    "Do not implement the GitHub Project V2 write path — that is Phase 4. "
    "Do not write a rehearsal runbook — that is Phase 5."
)


def compute_generation_date() -> str:
    """Return today's ISO date. Isolated so tests can patch it."""
    return datetime.date.today().isoformat()


def build_failed_output_path(output_path: Path) -> Path:
    """Where to save a candidate if validation fails before canonical promotion."""
    filename = f"{output_path.stem}_FAILED_CANDIDATE{output_path.suffix}"
    if output_path.is_absolute():
        return _resolve_manifest_doc_path(
            filename,
            lifecycle_status="archive",
            kind="failed_candidate",
            fallback_relative_path=Path("docs/archive") / filename,
        )
    return Path("docs/archive") / filename


def resolve_repo_path(path: Path) -> Path:
    """Resolve relative CLI paths against the repo root."""
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _repo_relative_doc_path(path: Path) -> str:
    """Return ``path`` relative to ``REPO_ROOT`` when possible."""
    resolved = resolve_repo_path(path)
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate the next canonical handover.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_PATH.relative_to(REPO_ROOT),
        help=(
            "Historical handover to use for continuity "
            "(default: docs/canonical/ALFRED_HANDOVER_9.md)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH.relative_to(REPO_ROOT),
        help=(
            "Canonical output path to write on success "
            "(default: docs/canonical/ALFRED_HANDOVER_10.md)"
        ),
    )
    parser.add_argument(
        "--failed-output",
        type=Path,
        default=FAILED_OUTPUT_PATH.relative_to(REPO_ROOT),
        help=(
            "Where to write a failed candidate when validation blocks promotion "
            "(default: docs/archive/ALFRED_HANDOVER_10_FAILED_CANDIDATE.md)"
        ),
    )
    parser.add_argument(
        "--historical-context-mode",
        choices=("summary", "minimal", "none", "full"),
        default="summary",
        help=(
            "How much of the previous canonical handover to pass into the planner. "
            "Default: summary"
        ),
    )
    return parser.parse_args(argv)


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Historical handover"


def _split_level2_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_key: Optional[str] = None
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current_key is not None:
                sections[current_key].append(line)
            continue
        if not in_fence and line.startswith("## "):
            current_key = line[3:].strip().lower()
            sections[current_key] = []
            continue
        if current_key is not None:
            sections[current_key].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _extract_metadata_lines(text: str) -> list[str]:
    keys = ("id", "date", "author", "previous_handover", "baseline_state")
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if any(lowered.startswith(f"**{key}:**") for key in keys):
            lines.append(stripped)
    return lines


def _extract_bullets(text: str, *, max_items: int) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped)
        if len(items) >= max_items:
            break
    return items


def _extract_table_rows(text: str, *, max_rows: int) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped.replace("|", "").strip()) <= {"-"}:
            continue
        rows.append(stripped)
        if len(rows) >= max_rows:
            break
    return rows


def _extract_signal_lines(text: str, *, max_lines: int) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("### ", "```", "<!--")):
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return lines


def _truncate_context(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    last_break = trimmed.rfind("\n")
    if last_break > max_chars // 2:
        trimmed = trimmed[:last_break]
    return trimmed.rstrip() + "\n\n[Historical context truncated]"


def _normalise_doc_reference_path(path: str) -> str:
    if path in _DOC_PATH_OVERRIDES:
        return _DOC_PATH_OVERRIDES[path]

    entry = resolve_policy_entry(path, REPO_ROOT)
    if entry is not None:
        return entry.current_path

    basename = Path(path).name
    matches = [
        candidate.current_path
        for candidate in load_docs_policy_entries(REPO_ROOT)
        if Path(candidate.current_path).name == basename
    ]
    unique_matches = sorted(set(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    return path


def _is_citable_doc_reference(path: str) -> bool:
    entry = resolve_policy_entry(path, REPO_ROOT)
    if entry is not None:
        return entry.citable
    normalised = _normalise_doc_reference_path(path)
    entry = resolve_policy_entry(normalised, REPO_ROOT)
    if entry is not None:
        return entry.citable
    if normalised.startswith("docs/archive/") or Path(normalised).name.endswith("_FAILED_CANDIDATE.md"):
        return False
    return True


def _normalise_historical_text(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        path = match.group("path")
        return f"`{_normalise_doc_reference_path(path)}`"

    return _DOC_REF_RE.sub(replacer, text)


def _normalise_reference_bullets(lines: list[str]) -> list[str]:
    normalised: list[str] = []
    for line in lines:
        doc_refs = [match.group("path") for match in _DOC_REF_RE.finditer(line)]
        if doc_refs and not all(_is_citable_doc_reference(path) for path in doc_refs):
            continue
        normalised.append(_normalise_historical_text(line))
    return normalised


def _archive_doc_label(path: str) -> str:
    filename = Path(path).name
    if filename == FAILED_FILENAME:
        return "the archived failed candidate"
    return f"archived document {filename}"


def _clean_reference_documents_block(markdown: str) -> str:
    lines = markdown.splitlines()
    cleaned: list[str] = []
    in_refs = False

    for line in lines:
        stripped = line.strip()
        if stripped == "**Reference Documents:**":
            in_refs = True
            cleaned.append(line)
            continue

        if in_refs:
            if stripped.startswith("- "):
                doc_refs = [match.group("path") for match in _DOC_REF_RE.finditer(line)]
                if doc_refs and not all(_is_citable_doc_reference(path) for path in doc_refs):
                    continue
                cleaned.append(_normalise_historical_text(line))
                continue
            if stripped:
                in_refs = False
            else:
                cleaned.append(line)
                continue

        cleaned.append(line)

    return "\n".join(cleaned)


def _rewrite_generated_doc_refs(markdown: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        path = match.group("path")
        if _is_citable_doc_reference(path):
            return f"`{_normalise_doc_reference_path(path)}`"
        return _archive_doc_label(_normalise_doc_reference_path(path))

    return _DOC_REF_RE.sub(replacer, markdown)


def _strip_backticks_from_nonexistent_current_state_paths(markdown: str) -> str:
    current_h2s = {"context — read this first", "what exists today"}
    current_section: Optional[str] = None
    lines: list[str] = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            lines.append(line)
            continue

        if current_section not in current_h2s:
            lines.append(line)
            continue

        def replacer(match: re.Match[str]) -> str:
            path = match.group("path").rstrip("/")
            normalised = _normalise_doc_reference_path(path)
            resolved = REPO_ROOT / normalised
            if resolved.exists():
                return f"`{normalised}`"
            return normalised

        lines.append(_LOCAL_PATH_RE.sub(replacer, line))

    return "\n".join(lines)


def normalise_generated_markdown(markdown: str) -> str:
    """Rewrite generated doc/path references to current policy-safe forms."""
    rewritten = _rewrite_generated_doc_refs(markdown)
    rewritten = _clean_reference_documents_block(rewritten)
    rewritten = _strip_backticks_from_nonexistent_current_state_paths(rewritten)
    return rewritten


def load_demo_plan_context() -> AuthoringContextPacket:
    """Build a deterministic authoring packet from the authoritative docs."""
    existing_specs = tuple(
        spec
        for spec in AUTHORITATIVE_SCOPE_SELECTION_SPECS
        if spec.source_path.is_file()
    )
    if not existing_specs:
        return AuthoringContextPacket(
            text="",
            source_doc_paths=(),
            selected_sections=(),
            facts=(),
            source_char_count=0,
            packet_char_count=0,
        )
    return build_authoring_context_packet(
        existing_specs,
        repo_root=REPO_ROOT,
        intro_lines=(
            "===== AUTHORITATIVE PHASE 3 AUTHORING PACKET — DO NOT TREAT AS HISTORICAL CONTINUITY =====",
            "Pass 1 indexed the authoritative docs by headings, rules, task specs, inherited constraints, and phase-detail sections.",
            "Pass 2 selected only the sections needed to author the Phase 3 canonical handover and rendered structured facts plus verbatim source excerpts.",
            "The source docs remain authoritative. The extracted packet is a deterministic view over those docs, not a replacement for them.",
            "",
            "===== AUTHORITATIVE SOURCE DOC MAP =====",
            "- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — Phase 3 scope, hard rules, done/failure conditions.",
            "- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — frozen kickoff charter input; still authoritative when describing what the harness reads.",
            "- `docs/active/DEMO_PROJECT_LAYOUT.md` — frozen workspace-shape contract; still authoritative when describing docs surface and external-workspace paths.",
            "- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — frozen board-seeding task and verbatim approval-gate wording.",
            "- `docs/canonical/ALFRED_HANDOVER_9.md` — ratified Phase 2 harness behavior and explicit Phase 3 follow-ups.",
            "Reference-doc expectation: the generated canonical should cite every authoritative source doc materially relied upon by the phase, including inherited frozen docs such as the charter and layout when their constraints are used directly.",
            "Source-of-truth expectation: persisted StoryProposal rows are runtime execution state for gate review and later board writes; they do not replace the demo project's docs surface or the handover artifact as Alfred's protocol source of truth.",
        ),
    )


def load_historical_context(
    source_path: Path,
    *,
    mode: str = "summary",
    max_chars: int = DEFAULT_CONTEXT_CHARS,
    excluded_doc_paths: tuple[str, ...] = (),
) -> Optional[str]:
    """Load a bounded historical context block for the planner."""
    if not source_path.is_file():
        return None
    if mode == "none":
        return None
    if _repo_relative_doc_path(source_path) in set(excluded_doc_paths):
        return None
    text = source_path.read_text(encoding="utf-8")
    if mode == "full":
        return (
            "Update the next canonical handover so it matches the live repository "
            f"today. Preserve the new handover identity (`{EXPECTED_HANDOVER_ID}`) and "
            "treat the previous canonical handover as continuity input, but prefer "
            "repo facts, validators, and git history over any stale prose.\n\n"
            f"{DEMO_PLAN_GROUNDING}\n\n"
            "Historical source: previous canonical handover (continuity only).\n\n"
            "---BEGIN HISTORICAL HANDOVER---\n"
            f"{_normalise_historical_text(text)}\n"
            "---END HISTORICAL HANDOVER---"
        )

    sections = _split_level2_sections(text)
    title = _extract_title(text)
    metadata = _extract_metadata_lines(text)
    context_body = sections.get("context — read this first", "")
    what_exists = sections.get("what exists today", "")
    produces = sections.get("what this phase produces", "") or sections.get(
        "what this handover produces", ""
    )
    task_overview = sections.get("task overview", "")

    parts: list[str] = [
        "Use this previous canonical handover for continuity only. Treat repo facts, "
        "validator findings, reference-doc checks, and current git history as more "
        "authoritative than any stale content from the earlier phase handover.",
        DEMO_PLAN_GROUNDING,
        "Historical source: previous canonical handover (continuity only).",
        f"Historical title: {title}",
    ]
    if metadata:
        parts.append("Historical metadata:")
        parts.extend(metadata[:5])

    if mode == "summary":
        ref_docs = _normalise_reference_bullets(_extract_bullets(context_body, max_items=4))
        if ref_docs:
            parts.append("Historical reference documents:")
            parts.extend(ref_docs)

        task_rows = [
            _normalise_historical_text(line)
            for line in _extract_table_rows(task_overview, max_rows=8)
        ]
        if task_rows:
            parts.append("Historical task overview:")
            parts.extend(task_rows)

        current_lines = [
            _normalise_historical_text(line)
            for line in _extract_signal_lines(what_exists, max_lines=10)
        ]
        if current_lines:
            parts.append("Historical WHAT EXISTS TODAY snapshot (may be stale):")
            parts.extend(current_lines)

        produces_lines = [
            _normalise_historical_text(line)
            for line in _extract_bullets(produces, max_items=8)
        ]
        if produces_lines:
            parts.append("Historical planned deliverables:")
            parts.extend(produces_lines)

    elif mode == "minimal":
        task_rows = [
            _normalise_historical_text(line)
            for line in _extract_table_rows(task_overview, max_rows=8)
        ]
        if task_rows:
            parts.append("Historical task overview:")
            parts.extend(task_rows)

    return _truncate_context("\n".join(parts), max_chars=max_chars)


def build_context_attempt_order(requested_mode: str) -> list[str]:
    """Return ordered context modes for planner fallback attempts."""
    orders = {
        "full": ["full", "summary", "minimal", "none"],
        "summary": ["summary", "minimal", "none"],
        "minimal": ["minimal", "none"],
        "none": ["none"],
    }
    return orders[requested_mode]


def build_planner_context(
    authoritative_scope: AuthoringContextPacket | str,
    source_path: Path,
    *,
    mode: str,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
) -> tuple[Optional[str], int]:
    """Assemble planner context while skipping duplicated continuity docs."""
    if isinstance(authoritative_scope, str):
        scope_text = authoritative_scope
        source_rel = _repo_relative_doc_path(source_path)
        scope_doc_paths = (source_rel,) if source_rel in scope_text else ()
    else:
        scope_text = authoritative_scope.text
        scope_doc_paths = authoritative_scope.source_doc_paths

    historical_context = load_historical_context(
        source_path,
        mode=mode,
        max_chars=max_chars,
        excluded_doc_paths=scope_doc_paths,
    )
    parts = [block for block in (scope_text, historical_context) if block]
    context = "\n\n".join(parts) if parts else None
    historical_chars = len(historical_context) if historical_context else 0
    return context, historical_chars


def validate_candidate(
    markdown: str,
    *,
    output_path: Path,
    expected_date: str,
) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` from the promotion validators."""
    from validate_alfred_handover import validate as validate_handover_structure
    from validate_alfred_planning_facts import (
        validate_current_state_facts,
        validate_future_task_realism,
    )

    errors: list[str] = []
    warnings: list[str] = []

    for message in validate_handover_structure(markdown):
        errors.append(f"[STRUCTURE] {message}")

    factual = validate_current_state_facts(
        markdown,
        source_path=output_path,
        expected_id=EXPECTED_HANDOVER_ID,
        expected_previous=EXPECTED_PREVIOUS_HANDOVER,
        expected_date=expected_date,
    )
    realism = validate_future_task_realism(markdown)

    for finding in factual + realism:
        formatted = finding.format()
        if finding.severity == "error":
            errors.append(formatted)
        else:
            warnings.append(formatted)

    return errors, warnings


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    source_path = resolve_repo_path(args.source)
    output_path = resolve_repo_path(args.output)
    failed_output_path = (
        resolve_repo_path(args.failed_output)
        if args.failed_output is not None
        else build_failed_output_path(output_path)
    )

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = AlfredConfig.model_validate(yaml.safe_load(f))

    print("Indexing corpus...")
    n = index_corpus(
        config.rag.corpus_path,
        config.rag.index_path,
        config.rag.embedding_model,
    )
    print(f"  {n} chunks indexed from {config.rag.corpus_path!r}")

    from alfred.agents.planner import load_canonical_template, run_planner
    from alfred.orchestrator import _run_critique_loop
    from alfred.schemas.agent import BoardState, PlannerInput
    from alfred.schemas.handover import HandoverContext, HandoverDocument
    from alfred.tools.git_log import read_git_log
    from alfred.tools.llm import resolve_model
    from alfred.tools.persistence import get_velocity_history
    from alfred.tools.rag import retrieve
    from alfred.tools.repo_facts import build_repo_facts_summary

    retrieval_query = (
        f"{SPRINT_GOAL} {EXPECTED_HANDOVER_ID} canonical generation {source_path.name}"
    )
    chunks = retrieve(retrieval_query, config.rag.index_path, top_k=6)
    print(f"  {len(chunks)} RAG chunks retrieved")

    if source_path.is_file():
        print(f"Loaded historical handover source from {source_path}")
    else:
        print(f"WARNING: source handover not found at {source_path}; generating without it")

    board = BoardState()
    if config.github.org and config.github.project_number:
        token = os.environ.get(config.github.token_env_var, "")
        if token:
            from alfred.tools.github_api import get_board_state

            board = get_board_state(
                config.github.org,
                config.github.project_number,
                token,
            )

    velocity = []
    if config.database.path:
        velocity = get_velocity_history(config.database.path, sprint_count=10)

    canonical_template = load_canonical_template(config.handover.template_path)
    if canonical_template:
        print(f"Loaded Alfred canonical scaffold from {config.handover.template_path}")
    else:
        print(
            f"WARNING: no canonical scaffold loaded from {config.handover.template_path!r}; "
            "generated candidate will not be promotion-safe without manual fixup."
        )

    git_history = read_git_log(max_commits=12)
    if git_history:
        print(f"  {len(git_history)} git commits loaded for ### Git History")
    else:
        print("WARNING: no git history available; ### Git History will be a TBD marker")

    repo_facts = build_repo_facts_summary()
    print(f"  {len(repo_facts)} repo-truth facts computed from live workspace")

    generation_date = compute_generation_date()
    print(
        f"Identity metadata: id={EXPECTED_HANDOVER_ID}, "
        f"previous={EXPECTED_PREVIOUS_HANDOVER}, date={generation_date}"
    )

    plan_provider, plan_model = resolve_model("plan", config)
    print(f"Calling planner ({plan_provider}/{plan_model})...")
    from alfred.tools.llm import LLMError

    demo_plan_context = load_demo_plan_context()
    if demo_plan_context.text:
        print(
            f"  Authoring context: {demo_plan_context.packet_char_count} chars from "
            f"{len(demo_plan_context.selected_sections)} selected sections across "
            f"{len(demo_plan_context.source_doc_paths)} source docs "
            f"({demo_plan_context.source_char_count} raw chars)"
        )
    else:
        print(
            "WARNING: authoritative scope docs missing; planner will lack the "
            "ratified Phase 3 scope brief."
        )

    planner_out = None
    last_error: Optional[Exception] = None
    for mode in build_context_attempt_order(args.historical_context_mode):
        current_handover_context, historical_chars = build_planner_context(
            demo_plan_context,
            source_path,
            mode=mode,
        )
        if current_handover_context:
            print(
                f"  Planner context mode `{mode}` with "
                f"{len(current_handover_context)} chars total "
                f"({demo_plan_context.packet_char_count} scope + "
                f"{historical_chars} historical)"
            )
        else:
            print(f"  Planner context mode `{mode}` with no context at all")
        if (
            source_path.is_file()
            and _repo_relative_doc_path(source_path) in set(demo_plan_context.source_doc_paths)
            and historical_chars == 0
        ):
            print(
                "  Historical continuity source already appears in authoritative "
                "scope; duplicate continuity context skipped"
            )
        try:
            planner_out = run_planner(
                PlannerInput(
                    board_state=board,
                    velocity_history=velocity,
                    sprint_goal=SPRINT_GOAL,
                    prior_handover_summaries=chunks,
                    current_handover_context=current_handover_context,
                    canonical_template=canonical_template,
                    git_history_summary=git_history,
                    repo_facts_summary=repo_facts,
                    generation_date=generation_date,
                    expected_handover_id=EXPECTED_HANDOVER_ID,
                    expected_previous_handover=EXPECTED_PREVIOUS_HANDOVER,
                ),
                provider=plan_provider,
                model=plan_model,
                db_path=config.database.path,
            )
            break
        except LLMError as exc:
            last_error = exc
            print(f"  Planner failed with `{mode}` context: {exc}")
            continue

    if planner_out is None:
        assert last_error is not None
        raise last_error

    temp_handover = HandoverDocument(
        id=EXPECTED_HANDOVER_ID,
        title=DISPLAY_TITLE,
        date=datetime.date.fromisoformat(generation_date),
        author="alfred",
        context=HandoverContext(narrative=""),
    )
    print("Running critique loop...")
    best_draft = _run_critique_loop(
        planner_out.draft_handover_markdown,
        temp_handover,
        config,
        config.database.path,
        repo_facts_summary=repo_facts,
        generation_date=generation_date,
        expected_handover_id=EXPECTED_HANDOVER_ID,
        expected_previous_handover=EXPECTED_PREVIOUS_HANDOVER,
    )
    best_draft = normalise_generated_markdown(best_draft)

    errors, warnings = validate_candidate(
        best_draft,
        output_path=output_path,
        expected_date=generation_date,
    )
    if warnings:
        print("\nValidator warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        failed_output_path.parent.mkdir(parents=True, exist_ok=True)
        failed_output_path.write_text(best_draft, encoding="utf-8")
        print("\nValidation failed; canonical file was NOT updated.")
        print(f"Candidate written to {failed_output_path}")
        print("Blocking issues:")
        for error in errors:
            print(f"  - {error}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(best_draft, encoding="utf-8")
    print(f"\nCanonical handover written to {output_path}")
    print(f"Critique iterations: {len(temp_handover.critique_history)}")
    print("\n--- DRAFT PREVIEW (first 60 lines) ---")
    lines = best_draft.splitlines()
    print("\n".join(lines[:60]))
    if len(lines) > 60:
        print(f"\n... ({len(lines) - 60} more lines in {output_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
