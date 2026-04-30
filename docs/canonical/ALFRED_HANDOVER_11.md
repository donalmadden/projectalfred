# Alfred's Handover Document #11 — Phase 4: Approval-Gated GitHub Project V2 Board Writes (from Persisted Story Proposals)

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_11
**date:** 2026-04-30
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_10
**baseline_state:** Phase 3 is complete and ratified: story proposals are persisted and the approval-gate review surface reads from persistence without regenerating proposals; Phase 4 must add the approval-gated GitHub Project V2 write path.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_10.md` — immediate predecessor; Phase 3 durable story proposal persistence + “review reads from persistence” constraints that Phase 4 must not break.
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — Phase 4 scope, hard rules, demo-done/failure conditions, and the “minimal viable slice” chain we must advance.
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — locked task id `TASK-SEED-BOARD-001`, 6–8 proposal constraint, and verbatim approval gate wording that must remain visible and truthful.
- `docs/active/DEMO_PROJECT_LAYOUT.md` — frozen demo-workspace docs surface shape; reaffirms “docs are the protocol surface” and that GitHub is downstream.
- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — frozen scenario input; ensures the generated proposals remain anchored in the charter (even though Phase 4 should not regenerate/mutate them).

This handover exists to close Phase 4 of the blank-project kickoff demo plan: turn human approval into a real gating mechanism for writing 6–8 previously persisted `StoryProposal` items onto an initially blank GitHub Project V2 board.

The critical constraint is “document as protocol”: the demo workspace `docs/` surface (including the approved/persisted kickoff handover markdown) remains the source of truth; GitHub is a downstream projection. Phase 3 already ensured proposals survive the pause/resume boundary as runtime execution state (SQLite). Phase 4 must:

1) link approvals to a specific handover/task/action + proposal batch,
2) ensure unapproved runs cannot call the GitHub write path,
3) write the reviewed persisted proposals to GitHub Project V2 as visible draft items,
4) transition proposal lifecycle state from pending → approved → written without regenerating or mutating reviewed story content.

---

## WHAT EXISTS TODAY

### Git History

```
30a9072  llm: fail fast on empty model config
7216bb4  config: switch default LLM provider to OpenAI
333cbe0  demo: read approval gate from persisted proposals
1686aef  planner: harden structured-output generation
e0c86d9  orchestrator: task 3 — persist story outputs and attach to TaskResult
2959a37  persistence: task 2 — store and query story proposals
9edb03a  schemas: task 1 — add story proposal persistence models
2d749c5  generator: prime for ALFRED_HANDOVER_10 (Phase 3) + open workflow discussion
cb59100  docs: promote ALFRED_HANDOVER_9 canonical handover
eb2b476  scripts: task 2 — demo execution harness (orchestrate + gate)
7fde9d9  scripts: task 1 — demo workspace initialiser
bfb3d2c  first fixed handover
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Runtime & Repo Inventory (relevant to Phase 4)

- `src/alfred/api.py` — **exists today**; FastAPI app with approvals endpoints and other runtime endpoints.
- `src/alfred/orchestrator.py` — **exists today**; orchestrated execution must remain the main flow (Phase 4 must not bypass it).
- `src/alfred/cli.py` — **exists today**; CLI entry point declared in `pyproject.toml` (`alfred.cli:main`).
- `src/alfred/tools/github_api.py` — **exists today**; GitHub adapter surface (Phase 4 should extend/consume rather than bypass).
- `src/alfred/tools/persistence.py` — **exists today**; holds SQLite persistence used in Phase 3 for story proposals; Phase 4 should extend to support lifecycle transitions and “write receipts” (or equivalent).
- `src/alfred/schemas/story_proposal.py` — **exists today**; Phase 3 schema for persisted proposals.

Important interpretation (Phase 4): persisted story proposals are runtime execution state that supports the pause/resume and approval gating. They are not a replacement for the demo workspace handover markdown, which remains the protocol artifact.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Single scenario is locked:** Customer Onboarding Portal.
2. **Demo workspace shape is frozen:** `<demo-project-root>/README.md`, `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace], `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace] (empty at kickoff; no `.gitkeep`).
3. **Docs are the protocol source of truth:** GitHub is a downstream projection.
4. **`TASK-SEED-BOARD-001` output count is hard-bounded:** 6–8 proposals; fewer/more is failure and must be re-run before approval is requested.
5. **Approval gate wording is verbatim-locked** from `docs/active/KICKOFF_HANDOVER_OUTLINE.md`.
6. **No proposal regeneration across the approval boundary:** the content reviewed at the gate must be the same persisted records that get written to GitHub.

---

## HARD RULES

1. **Do not bypass `orchestrate(...)`.** The main execution flow must remain orchestrator-mediated.
2. **Do not write to GitHub Project V2 without a genuine approval gate.** Approval must be recorded and checked before any `github_api` write call.
3. **Do not treat GitHub as source of truth.** The demo project docs + approved handover remain primary; GitHub is a projection of approved runtime/doc state.
4. **Do not regenerate or mutate story proposals after approval is requested.** The exact persisted rows must be the write source.
5. **Do not broaden scope** into Phase 5 (rehearsal/runbook), retrospectives, multi-sprint planning, story editing, or generalized workflow engines.

---

## WHAT THIS PHASE PRODUCES

- Approval → write integration that creates draft items in GitHub Project V2 **only after** an approval record is present and validated.
- A persistence-level lifecycle for proposals that supports: `pending` → `approved` → `written` (or equivalent) without changing story content.
- A “write receipt” record (minimal) that ties each created GitHub item back to the persisted proposal row (so we can prove “no regeneration” and support idempotency).
- Updates to the demo harness so the Phase 4 arc is observable: blank board before approval; no writes without approval; titles match after write.

Out of scope:
- Phase 5 demo script/runbook and rehearsal instrumentation.
- Any story editing UI or mutation flows.
- Enriching GitHub fields beyond creating visible draft items.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Define Phase 4 approval→write contract (linkage + state machine) | Concrete schema/state fields + invariants documented in-code and in tests | CHECKPOINT-1 |
| 2 | Extend persistence for proposal lifecycle + write receipts | SQLite DDL + CRUD for (a) proposal status transitions (b) write receipt mapping | |
| 3 | Implement approval-gated GitHub Project V2 write path | Orchestrated step that refuses to write unless approved; writes 6–8 draft items sourced from persistence | |
| 4 | Update API/harness surfaces to demonstrate the gate and evidence | API route(s) and/or `scripts/run_kickoff_demo.py` show: pending → approved → written; print evidence | |
| 5 | Tests: “no approval, no write”; “approved, writes exactly persisted proposals”; idempotency | `tests/` coverage for persistence + GitHub adapter call gating | |

---

## TASK 1 — Define Phase 4 Approval→Write Contract (Linkage + Lifecycle)

**Goal:** Specify the minimal, testable contract that ties (handover_id, task_id, action) + persisted proposal batch to an approval record, and gates a GitHub write step that consumes exactly those persisted proposals.

### Implementation

1. **Confirm the existing approval model surface** — inspect `src/alfred/api.py` (**exists today**) approvals endpoints to identify:
   - what an “approval request” record contains today (ids, status, timestamps)
   - what identifier is returned to the caller
   - how “pending approvals” are listed

2. **Define the Phase 4 linkage keys (no invention of a new workflow engine)** — choose a minimal linking strategy that can be validated deterministically:
   - required linkage: `handover_id`, `task_id` (must include `TASK-SEED-BOARD-001`), and an explicit `action` value (e.g., `WRITE_GITHUB_PROJECT_V2`).
   - required proposal batch reference: either (a) query proposals by `handover_id` + `task_id`, or (b) add a persisted `proposal_batch_id` if Phase 3 already persisted one.

   Constraint: do not introduce a generalized event log; keep it narrow and specific to this demo slice.

3. **Define proposal lifecycle states and invariants** — using the Phase 3 persisted proposals as the source:
   - `pending` (generated and stored; not yet approved)
   - `approved` (approval recorded; still not written)
   - `written` (GitHub write completed and receipt recorded)

   Invariants to enforce in code:
   - Cannot transition to `approved` unless there is a matching approval record.
   - Cannot transition to `written` unless the write step has succeeded.
   - Story content fields (`title`, `description`, `acceptance_criteria`, `story_points`) must not be edited as part of Phase 4.

4. **Define idempotency expectations (minimal but real)**
   - If the write step is re-run after a partial failure, the system must not create duplicates for proposals already marked `written`.
   - This requires either (a) checking a receipt table before creating a GitHub item or (b) checking proposal status `written` and skipping.

5. **Document evidence requirements inside the harness**
   - “Blank board before approval” must be observable.
   - “No write without approval” must be observable (explicit refusal / error and no GitHub calls).
   - “Approved proposals titles match created GitHub items” must be observable (print mapping proposal_id → github_item_id/title).

### Verification

```bash
# run tests
pytest -q

# typecheck (repo uses pyright)
pyright
```

**Expected:**
- Tests establish the contract for lifecycle transitions and gating preconditions.
- A clear linkage key set is agreed (handover/task/action) with deterministic behavior.

**Suggested commit message:** `phase4: task 1 — define approval→write contract and lifecycle invariants`

### CHECKPOINT-1 — Contract Sanity Check Before Implementing Writes

**Question:** Are the linkage keys and lifecycle states sufficient to (a) prove the write step is gated by approval, (b) consume exactly the persisted proposals, and (c) avoid duplicate writes on re-run?

**Evidence required:**
- A pasted excerpt (verbatim) showing:
  - the chosen linkage keys (fields / query parameters) for matching approvals
  - the list/query used to load proposals for writing
  - the lifecycle transition rules (a short bullet list)
- One example “happy path” sequence with identifiers:
  - request approval → approve → write

| Observation | Likely call |
|---|---|
| Linkage is explicit (handover_id + task_id + action), proposals are loaded from persistence by those keys, and idempotency has a concrete mechanism (status/receipt) | PROCEED |
| Linkage is ambiguous (e.g., approval not tied to task/action) or proposals could be reloaded from regenerated content | PIVOT |
| Write step would rely on GitHub as the source of truth or cannot show “no approval, no write” deterministically | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. Do not add a “demo-only” path that writes to GitHub outside `orchestrate(...)`.
2. Do not let the GitHub board become the primary state store (no “read GitHub to figure out what we proposed”).
3. Do not regenerate, re-rank, or “clean up” story proposals after they have been presented for review.
4. Do not broaden GitHub enrichment beyond creating visible draft items required to show a populated board.
5. Do not add new scenario inputs or modify the frozen demo-workspace shape.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- The Phase 3 schema slots (`approval_status`, `approval_decision_id`, `approved_at`, `written_at`) were dimensioned correctly: Phase 4 added zero columns to `story_proposals`. Only one new table (`proposal_write_receipts`) was needed.
- Linkage via `(handover_id, action_type=WRITE_GITHUB_PROJECT_V2, item_id=task_id)` reused the existing `pending_approvals` table verbatim — no API or schema change to the approval surface.
- Splitting the contract into a thin `board_write_contract.py` module (gate + lifecycle guards, no GitHub) before the orchestrator runner kept the precondition tests independent of the GraphQL fakes.
- The atomic `record_proposal_write` helper (single SQLite transaction: precondition check → insert receipt → mark written) made idempotent resume after a partial failure trivial — the writer just consumes whatever `select_writeable_proposals` returns on each run.

**What was harder than expected:**
- The harness arc wanted a refusal step *and* idempotent re-runs in the same code path, which conflicted: on a second run the prior approval is still valid, so the writer no longer refuses. Resolved by short-circuiting the arc when all proposals are already `written` rather than fabricating a refusal.
- Deciding whether to stamp `pending → approved` before or after the GitHub-config check — chose "after" so a missing token leaves rows untouched at `pending`. A subsequent run with a token replays cleanly.

**Decisions made during execution (deviations from this plan):**
- **No write-receipt fields added to `story_proposals`.** The plan listed receipts under Task 2 without prescribing a table shape. Chose a separate `proposal_write_receipts` table with a 1:1 FK to keep `story_proposals` focused on lifecycle state and receipts focused on traceability. Single-author judgement; no review needed at this size.
- **Did not modify `/approvals/*` endpoints.** The plan allowed "API route(s) and/or scripts/run_kickoff_demo.py" — chose harness-only because the existing endpoints already accept `action_type=WRITE_GITHUB_PROJECT_V2` as an opaque string. Adding a typed route would have been speculative scope.
- **Arc short-circuit on already-written batches** (see "harder than expected"). Self-approved.

**Forward plan:**
- Phase 5: rehearsal/runbook + recorded transcript of `--phase4` against a real GitHub Project. The harness already prints all the evidence the rehearsal needs; Phase 5 just needs to script the end-to-end demo and capture it.
- Smaller follow-up: surface `list_write_receipts` on the dashboard endpoint so a reviewer can see "what was written and when" without shelling into SQLite. Out-of-scope for Phase 4 by design (Hard Rule 5: don't broaden scope).
- Open question for Phase 5/6: when re-generating proposals in a new sprint, should an old approval row for `WRITE_GITHUB_PROJECT_V2` + `TASK-SEED-BOARD-001` be invalidated, or do we encode the proposal_batch_id into `item_id`? Current scheme (item_id=task_id) works for the kickoff because the task fires once. Multi-sprint reuse needs a decision before Phase 6.

**next_handover_id:** ALFRED_HANDOVER_12