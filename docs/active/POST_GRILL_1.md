# Concern X Implementation Plan

## Overview

Nine slices. Each is independently shippable and lands one user-meaningful capability. Order is dependency-driven: the foundations come first, the core renderer replacement is the load-bearing middle, validators land last.

## Slice 1 — Repo cleanup

**Objective:** Delete obsolete scripts and stale tests resolved during grilling. Clears false-signal noise so the renderer work doesn't look like a wider migration than it is.

**Files affected:**

- Delete: `scripts/dogfood_run.py`, `scripts/generate_phase7_canonical.py`, `tests/test_scripts/test_generate_phase7_canonical.py`
- Edit: `tests/test_scripts/test_generate_next_canonical_handover.py` — delete the 3 stale prose-assertion tests
- Edit: `scripts/generate_next_canonical_handover.py` only if it imports anything from the deleted scripts (likely not)

**Test strategy:** Run full suite; expect zero unintended breakages (these scripts have no live callers). Confirm via grep that nothing in `scripts/`, `src/`, `tests/`, `pyproject.toml`, or CI references the deleted files.

**Risk:** Low. Pre-deletion grep already confirmed the only references are an archived handover (#4) and the test file itself.

**Dependencies:** None.

**Acceptance criteria:**

- Both scripts and the test file are gone.
- `test_generate_next_canonical_handover.py` no longer has the 3 pre-existing failures.
- Full test suite passes (or, at minimum: pre-existing failure count drops to zero in that test module).

## Slice 2 — Phase ledger schema and seed file

**Objective:** Introduce the phase ledger as a typed YAML artifact with Pydantic-validated schema. Seed with phases 0–5 (mechanical fields, derived from canonical handovers). No behavior change to the generator yet — the ledger sits alongside, unused, until slice 6.

**Files affected:**

- New: `src/alfred/ledger/__init__.py`, `src/alfred/ledger/models.py` (Pydantic: `Phase`, `PhaseLedger`, `Brief`)
- New: `src/alfred/ledger/loader.py` (`load_ledger(path) -> PhaseLedger`)
- New: `docs/active/PHASE_LEDGER.yaml`
- New: `tests/test_ledger/test_models.py`, `tests/test_ledger/test_loader.py`

**Test strategy:** Pydantic validation tests (good ledger loads; missing field rejects; ratified-without-handover-id rejects; brief on a ratified row rejects; etc.). Integration test: load the seed file successfully. No tests against the generator yet.

**Risk:** Low. Additive only.

**Dependencies:** None (Slice 1 not strictly required, but recommended to land first to keep the test suite clean).

**Acceptance criteria:**

- `PHASE_LEDGER.yaml` exists with phases 0–5 entries that round-trip through the schema.
- Brief schema accepts the field set from `CONTEXT.md`'s Brief definition.
- Loader rejects malformed input with precise errors.
- The generator script is unchanged.

## Slice 3 — Reference tag canonicalization

**Objective:** Lock `[future-doc:]` / `[future-path:]` syntax in a deterministic parser. Audit existing handovers and normalize variants. Independent slice; no ledger dependency.

**Files affected:**

- New: `src/alfred/refs/__init__.py`, `src/alfred/refs/tags.py` (parser, regex, dataclass `ReferenceTag`)
- Edit: `scripts/validate_alfred_handover.py` to consume the new parser instead of inline regex
- New: `tests/test_refs/test_tags.py`
- Possibly edit: a handful of canonical handovers if the audit finds variants

**Test strategy:** Parser tests across canonical and pathological inputs (whitespace variants, missing colon, nested brackets). Audit script reports any non-canonical occurrences in `docs/`. Validator integration test confirms end-to-end recognition.

**Risk:** Low. The parser is well-bounded; the validator already does this informally and we're replacing inline regex with a tested module.

**Dependencies:** None.

**Acceptance criteria:**

- Canonical syntax documented in `CONTEXT.md` (already done) and locked in code as the only accepted form.
- All current handovers parse cleanly under the new parser.
- Validator emits a clean error citing line/column for any malformed tag.

## Slice 4 — Canonical-handover section contract

**Objective:** Make the implicit section contract for `canonical_handover` (currently in code at `_split_level2_sections`) explicit in `docs/DOCS_MANIFEST.yaml`. New validator enforces the contract. The summary extractor reads required headings from the manifest.

**Files affected:**

- Edit: `docs/DOCS_MANIFEST.yaml` (add `doc_classes:` section with `canonical_handover` declaration)
- New: `src/alfred/docs/__init__.py`, `src/alfred/docs/contracts.py` (loader for doc-class contracts)
- New: `src/alfred/docs/contract_validator.py` (validates a doc against its declared class)
- Edit: `scripts/generate_next_canonical_handover.py` — `_split_level2_sections` and friends read heading list from the contract instead of hardcoding
- New: `tests/test_docs/test_contracts.py`, `tests/test_docs/test_contract_validator.py`

**Test strategy:** Contract loader tests. Validator tests: a good handover passes; a handover missing `HARD RULES` fails with a precise message; a handover with a renamed heading fails. Refactor test: `_split_level2_sections` extraction is byte-identical for handover #12 before and after.

**Risk:** Medium. Touches the path that currently works. Mitigated by the byte-identical regression test.

**Dependencies:** Slice 2 not required, but the loader pattern from Slice 2 informs this one.

**Acceptance criteria:**

- `canonical_handover` class declared in manifest with required-heading list and semantic-class-per-heading.
- All existing canonical handovers (1–12) pass the contract validator.
- The summary extractor produces identical output before/after refactor on handover #12.

## Slice 5 — Three-role typed context bundle

**Objective:** Refactor `load_historical_context` and `build_planner_context` to consume a typed `ContextBundle` with three roles (`scope`, `carry_forward`, `continuity`). Implement role-specific rendering and dedup precedence per `CONTEXT.md`.

**Files affected:**

- New: `src/alfred/context/__init__.py`, `src/alfred/context/bundle.py` (`ContextBundle`, role enum, dedup logic, rendering rules)
- Edit: `scripts/generate_next_canonical_handover.py` — replace ad-hoc context assembly with the bundle
- New: `tests/test_context/test_bundle.py`

**Test strategy:** Unit tests for dedup precedence (path in scope + continuity -> continuity drops). Rendering rule tests (handover in carry_forward -> summarized; charter in carry_forward -> full text). Integration test: bundle for phase-3-style input matches expected output.

**Risk:** Medium-high. The current path has shipped fixes encoded in it (Phase 3 dedup); the refactor must preserve those.

**Dependencies:** Slice 4 (rendering relies on the section contract for the summary extractor).

**Acceptance criteria:**

- `ContextBundle` has exactly three roles; adding a fourth requires an ADR (test enforces this if practical, e.g. the role enum is a closed `Literal`).
- Phase 3 dedup case produces the same effective context as today.
- Carry-forward of a canonical handover renders summarized, not full-text.

## Slice 6 — Renderer replaces hand-edited identity constants

**Objective:** The core seam-closure. The generator becomes a renderer over (`PhaseLedger`, active `Brief`). Identity constants (`EXPECTED_HANDOVER_ID`, `EXPECTED_PREVIOUS_HANDOVER`, `DISPLAY_TITLE`, `SPRINT_GOAL`, `DEMO_PLAN_GROUNDING`, argparse help defaults, module docstring) all derive from ledger + brief.

**Files affected:**

- New: `src/alfred/render/__init__.py`, `src/alfred/render/handover_inputs.py` (renderer)
- Edit: `scripts/generate_next_canonical_handover.py` — delete or thin-passthrough the hand-edited constants; load ledger; pick active brief; call renderer; pass result to existing planner pipeline
- New: `tests/test_render/test_handover_inputs.py` (renderer-fixture tests per proposal D)
- Edit: `tests/test_scripts/test_generate_next_canonical_handover.py` — replace any remaining prose assertions with renderer-output assertions over a fixture ledger

**Test strategy:** Renderer-fixture tests: feed a fixture ledger with a known active brief, assert deterministic output. Integration test: generator produces a draft for phase 6 (or whatever phase is planning in the seed ledger) using the renderer instead of constants. Manual: dry-run the generator and inspect the prompt.

**Risk:** High. This is the slice that changes how phase advances work. Mitigation: keep the script's external interface (CLI args, output paths) identical; the change is purely internal source-of-truth.

**Dependencies:** Slices 2 (ledger), 4 (section contract), 5 (context bundle).

**Acceptance criteria:**

- Hand-edited identity constants are gone (or thin pass-throughs from ledger).
- Phase advance flow is: edit `PHASE_LEDGER.yaml` -> run generator. Nothing else.
- Renderer-fixture tests assert deterministic output.
- A dry-run for the next phase produces a prompt equivalent to (or better than) what the hand-edited approach would have produced.

## Slice 7 — Pre-flight validators

**Objective:** Five deterministic checks before any LLM call. Per `ADR-0003`.

**Files affected:**

- New: `src/alfred/validate/__init__.py`, `src/alfred/validate/preflight.py` (the 5 checks)
- Edit: `scripts/generate_next_canonical_handover.py` — call preflight before invoking the planner; hard-fail on failure
- New: `tests/test_validate/test_preflight.py`

**Test strategy:** Each check tested in isolation with a deliberately-malformed ledger. Integration test: real ledger passes preflight. Negative test: `next_handover_id` mismatch is caught and the LLM is never invoked.

**Risk:** Medium. Adds a fail-fast gate that could surface latent issues in current ledgers — but that's the point.

**Dependencies:** Slices 2, 5, 6.

**Acceptance criteria:**

- All 5 checks implemented, each with at least one negative test.
- Generator hard-fails before any LLM call when preflight fails.
- A passing preflight for the seed ledger is a regression test.

## Slice 8 — Post-generation validators

**Objective:** Six deterministic checks on planner output before promotion. Per `ADR-0003`.

**Files affected:**

- New: `src/alfred/validate/postgen.py`
- Edit: `scripts/generate_next_canonical_handover.py` — call postgen after planner returns; on failure, write `FAILED_CANDIDATE` artifact, do not promote
- New: `tests/test_validate/test_postgen.py`
- Possible edit: `scripts/validate_alfred_handover.py` to share check primitives

**Test strategy:** Each check tested with a synthetic output that violates exactly that check. Integration test: a known-good prior handover (e.g. #12) passes all 6 checks against its corresponding brief reconstructed from the ledger.

**Risk:** Medium. The "task closure" and "hard-rule presence" checks need careful matching logic (verbatim or declared near-verbatim).

**Dependencies:** Slices 2, 5, 6.

**Acceptance criteria:**

- All 6 checks implemented, each with at least one negative test.
- No LLM-judge anywhere (test enforces by inspecting imports, or by code review).
- Reconstructable past handovers (#10, #11, #12) pass postgen against their notional briefs.

## Slice 9 — Failed-candidate filename short-circuit

**Objective:** `validate_alfred_handover.py` recognizes `*_FAILED_CANDIDATE.md` and skips id/filename checks while running everything else.

**Files affected:**

- Edit: `scripts/validate_alfred_handover.py`
- New/edit: `tests/test_scripts/test_validate_alfred_handover.py`

**Test strategy:** Synthetic `FAILED_CANDIDATE` file with intentional id/filename mismatch — passes id-skip, fails on a separate check (e.g. malformed reference tag) to confirm other checks still run.

**Risk:** Low.

**Dependencies:** Slice 3 (parser shared) is helpful but not strict.

**Acceptance criteria:**

- `FAILED_CANDIDATE` files no longer produce id/filename mismatch errors.
- All other validation behavior is unchanged on those files.

## Recommended First Slice

Slice 1 — Repo cleanup
