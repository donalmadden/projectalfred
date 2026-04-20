# Project Alfred

> Alfred — document-mediated, checkpoint-gated agent coordination for software teams

Alfred operationalises a specific methodology for human+AI software development: the structured handover document is the interface between actors, not hidden state in vector stores or chat history. The document is the protocol.

*"Shall I take care of that, sir?"*

[![CI](https://github.com/donal/projectalfred/actions/workflows/ci.yml/badge.svg)](https://github.com/donal/projectalfred/actions/workflows/ci.yml)

## Status

- Core platform implemented through Phase 6.
- Current runtime includes schemas, four agent roles, four tool integrations, a hand-rolled orchestrator, a handover compiler, and a FastAPI API.
- Phase 6 complete: property tests (Hypothesis), eval harness, coverage gates (≥ 80% global), and a 5-stage CI pipeline.
- Phase 7+ work remains open: deployment packaging, Docker/runtime polish, and broader governance hardening.

## The Problem

Many agentic systems optimise for autonomy. Software teams usually need the opposite:

- **Auditability** — who decided what, and why
- **Reproducibility** — the same handover should drive the same coordination path
- **Bounded execution** — work stops at explicit checkpoints
- **Familiar interfaces** — Git, markdown, tickets, approvals, and post-mortems

Teams do not need more hidden state. They need a coordination system that behaves like software delivery, not like an improvising chat loop.

## The Approach

Alfred treats the handover document as a first-class coordination artifact — part PR description, part runbook, part ADR, part post-mortem. Humans and agents both read and write against the same explicit artifact.

Five design principles:
1. **Document as protocol** — the handover document is the control surface of the system
2. **Checkpoint-gated execution** — decision tables at defined gates, not emergent evaluation
3. **Reasoning/execution isolation** — planners reason, evaluators judge, executors execute
4. **Inline post-mortem → forward plan** — failures feed the next handover directly
5. **Statelessness by design** — a fresh session can cold-start from the document alone

## What Alfred Does Today

- **Generates** draft handovers from board state, velocity history, and retrieved handover context
- **Refines** drafts through a bounded planner–judge critique loop before human review
- **Compiles** approved prose into a structured `HandoverDocument`
- **Executes** structured handovers through a plain-Python orchestrator with checkpoint-gated control flow
- **Evaluates** checkpoints against executor output and routes `proceed` / `pivot` / `stop` / `escalate`
- **Retrieves** prior handover context through a local RAG index over markdown documents
- **Tracks** approval requests, expiry, and bookkeeping in SQLite
- **Exposes** the system through a FastAPI surface for generation, compilation, evaluation, approvals, retrospectives, and dashboard reads

## Agent Architecture

| Agent | Responsibility | Constraint |
|---|---|---|
| **Planner** | Sprint planning, capacity, priority, handover drafting | Never executes tasks |
| **Story Generator** | RAG-powered story creation against a quality rubric | Never writes to the board without approval |
| **Quality Judge** | Handover validation, checkpoint evaluation, HITL routing | Never modifies artifacts |
| **Retrospective Analyst** | Pattern extraction, velocity analysis, post-mortem synthesis | Read-only across handover corpus |
| **Compiler** | Approved prose → structured `HandoverDocument` | Extracts structure; does not redesign the draft |

## API Surface

The currently implemented HTTP entrypoints are:

- `POST /generate`
- `POST /compile`
- `POST /evaluate`
- `POST /approvals/request`
- `POST /approve`
- `GET /approvals/pending`
- `POST /approvals/expire`
- `POST /retrospective`
- `GET /dashboard`

## Capability Status

| Area | Current state |
|---|---|
| Purpose and methodology framing | Implemented |
| Schema layer and document model | Implemented |
| Orchestration and checkpoint control flow | Implemented |
| Tool integration (GitHub, RAG, persistence, LLM adapter) | Implemented |
| Multi-agent coordination | Implemented |
| Critique loop and cost routing | Implemented |
| Human-in-the-loop approval with timeout | Implemented |
| Dashboard/API visibility | Implemented at basic read-model level |
| Evaluation harness | Implemented (Phase 6) |
| Property-based tests | Implemented (Phase 6) |
| Coverage gates and CI pipeline | Implemented (Phase 6) |
| Deployment/runtime packaging | Planned in Phase 7 |
| Enterprise governance hardening | Planned in later phases |

## Running Locally

From the repo root:

```bash
pip install -e '.[dev]'

# Unit tests
pytest tests/ --ignore=tests/property -q

# Property tests (Hypothesis)
pytest tests/property/ -v

# Eval harness (deterministic fixtures, no API keys required)
python evals/run_evals.py

# Full suite with coverage gate
pytest --cov=alfred --cov-fail-under=80 -q --tb=short
python scripts/check_coverage.py

# API server
uvicorn alfred.api:app --reload
```

Notes:

- Runtime configuration lives in [`configs/default.yaml`](configs/default.yaml).
- The FastAPI app is the stable entrypoint today.
- A packaged CLI should not be considered the primary entrypoint yet.

## Dogfood

The first real dogfood target is [3b_EBD_MLOps](https://github.com/COGNIMANEU/3b_EBD_MLOps). Its BOB handover documents are both:

- the empirical foundation for the methodology
- the initial RAG corpus
- the source material for end-to-end dogfood runs

Phase 5 closed with a successful generation → compile → execute → checkpoint dogfood run against `BOB_HANDOVER_41.md`.

## What Is Not Done Yet

Alfred is not production-ready yet. The main unfinished areas are:

- deployment/runtime packaging
- Docker and operational polish
- broader governance and enterprise-readiness work

## Academic Context

The methodology draws on and is positioned against:

- Plan-and-Act (2025) — planner/executor separation
- MetaGPT (ICLR 2024) — SOP-encoded multi-agent workflows
- MAGIS (NeurIPS 2024) — manager/developer/QA decomposition
- CoALA (TMLR 2024) — cognitive architecture for language agents
- Meeting Bridges / boundary objects (CSCW) — document-as-coordination-artifact

Formal classification: *a document-externalized, checkpoint-gated, mixed-initiative orchestration architecture with role-isolated agents.*

## Tech Stack

Python · FastAPI · Pydantic · SQLite · GitHub Projects V2 GraphQL API · configurable LLM adapter

## License

Apache 2.0
