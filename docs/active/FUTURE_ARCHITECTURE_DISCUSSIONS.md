# Future Architecture Discussions

## Purpose

This brief records architecture discussions that appear promising and directionally aligned with Alfred's original vision, but are **not yet canonized** as settled protocol. It exists to keep high-value ideas visible without prematurely rewriting the canonical architecture.

## Current Discussion

### Candidate direction

The leading candidate product-shape discussion is:

> Alfred lives in the `docs/` folder of any code project.

In that model:

- Alfred is embedded directly in the project workspace
- markdown is the primary human/agent coordination surface
- `ALFRED_HANDOVER_n.md` remains the governed execution/history artifact
- adjacent docs can evolve into project-wiki surfaces such as charter, current state, decisions, runbook, and backlog
- GitHub Projects and similar tools become downstream projections rather than the source of truth

## Handover And Wiki Relationship

One promising refinement inside this direction is:

> The `ALFRED_HANDOVER_n.md` series should form the versioned spine of a project wiki, not replace the wiki with one endlessly mutable page.

That split appears practical:

- handovers act as the append-only execution journal
- adjacent docs act as the current-state wiki surface
- humans review the same markdown medium either way
- Alfred can update or propose updates to the current-state docs based on completed handovers

This keeps the handover series strong at auditability, traceability, and governed execution while still giving developers the "wiki-like" project surface they expect.

## Why This Fits The Existing Thesis

This direction is highly compatible with the strongest existing Alfred ideas:

- the document is the protocol
- state should live in inspectable artifacts rather than hidden agent memory
- reasoning and execution remain separated
- checkpoints and approvals continue to gate consequential actions
- git history plus docs together remain the durable project memory

In other words, this is not a repudiation of Alfred's architecture. It is a possible refinement of where that architecture should physically live.

## Why It Is Attractive

### 1. It meets developers where they already work

Developers across experience levels are already comfortable with:

- repository folders
- markdown docs
- git diffs
- pull requests
- runbooks and design notes

Placing Alfred inside `docs/` reduces the adoption burden and makes the system legible without a new UI.

### 2. It makes the "document as protocol" claim more practical

If Alfred's governing artifacts sit in the project's own `docs/` folder, then:

- the project memory is already where the team expects to find it
- handovers become easier to review in pull requests
- context survives across tools and across sessions

### 3. It makes GitHub Projects an optional projection

This is strategically helpful:

- boards are useful for visualising work
- boards are poor primary memory surfaces
- docs are better suited to durable reasoning, decisions, pivots, and handoffs

That suggests a healthier split:

- `docs/` is the source-of-truth coordination surface
- GitHub Projects is one downstream execution/visibility surface

## Why It Is Not Yet Canonical

This direction is not yet canonized because it changes Alfred's current embodied shape in meaningful ways.

### Low departure at the methodology level

At the ideas level, this is a small departure:

- it reinforces document-mediated coordination
- it reinforces externalized memory
- it reinforces human-readable state

### Moderate departure at the canonical embodiment level

At the implementation and canonical-architecture level, it is a more material shift:

- current canonical docs and code still describe Alfred primarily around Alfred's own repo-local corpus
- current runtime paths do not yet treat arbitrary project-local `docs/` folders as the natural home for Alfred artifacts
- current demo/build plans are only now being adjusted to this model

So this is best treated as an active architecture discussion and likely next-phase refinement, not already-settled doctrine.

## Candidate Project Layout

One plausible future Alfred-managed project layout is:

```text
my-project/
  src/
  tests/
  docs/
    CHARTER.md
    CURRENT_STATE.md
    DECISIONS.md
    RUNBOOK.md
    BACKLOG.md
    handovers/
      ALFRED_HANDOVER_1.md
      ALFRED_HANDOVER_2.md
```

In this model:

- `docs/handovers/` is the governed execution history
- the other docs act as current-state wiki/materialized views
- Alfred updates or proposes updates to those surfaces as execution proceeds

## Open Questions

These questions should be answered before canonization:

1. Should handovers live directly under `docs/` or under `docs/handovers/`?
2. Which wiki surfaces are mandatory versus optional for a new Alfred-managed project?
3. How much of the "current wiki" should Alfred update automatically versus propose for approval?
4. How should project-local docs interact with Alfred's own internal canonical corpus?
5. What is the minimal API/CLI change needed to support project-local `docs/` as Alfred's home without breaking current repo assumptions?
6. How should the wiki-view documents be regenerated or updated from completed handovers without losing human edits?

## Recommended Stance For Now

- Treat `docs/`-native Alfred as the leading candidate product direction
- Use it in the active demo/build planning where it clarifies the product story
- Do not yet rewrite canonical architecture documents as though the decision is final
- Revisit canonization once one practical end-to-end slice has been proven

## Bottom Line

The most promising future shape for Alfred is not "another agent UI" and not "a GitHub Project automation tool." It is:

> a document-mediated coordination layer embedded in the `docs/` folder of a code project, where markdown files act as the shared protocol between humans and AI tools.

That idea is strong enough to pursue, but not yet mature enough to declare as finalized canonical architecture.

---

## Parked: Socratic grilling as a first-class authoring mode

**Captured:** 2026-05-01, during the `HANDOVER_WORKFLOW_DISCUSSION.md` grilling session.

The Socratic grilling pattern — walking the user branch-by-branch down a decision tree, asking one question at a time with a recommended answer attached, updating `CONTEXT.md` inline as terms resolve, and offering ADRs only when a decision is hard-to-reverse + surprising + a real trade-off — has been concretely valuable for designing Alfred itself.

It is a candidate first-class authoring mode in Alfred:

- "Draft a brief by grilling me" alongside Alfred's other authoring entry points.
- Applies to stories, plans, and canonical handovers — anywhere a human-authored editorial seed feeds the protocol.
- Closes the property #6 gap on brief authoring: instead of a frontier model writing a brief from prose, a frontier model interviews the human to extract the brief field-by-field, with the human ratifying every answer. The smart model is at the *input* of the seam, not at the seam itself.
- Output is a structured brief object (the YAML the renderer consumes), plus inline updates to CONTEXT.md and any ADRs the conversation crystallises.

Not for now. Phase 5 just landed and there is workflow work ahead of this. Recorded so it does not get lost.

---

## Parked: Section contracts for non-handover doc classes

**Captured:** 2026-05-01, during the `HANDOVER_WORKFLOW_DISCUSSION.md` grilling session.

The lightweight section contract landing now (proposal J option (ii)) covers only the `canonical_handover` doc class — because that is the only class an extractor currently depends on. Charter, plan, scenario, outline, kickoff-outline, and operational-runbook docs remain conventionally structured but **not formally contracted**.

The deferred work (proposal J option (iii)): declare section contracts for the other planning-doc classes too. Each contract names required headings, semantic classes (`hard_rules`, `scope`, `tasks`, `approval_gate`, `success_criteria`, `post_mortem`, `non_goals`), verbatim-vs-extracted treatment, and authoritative-vs-historical-vs-prompt-only-vs-external-workspace-facing role.

Trigger to revisit: when a deterministic extractor needs to read a non-handover doc class to populate something downstream — most likely the **(b)-later** path for ledger authorship, where an extractor pre-populates ledger fields from the demo plan. At that point, the demo-plan doc class needs a contract. Not before.

Don't expand scope here pre-emptively. Each contract added is a real commitment to a heading vocabulary and a maintenance burden on doc authors.

---

## Parked: Agent tuning framework for heterogeneous coding agents

**Captured:** 2026-05-07, from internal product feedback during active handover-generation work.

The underlying observation is strong: not every coding agent has the same notion of "done," the same appetite for verbosity, or the same tolerance for ambiguity. A handover that is sufficient for one executor may be under-specified for another. Conversely, a handover that is maximally explicit for a slower, more verification-heavy agent may drown a faster executor in prompt bulk and reduce implementation quality rather than improve it.

The recent paired-agent workflow has already exposed a promising pattern:

- one agent executes against the handover
- another agent independently judges whether the task is actually complete
- the disagreement between those two judgments surfaces missing constraints, weak completion criteria, or ambiguous instructions

That suggests Alfred may need a **tuning framework**, but the durable tuning target is probably **not** "verbosity" in isolation. The more durable unit is the contract between:

- the handover / brief / checkpoint wording
- the executor profile's implementation behavior
- the reviewer profile's evidence threshold for calling work complete

## Candidate Direction

Treat tuning as a first-class, document-mediated layer rather than a pile of ad hoc per-agent prompt patches.

One plausible shape:

1. **Profile the execution style explicitly**

   Record a small number of tuning dimensions for an agent profile, for example:

   - verbosity preference
   - ambiguity tolerance
   - required verification depth
   - patch granularity
   - escalation threshold
   - appetite for local inference vs explicit instructions

   The important part is that these are **auditable knobs**, ideally living in `configs/` or planning artifacts, not hidden in an opaque system prompt.

2. **Run a done-gap comparison loop**

   After an executor claims completion, a separate reviewer profile compares:

   - what the handover said
   - what the executor changed
   - what evidence was produced
   - whether the checkpoint should actually be considered satisfied

   The output is not just `PROCEED / PIVOT / STOP`, but also a structured account of the **done-gap**:

   - which requirements were under-specified
   - which checks the executor assumed rather than proved
   - which parts of the handover invited drift
   - which instructions were too terse or too sprawling for the profile used

3. **Patch the handover contract before patching agent-specific prompts**

   The highest-leverage repair path is:

   - improve the handover / brief / checkpoint wording first
   - improve shared protocol instructions second
   - add agent-profile-specific prompt deltas only when the gap is truly profile-specific

   This matters because a recurring disagreement between executor and reviewer often means the protocol artifact is underspecified, not merely that one model needs a longer reminder.

4. **Keep the framework vendor-neutral**

   The framework should talk about **agent profiles** or **execution/review styles**, not hard-code assumptions about one named tool. Alfred's methodology should survive model churn.

## Why This Is Attractive

### 1. It fits Alfred's methodology better than raw prompt tweaking

This direction preserves the strongest Alfred idea: the document is the protocol. Instead of burying the fix in tool-specific instructions, it tries to improve the shared artifact that every cold-start session is supposed to rely on.

### 2. It turns recurring execution/review disagreement into product signal

Right now, when one agent says "done" and another says "not done," that can feel like friction. In a tuning framework, that disagreement becomes a measurement surface:

- where are handovers too vague?
- where are checkpoints too permissive?
- where is the reviewer asking for evidence the executor was never told to produce?

That is valuable feedback for the methodology itself.

### 3. It acknowledges real differences between agent profiles

This is the part of the request that is probably right in practice:

- some agents do better with compressed instructions
- some agents need more explicit decomposition
- some agents infer missing steps well
- some agents need stronger verification scaffolding

Pretending those differences do not exist just pushes the tuning burden into repeated manual repair work.

## Risks And Failure Modes

### 1. Overfitting to the current agent pair

The biggest risk is designing a framework that really means "make agent A and reviewer B agree," then discovering it does not generalize to other agents or future model updates.

### 2. Smuggling protocol logic back into hidden prompts

If Alfred calls this a tuning framework but implements it mostly as prompt folklore, then it violates the spirit of document-mediated coordination. The tuning layer must remain inspectable.

### 3. Confusing verbosity with completeness

Longer instructions are not automatically better instructions. More prose can increase ambiguity, hide the real acceptance criteria, and make it harder for the executor to locate the actual stop conditions.

### 4. Profile sprawl

If every agent/tool combination gets its own bespoke profile, the system becomes harder to reason about than the problem it is solving.

## Recommended Stance For Now

- Treat this as a **promising architecture direction**, not yet canonized.
- If implemented, start with a **small, explicit profile schema** and a **done-gap report** rather than a large tuning surface.
- Prefer improving **handover / brief / checkpoint instructions first** whenever the disagreement is really about missing contract language.
- Use agent-specific prompt deltas only for residual profile differences that remain after the shared artifact is tightened.

This means the strongest part of the request is not "add more model-specific prompts." The strongest part is:

> when executor and reviewer disagree about what "done" means, treat that as evidence that the protocol artifact itself may need repair.

## Trigger To Revisit

This should move from parked discussion to active design when one or more of the following becomes common:

1. The same handover repeatedly passes with one executor profile and fails with another.
2. Repair prompts keep repeating the same "you did not prove X" or "the checkpoint did not ask for evidence Y" pattern.
3. We want deterministic selection between a "lean executor" profile and a "thorough executor" profile without rewriting the whole handover each time.
4. Cross-agent review becomes a standard part of Alfred's execution loop rather than an ad hoc human practice.

## Bottom Line

This is a good idea, with one important refinement:

> Alfred should tune the protocol artifact first, and the agent profile second.

The comparison loop between executor-complete and reviewer-complete looks genuinely valuable. But if Alfred implements that insight well, the main output should be **better handovers and checkpoints**, not just better per-agent repair prompts.

---

## Parked: Treat canonical handover generation as a deterministic build pipeline, not a monolithic script

**Captured:** 2026-05-07, after the Slice 6/7 generator work, the `ALFRED_HANDOVER_19` bootstrap, and the closeout/prep step that moved the live seed to `ALFRED_HANDOVER_20`.

This is an extremely opinionated proposal because the recent work surfaced the same conclusion from multiple angles:

- Slice 6 proved that renderer-derived identity belongs behind a deterministic seam.
- Slice 7 proved that pre-flight validation belongs behind a deterministic seam.
- The bootstrap of `ALFRED_HANDOVER_19` proved that the **authoring packet / context-input planning seam** is still too implicit and too phase-specific.
- The closeout step for `ALFRED_HANDOVER_20` proved that **ratification and next-phase seeding are still manual protocol-adjacent surgery**, not a first-class operation.
- The Hugging Face / RAG behavior proved that Alfred's current "generate a canonical handover" path is still too exposed to **incidental runtime concerns** (network metadata checks, whole-corpus re-indexing) that should be adapters, not methodology.

The conclusion is not "add a few more helper functions."

The conclusion is:

> `scripts/generate_next_canonical_handover.py` has become a shallow, overloaded module whose interface is now carrying too many independent concerns. It should stop being the place where Alfred's generation methodology *lives* and become a thin adapter over a deterministic build pipeline.

### The evidence is no longer subtle

At the time of this note:

- `scripts/generate_next_canonical_handover.py` is **1172 lines**
- `tests/test_scripts/test_generate_next_canonical_handover.py` is **788 lines**
- `src/alfred/tools/handover_authoring_context.py` is **339 lines**
- `src/alfred/render/handover_inputs.py` is **263 lines**
- `src/alfred/validate/preflight.py` is **294 lines**

That is not automatically bad. Big files can still be deep. But the recent bug history says this one is not deep enough:

- stale phase-specific authoring selectors blocked `ALFRED_HANDOVER_19` bootstrap
- Check A's original wording was too weak because the *real* `scope` inputs were not the same thing as direct `scope_sources`
- Check C originally matched an instructional inline example of `**next_handover_id:** ...` instead of the real metadata line
- phase closeout to the next handover still required coordinated edits across:
  - canonical handover post-mortem
  - docs manifest registration
  - phase ledger ratification + seed row
  - real-ledger tests
- the RAG embedder path is cache-backed in practice, but still shaped like a network-capable runtime path when the methodology really wants a stable local adapter

The pattern is the important part:

- the methodology is getting stronger
- the script is accumulating too many places where the methodology is *realized informally*

That is the definition of a shallow module under pressure.

## Blunt Diagnosis

Today, Alfred's handover-generation stack is really **five modules pretending to be one**:

1. **Identity compiler**

   Render `handover_id`, `previous_handover`, display title, sprint goal, grounding, and CLI defaults from `PhaseLedger` + `Brief`.

   This is now reasonably explicit in `src/alfred/render/handover_inputs.py`.

2. **Context-input planner**

   Decide which docs become `scope`, which prior phases become `carry_forward`, which handover becomes `continuity`, which reference-tag sources matter, and which authoring selectors define the authoritative packet.

   This is still too implicit and too script-bound.

3. **Validation pipeline**

   Pre-flight before planner call, post-generation before promotion, and deterministic formatting of failures.

   Slice 7 made pre-flight real. Slice 8 is the obvious continuation.

4. **Prompt/retrieval adapter**

   Build the authoring packet, manage RAG indexing/retrieval, load the embedder, and constrain context volume.

   This is not methodology, but it materially affects generation reliability.

5. **Phase transition / ratification workflow**

   Close out a completed canonical handover, promote it into docs registry + ledger truth, and seed the next planning row.

   This is currently under-tooled and therefore brittle.

These deserve **named seams** and **small interfaces**. Right now they are still coupled primarily through one script and a cluster of tests.

## The Proposal

Promote handover generation to an explicit deterministic build pipeline with four primary seams:

1. **`HandoverBuildPlan` seam**
2. **`ValidationReport` seam**
3. **`PromotionResult` seam**
4. **`PhaseTransitionPlan` seam**

And then make `scripts/generate_next_canonical_handover.py` a thin adapter over those seams.

### 1. Introduce a real `HandoverBuildPlan`

This is the highest-leverage missing module.

The build plan should be the one place that answers:

- Which phase is active?
- What is the source canonical handover?
- What are the output and failed-candidate paths?
- Which docs are the real `scope` inputs?
- Which phase ids are `carry_forward`?
- Which path/role assignments will actually feed `ContextBundle`?
- Which markdown files are reference-tag sources?
- Which authoring selectors define the authoritative packet?

One plausible shape:

```python
@dataclass(frozen=True)
class HandoverBuildPlan:
    inputs: HandoverInputs
    source_path: Path
    output_path: Path
    failed_output_path: Path
    scope_doc_paths: tuple[Path, ...]
    carry_forward_phase_ids: tuple[int, ...]
    role_assignments: tuple[tuple[str, str], ...]
    reference_tag_sources: tuple[Path, ...]
    authoring_selection_specs: tuple[DocumentSelectionSpec, ...]
```

Strong opinion:

- `run_generator_preflight()` should not be inventing a quasi-plan ad hoc.
- `load_demo_plan_context()` should not be reading a separate, partially-overlapping notion of scope truth.
- `build_planner_context()` should not be downstream from a plan it cannot name.

All three should consume the same `HandoverBuildPlan`.

If Alfred does not do this, every new validator slice will keep rediscovering the same "what are the real inputs?" question in a different local form.

### 2. Make validation stages consume the build plan, not ad hoc parameter lists

Slice 7's pre-flight surface is already much better than what came before, but it still takes a fairly wide argument list.

That is acceptable as an intermediate step. It is not the final deep shape.

The deeper module is:

- `build_handover_plan(...) -> HandoverBuildPlan`
- `run_preflight(plan) -> ValidationReport`
- `run_postgen(plan, candidate) -> ValidationReport`

Where `ValidationReport` is explicit and stable:

```python
@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors: tuple[ValidationError, ...]
    warnings: tuple[ValidationWarning, ...]
```

Strong opinion:

- Alfred should stop passing long validator argument lists around once two validator stages exist.
- The build plan is the test surface.
- Validators should consume declared build intent, not reconstruct intent from ambient script state.

### 3. Freeze the generator script into an orchestration adapter

The generator script should eventually read like:

1. parse args
2. load ledger
3. build handover plan
4. run pre-flight
5. if dry-run: render dry-run report from plan
6. run planner / critique loop
7. run post-generation validation
8. promote or archive failed candidate

Nothing else.

That means:

- no selector folklore at top-level script scope except through a plan builder
- no phase-specific packet logic embedded directly in `main()`
- no validation-specific branching logic beyond "run report, format report, branch on report"
- no retrieval/indexing policy embedded in the promotion flow itself

This is not an aesthetic preference. It is a leverage preference.

The current script still has too much **interface bulk**:

- identity defaults
- scope planning
- authoring packet construction
- context bundle assembly
- pre-flight
- RAG indexing
- planner execution
- candidate validation
- promotion logic

That is too much methodology in one interface, even if the implementation is careful.

### 4. Split prompt/retrieval concerns behind an adapter with offline-first semantics

The recent Hugging Face behavior is a warning.

Even when the model artifacts are cached locally, Alfred still *looks* like a runtime that may need the network during generation. That is the wrong dependency profile for protocol generation.

Recommended stance:

- treat embedding model access as an **adapter**
- make it **offline-first by default once the cache is warm**
- stop rebuilding the Chroma index on every run unless either:
  - docs inventory changed materially
  - embedding model changed

Concrete direction:

- use `SentenceTransformer(..., local_files_only=True)` once the model is expected to be present
- allow an explicit "warm cache" or "refresh model" workflow separately from canonical handover generation
- fingerprint the indexed docs set + embedding model, and skip destructive re-index when unchanged

Strong opinion:

> Canonical handover generation should not be a "maybe the internet works today" workflow.

If the network is needed, that should be an explicit cache-warming step, not an incidental property of the main path.

### 5. Promote phase closeout / next-phase seeding to a first-class operation

The move from `ALFRED_HANDOVER_19` to `ALFRED_HANDOVER_20` required:

- filling post-mortem
- registering the handover in `DOCS_MANIFEST.yaml`
- ratifying the phase row in `PHASE_LEDGER.yaml`
- adding the next planning row
- updating the real-ledger tests
- re-checking continuity metadata

That is too protocol-adjacent to remain a manual ritual forever.

Alfred needs a `PhaseTransitionPlan` or equivalent seam that makes these operations inspectable and repeatable.

Not necessarily fully automated immediately. But at minimum:

- one deterministic report of "what must change to ratify phase N"
- one deterministic report of "what the next seed row for phase N+1 should be"
- one place that checks whether the closeout is internally coherent

Strong opinion:

> "Finish the handover, then manually remember the four other places truth must move" is exactly the kind of seam drift Alfred claims to protect against.

### 6. Treat authoring-packet selection as a planning concern, not script trivia

The bootstrap failure around stale Slice-6 selectors is one of the most important lessons from the recent work.

The bad pattern was:

- the ledger/brief said one thing
- the generator's packet selectors still said another
- the dry-run identity looked right
- the real generation path still failed or drifted

That means the **authoring packet selection plan** is now a first-class concern.

Recommended direction:

- keep section contracts narrow; do not rush to contract every doc class
- but move authoring-packet selector intent into a named plan module rather than letting it sit as top-level script constants forever
- make it testable as "for active phase X, which source docs and section paths are authoritative inputs?"

This is where Alfred should be opinionated:

- **the active slice title should drive the active plan section**
- **continuity selectors should target stable semantic sections, not brittle prose variants**
- **if a selector becomes phase-specific in a way that cannot be expressed as stable semantics, that is a design smell, not a local exception**

## What Not To Do

This proposal is intentionally strong because there are several attractive wrong turns.

### 1. Do not solve this by adding more helper functions to the script and calling it done

That is just object-level tidying. The problem is seam ownership, not line wrapping.

### 2. Do not move the protocol into hidden prompts or hidden runtime state

If the build plan or phase-transition plan is real, it must be inspectable in code and test surfaces.

### 3. Do not generalize all doc classes immediately

The right immediate deepening target is the handover build pipeline, not a sweeping schema program for every markdown file in the repo.

### 4. Do not add more validators without first naming the thing they validate

Once post-generation validators land, the shared build plan becomes non-negotiable. Otherwise Alfred will have pre-flight and post-generation stages each reconstructing input truth differently.

### 5. Do not let retrieval/runtime concerns leak upward into methodology claims

RAG, embedding caches, Chroma, and packet sizing are implementation concerns behind an adapter. They matter, but they should not dictate the protocol surface.

## Migration Path

This should not be done as a grand rewrite. The right migration is staged.

### Step 1 — Extract `HandoverBuildPlan` with no behavior change

- move the current pre-flight input planning into a named module
- have `run_generator_preflight()` and `load_demo_plan_context()` consume it
- keep CLI behavior unchanged

### Step 2 — Make post-generation validation consume the same plan

- Slice 8 should not invent a parallel notion of generator truth
- if a candidate fails, the failed-candidate decision should still cite the same build plan inputs

### Step 3 — Introduce an offline-first retrieval adapter

- local-files-only model loading after cache warm
- stable index fingerprint
- skip destructive re-index when unchanged

### Step 4 — Introduce a deterministic phase-closeout helper/report

- not necessarily full automation on day one
- but at least one authoritative place to compute:
  - manifest registration delta
  - ledger ratification delta
  - next planning-row skeleton
  - continuity metadata expectations

### Step 5 — Shrink the top-level script aggressively

Success is when `generate_next_canonical_handover.py` becomes boring.

That is a compliment.

## Why This Is Worth Doing

### 1. It increases locality

The recent bugs were not "hard algorithms." They were distributed truth problems.

Deepening the pipeline would concentrate:

- phase identity truth
- scope-input truth
- validation input truth
- promotion truth

into named modules instead of one script plus several tests plus human memory.

### 2. It increases leverage

Once a real build plan exists:

- new validators become easier to add
- dry-run becomes more meaningful
- closeout becomes easier to mechanize
- test suites can assert one object instead of shadowing behavior from many call sites

### 3. It improves AI navigability without depending on AI heroics

This is exactly the kind of depth Alfred should want:

- a smaller, clearer interface for the next agent
- fewer places where a model must "just know" which values are supposed to line up
- more deterministic reports and less patch-by-intuition surgery

## Risks

### 1. Over-abstracting too early

If Alfred introduces five new types and none of them become real seams, this becomes ceremony.

Mitigation:

- extract the build plan first
- prove two real consumers use it
- only then deepen further

### 2. Creating a second source of truth

The build plan must remain derived from ledger + manifest + docs, not become a parallel protocol artifact.

### 3. Treating phase closeout automation as protocol authority

Any closeout helper must remain a scaffold that updates derived views and draft docs. Canonical handovers stay the protocol surface.

## Recommended Stance For Now

- Treat this as the **leading architecture direction** for the next generation of Alfred's handover workflow.
- Do **not** canonize it as settled doctrine yet.
- But also: do **not** keep adding major features to `generate_next_canonical_handover.py` as if the current shape were healthy.

The strongest version of the recommendation is:

> Freeze the monolith. Extract the build plan. Make validators and packet assembly consume it. Then continue.

If Alfred ignores this, the likely future is not one catastrophic failure. It is a steady stream of "small" selector mismatches, validation drift, test shadowing, closeout omissions, and runtime surprises that collectively make the workflow feel more magical and less governed than the methodology promises.

## Bottom Line

Slice 6 and Slice 7 were a success. They also made the next deepening target obvious.

The next architecture move should **not** be "add more logic to the generator script."

It should be:

> turn canonical handover generation into an explicit deterministic build pipeline, and demote the script to a thin adapter over that pipeline.
