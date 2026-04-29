# Kickoff Handover Outline

This document freezes the exact shape of the kickoff handover Alfred must generate for the Customer Onboarding Portal demo. It is a target structure, not a sample.

## CONTEXT - READ THIS FIRST

The generated handover opens by stating the project identity, the charter's business objective, and the frozen demo facts: the demo project starts nearly blank, the GitHub Project board starts with zero items, the project docs are the source of truth, and board writes are gated behind human approval. It must make the run intent obvious to a non-technical reader: generate the first governed kickoff handover, compile it, produce 6-8 draft backlog items, pause, and wait for approval before any board mutation happens.

## WHAT EXISTS TODAY

The generated handover states that the demo workspace begins with `README.md`, `docs/CHARTER.md` [future-doc: path inside the external demo workspace], and an empty `docs/handovers/` [future-path: directory inside the external demo workspace] directory. It must also say explicitly that there is no prior delivery history, no existing `src/` tree, no tests, and no CI workflow in the demo workspace at kickoff.

## KICKOFF GOALS

The generated handover must say that this kickoff run aims to persist the first governed handover artifact in the demo project's `docs/handovers/` directory, translate the charter into a credible first-cut backlog for the blank GitHub Project, keep the docs artifact authoritative while treating the board as a downstream projection, and make the approval gate visible and understandable to a senior manager.

## PROPOSED BACKLOG - CUSTOMER ONBOARDING PORTAL

The generated handover must present 6-8 proposed kickoff stories. Every story must include a story title, a one-line description, 2-3 acceptance-criteria bullets, and a story-point estimate.

Benchmark story titles for review:

1. Define onboarding journey end-to-end
2. Stand up signup and identity verification surface
3. Build customer profile data model
4. Wire up document-upload and KYC checks
5. Compose welcome and activation email flow
6. Add internal-ops review queue for flagged customers
7. Instrument funnel analytics
8. Define rollout and pilot-cohort plan

The benchmark list is the comparison spine for review; the final runtime proposals may use cleaner wording, but every proposal must remain traceable to the charter and the final count must stay within 6-8 items.

## BOARD-SEEDING TASK

`TASK-SEED-BOARD-001`

- Agent: `story_generator` (implemented today at `src/alfred/agents/story_generator.py`)
- Input: the compiled `HandoverDocument` produced from the approved kickoff handover
- Output: a structured list of 6-8 `StoryProposal` items, each carrying `title`, `description`, `acceptance_criteria`, and `story_points`
- Gate: execution halts immediately after story generation; no board writes occur until the approval gate has been passed
- Failure mode: if fewer than 6 or more than 8 proposals are generated, the task fails and must be re-run before approval is requested

## APPROVAL GATE

The generated handover must include this approval prompt verbatim, with `N` replaced by the actual count of proposed items:

> Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

This wording is locked for Phase 4 reuse and must be presented as a read-only review checkpoint, not as an automatic write action.

## WHAT NOT TO DO

The generated handover must warn the executor not to write to the GitHub Project before approval, not to emit fewer than 6 or more than 8 proposals, not to collapse structured story fields into summary prose only, not to treat the benchmark titles as hardcoded output when the charter supports cleaner phrasing, and not to broaden scope into retrospectives, multi-sprint planning, or story editing.

## POST-MORTEM

The generated handover must reserve executor-fill subsections for `What worked`, `What was harder than expected`, `Decisions made during execution`, and `Forward plan`.
