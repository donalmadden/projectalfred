# Alfred's Handover Document #14 — Concern X, Slice 2: Phase Ledger Schema + Seed File

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0  
**id:** ALFRED_HANDOVER_14  
**date:** 2026-05-05  
**author:** Planner (draft; human to approve)  
**previous_handover:** ALFRED_HANDOVER_13  
**baseline_state:** Alfred has a working canonical handover workflow; Slice 1 cleanup is ratified; Slice 2 will add an additive phase-ledger scaffold (typed YAML + loader + seed file) with no generator behavior changes yet.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_13.md` — ratified completion of Concern X Slice 1 and explicit forward plan to Slice 2 only; locks “do not start Slice 3+” constraints.
- `docs/active/POST_GRILL_1.md` — authoritative Slice 2 scope: new ledger models + loader + seed docs/active/PHASE_LEDGER.yaml, with specific test strategy and acceptance criteria.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — resolved design constraints that Slice 2 must honor: “phase ledger” naming, authority flow (handover → ledger), brief is human-authored, and no-LLM-judge validation chain.

This handover plans **Concern X — Slice 2 only**: introduce a **typed YAML Phase Ledger** as a *derived, additive scaffold* that will later let the generator become a renderer (Slice 6), but **does not change** `scripts/generate_next_canonical_handover.py` in this slice. The ledger is explicitly **not** the source of truth: canonical handovers remain authoritative; the ledger is a mechanical derived view that can be reviewed and diffed.

---

## WHAT EXISTS TODAY

### Git History

```
8a8be72  cleanup: task 3 — fill post-mortem in ALFRED_HANDOVER_13
2ade6f7  cleanup: task 2 — delete 3 stale prose-assertion tests from canonical handover generator test module
025203c  cleanup: task 1 — delete obsolete dogfood/phase7 scripts and test
4103fa2  HANDOVER 13 updated
5dd5297  added 1st post-grill content & updates
08e7ff8  demo successfully ran
d51c8fe  added handover
a813021  phase5: add product-owner companion to the demo script
7790fbc  phase4: add operator scripts for resuming and backfilling the demo board
30ecf6e  phase4: render story bodies and support user-owned project boards
096e616  demo script finalised
f65a427  ready for demo
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Repo topology relevant to this slice

- Agent modules under `src/alfred/agents` **exist today**: `compiler.py`, `planner.py`, `quality_judge.py`, `retro_analyst.py`, `story_generator.py`.
- Tool modules under `src/alfred/tools` **exist today**: `board_write_contract.py`, `docs_policy.py`, `git_log.py`, `github_api.py`, `handover_authoring_context.py`, `llm.py`, `logging.py`, `persistence.py`, `rag.py`, `reference_doc_validator.py`, `repo_facts.py`, `story_markdown.py`.
- FastAPI app **exists today** at `src/alfred/api.py` (single-module structural rule; do not introduce src/alfred/api).
- `pyproject.toml` **exists today** with `[project]=True` and `[project.scripts]=True` and `alfred.cli:main`.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Slice discipline is mandatory**: implement **Slice 2 only**. Do not start Slice 3+ (doc-section contracts, renderer replacement, reference-tag parser changes, preflight/postgen validators, etc.). (From `docs/canonical/ALFRED_HANDOVER_13.md`, `docs/active/POST_GRILL_1.md`.)
2. **Phase ledger is a derived view, not authority**: authority flows **canonical handover → phase ledger**, never the reverse. Also: do not call it a “manifest” (term already taken by `docs/DOCS_MANIFEST.yaml`). (From `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)
3. **Brief is human-authored**: the brief is an editorial seed (including `hard_rules` and ordered task seeds) and must be modeled as such; deterministic extraction from other docs is future work. When field names differ between the older illustrative YAML sketch in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` and the resolved glossary in `CONTEXT.md`, treat `CONTEXT.md` as authoritative for field names. (From `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`, `CONTEXT.md`.)
4. **Deterministic validation chain; no LLM judge**: if validation is added later it must be deterministic only. For Slice 2, we only validate via Pydantic + unit tests; do not add any LLM-based “judge” logic. (From `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)

---

## HARD RULES

1. **No behavior change to the canonical generator in this slice**: do not modify `scripts/generate_next_canonical_handover.py` (per Slice 2 acceptance criteria in `docs/active/POST_GRILL_1.md`).
2. **Ledger is additive scaffolding only**: create new modules/files, but do not rewire runtime orchestration to use them yet.
3. **Keep naming + authority constraints**:
   - Name it **Phase Ledger** (not manifest).
   - Canonical handovers remain the protocol surface; the ledger is a derived view.
4. **Validation is deterministic only**: Pydantic schema validation + unit tests. No LLM judge.
5. **Respect repo placement rules for new files**:
   - New python package code belongs under `src/alfred/...`.
   - New tests belong under `tests/` as `test_*.py`.
   - New docs belong under `docs/` as `*.md` (and the seed YAML belongs under `docs/active/` as specified by Slice 2).

---

## WHAT THIS PHASE PRODUCES

- A new ledger package **to be created in this phase** at `src/alfred/ledger/` containing:
  - `src/alfred/ledger/__init__.py` — package marker.
  - `src/alfred/ledger/models.py` — Pydantic models: `Phase`, `PhaseLedger`, `Brief`, plus validation rules.
  - `src/alfred/ledger/loader.py` — `load_ledger(path) -> PhaseLedger` reading YAML and returning validated models with precise errors.
- A seed ledger file **to be created in this phase**: `docs/active/PHASE_LEDGER.yaml` populated with phases `0–5` as a mechanical, derived view of canonical handovers (no behavior change yet).
  - Before writing the seed file, read the illustrative YAML block in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` for overall document shape (`project`, `plan_path`, `phases`, `scope_sources`, `scope_carry_forward`).
  - Treat that YAML block as a shape example only. If any field names in the sketch conflict with the resolved terminology in `CONTEXT.md`, follow `CONTEXT.md`.
- Tests **to be created in this phase**:
  - `tests/test_ledger/test_models.py`
  - `tests/test_ledger/test_loader.py`

Out of scope:
- Any renderer work (Slice 6) or generator changes.
- Any reference-tag parser changes (Slice 3) or doc-class section-contract work (Slice 4).
- Any preflight/postgen validator introduction (Slices 7–8).
- Any automation that “extracts” the brief from existing docs.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Add Phase Ledger Pydantic schema | `src/alfred/ledger/models.py` + tests | CHECKPOINT-1 |
| 2 | Add YAML loader + seed ledger | `src/alfred/ledger/loader.py`, `docs/active/PHASE_LEDGER.yaml` + tests | (optional) |

---

## TASK 1 — Add Phase Ledger Pydantic schema

**Goal:** Introduce typed models for `Phase`, `PhaseLedger`, and `Brief` with the validation rules required by Slice 2.

### Implementation

1. **Create the ledger package** — add:
   - `src/alfred/ledger/__init__.py` (new package marker)
   - `src/alfred/ledger/models.py`

2. **Model `Brief` (human-authored editorial seed)** in `src/alfred/ledger/models.py`.
   - Include fields that match the resolved constraints in `CONTEXT.md` and `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.
   - When those two sources differ, `CONTEXT.md` wins for field names because it is the resolved glossary.
   - `title` (string)
   - `goal` (string)
   - `hard_rules` (list of strings)
   - `tasks` (ordered list of task seeds; each seed includes at least `id`, `title`, `intent`)
   - `out_of_scope` (list of strings)
   - `definition_of_done` (list of strings)
   - `followups_from_prior_phase` (list of strings)
   - Keep it strictly data: no behavior, no I/O.

3. **Model `Phase`** with the mechanical identity + lifecycle fields needed for Slice 2.
   - Minimum expected fields (aligning to `docs/active/POST_GRILL_1.md` and the resolved “phase ledger” concept):
     - `id` (int)
     - `title` (string)
     - `status` (enum-like string; at least `ratified` vs `planning`)
     - `handover_id` (string, optional depending on status)
     - `scope_sources` (list of strings; may be empty or omitted depending on what you decide is required)
     - `scope_carry_forward` (list of ints; for later slices; may be optional for Slice 2)
     - `brief` (optional `Brief`)

4. **Model `PhaseLedger`** as the top-level document.
   - Include a `project` identifier (string) if needed for future renderer work; keep it stable and simple.
   - Read the YAML sketch in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` before writing `docs/active/PHASE_LEDGER.yaml`; it is the authoritative example for overall seed-file shape, but not for stale field names superseded by `CONTEXT.md`.
   - Include `phases: list[Phase]`.
   - Add any additional top-level metadata only if it is clearly justified; avoid inventing fields.

5. **Add validation rules (must be deterministic, in-schema)**:
   - **Reject ratified rows without `handover_id`**.
   - **Reject briefs attached to ratified phases** (brief is only for unratified/planning phases).
   - **Reject malformed ledgers** with clear Pydantic errors (e.g., missing required fields, wrong types).
   - Consider (optional but useful) ledger-level validations:
     - Unique `Phase.id` values.
     - Status value is one of allowed set.

6. **Add unit tests** (per test placement rule: tests go under `tests/` as `test_*.py`):
   - Create `tests/test_ledger/test_models.py`.
   - Test cases should include:
     - “good” objects validate.
     - ratified-without-handover-id rejects.
     - brief-on-ratified rejects.
     - missing required fields rejects.

### Verification

```bash
pytest -q
pyright
```

**Expected:**
- Tests in `tests/test_ledger/test_models.py` pass.
- `pyright` reports no type errors introduced by the new package.

**Suggested commit message:** `ledger: task 1 — add PhaseLedger Pydantic models + validation`

### CHECKPOINT-1 — Schema acceptance before adding I/O and seed file

**Question:** Do the models and validation rules match Slice 2 constraints (derived ledger, human-authored brief, ratified constraints) without overreaching into future slices?

**Evidence required:**
- Paste the full contents (or a link in the PR) of:
  - `src/alfred/ledger/models.py`
  - `tests/test_ledger/test_models.py`
- Paste the output of:
  - `pytest -q`
  - `pyright`

| Observation | Likely call |
|---|---|
| All required validations exist; tests cover ratified-without-handover-id + brief-on-ratified; no generator changes | PROCEED |
| Models work but field set for `Brief` or `Phase` is under/over-specified vs the referenced docs | PIVOT |
| Any generator script changes were made, or validation depends on LLM/judging, or schema is missing the required rejection rules | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do **not** modify `scripts/generate_next_canonical_handover.py` in this slice (even to “wire it up” to the ledger).
2. Do **not** introduce doc-section contract machinery, reference-tag parsing changes, or context bundle rendering (those are later slices).
3. Do **not** describe the ledger as a new protocol authority; it is a derived scaffold.
4. Do **not** introduce any LLM-based “validation” or “judge” step.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- Slice discipline held: `scripts/generate_next_canonical_handover.py` was not touched, no renderer/preflight work leaked in, and the ledger sits as a purely additive scaffold under `src/alfred/ledger/`.
- Pydantic-only validation was sufficient to express every Slice 2 rejection rule (ratified-without-`handover_id`, brief-on-ratified, unique phase ids, status enum, missing required fields). No LLM judge was needed or introduced.
- The two-commit shape per task (`f362de3` for models, `9ecbf65` for loader + seed) kept the diff easy to review and matched the "one task = one commit" rule.
- Seeding from the already-ratified phases 0–5 of the blank-project kickoff demo gave the loader a real fixture to round-trip against, which caught field-naming drift early (see deviations).
- 21 tests across `tests/test_ledger/` pass; the loader test suite exercises both the live seed file and synthetic error paths under `tmp_path`, so the seed file is not the only thing covered.

**What was harder than expected:**
- Reconciling the illustrative YAML sketch in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` with the resolved glossary in `CONTEXT.md`: the sketch used `follow_ups` and implied a `plan_path`, while `CONTEXT.md` had already resolved the field name to `followups_from_prior_phase`. The plan as originally written did not call this conflict out, which is why the Brief field set had to be corrected mid-slice.
- Deciding what to do with `plan_path`: it appears in the sketch but had no acceptance criterion in `POST_GRILL_1.md`. Resolved by making it optional on `PhaseLedger` so the seed could carry it without forcing future ledgers to.
- Choosing the right level for status validation. `Literal["ratified", "planning"]` was preferred over a real `Enum` because the ledger is YAML-first and Pydantic surfaces clearer errors against a `Literal` for hand-edited files.

**Decisions made during execution (deviations from this plan):**
- *Renamed `Brief.follow_ups` → `Brief.followups_from_prior_phase`* to match `CONTEXT.md` as the resolved glossary. Also added an optional `plan_path: str | None` to `PhaseLedger` to match the YAML sketch shape. Committed as `914268c`. Approved by: planner clarification recorded in this same handover (HARD RULES item 3 was amended in the same commit window to make `CONTEXT.md` authoritative on field names; this document now carries that clarification directly).
- *Added `LedgerLoadError`* as a thin wrapper around YAML, type, and Pydantic validation failures so errors carry the originating file path. Not explicitly required by the plan but consistent with "precise errors" in the deliverable list. Approved by: executor judgment, scope-preserving (no new dependency, no behavior change to the generator).
- *Added a `TaskSeed` Pydantic model* for the items in `Brief.tasks` rather than a free-form `list[dict]`. This is stricter than the plan's "list of task seeds" wording but keeps validation deterministic and was needed to make `id`/`title`/`intent` enforceable. Approved by: executor judgment.
- *Skipped CHECKPOINT-1's "STOP HERE" gate* and proceeded to Task 2. The checkpoint was satisfied verbally rather than recorded in the document; this is a process gap to flag, not a scope deviation. Approved by: human (Donal), out-of-band.

**Forward plan:**
- `ALFRED_HANDOVER_14.md` now includes the field-name precedence clarification, the seed-file note about reading the illustrative YAML sketch, and this post-mortem. Keep those clarifications inherited as stable context when drafting HANDOVER_15.
- HANDOVER_15 should pick up Slice 3 (reference tag canonicalization) per `docs/active/POST_GRILL_1.md`. Slice 4 is the doc-class section-contract slice. The ledger remains additive until Slice 6 turns the generator into a renderer; do not wire `load_ledger` into the generator before then.
- When Slice 6 lands, the seed `docs/active/PHASE_LEDGER.yaml` will need a `planning`-status row with a populated `Brief` to exercise the renderer path; today every phase in the seed is `ratified`, so the brief-on-planning code path is only covered by unit tests, not by the live fixture.
- Consider tightening `PhaseLedger` later with a cross-phase invariant that every `id` in `scope_carry_forward` refers to an existing earlier phase. Deliberately deferred from Slice 2 to avoid scope creep, but it is the natural next validation rule once the renderer needs it.

**next_handover_id:** ALFRED_HANDOVER_15
