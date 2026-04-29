# Alfred Blank-Project Kickoff Demo Plan

## Purpose

This brief turns the proposed Alfred senior-management demo into a **phased concrete build plan**. It is deliberately narrow: the goal is not to make all of Alfred complete, but to land one end-to-end slice that is:

- faithful to [docs/protocol/architecture.md](../protocol/architecture.md)
- aligned with [docs/active/OPERATIONALISE_ALFRED.md](./OPERATIONALISE_ALFRED.md)
- grounded in a real project-kickoff use case
- demonstrable from a **brand-new code project whose `docs/` folder is Alfred's home**
- optionally projected into a **brand-new GitHub Project that starts empty**

## Single Blessed Demo Scenario

### Use case

The demo scenario is:

> A brand-new **Customer Onboarding Portal** code project is kicking off. A new repository or project workspace exists with a `docs/` folder but no meaningful delivery history yet, and the GitHub Project is empty. Alfred turns the project charter into governed markdown inside the project's `docs/` folder, compiles that handover into a structured execution artifact, executes the first backlog-seeding task through the orchestrator, pauses at a human approval gate, and only then writes the first draft stories into the blank GitHub Project as a downstream projection of the approved plan.

This use case is intentionally ordinary:

- senior stakeholders understand it immediately
- the first backlog is easy to judge as useful or not
- a docs-native project workspace is a surface developers already understand
- blank board -> seeded governed backlog is visually strong
- it aligns naturally with "document as protocol" and "checkpoint-gated execution"

### Allowed domain substitution

If the sponsor rejects the exact nouning, only the surface domain may change. The structure of the demo must remain the same.

Allowed substitutions:

- `Customer Onboarding Portal` -> `Vendor Risk Assessment Portal`
- `Customer Onboarding Portal` -> `Contract Approval Workflow`

Do **not** change the execution pattern in response to domain tweaks.

## Demo Outcome We Are Building Toward

By demo time, Alfred must be able to show this exact arc:

1. A new code project exists with `docs/CHARTER.md` [future-doc: path inside the external demo workspace] and an empty or near-empty `docs/` surface
2. GitHub Project starts with **0 items**
3. Alfred generates a **kickoff handover draft** for that project workspace
4. Alfred persists the approved kickoff artifact under the project's `docs/` folder
5. Alfred compiles the approved draft into a structured `HandoverDocument`
6. Alfred executes the first task through `orchestrate(...)`
7. Alfred reaches a checkpoint / approval gate before board writes
8. Human approves the write
9. Alfred writes the first 6-8 draft stories to the previously blank GitHub Project
10. Alfred shows the resulting state through the project docs artifact, logs, and board state

## Why This Slice Is The Right One

This slice directly addresses the gaps identified in `OPERATIONALISE_ALFRED.md`:

- it makes the orchestrator the primary execution surface for the demo
- it restores the handover artifact to the centre of the runtime story
- it closes one real HITL loop into a concrete action
- it places Alfred inside a medium developers are already comfortable using: the project's `docs/` folder
- it proves the architecture through a genuine product-kickoff use case

It also matches the architecture rather than bypassing it:

- Planner drafts, does not execute
- Story Generator proposes stories, does not write directly
- Quality Judge gates progress
- Orchestrator composes the flow
- The project docs remain the source-of-truth coordination surface
- Board writes happen only after approval

## Hard Rules

1. **Do not build a fake executive demo path that bypasses `orchestrate(...)`.**
2. **Do not let story creation write directly to GitHub without a visible approval gate.**
3. **Do not treat the GitHub Project as the source of truth.** The project `docs/` surface is primary; GitHub is a projection.
4. **Do not hide critical execution state in temporary process memory if it needs to survive a pause/resume boundary.**
5. **Do not broaden scope into retrospectives, advanced dashboards, or general workflow engines.**
6. **Do not build multiple demo scenarios.** One scenario, rehearsed well, beats three half-finished ones.
7. **Do not optimise for generality before the demo slice works.** The demo slice may be narrow as long as it is architecturally honest.
8. **Do not sell autonomy.** The differentiator is governed coordination.

## What The Demo Must Prove

### Architectural proof

- The handover document is the governing artifact
- The orchestrator is the runtime coordinator
- Checkpoints and approvals gate execution
- Agents remain role-isolated

### Business proof

- Alfred can accelerate the kickoff of a real new project
- Alfred can establish useful project memory inside the repository's `docs/` folder before any substantial feature code exists
- Alfred can seed a blank project board with a structured initial backlog
- Alfred improves control and auditability rather than reducing it

### Operational proof

- The service is runnable
- The flow is repeatable
- The canonical project docs state is visible and intelligible to humans
- The board state change is visible and easy to explain

## Out Of Scope

- Full generic orchestration platform
- Rich resume semantics for every possible agent/task type
- Retrospective flows
- Story editing after creation
- GitHub field enrichment beyond what is required to create visible draft items
- Multi-sprint planning
- Sophisticated dashboards beyond what already exists
- Broad documentation polish unrelated to the demo slice

## Minimal Viable Demo Slice

The only slice that matters is:

`project charter -> project docs artifact -> docs/handovers/ALFRED_HANDOVER_1.md -> human approval -> compile -> orchestrated backlog-seeding task -> approval -> GitHub Project populated`

If a proposed task does not directly advance that chain, it is suspect.

## Required Functional Capabilities

The demo slice requires the following concrete runtime capabilities:

1. A new code project can be initialized with a usable `docs/` surface
2. A kickoff prompt / charter can be turned into a draft handover for that project
3. The approved draft can be persisted under the project's `docs/` folder and compiled into a structured `HandoverDocument`
4. The compiled handover can contain a task whose execution uses the Story Generator to propose kickoff backlog items
5. The proposed backlog items can be carried in a structured form long enough to support approval and write
6. A checkpoint or approval gate can pause board writes
7. Approval can trigger the actual GitHub Project write
8. The GitHub Project write can be shown against an initially empty board without displacing the docs artifact as source of truth

## Phase Plan

### Phase 0 — Freeze The Scenario

**Goal:** Remove ambiguity before implementation starts.

**Deliverables:**

- Final demo scenario name: `Customer Onboarding Portal`
- Final demo code-project shape under the target project, with Alfred living in `docs/`
- Final demo board target: one brand-new GitHub Project V2 board with 0 starting items
- Final success criterion: 6-8 visible created draft items after human approval
- Final narrated arc: kickoff charter -> governed project docs -> governed backlog seed

**Acceptance criteria:**

- Team agrees there is exactly one demo scenario
- Team agrees the project `docs/` surface is primary and the GitHub Project is secondary
- Team agrees blank-board seeding is the core visual moment
- Team agrees no additional demo paths will be pursued before this one works

**Checkpoint question:**

Does everyone agree the demo is specifically "new code project with Alfred in `docs/` -> blank board projection" and not "all of Alfred"?

### Phase 1 — Define The Canonical Kickoff Handover Shape

**Goal:** Lock the handover artifact Alfred will generate and compile for this scenario.

**Deliverables:**

- A fixed kickoff charter prompt for the `Customer Onboarding Portal`
- A fixed initial project-docs shape, for example:
  - `README.md`
  - `docs/CHARTER.md` [future-doc: path inside the external demo workspace]
  - optional `docs/CURRENT_STATE.md` [future-doc: optional demo-workspace file; currently deferred]
  - `docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the demo workspace]
  - optional future-facing wiki surfaces kept deliberately narrow in this slice
- A fixed target handover outline for the generated draft
- A specific kickoff task that seeds the blank board
- A checkpoint definition that explicitly gates board writes

**Implementation direction:**

- Reuse Alfred's canonical handover scaffolding
- Persist the kickoff artifact inside the target project's `docs/` tree, not inside Alfred's own canonical repo history
- Ensure the first execution-relevant task is about generating and proposing kickoff backlog items
- Make the approval gate explicit in the task and checkpoint wording

**Acceptance criteria:**

- The handover reads like a credible kickoff artifact for a new project
- The artifact location under `docs/` is obvious and defensible to human developers
- The board-seeding task is obvious to a human reviewer
- The checkpoint language clearly says "do not write until approved"

**Checkpoint question:**

If a senior manager reads only the handover, would they understand what Alfred is about to do and why the approval is there?

### Phase 2 — Close The Execution Path Around The Orchestrator

**Goal:** Make the demo use `orchestrate(...)` as the primary runtime surface.

**Deliverables:**

- One narrow executable path that takes a compiled `HandoverDocument` and runs it through the orchestrator
- One narrow executable path that can target a specific code project and its `docs/` folder
- A demo-safe way to invoke that path, either through:
  - a new script under `scripts/`, or
  - a narrowly scoped API/CLI surface that is explicitly for handover execution

**Implementation direction:**

- Prefer the smallest honest interface
- The runtime must visibly route through `orchestrate(...)`
- The path must read and write project-local docs state rather than Alfred-internal docs state
- Tasks with results already set must remain re-runnable without duplication

**Acceptance criteria:**

- A compiled kickoff handover can be passed into the orchestrator
- The runtime can point at a target code project without ad hoc manual edits
- The orchestrator dispatches the backlog-seeding task
- The run halts or pauses cleanly at the intended gate instead of bypassing it

**Checkpoint question:**

Can we truthfully say the demo's core execution path is document -> orchestrator -> checkpoint, rather than direct agent calls glued together?

### Phase 3 — Carry Proposed Stories As First-Class Runtime State

**Goal:** Preserve proposed stories in a form that supports approval and later write.

**Deliverables:**

- A structured place for generated kickoff stories to live during the run
- Clear linkage from those stories back to the handover/task that produced them
- Enough persisted state that a human can review what is being approved

**Implementation direction:**

- Avoid storing only summary prose like "Generated 8 stories"
- Store enough detail to support approval and subsequent creation
- Keep the state aligned with the document-mediated architecture as far as the current schema reasonably allows
- Prefer persistence that is explainable from the project docs surface, with SQLite remaining strictly operational

**Acceptance criteria:**

- Human reviewers can see which stories are awaiting approval
- The post-generation state is inspectable and attributable to a specific task
- The board-write step does not need to regenerate stories to proceed

**Checkpoint question:**

If execution pauses after story generation, do we still have the exact proposed backlog items available for review and write?

### Phase 4 — Close The HITL Gate Into GitHub Board Writes

**Goal:** Turn approval into a real gating mechanism for blank-board seeding.

**Deliverables:**

- A pending approval record tied to the handover/task/action
- A write path that uses approved proposed stories to create items in GitHub Project V2
- Guardrails so unapproved writes do not occur

**Implementation direction:**

- Use the existing approval model wherever possible
- Make the "request approval" step part of the execution flow, not a side demo
- Perform actual board creation only after approval is recorded
- Treat the GitHub board as a downstream view of approved project docs state, not as the primary runtime memory

**Acceptance criteria:**

- Without approval: no board items are created
- With approval: 6-8 draft items appear on the previously blank board
- The created items correspond to the reviewed proposals

**Checkpoint question:**

Can we show a genuinely blank board before approval and a populated board after approval, with the transition explained by the gate?

### Phase 5 — Rehearsal, Instrumentation, And Demo Script

**Goal:** Make the slice dependable enough to present.

**Deliverables:**

- A repeatable step-by-step demo script
- A known-good project charter payload
- A known-good target code-project layout
- A known-good blank GitHub Project target
- A fallback plan for model or GitHub hiccups

**Implementation direction:**

- Run the demo flow end-to-end at least twice
- Capture the exact commands or UI actions
- Keep logs visible enough to support the auditability story

**Acceptance criteria:**

- Two clean rehearsal runs
- Stable timing and operator steps
- The presenter can explain the flow without improvising architecture caveats

**Checkpoint question:**

Can the operator run the demo from muscle memory without branching into troubleshooting theatre?

## Suggested Work Breakdown For The Next 24 Hours

### Track A — Artifact and scenario lock

- Freeze the `Customer Onboarding Portal` charter text
- Freeze the target code project's `docs/` layout for the demo
- Define the exact first 6-8 target stories Alfred should plausibly propose
- Define the fixed approval wording

### Track B — Orchestrated execution path

- Add the narrow execution harness around `orchestrate(...)`
- Ensure compiled handovers for this scenario can be run against a target project workspace without manual code intervention

### Track C — Proposal persistence and approval linkage

- Carry proposed story data through the execution boundary
- Link proposals to approval requests and the eventual write step

### Track D — GitHub write closure

- Wire the approved proposals into `create_story(...)`
- Verify behavior against a truly blank GitHub Project

### Track E — Rehearsal and operator clarity

- Rehearse from fresh code project + blank board to populated board
- Record exact steps
- Remove any step that requires hand-waving

## Definition Of Demo-Done

The slice is demo-done when all of the following are true:

- There is exactly one chosen scenario
- The scenario starts from a fresh code project whose `docs/` folder Alfred can use
- The scenario also starts from a blank GitHub Project
- Alfred generates, persists, and compiles a kickoff handover for that scenario
- Alfred executes the relevant task through the orchestrator
- Proposed stories survive long enough for human review
- Approval is required before board writes
- Board writes occur only after approval
- The previously blank board ends with visible draft backlog items
- The project docs artifact remains the explainable source of truth throughout the flow
- The whole flow can be rehearsed twice without improvisation

## Definition Of Failure

The demo slice should be considered failed if any of the following happen:

- The orchestrator is bypassed in the main execution flow
- The board is written without a genuine approval gate
- The GitHub Project effectively becomes the source of truth because the project docs artifact is missing or stale
- Proposed stories must be regenerated after approval because state was lost
- The "document as protocol" story cannot be explained honestly
- The implementation sprawls into many features without completing the blank-board kickoff slice

## Final Guidance

The fastest path to a good demo is not breadth. It is **architecturally honest narrowness**.

If we build this slice well, the story is powerful:

> Alfred helps a new software project start correctly: with governed project docs, an explicit kickoff handover, checkpoints, human approval, and an initial backlog projected into a blank GitHub Project without surrendering control to agent autonomy.

That is the build target. Everything else is secondary.
