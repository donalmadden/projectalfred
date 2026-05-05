# Alfred's Handover Document #15 — Concern X, Slice 3: Reference Tag Canonicalization

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_15
**date:** 2026-05-05
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_14
**baseline_state:** Slice 2 (phase ledger models + loader + seed) is complete; Slice 3 must harden reference-tag parsing and validator integration without starting any Slice 4+ work.

**Reference Documents:**
- `CONTEXT.md` — authoritative glossary for canonical reference-tag syntax (`[future-doc: <path>]`, `[future-path: <path>]`) and the no-LLM deterministic validation constraint.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — ratified resolution that reference tags stay inline in markdown prose (document as protocol) and must be parsed deterministically (no inference, no manifest-side semantics).
- `docs/active/POST_GRILL_1.md` — the Slice 3 scope definition: new parser module, validator refactor to consume it, parser + integration tests, and an audit/normalization pass over `docs/`.
- `docs/canonical/ALFRED_HANDOVER_14.md` — binding slice discipline and the explicit forward plan: execute Slice 3 only; do not start Slice 4+ (doc-class section contracts, renderer replacement, preflight/postgen validator expansion, failed-candidate handling).

This handover exists because Alfred’s current validators and prose checks still conflate two different categories of “paths written in a handover”:

1) paths that must exist in *this* repo today (e.g., backticked docs/... references that should resolve), and
2) paths that intentionally point into a future/external workspace (e.g., the blank-project demo workspace).

Concern X resolved this by requiring **typed reference tags inline in prose**. Slice 3 is the “lock it in code” step: implement a deterministic parser that recognizes **exactly** the two canonical forms and emits precise, location-rich errors for malformed variants; refactor `scripts/validate_alfred_handover.py` to use that shared parser instead of ad-hoc regex; and add tests + a narrow audit to ensure current canonical docs don’t contain variants.

---

## WHAT EXISTS TODAY

### Git History

```
22e9a46  lint: fix Ruff import cleanup
71f9160  ledger: fill ALFRED_HANDOVER_14 post-mortem and CONTEXT.md clarifications
9ecbf65  ledger: task 2 — add YAML loader and seed PHASE_LEDGER.yaml
914268c  ledger: align Brief field with CONTEXT.md (followups_from_prior_phase) and add plan_path
f362de3  ledger: task 1 — add PhaseLedger Pydantic models + validation
7453d8c  HANDOVER 14 updated
8a8be72  cleanup: task 3 — fill post-mortem in ALFRED_HANDOVER_13
2ade6f7  cleanup: task 2 — delete 3 stale prose-assertion tests from canonical handover generator test module
025203c  cleanup: task 1 — delete obsolete dogfood/phase7 scripts and test
4103fa2  HANDOVER 13 updated
5dd5297  added 1st post-grill content & updates
08e7ff8  demo successfully ran
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Reference-tag semantics (current behavior and gap)

- The canonical reference-tag forms are defined in `CONTEXT.md` (two forms only):
  - `[future-doc: <path>]`
  - `[future-path: <path>]`
- Today, tag recognition inside validation is not guaranteed to be centralized behind a single parser module with:
  - a typed output (so validators don’t re-interpret strings inconsistently), and
  - deterministic, location-rich error reporting for malformed variants.

This slice introduces a small “reference semantics layer” as code: a deterministic parser module used by validators.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Tags stay inline in prose.** `[future-doc: ...]` / `[future-path: ...]` must remain embedded in markdown text, not moved into any manifest side-channel (`docs/DOCS_MANIFEST.yaml` is not where these semantics live). (From `CONTEXT.md`, `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md`.)
2. **Deterministic validation only — no LLM-judge anywhere in the chain.** Tag parsing must be deterministic code with explicit syntax rules. (From `CONTEXT.md`.)
3. **Slice discipline:** do Slice 3 only. Do not start Slice 4+ work (doc class section contracts, renderer replacement, new preflight/postgen validator stages, failed-candidate filename short-circuiting). (From `docs/canonical/ALFRED_HANDOVER_14.md`, `docs/active/POST_GRILL_1.md`.)

---

## HARD RULES

1. **Obey Slice 3 scope only:** implement reference-tag parser + validator integration + tests + minimal doc audit. Do not implement Slice 4+ deliverables (doc section contracts, renderer replacement, new validation stages, failed-candidate handling).
2. **Canonical syntax is exact and exclusive:** accept only `[future-doc: <path>]` and `[future-path: <path>]` exactly (brackets + prefix + colon). No additional tag types (e.g. `[deferred-doc:]`) in this slice.
3. **No semantic inference:** the parser must not “guess” intent. It either parses a canonical tag or emits an error. No heuristic acceptance of near-misses.
4. **Deterministic only:** no LLM calls and no LLM-as-judge logic in validation or parsing.
5. **Placement rules are binding for new files:**
   - per **tool/module placement conventions**, new reference-tag parsing code must live under `src/alfred/`.
   - per **test placement rule**, new tests must land under `tests/` using `test_*.py`.
   - per **doc placement rule**, any doc edits are confined to `docs/*.md`.

---

## WHAT THIS PHASE PRODUCES

- A new reference-tag parsing module `src/alfred/refs/tags.py` **to be created in this phase** (per Slice 3 plan) that:
  - parses only `[future-doc: <path>]` and `[future-path: <path>]`;
  - returns a typed object (e.g., `ReferenceTag` with `kind` and `path`);
  - provides precise errors with source location (line/column or equivalent index ranges) for malformed tags.
- A package marker `src/alfred/refs/__init__.py` **to be created in this phase** (per Slice 3 plan).
- A refactor of `scripts/validate_alfred_handover.py` (exists today) to consume the shared parser module (no inline regex duplication).
- New tests:
  - `tests/test_refs/test_tags.py` **to be created in this phase** (per test placement rule).
  - A small integration test update/addition under existing validator test coverage (exact file to be determined by executor based on current test layout) to prove the validator correctly recognizes canonical tags and rejects malformed variants deterministically.
- A narrow audit/normalization pass over canonical docs under `docs/` to ensure there are no non-canonical tag spellings (only if found).

Out of scope:
- Any doc-class section contract work (Slice 4).
- Any renderer replacement / generator refactor (Slice 6).
- Adding new validator phases (preflight/postgen expansion) beyond refactoring the existing handover validator to use the new parser.
- Adding a third tag type (e.g. `[deferred-doc:]`).
- Any attempt to “resolve” future/external paths against a filesystem; `[future-doc:]` / `[future-path:]` explicitly mean “do not resolve against this repo.”

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Implement deterministic reference-tag parser module | `src/alfred/refs/tags.py` + `src/alfred/refs/__init__.py` with typed parse output + location-rich errors | CHECKPOINT-1 |
| 2 | Add parser unit tests (canonical + pathological) | `tests/test_refs/test_tags.py` | |
| 3 | Integrate parser into `validate_alfred_handover.py` + add integration coverage | Validator uses shared parser; integration test proves end-to-end behavior | |
| 4 | Audit/normalize docs for non-canonical tag variants (only if needed) | Minimal edits to `docs/` so all canonical handovers parse cleanly | |

---

## TASK 1 — Implement deterministic reference-tag parser module

**Goal:** Create a single shared parser that recognizes exactly the two canonical inline tags and produces typed results or deterministic, location-rich errors.

### Implementation

1. **Create package skeleton** — add `src/alfred/refs/__init__.py` **to be created in this phase**.
   - Rationale: keep reference semantics code discoverable and importable without touching unrelated packages.

2. **Create parser module** — add `src/alfred/refs/tags.py` **to be created in this phase** (per Slice 3 plan).
   - Define a small typed model (dataclass or Pydantic is acceptable; choose the lightest thing that meets needs) e.g.:
     - `ReferenceTag(kind: Literal["future-doc", "future-path"], path: str, span: (start, end) or line/col metadata)`
   - Provide a deterministic parse API designed for validator consumption, for example:
     - `extract_reference_tags(markdown_text: str) -> list[ReferenceTag]`
     - or `iter_reference_tags(markdown_text: str) -> Iterator[ReferenceTag]`
   - Parsing requirements (must be explicit in code, not implied):
     - Accept only exact prefixes: `future-doc` and `future-path`.
     - Require a colon after the prefix: `[future-doc:` not `[future-doc ]`.
     - Require a closing `]`.
     - Capture the `<path>` substring as-is (trim policy must be decided; see Open Questions).
     - Surface malformed tags with an error type that includes:
       - what was expected,
       - where (line/column strongly preferred), and
       - the offending snippet.

3. **Define error contract** — add a deterministic exception type in `src/alfred/refs/tags.py`.
   - Example: `ReferenceTagParseError(message, line, col)`.
   - The validator should be able to catch this and print a stable, testable error message.

4. **Keep scope tight** — do not implement generalized markdown parsing.
   - The parser may use regex, but must be:
     - strict on canonical form,
     - tested against edge cases (nested brackets, whitespace variants),
     - able to pinpoint location.

### Verification

```bash
# run the unit tests (exact command depends on repo conventions)
pytest -q

# ensure type checking remains green
pyright
```

**Expected:**
- Parser accepts canonical tags in arbitrary prose.
- Parser rejects malformed tags with deterministic messages that include location.

**Suggested commit message:** `refs: task 1 — add deterministic reference-tag parser`

### CHECKPOINT-1 — Parser contract agreed and usable by validator

**Question:** Is the parser strict enough to prevent near-miss variants, but ergonomic enough that the validator can report actionable errors (with stable location) without needing ad-hoc regexes?

**Evidence required:**
- A pasted snippet from a unit test run showing:
  - at least one canonical tag parse success assertion, and
  - at least one malformed tag failure assertion that includes line/column (or an equivalent stable location contract).
- A pasted excerpt of the public API signatures from `src/alfred/refs/tags.py`.

| Observation | Likely call |
|---|---|
| Canonical forms parse; malformed forms fail with stable, location-rich errors; API is simple for validator consumption | PROCEED |
| Canonical forms parse, but error locations are missing/unstable or API forces validator to re-parse lines manually | PIVOT |
| Parser is permissive (accepts variants), or scope drift into generalized markdown parsing begins | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do **not** add new reference tag types (e.g. `[deferred-doc:]`) in this slice.
2. Do **not** move tags into `docs/DOCS_MANIFEST.yaml` or any other side metadata; tags must remain inline in prose.
3. Do **not** add any LLM-judge or “smart interpretation” step to validation.
4. Do **not** start Slice 4+ tasks (doc-class section contracts, renderer replacement, new validator phases, failed-candidate filename policies).

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- Slice discipline held: `scripts/generate_next_canonical_handover.py` was not modified, no new validator phases were introduced, and no third tag type was added.
- The parser landed as a single, narrow module ([src/alfred/refs/tags.py](src/alfred/refs/tags.py)) with three deterministic public functions: `extract_reference_tags` (raises), `iter_reference_tags` (raises mid-iteration), and `scan_reference_tags` (collects all errors). Validators that want fail-fast and validators that want surface-everything both have a clean entry point.
- Pyright + 564 tests pass after the migration; the existing reference-doc validator tests passed unchanged against the refactored implementation, which confirms public signatures (`path_has_future_tag`, `link_is_inventory_exempt`) stayed stable.
- Repo-wide audit (Task 4) found 41 canonical tags across `docs/**/*.md` and **0** real malformed tags, so no doc edits were required. The `[future-doc:]`-style references in `HANDOVER_WORKFLOW_DISCUSSION.md`, `POST_GRILL_1.md`, and `ALFRED_HANDOVER_15.md` are all inside backticks and are correctly skipped by the parser.
- Behaviour-correctness improvement landed: a malformed near-miss like `[future-doc bad]` no longer silently exempts a nearby `docs/...md` path from inventory/existence checks. This matches the Slice 3 acceptance criterion to "reject malformed variants deterministically."

**What was harder than expected:**
- The HANDOVER_15 plan named `scripts/validate_alfred_handover.py` as the integration target, but that script is a *structural* gate and has zero reference-tag handling. The ad-hoc regex (`_EXPLICIT_FUTURE_PATH_TAG_RE`) actually lives in [src/alfred/tools/reference_doc_validator.py:23-26 (pre-refactor)](src/alfred/tools/reference_doc_validator.py) and is consumed by `scripts/validate_alfred_planning_facts.py`. The discrepancy was caught at CHECKPOINT-1 evidence and flagged before proceeding.
- Strict parsing initially produced 8 false positives across three real docs (`HANDOVER_WORKFLOW_DISCUSSION.md`, `POST_GRILL_1.md`, `ALFRED_HANDOVER_15.md`) — every one of them inside markdown code spans documenting the tag grammar itself (e.g. `` `[future-doc:]` `` as a label). Without code-span awareness, every doc that *describes* the parser would fail the parser. Resolved by adding narrow code-span skipping (single-backtick spans + triple-backtick fenced blocks); explicitly not a generalised markdown parser.
- The original `iter_reference_tags` API raised mid-iteration, which is wrong for validators that want every error in one pass. Refactored to share a single private `_walk()` generator with both raising (`iter_reference_tags`/`extract_reference_tags`) and collecting (`scan_reference_tags`) wrappers.

**Decisions made during execution (deviations from this plan):**
- *Task 3 retargeting.* What changed: integrated the shared parser into [src/alfred/tools/reference_doc_validator.py](src/alfred/tools/reference_doc_validator.py) (consumed by `scripts/validate_alfred_planning_facts.py`) instead of `scripts/validate_alfred_handover.py`. End-to-end coverage was added to [tests/test_scripts/test_validate_alfred_planning_facts.py](tests/test_scripts/test_validate_alfred_planning_facts.py). `scripts/validate_alfred_handover.py` was left unchanged — adding tag validation there would be new scope, not a refactor. Why: the named script had no ref-tag handling; the actual duplicated regex was elsewhere. Approved by: human (Donal), in-band, recorded after CHECKPOINT-1 evidence.
- *Markdown code-span skipping in the parser.* What changed: parser now skips text inside single-backtick inline code spans and triple-backtick fenced blocks (`_FENCED_BLOCK_RE`, `_INLINE_CODE_RE`). Why: without it, every doc that documents the tag grammar in prose would be flagged as malformed; this is targeted, not "generalised markdown parsing." Approved by: executor judgment, recorded here. Considered the alternative of editing 3 docs to use a non-bracket form; rejected as it would amputate the docs' ability to discuss their own grammar.
- *Added `scan_reference_tags()` to the parser API.* What changed: third public function alongside the two named in the plan, returning `(tags, errors)` for non-raising consumption. Why: validators need to surface every malformed tag in one pass; raising-on-first would either crash the validator or be silently caught and dropped. Approved by: executor judgment.
- *Reused `ReferenceDocFinding` with `issue_type="malformed_reference_tag"`* rather than introducing a new finding payload type. Why: keeps the validator-finding taxonomy stable; semantics fit (the malformed tag is a reference-doc hygiene issue). Approved by: executor judgment.

**Forward plan:**
- HANDOVER_16 should pick up Slice 4 (doc-class section contracts) per `docs/active/POST_GRILL_1.md`. The reference-tag parser is now the single source of truth for tag semantics — future validators should consume `alfred.refs.tags` rather than reach for a regex.
- A second consumer to consider migrating: [src/alfred/agents/planner.py:120-122](src/alfred/agents/planner.py#L120-L122) currently embeds the canonical tag form in a prompt string. That's a *production* of tags, not a parse, so it's correctly out of scope for Slice 3, but Slice 4 may want a single-source `CANONICAL_TAG_DOC_EXAMPLE` constant to keep the prompt and the parser in lockstep.
- The audit script used in this slice (`python -c "from alfred.refs.tags import scan_reference_tags; ..."`) is ad-hoc; if doc audits become recurrent, promoting it to a `scripts/audit_reference_tags.py` is the natural next move. Deferred — Slice 3 found nothing, so the cost of writing the script wasn't justified.
- The proximity model in `path_has_future_tag` (32-char look-behind, 160-char look-ahead) is preserved verbatim from the previous regex-based implementation. It is not load-bearing for Slice 3 correctness, but a future Slice may want to revisit "what does 'attached to' mean?" with the parser's structured spans now available.

**next_handover_id:** ALFRED_HANDOVER_16