# Alfred's Handover Document #4 — Output Hardening

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFREAD_HANDOVER_4_OUTPUT_HARDENING
**date:** 2026-04-20
**author:** Codex (diagnostic write-up for Donal)
**previous_handover:** ALFRED_HANDOVER_4
**baseline_state:** Phase 5 is complete. `docs/ALFRED_HANDOVER_5_DRAFT.md` exists and is substantively close to promotion, but the framework that generated it does not structurally enforce Alfred canonical output shape. The concrete miss that exposed this gap is the omission of `### Git History` under `## WHAT EXISTS TODAY`, even though the Alfred handover corpus treats that section as part of house style. The current codebase can generate, critique, compile, and execute handovers, but promotion to canonical Alfred protocol still relies too heavily on prompt quality and human catch-rate instead of hard output contracts.

**Reference Documents:**
- `~/code/projectalfred/docs/ALFRED_HANDOVER_4.md` — authoritative Phase 5 handover and post-mortem
- `~/code/projectalfred/docs/ALFRED_HANDOVER_4_BUG_SCRUB.md` — explicit error register for the Phase 6 draft scrub
- `~/code/projectalfred/docs/ALFRED_HANDOVER_5_DRAFT.md` — generated Phase 6 draft that exposed the output-hardening gap
- `~/code/projectalfred/configs/handover_template.md` — current canonical template, which does not encode Alfred house sections like `WHAT EXISTS TODAY` / `Git History`
- `~/code/projectalfred/src/alfred/agents/planner.py` — current planner prompt builder
- `~/code/projectalfred/src/alfred/schemas/handover.py` — current render/parse contract for handover documents
- `~/code/projectalfred/src/alfred/api.py` — current `/generate` path
- `~/code/projectalfred/scripts/generate_phase6.py` — current local generation path used to produce the Phase 6 draft

---

## WHAT EXISTS TODAY

### Git History — Relevant Baseline

```
fd724e1  phase5: task 6 — dogfood #2
79e2ce5  phase5: task 5 — hitl timeout
7b65daa  CODEX.md only; runtime unchanged after Phase 5 acceptance
```

### Current Output Pipeline

- `POST /generate` calls `run_planner(...)`, then `_run_critique_loop(...)`, and returns markdown only.
- `POST /compile` is separate and turns approved markdown into a structured `HandoverDocument`.
- `scripts/generate_phase6.py` reproduces the same planner + critique path locally and writes `docs/ALFRED_HANDOVER_5_DRAFT.md`.
- The current planner prompt asks for good handover content, but does not require Alfred house-style sections like `### Git History`.

### Current Structural Gap

- `configs/handover_template.md` is generic and does not encode Alfred canonical sections such as:
  - `## WHAT EXISTS TODAY`
  - `### Git History`
  - Alfred-style current-state recap blocks
- `configs/default.yaml` includes `handover.template_path`, but generation code does not currently use that template path as part of the planner scaffold.
- `HandoverDocument.render_markdown()` emits a generic schema-first layout, not the richer Alfred canonical house style.
- No validator exists that can block promotion when a generated Alfred handover is missing required sections.

### Why This Matters

- The framework currently treats canonical output shape as a prompting preference instead of a contract.
- That means the model can produce a document that is semantically useful but still not promotion-safe.
- Missing `Git History` is the symptom; the real defect is that Alfred house style is not encoded strongly enough in the generation and promotion path.

### Key Design Decisions Inherited (Do Not Revisit)

1. The codebase is the source of truth; the fix is to harden output contracts, not to explain away misses after the fact.
2. Alfred canonical handovers have a recognisable house style and that style should be enforced at promotion time.
3. Git history must come from real repository state, not from model hallucination.
4. The base `HandoverDocument` parser must remain permissive enough to handle legacy/Bob-style documents; Alfred-specific strictness belongs in an explicit profile or promotion gate.
5. Human approval remains required before a draft becomes protocol, but human review should not be the only defense against missing required sections.

---

## HARD RULES

1. **Do not solve this with prompt wording alone.** Prompt improvements are necessary but not sufficient.
2. **Do not require the model to invent git hashes or commit messages.** If `Git History` is required, feed it real git data.
3. **Do not make the base handover schema globally rigid** in a way that breaks permissive parsing of the existing BOB/legacy corpus.
4. **Do not leave `template_path` as decorative config.** If the setting remains in config, generation must actually use it.
5. **Do not allow promotion to canonical `ALFRED_HANDOVER_*.md` files without an explicit validation step.**
6. **Do not conflate draft generation with promotion.** `POST /generate` remains draft generation; promotion is a separate hardened step.
7. **One task = one commit** if this handover is executed as real implementation work. Suggested commit messages are provided below.

---

## WHAT THIS PHASE PRODUCES

- A canonical-output validation step that can fail promotion when required Alfred sections are missing
- A live Alfred-specific handover scaffold or output profile used during generation
- Structured git-history input for planner/generator paths
- Optional schema/render support for Alfred canonical `WHAT EXISTS TODAY` / `Git History` content
- Regression tests proving that a draft missing `### Git History` cannot silently become canonical

Out of scope:
- Implementing Phase 6 itself
- Redesigning the orchestrator runtime contract
- Rewriting the entire BOB corpus into Alfred house style
- Collapsing generic handover generation and Alfred canonical promotion into a single step

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Promotion Gate | `scripts/validate_alfred_handover.py` + tests | CHECKPOINT-1 |
| 2 | Template / Scaffold Wiring | Live Alfred canonical template/profile used during generation | |
| 3 | Structured Git History Input | Planner/generator path receives real git history | |
| 4 | Schema / Renderer Support | Optional Alfred canonical state/history fields round-trip safely | |
| 5 | Promotion Workflow Regression Pass | Missing-`Git History` case fails; canonical sample passes | CHECKPOINT-2 |

---

## TASK 1 — Promotion Gate

**Goal:** Make promotion to canonical Alfred handovers fail closed when required house-style sections are missing.

### Implementation

1. **Create `scripts/validate_alfred_handover.py`.**
   - Accept a markdown file path.
   - Exit non-zero if required Alfred sections are missing.
   - Minimum required headings:
     - `## CONTEXT — READ THIS FIRST`
     - `## WHAT EXISTS TODAY`
     - `### Git History`
     - `## HARD RULES`
     - `## TASK OVERVIEW`
     - `## WHAT NOT TO DO`
     - `## POST-MORTEM`

2. **Validate subsection placement, not just token presence.**
   - `### Git History` must appear under `## WHAT EXISTS TODAY`, not elsewhere in the file.
   - If the file is explicitly a draft, the validator may allow draft metadata, but it must still enforce structural requirements for promotion readiness.

3. **Add tests.**
   - One fixture missing `### Git History` must fail.
   - One fixture with all required Alfred sections must pass.
   - One fixture with `Git History` in the wrong section must fail.

4. **Document validator scope clearly.**
   - This validator is for Alfred canonical promotion, not for generic/Bob handovers.

### Verification

```bash
python scripts/validate_alfred_handover.py docs/ALFRED_HANDOVER_5_DRAFT.md
pytest tests/test_schemas/test_handover_output_profile.py -v
```

**Expected:**
- the validator fails on a fixture missing `### Git History`
- the validator passes on a canonical Alfred-style sample
- promotion readiness is now a machine-checkable contract, not a reviewer memory test

**Suggested commit message:** `output-hardening: task 1 — add alfred promotion validator`

### CHECKPOINT-1 — Promotion Gate Exists

**Question:** Can the framework now mechanically reject a canonical Alfred handover that is missing `### Git History`?

**Evidence required:**
- validator output for a failing fixture
- validator output for a passing fixture
- `pytest` output for the validator tests

| Observation | Likely call |
|---|---|
| Failing fixture is rejected; passing fixture is accepted | PROCEED |
| Validator only checks raw string presence, not section placement | PIVOT — tighten parsing before continuing |
| Validator cannot distinguish Alfred canonical files from generic handovers | PIVOT — add explicit scope/profile handling |
| Validator still allows promotion with missing `Git History` | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Template / Scaffold Wiring

**Goal:** Make Alfred canonical output shape come from a live scaffold/profile, not from prompt memory alone.

### Implementation

1. **Introduce an Alfred-specific canonical scaffold.**
   - Preferred approach: add `configs/alfred_handover_template.md`.
   - Alternative: upgrade `configs/handover_template.md` only if you explicitly decide there is no longer a generic template use case.

2. **Wire the template into generation.**
   - `handover.template_path` (or a new canonical-template setting) must be read during generation.
   - `src/alfred/api.py` and `scripts/generate_phase6.py` must pass scaffold content into the planner path.

3. **Make the planner prompt explicit about house style.**
   - Require the returned markdown to preserve the scaffold headings verbatim.
   - Require `## WHAT EXISTS TODAY` and `### Git History` explicitly for Alfred canonical outputs.

4. **Keep draft vs canonical responsibilities separate.**
   - Generation still returns a draft.
   - The scaffold shapes the draft.
   - The promotion validator decides whether the draft is eligible to become canonical.

### Verification

```bash
pytest tests/test_agents/test_planner.py -v
pytest tests/test_api.py -v
```

**Expected:**
- planner-facing tests confirm that the scaffold/profile is injected
- generated Alfred drafts now contain the required house sections by construction
- template config is now live runtime behavior rather than dead metadata

**Suggested commit message:** `output-hardening: task 2 — wire canonical scaffold into generation`

---

## TASK 3 — Structured Git History Input

**Goal:** Feed real git history into the generation path so `### Git History` is grounded in repository state instead of model recall.

### Implementation

1. **Extend the planner input contract.**
   - Add a field such as `git_history_summary: list[str]` or a structured `git_history` model to `PlannerInput`.
   - Keep it optional so non-repo or test contexts still work.

2. **Add a helper that reads git history deterministically.**
   - Use a bounded log window, for example the last 10–12 relevant commits.
   - The helper should degrade to an empty list if git metadata is unavailable, but canonical promotion must still fail later if the required section is missing.

3. **Populate git history in both generation entry points.**
   - `POST /generate`
   - `scripts/generate_phase6.py`

4. **Update the planner prompt.**
   - Require the planner to render the provided git history under `### Git History`.
   - Make clear that the model must use the supplied history and not invent extra commits.

### Verification

```bash
pytest tests/test_agents/test_planner.py tests/test_api.py -v
```

**Expected:**
- planner tests show supplied git history appears in the draft output contract
- API/script generation paths both provide git history to the planner
- the model is no longer responsible for guessing canonical commit history

**Suggested commit message:** `output-hardening: task 3 — feed real git history into planner`

---

## TASK 4 — Schema / Renderer Support

**Goal:** Encode Alfred canonical current-state/history structure in the data model without breaking permissive parsing of the broader corpus.

### Design constraint

- Alfred canonical handovers benefit from stronger structure.
- The base `HandoverDocument` still needs to parse legacy and Bob-style documents.
- Therefore any new Alfred-specific state/history fields must be optional and additive.

### Implementation

1. **Extend `src/alfred/schemas/handover.py` additively.**
   - Add optional fields for Alfred canonical output, for example:
     - `what_exists_today: list[str] = Field(default_factory=list)`
     - `git_history: list[str] = Field(default_factory=list)`
   - If you want stronger typing, introduce a small `GitCommitRef` model instead of raw strings.

2. **Update `render_markdown()`.**
   - When Alfred canonical fields are present, render:
     - `## WHAT EXISTS TODAY`
     - `### Git History`
   - Preserve existing behavior for documents that do not populate those fields.

3. **Update `from_markdown()`.**
   - Parse `### Git History` when present.
   - Keep parsing permissive; missing sections should not break non-Alfred documents.

4. **Add round-trip tests.**
   - Alfred canonical sample with git history should survive parse → render → parse.
   - Generic sample without those fields should still parse successfully.

### Verification

```bash
pytest tests/test_schemas/test_handover.py -v
```

**Expected:**
- Alfred canonical state/history content round-trips through the schema
- legacy/generic documents continue to parse without new required fields
- the renderer now has first-class support for the section that was previously only implied by house style

**Suggested commit message:** `output-hardening: task 4 — add canonical state and git-history support`

---

## TASK 5 — Promotion Workflow Regression Pass

**Goal:** Prove the end-to-end hardening path catches the exact class of miss that triggered this handover.

### Implementation

1. **Reproduce the original miss as a fixture.**
   - Use a sample Alfred draft that omits `### Git History`.
   - Assert that it cannot pass the canonical promotion validator.

2. **Add a canonical passing sample.**
   - Include all required Alfred sections and a grounded git-history block.

3. **Document the promotion path explicitly.**
   - Draft generation
   - Human review
   - Canonical-output validation
   - Promotion/copy to `docs/ALFRED_HANDOVER_N.md`

4. **Verify Phase 6 draft readiness with the new tooling.**
   - `docs/ALFRED_HANDOVER_5_DRAFT.md` should only be promoted after it passes the new validator and any final editorial adjustments.

### Verification

```bash
python scripts/validate_alfred_handover.py docs/ALFRED_HANDOVER_5_DRAFT.md
pytest tests/test_schemas/test_handover_output_profile.py tests/test_agents/test_planner.py tests/test_api.py -v
```

**Expected:**
- the exact missing-`Git History` failure mode is now covered by regression tests
- promotion is a distinct workflow with a hard gate
- the framework can no longer silently generate a nearly-canonical artifact that slips through without a house-style completeness check

**Suggested commit message:** `output-hardening: task 5 — add promotion regression coverage`

### CHECKPOINT-2 — Canonical Output Hardening Complete

**Question:** Has Alfred stopped relying on reviewer memory for canonical-output completeness?

**Evidence required:**
- passing output from the Alfred promotion validator on a canonical sample
- failing output from the validator on a missing-`Git History` fixture
- passing tests for planner wiring, schema round-trip, and promotion-gate regression coverage

| Observation | Likely call |
|---|---|
| Validator, scaffold wiring, git-history input, and regression tests all pass | APPROVE |
| Validator exists but generation still does not receive git history | PIVOT — finish Task 3 before close |
| Schema changes broke legacy handover parsing | STOP — restore permissive parsing before promotion |
| Promotion can still bypass validation manually or in code | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. **Do NOT fix this only by adding one more sentence to the planner prompt.** That is fragile and will regress.
2. **Do NOT let the model fabricate git history.** Canonical history must come from the repository.
3. **Do NOT make Alfred-specific strictness the default for every parsed handover.** Keep the broader corpus parseable.
4. **Do NOT leave `handover.template_path` unused** if it remains in the config.
5. **Do NOT promote drafts directly to canonical filenames** without running the new validator.
6. **Do NOT conflate “useful draft” with “promotion-safe canonical artifact.”**

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section before closing the work. The next planner or reviewer should be able to cold-start from this artifact alone.

**What worked:**
- *executor to fill*

**What was harder than expected:**
- *executor to fill*

**Decisions made during execution (deviations from this plan):**
- *executor to fill — each deviation must include: what changed, why, who approved*

**Forward plan:**
- *executor to fill*

**next_handover_id:** ALFRED_HANDOVER_5
