# Alfred's Handover Document #1 — Phase 2 Architecture

## CONTEXT — READ THIS FIRST

**Document Date:** 2026-04-15
**Previous Handover:** None. This is the first.
**Project:** ProjectAlfred — document-mediated, checkpoint-gated agent coordination for software teams
**Repo:** `~/code/projectalfred` (GitHub: `donalmadden/projectalfred`, public, Apache 2.0)
**Current State:** Phase 1 complete (3 commits on `main`). Phase 2 not started.
**Reference Documents:**
- `~/code/projectalfred/README.md` — methodology-first project framing
- `~/code/projectalfred/CLAUDE.md` — build rules and non-negotiable methodology properties
- `~/code/projectalfred/.gitignore` — Python + data/artifact exclusions
- `~/code/3b_EBD_MLOps/docs/BOB_HANDOVER_*.md` — the 37+ handover documents that ARE the empirical foundation
- `~/code/3b_EBD_MLOps/docs/builder_prompt.md` — the origin prompt that defined the 10 capability layers, 5 stretch enhancements, 8 build phases, target repo structure, and coding standards. **The canonical checklist for what "done" looks like.** See [Builder Prompt Traceability](#builder-prompt-traceability) below.
- `StigmergicSoftwareEngineeringBrainstorm.pdf` — 32-page literature review positioning the BOB methodology
**Author:** Donal (Project Lead)

---

## WHAT THIS PROJECT IS

Alfred operationalises a specific methodology for human+AI software development that Donal invented and refined across 37+ handover documents in the `3b_EBD_MLOps` project. The methodology has five non-negotiable properties:

1. **Document as protocol** — the handover document is the control surface of the system, not a side-channel. Never replace it with hidden state.
2. **Checkpoint-gated execution** — deterministic decision tables at defined gates. No emergent evaluation.
3. **Reasoning/execution isolation** — the executor never makes strategic decisions; the reviewer never executes code. Strict epistemic separation.
4. **Inline post-mortem → forward plan** — failure analysis is embedded in the execution artifact, not a separate process.
5. **Statelessness by design** — each session cold-starts from the document. Context loss is a feature.

These five properties are the reason this project exists. Every design decision in Alfred must preserve all five. If a proposed feature would violate any property, the feature is wrong, not the property.

### Formal Classification

A literature review (GPT 5.3, March 2026, captured in `StigmergicSoftwareEngineeringBrainstorm.pdf`) positioned the methodology against 2020-2025 literature and produced this formal classification:

> **"Document-externalized, checkpoint-gated, mixed-initiative planner/reviewer-executor architecture with role-isolated agents"**

Five novelty claims (all validated against literature):
1. Document as *protocol* (not just memory) — the control surface of the system
2. Checkpoint-gated execution with explicit decision tables
3. Hard separation of reasoning vs execution *with epistemic isolation*
4. Integrated post-mortem → forward-plan loop (inline causal learning)
5. Deliberate rejection of agent autonomy as a design goal

Novelty rating: **7/10** (systems/architecture track), **8.5-9/10** (AI teaming/developer workflow).

Key insight from the review: *"You are not trying to make agents fit into AI-native workflows. You are making agents conform to existing software team coordination primitives."*

Closest analogues in the literature:
- Plan-and-Act (2025) — planner/executor separation, but no document externalisation
- MetaGPT (ICLR 2024) — SOP-encoded multi-agent workflows, but agent-native SOPs
- MAGIS (NeurIPS 2024) — manager/developer/QA decomposition, but no checkpoint gating
- CoALA (TMLR 2024) — cognitive architecture for language agents, theoretical not operational
- Meeting Bridges / boundary objects (CSCW) — document-as-coordination-artifact, but not agent-mediated

None of these combine all five properties. That is the novelty.

### What Alfred Does

Alfred is NOT a generic AI Scrum Master. Alfred is a system that:

1. **Validates** handover documents against the methodology (completeness, decision tables, checkpoint definitions)
2. **Generates** handover drafts from board state, git history, and prior handovers (human approves before it becomes protocol)
3. **Evaluates** checkpoint gates against actual outputs (pass/fail), routing decisions to the appropriate actor
4. **Retrieves** across handover history via RAG (cross-document search without replacing individual documents as the interface)
5. **Manages** sprint lifecycle through GitHub Projects V2 (story generation, board state, velocity tracking)

The metaphor is Batman's Alfred — knows the mission, manages logistics, never upstages the human. The human is always the decision-maker.

### What Alfred Does NOT Do

- Replace handover documents with hidden state (vector DBs, chat history, agent memory)
- Make strategic decisions — Alfred drafts, humans approve
- Execute code or make commits — Alfred coordinates, humans and executors act
- Autonomously decide when to stop — checkpoint gates are explicit and deterministic

---

## WHAT EXISTS TODAY

### Git History (3 commits, `main`)

```
92a38e2 phase1: reframe — Alfred operationalises document-mediated coordination, not just Scrum management
0f63080 Fix project name formatting in README
becd8eb phase1: project framing — ProjectAlfred agentic Scrum Master
```

### Files

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | Methodology-first project description, agent architecture, capability contract, evaluation strategy, academic context | Complete |
| `CLAUDE.md` | Build rules, 5 non-negotiable properties, critical rules, tech stack, phase list, dogfood reference | Complete |
| `.gitignore` | Python, data/raw, data/processed, artifacts, vector stores, logs, IDE, OS | Complete |

No code exists. No directory structure beyond root. No `pyproject.toml`. No configs. No schemas.

### Tech Stack (decided, not yet implemented)

- **Python** — functions only, no classes except Pydantic models and FastAPI routers
- **FastAPI** — HTTP interface
- **Pydantic** — all schemas and config (inputs, outputs, state, agent boundaries)
- **SQLite** — state persistence
- **GitHub Projects V2 GraphQL API** — board integration
- **LLM API** — provider-agnostic, configured via `configs/`

### Dogfood

First production use case: `3b_EBD_MLOps`. The 37+ `BOB_HANDOVER_*.md` documents in that repo are:
- The empirical foundation for this methodology
- The initial RAG corpus for cross-document retrieval
- The test fixtures for handover validation
- The quality benchmark (see `COGNIMANEU/pilot01-development#20`)

---

## DESIGN DECISIONS ALREADY MADE

These were decided during Phase 1 and are not revisitable.

### 1. Alfred formalises the methodology, it doesn't replace it

A brainstorm explored 5 ideas for improving token efficiency:
- **Idea 1 (structured front-matter):** KEPT — Pydantic-parseable YAML front-matter on handover docs
- **Idea 2 (dual-layer docs):** KEPT PARTIALLY — machine-parseable metadata + human-readable narrative
- **Idea 3 (diff against persistent state):** KILLED — destroys self-containment (property 5)
- **Idea 4 (agent self-briefing):** FLAGGED DANGEROUS — replaces document with agent interpretation (violates property 1)
- **Idea 5 (RAG over corpus):** KEPT — cross-document retrieval supplements individual documents

The synthesis: **RAG supplements, never replaces.** RAG indexes handover history for cross-document retrieval, but the individual handover document remains the interface for any single session.

### 2. No AI tool attribution

Never reference any specific AI tool or vendor in any user-facing file (README, docs, comments, commit messages, PR descriptions). Use provider-agnostic language throughout ("LLM API", "language model"). This is enforced in `CLAUDE.md`.

### 3. Agent Architecture (sketched, needs formalisation)

| Agent | Responsibility | Constraint |
|---|---|---|
| **Planner** | Sprint planning, capacity, priority, handover drafting | Never executes tasks |
| **Story Generator** | RAG-powered story creation against quality rubric | Output validated before board write |
| **Quality Judge** | Handover validation, checkpoint evaluation, HITL routing | Never modifies artifacts |
| **Retrospective Analyst** | Pattern extraction, velocity analysis, post-mortem synthesis | Read-only across handover corpus |

These four agents enforce property 3 (reasoning/execution isolation). The Planner and Story Generator are reasoning-side. The Quality Judge is the checkpoint gate. The Retrospective Analyst is read-only pattern extraction.

### 4. Evaluation Strategy (designed, not yet implemented)

Five metrics:
- **Error propagation rate** — does the system continue after a detectable failure?
- **Checkpoint compliance** — are decision tables correctly evaluated?
- **Reproducibility score** — variance across repeated runs of the same task
- **State recoverability** — can a fresh agent resume from mid-task using only the document?
- **Control violations** — actions taken outside intended scope

Ablation variants: no checkpoints, no decision tables, no post-mortem, shared context.

### 5. Build Phases

| Phase | Name | Status |
|---|---|---|
| 1 | Project framing | **Complete** |
| 2 | Architecture | **Next** |
| 3 | Repository scaffold | Planned |
| 4 | Core implementation | Planned |
| 5 | Stretch enhancements | Planned |
| 6 | Evaluations and tests | Planned |
| 7 | Developer experience and deployment | Planned |
| 8 | Portfolio hardening | Planned |

### 6. Capability Layers (from builder prompt)

| Layer | Phase |
|---|---|
| Purpose and business framing | Phase 1 — done |
| Orchestration and agentic control flow | Phase 2 |
| Tool integration (GitHub Projects V2 API) | Phase 4 |
| Retrieval / RAG (over handover corpus) | Phase 4 |
| State / memory (document-mediated, not hidden) | Phase 4 |
| Evaluation / QA | Phase 6 |
| Observability / tracing | Phase 4 |
| Guardrails / robustness | Phase 4 |
| Deployment / runtime | Phase 7 |
| Enterprise readiness / governance | Phase 7 |

### 7. Stretch Enhancements

| Enhancement | Phase |
|---|---|
| Multi-agent coordination (Planner / Generator / Judge / Retro) | Phase 5 |
| Self-evaluation / critique loop (handover quality validation) | Phase 5 |
| Cost-aware model routing (cheap classifier, strong generator) | Phase 5 |
| Human-in-the-loop approval (checkpoint gating before board write) | Phase 5 |
| Live dashboard (sprint state, agent traces, quality scores) | Phase 5 |

### 8. Builder Prompt Traceability

The origin prompt (`~/code/3b_EBD_MLOps/docs/builder_prompt.md`) defines what "done" looks like for the entire project. It was written as a generic agentic AI showcase brief; Alfred adapts it to the specific methodology. The table below maps every builder prompt requirement to where it lands in Alfred's phases, noting adaptations.

**Capability Contract (builder prompt section "Capability Contract"):**

| # | Builder Prompt Requirement | Alfred Phase | Adaptation |
|---|---|---|---|
| 1 | Purpose — define problem, user, value; create `/docs/purpose.md` | Phase 1 (done) | `README.md` serves as purpose doc; no separate `purpose.md` needed |
| 2 | Orchestration — explicit workflow (graph/state machine), no hidden control flow | Phase 2 (this handover, Tasks 5-6) | Hand-rolled orchestrator, not a framework. Document-mediated state, not a state machine. |
| 3 | Tool Integration — >=2 tools, at least 1 LLM-driven tool call path | Phase 4 | GitHub Projects V2 API + RAG + LLM adapter. All LLM-driven. |
| 4 | RAG — ingestion + retrieval pipeline, configurable backend | Phase 4 | Handover corpus as RAG source. Section-boundary chunking. |
| 5 | State / Memory — explicit state object, persistence + replay | Phase 4 | Handover document IS the state object. SQLite for operational bookkeeping only. |
| 6 | Evals — `/evals/`, automated evaluation script | Phase 6 | `evals/` directory with 5 metrics + 4 ablation variants. Feeds the research paper. |
| 7 | Observability — structured logs, trace/run IDs | Phase 4 | Agent invocation traces: input hash, output hash, tokens, latency, checkpoint verdicts. |
| 8 | Guardrails — validation + retries, schema enforcement | Phase 4 | Pydantic schema enforcement at agent boundaries. Agent output cannot exceed contract. |
| 9 | Deployment — CLI or API, Dockerfile | Phase 7 | CLI (`alfred validate/generate/evaluate`) + FastAPI + Docker. |
| 10 | Enterprise Concerns — config separation, secrets handling | Phase 7 | Secrets by env var name only (never stored). Config in `configs/`. |

**Stretch Enhancements (builder prompt section "Mandatory Show-Off Enhancements", renamed "Stretch"):**

| Builder Prompt Requirement | Alfred Phase | Adaptation |
|---|---|---|
| Multi-Agent System — meaningful roles (planner/executor/critic) | Phase 5 | Planner / Story Generator / Quality Judge / Retro Analyst. Executor is external (human or Bob). |
| Self-Critique Loop — bounded reflection step | Phase 5 | Quality Judge validates handover drafts against the 5 methodology properties. |
| Cost-Aware Routing — model or strategy routing layer | Phase 5 | Cheap model for triage, strong model for generation. Task-type routing. |
| Human-in-the-Loop — approval checkpoint | Phase 5 | `escalate` checkpoint verdict + FastAPI approval endpoint. Already a core methodology property. |
| Dashboard — lightweight visibility | Phase 5 | Read-only web UI. Sprint state, agent traces, quality scores, velocity. Reads SQLite, not live APIs. |

**Target Repo Structure (builder prompt section "Repository Structure"):**

| Builder Prompt Directory | Alfred Equivalent | Phase |
|---|---|---|
| `src/` | `src/alfred/` | Phase 3 |
| `tests/` | `tests/` | Phase 3 (structure), Phase 6 (content) |
| `evals/` | `evals/` | Phase 6 — **not currently in Phase 3 scaffold spec; add it** |
| `docs/` | `docs/` | Phase 2 onwards |
| `configs/` | `configs/` | Phase 2 (Task 4) |
| `tools/` | `src/alfred/tools/` | Phase 3 — nested under `src/`, not top-level |
| `rag/` | `src/alfred/tools/rag.py` | Phase 4 — module not directory (until complexity warrants splitting) |
| `dashboard/` | `src/alfred/dashboard/` or `dashboard/` | Phase 5 — **not currently in Phase 3 scaffold spec; add it when Phase 5 is planned** |
| `scripts/` | `scripts/` | As needed — **not currently in scaffold spec; add if one-shot diagnostics arise** |
| `README.md` | `README.md` | Phase 1 (done) |
| `pyproject.toml` | `pyproject.toml` | Phase 2 (Task 8) |
| `Dockerfile` | `Dockerfile` | Phase 7 |
| `.env.example` | `.env.example` | Phase 7 — **not currently mentioned; add it** |

**Coding Standards (builder prompt section "Coding Standards"):** Python, typed where practical, Pydantic for schemas, modular design, no unnecessary abstraction, clear naming. All adopted. Alfred adds: functions only (no classes except Pydantic models), no AI tool attribution.

**Behaviour Rules (builder prompt section "Behaviour Rules"):** Do not build a toy chatbot. Do not hide complexity. Do not over-engineer without purpose. Do not skip evals or observability. Always favour inspectability. All adopted.

**Gaps identified:** The Phase 3 scaffold spec (Task 7) should be updated to include `evals/` and `.env.example`. The `dashboard/` and `scripts/` directories can wait until their respective phases.

---

## HARD RULES

1. **Work in `~/code/projectalfred`.** This is a standalone repo. Do not modify `3b_EBD_MLOps`.
2. **Functions only.** No classes except Pydantic models and FastAPI routers.
3. **Pydantic schemas for everything.** All agent inputs/outputs, all config, all state.
4. **Never hardcode.** All parameters in `configs/`.
5. **One task = one commit.** Commit messages: `phase2: task N — description`.
6. **No Docker yet.** Local venv first. Containerise in Phase 7.
7. **No AI tool attribution.** Never reference any specific AI tool or vendor in any user-facing file.
8. **The five methodology properties are non-negotiable.** If a design decision would violate any of them, the decision is wrong.
9. **RAG supplements, never replaces.** The individual handover document remains the interface.
10. **Alfred drafts, humans approve.** No autonomous write to production state without human gate.
11. **`pyproject.toml` is the single source of truth** for dependencies. Not `requirements.txt`.
12. **If anything is unclear, STOP and ask Donal.**

---

## WHAT PHASE 2 PRODUCES

By the end of Phase 2 you will have:

- `docs/architecture.md` — the system architecture document covering all 7 deliverables below
- `src/alfred/schemas/handover.py` — the Handover Pydantic model (THE spine of the system)
- `src/alfred/schemas/checkpoint.py` — Checkpoint gate and decision table schemas
- `src/alfred/schemas/agent.py` — agent input/output boundary schemas (per agent)
- `src/alfred/schemas/config.py` — system configuration schema
- `configs/default.yaml` — default configuration file validated against config schema
- `pyproject.toml` — project metadata and dependencies

You will **not**:
- Write any business logic, agent code, or API endpoints
- Set up FastAPI, SQLite, or any runtime infrastructure
- Write tests (Phase 6) or deployment config (Phase 7)
- Implement RAG, GitHub API integration, or LLM calls
- Create a working system — Phase 2 is architecture and schemas only

---

## THE CENTRAL ARCHITECTURAL QUESTION

**What is the Handover schema?**

That Pydantic model is the spine of the entire system. Every agent reads from it, writes to it, or validates against it. The schema must:

1. **Be self-contained** (property 5) — a fresh agent can reconstruct full context from one document
2. **Separate reasoning from execution** (property 3) — distinct sections for plan vs. results
3. **Embed checkpoints** (property 2) — decision tables with explicit pass/fail criteria
4. **Include post-mortem → forward plan** (property 4) — failure analysis feeds next iteration
5. **Be human-readable** (property 1) — renders as clean markdown, not just machine state

The schema must bridge two worlds: structured enough for agents to parse deterministically, narrative enough for humans to read and approve. This is the hard design problem.

---

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Design the Handover schema | `src/alfred/schemas/handover.py` |
| 2 | Design the Checkpoint and Decision Table schemas | `src/alfred/schemas/checkpoint.py` |
| 3 | Design agent boundary schemas | `src/alfred/schemas/agent.py` |
| 4 | Design system config schema | `src/alfred/schemas/config.py` + `configs/default.yaml` |
| 5 | Define orchestration style and data flow | `docs/architecture.md` (sections 1-3) |
| 6 | Define state flow and agent interaction model | `docs/architecture.md` (sections 4-5) |
| 7 | Define technical risks and Phase 3 scaffold spec | `docs/architecture.md` (sections 6-7) |
| 8 | Create `pyproject.toml` | `pyproject.toml` |

---

## TASK 1 — Design the Handover Schema

**Goal:** Define the Pydantic model that represents a single handover document. This is the most important artifact in the entire project.

### Requirements

The schema must represent the structure observed in the 37+ BOB_HANDOVER documents. Study at least 5 handovers (`BOB_HANDOVER_36.md`, `BOB_HANDOVER_37.md`, `BOB_HANDOVER_44.md` are good exemplars) and extract the recurring structure:

1. **Front-matter / metadata**: document ID, date, author, previous handover reference, baseline state, reference documents list
2. **Context block**: what the reader must know before touching anything — current state, key findings, why this task matters
3. **Task list**: numbered tasks with deliverables, each self-contained
4. **Per-task specification**: goal statement, step-by-step changes, verification commands, commit message, expected outputs
5. **Checkpoints**: explicit decision points with pass/fail criteria and routing (proceed / pivot / stop / escalate)
6. **Hard rules**: constraints the executor must not violate
7. **Anti-patterns**: "WHAT NOT TO DO" section
8. **Post-mortem section** (populated after execution): what happened, what was learned, what feeds forward

### Schema Design Principles

- Use `Optional` fields for sections populated after execution (post-mortem, checkpoint results)
- Use `Literal` types for enums (checkpoint verdict: `"proceed" | "pivot" | "stop" | "escalate"`)
- The schema must serialise to YAML front-matter + markdown body (not just JSON)
- Include a `render_markdown()` method that produces human-readable output matching BOB_HANDOVER style
- Include a `from_markdown()` classmethod that parses an existing handover document back into the schema
- Version the schema (`schema_version: str` field) so future changes are backwards-compatible

### What the model should look like (sketch, not prescription)

```python
class HandoverDocument(BaseModel):
    schema_version: str = "1.0"
    id: str                           # "ALFRED_HANDOVER_1"
    date: date
    author: str
    previous_handover: Optional[str]  # ID of predecessor
    baseline_state: str               # human-readable summary
    reference_documents: list[str]
    
    context: HandoverContext           # the "READ THIS FIRST" block
    hard_rules: list[str]
    tasks: list[HandoverTask]
    anti_patterns: list[str]          # "WHAT NOT TO DO"
    
    # Populated after execution
    post_mortem: Optional[PostMortem]
    next_handover_id: Optional[str]
```

The exact field names, nesting, and types are for you to determine by studying the actual handover documents. The sketch above is directional, not prescriptive. The key constraint is: **a round-trip `from_markdown() → render_markdown()` must produce output that a human would recognise as a valid BOB_HANDOVER document.**

### File location

```
src/alfred/schemas/handover.py
```

Create the directory structure `src/alfred/schemas/` with `__init__.py` files.

### Verification

```bash
cd ~/code/projectalfred
python -c "
from alfred.schemas.handover import HandoverDocument
# Should import without error
print('HandoverDocument fields:', list(HandoverDocument.model_fields.keys()))
"
```

**Commit message:** `phase2: task 1 — handover document schema`

---

## TASK 2 — Design the Checkpoint and Decision Table Schemas

**Goal:** Define the schemas that represent checkpoint gates and their decision tables.

### What checkpoints look like in practice

From `BOB_HANDOVER_44.md`:
- CHECKPOINT-1 decides "whether HO41 was even trained on what it claimed"
- CHECKPOINT-3 decides "whether the free localizer is viable" → triggered a pivot
- CHECKPOINT-5 decides "how much of 96.62% was classification vs localization"

From `BOB_HANDOVER_37.md`:
- Task 0 has an implicit checkpoint: "balanced accuracy should return to approximately 57%"
- Task 3 has an explicit verdict table mapping test balanced accuracy ranges to decisions

A checkpoint has:
1. **Gate ID** — ties to a specific task
2. **Question** — what the checkpoint decides (one sentence)
3. **Evidence required** — what the executor must paste (console output, metrics, table)
4. **Decision table** — mapping from observed evidence to verdict
5. **Verdict** — one of: `proceed`, `pivot`, `stop`, `escalate`
6. **Reasoning** — why this verdict (populated after evaluation)

### Schema Design Principles

- Decision tables are explicit: `if metric > X then proceed, elif metric < Y then revert`
- No fuzzy evaluation — the checkpoint either passes or it doesn't
- The `escalate` verdict means "a human must decide" — this is property 2 in action
- Checkpoints are first-class objects, not afterthoughts embedded in task prose

### File location

```
src/alfred/schemas/checkpoint.py
```

### Verification

```bash
cd ~/code/projectalfred
python -c "
from alfred.schemas.checkpoint import Checkpoint, DecisionTable, Verdict
print('Verdict options:', list(Verdict.__args__))
# Should show: ['proceed', 'pivot', 'stop', 'escalate']
"
```

**Commit message:** `phase2: task 2 — checkpoint and decision table schemas`

---

## TASK 3 — Design Agent Boundary Schemas

**Goal:** Define Pydantic schemas that formalise the input/output contract for each of the four agents.

### Agent contracts

Each agent has:
- **Input schema** — what it receives (subset of system state it is allowed to see)
- **Output schema** — what it produces (and nothing else)
- **Constraint** — what it is forbidden from doing (enforced by the schema, not by trust)

| Agent | Reads | Writes | Forbidden |
|---|---|---|---|
| **Planner** | Board state, velocity history, prior handovers (via RAG), current handover context | Draft handover document, sprint plan, task decomposition | Executing tasks, modifying code, writing to board without approval |
| **Story Generator** | Handover corpus (RAG), quality rubric, board state | Draft stories with acceptance criteria | Writing stories to board without validation, skipping quality rubric |
| **Quality Judge** | Handover document, checkpoint definitions, executor output | Checkpoint verdicts, validation reports, HITL escalation flags | Modifying handover documents, executing code, overriding human decisions |
| **Retrospective Analyst** | Full handover corpus (read-only), metrics history, velocity data | Pattern reports, trend analysis, retrospective summaries | Modifying any document, any write operation |

Property 3 (reasoning/execution isolation) means these boundaries are hard, not advisory. The schema should make it structurally impossible for an agent to produce output outside its contract.

### File location

```
src/alfred/schemas/agent.py
```

### Verification

```bash
cd ~/code/projectalfred
python -c "
from alfred.schemas.agent import (
    PlannerInput, PlannerOutput,
    StoryGeneratorInput, StoryGeneratorOutput,
    QualityJudgeInput, QualityJudgeOutput,
    RetroAnalystInput, RetroAnalystOutput,
)
print('All agent schemas importable')
"
```

**Commit message:** `phase2: task 3 — agent boundary schemas`

---

## TASK 4 — Design System Config Schema

**Goal:** Define the Pydantic model for system configuration and write the default config file.

### What needs to be configurable

```yaml
# LLM provider (provider-agnostic)
llm:
  provider: "anthropic"     # or "openai", "local", etc.
  model: "..."
  temperature: 0.0          # deterministic by default (property 2)
  max_tokens: 4096

# Cost routing (stretch enhancement — Phase 5)
cost_routing:
  enabled: false
  classifier_model: "..."   # cheap model for triage
  generator_model: "..."    # strong model for generation

# GitHub Projects V2
github:
  org: "..."
  project_number: 0
  token_env_var: "GITHUB_TOKEN"  # never store the token itself

# RAG
rag:
  corpus_path: ""            # path to handover document directory
  chunk_size: 1000
  chunk_overlap: 200
  embedding_model: "..."

# SQLite
database:
  path: "data/alfred.db"

# Handover
handover:
  schema_version: "1.0"
  template_path: "configs/handover_template.md"

# Agents
agents:
  planner:
    enabled: true
  story_generator:
    enabled: true
  quality_judge:
    enabled: true
  retro_analyst:
    enabled: true
```

### Schema Design Principles

- Every field must have a sensible default or be explicitly required
- Secrets (API keys, tokens) are referenced by environment variable name, never stored in config
- The config schema validates exhaustively — invalid config fails fast at startup, not at runtime
- Provider-agnostic LLM config: the `provider` field selects the adapter, not the API shape

### File locations

```
src/alfred/schemas/config.py    # Pydantic model
configs/default.yaml             # Default configuration
```

### Verification

```bash
cd ~/code/projectalfred
python -c "
import yaml
from alfred.schemas.config import AlfredConfig
with open('configs/default.yaml') as f:
    raw = yaml.safe_load(f)
config = AlfredConfig(**raw)
print('Config loaded:', config.model_dump_json(indent=2)[:200])
"
```

**Commit message:** `phase2: task 4 — system config schema and default config`

---

## TASK 5 — Define Orchestration Style and Data Flow

**Goal:** Write the first three sections of `docs/architecture.md`.

### Section 1: System Architecture

Draw the component diagram (as ASCII art or mermaid — not an image file):
- **API layer** (FastAPI) — HTTP endpoints for triggering workflows, HITL approval, dashboard
- **Orchestrator** — routes work to agents, enforces checkpoint gates, manages handover lifecycle
- **Agent layer** — four agents with isolated input/output contracts
- **Tool layer** — GitHub API adapter, RAG engine, SQLite persistence, LLM adapter
- **Document layer** — handover documents on filesystem (the protocol, property 1)

### Section 2: Orchestration Style

**Hand-rolled, not framework.** Justify this decision:
- LangGraph/CrewAI/AutoGen optimise for agent autonomy — Alfred deliberately rejects autonomy (property 5 of the methodology)
- Checkpoint gates require deterministic control flow that framework "tool-calling loops" cannot guarantee
- The orchestration logic is simple (linear task list with gate checks) — a framework would add complexity without benefit
- FastAPI + Pydantic + plain Python functions is sufficient and transparent

The orchestrator is a function, not a class. It takes a `HandoverDocument`, iterates through tasks, calls the appropriate agent for each, evaluates checkpoints, and returns an updated `HandoverDocument` with results filled in.

### Section 3: Data Flow

Document the flow for the three primary workflows:

**Workflow A — Handover Generation:**
```
Board state + git history + prior handovers (RAG) → Planner → Draft handover → Human approval → Handover document (filesystem)
```

**Workflow B — Checkpoint Evaluation:**
```
Executor output + Checkpoint definition → Quality Judge → Verdict + reasoning → Route (proceed/pivot/stop/escalate)
```

**Workflow C — Retrospective:**
```
Handover corpus (RAG) + metrics history → Retro Analyst → Pattern report + velocity analysis → Human review
```

### File location

```
docs/architecture.md
```

**Commit message:** `phase2: task 5 — architecture doc: system architecture, orchestration, data flow`

---

## TASK 6 — Define State Flow and Agent Interaction Model

**Goal:** Write sections 4-5 of `docs/architecture.md`.

### Section 4: State Flow

Alfred's state model is document-mediated (property 1). Explicitly define:

1. **What is persisted in SQLite:** Sprint metadata, velocity history, agent trace logs, checkpoint evaluation history. This is operational bookkeeping, NOT the source of truth.
2. **What is persisted on filesystem:** Handover documents (markdown), configuration (YAML). These ARE the source of truth.
3. **What is ephemeral:** Agent working memory during a single invocation. Dies when the agent returns. This IS property 5.
4. **What RAG indexes:** The handover corpus (all `.md` files matching the handover pattern). RAG is a retrieval optimisation, not state. If you deleted the RAG index, the system would rebuild it from the documents.

The state flow diagram should make it visually obvious that the handover document is the hub and everything else is a spoke.

### Section 5: Agent Interaction Model

Agents do not talk to each other. They talk to the orchestrator, which talks to the handover document. The interaction pattern is:

```
Orchestrator reads HandoverDocument
  → selects next task
  → constructs agent-specific input (from HandoverDocument + tools)
  → calls agent
  → receives agent output
  → validates output against agent's output schema
  → if task has checkpoint: calls Quality Judge with output + checkpoint definition
  → writes results back to HandoverDocument
  → repeats until all tasks complete or a checkpoint halts execution
```

There is no agent-to-agent communication channel. This is deliberate — it preserves property 3 (reasoning/execution isolation) and property 1 (document as protocol). If the Planner needs to know what the Quality Judge decided, it reads the handover document, not a message bus.

**Commit message:** `phase2: task 6 — architecture doc: state flow and agent interaction model`

---

## TASK 7 — Define Technical Risks and Phase 3 Scaffold Spec

**Goal:** Write sections 6-7 of `docs/architecture.md`.

### Section 6: Technical Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Handover schema too rigid** — real handovers vary in structure, forcing them into a schema loses information | High | Start with a permissive schema (many Optional fields). Validate against real BOB_HANDOVER docs before locking. `from_markdown()` must handle 37+ real documents. |
| **RAG retrieval quality** — poor chunk boundaries lose context, hallucinated retrieval contaminates agent input | Medium | Chunk at document section boundaries (not arbitrary token windows). Always include document ID and section header in chunk metadata. Validate retrieval with known-answer queries from the BOB corpus. |
| **LLM provider lock-in** — building against one API shape makes switching expensive | Medium | Abstract behind a minimal adapter interface: `complete(prompt, schema) → structured_output`. Provider-specific code lives only in adapter files. |
| **GitHub API rate limits** — Projects V2 GraphQL API has aggressive rate limits | Low | Batch mutations, cache board state, respect retry-after headers. Dashboard reads from SQLite cache, not live API. |
| **Checkpoint evaluation is subjective** — some gates require human judgment that can't be automated | Medium | This is not a bug, it is property 2. The `escalate` verdict exists for this. Alfred surfaces the evidence and the decision table; the human decides. |
| **Document-mediated state is slow** — reading/writing markdown files is slower than a database | Low | Acceptable. Alfred is not a real-time system. Handovers are created hourly/daily, not per-second. SQLite caches operational state for dashboard queries. |

### Section 7: Phase 3 Scaffold Specification

Phase 3 will create the directory structure, empty modules, and wiring. Specify exactly what Phase 3 must produce:

```
projectalfred/
├── pyproject.toml
├── configs/
│   └── default.yaml
├── docs/
│   └── architecture.md
├── src/
│   └── alfred/
│       ├── __init__.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── handover.py
│       │   ├── checkpoint.py
│       │   ├── agent.py
│       │   └── config.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── planner.py        # empty function stubs
│       │   ├── story_generator.py
│       │   ├── quality_judge.py
│       │   └── retro_analyst.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── github_api.py     # GitHub Projects V2 adapter
│       │   ├── rag.py            # RAG engine
│       │   ├── llm.py            # LLM adapter (provider-agnostic)
│       │   └── persistence.py    # SQLite operations
│       ├── orchestrator.py       # main orchestration function
│       └── api.py                # FastAPI app (endpoints only, no logic)
├── tests/
│   ├── __init__.py
│   ├── test_schemas/
│   ├── test_agents/
│   └── test_tools/
├── data/                         # .gitignore'd
│   └── .gitkeep
├── README.md
├── CLAUDE.md
└── .gitignore
```

Phase 3 creates this structure with:
- Schemas from Phase 2 (already implemented in Tasks 1-4)
- Empty function stubs in agents/ and tools/ (signature + docstring + `raise NotImplementedError`)
- FastAPI app with route definitions but no implementation
- Orchestrator function with the control flow skeleton but no agent calls
- `pyproject.toml` with all dependencies pinned

**Commit message:** `phase2: task 7 — architecture doc: technical risks and phase 3 scaffold spec`

---

## TASK 8 — Create pyproject.toml

**Goal:** Create the project metadata and dependency specification.

### Dependencies (known at this stage)

```toml
[project]
name = "projectalfred"
version = "0.1.0"
description = "Document-mediated, checkpoint-gated agent coordination for software teams"
requires-python = ">=3.11"
license = {text = "Apache-2.0"}

dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.6.0",
    "pyyaml>=6.0",
    "httpx>=0.27.0",      # GitHub API calls
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.3.0",
]
llm = [
    "anthropic>=0.49.0",
    "openai>=1.12.0",
]
rag = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"
```

The exact versions should be checked against current PyPI at build time. The structure above is directional.

### Verification

```bash
cd ~/code/projectalfred
python -m pip install -e ".[dev]" 2>&1 | tail -5
```

**Commit message:** `phase2: task 8 — pyproject.toml`

---

## FUTURE PHASES — SUMMARY

Phases 3-8 are not yet planned at task level. Each will get its own `ALFRED_HANDOVER_N.md` when the time comes, written with knowledge gained from completing the preceding phase. What follows is a catalogue of what each phase must deliver, derived from the README capability contract and stretch enhancement tables.

### Phase 3 — Repository Scaffold

**Scope:** Create the directory structure, empty modules, and wiring specified in Task 7 of this handover. No business logic.

**Deliverables:**
- Directory tree matching the Phase 3 scaffold spec (Task 7 above)
- Agent stubs: `planner.py`, `story_generator.py`, `quality_judge.py`, `retro_analyst.py` — function signatures with docstrings, `raise NotImplementedError`
- Tool stubs: `github_api.py`, `rag.py`, `llm.py`, `persistence.py` — same pattern
- `orchestrator.py` — control flow skeleton (iterate tasks, call agent stubs, check gates) with no real agent calls
- `api.py` — FastAPI app with route definitions, no implementation
- Schemas from Phase 2 wired into the package (`src/alfred/schemas/`)
- `pip install -e .` must succeed; `import alfred` must work

**Does NOT include:** Any working functionality. The scaffold is a skeleton that Phase 4 fills.

### Phase 4 — Core Implementation

**Scope:** Fill the stubs. This is where Alfred becomes functional. Five capability layers land here:

| Capability Layer | What it means concretely |
|---|---|
| **Tool integration** | GitHub Projects V2 GraphQL adapter — read board state, write stories (with HITL gate), query velocity. `tools/github_api.py` |
| **RAG** | Index handover corpus (all `BOB_HANDOVER_*.md` files), chunk at section boundaries, embed, retrieve. Cross-document search for the Planner and Retro Analyst. `tools/rag.py` |
| **State / memory** | SQLite for operational bookkeeping (sprint metadata, velocity history, agent traces, checkpoint history). Document-mediated, not hidden — the handover doc remains source of truth. `tools/persistence.py` |
| **Observability / tracing** | Structured logging of agent invocations: input hash, output hash, token usage, latency, checkpoint verdicts. Enough to replay and audit any agent decision. |
| **Guardrails / robustness** | Input validation (schema enforcement at agent boundaries), output validation (agent cannot produce fields outside its contract), cost caps (max tokens per invocation), rate limiting (GitHub API). |

**Key implementation decisions deferred to Phase 4:**
- RAG engine choice (ChromaDB vs FAISS vs something else)
- Embedding model for RAG
- LLM adapter implementation (which providers to support first)
- SQLite schema (tables, indexes)
- How `from_markdown()` handles the 37+ real BOB_HANDOVER documents (the hardest parse problem)

**Dogfood milestone:** By end of Phase 4, Alfred should be able to: (1) ingest the BOB_HANDOVER corpus, (2) answer RAG queries against it, (3) validate a handover document against the schema, (4) generate a draft handover from board state + corpus context. All with human approval gates.

### Phase 5 — Stretch Enhancements

**Scope:** Five enhancements that move Alfred from "functional tool" to "portfolio-grade demonstration of agentic AI engineering."

| Enhancement | What it requires |
|---|---|
| **Multi-agent coordination** | Planner, Story Generator, Quality Judge, and Retro Analyst running as distinct agents with isolated inputs/outputs, orchestrated by the main control loop. Not concurrent — sequential with checkpoint gates between them. |
| **Self-evaluation / critique loop** | Quality Judge validates handover drafts against the methodology's 5 properties before human review. Produces a structured quality report with pass/fail per property and specific deficiency callouts. |
| **Cost-aware model routing** | Cheap model (e.g. Haiku-class) for triage and classification tasks. Strong model (e.g. Opus-class) for generation and analysis. Router decides based on task type, not content. Configured in `configs/default.yaml`. |
| **Human-in-the-loop approval** | Explicit approval gate before any write to external systems (board, filesystem). FastAPI endpoint that presents the proposed action + evidence and blocks until human approves/rejects. The `escalate` checkpoint verdict routes here. |
| **Live dashboard** | Read-only web UI showing: current sprint state (from SQLite cache), agent trace history, quality scores over time, velocity trends. Reads from SQLite, never from live APIs. |

**Key design constraint:** Every enhancement must preserve all five methodology properties. The critique loop must not replace human judgment (property 2). Multi-agent coordination must not introduce hidden inter-agent state (properties 1 and 3). Cost routing must not degrade checkpoint compliance.

### Phase 6 — Evaluations and Tests

**Scope:** Implement the evaluation framework designed in Phase 1 and write the test suite.

**Five evaluation metrics (all must be implemented and benchmarked):**

| Metric | What it measures | How to test |
|---|---|---|
| **Error propagation rate** | Does the system continue after a detectable failure? | Inject failures (bad markdown, missing fields, LLM errors) and verify the system halts at the correct checkpoint |
| **Checkpoint compliance** | Are decision tables correctly evaluated? | Feed known pass/fail evidence to checkpoints and verify verdicts match expected outcomes |
| **Reproducibility score** | Variance across repeated runs of the same task | Run the same handover through Alfred N times, measure output variance (should be near-zero with temperature=0) |
| **State recoverability** | Can a fresh agent resume from mid-task using only the document? | Kill an in-progress run, cold-start a new agent with only the partially-completed handover, verify it picks up correctly |
| **Control violations** | Actions taken outside intended scope | Verify agent output schemas reject out-of-scope fields; verify no writes to external systems without HITL gate |

**Ablation variants (for the research paper):**
- No checkpoints — remove all gates, let agents run unchecked
- No decision tables — checkpoints exist but with no structured criteria (LLM judges freely)
- No post-mortem — remove the inline failure analysis loop
- Shared context — agents share working memory instead of communicating through the document

Each ablation should show degradation on at least one metric, validating that the methodology property it removes is load-bearing.

**Test suite:** Unit tests for schemas, integration tests for agent contracts, end-to-end tests using real BOB_HANDOVER documents as fixtures.

### Phase 7 — Developer Experience and Deployment

**Scope:** Make Alfred installable, runnable, and deployable by someone who isn't Donal.

| Deliverable | Detail |
|---|---|
| **CLI** | `alfred validate <handover.md>` — validate a document against the schema. `alfred generate --from-board` — draft a handover from board state. `alfred evaluate <handover.md>` — run checkpoint evaluation. |
| **Docker** | Single-container deployment. `docker compose up` starts FastAPI + SQLite + RAG index. No external dependencies except LLM API key. |
| **Configuration guide** | How to point Alfred at your own repo, your own board, your own LLM provider. |
| **CI/CD** | GitHub Actions: lint (ruff), test (pytest), type-check (mypy or pyright). |
| **Enterprise readiness** | API key management, rate limiting, audit logging, RBAC for the HITL approval endpoint. |

### Phase 8 — Portfolio Hardening

**Scope:** Make the project presentable as a portfolio piece and (optionally) a research artifact.

**Deliverables:**
- README rewrite with GIFs/screenshots of the dashboard and CLI
- Architecture diagrams (mermaid, rendered in docs)
- Evaluation results table (from Phase 6) prominently displayed
- "How it works" walkthrough using a real BOB_HANDOVER document as the running example
- Ablation results visualisation (for the paper)
- Contributing guide (if open-source traction warrants it)
- License review (Apache 2.0 confirmed)
- Dependency audit (no vulnerable or abandoned packages)

**Research paper tie-in:** Phase 8 produces the figures, tables, and example walkthroughs that go directly into the paper. The evaluation results from Phase 6 are the experimental section. The ablation variants are the "each property is necessary" argument.

---

## WHAT NOT TO DO

1. **Do NOT write business logic.** Phase 2 is schemas and architecture only. If you find yourself writing `def generate_handover()` with actual LLM calls, you have gone too far.
2. **Do NOT pick an agent framework.** The orchestration is hand-rolled. No LangChain, LangGraph, CrewAI, AutoGen, or any other framework. Plain Python functions.
3. **Do NOT implement RAG.** The RAG schema and config are designed in Phase 2. The implementation is Phase 4.
4. **Do NOT create a database.** The SQLite schema is described in architecture.md. The actual `.db` file is Phase 4.
5. **Do NOT make the Handover schema JSON-only.** It must render to human-readable markdown. If a human can't read the output, the schema is wrong (property 1).
6. **Do NOT design for "any document type."** Alfred handles handover documents in the BOB_HANDOVER style. It is not a generic document processor. Scope discipline.
7. **Do NOT add FastAPI middleware, auth, CORS, or deployment config.** That is Phase 7.
8. **Do NOT modify anything in `~/code/3b_EBD_MLOps`.** Read the BOB_HANDOVER docs for reference. Do not write to that repo.
9. **Do NOT reference any specific AI tool or vendor** in any file you create. Provider-agnostic language only.
10. **Do NOT over-design the schemas.** Start with what the 37+ real handover documents actually contain. If a field doesn't map to something observable in the BOB corpus, you probably don't need it.

---

## EXECUTION NOTES

- **Working directory:** `~/code/projectalfred`
- **Activate venv:** `cd ~/code/projectalfred && python -m venv .venv && source .venv/bin/activate`
- **Install deps:** `pip install -e ".[dev]"`
- **Read reference docs:** The BOB_HANDOVER documents are at `~/code/3b_EBD_MLOps/docs/BOB_HANDOVER_*.md` — read at least 5 before designing the Handover schema
- **Phase 2 should produce exactly 8 commits** on `main`, one per task
- The architecture document (`docs/architecture.md`) is built incrementally across Tasks 5-7 — each task appends sections, it does not rewrite the whole file
- All schemas go in `src/alfred/schemas/` — create the package structure in Task 1 and add to it in Tasks 2-4
- If a schema design decision is ambiguous, favour the interpretation that preserves all five methodology properties

---

## RELATIONSHIP TO THE PAPER

Donal intends to write a research paper on the stigmergic SE methodology in parallel with building Alfred. The evaluation framework (5 metrics, ablation variants) designed in Phase 1 feeds directly into the paper's experimental section. The Handover schema designed in Task 1 of this phase is the formal operationalisation of what the paper describes theoretically. Get it right.
