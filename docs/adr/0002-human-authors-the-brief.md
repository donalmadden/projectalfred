# The unratified phase's brief is human-authored

**Status:** accepted (2026-05-01)

The canonical-handover renderer needs a structured editorial seed for the next phase: title, goal, hard rules, task seeds (id + title + intent), out-of-scope, definition-of-done, follow-ups from the prior phase. We call this the **brief**, and it is written by a human (the methodology owner) — not by a frontier model, not by a deterministic extractor.

The brief commits the human to a phase shape and a task decomposition. The renderer pulls mechanical fields (handover ids, paths, scope-source paths) from the phase ledger automatically. The planner then expands each task seed into Implementation / Verification / CHECKPOINT bodies, threads hard rules through, and renders WHAT EXISTS TODAY from grounding sources.

## Considered options

- **(a) Human authors the brief.** Chosen.
- **(b) A deterministic extractor authors the brief from the demo plan.** Deferred. Requires the demo-plan doc class to honor an explicit section contract, which is not in scope yet. When that contract exists, an extractor can pre-populate brief fields *as a suggestion the human ratifies* — humans stay in the loop because of property #6.
- **(c) A frontier model authors the brief inside a structured-output schema.** Rejected. The schema catches malformed output, not wrong output (wrong phase number that typechecks, scope source that exists but isn't right for this phase). Property #6 says the seam is deterministic; option (c) keeps a smart model at the seam and dresses it up as guardrails.

## Consequences

- Task decomposition is *the* core planning act and stays a human decision. Letting the planner pick task slices was tempting (smart-model-inside-a-stage = allowed) but the slicing decision is editorial, not expansion, so it belongs in the brief.
- Hard rules are protocol invariants and are never model-invented; they are typed in by the human in the brief.
- The grilling-loop authoring mode (logged in `docs/active/FUTURE_ARCHITECTURE_DISCUSSIONS.md`) is the long-run authoring UX for briefs: a frontier model interviews the human field-by-field, but the human ratifies every answer. That keeps the smart model at the *input* of the seam, not at the seam itself.
