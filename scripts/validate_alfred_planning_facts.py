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
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alfred.schemas.claim_types import ClaimCategory  # noqa: E402
from alfred.schemas.repo_conventions import PartialStateFact, PartialStateType  # noqa: E402
from alfred.schemas.validator_findings import (  # noqa: E402
    FormattedFinding,
    HardRuleFinding,
    MetadataFinding,
    PartialStateFinding,
    PathFinding,
    PlacementFinding,
    PyprojectFinding,
    ReferenceDocFinding,
    StructuralFinding,
    TaskGranularityFinding,
    ToolingFinding,
    TopologyFinding,
)
from alfred.tools.docs_policy import read_docs_inventory  # noqa: E402
from alfred.tools.reference_doc_validator import (  # noqa: E402
    link_is_inventory_exempt,
    path_has_future_tag,
    validate_reference_doc_cross_links,
    validate_reference_doc_freshness,
    validate_reference_doc_structure,
)
from alfred.tools.repo_facts import (  # noqa: E402
    read_agent_modules,
    read_api_surface,
    read_packaging_state,
    read_partial_state_facts,
    read_reference_documents,
    read_supported_type_checkers,
    read_type_checkers,
    read_top_level_packages,
)

# ---------------------------------------------------------------------------
# Typed findings
# ---------------------------------------------------------------------------

Finding = FormattedFinding


def _path_finding(
    *,
    category: ClaimCategory,
    message: str,
    evidence: str,
    section: str,
    path: str,
    expected_state: str,
) -> Finding:
    return Finding(
        category=category,
        severity="error",
        human_message=message,
        evidence=evidence,
        section=section,
        finding_object=PathFinding(path=path, expected_state=expected_state),
    )


def _topology_finding(
    *,
    evidence: str,
    message: str,
    canonical_value: str,
) -> Finding:
    return Finding(
        category=ClaimCategory.CURRENT_TOPOLOGY,
        severity="error",
        human_message=message,
        evidence=evidence,
        section="current_state",
        finding_object=TopologyFinding(
            claimed_value=evidence,
            canonical_value=canonical_value,
        ),
    )


def _metadata_finding(
    *,
    field_name: str,
    actual_value: str,
    expected_value: str,
    message: str,
) -> Finding:
    return Finding(
        category=ClaimCategory.METADATA,
        severity="error",
        human_message=message,
        evidence=f"{field_name}: {actual_value}",
        section="metadata",
        finding_object=MetadataFinding(
            field_name=field_name,
            actual_value=actual_value,
            expected_value=expected_value,
        ),
    )


def _partial_state_finding(
    *,
    fact: PartialStateFact,
    incorrect_phrasing: str,
    message: str,
) -> Finding:
    return Finding(
        category=ClaimCategory.PARTIAL_STATE,
        severity="error",
        human_message=message,
        evidence=incorrect_phrasing,
        section="current_state",
        finding_object=PartialStateFinding(
            state_type=fact.state_type,
            subject=fact.label,
            incorrect_phrasing=incorrect_phrasing,
            correct_vocabulary=fact.expected_vocabulary,
            declared_location=fact.declared_location,
            implementation_location=fact.implementation_location,
        ),
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

_MARKDOWN_DECORATION_RE = re.compile(r"[*_`]+")
_TYPE_CHECKER_ACTION_RE = re.compile(
    r"\b(?:add|adopt|configure|enable|integrate|introduce|install|run|use|wire)\b",
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


def _strip_markdown_decoration(text: str) -> str:
    return _MARKDOWN_DECORATION_RE.sub("", text)


def _configured_type_checker_label(repo_root: Path) -> str:
    configured = read_type_checkers(repo_root)
    return ", ".join(configured) if configured else "none configured"


def _sentence_negates_type_checker(sentence: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(sentence).lower()
    escaped = re.escape(tool)
    negation_patterns = (
        rf"\b(?:do not|don't|must not|should not|cannot|can't|never)\b"
        rf"[^.\n]{{0,40}}\b{escaped}\b",
        rf"\b(?:no|not)\s+{escaped}\b",
        rf"\b{escaped}\b[^.\n]{{0,40}}\b(?:not in use|is not used|"
        rf"must not be used|should not be used|forbidden|prohibited|"
        rf"banned|out of scope|hard violation)\b",
    )
    return any(re.search(pattern, plain) for pattern in negation_patterns)


def _line_invokes_type_checker(line: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(line).strip().lower()
    if not plain or plain.startswith("#"):
        return False
    escaped = re.escape(tool)
    patterns = (
        rf"^(?:\$ )?(?:python\s+-m\s+)?{escaped}\b",
        rf"^run:\s*(?:python\s+-m\s+)?{escaped}\b",
    )
    return any(re.search(pattern, plain) for pattern in patterns)


def _sentence_claims_type_checker(sentence: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(sentence).lower()
    if tool not in plain or _sentence_negates_type_checker(sentence, tool):
        return False
    escaped = re.escape(tool)
    claim_patterns = (
        rf"\btype checker\s*:\s*{escaped}\b",
        rf"\btype checking\b[^.\n]{{0,60}}\b{escaped}\b",
        rf"\bhandled by\b[^.\n]{{0,40}}\b{escaped}\b",
        rf"\b{escaped}\b[^.\n]{{0,80}}\b(?:passes?|runs?|exits?|checks?|job|step|pipeline|ci)\b",
    )
    return any(re.search(pattern, plain) for pattern in claim_patterns)


def _sentence_proposes_type_checker(sentence: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(sentence).lower()
    if tool not in plain or _sentence_negates_type_checker(sentence, tool):
        return False
    escaped = re.escape(tool)
    proposal_patterns = (
        rf"\b(?:add|adopt|configure|enable|integrate|introduce|install|run|use|wire)\b[^.\n]{{0,80}}\b{escaped}\b",
        rf"\btype checking\b[^.\n]{{0,60}}\b{escaped}\b",
        rf"\btype checker\b[^.\n]{{0,60}}\b{escaped}\b",
        rf"\b{escaped}\b[^.\n]{{0,80}}\b(?:passes?|runs?|exits?|checks?|job|step|pipeline|ci)\b",
    )
    return any(re.search(pattern, plain) for pattern in proposal_patterns)


def _unexpected_type_checkers(repo_root: Path) -> list[str]:
    configured = set(read_type_checkers(repo_root))
    return [tool for tool in read_supported_type_checkers() if tool not in configured]


def _current_state_claims_absent_type_checker(text: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(text)
    for match in re.finditer(rf"\b{re.escape(tool)}\b", plain, re.IGNORECASE):
        sentence, _ = _find_sentence(plain, match.start())
        if _sentence_claims_type_checker(sentence, tool):
            return True
    return False


def _future_text_proposes_absent_type_checker(text: str, tool: str) -> bool:
    plain = _strip_markdown_decoration(text)

    for line in plain.splitlines():
        stripped = line.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        if _line_invokes_type_checker(line, tool):
            return True
        if f"[tool.{tool}]" in stripped:
            if stripped.startswith(("- ", "* ", "|")) or _TYPE_CHECKER_ACTION_RE.search(stripped):
                if not _sentence_negates_type_checker(stripped, tool):
                    return True

    for match in re.finditer(rf"\b{re.escape(tool)}\b", plain, re.IGNORECASE):
        sentence, _ = _find_sentence(plain, match.start())
        if _sentence_proposes_type_checker(sentence, tool):
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
        if path_has_future_tag(text, match.start(), match.end()):
            continue
        normalised = candidate.rstrip("/")
        full = repo_root / normalised
        if full.exists():
            continue
        if _claim_is_negated(text, (match.start(), match.end())):
            continue
        findings.append(
            _path_finding(
                category=ClaimCategory.CURRENT_PATH,
                message=f"{normalised!r} does not exist in the repo.",
                evidence=f"`{candidate}`",
                section="current_state",
                path=normalised,
                expected_state="exists today",
            )
        )
    return findings


_DOCS_MD_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.md)`")


def _check_reference_documents(
    text: str,
    repo_root: Path,
    *,
    reference_date: str | None = None,
) -> list[Finding]:
    """Validate referenced docs for existence, structure, cross-links, and freshness."""
    findings: list[Finding] = []
    citable_inventory = set(read_reference_documents(repo_root))
    docs_inventory = set(read_docs_inventory(repo_root))
    seen: set[str] = set()
    for match in _DOCS_MD_RE.finditer(text):
        path = match.group("path")
        if path in seen:
            continue
        seen.add(path)
        if link_is_inventory_exempt(text, match.start(), match.end()):
            continue
        if path not in citable_inventory:
            if _claim_is_negated(text, (match.start(), match.end())):
                continue
            findings.append(
                Finding(
                    category=ClaimCategory.REFERENCE_DOC,
                    severity="error",
                    human_message="not citable under the docs lifecycle policy.",
                    evidence=f"`{path}`",
                    section="current_state",
                    finding_object=ReferenceDocFinding(
                        doc_path=path,
                        issue_type="not_found",
                        expected_state="present and citable under docs policy",
                        actual_state="missing or policy-excluded",
                    ),
                )
            )
            continue

        for issue in validate_reference_doc_structure(path, repo_root):
            findings.append(
                Finding(
                    category=ClaimCategory.REFERENCE_DOC,
                    severity="error",
                    human_message=issue.message,
                    evidence=f"`{path}`",
                    section="current_state",
                    finding_object=ReferenceDocFinding(
                        doc_path=path,
                        issue_type=issue.issue_type,
                        expected_state="structurally valid reference doc",
                        actual_state=issue.message,
                    ),
                )
            )
        for issue in validate_reference_doc_cross_links(path, docs_inventory, repo_root):
            findings.append(
                Finding(
                    category=ClaimCategory.REFERENCE_DOC,
                    severity="error",
                    human_message=issue.message,
                    evidence=f"`{path}`",
                    section="current_state",
                    finding_object=ReferenceDocFinding(
                        doc_path=path,
                        issue_type=issue.issue_type,
                        expected_state="all docs/*.md cross-links resolve",
                        actual_state=issue.message,
                    ),
                )
            )
        for issue in validate_reference_doc_freshness(
            path,
            reference_date=reference_date,
            repo_root=repo_root,
        ):
            findings.append(
                Finding(
                    category=ClaimCategory.REFERENCE_DOC,
                    severity="warning",
                    human_message=issue.message,
                    evidence=f"`{path}`",
                    section="current_state",
                    finding_object=ReferenceDocFinding(
                        doc_path=path,
                        issue_type=issue.issue_type,
                        expected_state="recent enough to be a grounding source",
                        actual_state=issue.message,
                    ),
                )
            )
    return findings


def _check_api_topology(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    api = read_api_surface(repo_root)
    real_path = api["module_path"]
    real_endpoints = api["endpoints"]
    assert isinstance(real_path, str)
    assert isinstance(real_endpoints, list)

    # Reject directory-style claims about the API module.
    bad_api_dir = re.search(r"`src/alfred/api/(?:[A-Za-z0-9_.]+)?`", text)
    if bad_api_dir:
        findings.append(
            _topology_finding(
                evidence=bad_api_dir.group(0),
                message=f"the real FastAPI app lives in `{real_path}` (single file).",
                canonical_value=real_path,
            )
        )

    # Reject explicit `src/alfred/api/main.py` references in current-state text.
    if "src/alfred/api/main.py" in text:
        findings.append(
            _topology_finding(
                evidence="`src/alfred/api/main.py`",
                message=f"the FastAPI entrypoint is `{real_path}`.",
                canonical_value=real_path,
            )
        )

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
            findings.append(
                _topology_finding(
                    evidence=f"{claimed} endpoints",
                    message=(
                        f"does not match the real FastAPI surface "
                        f"({len(real_endpoints)} endpoints in {real_path})."
                    ),
                    canonical_value=f"{len(real_endpoints)} endpoints in {real_path}",
                )
            )
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
            findings.append(
                _topology_finding(
                    evidence="planner, executor, reviewer",
                    message=(
                        f"the real roster under src/alfred/agents/ is: "
                        f"{', '.join(real_agents)}."
                    ),
                    canonical_value=", ".join(real_agents),
                )
            )
            continue
        found = False
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                found = True
                break
        if found:
            findings.append(
                _topology_finding(
                    evidence=f"`{bad}`",
                    message=(
                        f"the real agent roster under src/alfred/agents/ is: "
                        f"{', '.join(real_agents)}."
                    ),
                    canonical_value=", ".join(real_agents),
                )
            )
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
            findings.append(
                _path_finding(
                    category=ClaimCategory.CURRENT_PATH,
                    message=(
                        f"not present. Real top-level names: "
                        f"{', '.join(sorted(real_top))}."
                    ),
                    evidence=f"`src/alfred/{name}/`",
                    section="current_state",
                    path=f"src/alfred/{name}/",
                    expected_state="real top-level package or module",
                )
            )
    return findings


def _check_type_checker(text: str, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    allowed_tool = _configured_type_checker_label(repo_root)
    for tool in _unexpected_type_checkers(repo_root):
        if not _current_state_claims_absent_type_checker(text, tool):
            continue
        findings.append(
            Finding(
                category=ClaimCategory.CURRENT_TOOLING,
                severity="error",
                human_message=(
                    f"the live type-checking toolchain from `pyproject.toml` is "
                    f"`{allowed_tool}`; `{tool}` is not configured today."
                ),
                evidence=f"`{tool}`",
                section="current_state",
                finding_object=ToolingFinding(
                    claimed_tool=tool,
                    allowed_tool=allowed_tool,
                ),
            )
        )
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
            findings.append(
                Finding(
                    category=ClaimCategory.PYPROJECT_STATE,
                    severity="error",
                    human_message=(
                        f"`pyproject.toml` is present with "
                        f"[project]={state['has_project_table']} and "
                        f"[project.scripts]={state['has_project_scripts']}."
                    ),
                    evidence=phrase,
                    section="current_state",
                    finding_object=PyprojectFinding(
                        claimed_state=phrase,
                        actual_state=(
                            f"[project]={state['has_project_table']}, "
                            f"[project.scripts]={state['has_project_scripts']}"
                        ),
                    ),
                )
            )
            break
    return findings


def _match_any_phrase(text: str, phrases: list[str]) -> Optional[str]:
    for phrase in phrases:
        if phrase in text:
            return phrase
    return None


def _positive_partial_state_phrases(fact: PartialStateFact) -> list[str]:
    phrases: list[str] = []
    for alias in fact.aliases:
        lower = alias.lower()
        phrases.extend(
            [
                f"{lower} exists",
                f"{lower} exists today",
                f"{lower} is implemented",
                f"{lower} is present",
                f"{lower} is available",
                f"{lower} is already present",
                f"{lower} already exists",
                f"{lower} is already wired",
            ]
        )
    if fact.state_type == PartialStateType.ENTRY_POINT:
        phrases.append(f"{fact.label.lower()} already exists")
    return phrases


def _absence_partial_state_phrases(fact: PartialStateFact) -> list[str]:
    if fact.state_type == PartialStateType.CLI:
        return [
            "no cli",
            "cli does not exist",
            "cli is missing",
            "cli is absent",
            "no alfred cli",
            "there is no cli",
        ]

    label = fact.label.lower()
    phrases = [
        f"no {label} is planned",
        f"{label} is not planned",
        f"there is no planned {label}",
    ]
    for alias in fact.aliases:
        lower = alias.lower()
        if "/" in lower:
            phrases.extend(
                [
                    f"no {lower} endpoint is planned",
                    f"{lower} endpoint is not planned",
                ]
            )
    return phrases


def _check_partial_state(text: str, repo_root: Path) -> list[Finding]:
    """Flag claims that misrepresent declared-but-unimplemented state.

    The repo can contain states that are declared in config or protocol docs but
    not implemented yet. Those states must be described with the vocabulary
    supplied by ``read_partial_state_facts()``.
    """
    findings: list[Finding] = []
    partial = read_partial_state_facts(repo_root)
    lower = text.lower()

    for fact in partial:
        positive_phrase = _match_any_phrase(lower, _positive_partial_state_phrases(fact))
        if positive_phrase:
            findings.append(
                _partial_state_finding(
                    fact=fact,
                    incorrect_phrasing=positive_phrase,
                    message=(
                        f"{fact.label} is not implemented today. Use "
                        f"`{fact.expected_vocabulary}` for this partial state."
                    ),
                )
            )
            continue

        absence_phrase = _match_any_phrase(lower, _absence_partial_state_phrases(fact))
        if absence_phrase:
            findings.append(
                _partial_state_finding(
                    fact=fact,
                    incorrect_phrasing=absence_phrase,
                    message=(
                        f"{fact.label} is already declared at {fact.declared_location}. "
                        f"Use `{fact.expected_vocabulary}`, not a total-absence claim."
                    ),
                )
            )

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
            findings.append(
                _metadata_finding(
                    field_name="id",
                    actual_value=declared_id,
                    expected_value=f"{filename_id} or {filename_id}_DRAFT",
                    message=(
                        f"does not match the filename `{source_path.name}` "
                        f"(expected `{filename_id}` or `{filename_id}_DRAFT`)."
                    ),
                )
            )

    if expected_id and declared_id and declared_id not in {expected_id, expected_id + "_DRAFT"}:
        findings.append(
            _metadata_finding(
                field_name="id",
                actual_value=declared_id,
                expected_value=expected_id,
                message=f"does not match expected id `{expected_id}` supplied to the validator.",
            )
        )

    if expected_previous and declared_prev and declared_prev != expected_previous:
        findings.append(
            _metadata_finding(
                field_name="previous_handover",
                actual_value=declared_prev,
                expected_value=expected_previous,
                message=f"does not match expected `{expected_previous}` supplied to the validator.",
            )
        )

    if expected_date and declared_date and declared_date != expected_date:
        findings.append(
            _metadata_finding(
                field_name="date",
                actual_value=declared_date,
                expected_value=expected_date,
                message=f"does not match expected `{expected_date}` supplied to the validator.",
            )
        )

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
    ctx_date = _extract_metadata_date(ctx)

    findings: list[Finding] = []
    findings.extend(_check_metadata(ctx, source_path, expected_id, expected_previous, expected_date))
    findings.extend(_check_path_existence(current, root))
    findings.extend(_check_reference_documents(current, root, reference_date=ctx_date))
    findings.extend(_check_api_topology(current, root))
    findings.extend(_check_agent_roster(current, root))
    findings.extend(_check_top_level_packages(current, root))
    findings.extend(_check_type_checker(current, root))
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
            findings.append(
                Finding(
                    category=ClaimCategory.PLACEMENT,
                    severity="error",
                    human_message="workflow files must live under `.github/workflows/`.",
                    evidence=f"`{path}`",
                    section="future_tasks",
                    finding_object=PlacementFinding(
                        artifact_type="workflow",
                        proposed_location=path,
                        canonical_location=".github/workflows/",
                        rule="Workflow files must be placed under `.github/workflows/`.",
                    ),
                )
            )
    return findings


def _check_schema_placement(text: str) -> list[Finding]:
    """Flag src/alfred/schemas.py (single file) — schemas must be a package."""
    findings: list[Finding] = []
    if re.search(r"`src/alfred/schemas\.py`", text):
        findings.append(
            Finding(
                category=ClaimCategory.PLACEMENT,
                severity="error",
                human_message=(
                    "schemas should be a package (`src/alfred/schemas/`), "
                    "not a single file `src/alfred/schemas.py`."
                ),
                evidence="`src/alfred/schemas.py`",
                section="future_tasks",
                finding_object=StructuralFinding(
                    artifact_type="schema",
                    proposed_shape="single file `src/alfred/schemas.py`",
                    required_shape="module inside `src/alfred/schemas/`",
                    rule="Schemas live in the `src/alfred/schemas/` package.",
                ),
            )
        )
    return findings


def _extract_handover_phase(markdown: str) -> Optional[int]:
    match = re.search(r"\bPhase\s+(?P<phase>\d+)\b", markdown, re.IGNORECASE)
    if not match:
        return None
    return int(match.group("phase"))


def _check_future_hard_rules(
    text: str,
    repo_root: Path,
    *,
    phase_number: Optional[int] = None,
) -> list[Finding]:
    """Flag future-task content that violates CLAUDE.md hard rules."""
    findings: list[Finding] = []

    allowed_tool = _configured_type_checker_label(repo_root)
    for tool in _unexpected_type_checkers(repo_root):
        if not _future_text_proposes_absent_type_checker(text, tool):
            continue
        findings.append(
            Finding(
                category=ClaimCategory.HARD_RULE,
                severity="error",
                human_message=(
                    f"draft introduces `{tool}`, but the live type-checking toolchain "
                    f"from `pyproject.toml` is `{allowed_tool}`."
                ),
                evidence=f"`{tool}`",
                section="future_tasks",
                finding_object=HardRuleFinding(
                    rule_name="unexpected_type_checker",
                    violation=f"future task proposes {tool}",
                    constraint=(
                        "keep the current type-checking toolchain unless a human "
                        "explicitly approves a pyproject/tooling change"
                    ),
                ),
            )
        )
        break

    docker_re = re.compile(
        r"\b(?:Docker|Dockerfile|docker-compose|docker\s+compose)\b",
        re.IGNORECASE,
    )
    for m in docker_re.finditer(text):
        window = text[max(0, m.start() - 40):m.end() + 40].lower()
        if "not " in window or "never " in window or "no docker" in window:
            continue
        if phase_number is not None and phase_number >= 7:
            break
        findings.append(
            Finding(
                category=ClaimCategory.HARD_RULE,
                severity="error",
                human_message=(
                    "Docker is forbidden until Phase 7 "
                    "(CLAUDE.md: 'No Docker yet — local venv first, containerise in Phase 7')."
                ),
                evidence=m.group(0),
                section="future_tasks",
                finding_object=HardRuleFinding(
                    rule_name="no_docker_yet",
                    violation=f"future task proposes {m.group(0)}",
                    constraint="Docker is out of scope until the allowed phase",
                    phase_allowed="Phase 7",
                ),
            )
        )
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
            findings.append(
                Finding(
                    category=ClaimCategory.TASK_GRANULARITY,
                    severity="warning",
                    human_message="task lacks a quoted file path or a test/validation reference.",
                    evidence=header,
                    section="future_tasks",
                    finding_object=TaskGranularityFinding(
                        task_heading=header,
                        missing_requirement="quoted file path or test/validation reference",
                    ),
                )
            )

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
    root = repo_root or Path(__file__).resolve().parents[1]
    sections = extract_sections(markdown)
    future_text = _future_task_text(sections)
    phase_number = _extract_handover_phase(markdown)

    findings: list[Finding] = []
    findings.extend(_check_workflow_placement(future_text))
    findings.extend(_check_schema_placement(future_text))
    findings.extend(_check_future_hard_rules(future_text, root, phase_number=phase_number))
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
