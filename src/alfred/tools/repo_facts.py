"""
Repo truth snapshot — authoritative current-state facts about the workspace.

Planner generation paths must pass these facts into the LLM prompt so that
present-tense claims in ``## WHAT EXISTS TODAY`` are grounded in the code that
actually ships, not inferred from RAG prose. The factual validator re-derives
the same facts at validation time; if the two diverge, the draft is rejected.

All helpers read directly from the repository (no RAG, no network). Pure
functions only; no caching beyond the duration of a single call. The repo
root is resolved from this file's location so callers do not need to pass a
path.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Files that represent "not a module" (package markers, caches, dunder files).
_EXCLUDED_MODULE_STEMS = {"__init__"}


def _src_dir(relative: str) -> Path:
    return _REPO_ROOT / "src" / "alfred" / relative


def read_agent_modules(repo_root: Optional[Path] = None) -> list[str]:
    """Return the sorted module stems under ``src/alfred/agents/`` (minus ``__init__``)."""
    root = repo_root or _REPO_ROOT
    directory = root / "src" / "alfred" / "agents"
    if not directory.is_dir():
        return []
    names = [p.stem for p in directory.glob("*.py") if p.stem not in _EXCLUDED_MODULE_STEMS]
    return sorted(names)


def read_tool_modules(repo_root: Optional[Path] = None) -> list[str]:
    """Return the sorted module stems under ``src/alfred/tools/`` (minus ``__init__``)."""
    root = repo_root or _REPO_ROOT
    directory = root / "src" / "alfred" / "tools"
    if not directory.is_dir():
        return []
    names = [p.stem for p in directory.glob("*.py") if p.stem not in _EXCLUDED_MODULE_STEMS]
    return sorted(names)


def read_top_level_packages(repo_root: Optional[Path] = None) -> list[str]:
    """Return the sorted package/module names directly under ``src/alfred/``.

    Excludes ``__pycache__`` and ``__init__``. Files are listed as stems (no
    ``.py``), directories are listed as names. The validator uses this to reject
    claims about nonexistent packages such as ``rag/`` or ``state/``.
    """
    root = repo_root or _REPO_ROOT
    directory = root / "src" / "alfred"
    if not directory.is_dir():
        return []
    entries: list[str] = []
    for entry in directory.iterdir():
        if entry.name.startswith("__"):
            continue
        if entry.is_dir():
            entries.append(entry.name)
        elif entry.suffix == ".py":
            entries.append(entry.stem)
    return sorted(entries)


_ENDPOINT_RE = re.compile(
    r"""^@app\.(?P<method>get|post|put|delete|patch)\(\s*["'](?P<path>[^"']+)["']""",
    re.MULTILINE,
)


def read_api_surface(repo_root: Optional[Path] = None) -> dict[str, object]:
    """Parse ``src/alfred/api.py`` and return the authoritative API surface.

    Returns a dict with:
      - ``module_path``: str relative to repo root (``src/alfred/api.py``)
      - ``endpoints``: list[str] formatted ``"METHOD /path"`` in source order
    """
    root = repo_root or _REPO_ROOT
    api_path = root / "src" / "alfred" / "api.py"
    if not api_path.is_file():
        return {"module_path": "src/alfred/api.py", "endpoints": []}
    text = api_path.read_text(encoding="utf-8")
    endpoints = [
        f"{m.group('method').upper()} {m.group('path')}"
        for m in _ENDPOINT_RE.finditer(text)
    ]
    return {"module_path": "src/alfred/api.py", "endpoints": endpoints}


def read_packaging_state(repo_root: Optional[Path] = None) -> dict[str, object]:
    """Return facts about the repo's packaging and toolchain state.

    Intentionally string-sniffing rather than TOML-parsing — the validator
    needs to know whether markers like ``[project]``, ``[project.scripts]``,
    and ``pyright``/``mypy`` are present, not their full resolved values.
    """
    root = repo_root or _REPO_ROOT
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return {
            "pyproject_exists": False,
            "has_project_table": False,
            "has_project_scripts": False,
            "uses_pyright": False,
            "uses_mypy": False,
            "cli_script_entry": None,
        }
    text = pyproject.read_text(encoding="utf-8")
    cli_entry: Optional[str] = None
    m = re.search(r"""^alfred\s*=\s*["']([^"']+)["']""", text, re.MULTILINE)
    if m:
        cli_entry = m.group(1)
    cli_module_exists = (root / "src" / "alfred" / "cli.py").is_file()
    return {
        "pyproject_exists": True,
        "has_project_table": "[project]" in text,
        "has_project_scripts": "[project.scripts]" in text,
        "uses_pyright": "pyright" in text,
        "uses_mypy": re.search(r"\bmypy\b", text) is not None,
        "cli_script_entry": cli_entry,
        "cli_module_exists": cli_module_exists,
    }


def read_reference_documents(repo_root: Optional[Path] = None) -> list[str]:
    """Return paths of canonical reference documents under ``docs/`` that exist today."""
    root = repo_root or _REPO_ROOT
    docs = root / "docs"
    if not docs.is_dir():
        return []
    names: list[str] = []
    for p in sorted(docs.iterdir()):
        if p.is_file() and p.suffix == ".md":
            names.append(f"docs/{p.name}")
    return names


def read_repo_conventions(repo_root: Optional[Path] = None) -> dict[str, str]:
    """Return canonical placement conventions as labeled paths.

    These are stable layout rules that the planner must follow when proposing
    new files. The validator uses them to flag future-task proposals that land
    in the wrong directory.
    """
    return {
        "workflow_root": ".github/workflows/",
        "schema_package_root": "src/alfred/schemas/",
        "agent_package_root": "src/alfred/agents/",
        "tool_package_root": "src/alfred/tools/",
        "script_root": "scripts/",
        "test_root": "tests/",
        "docs_root": "docs/",
        "config_root": "configs/",
    }


def read_partial_state_facts(repo_root: Optional[Path] = None) -> dict[str, str]:
    """Return labeled facts about items declared but not yet implemented.

    Each value is a human-readable description suitable for injection into
    a planner prompt. Keys are stable identifiers; values change as the repo
    evolves.
    """
    root = repo_root or _REPO_ROOT
    pkg = read_packaging_state(root)
    facts: dict[str, str] = {}

    if pkg["cli_script_entry"] and not pkg["cli_module_exists"]:
        facts["cli_module"] = (
            f"CLI script entry declared ({pkg['cli_script_entry']}) "
            f"but src/alfred/cli.py is absent"
        )
    elif pkg["cli_script_entry"] and pkg["cli_module_exists"]:
        facts["cli_module"] = (
            f"CLI script entry declared ({pkg['cli_script_entry']}) "
            f"and src/alfred/cli.py exists"
        )

    release_workflow = root / ".github" / "workflows" / "release.yml"
    if not release_workflow.exists():
        facts["release_workflow"] = (
            ".github/workflows/release.yml is not yet present"
        )

    return facts


def build_repo_facts_summary(repo_root: Optional[Path] = None) -> list[str]:
    """Render a human-readable bullet list for injection into the planner prompt.

    Each line is self-contained so the LLM can quote it directly under
    ``## WHAT EXISTS TODAY``. Keep the output deterministic: stable ordering and
    no timestamps.
    """
    root = repo_root or _REPO_ROOT
    agents = read_agent_modules(root)
    tools = read_tool_modules(root)
    top_level = read_top_level_packages(root)
    api = read_api_surface(root)
    pkg = read_packaging_state(root)

    lines: list[str] = []
    lines.append(
        f"Agent modules in src/alfred/agents/: {', '.join(agents) if agents else '(none)'}"
    )
    lines.append(
        f"Tool modules in src/alfred/tools/: {', '.join(tools) if tools else '(none)'}"
    )
    lines.append(
        f"Top-level names under src/alfred/: {', '.join(top_level) if top_level else '(none)'}"
    )
    lines.append(f"FastAPI module path: {api['module_path']}")
    endpoints = api["endpoints"]
    assert isinstance(endpoints, list)
    if endpoints:
        lines.append(f"FastAPI endpoints ({len(endpoints)}): {', '.join(endpoints)}")
    else:
        lines.append("FastAPI endpoints: (none parsed)")
    lines.append(
        "pyproject.toml: "
        f"exists={pkg['pyproject_exists']}, "
        f"[project]={pkg['has_project_table']}, "
        f"[project.scripts]={pkg['has_project_scripts']}, "
        f"cli_entry={pkg['cli_script_entry']}"
    )
    lines.append(
        f"Type checker: {'pyright' if pkg['uses_pyright'] else 'none'}"
        + (" (mypy IS NOT in use)" if not pkg["uses_mypy"] else " (mypy present)")
    )
    partial = read_partial_state_facts(root)
    for fact in partial.values():
        lines.append(f"Partial state: {fact}")
    conventions = read_repo_conventions(root)
    lines.append("Repo-growth conventions:")
    for label, path in conventions.items():
        lines.append(f"  {label}: {path}")
    return lines
