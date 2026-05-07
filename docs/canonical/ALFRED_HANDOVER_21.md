# Alfred's Handover Document #21 — Concern X, Slice 9: FAILED_CANDIDATE Filename Short-Circuit

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_21
**date:** 2026-05-07
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_20
**baseline_state:** Slice 7 pre-flight and Slice 8 post-generation validators exist today and the generator writes `*_FAILED_CANDIDATE.md` on validation failure, but the structural validator still flags id/filename mismatches on those debug artifacts.

**Reference Documents:**
- `CONTEXT.md` — defines the protocol constraints this slice must obey (document-as-protocol, checkpoint gates, typed context roles, and the **No-LLM-Judge** rule).
- `docs/active/POST_GRILL_1.md` — authoritative scope for Slice 9: implement `*_FAILED_CANDIDATE.md` filename short-circuit in `scripts/validate_alfred_handover.py` and add tests proving “id/filename checks skipped” while “other checks still run”.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — rationale for the validation-chain and protocol seams we must not blur; reinforces “deterministic validators only” and that the canonical markdown remains the reviewed control surface.
- `docs/canonical/ALFRED_HANDOVER_20.md` — continuity for the just-ratified Slice 8 behavior (postgen blocks promotion + writes `FAILED_CANDIDATE`) and the forward plan that seeds this slice.

This phase exists to narrow a sharp edge in the validator workflow: once Slice 8 began writing `*_FAILED_CANDIDATE.md` artifacts for debugging, the existing structural validator’s id/filename consistency checks started producing spurious noise (because the artifact filename intentionally does not match the handover id). The fix is intentionally small and deterministic: detect `*_FAILED_CANDIDATE.md` by filename in `scripts/validate_alfred_handover.py`, skip only the id/filename checks, and keep every other structural check unchanged.

---

## WHAT EXISTS TODAY

### Git History

```
6d90558  handover: close out slice 8 and seed slice 9
ec760bb  tests: task 3 — postgen coverage (negatives + known-good regression)
5f9df44  tests: checkpoint-2 follow-up — script-boundary proof postgen blocks promotion
743c504  generator: task 2 — run postgen before promotion; write FAILED_CANDIDATE on failure
0d12e89  validate: tighten checkpoint-1 — task-to-brief mapping + non-empty hard-rule phrases
6501085  added handover
8382a90  validate: task 1 — add post-generation validator (six deterministic checks)
f2559a1  handover: close out slice 7 and seed slice 8
3cb4c4c  tests: task 3 — preflight coverage (negative checks + real-ledger regression)
8a05341  generator: task 2 — run preflight before planner call (fail fast)
a9f6d66  validate: task 1 — add preflight validator (5 deterministic checks)
b052fd8  docs: clarify slice 7 scope-input preflight
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Validation-chain and generator surfaces (relevant to this slice)

- FastAPI app **exists today** as a single module at `src/alfred/api.py` (not in scope to change).
- Agent modules **exist today** under `src/alfred/agents`: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`.
- Tool modules **exist today** under `src/alfred/tools`: `board_write_contract`, `docs_policy`, `git_log`, `github_api`, `handover_authoring_context`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`, `story_markdown`.
- The canonical handover generator **exists today** at `scripts/generate_next_canonical_handover.py` and uses a checkpoint-gated flow:
  - Slice 7: deterministic pre-flight validation runs **before any LLM call**.
  - Slice 8: deterministic post-generation validation runs after planner return; failures write a `*_FAILED_CANDIDATE.md` artifact and block promotion.
- The structural validator script **exists today** at `scripts/validate_alfred_handover.py` and is invoked in the overall chain to enforce section-contract and other deterministic structural constraints.

### Key Design Decisions Inherited (Do Not Revisit)

1. **No LLM-judge anywhere in validation** — every pre-flight / post-generation / structural validator must be deterministic code only (per `CONTEXT.md` / ADR-0003 cited there).
2. **Checkpoint-gated execution remains the control surface** — on failure, we produce a debuggable artifact and block promotion; “semantic judgment” happens at human review, not inside validators.
3. **FAILED_CANDIDATE artifacts are debugging surfaces, not protocol artifacts** — they should be easy to inspect, but must not be promoted or treated as canonical.
4. **Slice 9 is narrow** — only apply a filename-pattern short-circuit inside the structural validator; do not change Slice 7 pre-flight or Slice 8 post-generation behavior.

---

## HARD RULES

1. **Slice 9 only:** implement filename short-circuit on the structural validator; do not start Slice 10+ work.
2. **No LLM-judge anywhere:** the short-circuit must be deterministic code only.
3. **Preserve Slice 7 and Slice 8 gates:** the short-circuit applies only to the structural validator on `*_FAILED_CANDIDATE.md` files.
4. **FAILED_CANDIDATE lifecycle stays unchanged:** do not promote them, alter how they are written, or extend their metadata contract.
5. **Short-circuit is narrow:** skip only the id/filename structural checks; all other structural checks must still run.

---

## WHAT THIS PHASE PRODUCES

- `scripts/validate_alfred_handover.py` updated so inputs whose filename matches `*_FAILED_CANDIDATE.md` skip id/filename checks while running every other structural check unchanged.
- `tests/test_scripts/test_validate_alfred_handover.py` updated with synthetic fixtures proving:
  - id/filename mismatch errors are suppressed for `*_FAILED_CANDIDATE.md`, and
  - unrelated structural failures still fail the validator (demonstrating “other checks still run”).

Out of scope:
- Any changes to `scripts/generate_next_canonical_handover.py`.
- Any changes to Slice 7 pre-flight or Slice 8 post-generation validators.
- Any generalization beyond filename pattern matching.
- Any new workflow, schema, or agent modules.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Implement FAILED_CANDIDATE filename short-circuit | `scripts/validate_alfred_handover.py` skips id/filename checks only when filename matches `*_FAILED_CANDIDATE.md` | CHECKPOINT-1 |
| 2 | Add script-boundary tests for both guarantees | `tests/test_scripts/test_validate_alfred_handover.py` proves id-skip + other-checks-still-run | CHECKPOINT-2 |

---

## TASK 1 — Implement FAILED_CANDIDATE filename short-circuit in structural validator

**Goal:** Update `scripts/validate_alfred_handover.py` so `*_FAILED_CANDIDATE.md` files do not produce id/filename mismatch errors, while all other validations still run unchanged.

### Implementation

1. **Locate the id/filename check(s)** — in `scripts/validate_alfred_handover.py`, identify the specific check(s) that compare:
   - the document’s internal `**id:** ...` value (or equivalent parsed id), and/or
   - the expected filename derived from the id.
2. **Define the short-circuit predicate** — a deterministic helper such as:
   - “is this path’s basename matching the suffix `_FAILED_CANDIDATE.md`?”
   Keep it strictly filename-based (per slice scope).
3. **Apply narrow skip** — conditionally skip only those id/filename consistency checks when the predicate is true.
   - Do **not** skip parsing, section-contract validation, reference-tag parsing, or any other check.
   - Ensure the rest of the validation pipeline executes in the same order.
4. **Keep operator output stable** — avoid changing unrelated error formatting; only remove id/filename mismatch messages for these files.

### Verification

```bash
python -m pytest -q
```

**Expected:**
- Existing tests continue to pass (no behavior change for non-FAILED_CANDIDATE files).
- New tests added in Task 2 demonstrate the new behavior for `*_FAILED_CANDIDATE.md`.

**Suggested commit message:** `validate: slice 9 — skip id/filename checks for *_FAILED_CANDIDATE.md`

### CHECKPOINT-1 — Short-circuit correctness (narrow + deterministic)

**Question:** Does the structural validator skip *only* id/filename checks for `*_FAILED_CANDIDATE.md` while leaving all other checks and outputs unchanged?

**Evidence required:**
- A link or pasted snippet (verbatim) of the updated code section in `scripts/validate_alfred_handover.py` showing:
  - the filename predicate, and
  - the conditional skip around the id/filename check(s).
- A sample validator run (verbatim CLI output) for a `*_FAILED_CANDIDATE.md` file that:
  - does **not** include id/filename mismatch errors, and
  - does include at least one other failure when present.

| Observation | Likely call |
|---|---|
| Predicate is strictly filename-based; only id/filename checks are skipped; other checks still execute | PROCEED |
| Predicate is too broad (e.g., skips whole validator or multiple checks) or behavior differs for non-FAILED_CANDIDATE | PIVOT |
| Changes touch Slice 7/8 gates, FAILED_CANDIDATE lifecycle, or introduces non-determinism/LLM | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Add tests proving id-skip and other-checks-still-run

**Goal:** Add tests that (a) prove id/filename mismatch errors are suppressed for `*_FAILED_CANDIDATE.md`, and (b) prove other structural checks still run and can fail for the same file.

### Implementation

1. **Create a synthetic FAILED_CANDIDATE fixture** — in `tests/test_scripts/test_validate_alfred_handover.py`, add a test that writes a temporary file whose filename ends with `_FAILED_CANDIDATE.md` and whose contents intentionally include:
   - an id that would normally imply a different filename (to trigger the would-be id/filename error), and
   - a separate, unrelated structural violation.

   The unrelated violation should be something the structural validator deterministically checks today (example from slice brief: malformed reference tag), so the test confirms “other checks still run.”

2. **Assert both halves of the contract**
   - Assert that the output does **not** contain the id/filename mismatch complaint for the FAILED_CANDIDATE input.
   - Assert that the output **does** contain the unrelated structural failure message.

3. **Add at least one negative test dedicated to the short-circuit**
   - Option A: A FAILED_CANDIDATE file that would *only* fail id/filename checks, and should now pass structural validation (if the validator script has a “no errors” return surface).
   - Option B (if the script always expects some minimal structure): a case where id mismatch is present but the test checks specifically that the id mismatch error is absent (even if other failures exist).

4. **Keep tests script-boundary oriented** — prefer calling the validator entrypoint in the same way production does (mirroring the Slice 7/8 testing approach), to reduce false confidence from unit-testing internal helpers only.

### Verification

```bash
python -m pytest -q tests/test_scripts/test_validate_alfred_handover.py
```

**Expected:**
- A `*_FAILED_CANDIDATE.md` fixture with id/filename mismatch does **not** fail on id/filename mismatch.
- The same fixture still fails on the unrelated structural check (proving other checks still run).

**Suggested commit message:** `tests: slice 9 — validate FAILED_CANDIDATE skips id check but keeps other checks`

### CHECKPOINT-2 — Test sufficiency (proves both guarantees)

**Question:** Do the tests deterministically prove both: “id/filename checks are skipped for FAILED_CANDIDATE” and “all other checks still run unchanged”?

**Evidence required:**
- The full diff (or pasted snippets) of the new/updated tests in `tests/test_scripts/test_validate_alfred_handover.py`.
- The pytest output showing the tests pass.

| Observation | Likely call |
|---|---|
| One test demonstrates id mismatch is suppressed; another assertion demonstrates a different structural check still fails on the same input | PROCEED |
| Tests pass but do not actually exercise the would-have-failed id/filename check (false positive) | PIVOT |
| Tests rely on non-deterministic behavior, external network, or LLM calls | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do **not** broaden the skip to “skip all structural validation” for FAILED_CANDIDATE files — only id/filename checks are exempt.
2. Do **not** modify Slice 7 pre-flight or Slice 8 post-generation validators, their call order, or their failure semantics.
3. Do **not** change how `scripts/generate_next_canonical_handover.py` writes FAILED_CANDIDATE artifacts (format/lifecycle/metadata).
4. Do **not** introduce an LLM-based judge or any non-deterministic heuristics into `scripts/validate_alfred_handover.py`.
5. Do **not** generalize the exemption beyond the filename pattern (no content-based detection; no new metadata fields).

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

**next_handover_id:** ALFRED_HANDOVER_22