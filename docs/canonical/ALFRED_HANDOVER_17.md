# Alfred's Handover Document #17 — Concern X, Slice 5: Three-role Typed Context Bundle

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_17
**date:** 2026-05-06
**author:** Planner (reasoning-only agent)
**previous_handover:** ALFRED_HANDOVER_16
**baseline_state:** Slice 4’s manifest-backed `canonical_handover` section contract exists today and is consumed by `scripts/generate_next_canonical_handover.py` for deterministic historical continuity extraction.

**Reference Documents:**
- `CONTEXT.md` — canonical definition of the three context roles (`scope`, `carry_forward`, `continuity`), rendering rules, and dedup precedence; also reaffirms deterministic-only validation (no LLM-judge).
- `docs/active/POST_GRILL_1.md` — the authoritative Slice 5 scope: introduces `ContextBundle`, target file paths, test plan, and acceptance criteria.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — resolved Concern X rationale for provenance-aware context assembly, role-specific rendering, and the “context duplication is a failure mode” post-Phase-3 incident.
- `docs/canonical/ALFRED_HANDOVER_16.md` — ratified completion of Slice 4 and explicit forward plan: Slice 5 only (typed bundle), no leakage into later slices.

This handover exists to execute **Concern X / Slice 5 only**: replace ad-hoc, stringly planner-context assembly in the canonical handover generator with a **typed** `ContextBundle` that models exactly three roles (`scope`, `carry_forward`, `continuity`), applies role-specific rendering rules, and enforces **dedup precedence** `scope` > `carry_forward` > `continuity`. This is a refactor with behavior-preservation constraints: it must preserve the Phase 3 duplicate-context suppression behavior and must reuse Slice 4’s deterministic `canonical_handover` summary extraction for summarized roles.

---

## WHAT EXISTS TODAY

### Git History

```
13651ad  handover: land refs hardening and slice 4 contracts
5c9ecb6  15 complete; generator set up for 16
b52a413  docs: sync HANDOVER_15 post-mortem with parser fix
b0fb820  refs: skip multi-backtick inline code spans in tag parser
db40747  refs: fill ALFRED_HANDOVER_15 post-mortem
692b6f3  refs: tasks 2-4 — migrate validators onto shared parser, add code-span skip, audit docs
cd8072f  refs: task 1 — add deterministic reference-tag parser
9538306  14 edited. 15 added cleanly
22e9a46  lint: fix Ruff import cleanup
71f9160  ledger: fill ALFRED_HANDOVER_14 post-mortem and CONTEXT.md clarifications
9ecbf65  ledger: task 2 — add YAML loader and seed PHASE_LEDGER.yaml
914268c  ledger: align Brief field with CONTEXT.md (followups_from_prior_phase) and add plan_path
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current generator + contract surfaces (Slice 4 baseline)

- The repository contains a FastAPI app at `src/alfred/api.py` (not in scope for this slice).
- The canonical handover workflow uses `scripts/generate_next_canonical_handover.py` (exists today) to assemble planner context and generate a draft canonical handover.
- Slice 4 introduced a manifest-backed `canonical_handover` doc-class contract in `docs/DOCS_MANIFEST.yaml` (exists today) and wired contract-driven splitting into the generator’s historical continuity extraction path (exists today).
- Current context assembly is still described (in Concern X) as an area that must stop being “just string concatenation” and become provenance-aware and role-specific.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Exactly three context roles**: `scope`, `carry_forward`, `continuity` (no fourth role without re-arguing via ADR). Rendering + dedup rules are methodology-level commitments (from `CONTEXT.md`).
2. **Rendering rules are role-specific** (not just dedup):
   - `scope` renders full text.
   - `carry_forward` renders full text for non-handover docs, but renders a deterministic summary for canonical handovers.
   - `continuity` always renders a deterministic summary (from `CONTEXT.md`).
3. **Dedup precedence is fixed**: `scope` > `carry_forward` > `continuity`; lower roles drop when paths collide (from `CONTEXT.md`).
4. **Deterministic-only validation chain**: no LLM-judge steps anywhere; semantic judgment remains at the human promotion gate (from `CONTEXT.md` and `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`).
5. **Doc-class section contract scope remains limited to `canonical_handover`** in this period; do not expand contracts for other doc classes in Slice 5 (from `CONTEXT.md` + Slice 4 ratification in `docs/canonical/ALFRED_HANDOVER_16.md`).

---

## HARD RULES

1. Implement **Slice 5 only**: typed `ContextBundle` + generator refactor + tests. Do not start later-slice items (renderer replacement, ledger-driven identity generation, pre-flight validators, post-generation validators, failed-candidate filename logic).
2. `ContextBundle` must have **exactly three roles** (`scope`, `carry_forward`, `continuity`). If an implementation approach makes it easy to add a fourth role, add a test or type-level closure that resists that drift.
3. Enforce dedup precedence **exactly**: `scope` > `carry_forward` > `continuity`.
4. Rendering rules must match `CONTEXT.md`:
   - `scope` full-text.
   - `carry_forward` full-text for non-handover docs; deterministic summary for canonical handovers.
   - `continuity` deterministic summary.
5. Keep validation deterministic (no LLM-as-judge logic added as part of this refactor).
6. Placement rules must be followed for any new artifacts:
   - per **schema placement rule**, schemas belong under `src/alfred/schemas/` (no new schemas expected in this slice).
   - per **test placement rule**, tests belong under `tests/` and use `test_*.py`.
   - per **module placement convention**, the new context package must be under `src/alfred/` (specifically `src/alfred/context/`).

---

## WHAT THIS PHASE PRODUCES

- A new context package implementing a typed three-role bundle:
  - `src/alfred/context/__init__.py` — to be created in this phase (per normal package layout under `src/alfred/`).
  - `src/alfred/context/bundle.py` — to be created in this phase; defines `ContextBundle`, a closed role set, dedup logic, and rendering helpers.
- A generator refactor:
  - `scripts/generate_next_canonical_handover.py` — to be edited in this phase; `load_historical_context()` and `build_planner_context()` stop assembling an opaque string blob and instead consume `ContextBundle`.
- Unit + integration tests:
  - `tests/test_context/test_bundle.py` — to be created in this phase (per test placement rule); proves dedup precedence and role-specific rendering, including the Phase 3 duplicate-context case.

Out of scope:
- Any renderer replacement beyond the generator’s context assembly.
- Any new doc-class contracts beyond `canonical_handover`.
- Any new validator stages (pre-flight/post-generation).
- Any ledger-driven identity generation changes.
- Any changes to FastAPI endpoints, agent roster, or unrelated tooling.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Create typed `ContextBundle` module | `src/alfred/context/bundle.py` + `src/alfred/context/__init__.py` | CHECKPOINT-1 |
| 2 | Refactor generator to use `ContextBundle` | Edited `scripts/generate_next_canonical_handover.py` using bundle for context assembly |  |
| 3 | Add tests for dedup + rendering + Phase 3 case | `tests/test_context/test_bundle.py` |  |

---

## TASK 1 — Create typed `ContextBundle` module

**Goal:** Introduce a typed, provenance-aware context bundle with exactly three roles and deterministic dedup + rendering rules.

### Implementation

1. **Create the new package location** — create `src/alfred/context/__init__.py` (per module placement convention under `src/alfred/`).
2. **Define the closed role set** in `src/alfred/context/bundle.py`:
   - Prefer a closed type (e.g., `Enum` or `Literal["scope", "carry_forward", "continuity"]`) such that introducing a new role is an explicit change.
3. **Model inputs as path-addressed items**:
   - A minimal, testable record type that includes at least: `path` (string), `role`, and enough metadata to decide rendering (e.g., whether the doc is a canonical handover).
   - Do not over-design: Slice 5 is about *bundle semantics* and *generator refactor*, not a new generalized document model.
4. **Implement dedup**:
   - Deterministically drop lower-precedence duplicates when the same `path` appears in multiple roles.
   - Ensure the implementation can report which items were dropped (useful for debugging and tests), but keep this as data, not logging side effects.
5. **Implement rendering helpers per role**:
   - `scope`: full text.
   - `carry_forward`: full text if non-handover; deterministic summary if canonical handover.
   - `continuity`: deterministic summary.
   - Reuse the existing deterministic summary/extractor path already used by Slice 4 for canonical handovers (do not reintroduce hardcoded heading knowledge).

### Verification

```bash
pytest -q
pyright
```

**Expected:**
- Tests can import `ContextBundle` from `src/alfred/context/bundle.py`.
- Static type checking passes (`pyright` is the repo type checker).
- No new role beyond the three defined roles is possible without editing the role definition (and ideally failing a test if attempted).

**Suggested commit message:** `context: task 1 — add typed ContextBundle with 3 roles and dedup/render rules`

### CHECKPOINT-1 — Bundle semantics locked (roles + dedup + render routing)

**Question:** Is the bundle’s role set closed to exactly three roles, and do dedup + render routing reflect `CONTEXT.md` without starting later-slice machinery?

**Evidence required:**
- A pasted snippet (verbatim) of the role definition from `src/alfred/context/bundle.py` showing exactly `scope`, `carry_forward`, `continuity`.
- A pasted snippet (verbatim) of the dedup precedence implementation showing ordering `scope` > `carry_forward` > `continuity`.
- A short note identifying which existing generator/extractor function is reused for canonical-handover summarization (name + call site), confirming it is deterministic and contract-driven.

| Observation | Likely call |
|---|---|
| Roles are exactly three, dedup precedence matches spec, and rendering routes canonical handovers through existing deterministic summarizer | PROCEED |
| Roles are correct but dedup or rendering deviates (e.g., continuity full-text, or carry_forward handovers full-text) | PIVOT |
| Implementation introduces a fourth role concept, adds LLM-judge validation, or expands doc-class contracts beyond `canonical_handover` | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Refactor generator to use `ContextBundle`

**Goal:** Replace ad-hoc context assembly in `scripts/generate_next_canonical_handover.py` with `ContextBundle` while preserving current behavior (including Phase 3 duplicate-context suppression).

### Implementation

1. **Identify current context assembly seams** in `scripts/generate_next_canonical_handover.py`:
   - `load_historical_context()`
   - `build_planner_context()`
   These should be refactored so they operate on a `ContextBundle` (or produce one + render it).
2. **Wire in the bundle**:
   - Collect candidate docs into role buckets (`scope`, `carry_forward`, `continuity`) as currently intended by the generator.
   - Build a `ContextBundle` and invoke its dedup step before rendering.
3. **Preserve the Phase 3 duplication fix as a general rule**:
   - If the previous canonical handover is already present as a scope doc (same path), it must not also appear under continuity after dedup.
4. **Keep output shape stable**:
   - Do not change unrelated prompt fields or the overall generator CLI surface.
   - Any new debug visibility should be additive and deterministic (e.g., reporting excluded duplicates), but must not require human interpretation to pass.

### Verification

```bash
pytest -q
python scripts/generate_next_canonical_handover.py --help
```

**Expected:**
- Generator still runs and prints help.
- Tests covering Phase 3 duplication behavior pass (added in Task 3).

**Suggested commit message:** `handover: task 2 — refactor generator context assembly onto ContextBundle`

---

## TASK 3 — Add tests for dedup + rendering + Phase 3 case

**Goal:** Prove, with deterministic tests, that the bundle enforces dedup precedence and role-specific rendering, including the known duplication failure mode.

### Implementation

1. **Create the test module** `tests/test_context/test_bundle.py` (per test placement rule).
2. **Unit tests: dedup precedence**
   - Same `path` appears in `scope` and `continuity` → continuity instance is dropped.
   - Same `path` appears in `carry_forward` and `continuity` (but not scope) → continuity instance is dropped.
3. **Unit tests: role rendering rules**
   - `carry_forward` canonical handover → rendering uses deterministic summary path (assert via a stubbed/fixture summarizer call boundary, or by asserting the output contains only the contracted sections rather than full file text).
   - `carry_forward` non-handover doc → rendering includes full text.
   - `continuity` always summarized.
4. **Integration test: Phase 3 style input**
   - Construct a bundle input where a canonical handover path is included as `scope` and also would have been included as `continuity`.
   - Assert rendered planner context includes it once (in scope full-text) and that continuity rendering excludes the duplicate.

### Verification

```bash
pytest -q tests/test_context/test_bundle.py
pyright
```

**Expected:**
- Tests demonstrate dedup precedence and rendering behaviors.
- The Phase 3 duplication scenario is explicitly encoded and guarded.

**Suggested commit message:** `tests: task 3 — add ContextBundle dedup and rendering coverage`

---

## WHAT NOT TO DO

1. Do not introduce a fourth context role or make roles configurable “because it might be useful.” Three roles is a methodology-level commitment.
2. Do not expand `docs/DOCS_MANIFEST.yaml` doc-class contracts beyond `canonical_handover` in this slice.
3. Do not add any LLM-judge validation step (even “optional”) to evaluate context quality or coverage.
4. Do not treat this slice as a rewrite of document loading across the whole repo; keep changes scoped to the canonical handover generator and the new context module.
5. Do not bypass Slice 4’s contract-driven extractor by reintroducing hardcoded heading strings for summaries.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- Slice discipline held: the implementation stayed inside `src/alfred/context/`, `scripts/generate_next_canonical_handover.py`, and tests. No Slice 6+ work leaked in (no renderer replacement, no ledger-driven identity generation, no new validator stages, no failed-candidate logic).
- The typed bundle landed as a narrow, reviewable seam under [src/alfred/context/bundle.py](src/alfred/context/bundle.py): exactly three roles (`scope`, `carry_forward`, `continuity`), fixed dedup precedence (`scope` > `carry_forward` > `continuity`), and role-specific render rules enforced in code rather than left implicit in generator string assembly.
- Slice 4’s contract-driven summary path was successfully reused instead of reintroducing heading knowledge. Canonical-handover summaries in the bundle route through `summarize_canonical_handover()` (`split_markdown_by_contract` + the manifest-backed `canonical_handover` contract), so Slice 5 stayed deterministic and built directly on Slice 4.
- The generator now genuinely routes planner-context assembly through `ContextBundle.render()` rather than using the bundle as a boolean dedup probe only. `build_planner_context()` constructs bundle items, renders them through the bundle, and still preserves the Phase 3 duplicate-continuity suppression behavior when the previous canonical handover is already present in scope.
- The second pass to add a real generator-level `carry_forward` path closed the main remaining Slice 5 gap. The generator now accepts concrete `carry_forward_items` and tests prove both supported render shapes: non-handover carry-forward renders full text; canonical-handover carry-forward renders a deterministic summary.
- Verification on the Slice 5 surfaces came back clean: `python -m pytest -q tests/test_context/test_bundle.py tests/test_scripts/test_generate_next_canonical_handover.py` passed (`34 passed`), `pyright src/alfred/context scripts/generate_next_canonical_handover.py tests/test_context/test_bundle.py` passed (`0 errors`), and `python scripts/generate_next_canonical_handover.py --help` still works with the expected Handover 17 defaults.

**What was harder than expected:**
- The current generator already has one “pre-rendered scope packet” seam (`AuthoringContextPacket.text`), so moving to a typed three-role bundle without starting Slice 6 required care. The cleanest Slice 5 move was to flow that packet through the bundle as a synthetic `scope` item rather than redesigning how authoritative docs are selected and rendered.
- Preserving continuity behavior while refactoring the assembly path was trickier than the bundle design itself. The old `load_historical_context()` code encoded the mode-aware continuity degradation (`full` / `summary` / `minimal` / `none`), and Slice 5 needed to preserve that exact behavior while still letting the bundle be the assembly mechanism.
- The first Slice 5 pass was only partially sufficient: it made the generator route through `ContextBundle.render()` but still exercised only `scope` + `continuity` in practice. A follow-up pass was needed to add a real generator-level `carry_forward` path so the slice was honest to its own handover wording.
- The bundle’s canonical-handover summary helper surfaces semantic section keys (`### context`, `### current_state`, etc.) rather than raw historical heading strings. That is correct and deterministic, but it means carry-forward summary tests need to assert semantic output rather than copy continuity-text expectations byte-for-byte.

**Decisions made during execution (deviations from this plan):**
- *Introduced `_render_historical_continuity()` as the shared continuity formatter.* What changed: continuity rendering logic was split out of `load_historical_context()` into a raw-markdown helper reused both by the legacy file-reading wrapper and by the bundle summarizer closure in `build_planner_context()`. Why: this let the generator preserve the existing mode-aware continuity behavior while making the bundle the real assembly seam. Approved by: executor judgment, scope-preserving.
- *Used a synthetic `scope` item path (`<scope-packet>`) for the pre-rendered authoritative packet.* What changed: `build_planner_context()` wraps the already-rendered authoritative packet in one `scope` item with a synthetic path, while also registering each authoritative source path as empty-text `scope` items for dedup semantics. Why: the generator already materializes authoritative scope as one packet string; replacing that upstream packet builder would have been Slice 6-style redesign, not Slice 5 refactor. Approved by: executor judgment.
- *Added `carry_forward_items` as a narrow optional parameter on `build_planner_context()` instead of inventing a broader loader framework.* What changed: the generator can now accept concrete `carry_forward` items, validate that they are correctly role-tagged, and pass them through the same bundle render path. Why: this closes the real Slice 5 gap at generator level while avoiding premature coupling to the phase ledger or a new document-loading subsystem. Approved by: executor judgment.
- *Kept continuity and canonical-handover carry-forward on different summarizer paths.* What changed: the bundle summarizer closure dispatches `continuity` items through `_render_historical_continuity()` (mode-aware generator summary) while canonical-handover `carry_forward` items use `summarize_canonical_handover()` (Slice 4 contract-driven summary). Why: `CONTEXT.md` requires both to be deterministic summaries, but only continuity is tied to the existing `--historical-context-mode` degradation path. Approved by: executor judgment.

**Forward plan:**
- HANDOVER_18 should pick up Slice 6 only: renderer replacement / identity-constant removal so the generator becomes a renderer over `PhaseLedger` + active `Brief`. Slice 5’s bundle now provides the context-assembly seam that Slice 6 can feed with real role sources.
- When Slice 6 wires the generator to the phase ledger, the most natural source of real `carry_forward` items will be ledger-derived scope-carry-forward paths rather than ad-hoc test inputs. The narrow `carry_forward_items` seam added here is intentionally enough to support that later wiring without further context-bundle redesign.
- The authoritative packet path remains synthetic in Slice 5 because upstream document selection still produces one rendered packet string. If a later slice wants per-document scope rendering inside the bundle, that should be argued explicitly as a new seam change rather than smuggled in as cleanup.
- Protocol closure remains separate from code completion: promote/register `ALFRED_HANDOVER_17.md` cleanly and update any required docs-governance metadata when this handover is accepted, rather than folding that operational step into the Slice 5 implementation itself.

**next_handover_id:** ALFRED_HANDOVER_18
