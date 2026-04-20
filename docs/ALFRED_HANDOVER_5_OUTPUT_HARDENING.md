# Alfred's Handover Document #5 — Output Hardening Remediation

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_5_OUTPUT_HARDENING
**date:** 2026-04-20
**author:** Codex (repo-grounded remediation plan)
**previous_handover:** ALFRED_HANDOVER_5
**baseline_state:** Phase 6 is closed at commit `6f68a3d` (`phase6: close — post-mortem and checkpoint-6-2 evidence`). `scripts/generate_phase7.py` was added at `d088630` and produced `docs/ALFRED_HANDOVER_6_DRAFT.md`. That draft passes the existing structural validator, but it is not promotion-safe because several `WHAT EXISTS TODAY` claims are factually wrong. Current head `86efac9` only adjusts planner token budget; the factual-grounding gap remains open. Executor cold-starts from this file to remediate the generation pipeline before any Phase 7 planning artifact is promoted.

**Reference Documents:**
- `docs/ALFRED_HANDOVER_5.md` — authoritative Phase 6 handover and close criteria
- `docs/ALFRED_HANDOVER_6_DRAFT.md` — current generated Phase 7 draft containing factual errors
- `scripts/generate_phase7.py` — current local generation path for the Phase 7 draft
- `scripts/validate_alfred_handover.py` — current structural validator (headings only)
- `src/alfred/agents/planner.py` — current planner prompt builder
- `src/alfred/schemas/agent.py` — current planner input/output contract
- `src/alfred/api.py` — real FastAPI entrypoint and current endpoint surface
- `pyproject.toml` — packaging and toolchain truth
- `README.md` — current project status and supported runtime surface
- `.github/workflows/ci.yml` — current Phase 6 CI pipeline

---

## WHAT EXISTS TODAY

### Git History

```
86efac9  fix: increase anthropic max_tokens to 8192 for planner output
d088630  phase7: add generate_phase7.py planner script
b3600e5  fix: sort imports in generate_phase6.py (ruff I001)
6f68a3d  phase6: close — post-mortem and checkpoint-6-2 evidence
b7ede23  phase6: task 5 — docs update
a4e82ed  phase6: task 4 — ci pipeline
08f5f02  phase6: task 3 — coverage gates
b53f2f4  phase6: task 2 — eval harness
67df354  phase6: task 1 — property test suite
90e97b7  first auto-generated handover doc passes!
c7ae43a  output-hardening: task 4 — add canonical state and git-history support
54470c3  output-hardening: task 3 — feed real git history into planner
```

### Current Hardening Already Present

- `configs/alfred_handover_template.md` is already injected into planner generation.
- `PlannerInput.canonical_template` and `PlannerInput.git_history_summary` already exist.
- `scripts/validate_alfred_handover.py` already enforces Alfred structural sections and `### Git History` placement.
- `docs/ALFRED_HANDOVER_6_DRAFT.md` is structurally valid under the current validator.
- Phase 6 quality infrastructure exists in-repo: property tests, eval harness, coverage gates, CI workflow, README updates, and `docs/architecture.md` Section 8.

### Real Current Runtime Shape

- FastAPI lives in `src/alfred/api.py`, not in `src/alfred/api/main.py`.
- Current implemented agent modules are:
  - `src/alfred/agents/planner.py`
  - `src/alfred/agents/story_generator.py`
  - `src/alfred/agents/quality_judge.py`
  - `src/alfred/agents/retro_analyst.py`
  - `src/alfred/agents/compiler.py`
- Current tool modules are:
  - `src/alfred/tools/llm.py`
  - `src/alfred/tools/git_log.py`
  - `src/alfred/tools/github_api.py`
  - `src/alfred/tools/persistence.py`
  - `src/alfred/tools/rag.py`
- Current API endpoints are declared directly in `src/alfred/api.py`:
  - `POST /generate`
  - `POST /evaluate`
  - `POST /approvals/request`
  - `POST /approve`
  - `GET /approvals/pending`
  - `POST /approvals/expire`
  - `POST /retrospective`
  - `POST /compile`
  - `GET /dashboard`
- `pyproject.toml` already contains `[project]` metadata and a `[project.scripts]` entry for `alfred = "alfred.cli:main"`, even though the referenced CLI module does not yet exist.
- The repo uses `pyright`, not `mypy`.

### Concrete Defects In The Current Phase 7 Draft

| ID | Defect in `docs/ALFRED_HANDOVER_6_DRAFT.md` | Why it is wrong | Code remediation required |
|---|---|---|---|
| R1 | References nonexistent `docs/handover_6.md` | That file does not exist; canonical close-out doc is Phase 6 material already in repo | Ground planner with authoritative reference-document paths and validate local path claims |
| R2 | Claims API lives in `src/alfred/api/` with five endpoints | Runtime is a single file `src/alfred/api.py` with nine endpoints | Inject API surface facts into planner input and add factual validation |
| R3 | Claims agent roster is planner/executor/reviewer/summariser | Those modules do not exist; real roles are planner/story_generator/quality_judge/retro_analyst plus compiler | Inject agent-roster facts and validate current-state role claims |
| R4 | Claims `src/alfred/rag/` and `src/alfred/state/` exist | Those packages do not exist; RAG and persistence live under `src/alfred/tools/` | Inject repo topology facts and reject nonexistent module claims |
| R5 | Claims `pyproject.toml` packaging metadata does not yet exist | `pyproject.toml` already has package metadata and a script entrypoint | Add packaging-state facts and require the planner to distinguish existing-but-incomplete from missing |
| R6 | Proposes adding `mypy` to dev extras | Repo contract from Phase 6 explicitly says not to add `mypy` | Add banned-contradiction checks against repo facts and handover hard rules |
| R7 | Proposes wiring probes into `src/alfred/api/main.py` | That import path does not exist in the current repo | Ground future-task paths against actual runtime entrypoints before proposing edits |
| R8 | Draft file path/id/title/date are inconsistent | File is `ALFRED_HANDOVER_6_DRAFT.md`, but body claims `ALFRED_HANDOVER_7` and old date `2025-01-31` | Inject explicit generation metadata and validate document identity after generation |
| R9 | `generate_phase7.py` only injects sprint goal, RAG, scaffold, board, velocity, and git history | That is enough for structural shape, but not enough for factual current-state claims | Extend planner input with authoritative repo-facts and generation metadata |
| R10 | Existing validator only checks headings and subsection placement | Structural validity allowed a factually wrong draft through | Add a second factual-validation pass for Alfred planning drafts |
| R11 | No regression tests cover this failure class | CI currently proves structure and test infra, not current-state truthfulness of generated planning docs | Add fixtures and tests for hallucinated current-state claims |

### Root Cause In The Current Code

- `PlannerInput` has no field for authoritative repo topology, packaging state, endpoint surface, or expected document identity.
- `scripts/generate_phase7.py` does not compute or pass a repo snapshot to the planner.
- `src/alfred/agents/planner.py` tells the model to preserve scaffold headings and supplied git history, but it does not give the model a comparable source of truth for modules, agent roster, API surface, packaging baseline, or current date.
- `scripts/validate_alfred_handover.py` is a structure gate, not a factual correctness gate.
- No tests currently assert that a generated Alfred phase-planning draft must not invent local paths, modules, agent roles, or present-day tooling claims.

### Key Design Decisions Inherited (Do Not Revisit)

1. The codebase is the source of truth for current-state claims, not the model.
2. Structural hardening from the earlier output-hardening phase must be preserved; this phase adds factual hardening, not a replacement for the scaffold/git-history validator.
3. Draft generation and canonical promotion remain separate concerns.
4. Factual validation should target present-tense/current-state claims. Future tasks and out-of-scope sections remain planning prose, not machine-checked implementation.
5. The fix is to supply better truth inputs and add explicit validation, not to hand-edit each future draft after the model hallucinates.

---

## HARD RULES

1. **Do not modify the codebase to match the hallucinated draft.** Fix the generation pipeline, not the repo to fit the bad output.
2. **Do not remove or weaken the existing structural validator.** Factual validation is additive.
3. **Do not add `mypy`.** The repo uses `pyright`; any type-checker scope change is separate human-approved work.
4. **Do not invent package/module paths in prompts, validators, tests, or regenerated drafts.** Local path claims must resolve against the real repo.
5. **Do not move FastAPI into `src/alfred/api/main.py` unless a separate approved refactor explicitly chooses that path.** The current source of truth is `src/alfred/api.py`.
6. **Do not replace the existing `AlfredConfig` model with `BaseSettings`/`pydantic-settings` as part of this hardening phase.** First repair factual grounding; config-system redesign is a separate product decision.
7. **Do not let the model infer handover ids, dates, or previous-handover references from context alone.** Generation metadata must be injected explicitly.
8. **One task = one commit** if this handover is executed as implementation work.

---

## WHAT THIS PHASE PRODUCES

- A repo-truth input layer for Alfred planning generation
- Extended planner input fields carrying authoritative repo facts and generation metadata
- Hardened planner prompt instructions forbidding invented current-state claims
- A factual validator for Alfred planning drafts, separate from the existing structural validator
- Regression tests covering hallucinated local paths, wrong agent rosters, wrong API/module claims, wrong tooling claims, and metadata mismatch
- A regenerated `docs/ALFRED_HANDOVER_6_DRAFT.md` that passes both structural and factual validation

Out of scope:
- Implementing Phase 7 deployment work itself
- Refactoring the runtime into a new module topology
- Changing the Phase 6 CI architecture
- Replacing the existing config system as part of this remediation
- Making the factual validator a general-purpose natural-language truth engine for every paragraph in every handover

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Repo Truth Snapshot | `src/alfred/tools/repo_facts.py` and planner-input extensions | CHECKPOINT-OH-1 |
| 2 | Planner Prompt Hardening | repo-grounded planner prompt and critique-loop propagation | |
| 3 | Factual Validation Gate | `scripts/validate_alfred_planning_facts.py` plus fixtures/tests | CHECKPOINT-OH-2 |
| 4 | Generation Metadata Consistency | corrected `generate_phase7.py` identity/date/path handling | |
| 5 | Regression Coverage | tests covering all R1-R11 failure modes | |
| 6 | Regenerate Phase 7 Draft | corrected `docs/ALFRED_HANDOVER_6_DRAFT.md` and evidence outputs | CHECKPOINT-OH-3 |

---

## TASK 1 — Repo Truth Snapshot

**Goal:** Give the planner authoritative current-state facts about the repo so present-tense claims are grounded in code, not inferred from RAG prose.

### Implementation

1. **Add `src/alfred/tools/repo_facts.py`.**
   - Implement plain functions only.
   - Minimum helpers:
     - `read_agent_modules()`
     - `read_tool_modules()`
     - `read_api_surface()`
     - `read_packaging_state()`
     - `read_reference_documents()`
     - `build_repo_facts_summary()`
   - Output may be `list[str]` or a small dict consumed immediately by generation code; do not introduce a heavyweight new subsystem.

2. **Read the real runtime shape from the repo.**
   - Agent roster comes from `src/alfred/agents/*.py`.
   - Tool modules come from `src/alfred/tools/*.py`.
   - API surface comes from `src/alfred/api.py`.
   - Packaging state comes from `pyproject.toml`.
   - Reference-document truth should prefer existing canonical docs under `docs/`.

3. **Extend `PlannerInput` in `src/alfred/schemas/agent.py`.**
   - Add optional fields for:
     - `repo_facts_summary: list[str]`
     - `generation_date: Optional[str]`
     - `expected_handover_id: Optional[str]`
     - `expected_previous_handover: Optional[str]`
   - Keep all fields optional/additive so existing tests and generation paths remain compatible.

4. **Populate these fields in generation entrypoints.**
   - `scripts/generate_phase7.py`
   - `src/alfred/api.py` `POST /generate`
   - Any helper used by critique-loop regeneration must preserve the same truth inputs across iterations.

### Verification

```bash
pytest tests/test_tools/test_repo_facts.py -v
pytest tests/test_api.py -k generate -v
```

**Expected:**
- Repo-fact helpers return the real current topology.
- Planner entrypoints receive authoritative facts before the first LLM call.
- Existing generation paths still work when optional repo facts are omitted.

**Suggested commit message:** `output-hardening: task 1 — add repo truth snapshot input`

### CHECKPOINT-OH-1 — Truth Inputs Exist

**Question:** Does the generation pipeline now have authoritative repo facts and explicit identity metadata available to the planner?

**Evidence required:**
- Test output for the repo-facts helper
- A captured planner prompt excerpt showing the repo-facts block and injected expected handover id/date

| Observation | Likely call |
|---|---|
| Repo facts and identity metadata are present in planner input | PROCEED |
| Facts are computed ad hoc inside prompt text only | PIVOT — move them into explicit input fields |
| Facts depend on hallucinated RAG content instead of repo inspection | STOP |

---

## TASK 2 — Planner Prompt Hardening

**Goal:** Make the planner treat repo facts as non-negotiable current-state truth and distinguish them from future work.

### Implementation

1. **Update `src/alfred/agents/planner.py` prompt construction.**
   - Add a section such as:
     - `REPOSITORY FACTS (authoritative current state — do not contradict)`
   - Include injected repo facts verbatim.
   - State clearly:
     - current-state claims must match supplied facts
     - future work belongs in task sections only
     - if a file/module is absent from supplied facts, the planner must not claim it exists today

2. **Add explicit prohibitions for known failure modes.**
   - Do not invent local paths.
   - Do not rename current modules in `WHAT EXISTS TODAY`.
   - Do not claim `mypy` is part of the repo unless supplied as fact.
   - Do not claim missing packaging metadata when `pyproject.toml` already contains it.

3. **Inject identity and temporal constraints.**
   - The prompt must tell the model:
     - today's date
     - expected draft id
     - expected previous handover id
   - Require those values to be used verbatim in the metadata block.

4. **Preserve hardening across critique iterations.**
   - `_run_critique_loop(...)` must continue passing `repo_facts_summary`, `generation_date`, and expected ids when the planner revises the draft.

### Verification

```bash
pytest tests/test_agents/test_planner.py -v
pytest tests/test_api.py -k "generate and (canonical or git_history or response_shape)" -v
```

**Expected:**
- Planner prompt tests show repo facts and expected ids/dates are injected.
- Critique-loop regeneration does not drop repo facts on later iterations.
- The prompt explicitly forbids invented current-state topology/tooling claims.

**Suggested commit message:** `output-hardening: task 2 — harden planner against factual hallucinations`

---

## TASK 3 — Factual Validation Gate

**Goal:** Add a machine-checkable factual lint pass for Alfred planning drafts so structurally valid but factually wrong current-state claims cannot be promoted or accepted.

### Implementation

1. **Create `scripts/validate_alfred_planning_facts.py`.**
   - Scope: Alfred planning drafts and canonical Alfred planning handovers only.
   - It complements `scripts/validate_alfred_handover.py`; it does not replace it.

2. **Validate local path claims.**
   - At minimum, check the `Reference Documents` section.
   - Reject local doc/code paths that do not exist, unless the text explicitly says they are planned outputs and places them in future-tense sections such as `WHAT THIS PHASE PRODUCES`.

3. **Validate current runtime claims against repo facts.**
   - Agent roster in `WHAT EXISTS TODAY`
   - FastAPI module path and endpoint surface
   - Top-level package/module claims under `src/alfred/`
   - Packaging/toolchain facts such as `pyright` vs `mypy`

4. **Validate metadata consistency.**
   - File path vs declared handover id
   - Handover number in the title vs expected draft id
   - Injected date vs rendered metadata date when generation metadata is supplied

5. **Emit precise failure output.**
   - Each error should identify:
     - offending claim
     - why it conflicts with repo facts
     - the expected fact or missing path

### Verification

```bash
python scripts/validate_alfred_handover.py docs/ALFRED_HANDOVER_6_DRAFT.md
python scripts/validate_alfred_planning_facts.py docs/ALFRED_HANDOVER_6_DRAFT.md
pytest tests/test_scripts/test_validate_alfred_planning_facts.py -v
```

**Expected:**
- The current bad draft fails the factual validator.
- A corrected draft can pass both structural and factual validation.
- Validator errors are specific enough to drive prompt or code fixes without manual archaeology.

**Suggested commit message:** `output-hardening: task 3 — add factual validator for planning drafts`

### CHECKPOINT-OH-2 — Factual Gate Works

**Question:** Can the system now reject the exact failure class that let the current Phase 7 draft through?

**Evidence required:**
- Factual-validator output against the current broken draft
- Passing output against a corrected or fixture-backed good sample
- `pytest` output for validator tests

| Observation | Likely call |
|---|---|
| Broken draft fails for wrong paths/topology/tooling claims; corrected sample passes | PROCEED |
| Validator only checks path existence and misses wrong agent/API/tooling claims | PIVOT — add repo-facts comparison |
| Validator is so broad that it flags future planned outputs as errors | PIVOT — scope checks to current-state sections only |
| Validator cannot detect id/title/date mismatch | PIVOT — add metadata checks before continuing |

---

## TASK 4 — Generation Metadata Consistency

**Goal:** Make `scripts/generate_phase7.py` supply stable identity and temporal metadata so the planner does not guess the handover number, previous handover, or date.

### Implementation

1. **Refactor `scripts/generate_phase7.py` constants.**
   - Introduce explicit constants for:
     - draft path
     - expected handover id
     - display title
     - previous handover id
     - current date

2. **Pass those values into `PlannerInput`.**
   - Use the new metadata fields from Task 1.
   - Ensure the same values are preserved when `_run_critique_loop(...)` performs revisions.

3. **Keep file naming and document metadata aligned.**
   - `docs/ALFRED_HANDOVER_6_DRAFT.md` should produce a draft whose metadata is for handover 6, not 7.
   - The metadata date must be injected from runtime, not left to model recall.

4. **Add a small helper test surface if needed.**
   - If the script is hard to test directly, extract pure helper functions and test those instead of shelling the whole script.

### Verification

```bash
pytest tests/test_scripts/test_generate_phase7.py -v
python scripts/generate_phase7.py
```

**Expected:**
- Script-level tests prove identity/date constants are consistent.
- A fresh generation run does not emit the wrong handover number or stale date.
- Critique-loop rewrites preserve the injected metadata.

**Suggested commit message:** `output-hardening: task 4 — ground phase7 generator metadata`

---

## TASK 5 — Regression Coverage

**Goal:** Add regression tests for every defect class in R1-R11 so the same draft-factuality failure does not silently recur.

### Implementation

1. **Add tool/helper tests.**
   - `tests/test_tools/test_repo_facts.py`
   - Cover agent roster, tool modules, API surface, and packaging-state extraction.

2. **Add planner prompt tests.**
   - Extend `tests/test_agents/test_planner.py` to assert that:
     - repo facts are injected
     - expected id/date are injected
     - prompt contains the non-hallucination instructions

3. **Add factual-validator tests.**
   - `tests/test_scripts/test_validate_alfred_planning_facts.py`
   - Fixtures must cover:
     - nonexistent local document path
     - nonexistent module path
     - wrong agent roster
     - wrong API entrypoint / endpoint count
     - false `mypy` claim
     - id/title/date mismatch

4. **Add generator metadata tests.**
   - `tests/test_scripts/test_generate_phase7.py`
   - Assert the script constants and prompt inputs are internally consistent.

5. **Keep CI-friendly boundaries.**
   - No live API calls.
   - No dependence on GitHub network state.
   - Use fixtures or monkeypatching where repo inspection needs a controlled surface.

### Verification

```bash
pytest tests/test_tools/test_repo_facts.py -v
pytest tests/test_agents/test_planner.py -v
pytest tests/test_scripts/test_validate_alfred_planning_facts.py -v
pytest tests/test_scripts/test_generate_phase7.py -v
```

**Expected:**
- Each R1-R11 failure mode has at least one automated test.
- Tests fail against the pre-fix behavior and pass against the hardened implementation.
- The regression suite fits inside the existing Phase 6 CI envelope.

**Suggested commit message:** `output-hardening: task 5 — add factual grounding regression tests`

---

## TASK 6 — Regenerate Phase 7 Draft

**Goal:** Re-run the generator after Tasks 1-5 and produce a corrected `docs/ALFRED_HANDOVER_6_DRAFT.md` that is both structurally and factually grounded.

### Implementation

1. **Run the hardened generator.**
   - Rebuild any local RAG index if needed.
   - Re-run `scripts/generate_phase7.py`.

2. **Run both validators.**
   - Structural validator:
     - `scripts/validate_alfred_handover.py`
   - Factual validator:
     - `scripts/validate_alfred_planning_facts.py`

3. **Manually scrub only if necessary.**
   - Any manual edits after generation must be treated as evidence that the pipeline is still not sufficiently hardened.
   - If manual edits are required, record exactly why in the post-mortem and do not call the pipeline fixed.

4. **Compare against the current bad draft.**
   - Confirm correction of:
     - wrong reference document path
     - wrong runtime module topology
     - wrong agent roster
     - wrong API claims
     - wrong packaging/tooling claims
     - wrong handover id/date metadata

### Verification

```bash
python scripts/generate_phase7.py
python scripts/validate_alfred_handover.py docs/ALFRED_HANDOVER_6_DRAFT.md
python scripts/validate_alfred_planning_facts.py docs/ALFRED_HANDOVER_6_DRAFT.md
git diff -- docs/ALFRED_HANDOVER_6_DRAFT.md
```

**Expected:**
- Regenerated draft passes both validators.
- The corrected draft describes the repo that actually exists today.
- The diff shows factual corrections, not a drift back to generic prose.

**Suggested commit message:** `output-hardening: task 6 — regenerate factual phase7 draft`

### CHECKPOINT-OH-3 — Draft Is Promotion-Safe

**Question:** Is the regenerated Phase 7 draft now both structurally valid and factually grounded enough to proceed to human review?

**Evidence required:**
- Generator output summary
- Structural-validator pass output
- Factual-validator pass output
- Short human comparison note covering the six corrected defect classes in Task 6

| Observation | Likely call |
|---|---|
| Draft passes both validators and current-state claims now match repo facts | APPROVE for human review |
| Draft passes structure but still fails factual validation | BLOCK |
| Draft passes validators only after manual edits | PIVOT — pipeline still incomplete; document the remaining gap |
| Draft still claims nonexistent modules/docs/tooling | STOP |

---

## WHAT NOT TO DO

1. **Do not promote the current `docs/ALFRED_HANDOVER_6_DRAFT.md` as-is.**
2. **Do not treat structural validity as factual validity.**
3. **Do not patch the next draft by hand and call the pipeline fixed.**
4. **Do not add `mypy`, `src/alfred/api/main.py`, `src/alfred/rag/`, or `src/alfred/state/` just because the bad draft mentioned them.**
5. **Do not let repo-facts gathering depend on RAG retrieval.** Repo facts must come from direct inspection of the workspace.
6. **Do not loosen the existing Phase 6 CI gates while implementing this remediation.**
7. **Do not broaden factual validation into speculative future-task policing.** Validate current-state claims only.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, replace this placeholder with actual execution evidence before closing the remediation. The next planning cycle should cold-start from the corrected Phase 7 draft, not from the current broken one.

**What worked:**
- TBD

**What was harder than expected:**
- TBD

**Decisions made during execution (deviations from this plan):**
- TBD

**Evidence collected:**
- TBD

**Remaining risks:**
- TBD

**next_handover_id:** ALFRED_HANDOVER_6
