# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

ProjectAlfred — operationalises document-mediated, checkpoint-gated agent coordination for software teams. The handover document is the protocol, not overhead.

## Core Methodology (non-negotiable)

These five properties are the foundation. Every design decision must preserve them:

1. **Document as protocol** — the handover document is the control surface, not a side-channel. Never replace it with hidden state.
2. **Checkpoint-gated execution** — deterministic decision tables at defined gates. No emergent evaluation.
3. **Reasoning/execution isolation** — executor never makes strategic decisions; reviewer never executes code. Strict epistemic separation.
4. **Inline post-mortem → forward plan** — failure analysis embedded in the execution artifact, not a separate process.
5. **Statelessness by design** — each session cold-starts from the document. Context loss is a feature.

## Tech Stack

- Python (functions only, no classes unless framework requires)
- FastAPI for HTTP interface
- Pydantic for all schemas and config
- SQLite for state persistence
- GitHub Projects V2 GraphQL API for board integration
- LLM API (provider-agnostic; configured via `configs/`)

## Critical Rules

- **Functions only** — no classes except Pydantic models and FastAPI routers
- **Pydantic schemas for everything** — all agent inputs/outputs, all config, all state
- **Never hardcode** — all parameters in `configs/`
- **pyproject.toml** is the single source of truth for dependencies
- **One task = one commit** — commit messages: `phaseN: taskN — description`
- **No Docker yet** — local venv first, containerise in Phase 7
- **No AI tool attribution in any document** — never reference Claude, Anthropic, GPT, OpenAI, or any specific AI tool or vendor in any user-facing file (README, docs, comments, commit messages). The project speaks for itself.
- **RAG supplements, never replaces** — RAG indexes handover history for cross-document retrieval, but the individual handover document remains the interface for any single session
- **Alfred drafts, humans approve** — Alfred can generate handover drafts but a human approves before it becomes protocol

## Build Phases

1. Project framing — done
2. Architecture — in progress
3. Repository scaffold
4. Core implementation
5. Stretch enhancements (multi-agent, critique loop, cost routing, HITL, dashboard)
6. Evaluations and tests
7. Developer experience and deployment
8. Portfolio hardening

## Dogfood Reference

- Real use case: `~/code/3b_EBD_MLOps`
- BOB_HANDOVER docs in that repo are the primary RAG corpus and empirical foundation
- Quality benchmark story: COGNIMANEU/pilot01-development#20

## Environment

```bash
source .venv/bin/activate
```

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `donalmadden/projectalfred`, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
