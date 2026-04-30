# Alfred's Handover Document #10 — Phase 3: Persist Proposed Stories as Runtime State (No Regeneration Across Gate)

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0  
**id:** ALFRED_HANDOVER_10  
**date:** 2026-04-29  
**author:** Alfred Planner (draft — human approval required)  
**previous_handover:** ALFRED_HANDOVER_9  
**baseline_state:** Phase 0/1 decisions are frozen; Phase 2 harness exists and halts at the approval gate after story generation, but Phase 3 persistence of proposed stories as durable runtime execution state is not yet implemented.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_9.md` — Phase 2 ratified harness + explicit Phase 3 follow-ups (persist proposed stories; move story output onto `TaskResult`; fail-fast `AlfredConfig` for empty model string).
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — Phase 3 scope + hard rules (especially: don’t hide critical execution state in temporary memory; document-as-protocol; no scope broadening).
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — `TASK-SEED-BOARD-001` contract (6–8 `StoryProposal` fields) + verbatim approval-gate wording (Phase 4 reuse).
- `docs/active/DEMO_PROJECT_LAYOUT.md` — external demo workspace layout contract and path semantics (Alfred must write artifacts under `<demo-project-root>/docs/handovers/`; no `.gitkeep`; demo workspace is separate from this repo).
- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — frozen scenario charter content used by the demo workspace (docs/CHARTER.md is a verbatim copy in the external workspace).
- `docs/DOCS_POLICY.md` — repo docs governance constraints (for any documentation updates performed in this repository).

Phase 3 exists to make the approval gate *real* by making the story proposals durable, reviewable, and reusable across a pause/resume boundary — without regenerating stories between “review” and the eventual Phase 4 “write to GitHub” action. This handover plans the smallest architecturally-honest slice: persist proposed stories (with linkage to the source handover/task) into Alfred’s runtime persistence layer (SQLite), surface them for review without re-invoking the story generator, and carry an approval-state slot forward (pending → approved → written) without implementing the GitHub write path (explicitly Phase 4).

---

## WHAT EXISTS TODAY

### Git History

```
2d749c5  generator: prime for ALFRED_HANDOVER_10 (Phase 3) + open workflow discussion
cb59100  docs: promote ALFRED_HANDOVER_9 canonical handover
eb2b476  scripts: task 2 — demo execution harness (orchestrate + gate)
7fde9d9  scripts: task 1 — demo workspace initialiser
bfb3d2c  first fixed handover
807b142  validator: support tagged future doc paths
e465cfd  updated for handover 9
b8e822e  tidied up docs
7101379  added postmortem to handover and updated script
3013445  demo: implement phase 1 kickoff docs
362c189  docs: register ALFRED_HANDOVER_8 in manifest
87fa16b  added first demo handover
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Runtime & Repo Inventory (relevant to Phase 3)

- `src/alfred/api.py` — **exists today**; FastAPI app with 11 endpoints (including approvals endpoints).
- `src/alfred/orchestrator.py` — **exists today**; provides `orchestrate(...)` (signature must be inspected before modifying integrations).
- `src/alfred/cli.py` — **exists today**; CLI entry point declared in `pyproject.toml` (`alfred.cli:main`).
- Agent modules in `src/alfred/agents` — **exist today**: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`.
- Tool modules in `src/alfred/tools` — **exist today**: `docs_policy`, `git_log`, `github_api`, `handover_authoring_context`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`.
- `pyproject.toml` — **exists today** with `[project]=True`, `[project.scripts]=True`, `cli_entry=alfred.cli:main`.

**Phase 2 harness behavior (already ratified):**
- `scripts/init_demo_workspace.py` — **exists today** (Phase 2) and creates the *external* demo workspace layout.
- `scripts/run_kickoff_demo.py` — **exists today** (Phase 2) and runs: persist kickoff handover in the *external* demo workspace, compile it, call `orchestrate(...)`, run `TASK-SEED-BOARD-001`, and halt at the approval gate with human-readable output.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Single scenario is locked:** Customer Onboarding Portal (no substitutions).
2. **Demo workspace shape is frozen:** `<demo-project-root>/README.md`, `<demo-project-root>/docs/CHARTER.md`, `<demo-project-root>/docs/handovers/` (empty at kickoff; no `.gitkeep`).
3. **Docs are the protocol source of truth:** the demo project’s `docs/` surface (and the approved/persisted handover artifact) is authoritative; GitHub is a downstream projection.
4. **6–8 proposals is a hard success criterion:** fewer than 6 or more than 8 is failure and must be re-run before approval.
5. **Approval gate wording is verbatim-locked** (from `docs/active/KICKOFF_HANDOVER_OUTLINE.md`).
6. **No GitHub write path in Phase 3:** Phase 4 owns board mutation; Phase 3 only prepares durable state and review surfaces.
7. **Do not hide critical state in temporary memory** if it must survive pause/resume (demo plan hard rule).

---

## HARD RULES

1. **Do not bypass `orchestrate(...)`.** Phase 3 changes must preserve orchestrator-mediated execution in the main run.
2. **Do not write to GitHub Project V2 in this phase.** Persisting proposals and recording approval state is allowed; performing the write is forbidden.
3. **Do not regenerate story proposals during review.** The proposals presented at the approval gate must be the persisted records created at generation time.
4. **Do not let persistence replace the docs artifact.** Persisted story rows are runtime execution state; the demo workspace handover markdown remains the protocol artifact.
5. **Do not revisit frozen Phase 0/1 inputs.** Charter text, outline sections, task id `TASK-SEED-BOARD-001`, and approval-gate wording are locked.
6. **Do not broaden scope** into retrospectives, multi-sprint planning, dashboards, or generalized workflow engines.
7. **Tooling constraint:** use the repo’s existing type checker (`pyright`); do not introduce `mypy`.

---

## WHAT THIS PHASE PRODUCES

- `src/alfred/schemas/story_proposal.py` — **to be created in this phase**; Pydantic schema(s) for persisted story proposals and approval lifecycle (per `schema` placement rule: schemas belong under `src/alfred/schemas/` as `{name}.py`).
- `src/alfred/tools/persistence.py` — **exists today**; **to be extended in this phase** with SQLite DDL/migrations (if present) and CRUD for persisted proposed stories (per `tool` placement rule: tool modules live under `src/alfred/tools/`).
- `src/alfred/orchestrator.py` — **exists today**; **to be updated in this phase** so structured agent output (story proposals) is persisted/attached to `TaskResult` (retiring reliance on the Phase 2 `set_agent_runner` side-channel pattern).
- `scripts/run_kickoff_demo.py` — **exists today**; **to be updated in this phase** to show gate review output sourced from persistence (not from transient in-memory return values).
- `tests/test_schemas/test_story_proposal.py` — **to be created in this phase** (per `test` placement rule: tests belong under `tests/` and must be `test_*.py`).
- `tests/test_tools/test_persistence_story_proposals.py` — **to be created in this phase**; persistence-layer tests for insert/list/update status.
- `tests/test_orchestrator/test_story_result_persistence.py` — **to be created in this phase**; verifies orchestrator emits/persists structured results without needing harness-side capture.
- `src/alfred/schemas/config.py` (or existing config module, if different) — **exists today or unknown; must be inspected**; **to be updated in this phase** to fail fast when an LLM-dependent path runs with an empty model string.

Out of scope:
- GitHub Project V2 write path (Phase 4).
- Rehearsal runbook and operator-facing documentation beyond what is required to verify Phase 3 (Phase 5).
- Retrospectives, story editing after creation, multi-sprint planning.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Define persisted `StoryProposal` + approval lifecycle schema | `src/alfred/schemas/story_proposal.py` | CHECKPOINT-1 |
| 2 | Implement SQLite persistence for proposed stories | updates in `src/alfred/tools/persistence.py` + tests | CHECKPOINT-2 |
| 3 | Persist structured agent output onto `TaskResult` via orchestrator | `src/alfred/orchestrator.py` update + tests | CHECKPOINT-3 |
| 4 | Gate review reads from persistence (no regeneration) | `scripts/run_kickoff_demo.py` update + tests | CHECKPOINT-4 |
| 5 | Fail-fast config: empty model string on LLM path | config module update + test | CHECKPOINT-5 |

---

## TASK 1 — Define persisted `StoryProposal` + approval lifecycle schema

**Goal:** Introduce explicit schema types to represent proposed stories as durable runtime execution state with traceability to the source handover/task and a Phase 4-ready approval status slot.

### Implementation

1. **Create a dedicated schema module** — add `src/alfred/schemas/story_proposal.py` (**to be created in this phase**, per `schema` placement rule).
2. **Define a stable story proposal record** — include fields required by the kickoff task contract:
   - `title: str`
   - `description: str`
   - `acceptance_criteria: list[str]`
   - `story_points: int`
3. **Add required traceability fields** (must support “no regeneration” and gate linkage):
   - `handover_id: str` (source handover)
   - `task_id: str` (should carry `TASK-SEED-BOARD-001`)
   - `proposed_story_id: str` (stable identifier; e.g., UUID as string)
   - `created_at: datetime` (or ISO string)
4. **Add approval lifecycle slot without implementing writes**:
   - `approval_status: Literal["pending", "approved", "written"]` (or equivalent enum)
   - `approval_decision_id: str | None` (placeholder link forward; may remain `None` in Phase 3)
   - `approved_at: datetime | None`, `written_at: datetime | None` (optional but helps Phase 4 audit)
5. **Define a minimal “persistence row” model** distinct from “agent output” if needed.
   - Agent output is the 6–8 proposals.
   - Persistence row adds ids, timestamps, and approval fields.

### Verification

```bash
pyright
pytest -q
```

**Expected:**
- Schema module imports cleanly.
- Unit tests validate that a proposal with required fields serializes/deserializes and enforces types (including `acceptance_criteria` list semantics).

**Suggested commit message:** `schemas: task 1 — add story proposal persistence models`

### CHECKPOINT-1 — Schema adequacy & Phase 4 compatibility

**Question:** Do the schema fields fully support Phase 3 “no regeneration across gate” and Phase 4 approval/write linkage without introducing Phase 4 behavior?

**Evidence required:**
- Paste the contents (or excerpt) of `src/alfred/schemas/story_proposal.py` showing:
  - the proposal model fields
  - the approval status field
  - the traceability linkage fields (`handover_id`, `task_id`, stable id)

| Observation | Likely call |
|---|---|
| Schema includes task-required story fields + traceability + status slot; no GitHub specifics | PROCEED |
| Traceability or status is underspecified (e.g., no stable id or no `task_id`) | PIVOT |
| Schema bakes in Phase 4 write mechanics or GitHub-specific fields prematurely | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Implement SQLite persistence for proposed stories

**Goal:** Store proposed stories durably in Alfred’s SQLite persistence so a review step can list them later without re-running the story generator.

### Implementation

1. **Inspect the existing persistence layer** — review `src/alfred/tools/persistence.py` (**exists today**) to find:
   - where SQLite DB path is configured
   - how connections are managed
   - whether there is an existing migrations/DDL pattern
2. **Add table DDL** for proposed stories.
   - Suggested table: `story_proposals`
   - Columns should include: `proposed_story_id` (PK), `handover_id`, `task_id`, `title`, `description`, `acceptance_criteria_json`, `story_points`, `approval_status`, timestamps.
3. **Add CRUD functions** (names may vary; keep consistent with existing module style):
   - `insert_story_proposals(handover_id, task_id, proposals) -> list[StoryProposalRecord]`
   - `list_story_proposals(handover_id, task_id) -> list[StoryProposalRecord]`
   - `update_story_proposal_status(proposed_story_id, status, ...) -> None`
4. **Ensure idempotency behavior is explicit** (human decision required):
   - Option A: each run inserts new `proposed_story_id` rows (multiple batches allowed).
   - Option B: enforce unique `(handover_id, task_id)` batch and replace rows.
   - Do not guess: surface as an open question if the existing persistence patterns don’t dictate it.
5. **Write tests** under `tests/`:
   - `tests/test_tools/test_persistence_story_proposals.py` (**to be created in this phase**, per `test` placement rule).
   - Use temp DB path/fixture consistent with existing tests.

### Verification

```bash
pyright
pytest -q
```

**Expected:**
- Creating the table works on a clean DB.
- Inserting 6–8 proposals persists rows.
- Listing returns the same rows without invoking any agent.
- Updating status changes the row deterministically.

**Suggested commit message:** `persistence: task 2 — store and query story proposals`

### CHECKPOINT-2 — Persistence meets “no regeneration” requirement

**Question:** Can a second process invocation (or a second listing call) retrieve the same story proposals from SQLite without calling the story generator?

**Evidence required:**
- Paste test output or a short snippet demonstrating:
  - insert in one step
  - list in a separate step
  - identical proposal ids/titles returned

| Observation | Likely call |
|---|---|
| Persisted records list identically across calls; no agent invocation required | PROCEED |
| Works only within one process (state not actually persisted) | STOP |
| Persistence works but linkage fields (`handover_id`, `task_id`) aren’t indexed/usable for lookup | PIVOT |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 3 — Persist structured agent output onto `TaskResult` via orchestrator

**Goal:** Retire the Phase 2 harness-side `set_agent_runner` capture as the primary mechanism by ensuring orchestrator-run tasks produce structured results (and persistence writes) as part of orchestrated execution.

### Implementation

1. **Inspect current orchestrator result types** — open `src/alfred/orchestrator.py` (**exists today**) and locate:
   - how a task result is represented (e.g., `TaskResult` model)
   - where agent outputs are captured
2. **Add a structured result channel** for `TASK-SEED-BOARD-001`.
   - If `TaskResult` already has a generic `data`/`payload` field, use it.
   - If not, add a minimal `structured_output` field rather than inventing side channels.
3. **At the point where `story_generator` returns the list of proposals**:
   - validate count is 6–8 (existing behavior may already do this; preserve).
   - write proposals to SQLite via the persistence API from Task 2.
   - attach the persisted records (or their ids) onto the task result.
4. **Keep Phase 3 narrow**:
   - Do not call `github_api`.
   - Do not mark anything `written`.
   - Default status should be `pending`.
5. **Add orchestrator tests**:
   - `tests/test_orchestrator/test_story_result_persistence.py` (**to be created in this phase**, per `test` placement rule).
   - Use a deterministic stub runner for the `story_generator` (no LLM credentials required).

### Verification

```bash
pyright
pytest -q
```

**Expected:**
- Orchestrator-run of the seed task produces a task result that includes persisted proposal ids/rows.
- Persistence layer contains rows keyed by `handover_id` and `task_id`.
- No `set_agent_runner` side-channel is required for persistence to occur.

**Suggested commit message:** `orchestrator: task 3 — persist story outputs and attach to TaskResult`

### CHECKPOINT-3 — Orchestrator is the durable truth of execution state

**Question:** After the orchestrator completes `TASK-SEED-BOARD-001`, is the persisted story state available via the orchestrator’s returned result *and* in SQLite, without harness-specific interception?

**Evidence required:**
- Paste a test snippet or console output showing:
  - a mocked run of orchestrate
  - resulting `TaskResult` includes story proposal ids or rows
  - DB rows exist for the same ids

| Observation | Likely call |
|---|---|
| TaskResult includes structured output and DB rows exist; harness can be dumb | PROCEED |
| DB persistence is still only possible via harness hooks | PIVOT |
| Orchestrator changes break existing Phase 2 harness behavior or bypass orchestrate | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 4 — Gate review reads from persistence (no regeneration)

**Goal:** Ensure the approval gate review output is sourced from persisted proposals (SQLite), not from in-memory agent outputs, so pause/resume does not require regeneration.

### Implementation

1. **Update `scripts/run_kickoff_demo.py`** (**exists today**) to:
   - run the orchestrated task as before
   - when printing the approval-gate review section, query SQLite for proposals by `handover_id` + `task_id` and print those
2. **Preserve verbatim approval prompt** from `docs/active/KICKOFF_HANDOVER_OUTLINE.md`:

> Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

(Replace `N` with the count from the persisted rows.)

3. **Add tests** `tests/test_scripts/test_run_kickoff_demo_persistence_gate.py` (**to be created in this phase**, per `test` placement rule) that:
   - stubs story generator once
   - runs the harness
   - runs a second “review-only” path (or reruns harness in a mode that skips generation if proposals already exist) and asserts the story generator stub was not invoked

> If `scripts/run_kickoff_demo.py` currently has no concept of “review-only”, the smallest honest option is to add an explicit CLI flag like `--review-only` that only lists persisted proposals and prints the approval prompt. This is Phase 3-appropriate because it surfaces persisted execution state without writing to GitHub.

### Verification

```bash
pyright
pytest -q
```

**Expected:**
- Gate listing can be printed without regenerating proposals.
- Approval prompt uses the locked wording.

**Suggested commit message:** `scripts: task 4 — approval gate reads persisted story proposals`

### CHECKPOINT-4 — Demonstrate pause/resume integrity

**Question:** Can an operator review the exact proposed stories after a pause (new process) without regenerating them?

**Evidence required:**
- Paste two command outputs:
  1) initial run output showing proposals persisted
  2) second run or `--review-only` output showing the same proposals and showing no generation occurred

| Observation | Likely call |
|---|---|
| Second invocation lists persisted proposals; story generator not called | PROCEED |
| Second invocation silently regenerates or overwrites proposals | STOP |
| Review works but can’t reliably select proposals for the correct handover/task | PIVOT |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 5 — Fail-fast config: empty model string on LLM path

**Goal:** Make LLM-dependent paths fail fast when configured with an empty model string, as a Phase 2 follow-up now that schema/persistence changes are in-flight.

### Implementation

1. **Locate the config surface** used to configure LLM model name (likely via an `AlfredConfig` model).
   - If `AlfredConfig` is not a Pydantic model, follow existing conventions; do not introduce a new config system.
2. **Add validation**: when an LLM-dependent path is invoked and the model string is empty/blank, raise a clear error before attempting any call.
3. **Add unit test** asserting the error and message.

### Verification

```bash
pyright
pytest -q
```

**Expected:**
- A run that would have invoked the LLM now fails with a clear message if model is empty.

**Suggested commit message:** `config: task 5 — fail fast on empty LLM model`

### CHECKPOINT-5 — Safety improvement does not change demo semantics

**Question:** Does fail-fast behavior improve operator feedback without changing the governed workflow semantics?

**Evidence required:**
- Paste the unit test name and assertion verifying failure message.

| Observation | Likely call |
|---|---|
| Clear error, triggers only when model is blank, no workflow semantics changed | PROCEED |
| Breaks tests or blocks stubbed/no-LLM demo paths unintentionally | PIVOT |
| Introduces new config subsystem or hidden defaults that mask misconfiguration | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do not add any GitHub Project write behavior (including “just a small create-item call”) — Phase 4 only.
2. Do not regenerate proposals during review; the review surface must read persisted proposals.
3. Do not treat persisted SQLite rows as replacing the demo workspace handover artifact — docs remain protocol.
4. Do not invent a new workflow engine or generalized event log; keep Phase 3 narrowly about story proposal persistence + review.
5. Do not change the locked approval-gate wording.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- *executor to fill*

**What was harder than expected:**
- *executor to fill*

**Decisions made during execution (deviations from this plan):**
- *executor to fill — each deviation must include: what changed, why, who approved*

**Forward plan:**
- *executor to fill*

**next_handover_id:** ALFRED_HANDOVER_11