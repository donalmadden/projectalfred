# Alfred's Handover Document #4 Bug Scrub — Repairing the Phase 6 Draft

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_4_BUG_SCRUB
**date:** 2026-04-17
**author:** Donal
**previous_handover:** ALFRED_HANDOVER_4
**baseline_state:** Phase 5 is complete. The phase-close handover state is commit `fd724e1` (`phase5: task 6 — dogfood #2`), with executable runtime behavior validated against commit `79e2ce5` (`phase5: task 5 — hitl timeout`) and documented in `ALFRED_HANDOVER_4.md`. A locally generated `docs/ALFRED_HANDOVER_5_DRAFT.md` now exists, produced via `scripts/generate_phase6.py` after fixing its `PlannerInput` assembly. The draft is promising but not yet safe to approve as protocol because it contains several repo-contract mismatches and house-style omissions.

**Reference Documents:**
- `~/code/projectalfred/docs/ALFRED_HANDOVER_4.md` — authoritative Phase 5 handover and post-mortem
- `~/code/projectalfred/docs/ALFRED_HANDOVER_5_DRAFT.md` — generated Phase 6 draft requiring scrub
- `~/code/projectalfred/docs/architecture.md` — methodology and design constraints
- `~/code/projectalfred/src/alfred/orchestrator.py` — actual `orchestrate()` contract
- `~/code/projectalfred/src/alfred/schemas/agent.py` — actual planner and agent I/O schemas
- `~/code/projectalfred/src/alfred/tools/llm.py` — actual tool-level exception surface
- `~/code/projectalfred/pyproject.toml` — actual dev tooling and test/type-check config
- `~/code/projectalfred/scripts/generate_phase6.py` — local script that generated the draft

---

## WHAT EXISTS TODAY

### Current State

- `docs/ALFRED_HANDOVER_5_DRAFT.md` exists and is structurally useful.
- The draft captures the right Phase 6 ambition: property tests, evals, coverage, CI, and docs.
- The draft does **not** yet faithfully describe the current repository contracts.
- The mismatches are concentrated in three tiers:
  - **Tier 1 — blocking contract errors**: if left in place, they will send the executor to implement the wrong architecture.
  - **Tier 2 — repo/tooling alignment errors**: executable in spirit, but currently point to the wrong tools, paths, or baseline.
  - **Tier 3 — fidelity/style errors**: do not block execution by themselves, but make the handover less trustworthy and less consistent with the Alfred corpus.

### Error Register

| Tier | Error | Where in draft | Why it is wrong | Repair task |
|---|---|---|---|---|
| 1 | `orchestrate()` described as returning `RunResult` and never mutating input | Task 1 property-test section | Actual contract returns `HandoverDocument` and writes execution state into it | Task 1 |
| 1 | `ToolInputError` required as a common tool failure surface | Task 1 tool-contract section | No such shared exception exists in repo; boundaries differ by tool | Task 1 |
| 1 | Per-module coverage `fail_under` implied as native config | Task 3 coverage-gate section | Global fail-under is easy; per-module gates need an explicit checker script or equivalent | Task 1 |
| 2 | `mypy alfred/` named as repo type-check stage | Task 4 CI stage | Current dev tooling includes `pyright`, not `mypy` | Task 2 |
| 2 | `pytest tests/unit/` named as existing suite path | Task 4 CI stage | Repo has `tests/test_agents`, `tests/test_tools`, `tests/test_schemas`, `tests/test_api.py`, `tests/test_orchestrator.py`; no `tests/unit/` tree exists | Task 2 |
| 2 | Phase 5 recap says FastAPI endpoints and async event loop were the Phase 5 deliverable | Sprint context | That recaps earlier work and misses the actual Phase 5 outputs from `ALFRED_HANDOVER_4.md` | Task 2 |
| 3 | Draft does not use Alfred handover house style | Whole document | Missing context block, baseline/git history, hard rules, task overview, out-of-scope section, post-mortem conventions | Task 3 |
| 3 | Some open questions are really unresolved implementation choices; others are already answerable from repo state | Open questions section | Mixes true human decisions with accidental uncertainty introduced by the draft | Task 3 |

### Key Design Decisions Inherited (Do Not Revisit)

1. The current codebase is the source of truth for contracts. The draft must be corrected to match the code, not the other way around, unless a human explicitly approves a redesign.
2. `orchestrate()` returns a `HandoverDocument` and may raise documented control-flow exceptions. It is not a pure planner-style function.
3. There is no shared `ToolInputError` abstraction today. Do not invent one casually just to make the draft read cleanly.
4. The current repo type checker is `pyright`, not `mypy`.
5. The current test tree is not split into `tests/unit/`; Phase 6 may add `tests/property/`, but it must coexist with the existing layout.
6. The Alfred handover corpus has a consistent style. The final Phase 6 handover should look like `ALFRED_HANDOVER_4.md`, not like a generic generated project plan.

---

## HARD RULES

1. **Do not change runtime architecture just to satisfy the faulty draft.** First repair the draft so it matches the repo.
2. **Do not invent `RunResult` or `ToolInputError`** unless a human explicitly approves that broader API redesign.
3. **Do not add `mypy` as a hidden prerequisite.** If the final approved plan wants `mypy`, it must say so explicitly and update `pyproject.toml`.
4. **Do not require a `tests/unit/` reorg** as a side effect of Phase 6 unless a human explicitly approves that churn.
5. **Keep the final Phase 6 handover in Alfred house style.** Context block, references, hard rules, task overview, verification, checkpoints, and post-mortem are required.
6. **Treat uncommitted local artifacts carefully.** `docs/ALFRED_HANDOVER_5_DRAFT.md` and `scripts/generate_phase6.py` are currently working-tree artifacts, not canonical history.
7. **One repair tier = one commit** if these fixes are executed as separate changes. Suggested messages appear under each task below.

---

## WHAT THIS SCRUB PRODUCES

- A repair plan that makes `docs/ALFRED_HANDOVER_5_DRAFT.md` repo-accurate.
- A mapping from each discovered error tier to concrete edits, file targets, and verification steps.
- A promotion checklist for turning the corrected draft into the real `docs/ALFRED_HANDOVER_5.md`.

Out of scope:
- Implementing Phase 6 itself
- Redesigning the orchestrator contract
- Introducing new shared exception abstractions without explicit approval
- Reorganizing the entire test tree for aesthetics alone

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Tier 1 Contract Repairs | Draft no longer references nonexistent contracts or impossible coverage config | CHECKPOINT-SCRUB-1 |
| 2 | Tier 2 Repo/Tooling Repairs | Draft commands, tools, and phase recap match the actual repo | |
| 3 | Tier 3 Fidelity Repairs | Draft normalized into Alfred handover house style | |
| 4 | Promotion Pass | Corrected draft promoted or copied to `ALFRED_HANDOVER_5.md` with final human review | CHECKPOINT-SCRUB-2 |

---

## TASK 1 — Tier 1 Contract Repairs

**Goal:** Remove every draft statement that points the executor at a contract the repo does not actually have.

### Implementation

1. **Repair the `orchestrate()` property-test target** in the Phase 6 draft:
   - Replace references to `RunResult` with the real return type: `HandoverDocument`.
   - Replace “never mutate its input argument” with repo-accurate invariants such as:
     - returns a `HandoverDocument`
     - only raises the documented control-flow exceptions (`CheckpointHalt`, `HumanEscalation`) rather than arbitrary exceptions
     - does not re-dispatch tasks whose `result` is already populated
     - writes checkpoint/task results back into the document as designed
   - If a non-mutation property is still desired, scope it to copied inputs in tests and describe that precisely instead of pretending the function is pure.

2. **Repair the tool-contract section** in the Phase 6 draft:
   - Remove all references to `ToolInputError`.
   - Replace them with a boundary-specific test strategy:
     - Pydantic request/model boundaries should fail validation before execution.
     - API layer invalid request shapes should map to FastAPI/Pydantic validation behavior.
     - `llm.complete()` failures should be described in terms of `LLMError`.
     - Tool property tests should assert “documented exception or validated rejection,” not a fake shared error type.

3. **Repair the coverage-gate mechanism** in the Phase 6 draft:
   - Replace any implication that per-module fail-under thresholds can be expressed directly as native coverage config.
   - Specify an explicit enforcement mechanism, for example:
     - `pytest --cov=alfred --cov-report=json`
     - a repo-local checker such as `scripts/check_coverage.py` that reads the JSON report
     - the checker enforces global and per-module thresholds
   - Keep the global `--cov-fail-under` if desired, but describe the per-module gate as custom enforcement.

4. **Make the draft explicit about what is unchanged**:
   - No new orchestrator return object.
   - No new shared tool exception class.
   - No coverage magic hidden in config.

### Verification

```bash
rg -n "RunResult|ToolInputError" docs/ALFRED_HANDOVER_5_DRAFT.md
rg -n "orchestrate\\(\\).*HandoverDocument|LLMError|check_coverage" docs/ALFRED_HANDOVER_5_DRAFT.md
```

**Expected:**
- no remaining `RunResult` references
- no remaining `ToolInputError` references
- the corrected draft explicitly references the real orchestrator and coverage-check flow

**Suggested commit message:** `phase6: scrub tier 1 — repair draft contracts`

---

## TASK 2 — Tier 2 Repo and Tooling Repairs

**Goal:** Align the Phase 6 draft with the repository’s real layout, tools, and completed Phase 5 baseline.

### Implementation

1. **Repair the CI/type-check section**:
   - Replace `mypy alfred/` with the current repo type-check tool: `pyright`.
   - If the final plan truly wants `mypy`, that must be reframed as new Phase 6 scope and must include `pyproject.toml` changes. Do not smuggle it in as if it already exists.

2. **Repair the test-path assumptions**:
   - Remove references to `pytest tests/unit/` unless a deliberate tree reorganization is separately approved.
   - Replace with repo-accurate commands, for example:
     - existing suite: `pytest tests/ --ignore=tests/property`
     - new property suite: `pytest tests/property/`
   - The draft may create `tests/property/`, but it must coexist with the current layout.

3. **Repair the Phase 5 recap**:
   - Replace the current summary with the actual outputs from `ALFRED_HANDOVER_4.md`:
     - handover compiler
     - critique loop
     - cost routing
     - RAG/compliance fixes
     - HITL timeout
     - dogfood #2
   - Remove or rewrite the “async event loop” claim unless it is specifically evidenced and intended.

4. **Repair documentation-tool assumptions**:
   - If the draft keeps `markdown-link-check`, it must say where that tool comes from and how it is installed.
   - Otherwise, replace that acceptance criterion with a repo-local verification approach already supported by project tooling.

5. **Repair any CI-provider ambiguity only if needed**:
   - It is fine to target GitHub Actions if that is the intended provider.
   - The final draft should present that as a chosen Phase 6 implementation target, not as uncertainty caused by lack of repo knowledge.

### Verification

```bash
rg -n "mypy|tests/unit|async event loop" docs/ALFRED_HANDOVER_5_DRAFT.md
rg -n "pyright|tests/property|pytest tests/" docs/ALFRED_HANDOVER_5_DRAFT.md
find tests -maxdepth 2 -type d | sort
```

**Expected:**
- no stale `mypy` or `tests/unit` references unless newly justified elsewhere
- commands in the draft match the actual repo layout
- Phase 5 recap matches `ALFRED_HANDOVER_4.md`

**Suggested commit message:** `phase6: scrub tier 2 — align draft with repo tooling`

---

## TASK 3 — Tier 3 Fidelity and House-Style Repairs

**Goal:** Turn the generated plan into a real Alfred handover rather than a generic project brief.

### Implementation

1. **Normalize the header and context**:
   - Add Alfred-style context metadata:
     - `schema_version`
     - `id`
     - `date`
     - `author`
     - `previous_handover`
     - `baseline_state`
   - Reference the real baseline:
     - Phase 5 closed in `ALFRED_HANDOVER_4.md`
     - code state validated at `79e2ce5`
     - handover/post-mortem recorded at `fd724e1`

2. **Add Alfred house sections**:
   - `WHAT EXISTS TODAY`
   - `HARD RULES`
   - `WHAT THIS PHASE PRODUCES`
   - `TASK OVERVIEW`
   - per-task verification blocks and suggested commit messages
   - `WHAT NOT TO DO`
   - executor post-mortem section matching the handover corpus style

3. **Tighten open questions**:
   - Keep only questions that truly require human judgment:
     - threshold values
     - fixture ownership
     - CI provider choice if still unresolved
     - strictness policy if intentionally open
   - Remove uncertainty that the repo already resolves, such as what the current type checker is or what the current test layout looks like.

4. **Make the final artifact promotion path explicit**:
   - `ALFRED_HANDOVER_5_DRAFT.md` is the generation artifact.
   - After scrub + approval, the canonical file should become `ALFRED_HANDOVER_5.md`.

### Verification

```bash
rg -n "^## CONTEXT|^## WHAT EXISTS TODAY|^## HARD RULES|^## TASK OVERVIEW|^## WHAT NOT TO DO|^## POST-MORTEM" docs/ALFRED_HANDOVER_5_DRAFT.md
```

**Expected:**
- the corrected draft now resembles `ALFRED_HANDOVER_4.md` in structure and level of operational detail

**Suggested commit message:** `phase6: scrub tier 3 — normalize handover style`

---

## TASK 4 — Promotion Pass

**Goal:** Promote the corrected draft into the real, executable Phase 6 handover.

### Implementation

1. Apply all Tier 1–3 corrections to `docs/ALFRED_HANDOVER_5_DRAFT.md`.
2. Perform a final read-through against this scrub document and `ALFRED_HANDOVER_4.md`.
3. If the corrected draft is approved, copy or rename it to `docs/ALFRED_HANDOVER_5.md`.
4. Preserve the generation artifact only if useful; otherwise treat `ALFRED_HANDOVER_5.md` as canonical.
5. Record any deviations from this scrub in the final handover post-mortem or in the commit message if they are minor.

### Verification

```bash
diff -u docs/ALFRED_HANDOVER_5_DRAFT.md docs/ALFRED_HANDOVER_5.md
rg -n "RunResult|ToolInputError|tests/unit|mypy alfred/" docs/ALFRED_HANDOVER_5.md
```

**Expected:**
- `ALFRED_HANDOVER_5.md` exists
- no stale blocking-contract strings remain
- the final handover is human-approved before execution begins

**Suggested commit message:** `phase6: promote scrubbed handover 5`

---

## CHECKPOINT-SCRUB-1 — Contract Accuracy Gate

**Question:** Has the Phase 6 draft been corrected so it no longer asks the executor to implement nonexistent contracts?

**Evidence required:**
- Updated `docs/ALFRED_HANDOVER_5_DRAFT.md`
- `rg` output showing no `RunResult` / `ToolInputError`
- Updated coverage-gate wording naming an explicit enforcement mechanism

| Observation | Likely call |
|---|---|
| All Tier 1 errors removed and draft now matches real code contracts | PROCEED to Tier 2/3 cleanup |
| Any fake contract remains (`RunResult`, `ToolInputError`, impossible coverage config) | STOP — repair draft before doing anything else |
| Coverage section partly repaired but still ambiguous about enforcement | PIVOT — tighten Task 3 wording before continuing |

---

## CHECKPOINT-SCRUB-2 — Promotion Gate

**Question:** Is the scrubbed Phase 6 handover now accurate enough to approve as protocol?

**Evidence required:**
- Final `docs/ALFRED_HANDOVER_5.md`
- Diff from the original generated draft
- Human review confirming open questions are truly human decisions

| Observation | Likely call |
|---|---|
| Tier 1–3 repairs complete; final handover matches repo and house style | APPROVE — Phase 6 handover may become protocol |
| Repo/tooling mismatches remain | BLOCK — do not approve yet |
| Content is accurate but still too generic or underspecified for execution | PROCEED WITH NOTES — one final specificity pass before approval |

---

## WHAT NOT TO DO

1. **Do NOT add new runtime abstractions** like `RunResult` or `ToolInputError` just because the draft mentioned them.
2. **Do NOT rewrite the orchestrator into a pure function** to make a property-test statement true.
3. **Do NOT reorganize the whole `tests/` tree** unless that reorg is explicitly approved for reasons beyond satisfying the draft.
4. **Do NOT add `mypy` silently** and then pretend it was always the plan.
5. **Do NOT approve `ALFRED_HANDOVER_5_DRAFT.md` in its current form** without applying this scrub.
6. **Do NOT lose the Phase 5 baseline.** `ALFRED_HANDOVER_4.md` remains the authoritative prior handover until `ALFRED_HANDOVER_5.md` is approved.

---

## POST-MORTEM

TBD

**What worked:**
- <fill in after scrub execution>

**What failed / findings:**
- <fill in after scrub execution>

**Forward plan:**
- <fill in after scrub execution>

**next_handover_id:** ALFRED_HANDOVER_5
