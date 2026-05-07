<!--
  Alfred canonical handover scaffold.

  This file is the house-style contract for Alfred canonical handovers. The
  planner prompt injects its contents and requires every `##` and `###`
  heading below to appear verbatim in generated drafts. The promotion
  validator (`scripts/validate_alfred_handover.py`) fails closed if a
  canonical draft is missing any required section.

  Scope: Alfred canonical promotion only. Legacy BOB documents continue to
  parse via `HandoverDocument.from_markdown()` without this strictness;
  the generic reference template at `configs/handover_template.md` covers
  the BOB-style path. Do not conflate the two.

  Placeholders:
    <angle-bracket placeholders> are substituted by the planner.
    Headings are NOT placeholders — leave them exactly as written.
-->

# Alfred's Handover Document #20 — Concern X, Slice 8: Post-generation Validators (Block Promotion + Write FAILED_CANDIDATE)

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_20
**date:** 2026-05-07
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_19
**baseline_state:** Slice 7 pre-flight validation exists and fails fast before any LLM call; the generator can produce a draft handover via the planner pipeline but does not yet deterministically validate the *returned draft* before promoting it to the canonical output path.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_19.md` — continuity for Slice 7 pre-flight invariants; must preserve fail-fast-before-LLM and the shared context-input planning seam.
- `docs/active/POST_GRILL_1.md` — authoritative slice plan; defines Slice 8 objective (six deterministic post-generation checks), file targets, and test strategy.
- `docs/active/HANDOVER_WORKFLOW_DISCUSSION.md` — resolved workflow constraints: phase ledger authority flow, brief semantics, and validator-chain shape.
- `CONTEXT.md` — glossary and protocol constraints (phase ledger, brief, context roles, doc class section contract, and the no-LLM-judge rule).
- `docs/DOCS_POLICY.md` — docs governance constraints relevant to citations and reference hygiene in canonical handovers.
- `docs/protocol/architecture.md` — system topology constraints (single FastAPI module path, agent/tool layout conventions) that planning must not contradict.

This phase adds a deterministic, post-generation validation gate that runs **after** the planner returns a draft and **before** the generator promotes it to the canonical output location. The gate must (a) enforce six minimal safety/closure checks on the draft, (b) write a `FAILED_CANDIDATE` artifact on failure, and (c) preserve Slice 7’s pre-flight fail-fast behavior and Slice 5/6’s context-bundle + renderer-derived identity seams. Per protocol, validators are deterministic code only: no LLM-as-judge anywhere.

---

## WHAT EXISTS TODAY

### Git History

```
f2559a1  handover: close out slice 7 and seed slice 8
3cb4c4c  tests: task 3 — preflight coverage (negative checks + real-ledger regression)
8a05341  generator: task 2 — run preflight before planner call (fail fast)
a9f6d66  validate: task 1 — add preflight validator (5 deterministic checks)
b052fd8  docs: clarify slice 7 scope-input preflight
5815670  generator: bootstrap slice 7 handover generation
bf9a99b  docs: seed slice 7 handover brief
e735e2e  docs: add ALFRED_HANDOVER_18 and tuning discussion
f83afca  tests: task 3 polish — fixture-driven script-boundary dry-run coverage
e881c4f  tests: task 3 — assert renderer outputs, not prose constants
9f04f40  generator: task 2 follow-up — derive scope-spec source path, add --dry-run, drop stale identity literals
beb82ed  generator: task 2 — derive identity constants via renderer
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current generator + validation surface (grounded, present-tense)

- FastAPI app **exists today** as a single module at `src/alfred/api.py` with 11 endpoints (not in scope to change).
- Agent modules **exist today** under `src/alfred/agents`: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`.
- Tool modules **exist today** under `src/alfred/tools`: `board_write_contract`, `docs_policy`, `git_log`, `github_api`, `handover_authoring_context`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`, `story_markdown`.
- The canonical handover generation workflow is driven by `scripts/generate_next_canonical_handover.py` (**exists today**). Slice 7 added a deterministic pre-flight gate that must hard-fail **before any LLM call**.
- A `validate` package **exists today** under `src/alfred/validate` and includes Slice 7 pre-flight validation (e.g., `src/alfred/validate/preflight.py` exists today). Slice 8 will add post-generation validation.
- `pyproject.toml` **exists today** with `[project]=True` and `[project.scripts]=True`, and declares `alfred.cli:main` as the CLI entry.
- Type checking uses **pyright** (do not introduce `mypy`).

### Key Design Decisions Inherited (Do Not Revisit)

1. **No LLM-judge in validation** — all validators (pre-flight and post-generation) are deterministic code; semantic judgment is reserved for the human approval gate (per `CONTEXT.md`).
2. **Exactly three context roles** — `scope`, `carry_forward`, `continuity` with fixed dedup precedence `scope` > `carry_forward` > `continuity` (per `CONTEXT.md`).
3. **Continuity is explicit** — preserve the explicit `previous_handover` contract; do not infer continuity by id ordering.
4. **Renderer-derived identity is the source of truth** — do not reintroduce hand-edited identity constants into the generator.
5. **Fail-fast pre-flight stays first** — Slice 8 adds a second gate after planner return; it must not weaken, bypass, or reorder Slice 7 pre-flight.

---

## HARD RULES

1. **Slice 8 only**: implement post-generation validation after planner return; do **not** start Slice 9 failed-candidate filename short-circuit logic.
2. **No LLM-judge anywhere**: post-generation checks must be deterministic code only (per `CONTEXT.md` / ADR-0003 referenced in workflow discussion).
3. **Preserve Slice 7 pre-flight**: generator must still hard-fail pre-flight errors before any planner/LLM call; postgen is additive.
4. **On post-generation failure, write `FAILED_CANDIDATE` and do not promote**: failure must block promotion to the canonical output path.
5. **Preserve Slice 5/6 seams**: keep the three-role `ContextBundle` seam and renderer-derived identity / CLI surface intact.

---

## WHAT THIS PHASE PRODUCES

- A deterministic post-generation validator module `src/alfred/validate/postgen.py` (**to be created in this phase**) implementing the fixed six-check minimum over planner output.
- Generator wiring updates to run post-generation validation after planner return and before promotion, writing a `FAILED_CANDIDATE` artifact on failure (edits to `scripts/generate_next_canonical_handover.py`).
- A dedicated test module `tests/test_validate/test_postgen.py` (**to be created in this phase**) with isolated negative tests per check plus at least one known-good regression.

Out of scope:
- Slice 9 failed-candidate filename short-circuit logic.
- Broad validator refactors beyond minimum sharing needed to land Slice 8 safely.
- FastAPI endpoint changes.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Implement deterministic post-generation validator | `src/alfred/validate/postgen.py` with six checks + error formatting | CHECKPOINT-1 |
| 2 | Wire postgen into generator promotion path | Generator runs postgen after planner return; on failure writes `FAILED_CANDIDATE` and blocks promotion | CHECKPOINT-2 |
| 3 | Add isolated negative tests + known-good regression | `tests/test_validate/test_postgen.py` with per-check negatives + regression pass | CHECKPOINT-3 |

---

## TASK 1 — Implement deterministic post-generation validator (six checks)

**Goal:** Create a pure, unit-testable post-generation validator that deterministically blocks promotion when the planner draft violates minimum protocol safety/closure checks.

### Implementation

1. **Create the module** — create `src/alfred/validate/postgen.py` (**to be created in this phase**). (Placement: per *tooling structure*, validation modules live under `src/alfred/validate/` which already exists today.)
2. **Define an explicit results contract** — implement a small return type (e.g. dataclass) representing `ok` + `errors`, and a `format_errors()` helper (match Slice 7 preflight style: validators stay pure/non-printing; script is the adapter).
3. **Implement the six deterministic checks** (minimum set; deterministic string/structure checks only):
   - **Check 1 — Metadata identity/chronology closure**: draft must contain `**id:** ALFRED_HANDOVER_20`, `**date:** 2026-05-07`, and `**previous_handover:** ALFRED_HANDOVER_19` in the `## CONTEXT — READ THIS FIRST` block.
   - **Check 2 — Required section contract present**: draft must contain all required `##` headings from the canonical scaffold, and include `### Git History` under `## WHAT EXISTS TODAY`.
   - **Check 3 — Git history integrity**: within the `### Git History` fenced block, the draft must include the exact commit lines supplied in the authoring packet (byte-for-byte string match on each line).
   - **Check 4 — Reference-doc hygiene closure**: the `Reference Documents` list must be non-empty and must not include `[future-doc:]` / `[future-path:]` tags (Slice 8 is validating a candidate for promotion; future tags indicate non-closed references).
   - **Check 5 — Hard-rules presence**: the `## HARD RULES` section must contain the Slice 8 invariants (at least the two most safety-critical ones): (a) no LLM-judge, and (b) write `FAILED_CANDIDATE` and do not promote on postgen failure; plus a check that Slice 8 scope limit (“Slice 8 only; do not start Slice 9…”) is present.
   - **Check 6 — Task closure against brief seed**: verify that `## TASK OVERVIEW` includes Tasks 1–3 corresponding to this phase’s brief (titles may vary slightly, but must include clear mapping to: postgen module, generator wiring, tests). Additionally ensure each task section exists (`## TASK 1 —`, `## TASK 2 —`, `## TASK 3 —`).

   Notes:
   - Keep matching deterministic and reviewable: prefer exact-string checks for the most safety-critical invariants (metadata, required headings, git history), and constrained substring checks for task titles.
   - No semantic “is this well written” checks.
4. **Expose one primary entrypoint** — e.g. `validate_postgen(draft_markdown: str, *, expected_id: str, expected_previous: str, expected_date: str, expected_git_history_lines: list[str]) -> PostgenResult`.
5. **Keep imports minimal** — only stdlib + repo-local utilities that are deterministic; do not import LLM tooling modules.

### Verification

```bash
pytest -q
python -m pyright
```

**Expected:**
- Unit tests for postgen can call the validator directly without invoking the generator script.
- `pyright` passes without new type errors.

**Suggested commit message:** `validate: task 1 — add post-generation validator (six deterministic checks)`

### CHECKPOINT-1 — Are the six checks precise, deterministic, and minimal?

**Question:** Do the post-generation checks deterministically prevent promotion of an invalid canonical draft, without expanding into Slice 9 logic or semantic judging?

**Evidence required:**
- A pasted list of the six checks as implemented (names + 1–2 lines of matching logic each).
- A pasted snippet of the validator public entrypoint signature.

| Observation | Likely call |
|---|---|
| Checks are purely deterministic (string/structure), cover metadata/sections/git history/hard rules/task closure/reference hygiene | PROCEED |
| Checks rely on fuzzy heuristics that could pass clearly invalid drafts or behave nondeterministically | PIVOT |
| Any LLM import/usage appears in postgen module, or Slice 9 logic is being added | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Wire postgen into generator (block promotion + write FAILED_CANDIDATE)

**Goal:** Ensure `scripts/generate_next_canonical_handover.py` runs post-generation validation **after** planner output and **before** promotion to canonical output; on failure it must write a `FAILED_CANDIDATE` artifact and exit non-zero (or otherwise signal failure) without modifying the canonical output.

### Implementation

1. **Locate the promotion seam** — in `scripts/generate_next_canonical_handover.py` (exists today), identify where planner output is currently written/promoted to canonical output path.
2. **Call postgen after planner return** — import the new validator from `src/alfred/validate/postgen.py` and run it on the candidate markdown.
3. **On failure, write FAILED_CANDIDATE** — implement writing of a `FAILED_CANDIDATE` artifact *without* adding Slice 9 filename short-circuit logic. Constrain to:
   - A deterministic location already used/appropriate for generator artifacts if one exists; otherwise, add the smallest new path convention in the script (document it inline in comments).
   - Include validator error output from `format_errors()` in the artifact body.
4. **Block promotion** — ensure canonical output path is not updated when postgen fails.
5. **Preserve Slice 7 ordering** — pre-flight must still run before any LLM call; postgen must run only after planner output is available.
6. **Preserve CLI surface** — do not change external CLI flags/behavior other than failing the run when postgen fails.

### Verification

```bash
pytest -q
python scripts/generate_next_canonical_handover.py --dry-run
```

**Expected:**
- When forced to fail postgen (via a test fixture / injected bad markdown), the generator writes `FAILED_CANDIDATE` and does not touch the canonical output.
- `--dry-run` still works and still performs deterministic checks.

**Suggested commit message:** `generator: task 2 — run postgen before promotion; write FAILED_CANDIDATE on failure`

### CHECKPOINT-2 — Does generator promotion fail closed?

**Question:** Can we demonstrate (with test evidence) that a postgen failure writes a `FAILED_CANDIDATE` artifact and blocks promotion, while pre-flight still fails fast before any LLM call?

**Evidence required:**
- A pasted test output excerpt showing the failing case and confirming artifact write.
- A pasted snippet showing the generator control flow ordering: preflight → planner call → postgen → promote.

| Observation | Likely call |
|---|---|
| Control flow ordering is correct; artifact is written; canonical promotion is blocked; no CLI drift | PROCEED |
| Artifact is written but promotion can still happen in some branch (e.g., exception path), or ordering is unclear | PIVOT |
| Pre-flight ordering is broken (LLM can be called before preflight), or Slice 9 logic creeps in | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 3 — Add isolated negative tests + known-good regression

**Goal:** Add tests that prove each postgen check fails in isolation, plus a regression test that a known-good prior handover passes postgen when validated against an appropriate notional brief/expectations.

### Implementation

1. **Create test module** — create `tests/test_validate/test_postgen.py` (**to be created in this phase**). (Placement: per *test placement rule*, tests belong under `tests/` using `test_*.py`.)
2. **Unit tests for each check** — create at least six tests, each crafting a minimal markdown draft that fails exactly one check:
   - missing/incorrect `id`
   - missing required heading
   - altered git history line
   - reference docs empty / contains future tag
   - hard rules missing required invariant phrase
   - task overview missing task row or missing task section
3. **Integration / regression test** — validate a known-good prior canonical handover (e.g. `docs/canonical/ALFRED_HANDOVER_12.md` exists today) against expectations constructed in-test:
   - This should not require reconstructing the entire historical brief system; it can be a “known-good draft passes structural checks” regression with appropriately parameterized `expected_id/previous/date/git_history` for that handover.
   - If deriving those expectations requires a helper, keep it deterministic and local to the test module.

   Note: The authoring packet suggests “reconstructable known-good handovers (#10/#11/#12) pass postgen against their notional briefs.” If full brief reconstruction from ledger is non-trivial, constrain to one handover regression in this slice and leave broader reconstruction as a follow-up (explicitly documented in `## WHAT NOT TO DO`).
4. **Script-boundary test (optional but preferred)** — add/extend a test that exercises `scripts/generate_next_canonical_handover.py` and asserts:
   - postgen failure → `FAILED_CANDIDATE` exists and canonical output not changed.

### Verification

```bash
pytest -q
python -m pyright
```

**Expected:**
- Each check has at least one negative test.
- At least one known-good regression passes.

**Suggested commit message:** `tests: task 3 — postgen coverage (negatives + known-good regression)`

### CHECKPOINT-3 — Are tests proving the gate behavior (not just unit behavior)?

**Question:** Do we have convincing evidence that (a) postgen catches the intended failure modes, and (b) generator promotion is blocked when postgen fails?

**Evidence required:**
- A pasted `pytest` summary showing the new tests.
- For the script-boundary test: a pasted assertion showing `FAILED_CANDIDATE` is written and canonical output is not updated.

| Observation | Likely call |
|---|---|
| All six checks have negative tests; at least one known-good regression passes; promotion-blocking is tested at script boundary | PROCEED |
| Only unit tests exist; generator wiring is untested; or regression is too brittle (prose assertions) | PIVOT |
| Tests require network/LLM, rely on nondeterminism, or effectively introduce an LLM-judge by snapshotting model output | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do **not** add any LLM-based evaluator/critic step to validation (no imports from LLM tooling; no “judge” prompts). Validators must be deterministic code only.
2. Do **not** implement Slice 9 failed-candidate filename short-circuit logic (keep failure handling minimal: write `FAILED_CANDIDATE`, block promotion).
3. Do **not** add prose-level snapshot assertions that will churn every handover (tests should assert structure, identity, and deterministic invariants; per workflow discussion, test the renderer/gates, not prose constants).
4. Do **not** change the three-role ContextBundle semantics or renderer-derived identity/CLI defaults while wiring postgen.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- Postgen landed cleanly as a sibling of the Slice-7 preflight module: same `check_*` shape, same orchestrator pattern, same `format_errors` operator surface. The package's public re-exports stayed minimal so callers compose explicit inputs rather than inheriting policy.
- The active phase's `Brief` (already in the ledger from Slice 6) carried everything postgen needed — `hard_rules`, `tasks[].intent`, `tasks[].title` — so deriving Check-5 anchors and Check-6 markers required no new schema or new editorial seed.
- Folding postgen into `validate_candidate()` reused the existing `FAILED_CANDIDATE` write convention. The artifact body now carries an HTML-comment validation-failure block at the tail so reviewers see both the failing draft and `format_postgen_errors()` output in one file.
- Symmetric script-boundary tests for the two gates now form a matched pair: `test_preflight_failure_blocks_planner_invocation` proves no LLM call before preflight; `test_postgen_failure_writes_failed_candidate_and_blocks_promotion` proves the canonical output is never written after a failing draft.

**What was harder than expected:**
- CHECKPOINT-1 went green only after two follow-up tightenings: Check 6 had to enforce per-task brief mapping (heading existence alone was too weak), and Check 5 had to refuse to silently no-op on empty phrases. Both gaps were caught by reviewer pushback, not by the validator's own self-tests.
- Substring-matching the brief's full `hard_rules` text would have failed the canonical handover #20 itself — the rendered prose legitimately paraphrases the brief. Resolution: extract one stable per-rule anchor (ALL-CAPS const, `Slice N`, CamelCase, hyphenated identifier) in the script and pass that to Check 5. The validator stayed a pure substring matcher; the deriver carries the paraphrase tolerance.
- CHECKPOINT-2 needed a deterministic script-boundary test, not a unit test. Driving `main()` past preflight into the postgen branch required patching the lazy `from alfred.X import Y` imports at the *source* module so the inner imports inside `main()` pick up the fakes, plus stubbing `validate_alfred_handover` and `validate_alfred_planning_facts` via `sys.modules` so postgen owned the failure signal.

**Decisions made during execution (deviations from this plan):**
- Hard-rule and task-marker derivers live in the script (the caller), not the validator. Why: the validator should stay a pure substring matcher; semantic normalisation (paraphrase tolerance) is project-specific policy that varies per slice. Putting it in the script keeps the validator reusable and the script auditable. Approved during CHECKPOINT-1 follow-up.
- Replaced `expected_task_count` with `required_task_markers: Sequence[Sequence[str]]` on the `validate_postgen` surface. Why: task count and per-task topic markers should share a single source of truth so a caller cannot pass `count=3` while supplying only two marker lists. The orchestrator now also raises `ValueError` on empty `required_hard_rule_phrases` or `required_task_markers` so Check 5/6 can never silently no-op. Approved during CHECKPOINT-1 follow-up.
- Folded postgen into the existing `validate_candidate()` path rather than running it as a separate gate stage. Why: a single failure path means the `FAILED_CANDIDATE` artifact captures every blocking issue (structure + facts + postgen) in one operator-readable artifact. Approved during Task 2.
- Enriched the `FAILED_CANDIDATE` artifact body with an HTML-comment block containing `format_postgen_errors()` output. Why: the brief required errors in the artifact body; HTML-comment keeps the file parseable as markdown by reviewers without polluting the draft. Approved during Task 2.

**Forward plan:**
- Ratify Slice 8 in `docs/active/PHASE_LEDGER.yaml` and seed Slice 9 as `ALFRED_HANDOVER_21` with `ALFRED_HANDOVER_20` as the explicit `previous_handover`.
- Slice 9 implements failed-candidate filename short-circuit in `scripts/validate_alfred_handover.py`: recognise `*_FAILED_CANDIDATE.md` filenames, skip id/filename checks, run every other structural check unchanged. Test strategy is a synthetic `FAILED_CANDIDATE` file with an intentional id mismatch plus a separate failing structural check, proving both halves of the contract.
- The hard-rule and task-marker derivers in `scripts/generate_next_canonical_handover.py` are slice-agnostic and should not need changes for Slice 9.
- Carry forward the seam discipline established here: validators stay deterministic pure matchers; semantic policy lives in callers; script-boundary tests prove gate behaviour end-to-end, not only at unit level.

**next_handover_id:** ALFRED_HANDOVER_21