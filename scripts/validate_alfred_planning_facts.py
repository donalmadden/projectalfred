#!/usr/bin/env python3
"""
Alfred factual-validation gate for planning drafts.

Complements ``scripts/validate_alfred_handover.py`` (which is a structural
gate). This script checks that present-tense claims in a draft match the
repository as it actually exists today. Structurally valid drafts that
invent modules, agents, API surfaces, or tooling claims must fail here.

Scope — only the current-state sections are inspected:
  - ``## CONTEXT — READ THIS FIRST``
  - ``## WHAT EXISTS TODAY``

Future-tense sections (``## WHAT THIS PHASE PRODUCES``, ``## TASK OVERVIEW``,
individual task bodies, ``## WHAT NOT TO DO``, ``## POST-MORTEM``) are
intentionally ignored so planners can propose new files/modules without the
validator flagging them as hallucinations.

Usage::

    python scripts/validate_alfred_planning_facts.py PATH [--expected-id ID]
        [--expected-previous ID] [--expected-date YYYY-MM-DD]

Exit codes: 0 = valid, 1 = factual failure, 2 = usage/IO error.
"""
from __future__ import annotations

import argparse
import enum
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alfred.tools.repo_facts import (  # noqa: E402
    read_agent_modules,
    read_api_surface,
    read_packaging_state,
    read_partial_state_facts,
    read_reference_documents,
    read_top_level_packages,
)

# ---------------------------------------------------------------------------
# Typed findings
# ---------------------------------------------------------------------------


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


@dataclass
class Finding:
    category: ClaimCategory
    severity: Literal["error", "warning"]
    message: str
    evidence: str
    section: str

    def format(self) -> str:
        return (
            f"[{self.severity.upper()}][{self.category.value}] "
            f"{self.evidence} — {self.message}"
        )


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

# Section scoping: all current-state claims must appear under one of these H2s.
# Matching is case-insensitive, dash-normalised, prefix-tolerant (same rules as
# the structural validator).
_CURRENT_STATE_H2S = (
    "CONTEXT — READ THIS FIRST",
    "WHAT EXISTS TODAY",
)

_DASH_RE = re.compile(r"[\u2010-\u2015\-]+")
_WS_RE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    text = text.strip().lower()
    text = _DASH_RE.sub("\u2014", text)
    text = _WS_RE.sub(" ", text)
    return text


def _heading_matches(actual: str, required: str) -> bool:
    a = _normalise(actual)
    r = _normalise(required)
    if a == r:
        return True
    if not a.startswith(r):
        return False
    return a[len(r)] in (" ", "\u2014", ":")


def extract_sections(markdown: str) -> dict[str, str]:
    """Return a dict of ``{normalised_h2: body_text}``.

    Body text excludes the H2 heading line itself but includes all sub-headings
    and prose under it until the next H2. Fenced code blocks are preserved.
    """
    sections: dict[str, str] = {}
    current_key: Optional[str] = None
    current_lines: list[str] = []
    in_fence = False

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current_key is not None:
                current_lines.append(line)
            continue
        if not in_fence:
            m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if m and len(m.group(1)) == 2:
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines)
                current_key = _normalise(m.group(2))
                current_lines = []
                continue
        if current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines)
    return sections


def current_state_text(sections: dict[str, str]) -> str:
    """Concatenate the body text of all current-state H2 sections."""
    parts: list[str] = []
    for key, body in sections.items():
        for required in _CURRENT_STATE_H2S:
            if _heading_matches(key, required):
                parts.append(body)
                break
    return "\n".join(parts)


def context_block(sections: dict[str, str]) -> str:
    for key, body in sections.items():
        if _heading_matches(key, "CONTEXT — READ THIS FIRST"):
            return body
    return ""


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

# Backtick-quoted local path in markdown body. Matches only paths rooted in
# known top-level directories so random prose like `0.1.0` is not flagged.
_PATH_RE = re.compile(
    r"`(?P<path>(?:docs|src|scripts|tests|configs|evals|\.github)/[A-Za-z0-9_./\-]+)`"
)


# Sentence boundary separators used for negation scoping.
# Matches double-newlines, period-space after a word char, and fence markers.
_SENTENCE_SEP_RE = re.compile(r"\n\n|(?<=\w)\. |```")

# Existence-denial phrases that can appear after the claim ("X does not exist").
_EXISTENCE_DENIAL_POST = (
    "does not exist",
    "is not present",
    "is missing",
    "not yet exist",
    "no longer exists",
    "has been removed",
    "has been deleted",
)

# Imperative negation words — negate an ACTION on the path, not its existence.
# "must not break `src/foo`" should NOT suppress a finding about `src/foo`.
_IMPERATIVE_NEG_RE = re.compile(
    r"\b(must not|should not|do not|don't|cannot|can't)\b",
    re.IGNORECASE,
)


def _find_sentence(text: str, pos: int) -> tuple[str, int]:
    """Return (sentence_text, sentence_start) for the sentence containing pos."""
    sent_start = 0
    for m in _SENTENCE_SEP_RE.finditer(text):
        if m.end() <= pos:
            sent_start = m.end()
        else:
            break
    after = _SENTENCE_SEP_RE.search(text, pos)
    sent_end = after.start() if after else len(text)
    return text[sent_start:sent_end], sent_start


def _claim_is_negated(text: str, match_span: tuple[int, int]) -> bool:
    """True if the claim is explicitly denied to exist within its sentence.

    Scopes negation to the containing sentence so that imperatives like
    "must not break `src/foo`" do not suppress findings about `src/foo`.
    Only post-claim existence-denial phrases ("does not exist", "is missing")
    and unambiguous pre-claim markers ("no `path`", "removed", "deleted")
    count as negation.
    """
    start, end = match_span
    sentence, sent_start = _find_sentence(text, start)
    sentence_lower = sentence.lower()

    claim_start_in_sent = start - sent_start
    claim_end_in_sent = end - sent_start

    post_claim = sentence_lower[claim_end_in_sent:]
    pre_claim = sentence_lower[:claim_start_in_sent]

    # Post-claim existence denial: "`src/foo` does not exist"
    if any(denial in post_claim for denial in _EXISTENCE_DENIAL_POST):
        return True

    # Sentence contains only an imperative negation — no existence denial implied
    if _IMPERATIVE_NEG_RE.search(sentence):
        return False

    # Non-imperative pre-claim markers: "no `path`", "no such path", etc.
    if re.search(r"\bno\s*$|\bno such\b|\bremoved\b|\bdeleted\b|\babsent\b", pre_claim):
        return True

    return False


def _check_path_existence(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for match in _PATH_RE.finditer(text):
        raw = match.group("path")
        candidate = raw.rstrip(".,:;")
        if candidate in seen:
            continue
        seen.add(candidate)
        normalised = candidate.rstrip("/")
        full = repo_root / normalised
        if full.exists():
            continue
        if _claim_is_negated(text, (match.start(), match.end())):
            continue
        findings.append(Finding(
            category=ClaimCategory.CURRENT_PATH,
            severity="error",
            message=f"{normalised!r} does not exist in the repo.",
            evidence=f"`{candidate}`",
            section="current_state",
        ))
    return findings


_DOCS_MD_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.md)`")


def _check_reference_documents(text: str, repo_root: Path) -> list[Finding]:
    """Flag backtick-quoted docs/*.md paths not in the canonical docs inventory."""
    findings: list[Finding] = []
    inventory = set(read_reference_documents(repo_root))
    seen: set[str] = set()
    for match in _DOCS_MD_RE.finditer(text):
        path = match.group("path")
        if path in seen:
            continue
        seen.add(path)
        if path in inventory:
            continue
        if _claim_is_negated(text, (match.start(), match.end())):
            continue
        findings.append(Finding(
            category=ClaimCategory.REFERENCE_DOC,
            severity="error",
            message="not in the canonical docs inventory.",
            evidence=f"`{path}`",
            section="current_state",
        ))
    return findings


def _check_api_topology(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    api = read_api_surface(repo_root)
    real_path = api["module_path"]
    real_endpoints = api["endpoints"]
    assert isinstance(real_endpoints, list)

    # Reject directory-style claims about the API module.
    bad_api_dir = re.search(r"`src/alfred/api/(?:[A-Za-z0-9_.]+)?`", text)
    if bad_api_dir:
        findings.append(Finding(
            category=ClaimCategory.CURRENT_TOPOLOGY,
            severity="error",
            message=(
                f"the real FastAPI app lives in `{real_path}` (single file)."
            ),
            evidence=bad_api_dir.group(0),
            section="current_state",
        ))

    # Reject explicit `src/alfred/api/main.py` references in current-state text.
    if "src/alfred/api/main.py" in text:
        findings.append(Finding(
            category=ClaimCategory.CURRENT_TOPOLOGY,
            severity="error",
            message=f"the FastAPI entrypoint is `{real_path}`.",
            evidence="`src/alfred/api/main.py`",
            section="current_state",
        ))

    # Endpoint count claim: phrases like "five endpoints", "5 endpoints".
    _NUM_WORDS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    count_re = re.compile(
        r"(?P<count>\b\d+\b|\bone\b|\btwo\b|\bthree\b|\bfour\b|\bfive\b|"
        r"\bsix\b|\bseven\b|\beight\b|\bnine\b|\bten\b)\s+endpoints?",
        re.IGNORECASE,
    )
    for m in count_re.finditer(text):
        raw = m.group("count").lower()
        claimed = int(raw) if raw.isdigit() else _NUM_WORDS[raw]
        if claimed != len(real_endpoints):
            findings.append(Finding(
                category=ClaimCategory.CURRENT_TOPOLOGY,
                severity="error",
                message=(
                    f"does not match the real FastAPI surface "
                    f"({len(real_endpoints)} endpoints in {real_path})."
                ),
                evidence=f"{claimed} endpoints",
                section="current_state",
            ))
            break  # one mismatch is enough; don't double-count

    return findings


# Known-bad agent names: modules that do not exist under src/alfred/agents/.
# Only flag these when they appear as code-style identifiers (backticked,
# module path, or .py reference) — bare prose mentions of "executor" and
# "reviewer" are legitimate methodology role words.
_KNOWN_BAD_AGENT_NAMES = ("executor", "reviewer", "summariser", "summarizer")


def _check_agent_roster(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    real_agents = read_agent_modules(repo_root)
    for bad in _KNOWN_BAD_AGENT_NAMES:
        patterns = (
            rf"`{bad}`",
            rf"`{bad}\.py`",
            rf"`src/alfred/agents/{bad}(?:\.py)?`?",
            rf"\b{bad}\.py\b",
            rf"\balfred\.agents\.{bad}\b",
        )
        # Special-case the "planner, executor, reviewer, summariser" enumeration
        # pattern — a comma-separated list claiming this is the real agent
        # roster. Catches the common hallucination without also catching bare
        # role-word usage.
        roster_re = re.compile(
            r"planner[\s,/|]+executor[\s,/|]+reviewer",
            re.IGNORECASE,
        )
        if bad == "executor" and roster_re.search(text):
            findings.append(Finding(
                category=ClaimCategory.CURRENT_TOPOLOGY,
                severity="error",
                message=(
                    f"the real roster under src/alfred/agents/ is: "
                    f"{', '.join(real_agents)}."
                ),
                evidence="planner, executor, reviewer",
                section="current_state",
            ))
            continue
        found = False
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                found = True
                break
        if found:
            findings.append(Finding(
                category=ClaimCategory.CURRENT_TOPOLOGY,
                severity="error",
                message=(
                    f"the real agent roster under src/alfred/agents/ is: "
                    f"{', '.join(real_agents)}."
                ),
                evidence=f"`{bad}`",
                section="current_state",
            ))
    return findings


def _check_top_level_packages(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    real_top = set(read_top_level_packages(repo_root))
    # Directory-style references to subpackages of src/alfred/.
    sub_re = re.compile(r"`src/alfred/(?P<name>[a-z_][a-z0-9_]*)/`", re.IGNORECASE)
    seen: set[str] = set()
    for m in sub_re.finditer(text):
        name = m.group("name")
        if name in seen:
            continue
        seen.add(name)
        if name not in real_top:
            if _claim_is_negated(text, (m.start(), m.end())):
                continue
            findings.append(Finding(
                category=ClaimCategory.CURRENT_PATH,
                severity="error",
                message=(
                    f"not present. Real top-level names: "
                    f"{', '.join(sorted(real_top))}."
                ),
                evidence=f"`src/alfred/{name}/`",
                section="current_state",
            ))
    return findings


def _check_type_checker(text: str) -> list[Finding]:
    findings: list[Finding] = []
    # "mypy" mentioned as part of current-state tooling is wrong.
    # Allow mention in contexts that explicitly negate it ("mypy is not used").
    for m in re.finditer(r"\bmypy\b", text, re.IGNORECASE):
        window_start = max(0, m.start() - 40)
        window_end = min(len(text), m.end() + 40)
        window = text[window_start:window_end].lower()
        if "not " in window or "never " in window or "is not" in window:
            continue
        findings.append(Finding(
            category=ClaimCategory.CURRENT_TOOLING,
            severity="error",
            message="the repo uses `pyright`. Phase 6 explicitly forbids adding `mypy`.",
            evidence="`mypy`",
            section="current_state",
        ))
        break
    return findings


def _check_pyproject_state(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    state = read_packaging_state(repo_root)
    if not state["pyproject_exists"]:
        return findings
    # Phrases that claim pyproject.toml is missing or must be created.
    bad_phrases = (
        "pyproject.toml does not exist",
        "pyproject.toml is missing",
        "pyproject.toml needs to be created",
        "no pyproject.toml",
        "create pyproject.toml",
    )
    lowered = text.lower()
    for phrase in bad_phrases:
        if phrase in lowered:
            findings.append(Finding(
                category=ClaimCategory.PYPROJECT_STATE,
                severity="error",
                message=(
                    f"`pyproject.toml` is present with "
                    f"[project]={state['has_project_table']} and "
                    f"[project.scripts]={state['has_project_scripts']}."
                ),
                evidence=phrase,
                section="current_state",
            ))
            break
    return findings


def _check_partial_state(text: str, repo_root: Path) -> list[Finding]:
    """Flag claims that misrepresent declared-but-unimplemented state.

    When the CLI entry is declared in pyproject.toml but src/alfred/cli.py is
    absent, a draft must not claim either "the CLI is implemented" or "there is
    no CLI at all". The correct vocabulary is "declared but unimplemented".
    """
    findings: list[Finding] = []
    pkg = read_packaging_state(repo_root)
    partial = read_partial_state_facts(repo_root)
    lower = text.lower()

    if "cli_module" in partial and not pkg.get("cli_module_exists"):
        # CLI declared but absent — flag over-confident claims in either direction
        implemented_phrases = (
            "cli is implemented",
            "cli exists",
            "cli is present",
            "cli is available",
            "alfred cli is implemented",
            "the cli is implemented",
        )
        absent_phrases = (
            "no cli",
            "cli does not exist",
            "cli is missing",
            "cli is absent",
            "no alfred cli",
            "there is no cli",
        )
        for phrase in implemented_phrases:
            if phrase in lower:
                findings.append(Finding(
                    category=ClaimCategory.PARTIAL_STATE,
                    severity="error",
                    message=(
                        "CLI script entry is declared in pyproject.toml "
                        "but src/alfred/cli.py does not yet exist. "
                        "Use 'declared but unimplemented'."
                    ),
                    evidence=phrase,
                    section="current_state",
                ))
                break
        for phrase in absent_phrases:
            if phrase in lower:
                findings.append(Finding(
                    category=ClaimCategory.PARTIAL_STATE,
                    severity="error",
                    message=(
                        "CLI script entry is declared in pyproject.toml. "
                        "Use 'declared but unimplemented', not an absence claim."
                    ),
                    evidence=phrase,
                    section="current_state",
                ))
                break

    return findings


# ---------------------------------------------------------------------------
# Metadata consistency
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"\*\*id:\*\*\s*(?P<id>[A-Za-z0-9_\-]+)")
_DATE_RE = re.compile(r"\*\*date:\*\*\s*(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})")
_PREV_RE = re.compile(r"\*\*previous_handover:\*\*\s*(?P<prev>[A-Za-z0-9_\-]+)")


def _extract_metadata_id(context: str) -> Optional[str]:
    m = _ID_RE.search(context)
    return m.group("id") if m else None


def _extract_metadata_date(context: str) -> Optional[str]:
    m = _DATE_RE.search(context)
    return m.group("date") if m else None


def _extract_metadata_previous(context: str) -> Optional[str]:
    m = _PREV_RE.search(context)
    return m.group("prev") if m else None


def _filename_id_stem(source_path: Path) -> str:
    """``ALFRED_HANDOVER_6_DRAFT.md`` → ``ALFRED_HANDOVER_6``."""
    stem = source_path.stem  # ALFRED_HANDOVER_6_DRAFT
    return re.sub(r"_DRAFT$", "", stem, flags=re.IGNORECASE)


def _check_metadata(
    context: str,
    source_path: Optional[Path],
    expected_id: Optional[str],
    expected_previous: Optional[str],
    expected_date: Optional[str],
) -> list[Finding]:
    findings: list[Finding] = []
    declared_id = _extract_metadata_id(context)
    declared_date = _extract_metadata_date(context)
    declared_prev = _extract_metadata_previous(context)

    if source_path is not None and declared_id:
        filename_id = _filename_id_stem(source_path)
        # Permit the declared id to match either the filename stem or the
        # filename stem plus `_DRAFT` (both are legitimate for a draft).
        legit = {filename_id, filename_id + "_DRAFT"}
        if declared_id not in legit:
            findings.append(Finding(
                category=ClaimCategory.METADATA,
                severity="error",
                message=(
                    f"does not match the filename `{source_path.name}` "
                    f"(expected `{filename_id}` or `{filename_id}_DRAFT`)."
                ),
                evidence=f"id: {declared_id}",
                section="metadata",
            ))

    if expected_id and declared_id and declared_id not in {expected_id, expected_id + "_DRAFT"}:
        findings.append(Finding(
            category=ClaimCategory.METADATA,
            severity="error",
            message=f"does not match expected id `{expected_id}` supplied to the validator.",
            evidence=f"id: {declared_id}",
            section="metadata",
        ))

    if expected_previous and declared_prev and declared_prev != expected_previous:
        findings.append(Finding(
            category=ClaimCategory.METADATA,
            severity="error",
            message=f"does not match expected `{expected_previous}` supplied to the validator.",
            evidence=f"previous_handover: {declared_prev}",
            section="metadata",
        ))

    if expected_date and declared_date and declared_date != expected_date:
        findings.append(Finding(
            category=ClaimCategory.METADATA,
            severity="error",
            message=f"does not match expected `{expected_date}` supplied to the validator.",
            evidence=f"date: {declared_date}",
            section="metadata",
        ))

    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_current_state_facts(
    markdown: str,
    source_path: Optional[Path] = None,
    *,
    expected_id: Optional[str] = None,
    expected_previous: Optional[str] = None,
    expected_date: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> list[Finding]:
    """Return typed findings for current-state factual claims. Empty list = grounded."""
    root = repo_root or Path(__file__).resolve().parents[1]
    sections = extract_sections(markdown)
    current = current_state_text(sections)
    ctx = context_block(sections)

    findings: list[Finding] = []
    findings.extend(_check_metadata(ctx, source_path, expected_id, expected_previous, expected_date))
    findings.extend(_check_path_existence(current, root))
    findings.extend(_check_reference_documents(current, root))
    findings.extend(_check_api_topology(current, root))
    findings.extend(_check_agent_roster(current, root))
    findings.extend(_check_top_level_packages(current, root))
    findings.extend(_check_type_checker(current))
    findings.extend(_check_pyproject_state(current, root))
    findings.extend(_check_partial_state(current, root))
    return findings


def validate(
    markdown: str,
    source_path: Optional[Path] = None,
    *,
    expected_id: Optional[str] = None,
    expected_previous: Optional[str] = None,
    expected_date: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> list[str]:
    """Return a list of factual errors. Empty list means the draft is grounded.

    Backwards-compatible shim over ``validate_current_state_facts``.
    """
    findings = validate_current_state_facts(
        markdown,
        source_path,
        expected_id=expected_id,
        expected_previous=expected_previous,
        expected_date=expected_date,
        repo_root=repo_root,
    )
    return [f.format() for f in findings]


# ---------------------------------------------------------------------------
# Future-task realism checks
# ---------------------------------------------------------------------------

_FUTURE_H2S = (
    "TASK OVERVIEW",
    "WHAT THIS PHASE PRODUCES",
)


def _future_task_text(sections: dict[str, str]) -> str:
    """Concatenate body text of future-tense sections only."""
    parts: list[str] = []
    for key, body in sections.items():
        for h2 in _FUTURE_H2S:
            if _heading_matches(key, h2):
                parts.append(body)
                break
    return "\n".join(parts)


# Backtick-quoted YAML/YML paths — potential workflow file references.
_YAML_PATH_RE = re.compile(r"`(?P<path>[A-Za-z0-9_./@\-]+\.ya?ml)`")

# Filenames that strongly suggest a GitHub Actions workflow.
_CI_FILENAMES = frozenset({
    "ci.yml", "cd.yml", "release.yml", "deploy.yml", "build.yml",
    "test.yml", "lint.yml", "check.yml", "ci.yaml", "cd.yaml",
    "release.yaml", "deploy.yaml",
})

# Directory patterns that indicate CI intent but are not `.github/workflows/`.
_CI_DIR_RE = re.compile(r"^(?:ci|actions|workflow|\.github(?!/workflows))/", re.IGNORECASE)


def _check_workflow_placement(text: str) -> list[Finding]:
    """Flag workflow-like YAML paths not rooted at .github/workflows/."""
    findings: list[Finding] = []
    for match in _YAML_PATH_RE.finditer(text):
        path = match.group("path")
        if path.startswith(".github/workflows/"):
            continue
        filename = Path(path).name.lower()
        if filename in _CI_FILENAMES or _CI_DIR_RE.match(path):
            findings.append(Finding(
                category=ClaimCategory.PLACEMENT,
                severity="error",
                message="workflow files must live under `.github/workflows/`.",
                evidence=f"`{path}`",
                section="future_tasks",
            ))
    return findings


def _check_schema_placement(text: str) -> list[Finding]:
    """Flag src/alfred/schemas.py (single file) — schemas must be a package."""
    findings: list[Finding] = []
    if re.search(r"`src/alfred/schemas\.py`", text):
        findings.append(Finding(
            category=ClaimCategory.PLACEMENT,
            severity="error",
            message=(
                "schemas should be a package (`src/alfred/schemas/`), "
                "not a single file `src/alfred/schemas.py`."
            ),
            evidence="`src/alfred/schemas.py`",
            section="future_tasks",
        ))
    return findings


def _check_future_hard_rules(text: str) -> list[Finding]:
    """Flag future-task content that violates CLAUDE.md hard rules."""
    findings: list[Finding] = []

    for m in re.finditer(r"\bmypy\b", text, re.IGNORECASE):
        window = text[max(0, m.start() - 40):m.end() + 40].lower()
        if "not " in window or "never " in window or "no mypy" in window:
            continue
        findings.append(Finding(
            category=ClaimCategory.HARD_RULE,
            severity="error",
            message="mypy is forbidden (repo uses pyright; CLAUDE.md hard rule).",
            evidence="`mypy`",
            section="future_tasks",
        ))
        break

    docker_re = re.compile(
        r"\b(?:Docker|Dockerfile|docker-compose|docker\s+compose)\b",
        re.IGNORECASE,
    )
    for m in docker_re.finditer(text):
        window = text[max(0, m.start() - 40):m.end() + 40].lower()
        if "not " in window or "never " in window or "no docker" in window:
            continue
        findings.append(Finding(
            category=ClaimCategory.HARD_RULE,
            severity="error",
            message=(
                "Docker is forbidden until Phase 7 "
                "(CLAUDE.md: 'No Docker yet — local venv first, containerise in Phase 7')."
            ),
            evidence=m.group(0),
            section="future_tasks",
        ))
        break

    return findings


_TASK_HEADING_RE = re.compile(r"^###\s+Task\s+\d+.*$", re.MULTILINE)


def _check_task_granularity(text: str) -> list[Finding]:
    """Warn when a numbered task has no quoted file path or no test/validation reference."""
    findings: list[Finding] = []
    task_starts = [(m.start(), m.group(0).strip()) for m in _TASK_HEADING_RE.finditer(text)]

    for i, (start, header) in enumerate(task_starts):
        end = task_starts[i + 1][0] if i + 1 < len(task_starts) else len(text)
        body = text[start:end]

        has_path = bool(re.search(r"`[A-Za-z][^`]*\.[a-z]{2,4}`", body))
        has_test_ref = bool(re.search(
            r"\btest\b|\bvalidat|\bpytest\b|\bcheck\b|\bassert\b",
            body,
            re.IGNORECASE,
        ))

        if not has_path or not has_test_ref:
            findings.append(Finding(
                category=ClaimCategory.TASK_GRANULARITY,
                severity="warning",
                message="task lacks a quoted file path or a test/validation reference.",
                evidence=header,
                section="future_tasks",
            ))

    return findings


def validate_future_task_realism(
    markdown: str,
    repo_root: Optional[Path] = None,
) -> list[Finding]:
    """Return realism findings for future-task sections.

    Only inspects ``## TASK OVERVIEW`` and ``## WHAT THIS PHASE PRODUCES``.
    Does not touch current-state sections — use ``validate_current_state_facts``
    for those.
    """
    sections = extract_sections(markdown)
    future_text = _future_task_text(sections)

    findings: list[Finding] = []
    findings.extend(_check_workflow_placement(future_text))
    findings.extend(_check_schema_placement(future_text))
    findings.extend(_check_future_hard_rules(future_text))
    findings.extend(_check_task_granularity(future_text))
    return findings


def _print_findings(label: str, findings: list[Finding]) -> None:
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    if errors or warnings:
        print(f"\n{label}:", file=sys.stderr)
    if errors:
        print("  ERRORS:", file=sys.stderr)
        for f in errors:
            print(f"    - {f.format()}", file=sys.stderr)
    if warnings:
        print("  WARNINGS:", file=sys.stderr)
        for f in warnings:
            print(f"    - {f.format()}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an Alfred planning draft against repository facts.",
    )
    parser.add_argument("path", type=Path, help="Path to the planning draft")
    parser.add_argument("--expected-id", default=None)
    parser.add_argument("--expected-previous", default=None)
    parser.add_argument("--expected-date", default=None)
    parser.add_argument(
        "--mode",
        choices=["facts", "realism", "both"],
        default="both",
        help="Which validator to run (default: both)",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"error: not a file: {args.path}", file=sys.stderr)
        return 2
    try:
        markdown = args.path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: could not read {args.path}: {exc}", file=sys.stderr)
        return 2

    facts_findings: list[Finding] = []
    realism_findings: list[Finding] = []

    if args.mode in ("facts", "both"):
        facts_findings = validate_current_state_facts(
            markdown,
            source_path=args.path,
            expected_id=args.expected_id,
            expected_previous=args.expected_previous,
            expected_date=args.expected_date,
        )

    if args.mode in ("realism", "both"):
        realism_findings = validate_future_task_realism(markdown)

    facts_errors = [f for f in facts_findings if f.severity == "error"]
    realism_errors = [f for f in realism_findings if f.severity == "error"]

    if facts_findings:
        _print_findings("CURRENT-STATE FACTUAL ISSUES", facts_findings)
    if realism_findings:
        _print_findings("FUTURE-TASK REALISM ISSUES", realism_findings)

    if facts_errors:
        print(f"\nFAIL (factual errors) {args.path}", file=sys.stderr)
        return 1
    if realism_errors:
        print(f"\nFAIL (realism errors) {args.path}", file=sys.stderr)
        return 2
    print(f"OK   {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
