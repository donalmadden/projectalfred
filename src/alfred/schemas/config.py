"""
System configuration schema.

All tuneable parameters live here. Secrets are referenced by environment
variable name only — never stored in config files.

The config schema validates exhaustively at startup: invalid config fails
fast, not at the point of first use.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# LLM provider configuration
# ---------------------------------------------------------------------------


class LLMConfig(BaseModel):
    """Language model provider configuration.

    Provider-agnostic: the `provider` field selects the adapter.
    All provider-specific implementation lives in `tools/llm.py`.
    """

    provider: str = "anthropic"
    model: str = ""
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)

    @field_validator("provider")
    @classmethod
    def provider_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("LLM provider must not be empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Cost-aware model routing (stretch enhancement — Phase 5)
# ---------------------------------------------------------------------------


class CostRoutingConfig(BaseModel):
    """Route tasks to cheap or strong models based on task type.

    Disabled by default. Enabled in Phase 5.
    Cheap model handles triage and classification tasks.
    Strong model handles generation and analysis tasks.
    """

    enabled: bool = False
    provider: str = ""  # can differ from llm.provider; falls back to llm.provider if empty
    classifier_model: str = ""
    generator_model: str = ""


# ---------------------------------------------------------------------------
# GitHub Projects V2
# ---------------------------------------------------------------------------


class GitHubConfig(BaseModel):
    """GitHub Projects V2 GraphQL API configuration.

    The actual token is never stored — only the name of the environment
    variable that holds it. Alfred reads `os.environ[token_env_var]` at
    runtime.
    """

    org: str = ""
    project_number: int = 0
    token_env_var: str = "GITHUB_TOKEN"

    @field_validator("token_env_var")
    @classmethod
    def token_env_var_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("token_env_var must not be empty — it names the env var that holds the token")
        return v.strip()


# ---------------------------------------------------------------------------
# RAG configuration
# ---------------------------------------------------------------------------


class RAGConfig(BaseModel):
    """Retrieval-augmented generation over the handover corpus.

    RAG supplements, never replaces: the individual handover document remains
    the interface for any single session.
    """

    corpus_path: str = ""
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    embedding_model: str = ""
    index_path: str = "data/rag_index"

    @model_validator(mode="after")
    def overlap_less_than_chunk(self) -> "RAGConfig":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than chunk_size ({self.chunk_size})"
            )
        return self


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------


class DatabaseConfig(BaseModel):
    """SQLite operational bookkeeping.

    Stores sprint metadata, velocity history, agent traces, and checkpoint
    evaluation history. This is NOT the source of truth — handover documents
    on the filesystem are.
    """

    path: str = "data/alfred.db"


# ---------------------------------------------------------------------------
# Handover document settings
# ---------------------------------------------------------------------------


class HandoverConfig(BaseModel):
    """Settings governing handover document handling."""

    schema_version: str = "1.0"
    template_path: str = "configs/handover_template.md"
    corpus_glob: str = "**/*_HANDOVER_*.md"


# ---------------------------------------------------------------------------
# Per-agent enable flags
# ---------------------------------------------------------------------------


class AgentToggle(BaseModel):
    """Enable/disable a specific agent."""

    enabled: bool = True


class PlannerAgentConfig(BaseModel):
    """Planner-specific settings including critique loop parameters."""

    enabled: bool = True
    max_critique_iterations: int = Field(default=2, ge=0)
    critique_quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class AgentsConfig(BaseModel):
    """Agent enable flags and per-agent settings. All enabled by default."""

    planner: PlannerAgentConfig = Field(default_factory=PlannerAgentConfig)
    story_generator: AgentToggle = Field(default_factory=AgentToggle)
    quality_judge: AgentToggle = Field(default_factory=AgentToggle)
    retro_analyst: AgentToggle = Field(default_factory=AgentToggle)


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------


class AlfredConfig(BaseModel):
    """System-wide configuration for Alfred.

    Loaded from `configs/default.yaml` (or an override file) at startup.
    Invalid config raises a ValidationError immediately — fail fast.

    Secrets (API keys, tokens) are never stored here. They are referenced
    by environment variable name and read from `os.environ` at runtime.
    """

    llm: LLMConfig = Field(default_factory=LLMConfig)
    cost_routing: CostRoutingConfig = Field(default_factory=CostRoutingConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    handover: HandoverConfig = Field(default_factory=HandoverConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
