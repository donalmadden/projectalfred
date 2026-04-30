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

## Fresh Findings From Recent Phase Advances

The Phase 2 -> Phase 3 generator advance surfaced several workflow issues that are more specific than the generic "hand-editing is brittle" complaint above.

### 1. Context duplication is now a real failure mode

Phase 3 changed `generate_next_canonical_handover.py` so the full Phase 2 canonical handover (`docs/canonical/ALFRED_HANDOVER_9.md`) was included as an **authoritative scope source**. The same file was also still being loaded again as the **historical continuity source** because it was the previous canonical handover.

That duplication was not conceptually wrong, but it was operationally expensive:

- the authoritative scope block alone grew to roughly 65k characters
- the `summary` planner context grew to roughly 70.5k characters
- Claude then returned a schema-invalid empty tool payload (`{}`) three times in a row, so `PlannerOutput.draft_handover_markdown` was missing and the run failed before critique or validation

The important lesson is that context assembly can no longer be treated as "just string concatenation." Alfred now needs to model **context provenance**:

- which documents are authoritative scope for this phase
- which documents are historical continuity only
- whether the same document is being supplied twice under different labels

The Phase 3 fix was to teach the generator to track which repo docs are already embedded in authoritative scope and suppress duplicate historical continuity input automatically. That should be treated as a general workflow principle, not a one-off repair.

### 2. Future / external workspace paths need first-class semantics

The validator failure around `ALFRED_HANDOVER_8.md` showed that the workflow still conflates two different things:

- a repo doc reference that should resolve in this repository today
- a path that belongs to a future or external demo workspace and is being named intentionally

Paths like `docs/CHARTER.md`, `docs/CURRENT_STATE.md`, or `docs/handovers/ALFRED_HANDOVER_1.md` were legitimate in the blank-project demo narrative, but they were not part of this repo's docs inventory. Without an explicit signal, the validator treated them as broken current-state references and blocked canonical promotion.

The immediate fix was the `[future-doc: ...]` / `[future-path: ...]` tagging convention plus validator support for those tags. The larger workflow lesson is that Alfred needs a **reference semantics layer**, not just regexes over backticked paths.

### 3. Stale tests are part of the workflow problem, not an unrelated hygiene issue

`tests/test_generate_next_canonical_handover.py` had Phase 1 expectations baked into it long after the script had advanced to later phases. The script kept working because those tests are not part of the generation path, so the drift remained latent until a fuller regression pass happened.

That means "phase advance" currently has an invisible extra requirement:

- update the generator script
- update the tests that mirror the generator script's current phase assumptions
- remember to actually run those tests

Any future workflow improvement should treat that as one problem, not three. If the phase configuration becomes declarative, the tests should consume the same declarative input rather than shadowing it with hardcoded prose assertions.

### 4. Failed-candidate artifacts are useful, but their validation semantics are different

`*_FAILED_CANDIDATE.md` files are useful for inspection and debugging, but they deliberately sit in an awkward middle state:

- their content often carries the canonical handover identity
- their filename carries the archive / failed-candidate identity

That means some validators will quite reasonably report a filename/id mismatch on those files even when the underlying draft content is fine. That is not the same class of failure as "the canonical draft is factually wrong." The workflow should eventually make that distinction explicit instead of treating failed-candidate files as if they were ordinary canonical targets.

### 5. Prompt shadows look like a viable pressure-release valve

The next failure mode after deduplicating historical context was still simple prompt bulk: even without double-loading `ALFRED_HANDOVER_9.md`, the authoritative scope block remained large enough that Claude repeatedly returned a schema-invalid empty tool payload.

That suggests a useful distinction between:

- **authoritative docs** that humans review, cite, validate, and promote
- **prompt shadows** that exist only to help the planner consume the right parts of those docs more cheaply

The current experiment takes the safer version of that idea:

- the source docs remain untouched
- generated shadow files live outside `docs/` so they do not enter docs inventory, validators, or RAG implicitly
- the generator opts into them explicitly via config
- provenance stays attached to the original source path, so the planner still knows which real doc each shadow stands in for

This is closer to a "shadow view" than a summary in the canonical sense. The important workflow idea is that Alfred may need a **prompt-facing representation layer** distinct from its human-facing record layer.

### 6. Selective authoring exposed an implicit planning-doc schema

The next experiment after prompt shadows was to stop stuffing whole docs into the planner and instead build a deterministic **authoring context packet** from selected sections of five source documents. That worked well enough to cut the packet from roughly 57k raw source characters to roughly 28k prompt characters without rewriting the source docs.

The important part is *why* it worked: the source documents were already carrying a lightweight semantic structure in their headings and section roles, even though Alfred does not yet name that structure explicitly. The selector could safely ask for things like:

- `Hard Rules`
- `Out Of Scope`
- `Definition Of Demo-Done`
- `APPROVAL GATE`
- `WHAT NOT TO DO`
- `POST-MORTEM`
- `TASK 2 — Demo Execution Harness > Implementation Notes on the Orchestrator Interface`

and then render some sections as **verbatim authority** while turning others into **structured facts**.

That means Alfred is already relying on an implicit planning-doc schema, just one that currently lives in code instead of in the docs system itself. The runtime extractor is deterministic; it is *not* a frontier model re-discovering meaning from scratch on every run. The frontier model is only downstream, consuming a curated packet.

This matters for future docs such as `ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md`. If Alfred wants to selectively load or query those documents safely, it will eventually need an explicit contract for what kind of planning document each file is and which sections carry which semantics. Otherwise every selective-loading improvement risks turning into ad hoc heading heuristics embedded in one script.

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
      - docs/archive/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PHASE_0_FROZEN_SCENARIO.md
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

### F. Context assembly should be provenance-aware

The generator should stop treating planner context as one opaque blob and instead assemble a typed bundle:

- authoritative scope docs
- historical continuity docs
- derived summaries
- docs intentionally excluded because they are duplicates

That bundle should support deterministic checks before the planner runs:

- no document appears in both authoritative and historical roles unless explicitly allowed
- historical continuity is skipped automatically when the same canonical handover is already embedded as scope
- prompt-size budgets can be measured by source class instead of only by total character count

The recent Phase 3 fix implemented the smallest version of this idea inside `generate_next_canonical_handover.py`. The broader workflow should treat it as a first-class design requirement.

### G. Prompt shadows should be declarative, generated, and non-citable

If Alfred adopts prompt shadows more broadly, they should follow a few hard constraints:

- source documents remain the only authoritative and citable artifacts
- prompt shadows live outside `docs/`
- every shadow declares its source path, generation method, and freshness
- the generator must be able to swap a source doc for a shadow doc without losing source provenance
- shadow generation rules should be declarative (for example selected headings), not ad hoc prose edits inside the generator script

That gives Alfred a way to manage prompt budgets without rewriting history or blurring the contract between "what the team ratified" and "what the planner needs to read quickly."

### H. Prompt-markdown transpilation could be a middle path before full compression

There is likely a useful middle ground between:

- passing whole human-authored markdown docs through unchanged
- sending them through an aggressive prose compressor such as Caveman

That middle ground is a deterministic **prompt-markdown transpiler**:

- source docs remain untouched and authoritative
- the transpiler emits a markdown packet optimized for prompt efficiency
- locked wording is preserved verbatim where needed
- explanatory prose is rewritten into compact field/value or bullet form
- repeated long doc names and paths are replaced with stable aliases

The important distinction is that this is still **markdown**, not a bespoke binary or JSON-only representation. The planner still receives a readable artifact, but one with much lower syntactic overhead than the original handover prose.

#### Proposed packet shape

```md
# AUTHORING_PACKET v1

## SOURCES
- PLAN = docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md
- H9 = docs/canonical/ALFRED_HANDOVER_9.md
- CHARTER = docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md
- LAYOUT = docs/active/DEMO_PROJECT_LAYOUT.md
- OUTLINE = docs/active/KICKOFF_HANDOVER_OUTLINE.md

## SCOPE
- phase: 3
- handover_id: ALFRED_HANDOVER_10
- previous_handover: ALFRED_HANDOVER_9
- goal: carry proposed stories as first-class runtime state
- inherits: PLAN, CHARTER, LAYOUT, OUTLINE, H9
- out_of_scope: Phase 4 board writes; Phase 5 rehearsal runbook

## FACTS
- PLAN.scope: persist StoryProposal records; no regeneration between gate and write
- PLAN.done: persisted rows inspectable after harness run; gate listing re-runnable without story regeneration
- CHARTER.user: operator running kickoff demo for customer-onboarding portal
- LAYOUT.rule: future workspace docs remain in demo workspace, not this repo
- H9.runtime: execution harness exists today; persistence layer does not

## VERBATIM_RULES
### PLAN.hard_rules
<exact text preserved>

### OUTLINE.approval_gate
<exact text preserved>

### H9.orchestrator_interface_notes
<exact text preserved>

## TASK_CONTRACTS
- T1: define persistence schema for StoryProposal records
- T2: persist structured proposals at harness capture point
- T3: surface persisted proposals to gate review without regeneration
- T4: carry approval state forward to Phase 4 boundary without writing to GitHub

## GUARDRAILS
- do_not_claim_existing: any persistence schema or durable proposal store
- do_not_reopen: Phase 1 frozen docs; Phase 2 harness contract
- do_not_implement: GitHub Project V2 write path

## POST_MORTEM_INPUTS
- H9.pm1: structured story output should move onto TaskResult
- H9.pm2: AlfredConfig should fail fast on empty model string
```

#### Why this should save tokens

- repeated long titles such as "Alfred's Handover Document #9 — Phase 2: ..." become short aliases like `H9`
- many markdown headings collapse into compact section labels
- narrative connective prose disappears
- only a small annex of sections remains verbatim
- the packet can omit visual formatting that humans value but the planner does not need

#### Suggested transpilation rules

- Keep these sections verbatim by default: `Hard Rules`, `APPROVAL GATE`, task-contract wording, and any text whose exact phrasing is itself protocol.
- Convert these sections into compact fact bullets by default: `What Exists Today`, `What This Phase Produces`, `Out Of Scope`, `Definition Of Demo-Done`, `What Not To Do`, `Post-Mortem`.
- Assign every source doc a short stable alias and every selected section a stable section id, e.g. `H9.task2.impl_notes`.
- Replace repeated repo paths with a single alias declaration block unless exact path spelling is itself the point.
- Preserve markdown as the output format so packet inspection and diff review remain easy.

#### Why this may fit Alfred better than full prose compression

- deterministic and auditable
- easier to test than LLM-driven compression
- more faithful to locked wording because verbatim sections are explicit
- easier to connect to future doc-type contracts and selector rules
- less likely to hallucinate semantic equivalence than a free-form summariser

### I. Reference semantics should be declared, not inferred from prose

The `[future-doc: ...]` / `[future-path: ...]` convention is a good stopgap, but the more general need is:

- a way to mark that a path belongs to the external demo workspace rather than this repo
- a way to mark that a path is intentionally deferred / optional
- a way for validators and renderers to read those semantics without brittle local heuristics

That may eventually belong in the phase manifest, a richer docs-manifest entry type, or a small typed annotation layer in markdown. The important point is that "this path is intentionally future/external" is workflow metadata, not incidental wording.

### J. Planning docs may need lightweight section contracts

The selective authoring packet suggests a new middle ground between "free-form markdown" and "fully structured data model":

- planning docs remain human-authored markdown
- each doc *type* declares a lightweight section contract
- selectors and validators consume that contract deterministically

For example, a future contract for a planning-doc type could declare:

- required headings
- semantic classes such as `hard_rules`, `scope`, `tasks`, `approval_gate`, `success_criteria`, `post_mortem`, `non_goals`
- whether a section must be passed through verbatim or may be rendered as extracted facts
- whether the doc is authoritative, historical, prompt-only, or external-workspace-facing
- whether missing sections are fatal or optional

That would let Alfred treat something like a frozen scenario doc, charter doc, kickoff outline, or canonical handover as a known document class rather than as arbitrary prose. The result should be safer selective loading, more stable prompt assembly, and less dependence on frontier-model judgment just to understand Alfred's own planning artifacts.

## Open Questions To Revisit

1. **Where does editorial content live?** The current `SPRINT_GOAL` paragraph carries judgment about what the next phase should and shouldn't include — that is real planning work, not boilerplate. Splitting it into structured fields (proposal B) preserves the judgment but changes its surface. Is that a net win or just relocated complexity?

2. **Manifest authorship.** Who writes the manifest entry for phase N+1? If a frontier model writes it, we have not eliminated the dependency, only shifted it. If a human writes it from the demo plan, what tooling makes that pleasant?

3. **Granularity of "ratified."** Today, "ratified" means "the canonical handover was promoted." Should the manifest mark individual decisions (Phase 1's three frozen specs) as ratified, or only whole phases? The former gives finer-grained scope-carry-forward; the latter is simpler.

4. **Backward compatibility.** Several scripts in `scripts/` (`dogfood_run.py`, `generate_phase7_canonical.py`, etc.) follow the same pattern of hand-edited identity constants. A manifest-driven renderer would either subsume them or coexist with them awkwardly.

5. **Validator coverage of editorial drift.** The biggest current failure mode is "the generated draft mentions the wrong phase or includes deliverables out of scope." A validator can catch the first mechanically; the second requires interpreting prose. How much can be deterministic?

6. **Stale tests.** `test_generate_next_canonical_handover.py` has three failing assertions today (since Phase 2). They are quietly excluded from "Phase 2 acceptance" because they pre-existed. A manifest-driven approach would let those tests be regenerated from the manifest fixture, so phase advances stop creating test rot.

7. **Failed-candidate lifecycle.** Should failed-candidate artifacts have a dedicated validation mode and metadata contract, or should the workflow avoid validating them directly and only validate canonical-target content before archive writeout?

8. **Prompt-budget policy.** Once scope is assembled from multiple ratified artifacts, what is the rule for "full text vs derived summary vs omit as duplicate"? Today that choice is ad hoc and reactive.

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
