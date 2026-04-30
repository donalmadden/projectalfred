# Alfred's Handover Document #8 — Phase 1: Kickoff Handover Shape

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_8
**date:** 2026-04-23
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_7
**baseline_state:** Phase 0 is fully ratified (DM sign-off 2026-04-22); the demo scenario, demo-project shape, blank GitHub Project board target, 6–8 items success criterion, and narrated arc are all frozen and locked against revision.

**Reference Documents:**
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — multi-phase build plan; this handover executes Phase 1 only
- The archived Phase 0 freeze record for the blank-project kickoff demo — every decision in that record is locked and may not be revisited here
- `docs/canonical/ALFRED_HANDOVER_7.md` — Phase 7/8 infrastructure baseline; confirms deployment surface is stable before demo work begins
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism constraints still in effect

This handover exists to close Phase 1 of the blank-project kickoff demo plan. Phase 0 locked *what* Alfred will demonstrate; Phase 1 locks *what Alfred will produce and read* — the exact charter text that feeds the run, the exact layout of the demo project's `docs/` folder, the exact outline of the kickoff handover Alfred will generate, the exact task definition that seeds the blank GitHub Project board, and the exact checkpoint language that gates the board-write step. Nothing in this handover reaches into the orchestrator harness (Phase 2), proposal-persistence model (Phase 3), GitHub write path (Phase 4), or rehearsal runbook (Phase 5). Those are explicitly deferred.

The Phase 1 acceptance test is a reading test: a senior manager must be able to read the generated handover draft alone and understand what Alfred is about to do and why the approval gate is there. Every deliverable in this phase serves that test.

---

## WHAT EXISTS TODAY

### Git History

```
35bde4a  demo: phase 0 freeze + repurpose canonical generator for kickoff demo
9309c68  docs: refine Alfred docs-native kickoff direction
994bcb3  docs: add Alfred operationalisation brief
6a71006  chore: ignore local remember state
a75bf85  docs: phase 8 portfolio polish and governance
2064480  adding candidate handover for reference
17e4fc4  docs: promote ALFRED_HANDOVER_7 canonical handover
1e9367a  phase8: add canonical generator and dynamic tooling validation
6b9fee6  docs: task 7 — README quick-starts and deployment docs update
1f27b2c  ci: task 6 — release workflow for GHCR and PyPI
981e20e  docker: task 5 — add image, compose, and env surface
ca3a1c6  phase7: tasks 1-4 — probes, logging, shutdown, and cli
```

### Current Repository State

The following modules and files **exist today**:

- Agent modules exist today under `src/alfred/agents`: `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`
- Tool modules exist today under `src/alfred/tools`: `docs_policy`, `git_log`, `github_api`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`
- FastAPI app exists today at `src/alfred/api.py` with 11 endpoints including `POST /compile`, `POST /generate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`
- `pyproject.toml` exists today with `[project]` and `[project.scripts]` populated; CLI entry `alfred.cli:main` is declared
- `docs/DOCS_POLICY.md` and `docs/DOCS_MANIFEST.yaml` exist today
- `docs/protocol/OPERATOR_RUNBOOK.md` exists today
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` exists today — the governing Phase 1–5 build plan
- An archived Phase 0 freeze record exists today under `docs/archive/` — retained for traceability while its decisions remain ratified history
- `docs/canonical/ALFRED_HANDOVER_7.md` exists today — Phase 7 canonical record
- Type checker in use: `pyright` (not `mypy`)

The following are **declared but unimplemented**:
- The demo project itself (the `Customer Onboarding Portal` workspace with its `docs/` surface) does not exist as a concrete directory in this repository today; it is a target external workspace to be initialised as a Phase 1 deliverable

The following are **to be created in this phase** (Phase 1):
- docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md — the frozen charter text Alfred will consume (per `doc` placement rule: `docs/`, `*.md`)
- docs/active/KICKOFF_HANDOVER_OUTLINE.md — the frozen target outline for the handover Alfred will generate (per `doc` placement rule)
- docs/active/DEMO_PROJECT_LAYOUT.md — the frozen spec for the demo project's `docs/` surface layout (per `doc` placement rule)
- docs/canonical/ALFRED_HANDOVER_8.md — this handover, promoted after human approval (per `handover_doc` naming convention: `ALFRED_HANDOVER_\d+`)

### Key Design Decisions Inherited (Do Not Revisit)

1. **Demo scenario is `Customer Onboarding Portal`** — frozen by Phase 0 sign-off; domain substitution is only permitted if a sponsor objects after the slice works end-to-end.
2. **Demo-project `docs/` shape is fixed** — `README.md`, `docs/CHARTER.md` [future-doc: path inside the external demo workspace], `docs/handovers/` [future-path: directory inside the external demo workspace] (empty); Alfred writes `docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the demo workspace] as its first persisted artifact.
3. **Success criterion is 6–8 visible draft items** on a previously blank GitHub Project V2 board; fewer or more is a Phase 4 acceptance failure.
4. **Narrated arc is locked** — charter → kickoff handover draft → human approval → persist → compile → orchestrate → story generation → approval gate → board write.
5. **Project `docs/` is primary; GitHub Project is a downstream projection** — board writes are never the source of truth.
6. **Alfred lives inside the demo project's `docs/` folder**, not inside this repository's `docs/`.
7. **No `src/`, no tests, no CI in the demo project at start** — the point is blank slate.
8. **Phase 1 deliverables are documents, not code** — execution harness lives in Phase 2.

---

## HARD RULES

1. **Do not revisit any Phase 0 freeze decision.** The scenario name, demo-project shape, board target, success criterion, and narrated arc are locked. If a Phase 1 deliverable appears to conflict, surface an open question rather than silently overriding the freeze.
2. **Do not build the execution harness in this phase.** Phase 1 produces frozen documents; Phase 2 closes the orchestrated execution path. Any code change in this phase is a scope violation.
3. **Do not write to the GitHub Project in this phase.** Board writes are gated behind Phase 4 approval machinery that does not exist yet.
4. **Do not store proposed stories only as prose.** When the outline references story generation, the structured form (title, acceptance criteria, story points) must be specified in the outline so Phase 3 knows what to persist.
5. **The checkpoint language must be explicit: "do not write to the board until the human approval gate has been passed."** Implicit gating is not acceptable.
6. **Do not use `mypy`.** The repository uses `pyright` for type checking.
7. **New files proposed in this phase must follow placement rules verbatim.** Documents go under `docs/` with `*.md` extension; scripts under `scripts/` with `*.py`; agents under `src/alfred/agents/`; etc.
8. **Do not broaden the demo scope.** Retrospectives, advanced dashboards, multi-sprint planning, and story editing after creation are out of scope for the demo slice.

---

## WHAT THIS PHASE PRODUCES

- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — the frozen, ≤400-word charter text for the Customer Onboarding Portal that Alfred will consume as its kickoff input (per `doc` placement rule: `docs/`, `*.md`)
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — the frozen section-by-section outline of the handover Alfred will generate, including the board-seeding task and checkpoint wording (per `doc` placement rule)
- `docs/active/DEMO_PROJECT_LAYOUT.md` — the frozen spec for the target demo-project `docs/` layout, including file names, one-line purpose of each file, and the empty `docs/handovers/` directory (per `doc` placement rule)
- `docs/canonical/ALFRED_HANDOVER_8.md` — this handover, promoted after human approval (per `handover_doc` naming convention)

Out of scope for this phase:
- Any code changes to `src/alfred/` — Phase 2
- The execution harness (script or CLI subcommand) that runs the orchestrator — Phase 2
- Proposal-persistence schema or model — Phase 3
- GitHub Project V2 write path — Phase 4
- Demo rehearsal runbook — Phase 5
- `docs/CURRENT_STATE.md` [future-doc: optional demo-workspace file; currently deferred] for the demo project — deferred per Phase 0 freeze; Phase 1 may add it only if the kickoff handover needs an explicit "what exists" anchor (surfaced as an open question below)
- Any archival sweep of `docs/active/` — deferred to a later phase

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Freeze the Kickoff Charter | `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` | CHECKPOINT-1 |
| 2 | Freeze the Demo-Project Layout | `docs/active/DEMO_PROJECT_LAYOUT.md` | — |
| 3 | Freeze the Kickoff Handover Outline | `docs/active/KICKOFF_HANDOVER_OUTLINE.md` | CHECKPOINT-2 |
| 4 | Promote This Handover | `docs/canonical/ALFRED_HANDOVER_8.md` | — |

---

## TASK 1 — Freeze the Kickoff Charter

**Goal:** Produce and ratify a ≤400-word charter document for the Customer Onboarding Portal that gives Alfred enough structured material to draft a credible kickoff handover without hallucinating domain context.

### Implementation

1. **Draft charter content** — Write `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` using the structure recommended by the Phase 0 freeze record: business context, primary user, success metric, known constraints, explicit non-goals. The charter must be specific enough that Alfred's Planner can infer 6–8 plausible kickoff backlog stories from it without free-association. Target length: 300–400 words.

   Suggested content anchors (drawn from Phase 0 candidate story list):
   - **Business context:** A financial-services firm needs a self-service portal for new customers to complete identity verification, upload KYC documents, and activate their account without branch visits.
   - **Primary user:** New retail customers onboarding digitally; secondary: internal compliance ops reviewing flagged cases.
   - **Success metric:** ≥80% of new customers complete onboarding end-to-end without human intervention within 10 minutes of starting.
   - **Known constraints:** Must integrate with existing identity-verification vendor API; no new data stores in Phase 1; mobile-first but not mobile-only.
   - **Explicit non-goals:** Branch-assisted onboarding, existing-customer flows, international KYC variations.

2. **Cross-check against Phase 0 candidate stories** — Verify that the charter text plausibly motivates each of the eight candidate stories listed in the Phase 0 freeze record. If any story cannot be derived from the charter without stretching, either adjust the charter text or surface a gap.

3. **Confirm word count** — The charter must not exceed 400 words. Count mechanically; do not estimate.

4. **Save at canonical path** — Per `doc` placement rule (`docs/`, `*.md`), save as `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`.

### Verification

```bash
# Confirm file exists at the correct path
ls docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md

# Word count check — must be ≤ 400
wc -w docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md

# Confirm required sections are present
grep -E "business context|primary user|success metric|known constraints|non-goal" \
  docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md --ignore-case
```

**Expected:**
- File exists at `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`
- Word count is ≤ 400
- All five structural elements (business context, primary user, success metric, known constraints, non-goals) are present
- A human reviewer can read the charter and derive 6–8 plausible kickoff stories without being told what they are

**Suggested commit message:** `demo: task 1 — freeze Customer Onboarding Portal charter`

### CHECKPOINT-1 — Charter Sufficiency

**Question:** Does the charter text give Alfred enough structured domain context to draft a credible kickoff handover and propose 6–8 plausible backlog stories, or does it require Alfred to hallucinate domain specifics?

**Evidence required:**
- Executor pastes the full text of `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` verbatim
- Executor pastes the output of `wc -w docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`
- Executor confirms each of the five structural sections is present and non-trivial

| Observation | Likely call |
|---|---|
| All five sections present, word count ≤ 400, reviewer can derive 6–8 stories without prompting | PROCEED |
| Fewer than five sections present or a section is one sentence with no actionable detail | PIVOT — expand charter before moving to Task 2 |
| Charter exceeds 400 words | PIVOT — trim to spec before moving to Task 2 |
| Charter is so generic that stories must be hallucinated (e.g. no domain, no metric, no constraint) | STOP — escalate to DM for charter content sign-off |

**STOP HERE.** Paste the charter text and word count, then wait for direction before beginning Task 2.

---

## TASK 2 — Freeze the Demo-Project Layout

**Goal:** Produce a single reference document that specifies, unambiguously, every file and directory that will exist in the demo project at the moment Alfred begins its run — so that Phase 2 can initialise the workspace deterministically and Phase 5 can reset it between rehearsal runs.

### Implementation

1. **Draft layout spec** — Write `docs/active/DEMO_PROJECT_LAYOUT.md`. It must list every file and directory, give a one-line purpose for each, and explicitly note which directories are empty at start.

   Required layout (locked by Phase 0 freeze):
   ```
   <demo-project-root>/
   ├── README.md                        # one-paragraph project description
   └── docs/
       ├── CHARTER.md                   # the kickoff charter Alfred consumes (content = Task 1 output)
       └── handovers/                   # empty at start; Alfred writes ALFRED_HANDOVER_1.md here
   ```

   The spec must answer all of the following, and only these, questions:
   - What is the one-paragraph text of `README.md`?
   - What is the content of `docs/CHARTER.md` [future-doc: path inside the external demo workspace]? (Answer: verbatim copy of `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — do not duplicate the text, reference the path)
   - Is `docs/handovers/` a git-tracked empty directory or does it require a `.gitkeep`? (Decide and record.)
   - Is `docs/CURRENT_STATE.md` [future-doc: optional demo-workspace file; currently deferred] included? (Decision required — see open questions.)

2. **Record the `ALFRED_HANDOVER_1.md` target path** — The layout spec must state explicitly: Alfred's first persisted artifact is `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md`. This is the file Phase 2 will write.

3. **Save at canonical path** — Per `doc` placement rule, save as `docs/active/DEMO_PROJECT_LAYOUT.md`.

### Verification

```bash
# Confirm file exists
ls docs/active/DEMO_PROJECT_LAYOUT.md

# Confirm the four required layout elements are described
grep -E "README\.md|CHARTER\.md|handovers|ALFRED_HANDOVER_1" \
  docs/active/DEMO_PROJECT_LAYOUT.md
```

**Expected:**
- File exists at `docs/active/DEMO_PROJECT_LAYOUT.md`
- All four required path elements (`README.md`, `docs/CHARTER.md` [future-doc: path inside the external demo workspace], `docs/handovers/` [future-path: directory inside the external demo workspace], `docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the demo workspace]) are named
- The `.gitkeep` question is answered explicitly
- The `docs/CURRENT_STATE.md` [future-doc: optional demo-workspace file; currently deferred] question is answered explicitly (include or explicitly defer)

**Suggested commit message:** `demo: task 2 — freeze demo project layout spec`

---

## TASK 3 — Freeze the Kickoff Handover Outline

**Goal:** Produce a fixed, section-by-section outline of the handover Alfred will generate for the Customer Onboarding Portal kickoff, including the board-seeding task specification and the exact checkpoint language that gates the board-write step.

### Implementation

1. **Draft the outline document** — Write `docs/active/KICKOFF_HANDOVER_OUTLINE.md`. This is the *shape* Alfred must produce, not an example or suggestion. It is the fixed target. Sections must include:

   **Required top-level sections in the generated handover:**
   - `## CONTEXT — READ THIS FIRST` — project identity, charter summary, phase zero summary
   - `## WHAT EXISTS TODAY` — state of the demo project at kickoff (README, charter, empty handovers dir)
   - `## KICKOFF GOALS` — what this kickoff run aims to accomplish
   - `## PROPOSED BACKLOG — CUSTOMER ONBOARDING PORTAL` — structured list of 6–8 proposed kickoff stories, each with: story title, one-line description, acceptance criteria (2–3 bullets), and story-point estimate
   - `## BOARD-SEEDING TASK` — the single executable task whose execution seeds the blank GitHub Project board (see step 2)
   - `## APPROVAL GATE` — verbatim checkpoint language (see step 3)
   - `## WHAT NOT TO DO` — scope-protection guardrails for this kickoff
   - `## POST-MORTEM` — executor-fill section for after the run

2. **Specify the board-seeding task** — The `## BOARD-SEEDING TASK` section must specify:
   - **Task ID:** `TASK-SEED-BOARD-001`
   - **Agent:** `story_generator` (exists today at `src/alfred/agents/story_generator.py`)
   - **Input:** the compiled `HandoverDocument` from this kickoff handover
   - **Output:** a structured list of 6–8 `StoryProposal` items, each carrying title, description, acceptance criteria, and story-point estimate
   - **Gate:** execution halts after story generation; no board writes until the approval gate is passed
   - **Failure mode:** if fewer than 6 or more than 8 proposals are generated, the task fails and must be re-run before approval is requested

3. **Specify the approval gate verbatim** — The `## APPROVAL GATE` section must contain the exact approval prompt wording (drawn from the Phase 0 freeze record recommended draft, updated with the actual N):

   > *"Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project."*

   Where `N` is the count of proposed items (6–8). This wording is locked; Phase 4 must use it verbatim.

4. **Embed the candidate story list** — The `## PROPOSED BACKLOG` outline must list the eight candidate stories from the Phase 0 freeze record as the benchmark:
   1. Define onboarding journey end-to-end
   2. Stand up signup and identity verification surface
   3. Build customer profile data model
   4. Wire up document-upload and KYC checks
   5. Compose welcome and activation email flow
   6. Add internal-ops review queue for flagged customers
   7. Instrument funnel analytics
   8. Define rollout and pilot-cohort plan

   The outline specifies the *structure* each story must carry; the Story Generator fills in the actual content at runtime.

5. **Save at canonical path** — Per `doc` placement rule, save as `docs/active/KICKOFF_HANDOVER_OUTLINE.md`.

### Verification

```bash
# Confirm file exists
ls docs/active/KICKOFF_HANDOVER_OUTLINE.md

# Confirm required sections are present
grep -E "^## (CONTEXT|WHAT EXISTS TODAY|KICKOFF GOALS|PROPOSED BACKLOG|BOARD-SEEDING TASK|APPROVAL GATE|WHAT NOT TO DO|POST-MORTEM)" \
  docs/active/KICKOFF_HANDOVER_OUTLINE.md

# Confirm task ID and agent reference
grep -E "TASK-SEED-BOARD-001|story_generator" \
  docs/active/KICKOFF_HANDOVER_OUTLINE.md

# Confirm approval gate wording is present
grep -i "reviewing now will not modify the board" \
  docs/active/KICKOFF_HANDOVER_OUTLINE.md
```

**Expected:**
- File exists at `docs/active/KICKOFF_HANDOVER_OUTLINE.md`
- All eight required sections are present
- `TASK-SEED-BOARD-001` and `story_generator` are named
- Approval gate wording matches the Phase 0 recommended draft verbatim
- The 6–8 story count constraint is stated explicitly in the task spec
- A senior manager reading only this outline would understand what Alfred is about to do and why the approval gate exists

**Suggested commit message:** `demo: task 3 — freeze kickoff handover outline and board-seeding task`

### CHECKPOINT-2 — Outline Intelligibility

**Question:** If a senior manager reads only `docs/active/KICKOFF_HANDOVER_OUTLINE.md` (and the charter it references), would they understand what Alfred is about to do, why the approval gate exists, and what the board will look like after approval?

**Evidence required:**
- Executor pastes the full text of `docs/active/KICKOFF_HANDOVER_OUTLINE.md` verbatim
- Executor confirms each of the eight required sections is present and non-trivial
- Executor confirms the approval gate wording matches the Phase 0 frozen draft exactly

| Observation | Likely call |
|---|---|
| All eight sections present; approval gate wording matches Phase 0 freeze; task spec names `story_generator` and `TASK-SEED-BOARD-001`; 6–8 constraint is explicit | PROCEED to Task 4 |
| Approval gate wording differs from Phase 0 freeze without explicit DM approval | PIVOT — correct wording before proceeding |
| Board-seeding task section is vague (no task ID, no agent name, no failure mode) | PIVOT — tighten task spec |
| A non-technical reader would not understand why approval exists before board writes | STOP — escalate to DM for outline review |

**STOP HERE.** Paste the outline text, then wait for direction before beginning Task 4.

---

## TASK 4 — Promote This Handover

**Goal:** After human approval of this draft, promote it to the canonical handover corpus so Phase 2 can cold-start from it.

### Implementation

1. **Await human approval** — This draft must not be promoted until a human reviewer has explicitly approved it. Do not self-promote.

2. **Copy to canonical location** — Per `doc` placement rule and `handover_doc` naming convention (`ALFRED_HANDOVER_\d+`), save the approved version as `docs/canonical/ALFRED_HANDOVER_8.md`.

3. **Update `docs/DOCS_MANIFEST.yaml`** — Add an entry for `docs/canonical/ALFRED_HANDOVER_8.md` and for each new `docs/active/` file created in Tasks 1–3. Failure to update the manifest will cause the docs-governance CI check (`scripts/check_manifest.py`) to fail.

4. **Verify governance CI passes** — Run the docs manifest check against the updated manifest.

### Verification

```bash
# Confirm canonical file exists
ls docs/canonical/ALFRED_HANDOVER_8.md

# Confirm manifest was updated
grep "ALFRED_HANDOVER_8" docs/DOCS_MANIFEST.yaml
grep "CUSTOMER_ONBOARDING_PORTAL_CHARTER" docs/DOCS_MANIFEST.yaml
grep "KICKOFF_HANDOVER_OUTLINE" docs/DOCS_MANIFEST.yaml
grep "DEMO_PROJECT_LAYOUT" docs/DOCS_MANIFEST.yaml

# Run governance check
python scripts/check_manifest.py
```

**Expected:**
- `docs/canonical/ALFRED_HANDOVER_8.md` exists
- All four new `docs/` files are registered in `docs/DOCS_MANIFEST.yaml`
- `scripts/check_manifest.py` exits 0

**Suggested commit message:** `demo: promote ALFRED_HANDOVER_8 and update docs manifest`

---

## WHAT NOT TO DO

1. **Do not revisit any Phase 0 freeze decision** — the scenario name, demo-project shape, board target, success criterion, and narrated arc are locked. Raise an open question rather than override.
2. **Do not write any code in this phase** — Phase 1 is entirely document work. Any `src/alfred/` change is a scope violation.
3. **Do not write to the GitHub Project** — board writes require Phase 4 approval machinery that does not exist yet.
4. **Do not describe the board-seeding task in prose only** — it must be a structured task spec with a task ID, named agent, structured output type, and explicit failure mode.
5. **Do not store proposed story data as summary prose** — the outline must specify the structured form (title, description, acceptance criteria, story-point estimate) so Phase 3 knows what to persist.
6. **Do not use vague checkpoint language** — "approval required" is not sufficient. The exact wording from Phase 0 must be reproduced verbatim.
7. **Do not place new documents anywhere other than `docs/active/`** — until promoted, all new handover-related documents live in `docs/active/`, not in `docs/canonical/` or the repository root.
8. **Do not omit `docs/DOCS_MANIFEST.yaml` updates** — every new file under `docs/` must be registered or the docs-governance CI gate will fail.
9. **Do not broaden Phase 1 scope** — if a task appears that belongs to Phase 2–5 (execution harness, persistence model, GitHub write, rehearsal), defer it and record it as a forward-plan item in the post-mortem.
10. **Do not claim `mypy` is in use** — this repository uses `pyright`.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section before closing the work. The next planner or reviewer must be able to cold-start from this artifact alone.

**What worked:**
- The two-source authoritative grounding (demo plan + Phase 0 freeze) gave Task 1–3 unambiguous inputs; no scope drift into Phases 2–5 occurred during drafting.
- Treating each Phase 1 deliverable as a frozen *spec* document rather than an example produced clean handoffs to Phase 2 — `DEMO_PROJECT_LAYOUT.md` reads as a workspace-init contract, `KICKOFF_HANDOVER_OUTLINE.md` reads as a runtime structure contract.
- Manifest hygiene held: `scripts/check_manifest.py` reports `No drift detected` after the new `docs/active/` entries were registered.

**What was harder than expected:**
- The CHARTER content question forked: Phase 0 sign-off was stamped against an earlier `CHARTER.md` draft under `docs/active/`, while the Phase 1 plan required a charter at `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`. Initially resolved by leaving the older file in place as a redirector; on review (2026-04-27) that was judged the wrong call — two competing entries in `docs/active/` blurred which charter was authoritative. Corrected by moving the older draft to `docs/archive/CUSTOMER_ONBOARDING_PORTAL_CHARTER_DRAFT.md`. Cleaner upstream would have been a single rename in Phase 0.
- The `## TASK 2` "Expected" verification line originally named `docs/canonical/ALFRED_HANDOVER_1.md` while every other reference (including the Phase 0 freeze and the layout doc) named `docs/handovers/ALFRED_HANDOVER_1.md`. Corrected in-place on 2026-04-27 so the verification line now matches the rest of the corpus.

**Decisions made during execution (deviations from this plan):**
- **Archived the prior charter draft from `docs/active/` to `docs/archive/CUSTOMER_ONBOARDING_PORTAL_CHARTER_DRAFT.md` (lifecycle: archive, indexed: false, citable: false).** Why: an earlier in-session decision retained it as an `active_brief` redirector, but on review that left two charter entries indexed under `docs/active/` and risked the planner citing the superseded text. Archiving makes the frozen Phase 1 charter the unambiguous authority while preserving the older draft for traceability. The `lifecycle_status: archive` flag excludes it from default generation and validation flows per `docs/DOCS_POLICY.md`. Approved: DM (in-session, 2026-04-27).
- **`KICKOFF_HANDOVER_OUTLINE.md` and `DEMO_PROJECT_LAYOUT.md` use ASCII hyphens (`-`) in section headers instead of em-dashes (`—`).** Why: matches the verification regex in this handover and avoids unicode-collision risk in downstream tooling. Approved: implicit — no behavioural impact.

**Forward plan:**
- Phase 2: Close the execution path around the orchestrator — narrow harness that takes a compiled `HandoverDocument` and runs it through `orchestrate(...)` targeting the demo project workspace
- Phase 3: Carry proposed stories as first-class runtime state — structured persistence of `StoryProposal` items linked to the handover task that generated them
- Phase 4: Close the HITL gate into GitHub Project V2 board writes — approval record tied to task, write path for blank-board seeding
- Phase 5: Rehearsal, instrumentation, and demo script

**next_handover_id:** ALFRED_HANDOVER_9
