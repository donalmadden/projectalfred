# Operationalise Alfred

## Purpose

This brief captures the architectural review of Alfred against [docs/protocol/architecture.md](../protocol/architecture.md) and turns that review into a forward plan. It is intended to seed the future-forward section of a later `ALFRED_HANDOVER_n.md`.

## Executive Call

- Alfred is highly faithful to its original vision in structure, methodology, and code organisation.
- Alfred is only partially faithful in live operational behaviour: the core architecture exists, but the public runtime still does not fully run through the document-mediated orchestration loop that the architecture treats as the product.
- The current stage is best described as **late prototype / pre-beta**, or informally **Phase 7.5**.
- The central next move is not "add more features". It is to **operationalise the architecture end-to-end**.

## What Alfred Already Proves

- A plain-Python orchestrator exists and enforces checkpoint-gated control flow.
- Agent roles are separated by typed input/output schemas rather than informal conventions.
- The handover document model is real, rich, and renderable.
- Checkpoint evaluation, verdict routing, and inline post-mortem behaviour are implemented.
- The tool layer is real: GitHub, RAG, LLM adapter, persistence, logging, docs policy, and repo-facts helpers all exist.
- The operational shell is real: FastAPI, CLI, health/readiness probes, structured logging, Docker, Compose, release workflow, and operator runbook.
- The repo has meaningful engineering discipline: unit tests, property tests, evals, coverage gates, and docs-governance checks.

## Gap Summary

### 1. The orchestrator exists, but it is not yet the dominant runtime path

- The architecture makes `orchestrate(handover, config) -> HandoverDocument` the centre of the system.
- In practice, the public API surface mostly exposes direct agent operations such as generate, evaluate, retrospective, and compile.
- This means the system is architecturally coherent but not yet fully operationalised around its own core abstraction.

### 2. The handover document is not yet the sole live execution artifact

- The architecture says the document should be the protocol and canonical state surface.
- Today, meaningful runtime state is split across markdown, JSON under `data/handovers/`, and SQLite bookkeeping.
- The split is not fatal, but it weakens the "document as protocol" claim in day-to-day execution.

### 3. HITL exists, but the approval loop is not yet closed into orchestration

- Approval request, approval decision, expiry, and listing endpoints exist.
- The system does not yet present a fully closed loop where an orchestration run pauses, persists the decision point in the handover, resumes from the same artifact, and then performs the gated action.
- This is especially important for board-write actions and true `escalate` handling.

### 4. The document state machine is thinner than the architectural vision

- The architecture describes explicit task lifecycle state such as `pending`, `in_progress`, and `complete`.
- The current schema captures results and checkpoints well, but task lifecycle status is still implicit.
- That makes replay and operator understanding workable, but not yet maximally explicit.

### 5. Alfred is stronger in architectural integrity than in product closure

- The repo already proves the design philosophy.
- What remains is to make the runtime behave like the philosophy, not merely describe it.

## Development-Stage Adjudication

Alfred should be treated as a **late prototype / pre-beta system**.

That means:

- The core ideas are no longer speculative.
- The primary modules and boundaries are no longer scaffolding.
- The system is demonstrable and testable.
- The remaining work is mainly about closing loops, reducing split-brain state, and making the public runtime faithful to the architectural thesis.

The simplest honest label is:

> Alfred has validated the architecture in code, but has not yet fully operationalised it in the primary runtime path.

## Operationalisation Objectives

### 1. Make the orchestrator the first-class execution surface

- Introduce an explicit API and CLI path for executing a structured `HandoverDocument` through `orchestrate(...)`.
- Treat direct agent endpoints as supporting surfaces, not the main product story.
- Ensure the primary demo path of Alfred goes through document -> orchestrator -> checkpoint -> decision -> resumed execution.

### 2. Promote the handover artifact back to canonical runtime state

- Decide what the canonical on-disk execution artifact should be for active runs.
- Ensure task outcomes, checkpoint verdicts, post-mortems, and resumable state are written back into that artifact in a durable and inspectable way.
- Keep SQLite operational and query-friendly, but clearly derived from the document artifact rather than competing with it.

### 3. Close the HITL loop

- Make `escalate` and approval-requiring actions produce resumable decision points tied to a specific handover and task/checkpoint.
- Ensure human approval updates the same execution record Alfred will later resume from.
- Wire board-write actions so the approval gate is not merely documented but enforced by the end-to-end flow.

### 4. Deepen the document state model

- Add explicit task lifecycle status if that remains the clearest way to match the architecture.
- Consider storing richer task outputs or typed execution snapshots when summaries are insufficient for replay or auditability.
- Keep the document readable by humans; do not solve this by hiding more state elsewhere.

### 5. Prove the loop end-to-end

- Add one or more dogfood paths that exercise generation, compilation, orchestration, checkpoint pause, human decision, resume, and completion.
- Add end-to-end tests for the orchestrated runtime, not only for agent endpoints and local primitives.
- Update portfolio/demo guidance so Alfred is presented as a document-native runtime, not just a collection of well-implemented components.

## Invariants To Preserve

- Do not replace the hand-rolled orchestrator with an autonomous agent framework.
- Do not introduce hidden memory or chat-history dependence as a substitute for document state.
- Do not let SQLite become the source of truth.
- Do not allow board writes to bypass human approval.
- Do not trade auditability for convenience while closing the runtime loop.

## Definition Of Done For "Operationalised Alfred"

- A structured handover can be executed through a first-class API or CLI path built around `orchestrate(...)`.
- The execution artifact can be paused and resumed without relying on hidden process state.
- Checkpoint verdicts and human decisions are durably written back into the execution artifact.
- Approval-gated actions are enforced by the runtime, not just by design intent.
- The primary Alfred demo can honestly show the full document-native loop from draft to gated execution.

## Candidate Future-Forward Section

The next phase should focus on operationalising Alfred rather than broadening it. The architecture has been validated in structure: the orchestrator exists, the agent boundaries are typed, the tool layer is real, and the runtime shell is already demoable. What remains is to make the live system behave like its own thesis. That means making `orchestrate(...)` the primary execution surface, restoring the handover artifact as the canonical runtime record, closing the human-approval loop into resumable execution semantics, and proving the full path end-to-end in dogfood and tests. Alfred is best understood today as a late prototype or pre-beta system: the bones are real, but the product still partially bypasses the operating model it argues for.
