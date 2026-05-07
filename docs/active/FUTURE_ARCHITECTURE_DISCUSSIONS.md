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
