# Project Alfred

> Alfred — document-mediated, checkpoint-gated agent coordination for software teams

Alfred operationalises a specific methodology for human+AI software development: the structured handover document is the interface between actors, not hidden state in vector stores or chat history. The document is the protocol.

*"Shall I take care of that, sir?"*

[![CI](https://github.com/donal/projectalfred/actions/workflows/ci.yml/badge.svg)](https://github.com/donal/projectalfred/actions/workflows/ci.yml)

## Status

- Core platform now includes the Phase 7 runtime and deployment surface.
- Current runtime includes typed schemas, four agent roles plus the compiler, a packaged CLI, a FastAPI API, structured request-aware logging, health probes, a rootless Docker image, and a tag-scoped release workflow.
- Quality gates remain in place: property tests (Hypothesis), eval harness, coverage gates (>= 80% global), and a 5-stage CI pipeline.
- Broader governance hardening and production deployment targets beyond the current Docker surface remain open.

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
- **Exposes** the system through a FastAPI surface for generation, compilation, evaluation, approvals, retrospectives, dashboard reads, and `/healthz` + `/readyz` probes
- **Ships** a packaged CLI for planning, evaluation, validation, version inspection, and local serving
- **Emits** structured JSON logs with per-request correlation IDs for API traffic
- **Runs** through a rootless Docker image locally and publishes release artifacts on version tags

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
- `GET /healthz`
- `GET /readyz`

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
| CLI entrypoint | Implemented (Phase 7) |
| Health and readiness probes | Implemented (Phase 7) |
| Structured request logging | Implemented (Phase 7) |
| Deployment/runtime packaging | Implemented (Phase 7) |
| Release automation | Implemented (Phase 7) |
| Enterprise governance hardening | Planned in later phases |

## Quick Start (Local)

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alfred version
alfred serve --reload
```

Notes:

- Runtime configuration lives in [`configs/default.yaml`](configs/default.yaml).
- Export provider or GitHub credentials in your shell before commands that need live model or board access.
- The packaged CLI is the preferred local entrypoint; `alfred serve` wraps the FastAPI app.
- Probe the service with:

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

- Run the full local quality gate with:

```bash
pytest tests/ --ignore=tests/property -q
pytest tests/property/ -v
python evals/run_evals.py
pytest --cov=alfred --cov-fail-under=80 -q --tb=short
python scripts/check_coverage.py
```

## Quick Start (Docker)

Use Docker Compose for the local container workflow:

```bash
cp .env.example .env
docker compose up --build
```

Then verify the service from another shell:

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

Notes:

- [`docker-compose.yml`](docker-compose.yml) injects variables from [`.env.example`](.env.example) via your local `.env`.
- `ALFRED_WORKSPACE_PATH` defaults to `.` and is mounted read-only at `/workspace`; change it in `.env` if you want the container to see a different checkout.
- [`Dockerfile`](Dockerfile) builds a rootless image whose default command is `alfred serve --host 0.0.0.0 --port 8000`.

## Environment Variables

The supported runtime variables are documented in [`.env.example`](.env.example):

- `LOG_LEVEL`: JSON log verbosity for API and middleware logging.
- `SHUTDOWN_DRAIN_TIMEOUT_S`: maximum shutdown drain window for pending approvals.
- `ANTHROPIC_API_KEY`: Anthropic credential for live planning and evaluation requests.
- `OPENAI_API_KEY`: OpenAI credential for live planning and evaluation requests.
- `GITHUB_TOKEN`: GitHub Projects V2 access for board-backed workflows.
- `ALFRED_WORKSPACE_PATH`: host path mounted into `/workspace` by Docker Compose.

## CLI Reference

The packaged entrypoint is `alfred`. Top-level help currently looks like:

```text
usage: alfred [-h] {plan,evaluate,serve,validate,version} ...
```

Subcommands:

- `alfred plan`: generate a draft handover plan.
- `alfred evaluate`: evaluate checkpoint evidence against a checkpoint definition.
- `alfred serve`: run the FastAPI service through uvicorn.
- `alfred validate`: run the planning factual validator against a handover markdown file.
- `alfred version`: print the installed Alfred package version.

Useful examples:

```bash
alfred --help
alfred plan --dry-run
alfred evaluate --dry-run
alfred validate docs/canonical/ALFRED_HANDOVER_6.md
alfred serve --help
```

## Dogfood

The first real dogfood target is [3b_EBD_MLOps](https://github.com/COGNIMANEU/3b_EBD_MLOps). Its BOB handover documents are both:

- the empirical foundation for the methodology
- the initial RAG corpus
- the source material for end-to-end dogfood runs

Phase 5 closed with a successful generation → compile → execute → checkpoint dogfood run against `BOB_HANDOVER_41.md`.

## What Is Not Done Yet

Alfred is not production-ready yet. The main unfinished areas are:

- broader production deployment targets beyond the current Docker surface
- additional operator ergonomics beyond the current CLI and probe set
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
