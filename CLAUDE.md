# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

ProjectAlfred — agentic Scrum Master for human+AI development teams.

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
- BOB_HANDOVER docs in that repo are the primary RAG corpus for testing
- Quality benchmark story: COGNIMANEU/pilot01-development#20

## Environment

```bash
source .venv/bin/activate
```
