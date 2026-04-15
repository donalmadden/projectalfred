# Project Alfred

> Alfred — document-mediated, checkpoint-gated agent coordination for software teams

Alfred operationalises a specific methodology for human+AI software development: the structured handover document is the interface between actors, not hidden state in vector databases or chat history. The document is the protocol.

*"Shall I take care of that, sir?"*

## Status

- Phase 1 complete: project framing
- Phase 2 in progress: architecture

## The Problem

Current agentic AI frameworks (AutoGen, CrewAI, LangGraph) optimise for agent autonomy. Real software teams need:
- **Auditability** — who decided what, and why
- **Reproducibility** — the same inputs produce the same coordination
- **Bounded execution** — agents stop at defined checkpoints, not when they feel like it
- **Familiar interfaces** — Git, markdown, tickets, PRs — not new mental models

Teams don't adopt tools that hide state, blur responsibility, or require learning agent-native abstractions.

## The Approach

Alfred treats the handover document as a first-class coordination artifact — a hybrid of PR description, Jira ticket, runbook, ADR, and postmortem that both humans and AI agents can read, write, and execute against.

Five design principles:
1. **Document as protocol** — the handover document is the control surface of the system, not side-channel context
2. **Checkpoint-gated execution** — deterministic decision tables at defined gates, not emergent evaluation
3. **Reasoning/execution isolation** — the executor never makes strategic decisions; the reviewer never executes code
4. **Inline post-mortem → forward plan** — failure analysis is embedded in the execution artifact, not a separate process
5. **Statelessness by design** — each session cold-starts from the document; context loss is a feature, not a bug

## What Alfred Does

- **Validates** handover documents against the methodology (completeness, decision tables, checkpoint definitions)
- **Generates** handover drafts from board state, git history, and prior handovers (human approves before it becomes protocol)
- **Evaluates** checkpoint gates against actual outputs (pass/fail), routing decisions to the appropriate actor
- **Retrieves** across handover history via RAG (cross-document search without replacing individual documents as the interface)
- **Manages** sprint lifecycle through GitHub Projects V2 (story generation, board state, velocity tracking)

## Agent Architecture

| Agent | Responsibility | Constraint |
|---|---|---|
| **Planner** | Sprint planning, capacity, priority, handover drafting | Never executes tasks |
| **Story Generator** | RAG-powered story creation against quality rubric | Output validated before board write |
| **Quality Judge** | Handover validation, checkpoint evaluation, HITL routing | Never modifies artifacts |
| **Retrospective Analyst** | Pattern extraction, velocity analysis, post-mortem synthesis | Read-only across handover corpus |

## Capability Contract

| Layer | Status |
|---|---|
| Purpose & business framing | Phase 1 — done |
| Orchestration & agentic control flow | Phase 2 |
| Tool integration (GitHub Projects V2 API) | Phase 4 |
| Retrieval / RAG (over handover corpus) | Phase 4 |
| State / memory (document-mediated, not hidden) | Phase 4 |
| Evaluation / QA | Phase 6 |
| Observability / tracing | Phase 4 |
| Guardrails / robustness | Phase 4 |
| Deployment / runtime | Phase 7 |
| Enterprise readiness / governance | Phase 7 |

## Stretch Enhancements

| Enhancement | Status |
|---|---|
| Multi-agent coordination (Planner / Generator / Judge / Retro) | Phase 5 |
| Self-evaluation / critique loop (handover quality validation) | Phase 5 |
| Cost-aware model routing (cheap classifier, strong generator) | Phase 5 |
| Human-in-the-loop approval (checkpoint gating before board write) | Phase 5 |
| Live dashboard (sprint state, agent traces, quality scores) | Phase 5 |

## Evaluation Strategy

Alfred is benchmarked against known failure modes in long-horizon agent execution:
- **Error propagation rate** — does the system continue after a detectable failure?
- **Checkpoint compliance** — are decision tables correctly evaluated?
- **Reproducibility score** — variance across repeated runs of the same task
- **State recoverability** — can a fresh agent resume from mid-task using only the document?
- **Control violations** — actions taken outside intended scope

Ablation variants: no checkpoints, no decision tables, no post-mortem, shared context.

## Dogfood

First production use case: [3b_EBD_MLOps](https://github.com/COGNIMANEU/3b_EBD_MLOps) — an MLOps platform for glass fibre manufacturing break-type classification. The 37 BOB_HANDOVER documents in that project are the empirical foundation for this methodology and form the initial RAG corpus.

## Academic Context

The methodology draws on and is positioned against:
- Plan-and-Act (2025) — planner/executor separation
- MetaGPT (ICLR 2024) — SOP-encoded multi-agent workflows
- MAGIS (NeurIPS 2024) — manager/developer/QA decomposition
- CoALA (TMLR 2024) — cognitive architecture for language agents
- Meeting Bridges / boundary objects (CSCW) — document-as-coordination-artifact

Formal classification: *a document-externalized, checkpoint-gated, mixed-initiative orchestration architecture with role-isolated agents.*

## Tech Stack

Python · FastAPI · Pydantic · SQLite · GitHub Projects V2 GraphQL API · LLM API (provider-configurable)

## License

Apache 2.0
