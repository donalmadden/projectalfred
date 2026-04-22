"""Generate the canonical handover that plans Phase 1 of the blank-project kickoff demo.

Follows the same validated canonical-generation path as the prior Phase 7
generator, but the planner is now grounded on two authoritative scope
sources — `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` and
`docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md` —
and seeded with the previous canonical handover
(`docs/canonical/ALFRED_HANDOVER_7.md`) as continuity context only. The
target output is `docs/canonical/ALFRED_HANDOVER_8.md`, written only after
the structural and grounding validators pass.

Scope of the generated handover: Phase 1 of the demo plan only — lock the
canonical kickoff handover shape (charter prompt, demo-project docs/
layout, target handover outline, kickoff task, board-write checkpoint).
Phases 2–5 of the demo plan (orchestrator harness, proposal persistence,
GitHub write path, rehearsal) are explicitly out of scope.
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
from alfred.tools.rag import index_corpus

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "default.yaml"

_DOC_REF_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.(?:md|pdf))`")
_LOCAL_PATH_RE = re.compile(
    r"`(?P<path>(?:docs|src|scripts|tests|configs|evals|\.github)/[A-Za-z0-9_./\-]+)`"
)

EXPECTED_HANDOVER_ID = "ALFRED_HANDOVER_8"
EXPECTED_PREVIOUS_HANDOVER = "ALFRED_HANDOVER_7"
DISPLAY_TITLE = "Demo Plan Phase 1 — Lock Kickoff Handover Shape"
SOURCE_FILENAME = f"{EXPECTED_PREVIOUS_HANDOVER}.md"
FAILED_FILENAME = f"{EXPECTED_HANDOVER_ID}_FAILED_CANDIDATE.md"
DEFAULT_CONTEXT_CHARS = 6000

DEMO_PLAN_PATH = REPO_ROOT / "docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md"
DEMO_FROZEN_SCENARIO_PATH = (
    REPO_ROOT / "docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md"
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
    "Generate the canonical handover that plans Phase 1 of the blank-project "
    "kickoff demo plan. Phase 0 is already frozen and ratified — the demo "
    "scenario (Customer Onboarding Portal), demo-project shape, blank "
    "GitHub Project board target, 6–8 visible draft items success criterion, "
    "and the narrated arc are locked. This handover must execute Phase 1 "
    "only: (a) freeze the exact kickoff charter content the demo will use as "
    "Alfred input, (b) freeze the target demo-project docs/ layout, "
    "(c) freeze the target outline of the kickoff handover Alfred will "
    "generate for the demo, (d) define the specific kickoff task whose "
    "execution seeds the blank GitHub Project board, and (e) define the "
    "checkpoint that gates the board-write step. Phase 2–5 deliverables "
    "(orchestrator harness, proposal persistence, GitHub write path, "
    "rehearsal runbook) are explicitly out of scope for this handover."
)

DEMO_PLAN_GROUNDING = (
    "Authoritative scope sources for this handover (full text included "
    "below in the planner context):\n"
    "- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — multi-phase "
    "build plan; this handover plans Phase 1 only.\n"
    "- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md` "
    "— Phase 0 freeze record (ratified). All five Phase 0 decisions are "
    "locked and may not be revisited.\n"
    "Treat the contents of those two docs as the source of truth for scope. "
    "Do not invent deliverables outside Phase 1. Do not revisit Phase 0 "
    "freeze decisions. The previously-prominent Phase 8 portfolio-polish "
    "scope is superseded by the demo plan and must not be carried forward."
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
            "(default: docs/canonical/ALFRED_HANDOVER_7.md)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH.relative_to(REPO_ROOT),
        help=(
            "Canonical output path to write on success "
            "(default: docs/canonical/ALFRED_HANDOVER_8.md)"
        ),
    )
    parser.add_argument(
        "--failed-output",
        type=Path,
        default=FAILED_OUTPUT_PATH.relative_to(REPO_ROOT),
        help=(
            "Where to write a failed candidate when validation blocks promotion "
            "(default: docs/archive/ALFRED_HANDOVER_8_FAILED_CANDIDATE.md)"
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


def load_demo_plan_context() -> str:
    """Return the full text of the demo plan + Phase 0 freeze as a labeled scope block.

    This is the planner's authoritative scope input. Unlike historical
    continuity context, it is not truncated — the planner needs the full
    Phase 1 deliverables and the full Phase 0 freeze decisions to produce
    a faithful canonical handover.
    """
    plan_text = (
        DEMO_PLAN_PATH.read_text(encoding="utf-8") if DEMO_PLAN_PATH.is_file() else ""
    )
    frozen_text = (
        DEMO_FROZEN_SCENARIO_PATH.read_text(encoding="utf-8")
        if DEMO_FROZEN_SCENARIO_PATH.is_file()
        else ""
    )
    if not plan_text and not frozen_text:
        return ""

    blocks: list[str] = [
        "===== AUTHORITATIVE PHASE 1 SCOPE — DO NOT TREAT AS HISTORICAL CONTEXT =====",
        "The two documents below define the source of truth for what this "
        "handover must lock down. Read them as the scope brief, not as "
        "historical narrative. Phase 0 is already ratified; this handover "
        "executes Phase 1 only.",
    ]
    if frozen_text:
        blocks.extend(
            [
                "",
                "----- BEGIN docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md -----",
                frozen_text.rstrip(),
                "----- END FROZEN SCENARIO -----",
            ]
        )
    if plan_text:
        blocks.extend(
            [
                "",
                "----- BEGIN docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md -----",
                plan_text.rstrip(),
                "----- END DEMO PLAN -----",
            ]
        )
    blocks.append("===== END AUTHORITATIVE PHASE 1 SCOPE =====")
    return "\n".join(blocks)


def load_historical_context(
    source_path: Path,
    *,
    mode: str = "summary",
    max_chars: int = DEFAULT_CONTEXT_CHARS,
) -> Optional[str]:
    """Load a bounded historical context block for the planner."""
    if not source_path.is_file():
        return None
    if mode == "none":
        return None
    text = source_path.read_text(encoding="utf-8")
    if mode == "full":
        return (
            "Update the next canonical handover so it matches the live repository "
            "today. Preserve the new handover identity (`ALFRED_HANDOVER_8`) and "
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
    if demo_plan_context:
        print(
            f"  Demo plan context: {len(demo_plan_context)} chars from "
            "demo plan + Phase 0 frozen scenario (authoritative scope)"
        )
    else:
        print(
            "WARNING: demo plan and Phase 0 frozen scenario both missing; "
            "planner will lack authoritative Phase 1 scope."
        )

    planner_out = None
    last_error: Optional[Exception] = None
    for mode in build_context_attempt_order(args.historical_context_mode):
        historical_context = load_historical_context(source_path, mode=mode)
        context_parts = [
            block for block in (demo_plan_context, historical_context) if block
        ]
        current_handover_context = "\n\n".join(context_parts) if context_parts else None
        if current_handover_context:
            print(
                f"  Planner context mode `{mode}` with "
                f"{len(current_handover_context)} chars total "
                f"({len(demo_plan_context)} scope + "
                f"{len(historical_context) if historical_context else 0} historical)"
            )
        else:
            print(f"  Planner context mode `{mode}` with no context at all")
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
