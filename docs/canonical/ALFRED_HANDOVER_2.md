# Alfred's Handover Document #2 — Phase 3: Repository Scaffold

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_2
**date:** 2026-04-16
**author:** Donal
**previous_handover:** ALFRED_HANDOVER_1
**baseline_state:** Phase 2 complete (9 commits on `main`). All schemas implemented and validated. Architecture document written in full. `pyproject.toml` present and `pip install -e .` passes. Phase 3 not started.

**Reference Documents:**
- `~/code/projectalfred/docs/ALFRED_HANDOVER_1.md` — Phase 2 handover; defines methodology, design decisions, Phase 3 scope
- `~/code/projectalfred/docs/architecture.md` — Full system architecture; Section 7 is the Phase 3 scaffold specification
- `~/code/projectalfred/CLAUDE.md` — Build rules and non-negotiable methodology properties
- `~/code/projectalfred/src/alfred/schemas/` — All four schemas implemented in Phase 2; Phase 3 wires them in
- `~/code/3b_EBD_MLOps/docs/BOB_HANDOVER_*.md` — The empirical corpus; use as reference, do not modify

---

## WHAT EXISTS TODAY

### Git History — Phase 2 Complete (9 commits)

The following commits constitute Phase 2 in full. They are the state this handover was written against.

```
cbb3340  phase 2 complete
a6a5985  phase2: task 8 — pyproject.toml
fe1bdf3  phase2: task 7 — architecture doc: technical risks and phase 3 scaffold spec
4e38373  phase2: task 6 — architecture doc: state flow and agent interaction model
7d75a3b  phase2: task 5 — architecture doc: system architecture, orchestration, data flow
a241932  phase2: task 4 — system config schema and default config
ef379dd  phase2: task 3 — agent boundary schemas
2ad1a0f  phase2: task 2 — checkpoint and decision table schemas
10b79a4  phase2: task 1 — handover document schema
```

### Files Delivered by Phase 2

| File | What it contains | Status |
|---|---|---|
| `src/alfred/schemas/handover.py` | `HandoverDocument` Pydantic model with `render_markdown()` and `from_markdown()` | Complete |
| `src/alfred/schemas/checkpoint.py` | `Checkpoint`, `DecisionTable`, `CheckpointResult`, `Verdict`, `create_checkpoint()` | Complete |
| `src/alfred/schemas/agent.py` | All four agent `Input`/`Output` schema pairs plus shared types | Complete |
| `src/alfred/schemas/config.py` | `AlfredConfig` and all sub-configs; validates exhaustively at import | Complete |
| `src/alfred/__init__.py` | Package init | Complete |
| `src/alfred/schemas/__init__.py` | Package init | Complete |
| `configs/default.yaml` | Default config; all secrets by env var name only | Complete |
| `docs/architecture.md` | 7-section architecture document | Complete |
| `pyproject.toml` | Dependencies, build config, tool config; `pip install -e .` passes | Complete |

### What Does NOT Exist

- `src/alfred/agents/` — no directory, no stubs
- `src/alfred/tools/` — no directory, no stubs
- `src/alfred/orchestrator.py` — no file
- `src/alfred/api.py` — no file
- `tests/` — no directory
- `configs/handover_template.md` — no file
- `data/` — no directory

`python -c "from alfred.orchestrator import orchestrate"` currently raises `ImportError`.

### Key Design Decisions Inherited from Phase 2

These are settled. Do not revisit them in Phase 3.

1. **Hand-rolled orchestrator.** No LangGraph, LangChain, CrewAI, AutoGen. Plain Python function.
2. **Agents are functions, not actors.** No inter-agent communication. All composition through the orchestrator and the `HandoverDocument`.
3. **State lives in the document.** SQLite is operational bookkeeping only; handover documents on filesystem are the source of truth.
4. **Schemas enforce contracts.** Agents cannot produce output outside their schema. Pydantic validation at every boundary.
5. **No AI tool attribution.** Provider-agnostic language throughout.

---

## HARD RULES

1. **Work in `~/code/projectalfred`** only. Do not touch `3b_EBD_MLOps`.
2. **Functions only.** No classes except Pydantic models and FastAPI routers.
3. **Stubs raise `NotImplementedError`, not `pass`.** A stub that silently does nothing masks import failures.
4. **Every stub imports from `src/alfred/schemas/`** so import resolution is validated at Phase 3, not Phase 4.
5. **One task = one commit.** Commit messages: `phase3: task N — description`.
6. **No implementation.** Phase 3 is structure only. If you find yourself writing an actual LLM call, a database query, or a GitHub API request, stop. That is Phase 4.
7. **No AI tool attribution** in any file you create.
8. **The five methodology properties are non-negotiable.** The orchestrator skeleton must reflect statelessness and checkpoint-gated control flow structurally, not as comments.
9. **`pip install -e .` must pass at all times.** Do not introduce imports that break the package.
10. **Phase 3 acceptance criteria (Task 8) must all pass before this phase is done.** If any import fails, the phase is not complete.

---

## WHAT THIS PHASE PRODUCES

By the end of Phase 3 you will have:

- `src/alfred/agents/` — four agent stub modules with correct signatures and docstrings
- `src/alfred/tools/` — four tool stub modules with correct signatures and docstrings
- `src/alfred/orchestrator.py` — control flow skeleton: iterates tasks, would call agents, enforces checkpoint gate logic
- `src/alfred/api.py` — FastAPI app with route definitions for all five endpoints
- `tests/` — directory structure with test stubs (importable, zero failures, all skip)
- `configs/handover_template.md` — blank handover template derived from the schema
- `data/.gitkeep` — runtime data directory tracked in repo (contents gitignored)
- Phase 3 acceptance criteria all pass (Task 8)

You will **not**:
- Implement any agent logic, tool calls, or LLM interactions
- Stand up a database or RAG index
- Write passing tests (stubs only)
- Modify the schemas from Phase 2
- Implement `render_markdown()` or `from_markdown()` beyond what Phase 2 already delivered

---

## TASK OVERVIEW

| # | Task | Deliverable | Commit |
|---|---|---|---|
| 1 | Create package directory structure | `agents/__init__.py`, `tools/__init__.py`, `data/.gitkeep` | `phase3: task 1 — package directory structure` |
| 2 | Agent stubs | `agents/planner.py`, `story_generator.py`, `quality_judge.py`, `retro_analyst.py` | `phase3: task 2 — agent stubs` |
| 3 | Tool stubs | `tools/github_api.py`, `rag.py`, `llm.py`, `persistence.py` | `phase3: task 3 — tool stubs` |
| 4 | Orchestrator skeleton | `src/alfred/orchestrator.py` | `phase3: task 4 — orchestrator skeleton` |
| 5 | API skeleton | `src/alfred/api.py` | `phase3: task 5 — api skeleton` |
| 6 | Test structure | `tests/` with stubs | `phase3: task 6 — test structure` |
| 7 | Handover template | `configs/handover_template.md` | `phase3: task 7 — handover template` |
| 8 | Integration validation | Acceptance criteria verified | `phase3: task 8 — integration validation` |

---

## TASK 1 — Create Package Directory Structure

**Goal:** Create the directory tree that Phase 2's architecture.md Section 7 specifies, with `__init__.py` files and a `data/.gitkeep`.

### Changes

- Create `src/alfred/agents/__init__.py` (empty)
- Create `src/alfred/tools/__init__.py` (empty)
- Create `tests/__init__.py` (empty)
- Create `tests/test_schemas/__init__.py` (empty)
- Create `tests/test_orchestrator.py` (empty stub — see Task 6)
- Create `data/.gitkeep` (empty file so the directory is tracked)
- Verify `data/` is gitignored for content but `.gitkeep` is tracked (check `.gitignore`)

### Verification

```bash
python -c "import alfred.agents; import alfred.tools; print('package structure ok')"
```

**Commit message:** `phase3: task 1 — package directory structure`

---

## TASK 2 — Agent Stubs

**Goal:** Create stub modules for all four agents. Each stub defines the correct public function signature, imports its input/output schemas, and raises `NotImplementedError`.

### Stub pattern (apply to all four)

```python
"""
<Agent name> — <one-line responsibility>.

Phase 4 implementation will:
- <what Phase 4 adds>
"""
from alfred.schemas.agent import <AgentInput>, <AgentOutput>


def <agent_function_name>(input: <AgentInput>) -> <AgentOutput>:
    """<One sentence: what this agent does and its key constraint>."""
    raise NotImplementedError
```

### Files

| File | Function | Input schema | Output schema |
|---|---|---|---|
| `src/alfred/agents/planner.py` | `run_planner` | `PlannerInput` | `PlannerOutput` |
| `src/alfred/agents/story_generator.py` | `run_story_generator` | `StoryGeneratorInput` | `StoryGeneratorOutput` |
| `src/alfred/agents/quality_judge.py` | `run_quality_judge` | `QualityJudgeInput` | `QualityJudgeOutput` |
| `src/alfred/agents/retro_analyst.py` | `run_retro_analyst` | `RetroAnalystInput` | `RetroAnalystOutput` |

### Verification

```bash
python -c "
from alfred.agents.planner import run_planner
from alfred.agents.story_generator import run_story_generator
from alfred.agents.quality_judge import run_quality_judge
from alfred.agents.retro_analyst import run_retro_analyst
print('all agent stubs importable')
"
```

**Commit message:** `phase3: task 2 — agent stubs`

---

## TASK 3 — Tool Stubs

**Goal:** Create stub modules for all four tools. Each stub defines the public interface, imports relevant types, and raises `NotImplementedError`.

### Files and their public interfaces

**`src/alfred/tools/github_api.py`**
```python
"""
GitHub Projects V2 GraphQL adapter.

Phase 4 implementation will:
- Read board state via GraphQL
- Write stories (gated by HITL approval)
- Query velocity history
"""
from alfred.schemas.agent import BoardState, BoardStory


def get_board_state(org: str, project_number: int, token: str) -> BoardState:
    raise NotImplementedError


def create_story(org: str, project_number: int, story: BoardStory, token: str) -> str:
    raise NotImplementedError
```

**`src/alfred/tools/rag.py`**
```python
"""
RAG engine over the handover corpus.

Phase 4 implementation will:
- Index handover documents at section boundaries
- Embed chunks using a configurable embedding model
- Retrieve relevant chunks by semantic similarity
"""
from alfred.schemas.agent import RAGChunk


def index_corpus(corpus_path: str, index_path: str, embedding_model: str) -> int:
    raise NotImplementedError


def retrieve(query: str, index_path: str, top_k: int = 5) -> list[RAGChunk]:
    raise NotImplementedError
```

**`src/alfred/tools/llm.py`**
```python
"""
Provider-agnostic LLM adapter.

Phase 4 implementation will:
- Support Anthropic and OpenAI providers
- Return structured output validated against a Pydantic schema
- Log token usage and latency
"""
from pydantic import BaseModel
from typing import Type, TypeVar

T = TypeVar("T", bound=BaseModel)


def complete(prompt: str, output_schema: Type[T], provider: str, model: str) -> T:
    raise NotImplementedError
```

**`src/alfred/tools/persistence.py`**
```python
"""
SQLite operational bookkeeping.

Phase 4 implementation will:
- Store sprint metadata and velocity history
- Log agent invocation traces (input hash, output hash, tokens, latency)
- Record checkpoint evaluation history
"""
from alfred.schemas.agent import VelocityRecord


def record_velocity(db_path: str, record: VelocityRecord) -> None:
    raise NotImplementedError


def get_velocity_history(db_path: str, sprint_count: int) -> list[VelocityRecord]:
    raise NotImplementedError
```

### Verification

```bash
python -c "
from alfred.tools.github_api import get_board_state
from alfred.tools.rag import retrieve
from alfred.tools.llm import complete
from alfred.tools.persistence import get_velocity_history
print('all tool stubs importable')
"
```

**Commit message:** `phase3: task 3 — tool stubs`

---

## TASK 4 — Orchestrator Skeleton

**Goal:** Create `src/alfred/orchestrator.py` with the control flow skeleton. No agent calls are implemented — stubs are called. The structure must reflect the methodology: task iteration, checkpoint gates, document-mediated state.

### The skeleton must show

1. Iteration through `handover.tasks` in order
2. Agent dispatch based on task type (stub: `raise NotImplementedError` per agent)
3. Checkpoint gate: if task has checkpoints, call Quality Judge stub; branch on verdict
4. Verdict routing: `proceed` continues, `stop` raises `CheckpointHalt`, `escalate` raises `HumanEscalation`
5. Write results back to `handover` before proceeding

### Exceptions (define in `orchestrator.py`)

```python
class CheckpointHalt(Exception):
    """Raised when a checkpoint returns a STOP verdict."""

class HumanEscalation(Exception):
    """Raised when a checkpoint returns an ESCALATE verdict requiring human decision."""
```

### Function signature

```python
from alfred.schemas.handover import HandoverDocument
from alfred.schemas.config import AlfredConfig

def orchestrate(handover: HandoverDocument, config: AlfredConfig) -> HandoverDocument:
    """
    Execute a handover document.

    Iterates through tasks in order. For each task:
      1. Constructs agent input from HandoverDocument + tools
      2. Calls the appropriate agent
      3. Validates output against the agent's output schema
      4. If the task has checkpoints: calls Quality Judge
      5. Routes based on verdict (proceed / pivot / stop / escalate)
      6. Writes results back to HandoverDocument

    Returns the updated HandoverDocument with results filled in.
    Raises CheckpointHalt on STOP verdict.
    Raises HumanEscalation on ESCALATE verdict.
    """
    raise NotImplementedError
```

### Verification

```bash
python -c "
from alfred.orchestrator import orchestrate, CheckpointHalt, HumanEscalation
print('orchestrator importable')
"
```

**Commit message:** `phase3: task 4 — orchestrator skeleton`

---

## TASK 5 — API Skeleton

**Goal:** Create `src/alfred/api.py` with a FastAPI app and all five route definitions. No implementation — each handler raises `NotImplementedError`.

### Routes

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/generate` | Trigger handover generation from board state |
| `POST` | `/evaluate` | Evaluate a checkpoint (executor output + checkpoint definition) |
| `POST` | `/approve` | HITL approval gate — approve or reject a pending action |
| `POST` | `/retrospective` | Trigger retrospective analysis for a sprint |
| `GET` | `/dashboard` | Read-only sprint state, quality scores, velocity |

### Pattern

```python
from fastapi import FastAPI

app = FastAPI(title="Alfred")

@app.post("/generate")
def generate():
    raise NotImplementedError

# ... repeat for all routes
```

Do not add auth, middleware, CORS, or any configuration. That is Phase 7.

### Verification

```bash
python -c "from alfred.api import app; print('FastAPI app importable, routes:', [r.path for r in app.routes])"
```

**Commit message:** `phase3: task 5 — api skeleton`

---

## TASK 6 — Test Structure

**Goal:** Create the test directory structure with stub test files. Tests must be importable, must not fail on collection, and should skip rather than fail where no implementation exists.

### Directory structure

```
tests/
├── __init__.py
├── test_schemas/
│   ├── __init__.py
│   ├── test_handover.py      ← schema round-trip tests (stub)
│   ├── test_checkpoint.py    ← checkpoint evaluation tests (stub)
│   └── test_config.py        ← config validation tests (stub)
└── test_orchestrator.py      ← orchestrator control flow tests (stub)
```

### Stub pattern

```python
import pytest

@pytest.mark.skip(reason="Phase 6 — not yet implemented")
def test_placeholder():
    pass
```

### Verification

```bash
pytest tests/ -v 2>&1 | tail -10
# Expected: all tests skipped, zero failures
```

**Commit message:** `phase3: task 6 — test structure`

---

## TASK 7 — Handover Template

**Goal:** Create `configs/handover_template.md` — a blank handover template that conforms to the HandoverDocument schema structure. This is the canonical starting point for writing a new handover document.

### What the template must contain

- All required section headers matching the `render_markdown()` output format from `handover.py`
- Placeholder text (`<fill in>`, `TBD`) for every required field
- The five methodology properties listed in the CONTEXT block as a reminder
- Comment lines (HTML `<!-- -->`) explaining each section's purpose, which `from_markdown()` ignores

The template should be usable as: copy, fill in, validate via `alfred validate`.

### Verification

```bash
# Template must exist and be non-empty
wc -l configs/handover_template.md
```

**Commit message:** `phase3: task 7 — handover template`

---

## TASK 8 — Integration Validation

**Goal:** Verify that the Phase 3 scaffold meets all acceptance criteria defined in `docs/architecture.md` Section 7.

### Acceptance criteria (all must pass)

```bash
# 1. Package imports cleanly
python -c "import alfred; print('import alfred: ok')"

# 2. Schema imports
python -c "
from alfred.schemas.handover import HandoverDocument
from alfred.schemas.checkpoint import Checkpoint, create_checkpoint
from alfred.schemas.agent import PlannerInput, QualityJudgeOutput
from alfred.schemas.config import AlfredConfig
print('schema imports: ok')
"

# 3. Agent stubs importable
python -c "
from alfred.agents.planner import run_planner
from alfred.agents.story_generator import run_story_generator
from alfred.agents.quality_judge import run_quality_judge
from alfred.agents.retro_analyst import run_retro_analyst
print('agent stubs: ok')
"

# 4. Tool stubs importable
python -c "
from alfred.tools.github_api import get_board_state
from alfred.tools.rag import retrieve
from alfred.tools.llm import complete
from alfred.tools.persistence import get_velocity_history
print('tool stubs: ok')
"

# 5. Orchestrator importable
python -c "from alfred.orchestrator import orchestrate; print('orchestrator: ok')"

# 6. API importable
python -c "from alfred.api import app; print('api: ok')"

# 7. Tests collect without error
pytest tests/ --collect-only 2>&1 | tail -5

# 8. pip install still passes
pip install -e . --quiet && echo 'pip install: ok'
```

All eight checks must pass without error. Document any failures and their resolution in the inline post-mortem below.

**Commit message:** `phase3: task 8 — integration validation`

---

## WHAT NOT TO DO

1. **Do NOT write any business logic.** No LLM calls, no GitHub API calls, no database queries. Raise `NotImplementedError`.
2. **Do NOT modify Phase 2 schemas.** They are settled. If you find a schema gap during scaffolding, note it as a forward item for Phase 4 — do not backfill.
3. **Do NOT add FastAPI middleware, auth, CORS, or deployment config.** Phase 7.
4. **Do NOT write passing tests.** Test stubs only. Phase 6 implements the test suite.
5. **Do NOT skip the acceptance criteria check** (Task 8). The scaffold is not done until all eight checks pass.
6. **Do NOT implement `orchestrate()`.** The skeleton shows the control flow structure. The body raises `NotImplementedError`.
7. **Do NOT add the `evals/` directory** yet. It belongs in Phase 6.
8. **Do NOT reference any specific AI tool or vendor** in any file.

---

## POST-MORTEM (Phase 2)

**What worked:**
- Schema-first approach validated immediately: `from_markdown()` and `render_markdown()` patterns established before any agent or tool code was written
- Deferred import pattern (handover → checkpoint circular reference) resolved cleanly with `model_rebuild()`
- Phase 2 produced exactly 8 meaningful commits, one per task — clean history
- `pip install -e .` installs cleanly with all dependencies pinned; all schema imports verified

**What was harder than expected:**
- BOB_HANDOVER documents have significant structural variation (HO44 uses `### HARD RULES` not `## HARD RULES`; results docs have different structure from planning docs). `from_markdown()` needs to be permissive to handle the real corpus.
- Circular import between `handover.py` (needs `Checkpoint`) and `checkpoint.py` required the deferred import pattern. This is resolved and documented but is a fragility to watch in Phase 4.

**Forward plan for Phase 3:**
- Agent stubs must import from `schemas/agent.py` so that any schema change in Phase 4 is immediately visible as a type error in the stub
- The orchestrator skeleton is the highest-risk stub — it must structurally encode checkpoint-gated control flow or Phase 4 will inherit bad patterns
- Retroactive `from_markdown()` validation of this document (ALFRED_HANDOVER_2.md) is a Phase 4 task per Design Decision 9

**next_handover_id:** ALFRED_HANDOVER_3 (Phase 4: Core Implementation)
