# Alfred's Handover Document #5 — Phase 6

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_5
**date:** 2026-04-20
**author:** Planner Agent (reasoning only; no execution authority)
**previous_handover:** ALFRED_HANDOVER_4
**baseline_state:** Phase 5 is complete and the output-hardening phase (ALFRED_HANDOVER_4_OUTPUT_HARDENING) is closed. The canonical Phase 6 planning artifact is this document. Phase-close state is commit `c7ae43a` (`output-hardening: task 4`). Executor cold-starts from this file.

**Reference Documents:**
- `docs/ALFRED_HANDOVER_4.md` — authoritative Phase 5 handover and post-mortem
- `docs/architecture.md` — methodology and design constraints
- `src/alfred/orchestrator.py` — real `orchestrate()` contract
- `src/alfred/schemas/agent.py` — planner and agent I/O schemas
- `src/alfred/tools/llm.py` — `LLMError` exception surface
- `pyproject.toml` — dev tooling, test config, dependency truth

---

## WHAT EXISTS TODAY

### Git History

```
c7ae43a  output-hardening: task 4 — add canonical state and git-history support
54470c3  output-hardening: task 3 — feed real git history into planner
82c2dad  output-hardening: task 2 — wire canonical scaffold into generation
b7c56d7  output-hardening: task 1 — add alfred promotion validator
0e67e8a  updated README
fd724e1  phase5: task 6 — dogfood #2
79e2ce5  phase5: task 5 — hitl timeout
74cd112  phase5: task 4 — rag and compliance fixes
d9559e4  phase5: task 3 — cost routing
cbdf91c  phase5: task 2 — critique loop
2446f44  phase5: task 1 — handover compiler
```

### Completed Phase 5 outputs (from `ALFRED_HANDOVER_4.md`)

- Handover compiler (`POST /compile`) — turns a raw document into an executable `HandoverDocument`
- Critique loop (`_run_critique_loop`) — iterative self-review before plan approval
- Cost routing — cheap/expensive LLM tier selection per task
- RAG/compliance fixes — embedder cache, compliance scan scoped to handover markdown only
- HITL timeout — `pending_approvals` table, `/approvals/request`, `/approve`, `/approvals/expire` endpoints
- Dogfood #2 — Alfred used to draft its own Phase 6 spec via `scripts/generate_phase6.py`

### Completed Output-Hardening outputs (from `ALFRED_HANDOVER_4_OUTPUT_HARDENING.md`)

- `scripts/validate_alfred_handover.py` — fail-closed promotion validator enforcing all Alfred canonical sections including `### Git History` placement
- `configs/alfred_handover_template.md` — canonical scaffold injected into every planner prompt
- `src/alfred/tools/git_log.py` — `read_git_log()` supplying real repository commits to the planner
- `PlannerInput.git_history_summary` — structured git history field; model forbidden from inventing commits
- `HandoverDocument.git_history` / `what_exists_today` — optional additive schema fields with render/parse round-trip
- `tests/test_scripts/test_validate_alfred_handover.py` — promotion regression coverage (original miss reproduced as fixture)

### Real orchestrator contract (executor must not deviate from this)

```python
def orchestrate(handover: HandoverDocument, config: AlfredConfig, *, db_path=None) -> HandoverDocument
```

- Returns the **same `HandoverDocument`** instance, mutated in place with task results and checkpoint verdicts
- Skips tasks whose `result` is already populated (re-runnable / stateless property 5)
- Uses `CheckpointHalt` (STOP verdict) and `HumanEscalation` (ESCALATE verdict) as its documented control-flow exceptions when checkpoint routing halts execution
- Does **not** return a `RunResult`; no such type exists

### Real test layout

```
tests/
  test_agents/
  test_tools/
  test_schemas/
  test_scripts/
  test_api.py
  test_orchestrator.py
```

No `tests/unit/` tree exists. Phase 6 adds `tests/property/` alongside the existing layout.

### Real type checker

`pyright` — configured in `pyproject.toml`. `mypy` is not in the repo.

### Current coverage baseline

Not yet measured. Task 3 establishes and records this.

---

## HARD RULES

1. **Do not invent `RunResult`.** The orchestrator returns `HandoverDocument`. Tests must assert on that.
2. **Do not invent `ToolInputError`.** No shared tool exception exists. Property tests assert boundary-specific behaviour: Pydantic validation at schema boundaries, `LLMError` from `llm.complete()`, FastAPI 422 at the API layer.
3. **Do not add `mypy`.** The repo uses `pyright`. If a reviewer wants `mypy`, that is a separate human-approved scope change requiring a `pyproject.toml` update.
4. **Do not reorganise the test tree.** `tests/property/` is added alongside the current layout, not instead of it.
5. **Do not express per-module coverage gates as native pytest-cov config** — `[tool.coverage.report] fail_under` is global only. Per-module thresholds require a custom enforcement script.
6. **Threshold values are Planner proposals** — a human must confirm or override coverage percentages and eval pass thresholds before they become blocking gates.
7. **No live API calls in CI.** All LLM calls in tests use the mock or stub provider.

---

## WHAT THIS PHASE PRODUCES

- `tests/property/` — Hypothesis-driven invariant tests for schemas, orchestrator, and tools
- `evals/` — deterministic harness scoring agent outputs against golden fixtures
- `scripts/check_coverage.py` — custom per-module coverage gate script
- `.github/workflows/ci.yml` — ordered CI pipeline: lint → unit → property → evals → coverage gate
- `docs/coverage_baseline.md` — recorded per-module coverage percentages at phase open
- Updated `docs/architecture.md` Section 8: Testing Strategy

Out of scope:
- Introducing `RunResult`, `ToolInputError`, or any new runtime abstraction
- Reorganising the existing `tests/` tree
- Adding `mypy` without explicit human approval
- Raising or changing `pyproject.toml` type-check config beyond what Phase 6 tasks require

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Property-Based Test Suite | `tests/property/` with Hypothesis tests | CHECKPOINT-6-1 |
| 2 | Evaluation Harness | `evals/scorer.py`, `evals/run_evals.py`, `evals/fixtures/` | |
| 3 | Coverage Gates | `scripts/check_coverage.py`, `docs/coverage_baseline.md` | |
| 4 | CI Pipeline | `.github/workflows/ci.yml` | |
| 5 | Documentation Updates | `docs/architecture.md` Section 8, `README.md` | CHECKPOINT-6-2 |

---

## TASK 1 — Property-Based Test Suite (`tests/property/`)

**Goal:** Use [Hypothesis](https://hypothesis.readthedocs.io/) to derive invariant tests from the schemas and contracts defined in `src/alfred/schemas/` and `src/alfred/orchestrator.py`.

**Subtasks:**

- T1.1 — Schema round-trip tests: for every Pydantic model, generate arbitrary valid instances, serialise to JSON, deserialise, assert equality.
- T1.2 — Orchestrator invariants: for any valid `HandoverDocument` input, `orchestrate()` must:
  - return a `HandoverDocument` (the real return type — not `RunResult`)
  - use `CheckpointHalt` / `HumanEscalation` for STOP / ESCALATE control-flow routing once a checkpoint has been evaluated
  - not re-dispatch any task whose `result` was already populated at call time
  - write checkpoint and task results back into the returned document
- T1.3 — Tool contract tests: each tool function must satisfy its declared type contract under fuzz inputs. Boundary-specific behaviour to assert:
  - Pydantic model boundaries: invalid types fail schema validation before execution
  - `llm.complete()`: propagates `LLMError` on provider failure
  - API layer: invalid request shapes produce FastAPI 422 responses
- T1.4 — Planner output invariants: `PlannerOutput` produced by the Planner agent must always contain a non-empty `draft_handover_markdown` string.

**Acceptance criteria:**
```
PASS  hypothesis runs ≥ 100 examples per test case (settings: max_examples=100)
PASS  no HealthCheck suppressions without an inline justification comment
PASS  all four subtask areas have ≥ 1 property test each
PASS  pytest tests/property/ exits 0 on a clean checkout
```

### Verification

```bash
pytest tests/property/ -v
```

**Expected:**
- property suite exits 0 on a clean checkout
- orchestrator invariants are tested against the real `HandoverDocument` contract, including re-run skipping and in-place result writes
- STOP / ESCALATE routing is asserted via `CheckpointHalt` / `HumanEscalation` without claiming those are the only possible underlying failures

**Suggested commit message:** `phase6: task 1 — property test suite`

---

## TASK 2 — Evaluation Harness (`evals/`)

**Goal:** Build a deterministic, repeatable harness that scores agent outputs against human-curated golden fixtures. No live LLM calls; CI must run without API keys.

**Subtasks:**

- T2.1 — Golden fixture format: define `evals/fixtures/*.json` structure (input snapshot + expected output fields + tolerance metadata). Validate against `evals/fixtures/schema.json`.
- T2.2 — Scorer: `evals/scorer.py` — for each fixture, run the relevant agent with a **mocked LLM**, compare output fields, produce `EvalResult(passed: bool, score: float, diff: str)`.
- T2.3 — Harness runner: `evals/run_evals.py` — iterate all fixtures, aggregate scores, print a human-readable table to stdout, exit non-zero if `pass_rate < EVAL_PASS_THRESHOLD`.
- T2.4 — Initial golden fixtures: author ≥ 3 fixtures covering (a) happy-path orchestration, (b) checkpoint gate rejection, (c) Planner output structure.

**Acceptance criteria:**
```
PASS  python evals/run_evals.py exits 0 against the authored fixtures
PASS  harness uses only mocked LLM — no API key required to run
PASS  each fixture file validates against evals/fixtures/schema.json
PASS  eval report is printed to stdout in a human-readable table
PASS  EVAL_PASS_THRESHOLD is configurable via environment variable (default: 1.0)
```

### Verification

```bash
python evals/run_evals.py
```

**Expected:**
- harness exits 0 against the authored fixtures
- report is printed to stdout in a human-readable table
- execution uses mocked LLM responses only and does not require API keys

**Suggested commit message:** `phase6: task 2 — eval harness`

---

## TASK 3 — Coverage Gates

**Goal:** Enforce minimum coverage thresholds globally and per critical module, blocking CI on regression. Per-module gates use a custom enforcement script because `pytest-cov`'s native `fail_under` is global only.

**Subtasks:**

- T3.1 — Baseline measurement: run `pytest --cov=alfred --cov-report=json` on the current codebase; record per-module percentages in `docs/coverage_baseline.md` and commit it.
- T3.2 — Global gate: add `--cov-fail-under=80` to the CI coverage stage in `pyproject.toml` or the CI workflow.
- T3.3 — Per-module gate script: write `scripts/check_coverage.py` that reads the JSON report and enforces module-level thresholds, exiting non-zero on violation. Thresholds are passed as config (not hardcoded).
- T3.4 — Exclusion policy: document which lines are legitimately excluded (e.g. `if TYPE_CHECKING:` blocks) in `docs/coverage_baseline.md`.

**Acceptance criteria:**
```
PASS  docs/coverage_baseline.md committed with per-module percentages
PASS  pytest --cov=alfred --cov-fail-under=80 exits 0 (threshold subject to human approval)
PASS  python scripts/check_coverage.py exits 0 against the authored baseline
PASS  alfred/orchestrator.py meets its per-module threshold (proposed: ≥ 90%)
PASS  alfred/agents/planner.py meets its per-module threshold (proposed: ≥ 85%)
```

> **Human approval required:** Threshold values above are Planner proposals. A human must confirm or override before these become blocking gates (see Open Questions §1).

### Verification

```bash
pytest --cov=alfred --cov-report=json
python scripts/check_coverage.py
```

**Expected:**
- `docs/coverage_baseline.md` is committed with the measured per-module percentages
- the global coverage gate passes at the approved threshold
- `scripts/check_coverage.py` enforces the per-module thresholds explicitly rather than relying on native coverage config magic

**Suggested commit message:** `phase6: task 3 — coverage gates`

---

## TASK 4 — CI Pipeline (`.github/workflows/ci.yml`)

**Goal:** Wire all quality gates into a single, ordered GitHub Actions pipeline that blocks merges on failure.

**Pipeline stages (in order):**

```
lint  →  unit-tests  →  property-tests  →  evals  →  coverage-gate
```

**Subtasks:**

- T4.1 — Lint stage: `ruff check .` + `pyright` — must exit 0. (`pyright` is the repo type checker; `mypy` is not used.)
- T4.2 — Unit-test stage: `pytest tests/ --ignore=tests/property` with JUnit XML output. (The existing suite lives in `tests/test_agents/`, `tests/test_tools/`, `tests/test_schemas/`, `tests/test_scripts/`, `tests/test_api.py`, `tests/test_orchestrator.py`; there is no `tests/unit/` tree.)
- T4.3 — Property-test stage: `pytest tests/property/` — inherits Hypothesis database from cache.
- T4.4 — Eval stage: `python evals/run_evals.py` — no secrets required.
- T4.5 — Coverage-gate stage: `pytest --cov=alfred --cov-fail-under=80` followed by `python scripts/check_coverage.py`.
- T4.6 — Hypothesis database caching: cache `.hypothesis/` directory keyed on `hashFiles('pyproject.toml')`.

**Acceptance criteria:**
```
PASS  pipeline triggers on: push to main, all PRs targeting main
PASS  each stage is a separate CI job with explicit needs: dependency
PASS  no stage uses live LLM API keys
PASS  pipeline completes in < 10 minutes on a standard GitHub-hosted runner
PASS  failing any stage blocks merge (branch protection rule documented in README)
```

### Verification

```bash
ruff check .
pyright
pytest tests/ --ignore=tests/property -v
pytest tests/property/ -v
python evals/run_evals.py
pytest --cov=alfred --cov-fail-under=80 --cov-report=json
python scripts/check_coverage.py
```

**Expected:**
- all local stages pass in the same order the GitHub Actions workflow enforces
- no stage requires live LLM credentials
- the corresponding GitHub Actions run on `main` is green before branch protection is considered satisfied

**Suggested commit message:** `phase6: task 4 — ci pipeline`

---

## TASK 5 — Documentation Updates

**Goal:** Ensure `docs/architecture.md` and `README.md` reflect the new quality infrastructure.

**Subtasks:**

- T5.1 — Add "Section 8: Testing Strategy" to `docs/architecture.md` describing the four-layer test pyramid (unit → property → eval → coverage gate).
- T5.2 — Update `README.md` "Getting Started" with `pytest` and `evals/run_evals.py` invocation instructions.
- T5.3 — Add CI status badge to `README.md` pointing to the GitHub Actions workflow run page.

**Acceptance criteria:**
```
PASS  Section 8 exists in docs/architecture.md and references all four test layers
PASS  README badge renders correctly (link to workflow run page)
PASS  all internal markdown links in updated files resolve correctly
```

### Verification

```bash
rg -n "Section 8|Testing Strategy|evals/run_evals.py|Actions" docs/architecture.md README.md
```

**Expected:**
- `docs/architecture.md` contains Section 8 covering unit, property, eval, and coverage layers
- `README.md` includes local verification commands and the GitHub Actions badge/link
- updated markdown links are checked as part of human review before close

**Suggested commit message:** `phase6: task 5 — docs update`

---

## CHECKPOINT-6-1 — Property and Eval Gate

**Question:** Are the property tests and eval harness producing stable, meaningful results?

**Evidence required:**
- `pytest tests/property/` exit 0 output
- `python evals/run_evals.py` stdout report showing ≥ 3 fixtures at pass rate ≥ threshold

| Observation | Likely call |
|---|---|
| Property tests pass, eval harness passes all authored fixtures | PROCEED to coverage and CI tasks |
| Property tests pass but eval harness below threshold | PIVOT — triage failing fixtures before proceeding |
| Any Hypothesis HealthCheck suppressed without comment | STOP — add justification or fix the test |

---

## CHECKPOINT-6-2 — Phase Exit Gate

**Question:** Is Phase 6 complete enough to approve Phase 7 planning?

**Evidence required:**
- `pytest tests/property/` exit 0
- `python evals/run_evals.py` stdout showing pass rate ≥ `EVAL_PASS_THRESHOLD`
- `pytest --cov=alfred --cov-fail-under=80` exit 0
- `python scripts/check_coverage.py` exit 0 (per-module thresholds met)
- GitHub Actions run URL showing all jobs green on `main`
- `docs/architecture.md` Section 8 present

| Observation | Likely call |
|---|---|
| All six evidence items present | APPROVE — Phase 7 planning may begin |
| CI green but coverage gates not yet scripted | BLOCK — Task 3 incomplete |
| Documentation incomplete | PROCEED WITH NOTES — complete Task 5 before close |

> **This table is a DRAFT. A human must confirm it before it becomes a blocking gate.**

---

## OPEN QUESTIONS REQUIRING HUMAN JUDGMENT

1. **Coverage thresholds:** Global floor 80%, `orchestrator.py` 90%, `planner.py` 85% are Planner proposals. Confirm or override before Task 3 begins.

2. **Eval pass threshold:** Default `EVAL_PASS_THRESHOLD=1.0` (single fixture failure blocks CI). Should this be relaxed to 0.8 during Phase 6 while the fixture library is being authored?

3. **Hypothesis `max_examples`:** 100 per test is a reasonable starting point. Is there a CI time budget for the property-test stage? (Planner assumption: < 3 minutes for the full suite.)

4. **Golden fixture authorship:** Fixtures require human-curated expected output fields. Who authors and reviews the ≥ 3 initial fixtures? This cannot be delegated to an executor agent.

5. **Phase 7 threshold ownership:** Should the Phase 7 Planner have explicit permission to raise coverage thresholds, or must each change go through a separate gate approval?

---

## WHAT NOT TO DO

1. **Do NOT add `RunResult`** or any new return-type wrapper around `orchestrate()`.
2. **Do NOT add `ToolInputError`** — test boundary-specific error types that actually exist.
3. **Do NOT add `mypy`** without an explicit human decision and a `pyproject.toml` update.
4. **Do NOT create `tests/unit/`** — the existing test tree stays; only `tests/property/` is added.
5. **Do NOT use native per-module `fail_under`** in coverage config — it does not work that way; write `scripts/check_coverage.py`.
6. **Do NOT call live LLM APIs in any test or CI stage.**
7. **Do NOT approve this document** without a human confirming the coverage thresholds and eval pass threshold.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section before closing the phase. After promotion to canonical, the Phase 7 Planner will cold-start from this artifact.

**What worked:**
- Hypothesis strategies using printable ASCII (`min_codepoint=32, max_codepoint=126`) avoided surrogate-character JSON round-trip failures cleanly.
- `try/finally` state restoration for `llm._PROVIDERS` and `orchestrator._AGENT_RUNNERS` kept property tests fully isolated between Hypothesis examples.
- The eval fixture tolerance mechanism (`"substring"` comparison) handled the planner markdown check without hardcoding exact LLM output.
- `ruff check --fix` auto-resolved 64 of 66 lint issues from pre-existing codebase patterns; only 2 ambiguous-name (`E741`) errors in `handover.py` needed manual fixes.

**What was harder than expected:**
- Ruff revealed 59+ pre-existing lint errors across the codebase (UP045, I001, E402, F541, E741) that were not introduced in Phase 6. Required adding four ignore rules and a manual rename pass in `handover.py`.
- Pyright has 30 pre-existing type errors predating Phase 6; made advisory (`continue-on-error: true`) in CI with an inline comment. Cannot be made blocking without a dedicated type-cleanup phase.
- Eval fixture 3 (planner output structure) initially failed scoring because `checks["draft_handover_markdown_contains"] = True` (bool) was compared against `expected[...] = "Phase 7"` (str). Required adding a tolerance-aware `_passes()` function to the scorer.
- `orchestrator.py` coverage settled at 79.2%, not 80%, due to external I/O paths (GitHub API, SQLite, RAG) that are structurally disabled in tests. Per-module threshold set to 79% with documented rationale.

**Decisions made during execution (deviations from this plan):**
- `EVAL_PASS_THRESHOLD` default changed from `1.0` (handover proposal) to `0.8` — human approved before Task 2 implementation.
- Coverage thresholds: global 80% approved; per-module proposals (`orchestrator.py` 90%, `planner.py` 85%) overridden by human to `orchestrator.py` 79% (current level) and `planner.py` 80%. Rationale documented in `docs/coverage_baseline.md`.
- `pyright` made advisory in CI (`continue-on-error: true`) rather than blocking, due to 30 pre-existing errors. Human approved.
- Phase 7 may raise coverage thresholds autonomously without a separate gate approval — human confirmed.

**Metrics at phase close:**
- Final global coverage: 80.9%
- Property test count: 24 (across 4 modules, ≥100 examples each)
- Eval fixture count: 3 (pass rate 3/3 = 1.00 ≥ 0.80 threshold)
- CI pipeline runtime: < 3 minutes (local); GitHub Actions TBD
- Open questions resolved: 5/5

**next_handover_id:** ALFRED_HANDOVER_6
