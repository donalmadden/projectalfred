# Handover Workflow Discussion

> **Status:** Open. Park until the blank-project kickoff demo plan is fully complete (through Phase 5). Then revisit and elevate to a first-class Alfred workflow.
>
> **Owner:** Donal.
>
> **Linked to:** [ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md](./ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md), [scripts/generate_next_canonical_handover.py](../../scripts/generate_next_canonical_handover.py).

## Why This Discussion Exists

Every advance through the demo plan requires hand-editing `scripts/generate_next_canonical_handover.py` so the planner is grounded on the right scope sources and primed with the right identity (handover id, previous handover, title, sprint goal, grounding text). That hand-editing currently depends on a frontier model — Claude — reading the demo plan, the previous canonical handover, and the script, then producing a coherent surgery patch. When the model gets it wrong (subtly: stale phase number in one constant, scope source missing from the grounding block, sprint goal still describing the previous phase), the generated draft drifts off-scope and validation rejection rates go up.

That is the wrong dependency profile for a methodology that markets itself as "document-mediated, checkpoint-gated, frontier-model-independent at the seams." The protocol should not silently rely on a smart model to keep its own scaffolding consistent.

This document captures the problem so the next iteration of Alfred can address it deliberately, after the demo slice is complete.

## What The Current Workflow Looks Like

To advance from canonical handover N to N+1 today:

1. **Read the demo plan** to identify which phase is now active.
2. **Read the previous canonical handover** to know what was actually delivered (vs. planned).
3. **Hand-edit `scripts/generate_next_canonical_handover.py`**, updating at minimum:
   - `EXPECTED_HANDOVER_ID` and `EXPECTED_PREVIOUS_HANDOVER`
   - `DISPLAY_TITLE` (phase title)
   - `SPRINT_GOAL` — a multi-paragraph editorial brief describing what the next handover must lock down, what is now ratified, and what is out of scope
   - `DEMO_PLAN_GROUNDING` — bullet list of authoritative scope sources with phase-aware framing
   - `load_demo_plan_context()` — the function that materialises the scope block; phase number and scope-source list are baked into the function body
   - The module docstring (mentions phase number)
   - The argparse `--source` / `--output` / `--failed-output` help text (default paths hardcoded in help strings)
   - Optionally: add a new constant for the *previous* phase's canonical handover so it gets pulled in as a frozen scope source
4. **Spot-check** that nothing else mentions the old phase number.
5. **Run the script.**
6. **Read the generated draft.** Iterate on the grounding text and sprint goal if the planner drifted.

Step 3 alone is six places to keep in sync. Step 4 is "trust me" until proven otherwise — the script ran fine for Phase 2 with stale `test_generate_next_canonical_handover.py` assertions left over from Phase 1, because the tests aren't part of the generation path. The deviation surfaced only when a full regression run was executed.

## What The Current Workflow Depends On A Frontier Model For

| Step | Mechanical? | Editorial? | Frontier model needed? |
|---|---|---|---|
| Bump `EXPECTED_HANDOVER_ID` (N → N+1) | yes | no | no — derivable from a phase index |
| Bump `EXPECTED_PREVIOUS_HANDOVER` | yes | no | no — derivable from the same index |
| Update `DISPLAY_TITLE` | yes | partial | no if phase titles live in the demo plan |
| Bump default paths in argparse help | yes | no | no |
| Bump module docstring phase number | yes | no | no |
| Decide which previous canonical handovers become "frozen scope sources" | mostly mechanical | partial | no if the rule is "every ratified prior phase canonical" |
| Write the `SPRINT_GOAL` paragraph | no | yes | currently yes |
| Write the `DEMO_PLAN_GROUNDING` paragraph | no | yes | currently yes |
| Decide which active-docs become Phase N scope sources | partial | partial | currently yes |
| Inline-verify the generated draft is on-scope | no | yes | currently yes (used to be a human reviewer; now Claude) |

The mechanical rows above could be eliminated entirely. The editorial rows are where the real work is — but only the very first editorial draft per phase actually requires judgment. After the phase plan is locked, the sprint goal is a near-mechanical translation of the demo-plan phase entry plus any post-mortem follow-ups from the prior canonical handover.

## Proposal Sketch — Not For Implementation Yet

A first-class workflow could look like this. None of this is settled; the point is to give the after-Phase-5 revisit a concrete starting shape to argue with.

### A. Phase manifest as the source of truth

Move identity and scope-source data out of the generator script and into a declarative phase manifest, e.g. `docs/active/PHASE_MANIFEST.yaml`:

```yaml
project: blank_project_kickoff_demo
plan_path: docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md
phases:
  - id: 0
    handover_id: ALFRED_HANDOVER_5  # or whichever Phase 0 was promoted as
    title: Freeze The Scenario
    status: ratified
    scope_sources:
      - docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md
  - id: 1
    handover_id: ALFRED_HANDOVER_8
    title: Define The Canonical Kickoff Handover Shape
    status: ratified
    scope_sources:
      - docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md
      - docs/active/DEMO_PROJECT_LAYOUT.md
      - docs/active/KICKOFF_HANDOVER_OUTLINE.md
  - id: 2
    handover_id: ALFRED_HANDOVER_9
    title: Close Orchestrated Execution Path
    status: ratified
  - id: 3
    handover_id: ALFRED_HANDOVER_10
    title: Carry Proposed Stories As First-Class Runtime State
    status: planning
    sprint_goal_seed: |
      Phase 3 must carry proposed stories as first-class runtime state...
    scope_carry_forward: [0, 1, 2]   # which prior phases' artifacts ground this one
```

The generator script becomes a renderer that:
1. Reads the manifest
2. Identifies the next phase whose `status: planning`
3. Pulls every `scope_sources` entry from every `scope_carry_forward` phase
4. Pulls the previous ratified phase's canonical handover automatically
5. Composes the grounding block and the sprint goal from declarative inputs

Hand-editing the generator script disappears. Advancing to the next phase becomes a manifest update + a script run.

### B. Sprint goal as a structured object, not a paragraph

The sprint goal today is a 20-line prose paragraph hand-written by Claude. It could be a structured object:

```yaml
sprint_goal:
  this_phase_must_lock_down:
    - The persistence schema for StoryProposal records (Pydantic + SQLite)
    - The harness insertion point for the persistence write
    - How the gate review surfaces persisted records without regeneration
  ratified_inputs:
    - phase_0
    - phase_1
    - phase_2
  out_of_scope:
    - phase_4   # GitHub Project V2 write path
    - phase_5   # rehearsal runbook
  observable_evidence_of_completion:
    - Inspect persisted rows after a harness run
    - Re-run gate listing without re-invoking the story generator
  followups_from_prior_phase:
    - Move structured story output onto TaskResult
    - Make AlfredConfig fail fast on empty model string
```

The renderer assembles these into the prose paragraph the planner needs. The structured form is reviewable, diffable, and template-fillable without LLM intervention.

### C. Pre-flight validators before the planner runs

Before invoking the planner, run cheap deterministic checks:

- Every `scope_sources` path exists on disk
- Every prior-phase canonical handover referenced exists in `docs/canonical/`
- The previous-phase canonical handover's `next_handover_id` matches this phase's `handover_id`
- No phase number is mentioned in the script outside of derived-from-manifest paths

If any check fails, bail before any LLM call. This catches "stale phase number in one constant" mechanically.

### D. Test the renderer, not the prose

`tests/test_scripts/test_generate_next_canonical_handover.py` currently asserts properties of the prose constants (`assert "Phase 1" in SPRINT_GOAL`). Those assertions go stale every phase advance — which is why we currently have three pre-existing failing tests in that file that have been failing since Phase 2.

If the renderer takes manifest input and produces grounding text, the tests can fixture a known manifest and assert the renderer's output deterministically. No prose-level assertions; no churn per phase.

### E. Optional: post-generation validators

After the planner produces a draft, additional cheap validators can check it cites only `scope_sources` from the manifest, mentions the right phase number, and includes the expected `next_handover_id`. The current `validate_alfred_handover.py` already does some of this; tightening the integration is a small addition.

## Open Questions To Revisit

1. **Where does editorial content live?** The current `SPRINT_GOAL` paragraph carries judgment about what the next phase should and shouldn't include — that is real planning work, not boilerplate. Splitting it into structured fields (proposal B) preserves the judgment but changes its surface. Is that a net win or just relocated complexity?

2. **Manifest authorship.** Who writes the manifest entry for phase N+1? If a frontier model writes it, we have not eliminated the dependency, only shifted it. If a human writes it from the demo plan, what tooling makes that pleasant?

3. **Granularity of "ratified."** Today, "ratified" means "the canonical handover was promoted." Should the manifest mark individual decisions (Phase 1's three frozen specs) as ratified, or only whole phases? The former gives finer-grained scope-carry-forward; the latter is simpler.

4. **Backward compatibility.** Several scripts in `scripts/` (`dogfood_run.py`, `generate_phase7_canonical.py`, etc.) follow the same pattern of hand-edited identity constants. A manifest-driven renderer would either subsume them or coexist with them awkwardly.

5. **Validator coverage of editorial drift.** The biggest current failure mode is "the generated draft mentions the wrong phase or includes deliverables out of scope." A validator can catch the first mechanically; the second requires interpreting prose. How much can be deterministic?

6. **Stale tests.** `test_generate_next_canonical_handover.py` has three failing assertions today (since Phase 2). They are quietly excluded from "Phase 2 acceptance" because they pre-existed. A manifest-driven approach would let those tests be regenerated from the manifest fixture, so phase advances stop creating test rot.

## Constraints On The Revisit

- **Park until the demo plan is complete (Phase 5).** Doing this now would broaden Phase 3 scope and risk the demo slice. The demo's value is "narrowness honestly executed"; metawork on the generator is not in that slice.
- **Don't pre-commit to the proposal sketch above.** Treat it as one starting point among several.
- **Match the methodology's epistemic separation.** Whatever lands should keep editorial decisions (what's in scope) reviewable as documents, not buried in code. The handover document remains the protocol surface; the manifest is scaffolding for generating it.
- **No new frontier-model dependencies.** A solution that "uses Claude better" is the same anti-pattern in nicer clothes. The goal is to reduce the surface area where a frontier model's careful reading is the only thing keeping the scaffolding consistent.

## What Would Trigger Revisiting

Any of the following:

- A canonical handover advance produces a generated draft that ships with the wrong phase number or stale scope sources, and the issue isn't caught by the existing validators.
- The hand-edit step becomes the longest part of advancing a phase.
- A new project picks up Alfred and discovers the same hand-edit ritual must be reinvented for its own demo plan.
- Phase 5 closes and we have rehearsal time to invest in tooling rather than features.

When one of those triggers fires, this document is the starting brief.
