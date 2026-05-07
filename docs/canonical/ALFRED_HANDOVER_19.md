# Alfred's Handover Document #19 — Concern X, Slice 7: Pre-flight Validators (Fail Fast Before Any LLM Call)

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_19
**date:** 2026-05-07
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_18
**baseline_state:** The handover generator derives identity from the phase ledger+brief (Slice 6) but still lacks deterministic pre-flight checks to hard-fail before any LLM call.

**Reference Documents:**
- `CONTEXT.md` — glossary definitions and protocol invariants: phase ledger authority flow, brief semantics, context roles/dedup rules, doc-class contract, and the no-LLM-judge constraint that governs all validation.
- `docs/active/POST_GRILL_1.md` — defines Slice 7 objective, the fixed set of five pre-flight checks, file-level deliverables, and acceptance criteria.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — resolved workflow decisions we must not re-argue: ledger is derived (not protocol), brief is human-authored, exactly three context roles with fixed dedup precedence, deterministic validation only, and renderer-fixture testing philosophy.
- `docs/canonical/ALFRED_HANDOVER_18.md` — continuity input for the active phase; specifically: Slice 6’s explicit `previous_handover` contract (no inference from phase ordering), renderer-derived identity flow, and the script-boundary dry-run/testing pattern to preserve.
- `docs/active/PHASE_LEDGER.yaml` — active planning-row seed for Slice 7; constrains `handover_id`, `previous_handover`, carry-forward semantics, and the brief fields this phase must operationalise.

This phase implements **Slice 7 only**: a deterministic pre-flight gate that runs **before any LLM call** in `scripts/generate_next_canonical_handover.py`. The goal is to convert “we will probably fail later” conditions (bad paths, bad carry-forward ids, continuity mismatch, role-duplication, malformed reference tags) into fast, clear, deterministic errors.

This handover is the protocol surface for the change: the validator behavior, file placement, and checkpoints live here (document-as-protocol), and execution must stop at explicit checkpoints for human approval (checkpoint-gated execution). No model-judge logic is permitted anywhere in the validation chain.

---

## WHAT EXISTS TODAY

### Git History

```
bf9a99b  docs: seed slice 7 handover brief
e735e2e  docs: add ALFRED_HANDOVER_18 and tuning discussion
f83afca  tests: task 3 polish — fixture-driven script-boundary dry-run coverage
e881c4f  tests: task 3 — assert renderer outputs, not prose constants
9f04f40  generator: task 2 follow-up — derive scope-spec source path, add --dry-run, drop stale identity literals
beb82ed  generator: task 2 — derive identity constants via renderer
3027eae  render: task 1 pivot — explicit previous_handover, hard_rules, title equality
396907c  render: task 1 — add deterministic handover inputs renderer
64e5c44  generator: retarget next handover to slice 6
016ce8e  docs: add ALFRED_HANDOVER_17 canonical handover
52b04db  handover: wire carry_forward role through ContextBundle assembly
1d2c9ae  handover: route planner-context assembly through ContextBundle.render
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current generator + workflow shape (grounded repo facts)

- The FastAPI app exists today as a single module at `src/alfred/api.py` (not in scope to change).
- Agent modules exist today under `src/alfred/agents`: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`.
- Tool modules exist today under `src/alfred/tools`: `board_write_contract`, `docs_policy`, `git_log`, `github_api`, `handover_authoring_context`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`, `story_markdown`.
- The canonical handover workflow is driven by `scripts/generate_next_canonical_handover.py` (exists today). It assembles planner context and invokes the planner pipeline.
- Slice 5 introduced a typed three-role context seam in `src/alfred/context` (exists today) with invariants we must preserve:
  - exactly three roles: `scope`, `carry_forward`, `continuity`
  - dedup precedence: `scope` > `carry_forward` > `continuity`
  - role-specific rendering rules (full text vs deterministic summary)
- Slice 6 moved identity and “what phase are we generating?” inputs behind a deterministic renderer: `src/alfred/render/handover_inputs.py` (exists today). It consumes a phase ledger + active brief and includes an explicit `previous_handover` contract; **continuity must not be inferred from phase ordering**.

### Key Design Decisions Inherited (Do Not Revisit)

1. **No LLM-judge in validation**: all validators are deterministic code; semantic judgment happens at the human approval gate (per `CONTEXT.md` and workflow discussion).
2. **Exactly three context roles** (`scope`, `carry_forward`, `continuity`) with fixed dedup precedence `scope` > `carry_forward` > `continuity` (per `CONTEXT.md`).
3. **Continuity is explicit**: preserve Slice 6’s `previous_handover` contract; do not guess continuity from phase-id ordering (per `docs/canonical/ALFRED_HANDOVER_18.md`).
4. **Renderer-derived identity must remain the source for generator identity/CLI defaults**: do not reintroduce hand-edited identity constants into the generator.

---

## HARD RULES

1. **Slice 7 only**: implement *pre-flight* validation before the planner call. Do **not** start Slice 8+ post-generation validators or Slice 9 failed-candidate filename short-circuit logic.
2. **No LLM-judge anywhere**: pre-flight checks must be deterministic code only (per `CONTEXT.md`).
3. **Preserve explicit continuity**: the generator must reject missing/malformed `previous_handover` continuity metadata; do not infer continuity from phase ordering.
4. **Hard-fail before any LLM call** when pre-flight validation fails.
5. **Preserve the Slice 5 ContextBundle seam and Slice 6 renderer-derived identity/CLI surface**: do not change external CLI flags as part of wiring preflight.

---

## WHAT THIS PHASE PRODUCES

- A new pre-flight validation package and module: `src/alfred/validate/__init__.py` and `src/alfred/validate/preflight.py` (**to be created in this phase**, per placement rule: source modules live under `src/alfred/`).
- Generator wiring so `scripts/generate_next_canonical_handover.py` runs pre-flight validation **before** any planner/LLM invocation and fails closed with actionable errors.
- A new unit test module `tests/test_validate/test_preflight.py` (**to be created in this phase**, per test placement rule: tests live under `tests/` with `test_*.py`).

Out of scope:
- Slice 8 post-generation validators.
- Slice 9 failed-candidate filename logic.
- Any FastAPI endpoint changes (FastAPI remains in `src/alfred/api.py`).
- Generalizing Slice-6-specific scope packet wording unless required for safe pre-flight wiring.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Implement deterministic pre-flight validator module | `src/alfred/validate/preflight.py` + `src/alfred/validate/__init__.py` | CHECKPOINT-1 |
| 2 | Wire pre-flight into generator before planner/LLM call | Edited `scripts/generate_next_canonical_handover.py` (no CLI flag changes) | CHECKPOINT-2 |
| 3 | Add isolated negative tests + real-ledger passing regression | `tests/test_validate/test_preflight.py` |  |

---

## TASK 1 — Implement deterministic pre-flight validator module

**Goal:** Add a deterministic, unit-testable pre-flight validation entrypoint implementing the required five checks.

### Implementation

1. **Create validate package** — create `src/alfred/validate/__init__.py` (**to be created in this phase**).
   - Keep exports minimal (e.g., `run_preflight(...)`), so generator wiring is explicit.

2. **Create module with the five required checks** — create `src/alfred/validate/preflight.py` (**to be created in this phase**).

   The module should expose a single orchestration function (naming is executor’s choice, but must be stable and testable), which runs the fixed set of checks and raises or returns a deterministic structured error.

   **Minimum five checks (fixed scope for Slice 7):**

   - **Check A — assembled scope-input paths exist**
     - Validate the actual doc set that the generator will register as `scope` items, not merely the planning row's direct `scope_sources` field.
     - For this repo today, derive that set from the same authoring-context selection plan / authoritative packet inputs that `build_planner_context(...)` will consume at runtime.
     - Exclude synthetic in-memory packet markers (for example the pre-rendered scope packet path placeholder) from filesystem existence checks.
     - Do **not** implement this check by iterating `active.scope_sources` alone: the live Slice 7 planning row carries scope via prior ratified phase material and authoring-packet selection, while direct `scope_sources` may be empty.
     - Errors must name the missing path(s).
     - Validator must be deterministic: file existence only.

   - **Check B — carry-forward phase ids exist and are ratified**
     - For each `scope_carry_forward` phase id referenced by the active planning row, verify:
       - the phase id exists in the ledger
       - that phase status is `ratified`
     - Errors must name the invalid ids and whether missing vs wrong status.

   - **Check C — previous handover’s `next_handover_id` matches**
     - Preserve Slice 6’s explicit continuity approach: use the planning row’s `previous_handover` and verify the referenced canonical handover declares `**next_handover_id:** ALFRED_HANDOVER_19` (or generally “matches the planning row’s handover id”).
     - Error should state both values.
     - This is a deterministic parse of markdown content (no semantic inference).

   - **Check D — no path appears in more than one context role**
     - Validate the assembled `ContextBundle` inputs (or the pre-bundle doc list, depending on where wiring is easiest) so a single path does not appear in multiple roles.
     - This check should align with the methodology invariant: dedup precedence exists, but this preflight ensures we are not silently duplicating or mis-assigning paths.
     - Error should include the path and the roles it appeared in.

   - **Check E — reference tags parse**
     - Deterministically scan relevant markdown inputs for `[future-doc: ...]` and `[future-path: ...]` tags and ensure they parse per the existing tag conventions.
     - Fail closed on malformed tags.

   **Error shape requirement:**
   - Errors must be actionable and human-readable (clear “what failed” + “where”).
   - Avoid mixing printing/logging with validation logic; the generator script can format final output.

3. **Add typing + pyright friendliness**
   - Use repo type checker conventions (pyright; **do not introduce mypy**).

### Verification

```bash
# run unit tests (adjust runner to repo convention)
pytest -q

# optionally, run pyright if it is part of the repo’s standard checks
pyright
```

**Expected:**
- A unit-testable preflight API exists.
- Each of the five checks can be triggered deterministically in isolation (via tests in Task 3).

**Suggested commit message:** `validate: task 1 — add preflight validator (5 deterministic checks)`

### CHECKPOINT-1 — Preflight module is correct and testable

**Question:** Do we have the correct, *minimal* Slice-7 preflight surface (exactly five deterministic checks) with an error interface that can be wired into the generator without changing the CLI?

**Evidence required:**
- The executor pastes:
  - the public function signature(s) from `src/alfred/validate/preflight.py`
  - a short snippet showing how each check produces a distinct, human-readable error (e.g., exception messages or structured error rendering)
  - a list of the exact five checks implemented (A–E) mapping to code locations

| Observation | Likely call |
|---|---|
| Exactly 5 checks implemented; each deterministic; clear error messages; no generator coupling | PROCEED |
| Checks exist but error reporting is too opaque, or wiring assumptions are embedded in validator | PIVOT |
| Any check requires LLM semantics, adds post-generation validation, or weakens continuity rule | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Wire pre-flight into generator before planner/LLM call

**Goal:** Ensure `scripts/generate_next_canonical_handover.py` hard-fails on preflight errors **before any LLM call**, while preserving Slice 6 renderer-derived identity and existing CLI flags.

### Implementation

1. **Identify the earliest safe wiring point**
   - Insert preflight after the generator has enough information to:
     - know the active planning row / handover inputs (from Slice 6 renderer)
     - know which docs will be used for context roles
   - But it must run **before** any planner/LLM call is made.
   - Build one deterministic context-input plan first (scope doc paths, carry-forward items, continuity source path), and feed that same plan into both preflight and the later planner-context assembly so validation and runtime cannot drift.
   - Construct that plan before any "missing file" filtering step; a missing scope doc must fail loudly rather than disappearing from the packet builder's input set.

2. **Hard-fail behavior**
   - On any preflight failure:
     - exit non-zero
     - print a clear error summary
     - confirm no planner invocation happened

3. **Preserve CLI surface**
   - Do not add/remove flags.
   - Preserve the Slice 6 `--dry-run` non-destructive verification flow (exists today).
   - If `--dry-run` currently avoids the planner call, preflight should still run (because it validates inputs), unless that would conflict with established behavior; if behavior changes, it must be explicitly called out and approved at CHECKPOINT-2.

4. **No workflow generalization**
   - Keep changes minimal and local to preflight wiring.

### Verification

```bash
# script-level tests (repo has existing tests around generator; run all)
pytest -q

# optional: run the generator in dry-run mode to confirm preflight runs and passes
python scripts/generate_next_canonical_handover.py --dry-run
```

**Expected:**
- When a preflight check fails, the script exits before any planner/LLM call.
- Existing CLI flags still work.
- Dry-run remains non-destructive and continues to be a useful verification path.

**Suggested commit message:** `generator: task 2 — run preflight before planner call (fail fast)`

### CHECKPOINT-2 — Generator is provably fail-fast before any LLM call

**Question:** Can we prove (with deterministic tests) that preflight failures prevent any planner/LLM invocation and that we didn’t accidentally change the CLI contract?

**Evidence required:**
- The executor pastes:
  - the exact code location in `scripts/generate_next_canonical_handover.py` where preflight runs relative to planner invocation
  - test output (or test names + assertions) showing a failing preflight blocks the planner call
  - `--help` output diff or an explicit statement that CLI flags are unchanged

| Observation | Likely call |
|---|---|
| Tests prove preflight runs before planner; negative test proves planner not invoked; CLI unchanged | PROCEED |
| Preflight runs but ordering is ambiguous or only manually verified; tests don’t prove “no LLM call” | PIVOT |
| CLI changed unexpectedly, or preflight occurs after planner starts, or continuity is inferred | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 3 — Add isolated negative tests and a real-ledger passing regression

**Goal:** Ensure each check has a negative test, plus an integration/regression test that the real seed ledger passes preflight.

### Implementation

1. **Create test module** — `tests/test_validate/test_preflight.py` (**to be created in this phase**, per test placement rule).

2. **Isolated negative tests (one per check)**
   - For each check A–E, create a deliberately malformed fixture (likely a malformed ledger fixture and/or minimal markdown fixtures) that triggers only that check.
   - Each test should assert:
     - the raised/returned error identifies the correct failure cause
     - error message includes the relevant path/id/value

3. **Integration regression: real ledger passes**
   - Add a test that loads the real seed ledger (the same one the generator uses today) and asserts preflight passes.

4. **Negative integration: next_handover_id mismatch blocks planner invocation**
   - Add a test that simulates a mismatch between planning row handover id and previous handover’s `next_handover_id`, and asserts the generator fails before calling the planner.
   - This test must be deterministic and must not require an actual LLM.

### Verification

```bash
pytest -q
```

**Expected:**
- 5 negative tests minimum (A–E).
- 1 passing regression for the real ledger.
- 1 negative integration test proving “no planner call on mismatch”.

**Suggested commit message:** `tests: task 3 — preflight coverage (negative checks + real-ledger regression)`

---

## WHAT NOT TO DO

1. Do **not** introduce any LLM-judge or semantic scoring into preflight or any other validator (deterministic only).
2. Do **not** start Slice 8 post-generation validators or Slice 9 failed-candidate naming logic.
3. Do **not** weaken Slice 6 continuity by inferring `previous_handover` from phase ordering; missing/malformed continuity must fail loudly.
4. Do **not** “fix” failures by silently dropping docs from context roles; preflight should surface the problem, not mask it.
5. Do **not** add new CLI flags or change the meaning of existing ones as part of wiring.
6. Do **not** implement Check A by validating only the planning row's direct `scope_sources`; validate the real `scope` role inputs the generator will register.
7. Do **not** let nonexistent scope docs disappear via preflight inputs that were already filtered by `Path.is_file()` or equivalent; missing paths must remain visible to the validator.

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

**next_handover_id:** ALFRED_HANDOVER_20
