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

from alfred.schemas.repo_conventions import (
    PartialStateFact,
    PartialStateType,
    RepoGrowthFacts,
    infer_repo_growth_facts,
    phase_label_from_handover_text,
)
from alfred.tools.docs_policy import iter_policy_paths, read_citable_docs

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
_HANDOVER_NUMBER_RE = re.compile(r"ALFRED_HANDOVER_(?P<number>\d+)(?:_[A-Z0-9_]+)?\.md$")
_SUPPORTED_TYPE_CHECKERS = (
    "basedpyright",
    "mypy",
    "pyright",
    "pyre",
    "pyrefly",
    "pytype",
    "ty",
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
    and type-checker tool sections are present, not their full resolved values.
    """
    root = repo_root or _REPO_ROOT
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return {
            "pyproject_exists": False,
            "has_project_table": False,
            "has_project_scripts": False,
            "type_checkers": [],
            "cli_script_entry": None,
        }
    text = pyproject.read_text(encoding="utf-8")
    cli_entry: Optional[str] = None
    m = re.search(r"""^alfred\s*=\s*["']([^"']+)["']""", text, re.MULTILINE)
    if m:
        cli_entry = m.group(1)
    cli_module_exists = (root / "src" / "alfred" / "cli.py").is_file()
    type_checkers = [
        tool for tool in _SUPPORTED_TYPE_CHECKERS if f"[tool.{tool}]" in text
    ]
    return {
        "pyproject_exists": True,
        "has_project_table": "[project]" in text,
        "has_project_scripts": "[project.scripts]" in text,
        "type_checkers": type_checkers,
        "cli_script_entry": cli_entry,
        "cli_module_exists": cli_module_exists,
    }


def read_type_checkers(repo_root: Optional[Path] = None) -> list[str]:
    """Return the configured static type checkers inferred from pyproject.toml."""
    state = read_packaging_state(repo_root)
    configured = state.get("type_checkers", [])
    assert isinstance(configured, list)
    return [tool for tool in configured if isinstance(tool, str)]


def read_supported_type_checkers() -> list[str]:
    """Return the stable list of type checkers recognized by repo-fact tooling."""
    return list(_SUPPORTED_TYPE_CHECKERS)


def read_reference_documents(repo_root: Optional[Path] = None) -> list[str]:
    """Return citable markdown docs according to the docs lifecycle policy."""
    root = repo_root or _REPO_ROOT
    return read_citable_docs(root)


def read_docs_governance_state(repo_root: Optional[Path] = None) -> dict[str, bool]:
    """Return whether the docs governance surfaces already exist today."""
    root = repo_root or _REPO_ROOT
    docs_dir = root / "docs"
    return {
        "policy_exists": (docs_dir / "DOCS_POLICY.md").is_file(),
        "manifest_exists": (docs_dir / "DOCS_MANIFEST.yaml").is_file(),
        "archive_dir_exists": (docs_dir / "archive").is_dir(),
    }


def read_repo_growth_facts(repo_root: Optional[Path] = None) -> RepoGrowthFacts:
    """Return the typed repo-growth conventions inferred from the workspace."""
    return infer_repo_growth_facts(repo_root or _REPO_ROOT)


def read_repo_conventions(repo_root: Optional[Path] = None) -> dict[str, str]:
    """Return canonical placement conventions as labeled paths.

    These are stable layout rules that the planner must follow when proposing
    new files. The validator uses them to flag future-task proposals that land
    in the wrong directory.
    """
    growth = read_repo_growth_facts(repo_root)
    placement = {rule.artifact_type: rule.canonical_root for rule in growth.placement_rules}
    return {
        "workflow_root": placement.get("workflow", ".github/workflows/"),
        "schema_package_root": placement.get("schema", "src/alfred/schemas/"),
        "agent_package_root": placement.get("agent", "src/alfred/agents/"),
        "tool_package_root": placement.get("tool", "src/alfred/tools/"),
        "script_root": placement.get("script", "scripts/"),
        "test_root": placement.get("test", "tests/"),
        "docs_root": placement.get("doc", "docs/"),
        "config_root": "configs/",
    }


def _latest_handover_doc(repo_root: Path) -> Optional[Path]:
    docs = repo_root / "docs"
    ranked: list[tuple[int, str, Path]] = []
    policy_paths = iter_policy_paths(
        repo_root=repo_root,
        start_path=docs,
        citable=True,
        authoritative=True,
        markdown_only=True,
    )
    candidates = policy_paths if policy_paths else sorted(docs.glob("ALFRED_HANDOVER_*.md"))
    for path in candidates:
        if "_DRAFT" in path.stem:
            continue
        match = _HANDOVER_NUMBER_RE.match(path.name)
        if not match:
            continue
        ranked.append((int(match.group("number")), path.name, path))
    if not ranked:
        return None
    ranked.sort()
    return ranked[-1][2]


def _add_declared_path_state(
    facts: list[PartialStateFact],
    *,
    repo_root: Path,
    handover_path: Path,
    handover_text: str,
    state_key: str,
    state_type: PartialStateType,
    label: str,
    implementation_location: str,
    expected_vocabulary: str,
    aliases: list[str],
) -> None:
    if implementation_location not in handover_text:
        return
    if (repo_root / implementation_location).exists():
        return
    rel_handover = handover_path.relative_to(repo_root).as_posix()
    facts.append(
        PartialStateFact(
            state_key=state_key,
            state_type=state_type,
            label=label,
            is_declared=True,
            is_implemented=False,
            declared_location=f"{rel_handover} (future task reference)",
            implementation_location=implementation_location,
            description=(
                f"{label} is declared in {rel_handover} but the implementation target "
                f"`{implementation_location}` does not exist yet."
            ),
            expected_vocabulary=expected_vocabulary,
            aliases=aliases,
        )
    )


def read_partial_state_facts(repo_root: Optional[Path] = None) -> list[PartialStateFact]:
    """Return typed facts for declared-but-not-yet-implemented repo states."""
    root = repo_root or _REPO_ROOT
    pkg = read_packaging_state(root)
    facts: list[PartialStateFact] = []

    if pkg["cli_script_entry"] and not pkg["cli_module_exists"]:
        facts.append(
            PartialStateFact(
                state_key="cli_module",
                state_type=PartialStateType.CLI,
                label="CLI entry point",
                is_declared=True,
                is_implemented=False,
                declared_location="pyproject.toml [project.scripts]",
                implementation_location="src/alfred/cli.py",
                description=(
                    f"CLI script entry `{pkg['cli_script_entry']}` is declared in "
                    "pyproject.toml but `src/alfred/cli.py` does not exist yet."
                ),
                expected_vocabulary="declared but unimplemented",
                aliases=["cli", "alfred cli", "cli entry point", "alfred.cli:main"],
            )
        )

    latest_handover = _latest_handover_doc(root)
    if latest_handover is not None:
        handover_text = latest_handover.read_text(encoding="utf-8")
        phase_label = phase_label_from_handover_text(handover_text)
        planned_vocab = f"proposed for {phase_label}"

        _add_declared_path_state(
            facts,
            repo_root=root,
            handover_path=latest_handover,
            handover_text=handover_text,
            state_key="release_workflow",
            state_type=PartialStateType.WORKFLOW,
            label="Release workflow",
            implementation_location=".github/workflows/release.yml",
            expected_vocabulary=planned_vocab,
            aliases=[
                "release workflow",
                "release.yml",
                ".github/workflows/release.yml",
            ],
        )
        _add_declared_path_state(
            facts,
            repo_root=root,
            handover_path=latest_handover,
            handover_text=handover_text,
            state_key="health_schema",
            state_type=PartialStateType.SCHEMA,
            label="Health schema",
            implementation_location="src/alfred/schemas/health.py",
            expected_vocabulary=planned_vocab,
            aliases=[
                "health schema",
                "healthcheck model",
                "src/alfred/schemas/health.py",
            ],
        )
        _add_declared_path_state(
            facts,
            repo_root=root,
            handover_path=latest_handover,
            handover_text=handover_text,
            state_key="operations_doc",
            state_type=PartialStateType.DOC,
            label="Operations runbook",
            implementation_location="docs/operations.md",
            expected_vocabulary=planned_vocab,
            aliases=[
                "operations doc",
                "operations runbook",
                "docs/operations.md",
            ],
        )

        api_endpoints = read_api_surface(root)["endpoints"]
        assert isinstance(api_endpoints, list)
        real_endpoints = set(api_endpoints)
        rel_handover = latest_handover.relative_to(root).as_posix()
        for state_key, label, signature, endpoint_path in (
            ("healthz_entry_point", "Health liveness endpoint", "GET /healthz", "/healthz"),
            ("readyz_entry_point", "Readiness endpoint", "GET /readyz", "/readyz"),
        ):
            if signature not in handover_text or signature in real_endpoints:
                continue
            facts.append(
                PartialStateFact(
                    state_key=state_key,
                    state_type=PartialStateType.ENTRY_POINT,
                    label=label,
                    is_declared=True,
                    is_implemented=False,
                    declared_location=f"{rel_handover} (future task reference)",
                    implementation_location=f"src/alfred/api.py -> {signature}",
                    description=(
                        f"{label} `{signature}` is declared in {rel_handover} but is not "
                        "implemented in the FastAPI surface today."
                    ),
                    expected_vocabulary=planned_vocab,
                    aliases=[
                        label.lower(),
                        signature.lower(),
                        endpoint_path,
                        f"{endpoint_path} endpoint",
                    ],
                )
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
    type_checkers = read_type_checkers(root)
    reference_docs = read_reference_documents(root)
    docs_governance = read_docs_governance_state(root)
    growth = read_repo_growth_facts(root)

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
        "Citable reference docs: "
        + (", ".join(reference_docs) if reference_docs else "(none)")
    )
    lines.append(
        "Docs governance: "
        f"docs/DOCS_POLICY.md exists={docs_governance['policy_exists']}, "
        f"docs/DOCS_MANIFEST.yaml exists={docs_governance['manifest_exists']}, "
        f"docs/archive/ exists={docs_governance['archive_dir_exists']}"
    )
    lines.append(
        "Type checker: "
        + (", ".join(type_checkers) if type_checkers else "none")
    )
    partial = read_partial_state_facts(root)
    if partial:
        lines.append("Partial-state facts:")
        for fact in partial:
            lines.append(
                f"  {fact.state_type.value} / {fact.label}: {fact.description}"
            )
            lines.append(
                f"  Declared={fact.is_declared}, Implemented={fact.is_implemented}, "
                f"Vocabulary=\"{fact.expected_vocabulary}\""
            )

    lines.append("Repo-growth placement rules:")
    for rule in growth.placement_rules:
        lines.append(
            f"  {rule.artifact_type}: root={rule.canonical_root}, pattern={rule.pattern}"
        )
    lines.append("Repo-growth naming conventions:")
    for rule in growth.naming_conventions:
        lines.append(f"  {rule.artifact_type}: {rule.pattern}")
    lines.append("Repo-growth structural rules:")
    for rule in growth.structural_rules:
        lines.append(
            f"  {rule.artifact_type}: required={rule.required_shape}; "
            f"forbidden={rule.forbidden_shape}"
        )
    return lines
