# Alfred — System Architecture

## Section 1: System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                         │
│  POST /generate  POST /evaluate  POST /approve  GET /dashboard      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Orchestrator                              │
│         orchestrate(handover: HandoverDocument) → HandoverDocument  │
│                                                                     │
│  reads HandoverDocument → selects task → calls agent → checks gate  │
│  → writes result back to HandoverDocument → repeats or halts        │
└────────┬──────────┬───────────────┬──────────────────┬─────────────┘
         │          │               │                  │
         ▼          ▼               ▼                  ▼
┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐
│ Planner  │ │   Story      │ │   Quality    │ │    Retro       │
│          │ │  Generator   │ │    Judge     │ │   Analyst      │
│ Drafts   │ │              │ │              │ │                │
│ handover │ │ Draft stories│ │ Evaluates    │ │ Read-only      │
│ Sprint   │ │ against      │ │ checkpoints  │ │ pattern        │
│ planning │ │ rubric       │ │ Validates    │ │ extraction     │
│          │ │              │ │ handovers    │ │ Velocity       │
│ NEVER    │ │ NEVER writes │ │ NEVER modif. │ │ analysis       │
│ executes │ │ to board w/o │ │ artifacts    │ │                │
│          │ │ validation   │ │              │ │ NEVER writes   │
└────┬─────┘ └──────┬───────┘ └──────┬───────┘ └────────┬───────┘
     │              │                │                   │
     └──────────────┴────────────────┴───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Tool Layer                                │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────┐  ┌───────────┐  │
│  │ GitHub Projects  │  │  RAG Engine  │  │ LLM  │  │ SQLite    │  │
│  │    V2 API        │  │              │  │Adapt.│  │Persistence│  │
│  │ (tools/github    │  │ (tools/      │  │(tools│  │(tools/    │  │
│  │  _api.py)        │  │  rag.py)     │  │/llm) │  │persist.)  │  │
│  └──────────────────┘  └──────────────┘  └──────┘  └─────┬─────┘  │
└──────────────────────────────────────────────────────────┼─────────┘
                                                           │
              ┌────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Document Layer (Filesystem)                   │
│                                                                     │
│  docs/BOB_HANDOVER_*.md        ← handover corpus (source of truth) │
│  docs/ALFRED_HANDOVER_*.md     ← Alfred's own handovers            │
│  configs/default.yaml          ← system configuration              │
│  data/alfred.db                ← SQLite (operational bookkeeping)  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|---|---|---|
| **API Layer** | HTTP endpoints, HITL approval gate, dashboard reads | `src/alfred/api.py` — FastAPI routers only |
| **Orchestrator** | Routes work to agents, enforces checkpoint gates, manages handover lifecycle | `src/alfred/orchestrator.py` — single function |
| **Planner** | Sprint planning, capacity, priority, handover drafting | `src/alfred/agents/planner.py` |
| **Story Generator** | RAG-powered story creation against quality rubric | `src/alfred/agents/story_generator.py` |
| **Quality Judge** | Handover validation, checkpoint evaluation, HITL routing | `src/alfred/agents/quality_judge.py` |
| **Retro Analyst** | Pattern extraction, velocity analysis, post-mortem synthesis | `src/alfred/agents/retro_analyst.py` |
| **GitHub API** | Read board state, write stories (with HITL gate), query velocity | `src/alfred/tools/github_api.py` |
| **RAG Engine** | Index handover corpus, chunk at section boundaries, retrieve | `src/alfred/tools/rag.py` |
| **LLM Adapter** | Provider-agnostic LLM calls; returns structured output | `src/alfred/tools/llm.py` |
| **Persistence** | SQLite operational bookkeeping (not the source of truth) | `src/alfred/tools/persistence.py` |
| **Document Layer** | Handover documents on filesystem — the protocol (property 1) | Markdown files, read by all components |

---

## Section 2: Orchestration Style

### Decision: Hand-rolled orchestrator, not a framework

Alfred uses a plain Python function as its orchestrator. No LangGraph, LangChain, CrewAI, AutoGen, or any multi-agent framework.

**Justification:**

1. **Frameworks optimise for the wrong thing.** LangGraph, CrewAI, and AutoGen optimise for agent autonomy — emergent tool-calling loops, self-directed chains of thought, agents that decide when to stop. Alfred's methodology deliberately rejects autonomy (property 5: statelessness by design; the document decides what happens next, not the agent).

2. **Checkpoint gates require deterministic control flow.** Framework "tool-calling loops" cannot guarantee that a checkpoint is evaluated before execution continues. The orchestrator must be able to pause, route to the Quality Judge, receive a verdict, and branch deterministically. This is a simple state machine, not an autonomous loop.

3. **The orchestration logic is simple.** The orchestrator does one thing: iterate through the task list in a `HandoverDocument`, call the appropriate agent for each task, evaluate checkpoints, write results back. A framework would add abstraction on top of simple sequential logic.

4. **Transparency matters.** Every step of the orchestration must be inspectable and reproducible. Hidden orchestration state (framework internals, chat history, agent memory) violates property 1 (document as protocol).

### Orchestrator contract

```python
def orchestrate(
    handover: HandoverDocument,
    config: AlfredConfig,
) -> HandoverDocument:
    """
    Execute a handover document.

    Iterates through tasks in order:
      1. Constructs agent-specific input from HandoverDocument + tools
      2. Calls the appropriate agent
      3. Validates output against the agent's output schema
      4. If the task has a checkpoint: calls Quality Judge with output + checkpoint definition
      5. Routes based on checkpoint verdict (proceed / pivot / stop / escalate)
      6. Writes results back to HandoverDocument
      7. Repeats until all tasks complete or a checkpoint halts execution

    Returns the updated HandoverDocument with results filled in.
    Raises CheckpointHalt if a STOP verdict is received.
    Raises HumanEscalation if an ESCALATE verdict is received.
    """
```

The orchestrator is a function, not a class. It takes a `HandoverDocument` and returns an updated `HandoverDocument`. State lives in the document, not in the orchestrator.

---

## Section 3: Data Flow

### Workflow A — Handover Generation

A human triggers handover generation. Alfred drafts; the human approves.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRIGGER: POST /generate  (or CLI: alfred generate --from-board)    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Read board state            │
           │  (GitHub Projects V2 API)    │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Retrieve prior handovers    │
           │  (RAG over corpus)           │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Planner                     │
           │  Input:  PlannerInput        │
           │  Output: PlannerOutput       │
           │  (draft_handover_markdown)   │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Quality Judge               │
           │  Validates draft against     │
           │  5 methodology properties    │
           │  Output: validation_issues   │
           │          quality_score       │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  HITL APPROVAL GATE          │◄── Human approves / rejects
           │  POST /approve               │
           │  Blocks until decision       │
           └──────────────┬───────────────┘
                          │ approved
                          ▼
           ┌──────────────────────────────┐
           │  Write handover document     │
           │  to filesystem               │
           │  (docs/ALFRED_HANDOVER_N.md) │
           └──────────────────────────────┘
```

### Workflow B — Checkpoint Evaluation

The executor completes a task and pastes output. The Quality Judge evaluates it.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRIGGER: POST /evaluate  (executor output + checkpoint definition) │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Quality Judge               │
           │  Input:  QualityJudgeInput   │
           │    - executor console output │
           │    - checkpoint definition   │
           │    - decision table          │
           │  Output: QualityJudgeOutput  │
           │    - verdict                 │
           │    - reasoning               │
           │    - hitl_required flag      │
           └──────────────┬───────────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
     verdict = proceed         verdict = escalate
             │                         │
             ▼                         ▼
     Continue next task     HITL approval gate
                            Human decides proceed/stop
             │                         │
             ▼                         ▼
     Write verdict to        Write human decision
     HandoverDocument        to HandoverDocument
```

### Workflow C — Retrospective

Triggered at end of sprint. Read-only analysis across handover corpus.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRIGGER: POST /retrospective  (sprint number)                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Retrieve handover corpus    │
           │  (RAG: all handovers for     │
           │   this sprint + prior N)     │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Read velocity history       │
           │  from SQLite                 │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Retro Analyst               │
           │  Input:  RetroAnalystInput   │
           │  Output: RetroAnalystOutput  │
           │    - pattern_report          │
           │    - velocity_trend          │
           │    - retrospective_summary   │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Human review                │
           │  (no write without approval) │
           └──────────────────────────────┘
```
