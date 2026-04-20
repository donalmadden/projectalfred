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

from alfred.tools.repo_facts import (  # noqa: E402
    read_agent_modules,
    read_api_surface,
    read_packaging_state,
    read_top_level_packages,
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
    r"`(?P<path>(?:docs|src|scripts|tests|configs|evals)/[A-Za-z0-9_./\-]+)`"
)


_NEGATION_CUES = (
    " no ", " not ", " never ", " without ", " isn't ", " doesn't ",
    "does not exist", "is not present", "is missing", "not yet exist",
    "no such", "removed", "deleted",
)


def _is_negated(text: str, match_start: int) -> bool:
    """True if the match is in a context that explicitly denies the path exists.

    Heuristic: look at the 80 characters before the match and the opening of
    the sentence it sits in. Catches phrases like "No `tests/unit/` tree exists"
    and "`src/alfred/api/main.py` does not exist".
    """
    window_start = max(0, match_start - 80)
    window = (" " + text[window_start:match_start].lower()).replace("\n", " ")
    if any(cue in window for cue in _NEGATION_CUES):
        return True
    # Also look 60 chars after, catching "... does not exist" trailing the path.
    tail_end = min(len(text), match_start + 200)
    tail = text[match_start:tail_end].lower().replace("\n", " ")
    if any(cue in tail[:120] for cue in ("does not exist", "is not present", "is missing", "not yet exist")):
        return True
    return False


def _check_path_existence(text: str, repo_root: Path) -> list[str]:
    errors: list[str] = []
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
        if _is_negated(text, match.start()):
            continue
        errors.append(
            f"Reference to `{candidate}` in a current-state section, but "
            f"{normalised!r} does not exist in the repo."
        )
    return errors


def _check_api_topology(text: str, repo_root: Path) -> list[str]:
    errors: list[str] = []
    api = read_api_surface(repo_root)
    real_path = api["module_path"]
    real_endpoints = api["endpoints"]
    assert isinstance(real_endpoints, list)

    # Reject directory-style claims about the API module.
    bad_api_dir = re.search(r"`src/alfred/api/(?:[A-Za-z0-9_.]+)?`", text)
    if bad_api_dir:
        errors.append(
            f"Claim mentions `{bad_api_dir.group(0)}` but the real FastAPI app "
            f"lives in `{real_path}` (single file)."
        )

    # Reject explicit `src/alfred/api/main.py` references in current-state text.
    if "src/alfred/api/main.py" in text:
        errors.append(
            "Reference to `src/alfred/api/main.py` in a current-state section, "
            f"but the FastAPI entrypoint is `{real_path}`."
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
            errors.append(
                f"Claim of {claimed} endpoints does not match the real FastAPI "
                f"surface ({len(real_endpoints)} endpoints in {real_path})."
            )
            break  # one mismatch is enough; don't double-count

    return errors


# Known-bad agent names: modules that do not exist under src/alfred/agents/.
# Only flag these when they appear as code-style identifiers (backticked,
# module path, or .py reference) — bare prose mentions of "executor" and
# "reviewer" are legitimate methodology role words.
_KNOWN_BAD_AGENT_NAMES = ("executor", "reviewer", "summariser", "summarizer")


def _check_agent_roster(text: str, repo_root: Path) -> list[str]:
    errors: list[str] = []
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
            errors.append(
                "Current-state section enumerates `planner, executor, reviewer` "
                f"as the agent roster, but the real roster under "
                f"src/alfred/agents/ is: {', '.join(real_agents)}."
            )
            continue
        found = False
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                found = True
                break
        if found:
            errors.append(
                f"Current-state section references `{bad}` as an agent module, "
                f"but the real agent roster under src/alfred/agents/ is: "
                f"{', '.join(real_agents)}."
            )
    return errors


def _check_top_level_packages(text: str, repo_root: Path) -> list[str]:
    errors: list[str] = []
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
            errors.append(
                f"Reference to `src/alfred/{name}/` as an existing package, "
                f"but it is not present. Real top-level names: "
                f"{', '.join(sorted(real_top))}."
            )
    return errors


def _check_type_checker(text: str) -> list[str]:
    errors: list[str] = []
    # "mypy" mentioned as part of current-state tooling is wrong.
    # Allow mention in contexts that explicitly negate it ("mypy is not used").
    for m in re.finditer(r"\bmypy\b", text, re.IGNORECASE):
        window_start = max(0, m.start() - 40)
        window_end = min(len(text), m.end() + 40)
        window = text[window_start:window_end].lower()
        if "not " in window or "never " in window or "is not" in window:
            continue
        errors.append(
            "Current-state section references `mypy`, but the repo uses "
            "`pyright`. Phase 6 explicitly forbids adding `mypy`."
        )
        break
    return errors


def _check_pyproject_state(text: str, repo_root: Path) -> list[str]:
    errors: list[str] = []
    state = read_packaging_state(repo_root)
    if not state["pyproject_exists"]:
        return errors
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
            errors.append(
                f"Claim '{phrase}' but `pyproject.toml` is present with "
                f"[project]={state['has_project_table']} and "
                f"[project.scripts]={state['has_project_scripts']}."
            )
            break
    return errors


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
) -> list[str]:
    errors: list[str] = []
    declared_id = _extract_metadata_id(context)
    declared_date = _extract_metadata_date(context)
    declared_prev = _extract_metadata_previous(context)

    if source_path is not None and declared_id:
        filename_id = _filename_id_stem(source_path)
        # Permit the declared id to match either the filename stem or the
        # filename stem plus `_DRAFT` (both are legitimate for a draft).
        legit = {filename_id, filename_id + "_DRAFT"}
        if declared_id not in legit:
            errors.append(
                f"Metadata id `{declared_id}` does not match the filename "
                f"`{source_path.name}` (expected `{filename_id}` or "
                f"`{filename_id}_DRAFT`)."
            )

    if expected_id and declared_id and declared_id not in {expected_id, expected_id + "_DRAFT"}:
        errors.append(
            f"Metadata id `{declared_id}` does not match expected id "
            f"`{expected_id}` supplied to the validator."
        )

    if expected_previous and declared_prev and declared_prev != expected_previous:
        errors.append(
            f"Metadata previous_handover `{declared_prev}` does not match "
            f"expected `{expected_previous}` supplied to the validator."
        )

    if expected_date and declared_date and declared_date != expected_date:
        errors.append(
            f"Metadata date `{declared_date}` does not match expected "
            f"`{expected_date}` supplied to the validator."
        )

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate(
    markdown: str,
    source_path: Optional[Path] = None,
    *,
    expected_id: Optional[str] = None,
    expected_previous: Optional[str] = None,
    expected_date: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> list[str]:
    """Return a list of factual errors. Empty list means the draft is grounded."""
    root = repo_root or Path(__file__).resolve().parents[1]
    sections = extract_sections(markdown)
    current = current_state_text(sections)
    ctx = context_block(sections)

    errors: list[str] = []
    errors.extend(_check_metadata(ctx, source_path, expected_id, expected_previous, expected_date))
    errors.extend(_check_path_existence(current, root))
    errors.extend(_check_api_topology(current, root))
    errors.extend(_check_agent_roster(current, root))
    errors.extend(_check_top_level_packages(current, root))
    errors.extend(_check_type_checker(current))
    errors.extend(_check_pyproject_state(current, root))
    return errors


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an Alfred planning draft against repository facts.",
    )
    parser.add_argument("path", type=Path, help="Path to the planning draft")
    parser.add_argument("--expected-id", default=None)
    parser.add_argument("--expected-previous", default=None)
    parser.add_argument("--expected-date", default=None)
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"error: not a file: {args.path}", file=sys.stderr)
        return 2
    try:
        markdown = args.path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: could not read {args.path}: {exc}", file=sys.stderr)
        return 2

    errors = validate(
        markdown,
        source_path=args.path,
        expected_id=args.expected_id,
        expected_previous=args.expected_previous,
        expected_date=args.expected_date,
    )
    if errors:
        print(f"FAIL {args.path}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"OK   {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
