"""Tests for ``alfred.tools.repo_facts`` — the repo truth snapshot."""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.tools import repo_facts

# ---------------------------------------------------------------------------
# Fixtures — a fake repo tree mirroring the real Alfred layout.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Build a minimal repo tree under tmp_path."""
    alfred = tmp_path / "src" / "alfred"
    (alfred / "agents").mkdir(parents=True)
    (alfred / "tools").mkdir(parents=True)
    (alfred / "schemas").mkdir(parents=True)

    # Package markers
    (alfred / "__init__.py").write_text("")
    (alfred / "agents" / "__init__.py").write_text("")
    (alfred / "tools" / "__init__.py").write_text("")
    (alfred / "schemas" / "__init__.py").write_text("")

    # Agents
    for name in ("planner", "story_generator", "quality_judge"):
        (alfred / "agents" / f"{name}.py").write_text("# stub\n")

    # Tools
    for name in ("llm", "rag", "persistence"):
        (alfred / "tools" / f"{name}.py").write_text("# stub\n")

    # Orchestrator + api
    (alfred / "orchestrator.py").write_text("# stub\n")
    (alfred / "api.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        '@app.get("/dashboard")\n'
        "def dashboard(): ...\n\n"
        '@app.post("/generate")\n'
        "def generate(): ...\n\n"
        '@app.post("/approvals/request")\n'
        "def approvals_request(): ...\n"
    )

    # pyproject.toml with both markers and pyright
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        "name = \"alfred\"\n\n"
        "[project.scripts]\n"
        "alfred = \"alfred.cli:main\"\n\n"
        "[tool.pyright]\n"
        "include = [\"src\"]\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Individual readers
# ---------------------------------------------------------------------------


def test_read_agent_modules_excludes_dunder(fake_repo: Path) -> None:
    agents = repo_facts.read_agent_modules(fake_repo)
    assert "planner" in agents
    assert "story_generator" in agents
    assert "quality_judge" in agents
    assert "__init__" not in agents


def test_read_agent_modules_sorted(fake_repo: Path) -> None:
    agents = repo_facts.read_agent_modules(fake_repo)
    assert agents == sorted(agents)


def test_read_tool_modules_excludes_dunder(fake_repo: Path) -> None:
    tools = repo_facts.read_tool_modules(fake_repo)
    assert set(tools) == {"llm", "rag", "persistence"}


def test_read_top_level_packages_excludes_pycache_and_dunder(fake_repo: Path) -> None:
    top = repo_facts.read_top_level_packages(fake_repo)
    assert "agents" in top
    assert "tools" in top
    assert "schemas" in top
    assert "orchestrator" in top
    assert "api" in top
    assert "__pycache__" not in top
    assert "__init__" not in top


def test_read_api_surface_parses_endpoints(fake_repo: Path) -> None:
    api = repo_facts.read_api_surface(fake_repo)
    assert api["module_path"] == "src/alfred/api.py"
    endpoints = api["endpoints"]
    assert "GET /dashboard" in endpoints
    assert "POST /generate" in endpoints
    assert "POST /approvals/request" in endpoints


def test_read_api_surface_returns_empty_when_missing(tmp_path: Path) -> None:
    api = repo_facts.read_api_surface(tmp_path)
    assert api["module_path"] == "src/alfred/api.py"
    assert api["endpoints"] == []


def test_read_packaging_state_detects_project_table(fake_repo: Path) -> None:
    state = repo_facts.read_packaging_state(fake_repo)
    assert state["pyproject_exists"] is True
    assert state["has_project_table"] is True
    assert state["has_project_scripts"] is True
    assert state["uses_pyright"] is True
    assert state["uses_mypy"] is False
    assert state["cli_script_entry"] == "alfred.cli:main"


def test_read_packaging_state_missing_pyproject(tmp_path: Path) -> None:
    state = repo_facts.read_packaging_state(tmp_path)
    assert state["pyproject_exists"] is False
    assert state["has_project_table"] is False
    assert state["cli_script_entry"] is None


def test_read_packaging_state_detects_mypy_when_present(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"x\"\n\n[tool.mypy]\nstrict = true\n"
    )
    state = repo_facts.read_packaging_state(tmp_path)
    assert state["uses_mypy"] is True
    assert state["uses_pyright"] is False


# ---------------------------------------------------------------------------
# build_repo_facts_summary — the bullet list injected into the planner prompt.
# ---------------------------------------------------------------------------


def test_build_repo_facts_summary_contains_agent_modules(fake_repo: Path) -> None:
    lines = repo_facts.build_repo_facts_summary(fake_repo)
    joined = "\n".join(lines)
    assert "planner" in joined
    assert "story_generator" in joined
    assert "quality_judge" in joined


def test_build_repo_facts_summary_contains_fastapi_path(fake_repo: Path) -> None:
    lines = repo_facts.build_repo_facts_summary(fake_repo)
    joined = "\n".join(lines)
    assert "src/alfred/api.py" in joined


def test_build_repo_facts_summary_mentions_pyright_not_mypy(fake_repo: Path) -> None:
    lines = repo_facts.build_repo_facts_summary(fake_repo)
    joined = "\n".join(lines)
    assert "pyright" in joined
    assert "mypy IS NOT in use" in joined


def test_build_repo_facts_summary_is_deterministic(fake_repo: Path) -> None:
    a = repo_facts.build_repo_facts_summary(fake_repo)
    b = repo_facts.build_repo_facts_summary(fake_repo)
    assert a == b


def test_build_repo_facts_summary_reports_endpoint_count(fake_repo: Path) -> None:
    lines = repo_facts.build_repo_facts_summary(fake_repo)
    joined = "\n".join(lines)
    # Three endpoints in the fake repo.
    assert "FastAPI endpoints (3)" in joined


# ---------------------------------------------------------------------------
# Real repo smoke tests — live workspace, not a fixture.
# Guards against regressions in the real source tree.
# ---------------------------------------------------------------------------


def test_live_repo_has_all_five_agents() -> None:
    agents = repo_facts.read_agent_modules()
    for expected in ("planner", "story_generator", "quality_judge", "retro_analyst", "compiler"):
        assert expected in agents, f"missing agent module: {expected}"


def test_live_repo_api_is_single_file() -> None:
    api = repo_facts.read_api_surface()
    assert api["module_path"] == "src/alfred/api.py"
    assert len(api["endpoints"]) > 0


def test_live_repo_uses_pyright_not_mypy() -> None:
    state = repo_facts.read_packaging_state()
    assert state["uses_pyright"] is True
    assert state["uses_mypy"] is False
