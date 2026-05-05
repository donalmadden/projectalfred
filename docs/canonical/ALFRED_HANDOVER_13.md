# Alfred's Handover Document #13 — Concern X, Slice 1: Repo Cleanup (Delete Obsolete Scripts + Stale Tests)

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_13
**date:** 2026-05-05
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_12
**baseline_state:** Phase 5 demo polish is ratified through ALFRED_HANDOVER_12; this phase shifts to Concern X seam-discipline migration and executes Slice 1 only: repo cleanup (deleting obsolete scripts/tests and removing known-stale assertions).

**Reference Documents:**
- `docs/active/POST_GRILL_1.md` — authoritative scope for Concern X Slice 1 (exact delete/edit list, acceptance criteria, and test strategy).
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — constrains the broader migration and explicitly marks the two scripts + tests as obsolete; also clarifies that the stale prose-assertion tests should be deleted (not “fixed”).
- `docs/canonical/ALFRED_HANDOVER_12.md` — continuity only (what was last ratified; confirms we are not reopening Phase 5 demo work).

This handover is a narrow cleanup phase intended to remove false-signal noise before the Concern X renderer/validator work begins. The goal is not to redesign any workflow or ship any new methodology scaffolding (phase ledger, section contracts, reference-tag parsing, validators, renderer replacement, etc.). The only changes are deletions of explicitly-obsolete scripts and their stale tests, plus a small targeted edit to remove three known-stale prose assertions in an existing test module.

---

## WHAT EXISTS TODAY

### Git History

```
5dd5297  added 1st post-grill content & updates
08e7ff8  demo successfully ran
d51c8fe  added handover
a813021  phase5: add product-owner companion to the demo script
7790fbc  phase4: add operator scripts for resuming and backfilling the demo board
30ecf6e  phase4: render story bodies and support user-owned project boards
096e616  demo script finalised
f65a427  ready for demo
af2c71f  updated to next handover
5fd60a7  installing Matt Pocock skills
811ff13  phase4: task 5 — fill in post-mortem; coverage audit complete
fe59615  phase4: task 4 — harness arc prints refusal, approval, write receipts
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Repo Surfaces Relevant To This Cleanup

- The repo contains a `scripts/` directory (exists today) and a `tests/` directory (exists today). This phase operates only on a small subset of those surfaces.
- Alfred’s runtime surfaces (agents/tools/API) are not being changed in this slice; the work here is housekeeping intended to reduce confusion and remove tests that encode now-rejected expectations.

**Partial state (explicit):**
- This handover does not introduce or complete any “declared but unimplemented” CLI/workflow items; it only removes obsolete artifacts and edits one test module.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Concern X migration is slice-driven and must start with Slice 1 cleanup only** (per `docs/active/POST_GRILL_1.md`).
2. **Obsolete artifacts should be deleted, not kept as “historical helpers”** when they create false signals about the current protocol direction (per `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`).
3. **Three currently-failing prose-assertion tests in `tests/test_scripts/test_generate_next_canonical_handover.py` are to be deleted during migration, not fixed** (per `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`).

---

## HARD RULES

1. **Slice discipline:** Execute **Slice 1 only**. Do not start later Concern X slices (phase ledger, brief extractor, context bundle roles/dedup, doc class section contract, renderer replacement, pre-flight/post-gen validators, failed-candidate behavior changes).
2. **Delete, don’t replace:** The obsolete scripts/tests listed in this handover must be removed, not reintroduced under new names.
3. **No new runtime product scope:** Do not change the FastAPI API surface, orchestrator behavior, agent logic, approval/write mechanics, or persistence schemas as part of this cleanup.
4. **Deterministic evidence only:** Verification must be based on deterministic commands (grep, test runs). No LLM-based “judge” step is permitted anywhere in the validation chain (migration-wide constraint reiterated in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`).

---

## WHAT THIS PHASE PRODUCES

- Deleted obsolete scripts:
  - `scripts/dogfood_run.py` (exists today; to be deleted in this phase)
  - `scripts/generate_phase7_canonical.py` (exists today; to be deleted in this phase)
- Deleted obsolete test:
  - `tests/test_scripts/test_generate_phase7_canonical.py` (exists today; to be deleted in this phase)
- Edited existing test module:
  - `tests/test_scripts/test_generate_next_canonical_handover.py` (exists today; to be edited in this phase) — remove **exactly** the three stale prose-assertion tests referenced by the Concern X docs.

Out of scope:
- Any phase-ledger implementation.
- Any new doc-class section-contract machinery.
- Any renderer replacement or fixture-based renderer tests (those land in later slices).
- Any refactor of `scripts/generate_next_canonical_handover.py` beyond removing imports that reference deleted files (and only if such imports exist).

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Delete obsolete scripts + their test | Remove the 2 scripts and 1 test file; repo no longer references them | CHECKPOINT-1 |
| 2 | Remove stale prose-assertion tests from canonical-handover generator test module | `tests/test_scripts/test_generate_next_canonical_handover.py` no longer contains the 3 known-stale assertions | |
| 3 | Regression verification: reference audit + full test run | Evidence bundle: grep results + test run summary showing no dependence on deleted files | |

---

## TASK 1 — Delete Obsolete Scripts + Their Test

**Goal:** Remove explicitly-obsolete scripts and their obsolete test so they cannot mislead future work or fail CI.

### Implementation

1. **Delete the two obsolete scripts** — remove these files:
   - `scripts/dogfood_run.py`
   - `scripts/generate_phase7_canonical.py`
2. **Delete the obsolete test module** — remove:
   - `tests/test_scripts/test_generate_phase7_canonical.py`
3. **Audit for references** (do not edit anything yet unless necessary):
   - Search in `scripts/`, `src/`, `tests/`, `pyproject.toml`, and `.github/` (if present) for imports, mentions, or CLI wiring pointing to the deleted scripts.
4. **Only if necessary:** edit `scripts/generate_next_canonical_handover.py` (exists today) to remove any import(s) of the deleted scripts.

### Verification

```bash
# 1) Prove the deleted files are gone
ls -la scripts/ | rg -n "dogfood_run\.py|generate_phase7_canonical\.py" || true
ls -la tests/test_scripts/ | rg -n "test_generate_phase7_canonical\.py" || true

# 2) Prove nothing still references them
rg -n "dogfood_run\.py|generate_phase7_canonical\.py|test_generate_phase7_canonical" scripts src tests pyproject.toml .github || true

# 3) Run tests (full suite per slice guidance)
pytest -q
```

**Expected:**
- The three deleted files do not appear in directory listings.
- `rg` finds **zero** references in `scripts/`, `src/`, `tests/`, `pyproject.toml`, and `.github/`.
- Test suite passes, or at minimum: there are no failures attributable to missing/deleted modules (if pre-existing unrelated failures exist, capture them in POST-MORTEM with counts).

**Suggested commit message:** `cleanup: task 1 — delete obsolete dogfood/phase7 scripts and test`

### CHECKPOINT-1 — Safe-Delete Gate (No Remaining References)

**Question:** Is it safe to proceed to the test-module edit knowing the deleted artifacts are fully unreferenced across code, tests, packaging, and CI?

**Evidence required:**
- Paste the exact `rg` command(s) output showing **no matches** (or, if there are matches, paste them verbatim).
- Paste the `pytest -q` summary line(s) (pass/fail).

| Observation | Likely call |
|---|---|
| `rg` shows zero references; `pytest -q` passes | PROCEED |
| `rg` shows references limited to comments/docs only (no imports/CLI hooks); `pytest -q` passes | PROCEED (optionally remove comment references if misleading, but keep scope tight) |
| `rg` shows imports/CLI wiring/CI steps referencing deleted files | PIVOT (remove/update those references within Slice 1 scope, then re-run verification) |
| `pytest -q` fails due to missing modules from these deletes | PIVOT (fix the referencing caller or revert deletes; do not “paper over” by re-adding obsolete scripts) |
| Significant unrelated failures appear | STOP (capture evidence + ask for human direction on whether to continue within Slice 1 or isolate failures first) |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do not start implementing Concern X “Slice 2+” items (phase ledger, brief, context roles/dedup, section contract, renderer replacement, pre-flight/post-gen validators).
2. Do not convert the removed scripts into “new improved” versions under different names in this phase.
3. Do not add new CI workflows as part of this cleanup (per workflow placement rule they would belong under `.github/workflows/*.yml`, but that is explicitly not needed for Slice 1).
4. Do not fix the stale prose-assertion tests by weakening assertions or rewriting expected prose; the plan is to delete those assertions.

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

**next_handover_id:** ALFRED_HANDOVER_14