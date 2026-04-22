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
