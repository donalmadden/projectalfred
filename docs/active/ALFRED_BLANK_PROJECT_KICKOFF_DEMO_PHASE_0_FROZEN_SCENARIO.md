# Alfred Blank-Project Kickoff Demo — Phase 0 Frozen Scenario

> **Status:** Phase 0 of [ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md](./ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md). This document is the **freeze record** for the demo scenario. Once ratified, no decision below may be revisited inside Phases 1–5 without re-opening Phase 0 explicitly.

---

## Why this document exists

The demo plan's Phase 0 goal is *"Remove ambiguity before implementation starts."* That requires a single, citable artifact that captures every freeze decision so Phase 1 onward can proceed without re-litigating scope. This document is that artifact.

It is intentionally short. Anything not frozen here is, by definition, **not yet decided**, and any later phase that depends on an undecided detail must surface that gap rather than invent an answer.

---

## Frozen Decisions

### 1. Demo scenario name

**Frozen value:** `Customer Onboarding Portal`

No domain substitution will be exercised before the slice works end-to-end. The two substitutions sanctioned by the plan (`Vendor Risk Assessment Portal`, `Contract Approval Workflow`) remain on the shelf as fallbacks **only if** a sponsor objects to the chosen domain after the slice is otherwise complete.

### 2. Demo code-project shape

**Frozen value:** A brand-new code project (created fresh for the demo) whose only initial documentation surface is:

```
<demo-project-root>/
├── README.md                    # one-paragraph project description
└── docs/
    ├── CHARTER.md               # the kickoff charter Alfred consumes
    └── handovers/               # empty at start; Alfred writes ALFRED_HANDOVER_1.md here
```

Constraints:

- Alfred lives **inside the demo project's `docs/` folder**, not inside this repository's `docs/` folder.
- No `src/`, no tests, no CI workflows in the demo project at start. The point is "blank slate".
- The handovers subdirectory exists but is empty; the first artifact Alfred persists is `docs/handovers/ALFRED_HANDOVER_1.md`.
- Optional `docs/CURRENT_STATE.md` is **deferred** — Phase 1 may add it if the kickoff handover needs an explicit "what exists" anchor, but Phase 0 does not require it.

### 3. Demo board target

**Frozen value:** Exactly one brand-new GitHub Project V2 board, created fresh for the demo, with **0 starting items** at the moment the demo begins.

Constraints:

- The board is owned by an account/org the demo operator controls.
- No pre-seeded columns, custom fields, or items beyond GitHub's defaults.
- The board ID/URL is captured in the demo runbook (Phase 5 deliverable), not here, so this freeze remains valid across re-runs against fresh boards.

### 4. Success criterion

**Frozen value:** Between **6 and 8 visible draft items** appear on the previously blank GitHub Project board after the human approves the board-write step.

Constraints:

- Items must be visible on the board UI, not merely created via API and hidden.
- Items must originate from the Story Generator's proposals for the kickoff backlog — not hardcoded.
- Fewer than 6 or more than 8 items is a Phase 4 acceptance failure, not a Phase 0 redefinition.

### 5. Narrated arc

**Frozen value:** The single demo arc is:

> **kickoff charter → governed project docs → governed backlog seed**

Expanded to the operator-visible chain (matches the plan's "Demo Outcome We Are Building Toward"):

```
docs/CHARTER.md
  → Alfred generates kickoff handover draft
    → Human approves draft
      → docs/handovers/ALFRED_HANDOVER_1.md persisted
        → Compile to HandoverDocument
          → orchestrate(...) dispatches backlog-seeding task
            → Story Generator proposes 6–8 stories
              → Approval gate (no board writes yet)
                → Human approves
                  → GitHub Project V2 populated with 6–8 draft items
```

No alternative arcs may be demonstrated alongside this one.

---

## Items requiring human sign-off before Phase 1 begins

Phase 0 cannot be considered closed until the following are ratified by the project lead. They are surfaced here rather than guessed so Phase 1 inherits unambiguous inputs.

1. **Charter text for `docs/active/CHARTER.md`** — needs a one-page (≤ 400 word) charter for the Customer Onboarding Portal that gives Alfred enough material to draft a credible kickoff handover. Recommended structure: business context, primary user, success metric, known constraints, explicit non-goals. **[DM]**

2. **Candidate first-backlog story titles (6–8)** — a list of plausible kickoff stories so Phase 4 has a benchmark to compare Story Generator output against. Suggested working list (subject to sign-off):
   1. Define onboarding journey end-to-end
   2. Stand up signup and identity verification surface
   3. Build customer profile data model
   4. Wire up document-upload and KYC checks
   5. Compose welcome and activation email flow
   6. Add internal-ops review queue for flagged customers
   7. Instrument funnel analytics
   8. Define rollout and pilot-cohort plan
   **[DM]**

3. **Approval-gate wording** — the exact prompt the operator sees when the run pauses for board-write approval. Recommended draft: *"Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project."* **[DM]**

---

## Acceptance check (matches plan's Phase 0 acceptance criteria)

| Criterion | Status |
|---|---|
| Team agrees there is exactly one demo scenario | Ratified by signing this doc |
| Team agrees the project `docs/` surface is primary and the GitHub Project is secondary | Ratified by signing this doc |
| Team agrees blank-board seeding is the core visual moment | Ratified by signing this doc |
| Team agrees no additional demo paths will be pursued before this one works | Ratified by signing this doc |

**Checkpoint question (verbatim from plan):** *Does everyone agree the demo is specifically "new code project with Alfred in `docs/` → blank board projection" and not "all of Alfred"?*

**Sign-off:** _DM — 2026-04-22._

---

## What Phase 0 explicitly does **not** decide

To prevent scope creep into Phase 1:

- The exact handover **outline** Alfred will produce → Phase 1 deliverable.
- Where the **execution harness** lives (script vs CLI subcommand) → Phase 2 deliverable.
- The **approval persistence model** for in-flight proposals → Phase 3 deliverable.
- The **GitHub write path** implementation details → Phase 4 deliverable.
- The **rehearsal runbook** → Phase 5 deliverable.

Anything in those buckets surfacing in Phase 0 review is a sign Phase 0 is being over-scoped.
