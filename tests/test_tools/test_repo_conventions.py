"""Tests for typed repo-growth conventions."""
from __future__ import annotations

from pathlib import Path

from alfred.schemas.repo_conventions import (
    format_repo_growth_facts_for_prompt,
    infer_repo_growth_facts,
)


def _fake_repo(tmp_path: Path) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "tests" / "test_agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "schemas").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "tools").mkdir(parents=True)

    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (tmp_path / "docs" / "ALFRED_HANDOVER_6.md").write_text("# Handover\n", encoding="utf-8")
    (tmp_path / "scripts" / "generate_phase7.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "tests" / "test_agents" / "test_planner.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "src" / "alfred" / "api.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "src" / "alfred" / "agents" / "planner.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "src" / "alfred" / "schemas" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "alfred" / "schemas" / "checkpoint.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "src" / "alfred" / "tools" / "repo_facts.py").write_text("# stub\n", encoding="utf-8")
    return tmp_path


def test_infer_repo_growth_facts_returns_placement_rules(tmp_path: Path) -> None:
    facts = infer_repo_growth_facts(_fake_repo(tmp_path))
    artifact_types = {rule.artifact_type for rule in facts.placement_rules}
    assert {"workflow", "schema", "agent", "tool", "test", "doc", "script"} <= artifact_types


def test_infer_repo_growth_facts_returns_naming_conventions(tmp_path: Path) -> None:
    facts = infer_repo_growth_facts(_fake_repo(tmp_path))
    artifact_types = {rule.artifact_type for rule in facts.naming_conventions}
    assert {"handover_doc", "workflow", "test_module", "schema_module"} <= artifact_types


def test_infer_repo_growth_facts_returns_structural_rules(tmp_path: Path) -> None:
    facts = infer_repo_growth_facts(_fake_repo(tmp_path))
    artifact_types = {rule.artifact_type for rule in facts.structural_rules}
    assert {"api", "schema", "agent", "tool"} <= artifact_types


def test_format_repo_growth_facts_for_prompt_mentions_examples(tmp_path: Path) -> None:
    prompt_block = format_repo_growth_facts_for_prompt(repo_root=_fake_repo(tmp_path))
    assert "Placement rules:" in prompt_block
    assert "Naming conventions:" in prompt_block
    assert "Structural rules:" in prompt_block
    assert ".github/workflows/" in prompt_block
    assert "ALFRED_HANDOVER_" in prompt_block
