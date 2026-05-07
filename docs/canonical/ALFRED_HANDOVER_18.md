# Alfred's Handover Document #18 — Concern X, Slice 6: Ledger+Brief Renderer Replaces Hand-Edited Identity Constants

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_18
**date:** 2026-05-07
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_17
**baseline_state:** The handover generator still relies on hand-edited identity/sprint constants inside `scripts/generate_next_canonical_handover.py`, while Slice 5’s typed three-role `ContextBundle` seam exists today and is ready to be fed by ledger/brief-derived inputs.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_17.md` — Slice 5 ratified baseline; locks the three-role `ContextBundle` seam and calls for Slice 6 renderer/identity-constant removal next.
- `docs/active/POST_GRILL_1.md` — Authoritative Concern X slice plan; defines Slice 6 objective, affected files, test strategy, and acceptance criteria.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — Resolved Concern X decisions: phase ledger authority flow, brief fields, renderer-fixture testing, and provenance-aware context bundle rules.
- `CONTEXT.md` — Canonical glossary/constraints: definitions for Phase Ledger, Brief, Context Roles (three only), Doc Class/contract semantics, and the no-LLM-judge validator constraint.
- `docs/active/PHASE_LEDGER.yaml` — Seed ledger input; concrete renderer inputs and active-phase selection are constrained by this file’s shape/content.

This handover exists to execute **Concern X, Slice 6** only: replace the generator’s hand-edited identity constants (handover id, previous id, title, sprint-goal text, demo-plan grounding, argparse defaults, and module docstring text) with a **deterministic renderer** that derives them from the **PhaseLedger + active Brief**. This is the seam-closure: advancing phases becomes “edit the ledger → run the generator”, while keeping the external CLI and promotion workflow stable.

This phase must **preserve** Slice 5’s typed `ContextBundle` assembly seam and Slice 4’s deterministic `canonical_handover` summary path. It must **not** start Slice 7+ work (validator-chain expansion, failed-candidate filename logic, or new governance automation).

---

## WHAT EXISTS TODAY

### Git History

```
64e5c44  generator: retarget next handover to slice 6
016ce8e  docs: add ALFRED_HANDOVER_17 canonical handover
52b04db  handover: wire carry_forward role through ContextBundle assembly
1d2c9ae  handover: route planner-context assembly through ContextBundle.render
3145ab9  tests: task 3 — add ContextBundle dedup and rendering coverage
e500cc9  handover: task 2 — refactor generator context assembly onto ContextBundle
d6e4eda  context: task 1 — add typed ContextBundle with 3 roles and dedup/render rules
13651ad  handover: land refs hardening and slice 4 contracts
5c9ecb6  15 complete; generator set up for 16
b52a413  docs: sync HANDOVER_15 post-mortem with parser fix
b0fb820  refs: skip multi-backtick inline code spans in tag parser
db40747  refs: fill ALFRED_HANDOVER_15 post-mortem
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current generator + protocol seams (relevant to Slice 6)

- The canonical handover workflow is driven by `scripts/generate_next_canonical_handover.py` (exists today). It produces a draft canonical handover by assembling planner context, then running the planner stage.
- Slice 5 introduced a typed, three-role provenance-aware seam in `src/alfred/context` (exists today) that enforces:
  - exactly three roles: `scope`, `carry_forward`, `continuity`
  - dedup precedence: `scope` > `carry_forward` > `continuity`
  - role-specific rendering rules (full text vs deterministic summary)
- Slice 4 introduced doc-class contract-driven canonical-handover splitting via `docs/DOCS_MANIFEST.yaml` (exists today) and the deterministic summary path used by the generator for canonical handover summaries.
- **Partial state:** Phase-ledger-driven identity rendering is **declared as the Slice 6 goal** in the authoritative docs, but the actual renderer package (`src/alfred/render/…`) is **to be created in this phase**.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Exactly three context roles**: `scope`, `carry_forward`, `continuity` — no fourth role without a re-argued ADR (per `CONTEXT.md`).
2. **Rendering rules are role-specific and deterministic**: `scope` is full text; `carry_forward` is full text for non-handover docs and deterministic summary for canonical handovers; `continuity` is always deterministic summary.
3. **Dedup precedence is fixed**: `scope` > `carry_forward` > `continuity`.
4. **No LLM-judge in validation**: the validator chain is deterministic only; semantic judgment happens at the human approval gate (per `CONTEXT.md`).
5. **API topology constraint**: FastAPI remains a single module at `src/alfred/api.py` (not in scope for this slice).

---

## HARD RULES

1. **Slice 6 only:** Do not start Slice 7+ work (no new validator stages, no failed-candidate filename logic, no new governance automation beyond what Slice 6 requires).
2. **Renderer must be deterministic:** Inputs = `docs/active/PHASE_LEDGER.yaml` + the selected active phase’s `Brief` fields; output = identity/constants strings with no network calls and no LLM usage.
3. **Authority flow is one-way:** The phase ledger is a derived view; do not make the ledger override or “correct” protocol artifacts. The renderer consumes the ledger as the seed for the *next* unratified phase, consistent with `CONTEXT.md`.
4. **Preserve Slice 5 seam:** Keep the `ContextBundle` roles, dedup precedence, and role-specific rendering rules unchanged.
5. **Preserve Slice 4 summary path:** Canonical-handover summaries used for `carry_forward` and `continuity` remain contract-driven and deterministic.
6. **Do not change external generator interface:** Keep `scripts/generate_next_canonical_handover.py` CLI arguments, help UX, and output locations stable; internal wiring may change.
7. **Placement rules (non-negotiable):**
   - Per **schema placement rule**, schema modules live under `src/alfred/schemas/` (no `src/alfred/schemas.py`).
   - Per **test placement rule**, tests live under `tests/` as `test_*.py`.
   - Per **agent/tool placement rules**, do not introduce ad-hoc top-level helper modules; new code should land in an appropriate package.
   - **New renderer package** must live under `src/alfred/` (see Slice 6 file list); do not create a parallel top-level `render/` directory.

---

## WHAT THIS PHASE PRODUCES

- A new renderer package: `src/alfred/render/__init__.py` (to be created in this phase) and `src/alfred/render/handover_inputs.py` (to be created in this phase) that derives:
  - `EXPECTED_HANDOVER_ID`
  - `EXPECTED_PREVIOUS_HANDOVER`
  - `DISPLAY_TITLE`
  - `SPRINT_GOAL`
  - `DEMO_PLAN_GROUNDING`
  - argparse help defaults (where currently hard-coded)
  - module docstring identity text (where currently hard-coded)
  from `docs/active/PHASE_LEDGER.yaml` + the active phase’s `Brief`.
- A refactor of `scripts/generate_next_canonical_handover.py` (exists today; to be edited in this phase) to call the renderer and feed its outputs into the existing planner pipeline.
- Renderer-fixture tests: `tests/test_render/test_handover_inputs.py` (to be created in this phase).
- Updated integration tests: `tests/test_scripts/test_generate_next_canonical_handover.py` (exists today; to be edited in this phase) so assertions target renderer output over a fixture ledger/brief, not prose constants.

Out of scope:
- Adding/altering pre-flight or post-generation validators (Slice 7+).
- Failed-candidate filename logic or archive workflows (Slice 8+).
- Any changes to FastAPI endpoints or service wiring.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Create a deterministic handover-inputs renderer | `src/alfred/render/handover_inputs.py` + focused unit tests | CHECKPOINT-1 |
| 2 | Wire generator to renderer (remove hand-edited constants) | Updated `scripts/generate_next_canonical_handover.py` uses renderer outputs; CLI stable | CHECKPOINT-2 |
| 3 | Replace stale prose assertions with fixture-based renderer assertions | Updated `tests/test_scripts/test_generate_next_canonical_handover.py` | |

---

## TASK 1 — Create a deterministic handover-inputs renderer

**Goal:** Introduce a renderer surface that deterministically derives all generator identity/constants from the PhaseLedger + active Brief.

### Implementation

1. **Add the renderer package** — create `src/alfred/render/__init__.py` (to be created in this phase) and `src/alfred/render/handover_inputs.py` (to be created in this phase).
   - Placement note (PLACEMENT): per repo conventions, new package code belongs under `src/alfred/` and tests under `tests/`.

2. **Define a minimal renderer API** in `src/alfred/render/handover_inputs.py` (to be created in this phase).
   - Target shape: a small set of pure functions (or a small dataclass returned by a pure function) that accepts:
     - parsed PhaseLedger content
     - selected active phase entry (the “planning” phase)
   - Produces a single object containing the derived strings the generator currently hard-codes.

3. **Ledger/brief selection semantics** (deterministic):
   - Identify the “active” phase as the **next phase whose status is planning**, per the resolved workflow discussion.
   - Extract the active phase’s `handover_id`, `previous_handover`, `title`, and `brief` fields (as present in `docs/active/PHASE_LEDGER.yaml`).
   - Assemble:
     - `DISPLAY_TITLE` from the phase title (and/or ledger formatting rules) in the same house style as canonical handovers.
     - `SPRINT_GOAL` as a rendered paragraph derived from the brief fields. (Keep it deterministic; do not invoke an LLM.)
     - `DEMO_PLAN_GROUNDING` from the ledger’s plan path and relevant scope sources (as described in workflow docs).

4. **Keep the renderer narrowly scoped**:
   - Do not re-architect context assembly. The renderer only replaces identity/constants and related help/docstring text.
   - Consume existing parsing utilities where they already exist; otherwise add only the minimum deterministic YAML read/parse path needed.

5. **Add renderer-fixture tests** — create `tests/test_render/test_handover_inputs.py` (to be created in this phase).
   - Fixture a minimal ledger structure (in-test string or a small fixture file under tests if that is the repo norm) and assert:
     - active-phase selection is deterministic
     - derived IDs and title match exactly
     - sprint goal rendering is stable and uses the brief fields
     - demo plan grounding is stable

### Verification

```bash
python -m pytest -q tests/test_render/test_handover_inputs.py
pyright src/alfred/render tests/test_render/test_handover_inputs.py
```

**Expected:**
- Tests pass and assert stable string outputs (no prose-level “contains Phase X” brittle assertions).
- `pyright` reports `0 errors` for the new renderer module.

**Suggested commit message:** `render: task 1 — add deterministic handover inputs renderer`

### CHECKPOINT-1 — Renderer surface is correct and minimal

**Question:** Does the renderer produce all identity/constants deterministically from `docs/active/PHASE_LEDGER.yaml` + active Brief, without pulling in Slice 7+ scope?

**Evidence required:**
- Paste the public renderer API signature(s) from `src/alfred/render/handover_inputs.py`.
- Paste the unit test names and their asserted outputs (or a short excerpt showing the key expected strings).
- Paste `pyright` summary line for the new module(s).

| Observation | Likely call |
|---|---|
| Renderer covers all constants listed in Slice 6 objective; no generator constants remain that should be ledger-derived; tests are stable | PROCEED |
| Renderer exists but coverage is partial (e.g., only handover ids, not sprint goal / grounding / help defaults) | PIVOT |
| Renderer design requires broad refactors (new context system, new doc-class contracts, validator changes) or introduces non-determinism | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Wire generator to renderer (remove hand-edited constants)

**Goal:** Refactor `scripts/generate_next_canonical_handover.py` so it no longer relies on hand-edited identity constants; instead it loads the phase ledger, selects the active brief, calls the renderer, and feeds renderer-produced inputs into the existing planner pipeline.

### Implementation

1. **Identify the current constant surface** in `scripts/generate_next_canonical_handover.py` (exists today) that Slice 6 lists:
   - `EXPECTED_HANDOVER_ID`, `EXPECTED_PREVIOUS_HANDOVER`, `DISPLAY_TITLE`, `SPRINT_GOAL`, `DEMO_PLAN_GROUNDING`
   - argparse help defaults
   - module docstring identity text

2. **Add ledger loading** inside the script:
   - Read `docs/active/PHASE_LEDGER.yaml` (exists today) deterministically.
   - Select the active phase per Task 1 semantics.

3. **Call the renderer** and replace the constants with renderer outputs.
   - The script may keep constant *names* (for minimal diff) but must treat them as derived values rather than hand-edited literals.

4. **Preserve external CLI surface**:
   - `--help` output should remain equivalent in structure and options.
   - Default values should now be renderer-derived, but the flags and their meanings should not change.

5. **Preserve Slice 5 context assembly seam**:
   - Do not alter `ContextBundle` behavior.
   - Ensure any renderer-produced strings that feed into context/prose do not bypass role rendering rules.

### Verification

```bash
python -m pytest -q tests/test_scripts/test_generate_next_canonical_handover.py
python scripts/generate_next_canonical_handover.py --help
python scripts/generate_next_canonical_handover.py --dry-run
```

**Expected:**
- The generator runs and produces a draft using ledger/brief-derived identity.
- `--help` still works and defaults reflect ledger-derived values.
- No Slice 7+ behavior changes appear (no new validator stages, no new filename logic).

**Suggested commit message:** `generator: task 2 — derive identity constants via renderer`

### CHECKPOINT-2 — End-to-end generator uses renderer, CLI stable

**Question:** Is the generator now a thin orchestrator over ledger selection + renderer outputs + existing planner pipeline, with no hand-edited identity constants remaining?

**Evidence required:**
- Paste the diff hunk (or excerpt) showing removal/replacement of the hand-edited constants in `scripts/generate_next_canonical_handover.py`.
- Paste the first ~15 lines of `python scripts/generate_next_canonical_handover.py --help` showing defaults.
- Paste the path(s) of the produced draft from `--dry-run` and the top-of-file title line to show the derived ID/title.

| Observation | Likely call |
|---|---|
| Constants are fully derived; help defaults updated; dry-run output title/id match ledger | PROCEED |
| Generator still has one or two hand-edited identity literals (e.g., demo grounding block) due to missing renderer fields | PIVOT |
| CLI changed incompatibly, or generator now depends on non-deterministic steps / new workflows | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 3 — Replace stale prose assertions with fixture-based renderer assertions

**Goal:** Update integration tests so they assert renderer-driven outputs over a fixture ledger/brief rather than brittle prose-constant content.

### Implementation

1. **Edit `tests/test_scripts/test_generate_next_canonical_handover.py`** (exists today; to be edited in this phase).
2. **Delete/replace prose assertions** that check for phase-name substrings in sprint-goal text.
3. **Assert deterministically** that:
   - the script uses renderer outputs (e.g., expected derived id/title present in produced draft)
   - the active-phase selection is respected for defaults
4. Keep tests resilient to future phase advances by:
   - using fixture ledger content inside tests
   - avoiding assertions tied to the repo’s current real phase number/name

### Verification

```bash
python -m pytest -q tests/test_scripts/test_generate_next_canonical_handover.py
```

**Expected:**
- Tests pass without relying on hand-edited constants.
- Assertions target the renderer output shape.

**Suggested commit message:** `tests: task 3 — assert renderer outputs, not prose constants`

---

## WHAT NOT TO DO

1. Do not add Slice 7+ validator-chain work (no new pre-flight/post-generation checks; no LLM-judge steps; no extra governance automation).
2. Do not change the number or meaning of context roles; do not introduce a fourth role.
3. Do not “promote the ledger” into being a protocol artifact; it remains a derived/seed view per `CONTEXT.md`.
4. Do not create new top-level directories for rendering code (no `render/` at repo root); per placement conventions, renderer code belongs under `src/alfred/`.
5. Do not paper over missing derivations by re-introducing hand-edited constants under new names; either derive it from the brief/ledger or explicitly defer.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- The renderer seam stayed narrow. `src/alfred/render/handover_inputs.py` now owns the identity-bearing generator inputs (`handover_id`, `previous_handover`, display title, sprint goal, demo-plan grounding, module docstring text, and argparse defaults) as a deterministic function over the ledger + active brief.
- Wiring the generator through a single `HANDOVER_INPUTS` object kept the Task 2 diff understandable while preserving the existing planner / `ContextBundle` / validator pipeline shape.
- The real seed ledger is now usable for Slice 6 generation: it includes a planning row with a brief and explicit continuity identity, so the generator can cold-start from repo state rather than hand-edited script constants.
- Verification coverage improved materially across the seam:
  - renderer tests prove deterministic output shape and error cases
  - ledger tests prove the planning-row contract
  - generator tests now prove renderer-backed wiring, `--help` defaults, `--dry-run` behavior, and script-boundary dry-run rendering
- The final non-destructive verification path (`--dry-run`) turned out to be genuinely useful both for human review and for making the Task 3 script tests more honest.

**What was harder than expected:**
- The repo ledger is multi-track: the blank-project kickoff demo ratified phases and the Concern X seam-discipline work share one seed file. Deriving `previous_handover` mechanically from the highest prior ratified phase id produced the wrong continuity source (`ALFRED_HANDOVER_12` instead of `ALFRED_HANDOVER_17`).
- The first pass at Task 3 removed the worst brittle prose assertions, but it did not yet fully prove script-boundary behavior from fixture-derived identity. A second polish pass was needed so the tests exercised a real script helper rather than only the renderer in isolation.
- Some apparently "identity-free" prose in the generator still encoded phase-specific assumptions (`Handover 18`, fixed previous handover path, fixed close-out wording). Those remnants had to be removed or converted to derived values before CHECKPOINT-2 was honestly green.
- `DEMO_PLAN_GROUNDING` and similar narrative blocks are deterministic now, but keeping them deterministic while still useful to the planner required care; phrase-level assertions in tests were too brittle and had to be replaced with wiring-level assertions.

**Decisions made during execution (deviations from this plan):**
- Added explicit `previous_handover` support on planning rows in the `PhaseLedger` schema and seed ledger, and changed the renderer to consume that field instead of inferring continuity from phase-id ordering.
  Why: the shared multi-track ledger made inferred continuity incorrect for Concern X Slice 6.
  Who approved: human checkpoint review during CHECKPOINT-1 verification.
- Enforced `phase.title == brief.title` for the active planning row consumed by the renderer, while continuing to render `DISPLAY_TITLE` from the brief/title value.
  Why: the docs contract allowed two title-bearing fields; enforcing equality prevented silent drift and kept one deterministic display-title source of truth.
  Who approved: human checkpoint review during CHECKPOINT-1 verification.
- Added `--dry-run` plus a pure `render_dry_run_report()` helper in the generator.
  Why: CHECKPOINT-2 explicitly required non-destructive verification, and Task 3 polish needed a script-boundary function that could be driven from fixture-derived `HandoverInputs`.
  Who approved: human checkpoint review during CHECKPOINT-2 follow-up.
- Kept the authoritative Slice 6 source-selection / packet-framing prose phase-specific instead of attempting to generalize the whole generator in this slice.
  Why: broad generator generalization would have expanded scope beyond Slice 6; the checkpoint goal was ledger/brief-driven identity replacement, not full workflow parameterization.
  Who approved: accepted as within-scope during human checkpoint review of CHECKPOINT-2 and Task 3 polish.

**Forward plan:**
- Slice 6 is complete enough to hand off. The next canonical handover should start Slice 7: pre-flight validators, with special attention to the now-explicit `previous_handover` field and the real seed ledger's planning-row contract.
- Preserve the current explicit continuity rule in future validator work: the generator should continue to reject missing / malformed planning-row continuity rather than silently guessing from phase ordering.
- Treat the new dry-run helper and script-boundary fixture tests as the minimum testing pattern for future generator changes: prove renderer/validator wiring at the script edge, not only in lower-level unit tests.
- Acknowledge one non-blocking limitation for future cleanup: the generator is now renderer-backed for identity, but it still carries Slice-6-specific authoritative-scope packet wording and document selection. Future workflow-generalization work should address that explicitly rather than letting it drift implicitly.
- Before opening Slice 7, ensure this handover is promoted cleanly and that the repo state used by the generator matches the ratified artifact.

**next_handover_id:** ALFRED_HANDOVER_19
