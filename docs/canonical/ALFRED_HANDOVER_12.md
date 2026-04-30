# Alfred's Handover Document #12 — Phase 5: Rehearsal, Operator Runbook, And Demo-Grade Instrumentation

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_12
**date:** 2026-04-30
**author:** Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_11
**baseline_state:** Phase 4’s approval-gated GitHub Project V2 writes from persisted story proposals are implemented; Phase 5 now packages the slice into a repeatable, demo-grade operator flow with clear evidence surfaces and a fallback plan.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_11.md` — confirms Phase 4 behavior is already ratified; Phase 5 must treat it as the product to rehearse (not redesign).
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — Phase 5 scope/goal; hard rules; demo-done and failure definitions.
- `docs/active/DEMO_PROJECT_LAYOUT.md` — frozen demo-workspace shape and doc-path contract (external demo workspace paths).
- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — known-good charter payload that must be used verbatim for the demo.
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — locked kickoff handover shape, `TASK-SEED-BOARD-001` contract, and verbatim approval-gate wording.
- `docs/protocol/OPERATOR_RUNBOOK.md` — repo’s operator/runbook conventions; Phase 5 output should align with protocol expectations.

This handover exists because the demo slice is now functionally complete through Phase 4, but it is not yet “demo-grade.” Phase 5 is explicitly about dependability and operator clarity: a step-by-step script, frozen demo inputs, and evidence surfaces that let an operator explain “document as protocol” and “checkpoint-gated execution” without improvisation. No new product scope is intended; we are packaging and rehearsing what already exists.

---

## WHAT EXISTS TODAY

### Git History

```
5fd60a7  installing Matt Pocock skills
811ff13  phase4: task 5 — fill in post-mortem; coverage audit complete
fe59615  phase4: task 4 — harness arc prints refusal, approval, write receipts
1bfb6c0  phase4: task 3 — orchestrated, approval-gated GitHub board write
f2abe77  phase4: task 2 — write-receipt persistence + atomic write-and-mark
9aaba1f  phase4: task 1 — define approval→write contract and lifecycle invariants
42d2953  generator: advance to ALFRED_HANDOVER_11 and promote phase 4 canonical
30a9072  llm: fail fast on empty model config
7216bb4  config: switch default LLM provider to OpenAI
333cbe0  demo: read approval gate from persisted proposals
1686aef  planner: harden structured-output generation
e0c86d9  orchestrator: task 3 — persist story outputs and attach to TaskResult
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Runtime & Repo Inventory (relevant to Phase 5)

- `src/alfred/api.py` — **exists today**; FastAPI app with endpoints including approvals, compile, and dashboard.
- `src/alfred/orchestrator.py` — **exists today**; main execution flow is orchestrator-mediated.
- `src/alfred/cli.py` — **exists today**; CLI entry point is wired (note: `pyproject.toml` declares `alfred.cli:main`).
- `src/alfred/agents/story_generator.py` — **exists today**; produces structured 6–8 story proposals as required by `TASK-SEED-BOARD-001`.
- `src/alfred/tools/persistence.py` — **exists today**; SQLite persistence supporting proposals + approvals + write receipts (Phase 4).
- `src/alfred/tools/github_api.py` — **exists today**; GitHub Project V2 write adapter used only after approval.
- `docs/DOCS_POLICY.md` and `docs/DOCS_MANIFEST.yaml` — **exists today**; docs governance is in place for adding Phase 5 operator artifacts.

**Partial state (explicit):**
- No new Phase 5-specific demo script document is listed in repo facts; any such document is **to be created in this phase** under `docs/` (per doc placement rule).

### Key Design Decisions Inherited (Do Not Revisit)

1. **Single scenario is locked:** Customer Onboarding Portal.
2. **Demo workspace shape is frozen** (external workspace): `<demo-project-root>/README.md`, `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace], `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace] (empty at kickoff; no `.gitkeep`).
3. **Docs are the protocol source of truth; GitHub is a downstream projection.**
4. **Approval gate is real and visible**; board writes are forbidden before approval is recorded.
5. **No proposal regeneration across the approval boundary:** the reviewed proposals are the ones written.
6. **`TASK-SEED-BOARD-001` hard-bounds output count:** must be 6–8 proposals or the run fails and must be re-run before approval is requested.

---

## HARD RULES

1. **Do not bypass `orchestrate(...)`.** No “demo-only” path that skips orchestrator-mediated execution.
2. **Do not let story creation write to GitHub without a visible approval gate.** Approval must be obtained and recorded before any GitHub write call.
3. **Do not treat the GitHub Project as the source of truth.** The project docs + approved handover remain primary.
4. **Do not hide critical execution state in process memory** if it needs to survive a pause/resume boundary (approval checkpoints must be resumable).
5. **Do not broaden scope** into retrospectives, advanced dashboards, multi-sprint planning, story editing, or general workflow engines.
6. **Do not change the frozen demo inputs** (scenario, charter text, or demo-workspace shape) for convenience.

---

## WHAT THIS PHASE PRODUCES

- A repeatable **operator demo script** that starts from: fresh demo workspace + blank GitHub Project → generates kickoff handover → persists it → compiles it → runs `TASK-SEED-BOARD-001` → requests approval → writes 6–8 draft items to GitHub Project → shows receipts/evidence.
- A **frozen “known-good” demo configuration record** (human-readable) that names:
  - which charter payload is used (verbatim from `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` via the external workspace copy rule),
  - the expected external demo workspace layout,
  - the target GitHub Project identity that must start blank.
- A minimal **instrumentation/evidence checklist** the operator can point to during the demo (logs, API responses, persisted artifacts) that supports the auditability story without adding new product behavior.
- A narrow **fallback plan** for predictable failure modes (LLM/provider hiccups; GitHub rate limits; partial-run resume), that preserves “governed coordination” rather than faking writes.

Out of scope:
- Any redesign of approval/write mechanics, persistence schema, agent behavior, or proposal content model.
- Any new scenario, new backlog management features, or multi-sprint planning.
- Any new “auto-retry until it works” behavior that could hide the checkpoint-gated story.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Author the Phase 5 demo script (step-by-step operator flow) | New doc: `docs/active/PHASE_5_DEMO_SCRIPT.md` (**to be created in this phase**, per doc placement rule) | CHECKPOINT-1 |
| 2 | Define frozen demo inputs & preflight checklist | Section in `docs/active/PHASE_5_DEMO_SCRIPT.md` + optional helper script `scripts/demo_preflight.py` (**to be created in this phase**, per script placement rule) | CHECKPOINT-2 |
| 3 | Evidence surfaces & instrumentation checklist (no new product scope) | Add “evidence capture” steps + expected artifacts/outputs; optional small logging tweaks if strictly necessary | CHECKPOINT-3 |
| 4 | Rehearsal acceptance standard + fallback plan | “Two clean runs” rubric + deterministic fallback branches (no fake writes) | CHECKPOINT-4 |

---

## TASK 1 — Author the Phase 5 Demo Script (Operator Flow)

**Goal:** Produce a single, readable, deterministic operator script that can be followed live without improvisation.

### Implementation

1. **Create the demo script document** — create `docs/active/PHASE_5_DEMO_SCRIPT.md` (**to be created in this phase**; per doc placement rule, docs belong under `docs/` using `*.md`).
2. **Write the operator flow as numbered steps** — include:
   - starting conditions: blank GitHub Project (0 items), fresh external demo workspace,
   - commands/UI actions the operator performs,
   - the *observable evidence* after each step (files created, API responses, log lines to look for).
3. **Embed the locked approval gate wording verbatim** (from `docs/active/KICKOFF_HANDOVER_OUTLINE.md`) in the script where the operator requests approval:

   > Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

4. **Explicitly call out the two approval gates** (conceptually):
   - approval to persist/accept the kickoff handover artifact (if your operator flow includes an explicit approval endpoint for it),
   - approval to write the 6–8 proposals to GitHub Project.

   If only one approval gate is implemented in the runtime, the script must not invent the second; it must reflect the real behavior and clearly label what is and is not gated today.

### Verification

```bash
# Documentation governance checks (exact command may vary by repo tooling)
# Run the repo's doc manifest validation if present in scripts/
ls docs/active/PHASE_5_DEMO_SCRIPT.md
```

**Expected:**
- `docs/active/PHASE_5_DEMO_SCRIPT.md` exists and is readable end-to-end.
- The script references external demo-workspace paths with explicit tags like:
  - `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]
  - `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace]
- The approval gate prompt appears verbatim.

**Suggested commit message:** `docs: task 1 — add phase 5 operator demo script draft`

### CHECKPOINT-1 — Demo Script Completeness Gate

**Question:** Is the demo script specific enough that a second operator can follow it without asking clarifying questions?

**Evidence required:**
- A link to the PR/commit OR a pasted excerpt containing:
  - the step list (at least 10 steps, if that’s what’s required to cover the full arc),
  - the verbatim approval-gate block,
  - the “observable evidence” bullets for at least 3 key moments (pre-approval, post-approval, post-write).

| Observation | Likely call |
|---|---|
| Every step has an action + expected evidence; no undefined “magic happens” transitions | PROCEED |
| Some steps are hand-wavy (missing commands, missing where to look for evidence) but structure is right | PIVOT (tighten wording; add evidence bullets; re-check) |
| Script depends on unimplemented behavior (invented endpoints, fake board writes, hidden state) | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — Frozen Demo Inputs & Preflight Checklist

**Goal:** Ensure the demo starts from known-good inputs and preconditions so rehearsals are repeatable.

### Implementation

1. **Add a “Frozen Inputs” section** to `docs/active/PHASE_5_DEMO_SCRIPT.md` listing:
   - the scenario: Customer Onboarding Portal,
   - charter source: `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` (must be copied verbatim into external workspace `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]),
   - the required external workspace shape per `docs/active/DEMO_PROJECT_LAYOUT.md`.
2. **Add a “Preflight Checklist” section** that the operator checks before starting:
   - GitHub Project is empty (0 items).
   - API/service can start and `/healthz` and `/readyz` respond.
   - LLM provider config is set (and not empty).
3. **Optional helper script** — create `scripts/demo_preflight.py` (**to be created in this phase**; per script placement rule, scripts belong under `scripts/` using `*.py`) that prints:
   - environment variables present (without secrets),
   - connectivity checks to the running service,
   - a reminder to confirm the board is blank via UI.

### Verification

```bash
ls docs/active/PHASE_5_DEMO_SCRIPT.md
ls scripts/demo_preflight.py
```

**Expected:**
- The doc contains a concrete checklist with yes/no items.
- If `scripts/demo_preflight.py` is created, it is runnable and does not require privileged secrets beyond what the demo already needs.

**Suggested commit message:** `demo: task 2 — add preflight checklist and frozen inputs`

### CHECKPOINT-2 — Rehearsal Preconditions Gate

**Question:** Are the demo inputs and starting conditions frozen tightly enough to make two clean rehearsals realistic?

**Evidence required:**
- Pasted “Preflight Checklist” section.
- The exact identifier (URL/name) of the target GitHub Project to be used for rehearsal (human-supplied).

| Observation | Likely call |
|---|---|
| Checklist is actionable and includes both service readiness + blank-board confirmation | PROCEED |
| Checklist exists but misses one of: blank board, charter source, readiness endpoints | PIVOT |
| Inputs are ambiguous (multiple boards, multiple charters, or “whatever is available”) | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 3 — Evidence Surfaces & Instrumentation Checklist (No New Product Scope)

**Goal:** Make the auditability story easy to show by pointing to artifacts/logs that already exist (or minimal logging that does not change behavior).

### Implementation

1. **In the demo script, add an “Evidence to Point To” subsection** at each critical stage:
   - Before any approval: show that proposals exist but board is unchanged.
   - After approval request: show pending approval record.
   - After approval: show write receipts and GitHub items created.
2. **Define the minimum “evidence bundle”** the operator can capture during rehearsal:
   - persisted kickoff handover artifact in external workspace `docs/canonical/ALFRED_HANDOVER_1.md` [future-doc: path inside the external demo workspace],
   - the compiled handover confirmation (whatever the runtime exposes),
   - an approvals listing (e.g., via API endpoint),
   - a record of write receipts (via logs or persistence query surface),
   - a screenshot of the GitHub Project showing 6–8 items post-approval.
3. **Only if strictly necessary, add small logging improvements** in existing modules (e.g., `src/alfred/tools/logging.py` **exists today**) to ensure the operator can find the specific lines quickly. Do not add new endpoints or change flow.

### Verification

```bash
# No single mandated command here; verification is that the script references concrete evidence surfaces
rg -n "Evidence" docs/active/PHASE_5_DEMO_SCRIPT.md
```

**Expected:**
- Each stage has a “what to show” item.
- No evidence step depends on reading GitHub as the primary record; GitHub is shown as projection.

**Suggested commit message:** `docs: task 3 — add evidence checklist for demo auditability`

### CHECKPOINT-3 — Evidence Integrity Gate

**Question:** Does the evidence plan support the “document as protocol” story without making GitHub the primary record?

**Evidence required:**
- Pasted excerpt(s) of the evidence checklist sections covering: pre-approval, approval pending, post-write.

| Observation | Likely call |
|---|---|
| Evidence prioritizes docs + persisted records, with GitHub as projection | PROCEED |
| Evidence is mostly logs/screenshots and under-specifies the persisted handover artifact | PIVOT |
| Evidence relies on “read GitHub to know what was proposed” | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 4 — Rehearsal Acceptance Standard + Fallback Plan

**Goal:** Define what “demo-grade” means and how to handle predictable failures without faking the governed workflow.

### Implementation

1. **Add a “Rehearsal Acceptance Standard” section** to `docs/active/PHASE_5_DEMO_SCRIPT.md`:
   - two clean end-to-end runs,
   - stable timing expectations (human-supplied thresholds),
   - zero architecture caveat improvisation: every caveat must be in-script.
2. **Add a “Fallback Plan” section** with narrow, honest branches:
   - If LLM provider fails: retry once; if still failing, stop and explain that the run cannot proceed without generating proposals (no manual substitution).
   - If GitHub write fails after approval: do not regenerate; preserve receipts/error logs; demonstrate that approvals were recorded and that write is blocked/failed honestly.
   - If the board is not blank at start: stop; reset board; restart.
3. **Add a “Demo narrator notes” section**: one paragraph explaining the arc in plain language, emphasizing checkpoints and approvals.

### Verification

```bash
rg -n "Rehearsal Acceptance" docs/active/PHASE_5_DEMO_SCRIPT.md
rg -n "Fallback" docs/active/PHASE_5_DEMO_SCRIPT.md
```

**Expected:**
- Acceptance standard is measurable.
- Fallback plan never instructs faked outputs or manual board edits that would break the governance story.

**Suggested commit message:** `docs: task 4 — add rehearsal rubric and fallback plan`

### CHECKPOINT-4 — Demo-Grade Readiness Gate

**Question:** Is the Phase 5 package sufficient to run the demo twice cleanly and explain failures honestly?

**Evidence required:**
- The acceptance rubric section.
- The fallback plan section.
- A human-confirmed statement of which exact GitHub Project is used for rehearsal.

| Observation | Likely call |
|---|---|
| Rubric is measurable; fallback is honest; dependencies are named | PROCEED |
| Rubric exists but is subjective; fallback lacks stop conditions | PIVOT |
| Plan includes “fake it” instructions or requires hidden manual state edits | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do not add new runtime features (new endpoints, new schemas, new workflow engine concepts) under the banner of “instrumentation.”
2. Do not change the frozen demo-workspace layout (including adding `.gitkeep` to the external demo workspace contract).
3. Do not “fix” proposal quality by editing proposals after generation; proposal content is part of the governed artifact boundary.
4. Do not turn the GitHub board into the place we verify what happened; treat it as a projection shown *after* approvals.
5. Do not widen the scenario scope beyond Customer Onboarding Portal.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- The four-task arc landed as planned: `docs/active/PHASE_5_DEMO_SCRIPT.md` covers the operator flow, frozen inputs/preflight, evidence surfaces, and rehearsal-acceptance + fallback sections, with the verbatim approval-gate wording embedded.
- A plain-English companion (`docs/active/PHASE_5_DEMO_SCRIPT_PRODUCT_OWNER.md`, registered in `docs/DOCS_MANIFEST.yaml`) was added so a non-technical operator can narrate the run alongside the technical script — this fell within Phase 5's "operator clarity" goal without expanding product scope.
- Two operator scripts were added under `scripts/` to keep rehearsal honest when reality deviates: `scripts/resume_phase4_write.py` retries the approved board-write step after a config fix without regenerating proposals, and `scripts/backfill_phase4_bodies.py` patches existing draft-issue bodies on a board that was written before body rendering existed. Neither bypasses `orchestrate(...)` or the approval gate.
- Body rendering shipped as a small feature delta (`src/alfred/tools/story_markdown.py` + `render_story_proposal_body` wired through the orchestrator's board-writer). Draft cards now open with description, acceptance criteria, and story points — which directly improves the "evidence to point to" moment of the demo.
- The GitHub adapter (`src/alfred/tools/github_api.py`) was extended to resolve ProjectV2 boards under either an `organization(login:)` or `user(login:)` root, and exposes `update_story_body` for retroactive patches. Tests cover both owner kinds and the new mutation path.

**What was harder than expected:**
- The original plan framed Phase 5 as pure packaging, but rehearsal surfaced two real product gaps that had to be addressed to keep the demo honest: (1) draft cards on the live board were title-only, which weakened the "evidence" story in Task 3; (2) the target rehearsal board lives under a personal user login, not an organization, and the adapter's GraphQL only queried `organization(login:)`. Both were fixed as narrow, tested changes rather than worked around in the script.
- Deciding what counts as "minimal logging tweaks" vs. new product scope (per Hard Rule 1 / Task 3) required care. We held the line: no new endpoints, no new schemas, only the body-rendering helper and the two retry/backfill scripts.

**Decisions made during execution (deviations from this plan):**
- Added `src/alfred/tools/story_markdown.py` and threaded `render_story_proposal_body(...)` into `orchestrator._run_board_writer`. *Why:* Task 3 evidence requires that what an operator opens in GitHub matches what was approved in the persisted proposal; title-only cards forced narration to fill the gap. *Approved by:* Donal, in the rehearsal turn that preceded these commits.
- Extended `github_api.py` to dual-resolve owners as organization-or-user and added `update_story_body(...)`. *Why:* the rehearsal board is `donalmadden/<n>`, a user-owned ProjectV2; the original adapter raised "Could not resolve to an Organization" and blocked the demo. *Approved by:* Donal, same rehearsal turn.
- Added `scripts/resume_phase4_write.py` and `scripts/backfill_phase4_bodies.py` under `scripts/` per the placement rule. *Why:* Phase 5's fallback plan calls for honest recovery without regenerating proposals or hand-editing the board; these scripts make those branches executable. *Approved by:* Donal, same rehearsal turn.
- Added `docs/active/PHASE_5_DEMO_SCRIPT_PRODUCT_OWNER.md` (registered as `kind: active_brief`, `lifecycle_status: active` in `DOCS_MANIFEST.yaml`). *Why:* the rehearsal exposed that the technical script alone is hard to narrate live; a product-owner companion preserves the "explain checkpoints and approvals in plain language" intent of Task 4's narrator notes without bloating the technical doc. *Approved by:* Donal.

**Forward plan:**
- Run two clean rehearsals against the user-owned target board per the Task 4 acceptance rubric and capture the evidence bundle (persisted handover, approvals listing, write receipts, post-write board screenshot).
- If a rehearsal fails partway, exercise the fallback scripts (`resume_phase4_write.py`, `backfill_phase4_bodies.py`) to confirm the recovery branches in `PHASE_5_DEMO_SCRIPT.md` work as documented.
- Do not broaden scope in Handover 13. Likely next-phase candidates are evaluations/tests (Phase 6) and developer-experience hardening (Phase 7) — not new product features layered onto the kickoff slice.
- Watch for one cleanup item: the operator scripts currently live under `scripts/` as one-shot helpers; if they become reused beyond the kickoff demo, consider promoting their core logic into `src/alfred/` modules with proper test coverage.

**next_handover_id:** ALFRED_HANDOVER_13