# Alfred's Handover Document #16 — Concern X, Slice 4: Canonical-handover Section Contract

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0  
**id:** ALFRED_HANDOVER_16  
**date:** 2026-05-06  
**author:** Planner (draft; human to approve)  
**previous_handover:** ALFRED_HANDOVER_15  
**baseline_state:** `canonical_handover` structure is still implicitly hardcoded in generator/extractor code (not declared in `docs/DOCS_MANIFEST.yaml`), and there is no doc-class contract loader/validator yet.

**Reference Documents:**
- `CONTEXT.md` — Defines `Doc Class`, including “section contract” semantics, and reiterates the deterministic/no-LLM validation constraint that this phase must obey.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — Records the resolved decision: only `canonical_handover` gets a declared contract (others remain uncontracted), tags remain inline in prose, and the validation chain must remain deterministic.
- `docs/active/POST_GRILL_1.md` — Slice 4 objective, required file targets, required tests (including byte-identical regression on handover #12), and acceptance criteria.
- `docs/canonical/ALFRED_HANDOVER_15.md` — Ratified close-out of Slice 3 and explicit forward plan to execute Slice 4 next; also locks in “do not start Slice 5+ work.”

This handover exists to move an implicit, code-embedded contract (“what headings a canonical handover must have, and how the extractor treats them”) into an explicit, reviewable, deterministic artifact in `docs/DOCS_MANIFEST.yaml`, and to refactor the generator/extractor to consume that artifact. This is the first step in making selective loading and deterministic extraction stable and inspectable without inventing broader doc-class machinery.

---

## WHAT EXISTS TODAY

### Git History

```
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
f362de3  ledger: task 1 — add PhaseLedger Pydantic models + validation
```

### Current-state recap (repo facts; do not contradict)

- FastAPI app **exists today** at `src/alfred/api.py` (single-module rule applies).
- Agent modules under `src/alfred/agents` **exist today**: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`.
- Tool modules under `src/alfred/tools` **exist today**: `board_write_contract`, `docs_policy`, `git_log`, `github_api`, `handover_authoring_context`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`, `story_markdown`.
- Docs governance **exists today**: `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, and `docs/archive`.
- Type checker is **pyright** (**CURRENT_TOOLING**).
- `pyproject.toml` **exists today** with `[project]=True` and `[project.scripts]=True`, with CLI entry `alfred.cli:main` (**PYPROJECT_STATE**).

### Partial state

- `docs/DOCS_MANIFEST.yaml` **exists today** but does not yet serve as the explicit `canonical_handover` section contract source consumed by the generator/extractor (this Slice 4 plan will make it do so).
- A doc-class contract loader/validator under src/alfred/docs is **to be created in this phase** (per Slice 4 targets in `docs/active/POST_GRILL_1.md`).

### Key Design Decisions Inherited (Do Not Revisit)

1. **Deterministic validation only; no LLM-judge steps anywhere in the validation chain.** Any “does this make sense?” judgment stays with the human approval gate. (From `CONTEXT.md` + `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)
2. **Doc-class section contract scope is limited to `canonical_handover` in this slice.** Other planning-doc classes remain uncontracted until a deterministic consumer requires them. (From `CONTEXT.md` + `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)
3. **Reference tags remain inline in prose** (`[future-doc: ...]`, `[future-path: ...]`), and their semantics do not move into `docs/DOCS_MANIFEST.yaml`. (From `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` + `docs/canonical/ALFRED_HANDOVER_15.md`.)
4. **Slice discipline:** do Slice 4 only. Do not start Slice 5+ items (typed context bundles, renderer replacement, new validator stages, failed-candidate filename short-circuiting). (From `docs/active/POST_GRILL_1.md` + `docs/canonical/ALFRED_HANDOVER_15.md`.)

---

## HARD RULES

1. **No LLM-judge validators.** All new validation added in this phase must be deterministic code with precise, location-rich errors.
2. **Only `canonical_handover` gets a declared contract in this slice.** Do not add contracts for charter/plan/scenario/outline.
3. **Do not move reference-tag semantics into the manifest.** Tags stay inline in markdown prose; the manifest is for doc-class contracts, not tag attachment rules.
4. **Respect repo placement/structure rules:**
   - Per **schema placement rule**, schema modules belong under `src/alfred/schemas/` (not used by this slice unless truly required).
   - Per **tool placement rule**, tool modules belong under `src/alfred/tools/` (not used by this slice).
   - Per **test placement rule**, tests belong under `tests/` as `test_*.py`.
   - New doc-contract code must land under `src/alfred/docs/` (**to be created in this phase**) as specified by `docs/active/POST_GRILL_1.md`.
5. **No API topology changes.** FastAPI remains a single module at `src/alfred/api.py`.

---

## WHAT THIS PHASE PRODUCES

- An explicit `canonical_handover` doc-class section contract declared in `docs/DOCS_MANIFEST.yaml` (required level-2 headings + per-heading semantic role + rendering treatment).
- A deterministic contract loader under `src/alfred/docs/contracts.py` and package marker `src/alfred/docs/__init__.py` (**to be created in this phase**).
- A deterministic contract validator under `src/alfred/docs/contract_validator.py` (**to be created in this phase**) that can validate a markdown doc against its declared doc class and emit precise, actionable errors.
- Generator/extractor refactor in `scripts/generate_next_canonical_handover.py` to read the heading list from the manifest-declared contract rather than hardcoding `_split_level2_sections` assumptions.
- Tests:
  - `tests/test_docs/test_contracts.py` (**to be created in this phase**) for loader behavior.
  - `tests/test_docs/test_contract_validator.py` (**to be created in this phase**) for contract enforcement (missing/renamed headings).
  - A regression test proving extraction output for `docs/canonical/ALFRED_HANDOVER_12.md` is byte-identical before vs after the refactor.

Out of scope:
- Any Slice 5+ work: typed context bundles, renderer replacement, new pre-flight/post-generation validator stages, failed-candidate filename short-circuiting, or any non-`canonical_handover` doc-class contracts.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Declare `canonical_handover` contract in docs manifest | Edit `docs/DOCS_MANIFEST.yaml` with `doc_classes:` → `canonical_handover` contract | CHECKPOINT-1 |
| 2 | Implement contract loader | `src/alfred/docs/__init__.py` + `src/alfred/docs/contracts.py` |  |
| 3 | Implement contract validator | `src/alfred/docs/contract_validator.py` |  |
| 4 | Refactor generator/extractor to consume contract | Edit `scripts/generate_next_canonical_handover.py` to load headings from contract | CHECKPOINT-2 |
| 5 | Add tests + regression coverage | `tests/test_docs/test_contracts.py`, `tests/test_docs/test_contract_validator.py`, regression test for handover #12 | CHECKPOINT-3 |

---

## TASK 1 — Declare the `canonical_handover` section contract in `docs/DOCS_MANIFEST.yaml`

**Goal:** Add an explicit doc-class contract for `canonical_handover` so the required level-2 headings and their deterministic treatment are reviewable and machine-consumable.

### Implementation

1. **Add `doc_classes:` root (if not already present) and declare `canonical_handover`.**
   - Include a required heading list (level-2 / `##` headings), in the canonical order enforced by the contract.
2. **For each required heading, declare:**
   - A semantic class (e.g., `current_state`, `protocol_invariant`, `deliverables`, `tasks`, `non_goals`, `retrospective`).
   - A rendering treatment (`verbatim` vs `extractable` / “bullets allowed”).
3. **Keep scope narrow:** only `canonical_handover` in this slice.

> Note: The exact schema keys used inside `docs/DOCS_MANIFEST.yaml` must be chosen to match existing manifest conventions. If no conventions exist yet for doc-class metadata, define them minimally and document them in comments in the YAML (deterministic and human-readable).

### Verification

```bash
python -m pytest -q
python scripts/validate_alfred_planning_facts.py
```

**Expected:**
- Tests still pass (or at minimum, failures are limited to the new, expected tests added later in this phase).
- Planning-facts validation still passes (manifest remains valid YAML and docs governance remains intact).

**Suggested commit message:** `docs: slice 4 — declare canonical_handover contract in DOCS_MANIFEST`

### CHECKPOINT-1 — Contract shape + heading list sanity

**Question:** Is the `canonical_handover` contract in the manifest both (a) minimal and (b) sufficient to represent the real canonical handover section contract without inventing broader doc-class machinery?

**Evidence required:**
- Paste the new `doc_classes:` YAML block verbatim.
- Paste a list of the exact `##` headings from one canonical handover (suggest: `docs/canonical/ALFRED_HANDOVER_15.md`) to show the contract matches reality.

| Observation | Likely call |
|---|---|
| Contract declares only `canonical_handover`, and its headings match an existing canonical handover exactly | PROCEED |
| Contract headings require renaming/reordering of existing canonical handovers to pass | PIVOT (adjust contract to reality; do not rewrite history) |
| Contract attempts to add non-handover doc classes or embeds reference-tag semantics | STOP (scope violation) |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Implement doc-contract loader (`src/alfred/docs/contracts.py`)

**Goal:** Provide deterministic code that loads the `canonical_handover` contract from `docs/DOCS_MANIFEST.yaml` and exposes a typed API for downstream consumers.

### Implementation

1. **Create package marker** `src/alfred/docs/__init__.py` (**to be created in this phase**).
2. **Create loader module** `src/alfred/docs/contracts.py` (**to be created in this phase**):
   - Define a small typed model (dataclass or Pydantic, consistent with repo norms) for:
     - doc class name
     - required level-2 headings (ordered)
     - per-heading semantic class
     - per-heading rendering treatment
   - Implement `load_doc_contracts()` that reads `docs/DOCS_MANIFEST.yaml` and returns a mapping.
   - Implement `get_doc_class_contract(doc_class: str)` convenience accessor that raises a precise error if missing.
3. Ensure errors are location-rich where feasible (at least: include doc class name and missing key paths).

### Verification

```bash
python -m pytest -q tests/test_docs/test_contracts.py
pyright
```

**Expected:**
- Loader tests pass.
- Pyright reports no new type errors.

**Suggested commit message:** `docs: slice 4 — add contract loader`

---

## TASK 3 — Implement contract validator (`src/alfred/docs/contract_validator.py`)

**Goal:** Deterministically validate that a markdown document conforms to its declared `canonical_handover` section contract (presence + exact match for required `##` headings).

### Implementation

1. **Create validator module** `src/alfred/docs/contract_validator.py` (**to be created in this phase**):
   - Parse markdown for level-2 headings (`## `) deterministically.
   - Compare observed heading list to contract required heading list.
   - Emit actionable failures:
     - missing heading(s)
     - renamed heading(s) (treat as missing + unexpected)
     - unexpected extra headings (decide if fatal or warning; Slice 4 acceptance criteria emphasize missing/renamed as failures)
   - Provide an API like `validate_doc_against_contract(markdown: str, contract: DocContract) -> list[Finding]`.
2. Add tests that:
   - a “good” canonical handover passes
   - missing `## HARD RULES` fails with a precise message
   - renamed heading (e.g. `## HARD-RULES`) fails

### Verification

```bash
python -m pytest -q tests/test_docs/test_contract_validator.py
pyright
```

**Expected:**
- Tests cover at least: good doc, missing required heading, renamed heading.

**Suggested commit message:** `docs: slice 4 — add contract validator`

---

## TASK 4 — Refactor generator/extractor to consume contract (`scripts/generate_next_canonical_handover.py`)

**Goal:** Replace hardcoded `_split_level2_sections` (and friends) heading knowledge with contract-driven heading lists sourced from the manifest.

### Implementation

1. **Locate the implicit contract** currently embedded in `scripts/generate_next_canonical_handover.py` (the `_split_level2_sections` path).
2. **Load the contract** via `src/alfred/docs/contracts.py` and use the required heading list as the single source of truth.
3. **Keep behavior stable:** this is a refactor; output must remain byte-identical for the regression target.
4. **Do not broaden scope:** no new doc classes, no changes to reference-tag behavior, no new validator phases.

### Verification

```bash
python -m pytest -q
python scripts/generate_next_canonical_handover.py --help
```

**Expected:**
- All tests pass.
- Script still runs and produces output as before (behavioral parity to be proven by regression test in Task 5).

**Suggested commit message:** `generator: slice 4 — consume canonical_handover contract for section splitting`

### CHECKPOINT-2 — Refactor risk gate (behavioral parity before adding broad tests)

**Question:** Does the generator/extractor produce the same section-splitting behavior when driven by the manifest contract, before we lock it in with byte-identical regression?

**Evidence required:**
- A short diff or description showing what code changed (hardcoded headings → contract call).
- A snippet showing the contract-driven heading list used at runtime (e.g., printed list in a debug run, or a unit test asserting the list is loaded).

| Observation | Likely call |
|---|---|
| Contract-driven list is used, and local spot-check shows identical section boundaries | PROCEED |
| Section splitting changes because contract differs subtly from code assumptions | PIVOT (adjust contract to match historical reality; preserve existing behavior) |
| Refactor introduces new “interpretation” logic or starts pulling in other doc classes | STOP (scope violation) |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 5 — Add tests + byte-identical regression (handover #12)

**Goal:** Prove Slice 4 did not change extractor output semantics and that the new validator enforces the declared contract across the existing canonical corpus.

### Implementation

1. **Loader tests** in `tests/test_docs/test_contracts.py` (**to be created in this phase**):
   - can load `canonical_handover`
   - required headings list is non-empty and contains required scaffold headings
2. **Validator tests** in `tests/test_docs/test_contract_validator.py` (**to be created in this phase**):
   - missing `## HARD RULES` fails with precise message
   - renamed heading fails
3. **Corpus conformance test:** validate that all `docs/canonical/ALFRED_HANDOVER_1.md` through at least `docs/canonical/ALFRED_HANDOVER_12.md` (and ideally through `15`) conform to the contract.
4. **Byte-identical regression:**
   - Choose `docs/canonical/ALFRED_HANDOVER_12.md` as the fixed input.
   - Capture the “historical extraction” output before refactor and after refactor and assert byte-identical.
   - Implementation approach must be deterministic and self-contained in tests (no golden files unless already a repo convention).

### Verification

```bash
python -m pytest -q
pyright
python scripts/validate_alfred_planning_facts.py
```

**Expected:**
- Contract loader/validator tests pass.
- All existing canonical handovers pass the contract validator.
- Regression test proves byte-identical output for handover #12.

**Suggested commit message:** `tests: slice 4 — contract tests + handover 12 extraction regression`

### CHECKPOINT-3 — Acceptance criteria gate

**Question:** Do we meet the Slice 4 acceptance criteria from `docs/active/POST_GRILL_1.md` without pulling in Slice 5+ scope?

**Evidence required:**
- Paste pytest summary showing all tests passing.
- Paste the specific test output (or assertion description) demonstrating byte-identical extraction for handover #12.
- Paste a short snippet showing the manifest contract exists and is consumed.

| Observation | Likely call |
|---|---|
| All tests pass; contract declared; validator enforces; handovers pass; byte-identical regression passes | PROCEED (ready for human approval/promotion) |
| Contract validator fails on older canonical handovers due to historical inconsistencies | PIVOT (adjust contract to match reality; do not rewrite historical handovers unless explicitly approved) |
| Work drifted into typed context bundles, renderer replacement, or new validator stages | STOP (scope violation) |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do **not** add doc-class contracts for non-handover planning docs (charter/plan/scenario/outline). Slice 4 is `canonical_handover` only.
2. Do **not** add any LLM-judge or semantic validators. Validation must remain deterministic.
3. Do **not** move `[future-doc: ...]` / `[future-path: ...]` semantics into `docs/DOCS_MANIFEST.yaml` or any side channel.
4. Do **not** start Slice 5+ items (typed context bundle refactor, renderer replacement, new pre-flight/postgen stages, failed-candidate filename logic).

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- Slice discipline held: the change set stayed inside `docs/DOCS_MANIFEST.yaml`, the new `src/alfred/docs/` package, the canonical handover generator, and tests. No typed-context bundle, renderer, preflight/postgen validator, or failed-candidate lifecycle work leaked in.
- The manifest-backed contract is now real and consumed by code: `canonical_handover` is declared once in `docs/DOCS_MANIFEST.yaml`, `load_doc_contracts()` / `get_doc_class_contract()` load it deterministically, and `load_historical_context()` in `scripts/generate_next_canonical_handover.py` now splits historical handovers through that contract instead of hardcoded heading strings.
- The backward-compatibility strategy worked: heading aliases for historical corpus variations (`WHAT THIS HANDOVER PRODUCES`, `WHAT PHASE 2 PRODUCES`, `POST-MORTEM (Phase 2)`) let all canonical handovers 1–15 validate without rewriting history.
- Regression coverage proved the refactor stayed behaviorally stable where it mattered: `tests/test_scripts/test_generate_next_canonical_handover.py` reconstructs the legacy summary-extraction path and asserts the Handover 12 summary is byte-identical before vs after the contract-driven refactor.
- Verification came back clean on the Slice 4 surfaces: 26 targeted tests passed, full pytest passed (`578 passed, 2 skipped`), targeted pyright for the new docs-contract code passed (`0 errors`), `python scripts/generate_next_canonical_handover.py --help` still works, and `python scripts/validate_alfred_planning_facts.py docs/canonical/ALFRED_HANDOVER_15.md --mode both --expected-id ALFRED_HANDOVER_15 --expected-previous ALFRED_HANDOVER_14 --expected-date 2026-05-05` returned `OK`.

**What was harder than expected:**
- The historical corpus is not literally uniform at the level-2 heading string level. The obvious version of the contract — “one exact heading name per section” — would have failed on real promoted history (`ALFRED_HANDOVER_1` uses `WHAT PHASE 2 PRODUCES`; `ALFRED_HANDOVER_2` uses `POST-MORTEM (Phase 2)`). The contract had to model semantic sections with accepted literal aliases rather than pretend the old corpus was cleaner than it is.
- The phrase “all existing canonical handovers pass the contract validator” is only achievable if the validator distinguishes extractor-consumed contract sections from historical extra headings. Older canonical handovers contain many legitimate non-contracted `##` sections (`WHAT THIS PROJECT IS`, `DESIGN DECISIONS ALREADY MADE`, `OPEN QUESTIONS REQUIRING HUMAN JUDGMENT`, etc.), so treating every undeclared heading as an error would have turned Slice 4 into a retroactive doc rewrite.
- Proving byte-identical regression needed a test-local reconstruction of the legacy summary-extraction flow because the old implementation is gone once the refactor lands. The test now encodes the pre-refactor behavior explicitly, which is better than a golden file but took a careful copy of the old logic.
- `scripts/check_manifest.py` still reports unrelated docs-governance drift in the live repo (deleted archived failed-candidate files still declared; three ADR markdown files present on disk but not registered). That drift predates Slice 4 and was intentionally not “fixed while here,” but it means the narrow docs-governance check is noisier than the Slice 4 code/tests signal.

**Decisions made during execution (deviations from this plan):**
- *Backward-compatible heading aliases in the contract.* What changed: the `deliverables` and `retrospective` sections in `doc_classes.canonical_handover` accept historical aliases (`WHAT THIS HANDOVER PRODUCES`, `WHAT PHASE 2 PRODUCES`, `POST-MORTEM (Phase 2)`) rather than enforcing a single literal heading for every promoted handover. Why: real promoted canonical handovers already vary, and CHECKPOINT-1 explicitly called for adjusting the contract to reality rather than rewriting history. Approved by: human (Donal), in-band, by approving PROCEED after the checkpoint evidence showed the corpus variation.
- *Validator scope kept to contracted sections only.* What changed: `validate_doc_against_contract()` treats missing required contracted sections and ordering problems as errors, but tolerates other level-2 headings when `allow_unexpected_headings: true` is set in the manifest. Why: Slice 4 is about making the extractor’s implicit section contract explicit, not about declaring every legacy canonical heading variant as a formal doc-class taxonomy. Approved by: executor judgment, consistent with the manifest flag introduced at CHECKPOINT-1.
- *Used frozen dataclasses for contract models instead of Pydantic.* What changed: `DocContract` / `DocSectionContract` landed as small immutable dataclasses in `src/alfred/docs/contracts.py`. Why: the loader only needs deterministic manifest parsing plus precise path-rich errors; adding a new Pydantic layer here would have been heavier than the repo’s existing lightweight manifest helpers in `alfred.tools.docs_policy`. Approved by: executor judgment.
- *Refactor stayed in the generator summary path only.* What changed: the contract-driven splitter was wired into `scripts/generate_next_canonical_handover.py`, while `src/alfred/schemas/handover.py` was deliberately left untouched. Why: the handover scoped Slice 4 to the historical-context extractor path; broadening into schema parsing would have been extra consumer work not required to satisfy the acceptance criteria. Approved by: executor judgment.

**Forward plan:**
- HANDOVER_17 should pick up Slice 5 only: typed context bundles (`scope`, `carry_forward`, `continuity`) and the role-specific rendering/dedup rules described in `CONTEXT.md` / `POST_GRILL_1.md`. Slice 4’s contract loader and contract-driven splitter are now the foundation that Slice 5 can build on.
- The next consumer worth revisiting after Slice 5 is `src/alfred/schemas/handover.py`, which still has its own permissive level-2 splitter. It was correctly left alone in Slice 4, but the repo now has a single manifest-backed contract source if a later slice wants schema parsing to align with the same section semantics.
- The pre-existing manifest drift surfaced during CHECKPOINT-1 remains outstanding and should be handled as separate docs-governance cleanup, not folded into Concern X scope by accident.
- Keep the Handover 12 byte-identical regression test when moving into Slice 5+. It is the best guardrail against accidentally changing the meaning of historical continuity extraction while refactoring the broader context-assembly path.

**next_handover_id:** ALFRED_HANDOVER_17
