"""Generate the next canonical handover from the PhaseLedger + active Brief.

Identity (`handover_id`, `previous_handover`, display title), sprint goal,
demo-plan grounding, and argparse defaults are derived deterministically
from `docs/active/PHASE_LEDGER.yaml` and the planning row's `Brief` via
`alfred.render.handover_inputs.render_handover_inputs`. Advancing phases
is now "edit the ledger, run the script" — no hand-edited identity
literals live in this module.

The downstream pipeline (planner call, three-role `ContextBundle`
assembly, contract-driven canonical-handover summary, validators, and
promotion) is unchanged from Slice 5. Phase-specific narrative for the
generated draft comes from the brief; this module is a thin orchestrator.
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

from alfred.context import ContextBundle, ContextItem, summarize_canonical_handover
from alfred.docs.contract_validator import split_markdown_by_contract
from alfred.docs.contracts import DocContract, get_doc_class_contract
from alfred.ledger.loader import load_ledger
from alfred.render.handover_inputs import (
    HandoverInputs,
    render_handover_inputs,
    select_active_phase,
)
from alfred.schemas.config import AlfredConfig
from alfred.tools.docs_policy import (
    is_citable_doc,
    load_docs_policy_entries,
    resolve_policy_entry,
)
from alfred.tools.handover_authoring_context import (
    AuthoringContextPacket,
    DocumentSelectionSpec,
    SectionSelector,
    build_authoring_context_packet,
)
from alfred.tools.rag import index_corpus
from alfred.validate import PreflightError, format_errors, run_preflight

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "default.yaml"

_DOC_REF_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.(?:md|pdf))`")
_LOCAL_PATH_RE = re.compile(
    r"`(?P<path>(?:docs|src|scripts|tests|configs|evals|\.github)/[A-Za-z0-9_./\-]+)`"
)

LEDGER_PATH = REPO_ROOT / "docs/active/PHASE_LEDGER.yaml"
HANDOVER_INPUTS: HandoverInputs = render_handover_inputs(load_ledger(LEDGER_PATH))

# Identity is derived from the ledger; these names are kept for minimal-diff
# compatibility with downstream callers and tests, but they are no longer
# hand-edited literals.
EXPECTED_HANDOVER_ID = HANDOVER_INPUTS.handover_id
EXPECTED_PREVIOUS_HANDOVER = HANDOVER_INPUTS.previous_handover
DISPLAY_TITLE = HANDOVER_INPUTS.display_title
SPRINT_GOAL = HANDOVER_INPUTS.sprint_goal
DEMO_PLAN_GROUNDING = HANDOVER_INPUTS.demo_plan_grounding
SOURCE_FILENAME = f"{EXPECTED_PREVIOUS_HANDOVER}.md"
FAILED_FILENAME = f"{EXPECTED_HANDOVER_ID}_FAILED_CANDIDATE.md"
DEFAULT_CONTEXT_CHARS = 6000

CONTEXT_PATH = REPO_ROOT / "CONTEXT.md"
WORKFLOW_DISCUSSION_PATH = REPO_ROOT / "docs/active/HANDOVER_WORKFLOW_DISCUSSION.md"
POST_GRILL_PLAN_PATH = REPO_ROOT / "docs/active/POST_GRILL_1.md"
LEDGER_FILE_PATH = LEDGER_PATH


def _previous_canonical_handover_path() -> Path:
    """Return the previous canonical handover path derived from the ledger.

    Defined here (forward-declared) so AUTHORITATIVE_SCOPE_SELECTION_SPECS can
    cite the previous handover by derived identity rather than hand-edited
    literal. Resolution against the docs manifest happens later via
    ``_resolve_manifest_doc_path`` for the same filename.
    """
    return REPO_ROOT / "docs/canonical" / SOURCE_FILENAME


AUTHORITATIVE_SCOPE_SELECTION_SPECS: tuple[DocumentSelectionSpec, ...] = (
    DocumentSelectionSpec(
        source_path=CONTEXT_PATH,
        selectors=(
            SectionSelector(
                "Phase Ledger",
                "canonical definition of the derived ledger and its authority flow",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Brief",
                "canonical definition of the human-authored editorial seed the renderer must consume",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Context Roles",
                "canonical definition of the three planner-context roles that Slice 6 must preserve",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Doc Class",
                "section-contract semantics that the preserved bundle/historical-summary seam still relies on",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "No-LLM-Judge Constraint",
                "deterministic validation constraint that still governs the renderer-backed generator",
            ),
        ),
    ),
    DocumentSelectionSpec(
        source_path=WORKFLOW_DISCUSSION_PATH,
        selectors=(
            SectionSelector(
                "Resolved (Concern X)",
                "accepted seam-discipline decisions that Slice 6 must honor",
                render_mode="facts_only",
            ),
            SectionSelector(
                "Proposal Sketch — Now Resolved > A. Phase manifest as the source of truth",
                "resolved phase-ledger rationale and authority-flow constraint that Slice 6 must operationalise",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Proposal Sketch — Now Resolved > B. Sprint goal as a structured object, not a paragraph",
                "resolved brief rationale and required editorial fields the renderer must consume",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Proposal Sketch — Now Resolved > D. Test the renderer, not the prose",
                "renderer-fixture testing rule that Slice 6 should make concrete",
                render_mode="facts_and_verbatim",
            ),
            SectionSelector(
                "Proposal Sketch — Now Resolved > F. Context assembly should be provenance-aware",
                "slice-5 bundle seam that Slice 6 must preserve rather than redesign",
                render_mode="facts_and_verbatim",
            ),
        ),
    ),
    DocumentSelectionSpec(
        source_path=POST_GRILL_PLAN_PATH,
        selectors=(
            SectionSelector("Overview", "overall slice framing"),
            SectionSelector(
                DISPLAY_TITLE,
                "active slice scope, files, tests, and acceptance criteria",
                render_mode="facts_and_verbatim",
            ),
        ),
    ),
    DocumentSelectionSpec(
        source_path=_previous_canonical_handover_path(),
        selectors=(
            SectionSelector(
                "WHAT EXISTS TODAY",
                "current repository and generator state inherited from the previous ratified phase",
            ),
            SectionSelector(
                "WHAT EXISTS TODAY > Key Design Decisions Inherited (Do Not Revisit)",
                "decisions from the prior ratified phase that remain locked",
            ),
            SectionSelector(
                "POST-MORTEM",
                "ratified close-out and explicit forward plan to the active phase",
                render_mode="facts_and_verbatim",
            ),
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

def compute_generation_date() -> str:
    """Return today's ISO date. Isolated so tests can patch it."""
    return datetime.date.today().isoformat()


def render_dry_run_report(
    inputs: HandoverInputs,
    *,
    source_path: Path,
    output_path: Path,
    failed_output_path: Path,
) -> str:
    """Render the ``--dry-run`` block deterministically from a HandoverInputs.

    Pure function over its arguments — no module-level globals — so tests
    can drive it with a fixture-derived ``HandoverInputs`` and confirm
    every line of the script-boundary output follows the fixture identity.
    """
    return "\n".join(
        [
            "--- DRY RUN: renderer-derived identity ---",
            f"# {inputs.display_title}",
            f"id: {inputs.handover_id}",
            f"previous_handover: {inputs.previous_handover}",
            f"would-read source:   {source_path}",
            f"would-write output:  {output_path}",
            f"would-write failed:  {failed_output_path}",
            "(no LLM call, no files modified)",
        ]
    )


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
        help=HANDOVER_INPUTS.argparse_defaults.source_help,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH.relative_to(REPO_ROOT),
        help=HANDOVER_INPUTS.argparse_defaults.output_help,
    )
    parser.add_argument(
        "--failed-output",
        type=Path,
        default=FAILED_OUTPUT_PATH.relative_to(REPO_ROOT),
        help=HANDOVER_INPUTS.argparse_defaults.failed_output_help,
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the renderer-derived identity and the paths the script "
            "would write, then exit before any LLM call. Does not modify the "
            "canonical or archive output paths."
        ),
    )
    return parser.parse_args(argv)


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Historical handover"


def _canonical_handover_contract() -> DocContract:
    return get_doc_class_contract("canonical_handover", repo_root=REPO_ROOT)


def _split_level2_sections(markdown: str) -> dict[str, str]:
    return split_markdown_by_contract(markdown, _canonical_handover_contract())


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
    previous_handover_doc = (
        f"`docs/canonical/{EXPECTED_PREVIOUS_HANDOVER}.md` — previous "
        "ratified canonical handover (continuity input for the active phase)."
    )
    intro_lines = (
        f"===== AUTHORITATIVE AUTHORING PACKET FOR {EXPECTED_HANDOVER_ID} "
        f"({DISPLAY_TITLE}) — DO NOT TREAT AS HISTORICAL CONTINUITY =====",
        "Pass 1 indexed the authoritative docs by phase-ledger/brief "
        "source-of-truth semantics and preserved context-bundle "
        "constraints from prior ratified phases.",
        f"Pass 2 selected only the sections needed to author the "
        f"{EXPECTED_HANDOVER_ID} renderer brief and rendered structured "
        "facts plus verbatim source excerpts.",
        "The source docs remain authoritative. The extracted packet is a "
        "deterministic view over those docs, not a replacement for them.",
        "",
        "===== AUTHORITATIVE SOURCE DOC MAP =====",
        "- `CONTEXT.md` — canonical glossary for `Phase Ledger`, `Brief`, "
        "`Context Roles`, `Doc Class`, and the no-LLM validator rule.",
        "- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — resolved "
        "Concern X rationale for phase ledger, brief, renderer-fixture "
        "tests, and preserved provenance-aware context assembly.",
        "- `docs/active/POST_GRILL_1.md` — post-grill implementation "
        "plan; this handover plans the active brief's slice only.",
        f"- {previous_handover_doc}",
        "- `docs/active/PHASE_LEDGER.yaml` — seed ledger input; repo "
        "truth for concrete renderer inputs and active-phase selection "
        "(this is where the renderer reads its identity from).",
        "Reference-doc expectation: the generated canonical should cite "
        "the markdown source docs directly, and cite "
        "`docs/active/PHASE_LEDGER.yaml` when concrete renderer inputs or "
        "active-phase selection examples materially constrain the phase.",
        "Source-of-truth expectation: identity, sprint goal, and demo "
        "plan grounding are derived from `PhaseLedger` + the active "
        "`Brief` while preserving the typed `ContextBundle` seam and "
        "the contract-driven continuity summarizer.",
    )
    return build_authoring_context_packet(
        existing_specs,
        repo_root=REPO_ROOT,
        intro_lines=intro_lines,
    )


def required_citable_docs(source_path: Path) -> tuple[str, ...]:
    """Return repo-relative docs that must be citable before planning starts."""
    doc_paths: list[str] = []
    if source_path.is_file():
        doc_paths.append(_repo_relative_doc_path(source_path))
    for spec in AUTHORITATIVE_SCOPE_SELECTION_SPECS:
        if spec.source_path.is_file():
            doc_paths.append(_repo_relative_doc_path(spec.source_path))
    # Preserve order while deduplicating.
    return tuple(dict.fromkeys(doc_paths))


def validate_required_citable_docs(source_path: Path) -> list[str]:
    """Return any required docs that exist on disk but are not citable."""
    missing: list[str] = []
    for rel_path in required_citable_docs(source_path):
        if not is_citable_doc(rel_path, REPO_ROOT):
            missing.append(rel_path)
    return missing


def run_generator_preflight(source_path: Path) -> list[PreflightError]:
    """Run the deterministic Slice-7 preflight before any planner / LLM call.

    Builds one context-input plan from the ledger + the script's
    ``AUTHORITATIVE_SCOPE_SELECTION_SPECS`` and feeds it to
    :func:`alfred.validate.run_preflight`. The same plan reflects what the
    downstream :func:`build_planner_context` call will register, so
    validation and runtime cannot drift.

    Important: the input lists are constructed **before** any
    ``Path.is_file()`` filtering. A missing scope doc must surface as a
    preflight Check-A failure rather than silently disappearing from the
    packet builder's input set.

    Role-assignment plan: each authoritative-scope source gets role
    ``scope``; the previous canonical handover gets role ``continuity``
    only when it is not already an authoritative scope source — the
    Slice-5 ``ContextBundle`` applies the same precedence at runtime via
    dedup, so collapsing it here avoids flagging the intentional
    defensive registration while still catching genuine misassignments.
    """
    ledger = load_ledger(LEDGER_PATH)
    active = select_active_phase(ledger)

    scope_paths = tuple(
        spec.source_path for spec in AUTHORITATIVE_SCOPE_SELECTION_SPECS
    )
    scope_rel_paths = tuple(_repo_relative_doc_path(p) for p in scope_paths)
    role_assignments: list[tuple[str, str]] = [
        (rel, "scope") for rel in scope_rel_paths
    ]
    source_rel = _repo_relative_doc_path(source_path)
    if source_rel not in scope_rel_paths:
        role_assignments.append((source_rel, "continuity"))

    reference_tag_sources = tuple(p for p in scope_paths if p.suffix == ".md")

    return run_preflight(
        ledger=ledger,
        scope_paths=scope_paths,
        carry_forward_phase_ids=tuple(active.scope_carry_forward),
        previous_handover_path=source_path,
        expected_handover_id=EXPECTED_HANDOVER_ID,
        role_assignments=tuple(role_assignments),
        reference_tag_sources=reference_tag_sources,
    )


def _render_historical_continuity(
    text: str,
    *,
    mode: str,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
) -> Optional[str]:
    """Render the deterministic historical continuity block from raw markdown.

    Used both by :func:`load_historical_context` (file-reading wrapper kept for
    callers that take a ``Path``) and by the bundle summarizer in
    :func:`build_planner_context`. Section identity comes from the Slice 4
    ``canonical_handover`` contract via :func:`_split_level2_sections` — no
    heading strings are hardcoded here.
    """
    if mode == "none":
        return None
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
    context_body = sections.get("context", "")
    what_exists = sections.get("current_state", "")
    produces = sections.get("deliverables", "")
    task_overview = sections.get("task_overview", "")

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
    return _render_historical_continuity(text, mode=mode, max_chars=max_chars)


def build_context_attempt_order(requested_mode: str) -> list[str]:
    """Return ordered context modes for planner fallback attempts."""
    orders = {
        "full": ["full", "summary", "minimal", "none"],
        "summary": ["summary", "minimal", "none"],
        "minimal": ["minimal", "none"],
        "none": ["none"],
    }
    return orders[requested_mode]


_SCOPE_PACKET_PATH = "<scope-packet>"


def build_planner_context(
    authoritative_scope: AuthoringContextPacket | str,
    source_path: Path,
    *,
    mode: str,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
    carry_forward_items: tuple[ContextItem, ...] = (),
) -> tuple[Optional[str], int]:
    """Assemble planner context via a typed three-role :class:`ContextBundle`.

    The bundle is the assembly mechanism — not just a dedup check. Each
    authoritative-scope source path is registered as a ``scope`` item, the
    pre-rendered scope packet flows through one synthetic-path ``scope`` item,
    optional ``carry_forward_items`` are inserted directly into the bundle,
    and the previous canonical handover is registered as a ``continuity`` item
    carrying the raw source markdown. ``ContextBundle.render()`` then applies
    role-specific rendering and dedup precedence — when the source handover's
    path collides with a scope source, the continuity item is dropped
    deterministically (preserving the Phase 3 duplicate-context fix).

    Summarizer dispatch:
    - ``continuity`` items use the mode-aware
      :func:`_render_historical_continuity` so the existing
      ``--historical-context-mode`` degradation path (full/summary/minimal) is
      preserved without reintroducing hardcoded heading strings.
    - ``carry_forward`` canonical-handover items use the contract-driven
      :func:`summarize_canonical_handover` (Slice 4 deterministic summary).
    """
    for item in carry_forward_items:
        if item.role != "carry_forward":
            raise ValueError(
                f"carry_forward_items must all carry role='carry_forward'; "
                f"got {item.role!r} on {item.path!r}."
            )
    if isinstance(authoritative_scope, str):
        scope_text = authoritative_scope
        source_rel = _repo_relative_doc_path(source_path)
        scope_doc_paths: tuple[str, ...] = (
            (source_rel,) if source_rel in scope_text else ()
        )
    else:
        scope_text = authoritative_scope.text
        scope_doc_paths = authoritative_scope.source_doc_paths

    source_rel = _repo_relative_doc_path(source_path)

    items: list[ContextItem] = []
    if scope_text:
        items.append(
            ContextItem(path=_SCOPE_PACKET_PATH, role="scope", text=scope_text)
        )
    seen_scope_paths: set[str] = {_SCOPE_PACKET_PATH}
    for path in scope_doc_paths:
        if path in seen_scope_paths:
            continue
        seen_scope_paths.add(path)
        items.append(ContextItem(path=path, role="scope", text=""))

    items.extend(carry_forward_items)

    if mode != "none" and source_path.is_file():
        raw_source_text = source_path.read_text(encoding="utf-8")
        items.append(
            ContextItem(
                path=source_rel,
                role="continuity",
                text=raw_source_text,
                is_canonical_handover=True,
            )
        )

    def _summarizer(item: ContextItem) -> str:
        if item.role == "continuity":
            rendered = _render_historical_continuity(
                item.text, mode=mode, max_chars=max_chars
            )
            return rendered or ""
        # carry_forward canonical handovers use the Slice 4 contract-driven
        # deterministic summary (default bundle path).
        return summarize_canonical_handover(item.text)

    rendered_items = ContextBundle(items=tuple(items)).render(
        summarizer=_summarizer
    )

    blocks = [rendered.rendered_text for rendered in rendered_items if rendered.rendered_text]
    context = "\n\n".join(blocks) if blocks else None
    historical_chars = sum(
        len(rendered.rendered_text)
        for rendered in rendered_items
        if rendered.item.role == "continuity" and rendered.rendered_text
    )
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
    print(HANDOVER_INPUTS.module_docstring)

    source_path = resolve_repo_path(args.source)
    output_path = resolve_repo_path(args.output)
    failed_output_path = (
        resolve_repo_path(args.failed_output)
        if args.failed_output is not None
        else build_failed_output_path(output_path)
    )

    # Slice-7 deterministic pre-flight gate: every check below runs in
    # pure code over the renderer/ledger inputs, never invokes an LLM,
    # and hard-fails the script before any planner call. Runs on the
    # --dry-run path too, so dry-run doubles as an inputs-only smoke
    # test.
    preflight_errors = run_generator_preflight(source_path)
    if preflight_errors:
        print()
        print(
            "Pre-flight validation failed; the generator will not call "
            "the planner."
        )
        print(format_errors(preflight_errors))
        return 1

    if args.dry_run:
        print()
        print(
            render_dry_run_report(
                HANDOVER_INPUTS,
                source_path=source_path,
                output_path=output_path,
                failed_output_path=failed_output_path,
            )
        )
        return 0

    non_citable = validate_required_citable_docs(source_path)
    if non_citable:
        print("Validation failed before planner call: required source docs are not citable.")
        print("Register these docs in docs/DOCS_MANIFEST.yaml with citable=true:")
        for rel_path in non_citable:
            print(f"  - {rel_path}")
        return 1

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
            "active phase scope brief."
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
