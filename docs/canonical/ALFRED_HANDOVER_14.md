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
3. **Brief is human-authored**: the brief is an editorial seed (including `hard_rules` and ordered task seeds) and must be modeled as such; deterministic extraction from other docs is future work. (From `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)
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
- Tests **to be created in this phase**:
  - `tests/test_ledger/test_models.py`
  - `tests/test_ledger/test_loader.py`

Out of scope:
- Any renderer work (Slice 6) or generator changes.
- Any doc-class section-contract work (Slice 3) or reference-tag parser changes.
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
   - Include fields that match the constraints in `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`:
     - `title` (string)
     - `goal` (string)
     - `hard_rules` (list of strings)
     - `tasks` (ordered list of task seeds; each seed includes at least `id`, `title`, `intent`)
     - `out_of_scope` (list of strings)
     - `definition_of_done` (list of strings)
     - `follow_ups` (list of strings)
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
- *executor to fill*

**What was harder than expected:**
- *executor to fill*

**Decisions made during execution (deviations from this plan):**
- *executor to fill — each deviation must include: what changed, why, who approved*

**Forward plan:**
- *executor to fill*

**next_handover_id:** ALFRED_HANDOVER_15