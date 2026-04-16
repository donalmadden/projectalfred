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

---

## Section 4: State Flow

### State lives in the document, not in the orchestrator

Alfred has no hidden state. All runtime state is written into the `HandoverDocument` as tasks complete and checkpoints are evaluated. The document is a complete, reproducible record of the session.

```
HandoverDocument lifecycle:

  DRAFT                 IN_PROGRESS             COMPLETE
  ──────                ───────────             ────────

  tasks:                tasks:                  tasks:
    - status: pending     - status: complete      - status: complete (all)
    - result: None        - result: {...}        
                          - checkpoint:         post_mortem:
                            result: {...}         - what_worked: [...]
                                                  - what_failed: [...]
                                                  - forward_plan: [...]
```

### State transitions per task

```
             ┌──────────────────────────────┐
             │  task.status = "pending"     │
             └──────────────┬───────────────┘
                            │  orchestrator calls agent
                            ▼
             ┌──────────────────────────────┐
             │  task.status = "in_progress" │
             └──────────────┬───────────────┘
                            │  agent returns output
                            ▼
             ┌──────────────────────────────┐
             │  Has checkpoint?             │
             └──────┬───────────────────────┘
                    │
         ┌──────────┴───────────┐
         │ No checkpoint        │ Checkpoint present
         ▼                      ▼
  task.status =      Quality Judge evaluates
  "complete"         ┌─────────────────────┐
  Write result       │ verdict             │
                     └──────┬──────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     "proceed"          "pivot"          "stop" /
     task.status =    Orchestrator       "escalate"
     "complete"       revises plan       Halt execution
```

### Persistence strategy

Two persistence layers — one canonical, one operational:

| Layer | Storage | What lives here | Source of truth? |
|---|---|---|---|
| **Document layer** | Filesystem (`.md` files) | Handover documents, decisions, task results, post-mortems | **Yes** |
| **Operational layer** | SQLite (`data/alfred.db`) | Velocity history, agent traces, checkpoint evaluation history, sprint metadata | No — derived from documents |

SQLite is rebuilt from the document corpus at any time. If it diverges from the documents, documents win.

---

## Section 5: Agent Interaction Model

### Agents are functions, not actors

Agents do not communicate with each other. They do not share state, hold references, or form a graph. Each agent is a pure function: given an input schema, it returns an output schema. The orchestrator is the only entity that composes them.

```
WRONG (framework-style):

  Planner ──message──► Story Generator ──critique──► Quality Judge
     ▲                                                     │
     └─────────────────── revision loop ──────────────────┘

CORRECT (Alfred):

  Orchestrator
      │
      ├──► Planner(PlannerInput) → PlannerOutput
      │
      ├──► StoryGenerator(StoryGeneratorInput) → StoryGeneratorOutput
      │
      ├──► QualityJudge(QualityJudgeInput) → QualityJudgeOutput
      │
      └──► RetroAnalyst(RetroAnalystInput) → RetroAnalystOutput
```

### Information flow between agents

Agents do not pass output directly to each other. When the orchestrator needs to route output from one agent as input to another, it writes the output to the `HandoverDocument` first, then constructs a fresh input from the document.

```
Planner produces draft_handover_markdown
        │
        ▼
Orchestrator writes draft to HandoverDocument.tasks[n].result
        │
        ▼
Orchestrator constructs QualityJudgeInput from HandoverDocument
        │
        ▼
Quality Judge evaluates the draft
```

This ensures: (a) the document is always the record; (b) no agent sees another agent's internal reasoning; (c) a session can be replayed from any point by re-reading the document.

### Agent capability matrix

| Agent | Reads board | Writes board | Reads corpus | Writes docs | Evaluates checkpoints | Executes tasks |
|---|---|---|---|---|---|---|
| Planner | ✓ | ✗ | ✓ | Draft only | ✗ | ✗ |
| Story Generator | ✓ | ✗ | ✓ | Draft only | ✗ | ✗ |
| Quality Judge | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| Retro Analyst | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |

No agent writes to the board directly. Board writes require a HITL approval gate.

---

## Section 6: Technical Risks

### Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | LLM output fails to parse against output schema | High | Medium | Pydantic validation at every agent boundary; retry with structured output prompt on parse failure; log failure to HandoverDocument |
| R2 | GitHub Projects V2 GraphQL API rate limits or schema changes | Medium | High | Wrap all API calls in thin adapter (`tools/github_api.py`); mock the adapter in tests; rate-limit backoff |
| R3 | RAG retrieves irrelevant chunks, degrading planner quality | Medium | Medium | Section-boundary chunking (not sentence-boundary); relevance score threshold; log retrieved chunks to HandoverDocument for inspection |
| R4 | Checkpoint decision tables become stale as methodology evolves | Low | High | Decision tables live in the handover document itself, not in code — human updates the document, not a config file |
| R5 | HITL gate blocks indefinitely in automated runs | Low | Low | Configurable timeout; default verdict on timeout (stop, not proceed); surface timeout in HandoverDocument |
| R6 | SQLite diverges from document corpus (e.g., manual edits to docs) | Medium | Low | SQLite is rebuildable from corpus at any time; provide `alfred rebuild-index` command in Phase 7 |
| R7 | Circular import between `handover.py` and `checkpoint.py` | Resolved | — | Deferred import at module bottom with `model_rebuild()` — pattern is in place |
| R8 | Orchestrator grows implicit state over time (methodology drift) | Medium | High | Orchestrator is a single function with no instance variables; state is only written to HandoverDocument; enforced by code review |

### Architecture invariants (must never be violated)

1. The `HandoverDocument` is the only shared state between the orchestrator and agents.
2. Agents receive typed input schemas; they return typed output schemas. No unstructured dicts cross agent boundaries.
3. A checkpoint verdict of `escalate` always routes to the HITL gate. The orchestrator cannot override this.
4. No agent holds a reference to another agent. All composition is done by the orchestrator.
5. Board writes only occur after a HITL approval gate clears.

---

## Section 7: Phase 3 Scaffold Specification

Phase 3 creates the repository structure that Phase 4 implementation fills in. Every file listed here is a stub: it has the correct module structure and docstring, but no implementation. This lets Phase 4 work in parallel without import errors.

### Directory tree

```
projectalfred/
├── src/
│   └── alfred/
│       ├── __init__.py
│       ├── api.py                    ← FastAPI app and routers (stub)
│       ├── orchestrator.py           ← orchestrate() function (stub)
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── planner.py            ← Planner agent (stub)
│       │   ├── story_generator.py    ← Story Generator agent (stub)
│       │   ├── quality_judge.py      ← Quality Judge agent (stub)
│       │   └── retro_analyst.py      ← Retro Analyst agent (stub)
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── handover.py           ← HandoverDocument schema ✓ done
│       │   ├── checkpoint.py         ← Checkpoint schema ✓ done
│       │   ├── agent.py              ← Agent I/O schemas ✓ done
│       │   └── config.py             ← AlfredConfig schema ✓ done
│       └── tools/
│           ├── __init__.py
│           ├── github_api.py         ← GitHub Projects V2 adapter (stub)
│           ├── rag.py                ← RAG engine (stub)
│           ├── llm.py                ← LLM adapter (stub)
│           └── persistence.py        ← SQLite persistence (stub)
├── tests/
│   ├── __init__.py
│   ├── test_schemas/
│   │   ├── __init__.py
│   │   ├── test_handover.py          ← Schema round-trip tests (stub)
│   │   ├── test_checkpoint.py        ← Checkpoint tests (stub)
│   │   └── test_config.py            ← Config validation tests (stub)
│   └── test_orchestrator.py          ← Orchestrator tests (stub)
├── configs/
│   ├── default.yaml                  ← System config ✓ done
│   └── handover_template.md          ← Handover template (stub)
├── docs/
│   ├── architecture.md               ← This document ✓ done
│   └── ALFRED_HANDOVER_*.md          ← Handover corpus
├── data/                             ← Runtime data (gitignored)
│   ├── alfred.db                     ← SQLite (created at runtime)
│   └── rag_index/                    ← RAG index (created at runtime)
├── pyproject.toml                    ← Dependencies and tooling ← Task 8
└── CLAUDE.md                         ← ✓ done
```

### Stub contract

Each stub file must:
1. Have a module-level docstring that states the component's responsibility and what Phase 4 will implement.
2. Define the public function or router signature with the correct type annotations.
3. Raise `NotImplementedError` in the function body (not `pass`) so import-time errors are caught.
4. Import from the schema layer (`src/alfred/schemas/`) so import resolution is validated.

### Phase 3 acceptance criteria

- `python -c "import alfred"` succeeds with no errors.
- `python -c "from alfred.schemas.handover import HandoverDocument"` succeeds.
- `python -c "from alfred.orchestrator import orchestrate"` succeeds (raises `NotImplementedError` if called).
- All stub files exist at the paths specified above.
- `pytest tests/` runs without import errors (all tests skip or pass).
- `pyproject.toml` is present and `pip install -e .` completes cleanly.
