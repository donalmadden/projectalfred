# Project Alfred

> Alfred — agentic Scrum Master for human+AI development teams

Alfred is an open-source agentic AI system that manages the complete Scrum lifecycle: story generation, sprint planning with human approval, execution tracking, retrospective analysis, and velocity learning — integrated with GitHub Projects V2.

*"Shall I take care of that, sir?"*

## Status

- Phase 1 complete: project framing
- Phase 2 in progress: architecture

## Use Case

Modern development teams increasingly include both human and AI actors. Standard Scrum tooling was designed for human-only teams — stories are ambiguous, acceptance criteria are informal, and retrospective analysis is manual.

Alfred provides:
- Machine-verifiable acceptance criteria in every story
- Role-aware story generation (e.g. MLOps Engineer / ML Engineer / Data Scientist)
- Sprint lifecycle state management with full audit trail
- Structured retrospectives with pattern extraction
- Velocity tracking across human and AI actors
- Human-in-the-loop approval before any board mutation

## Agent Architecture

| Agent | Responsibility |
|---|---|
| **Planner** | Sprint planning, capacity allocation, priority ordering |
| **Story Generator** | RAG-powered story creation against a quality rubric |
| **Quality Judge** | Rubric-based validation, HITL approval routing |
| **Retrospective Analyst** | Pattern extraction, velocity analysis, improvement suggestions |

## Capability Contract

| Layer | Status |
|---|---|
| Purpose & business framing | Phase 1 — done |
| Orchestration & agentic control flow | Phase 2 |
| Tool integration (GitHub Projects V2 API) | Phase 4 |
| Retrieval / RAG | Phase 4 |
| State / memory | Phase 4 |
| Evaluation / QA | Phase 6 |
| Observability / tracing | Phase 4 |
| Guardrails / robustness | Phase 4 |
| Deployment / runtime | Phase 7 |
| Enterprise readiness / governance | Phase 7 |

## Stretch Enhancements

| Enhancement | Status |
|---|---|
| Multi-agent coordination (Planner / Generator / Judge / Retro) | Phase 5 |
| Self-evaluation / critique loop (story quality pass) | Phase 5 |
| Cost-aware model routing (cheap classifier, strong generator) | Phase 5 |
| Human-in-the-loop approval (sprint sign-off before board write) | Phase 5 |
| Live dashboard (sprint state, agent traces, quality scores) | Phase 5 |

## Dogfood

First production use case: [3b_EBD_MLOps](https://github.com/COGNIMANEU/3b_EBD_MLOps) — an MLOps platform for glass fibre manufacturing break-type classification. The BOB_HANDOVER documents in that project form the initial RAG corpus and the quality benchmark story is [pilot01-development#20](https://github.com/COGNIMANEU/pilot01-development/issues/20).

## Tech Stack

Python · FastAPI · Pydantic · SQLite · GitHub Projects V2 GraphQL API · LLM API (provider-configurable)

## License

Apache 2.0
