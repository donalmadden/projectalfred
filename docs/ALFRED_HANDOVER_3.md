# Alfred's Handover Document #3 — Phase 4: Core Implementation

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_3
**date:** 2026-04-16
**author:** Donal
**previous_handover:** ALFRED_HANDOVER_2
**baseline_state:** Phase 3 complete (9 commits on `main`). Package scaffold in place: all four agent stubs, all four tool stubs, orchestrator skeleton, FastAPI skeleton with five routes, test directory with skip-placeholders, handover template. Every stub raises `NotImplementedError` and imports resolve against Phase 2 schemas. `pip install -e .` passes. Phase 4 not started.

**Reference Documents:**
- `~/code/projectalfred/docs/ALFRED_HANDOVER_2.md` — Phase 3 handover; defines the scaffold Phase 4 fills in
- `~/code/projectalfred/docs/architecture.md` — Full system architecture; Sections 1–5 define what Phase 4 must implement
- `~/code/projectalfred/CLAUDE.md` — Build rules and non-negotiable methodology properties
- `~/code/projectalfred/src/alfred/schemas/` — Agent input/output contracts Phase 4 must honour
- `~/code/projectalfred/configs/default.yaml` — System config; all runtime parameters live here
- `~/code/3b_EBD_MLOps/docs/BOB_HANDOVER_*.md` — Empirical corpus; read-only dogfood target

---

## WHAT EXISTS TODAY

### Git History — Phase 3 Complete (9 commits)

```
f33dd58  phase 3 complete
63a6aa3  phase3: task 8 — integration validation
76136b2  phase3: task 7 — handover template
644f892  phase3: task 6 — test structure
e234930  phase3: task 5 — api skeleton
6baa342  phase3: task 4 — orchestrator skeleton
fa5fafe  phase3: task 3 — tool stubs
957df40  phase3: task 2 — agent stubs
e15d294  phase3: task 1 — package directory structure
```

Baseline before Phase 3: commit `75cd96a` (Phase 2 handover 2). Phase 2 itself concluded at `cbb3340`.

### Files Phase 4 Fills In

| File | Current state | Phase 4 deliverable |
|---|---|---|
| `src/alfred/tools/persistence.py` | stub, `NotImplementedError` | SQLite-backed bookkeeping; schema bootstrap on first use |
| `src/alfred/tools/llm.py` | stub | Provider-agnostic structured-output `complete()` (Anthropic first; OpenAI via same interface) |
| `src/alfred/tools/rag.py` | stub | Section-boundary chunking, embeddings, top-k retrieval |
| `src/alfred/tools/github_api.py` | stub | GraphQL read of Projects V2 board state; create-story write path |
| `src/alfred/agents/quality_judge.py` | stub | Evaluates a checkpoint; produces a `Verdict` via decision table |
| `src/alfred/agents/planner.py` | stub | Drafts a `HandoverDocument` from board state + RAG context |
| `src/alfred/agents/story_generator.py` | stub | Produces validated `BoardStory` objects from a planner draft |
| `src/alfred/agents/retro_analyst.py` | stub | Read-only pattern extraction from completed sprint + history |
| `src/alfred/orchestrator.py` | skeleton | Full `orchestrate()`: task iteration, agent dispatch, checkpoint gate, verdict routing, handover write-back |
| `src/alfred/api.py` | 5 routes raising `NotImplementedError` | All five endpoints wired to the orchestrator + tools |

### Key Design Decisions Inherited (Do Not Revisit)

1. Hand-rolled orchestrator. No LangGraph/LangChain/CrewAI/AutoGen.
2. Functions only; no classes except Pydantic models and FastAPI routers.
3. State lives in the `HandoverDocument` on the filesystem. SQLite is bookkeeping only.
4. Schemas enforce contracts; validate at every boundary.
5. Provider-agnostic language; no AI tool attribution in any file.
6. RAG supplements, never replaces, the handover document.
7. Alfred drafts, humans approve.

---

## HARD RULES

1. **Work in `~/code/projectalfred`** only. `3b_EBD_MLOps` is read-only dogfood corpus.
2. **Functions only.** No classes except Pydantic models and FastAPI routers.
3. **All config via `configs/`**, never hardcoded. Secrets by env var name only.
4. **Pydantic validation at every boundary.** No `dict`-shaped agent outputs.
5. **One task = one commit.** Commit messages: `phase4: task N — description`.
6. **`pip install -e .` must pass at all times.** No new dependency without adding it to `pyproject.toml`.
7. **No new framework dependencies** for orchestration (rule 1 restated — this is the most likely rule to be tempted to break).
8. **No AI tool attribution** anywhere.
9. **The five methodology properties are non-negotiable.** Any implementation that hides state outside the `HandoverDocument`, that evaluates checkpoints with freeform LLM reasoning instead of the decision table, or that lets one agent call another directly, is wrong.
10. **Tests live alongside each implementation task.** Each task produces at least one real (non-skipped) test that exercises the new code path.

---

## WHAT THIS PHASE PRODUCES

- Four working tools with real implementations, tested in isolation
- Four working agents, each callable end-to-end with a mocked LLM
- A functioning `orchestrate()` that runs a complete handover through task iteration and checkpoint gates
- Five FastAPI endpoints wired to the orchestrator
- A first end-to-end dogfood run: feed a BOB handover through the system and produce a structured evaluation
- Real (non-skipped) tests for each tool and agent

Out of scope:
- Multi-agent critique loops, cost routing, HITL UI (Phase 5)
- Full test suite and evaluation harness (Phase 6)
- Docker, deployment config, auth (Phase 7)

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Persistence tool | `tools/persistence.py` + SQLite schema bootstrap + tests |  |
| 2 | LLM tool | `tools/llm.py` with Anthropic adapter + schema-validated output + tests |  |
| 3 | RAG tool | `tools/rag.py` with section-boundary chunking, embeddings, retrieval + tests |  |
| 4 | GitHub API tool | `tools/github_api.py` GraphQL read + create-story + tests | CHECKPOINT-1 |
| 5 | Quality Judge agent | `agents/quality_judge.py` decision-table evaluator + tests |  |
| 6 | Planner agent | `agents/planner.py` draft-handover generator + tests |  |
| 7 | Story Generator agent | `agents/story_generator.py` + tests |  |
| 8 | Retro Analyst agent | `agents/retro_analyst.py` + tests | CHECKPOINT-2 |
| 9 | Orchestrator | `orchestrator.py` full implementation + tests |  |
| 10 | API | `api.py` wired to orchestrator + tests |  |
| 11 | End-to-end dogfood | One BOB handover run end-to-end; results captured in post-mortem | CHECKPOINT-3 |

---

## TASK 1 — Persistence Tool

**Goal:** Replace `tools/persistence.py` stubs with a working SQLite-backed bookkeeping layer.

1. **Schema bootstrap** — on first call, create tables: `velocity`, `agent_invocations`, `checkpoint_history`. Idempotent.
2. **Implement `record_velocity(db_path, record)`** — insert/upsert by `sprint_number`.
3. **Implement `get_velocity_history(db_path, sprint_count)`** — return the most recent `sprint_count` records, ordered.
4. **Add `record_agent_invocation(...)` and `record_checkpoint(...)`** — minimal signatures in the module; orchestrator and agents use them in later tasks.
5. **Tests** — `tests/test_tools/test_persistence.py`: round-trip a velocity record, fetch history, verify idempotent bootstrap.

### Verification

```bash
pytest tests/test_tools/test_persistence.py -v
```

**Expected:** all tests pass; no skips.

**Commit message:** `phase4: task 1 — persistence tool`

---

## TASK 2 — LLM Tool

**Goal:** Provider-agnostic structured-output completion. First adapter: Anthropic. Interface must make adding a second provider a drop-in.

1. **Read provider/model from config** — do not hardcode. Respect `AlfredConfig.llm`.
2. **Implement `complete(prompt, output_schema, provider, model) -> T`** — returns an instance of `output_schema` (a Pydantic `BaseModel` subclass). Use the provider's structured-output / tool-use mechanism; validate before returning.
3. **Retry on schema-validation failure** — up to N attempts (N from config). If still failing, raise.
4. **Log token usage and latency** via `tools.persistence.record_agent_invocation`.
5. **Tests** — `tests/test_tools/test_llm.py`: use a mocked HTTP client; verify schema validation, retry, and logging.

### Verification

```bash
pytest tests/test_tools/test_llm.py -v
```

**Commit message:** `phase4: task 2 — llm tool`

---

## TASK 3 — RAG Tool

**Goal:** Index the handover corpus and retrieve relevant chunks.

1. **Chunk at section boundaries** (`##` headers). Each chunk carries `document_id`, `section_header`, `content`.
2. **Embed** using the model named in config. Persist the index under `index_path`.
3. **`retrieve(query, index_path, top_k)`** — semantic similarity; return `list[RAGChunk]` with `relevance_score`.
4. **Tests** — `tests/test_tools/test_rag.py`: index a small fixture corpus, retrieve against a known query, assert top-k ordering. Use a deterministic or mocked embedding.

### Verification

```bash
pytest tests/test_tools/test_rag.py -v
```

**Commit message:** `phase4: task 3 — rag tool`

---

## TASK 4 — GitHub API Tool

**Goal:** Projects V2 GraphQL adapter for reading board state and creating stories.

1. **`get_board_state(org, project_number, token) -> BoardState`** — one GraphQL query; map fields to `BoardState` / `BoardStory`.
2. **`create_story(org, project_number, story, token) -> str`** — returns new item id. Gated by HITL approval at the orchestrator layer; this function only does the write.
3. **Error handling** — raise on non-2xx; surface GraphQL errors clearly.
4. **Tests** — `tests/test_tools/test_github_api.py`: mock `httpx` client; verify request shape, response parsing, error propagation.

### Verification

```bash
pytest tests/test_tools/test_github_api.py -v
```

**Commit message:** `phase4: task 4 — github api tool`

### CHECKPOINT-1 — Tools Complete

**Question:** Do all four tools have real implementations with passing tests, and does the full tool surface import cleanly?

**Evidence required:** paste the output of:

```bash
pytest tests/test_tools/ -v
python -c "
from alfred.tools.persistence import record_velocity, get_velocity_history
from alfred.tools.llm import complete
from alfred.tools.rag import retrieve, index_corpus
from alfred.tools.github_api import get_board_state, create_story
print('tools surface ok')
"
```

| Observation | Likely call |
|---|---|
| All four tool test modules pass; surface imports cleanly | PROCEED |
| A tool interface needs adjustment but implementation is sound | PIVOT — adjust schema in agent.py, document, continue |
| A tool is blocked on an external dependency (API access, credentials) | ESCALATE |
| Tool tests fail or imports break | STOP — fix before continuing |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 5 — Quality Judge Agent

**Goal:** Evaluate a checkpoint against executor output. Produce a `Verdict` via the decision table — never via freeform reasoning.

1. **Read input** — `QualityJudgeInput` (checkpoint definition + executor output + handover context).
2. **Apply the decision table** — match observations against rows; return the matched `Verdict`. Fall through to `escalate` if no row matches.
3. **LLM is used only to classify observations** against the decision table's observation column, never to decide the verdict.
4. **Write result** — return `QualityJudgeOutput`; orchestrator records via `persistence.record_checkpoint`.
5. **Tests** — `tests/test_agents/test_quality_judge.py`: feed a canned checkpoint + output, mock the LLM classification, assert the verdict comes from the decision table.

### Verification

```bash
pytest tests/test_agents/test_quality_judge.py -v
```

**Commit message:** `phase4: task 5 — quality judge agent`

---

## TASK 6 — Planner Agent

**Goal:** Draft a `HandoverDocument` from current board state plus RAG context.

1. **Input** — `PlannerInput`: board state, RAG chunks, velocity history, any prior handover id.
2. **Build prompt** — structured prompt referencing methodology properties; ask for a draft handover matching `HandoverDocument` schema.
3. **Call `llm.complete(..., output_schema=PlannerOutput)`** — rely on schema validation + retry in the LLM tool.
4. **Never writes to the board.** Returns draft only.
5. **Tests** — `tests/test_agents/test_planner.py`: mock LLM; verify input is populated correctly and output validates.

### Verification

```bash
pytest tests/test_agents/test_planner.py -v
```

**Commit message:** `phase4: task 6 — planner agent`

---

## TASK 7 — Story Generator Agent

**Goal:** Produce validated `BoardStory` objects from a planner draft.

1. **Input** — `StoryGeneratorInput`: planner draft + board context.
2. **Output** — `StoryGeneratorOutput` with a `list[BoardStory]`; story points restricted to the `StoryPoint` literal set.
3. **Call `llm.complete(..., output_schema=StoryGeneratorOutput)`**.
4. **Tests** — mock LLM; verify schema conformance and story-point constraint.

### Verification

```bash
pytest tests/test_agents/test_story_generator.py -v
```

**Commit message:** `phase4: task 7 — story generator agent`

---

## TASK 8 — Retro Analyst Agent

**Goal:** Read-only pattern extraction from a completed sprint plus historical context.

1. **Input** — `RetroAnalystInput`: completed handover(s), velocity history, RAG chunks.
2. **Output** — `RetroAnalystOutput`: patterns, root causes, forward recommendations.
3. **No write operations.** Agent surface must not touch persistence or github_api.
4. **Tests** — mock LLM; assert output shape; assert no write-path tools are called (use a spy/mock).

### Verification

```bash
pytest tests/test_agents/test_retro_analyst.py -v
```

**Commit message:** `phase4: task 8 — retro analyst agent`

### CHECKPOINT-2 — Agents Complete

**Question:** Do all four agents run end-to-end with a mocked LLM and produce schema-valid output?

**Evidence required:** paste the output of:

```bash
pytest tests/test_agents/ -v
```

| Observation | Likely call |
|---|---|
| All agent test modules pass; output is schema-valid | PROCEED |
| A schema needs tightening (e.g. `StoryPoint` too permissive in practice) | PIVOT — note as forward item, adjust in task 9 if it blocks the orchestrator |
| An agent requires context the current schema doesn't expose | ESCALATE — schema change affects Phase 2 invariants |
| Agent tests fail | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 9 — Orchestrator

**Goal:** Implement `orchestrate(handover, config) -> HandoverDocument`. The skeleton from Phase 3 already encodes the control flow structurally; task 9 fills in the bodies.

1. **Iterate `handover.tasks` in order.**
2. **Dispatch** — pick the agent function based on task type; build agent input from handover + tools; call; validate output.
3. **Write back** — attach agent output to the task on the `HandoverDocument`.
4. **Checkpoint gate** — if the task has a checkpoint, call Quality Judge; persist via `record_checkpoint`; route on verdict.
5. **Verdict routing** — `proceed` continues; `pivot` logs and continues; `stop` raises `CheckpointHalt`; `escalate` raises `HumanEscalation`.
6. **Statelessness** — the only persistent state is the `HandoverDocument` itself and SQLite bookkeeping. The orchestrator function must be re-runnable from a partially-completed handover.
7. **Tests** — `tests/test_orchestrator.py`: feed a synthetic handover with a checkpoint that triggers each verdict; verify routing; verify writes land on the handover object.

### Verification

```bash
pytest tests/test_orchestrator.py -v
```

**Commit message:** `phase4: task 9 — orchestrator`

---

## TASK 10 — API

**Goal:** Wire the five endpoints to the orchestrator and tools. Each endpoint deserializes input, calls the relevant function, returns a schema-validated response.

1. **`POST /generate`** — loads board state via `github_api`, calls `planner` + `story_generator`; returns draft `HandoverDocument`.
2. **`POST /evaluate`** — accepts a checkpoint + executor output; calls `quality_judge`; returns `CheckpointResult`.
3. **`POST /approve`** — HITL gate: flips a pending action's approval flag; persists via `persistence`.
4. **`POST /retrospective`** — calls `retro_analyst`; returns report.
5. **`GET /dashboard`** — read-only: sprint state, recent checkpoint outcomes, velocity history.
6. **Tests** — `tests/test_api.py`: FastAPI `TestClient`; mock the orchestrator layer; verify status codes, request/response shapes.

### Verification

```bash
pytest tests/test_api.py -v
```

**Commit message:** `phase4: task 10 — api`

---

## TASK 11 — End-to-End Dogfood

**Goal:** Run one real BOB handover end-to-end through the system. No mocks below the LLM boundary.

1. **Pick a target** — one completed BOB_HANDOVER from `~/code/3b_EBD_MLOps/docs/`. Index a small corpus slice via `rag.index_corpus`.
2. **Run `/evaluate`** against one checkpoint from that handover.
3. **Capture** — the checkpoint result, the agent invocation trace, any schema validation failures. Save to `data/dogfood/handover3_run1.json`.
4. **Document findings** in this file's post-mortem: what worked, what broke, where the schemas proved too tight or too loose.

### Verification

```bash
ls -la data/dogfood/
cat data/dogfood/handover3_run1.json | head -50
```

**Commit message:** `phase4: task 11 — end-to-end dogfood`

### CHECKPOINT-3 — Phase 4 Acceptance

**Question:** Does the system run end-to-end against a real handover and produce a schema-valid checkpoint result?

**Evidence required:** paste:
- `pytest -v` full output (all tests pass, none skip except the Phase 6 placeholders)
- Contents of `data/dogfood/handover3_run1.json`
- The verdict and decision-table row that matched

| Observation | Likely call |
|---|---|
| End-to-end run succeeds; verdict comes from decision table; schemas hold | PROCEED — Phase 4 complete; write next handover |
| Run succeeds but verdict logic used LLM reasoning instead of the table | STOP — methodology violation; rework task 5 |
| Schemas rejected the real handover | PIVOT — document required schema changes as a Phase 5 forward item |
| Run failed on infrastructure (API key, rate limit) | ESCALATE |

**STOP HERE.** Wait for direction before writing the Phase 5 handover.

---

## WHAT NOT TO DO

1. **Do NOT introduce LangChain, LangGraph, CrewAI, AutoGen** or any other orchestration framework.
2. **Do NOT let agents call other agents directly.** All composition goes through the orchestrator.
3. **Do NOT evaluate checkpoints with freeform LLM reasoning.** The decision table is the verdict source; the LLM only classifies observations.
4. **Do NOT persist state outside the `HandoverDocument` + SQLite bookkeeping.** No caches, no global variables, no hidden queues.
5. **Do NOT hardcode provider, model, or prompts.** Config-driven.
6. **Do NOT skip tests** "because the real thing is tested in task 11". Each task ships its own tests.
7. **Do NOT expand the API surface** beyond the five routes.
8. **Do NOT write to the GitHub board without HITL approval.** `create_story` is gated at the orchestrator layer.

---

## POST-MORTEM

**Dogfood run:** `data/dogfood/handover3_run1.json`
**Target:** BOB_HANDOVER_40, HO40-CHECKPOINT-1 (environment + data audit gate)
**Provider/model:** openai / gpt-4o-mini
**Verdict:** `proceed` — quality score 1.0, no HITL escalation, 2.3s end-to-end

**What worked:**
- Full pipeline executed without mocks: RAG indexing → chunk retrieval → quality judge → structured output → persistence
- Decision-table verdict routing correct: LLM classified observation index 0 (`proceed`), verdict looked up deterministically
- OpenAI structured-output adapter (`json_schema` response format) worked first time — no schema validation retries
- RAG retrieved 3 relevant chunks from the 15-chunk HO40 corpus slice in under 1s (post-model-load)
- SQLite persistence wrote the agent invocation trace to `data/dogfood/alfred_dogfood.db` without error

**What failed / findings:**
- `methodology_compliance` flags properties 3 and 4 as `False` — expected: the keyword scan in `_check_methodology_compliance` looks for literal methodology prose in the handover markdown, not executor console output. Scope is correct; keyword list needs review in Phase 5.
- `sentence-transformers` and `openai` were not installed in the venv at task-11 start — declared in `pyproject.toml` but `pip install -e .` had not been re-run after they were added. Fix: CI should gate on `pip install -e .[dev]`.
- Embedder model reloads on every `retrieve()` call (no process-level cache). Acceptable for CLI use; Phase 5 should cache at process level.

**Forward plan:**
- Phase 5: add embedder caching to `rag.py` to avoid double model load per run
- Phase 5: revisit `_check_methodology_compliance` — scope keyword scan to handover markdown only, not executor output
- Phase 6 CI: add `pip install -e .[dev]` gate to ensure all declared deps are present before tests run

**next_handover_id:** ALFRED_HANDOVER_4 (Phase 5: Stretch Enhancements)
