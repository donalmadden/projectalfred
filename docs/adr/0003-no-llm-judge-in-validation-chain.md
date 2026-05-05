# No LLM-judge in the validation chain

**Status:** accepted (2026-05-01)

Both pre-flight validators (run before the planner is invoked) and post-generation validators (run on the planner's output before promotion) must contain **zero LLM-judge steps**. Every validator is deterministic code.

The temptation to add an LLM-judge will recur — the obvious failure mode "the planner included a deliverable that's actually phase N+1 work" looks like a job for semantic interpretation, and LLM-as-judge feels rigorous. It is methodologically wrong here. Putting an LLM-judge at "draft generated → draft accepted into protocol" places a smart model at a seam, which property #6 forbids.

Drift that requires semantic interpretation is the **human reviewer's job at the promotion gate**, not a validator's. The mechanical validators free the reviewer to focus on the semantic layer by eliminating the rest.

## Mechanical coverage (deterministic only)

- Pre-flight: scope-source paths exist; carry-forward phase ids exist and are ratified; previous handover's `next_handover_id` matches; no path appears in more than one context role; reference tags parse.
- Post-generation: phase number consistency; `next_handover_id` declared and correct; citation closure (every authoritative-doc reference in output appears in `scope_sources` ∪ `scope_carry_forward`); task closure (output sections ↔ brief task seeds); hard-rule presence (verbatim or declared near-verbatim); reference-tag parsing.

## Considered options

- **(α) Mechanical validators do what they can; semantic drift is the human reviewer's job.** Chosen.
- **(β) Add an LLM-judge with a confidence threshold to catch out-of-scope smuggling.** Rejected. Property #6 violation in the validation chain. Confidence thresholds do not redeem this — a smart model evaluating "is X in scope" is exactly the connective-tissue work the methodology says must not depend on a smart model.

## Consequences

- Coverage of editorial drift has a deterministic ceiling. The promotion gate (human reviewer) is the only place semantic-class drift gets caught. This is acceptable: the methodology already designs human approval into the gate; this constraint clarifies what that approval is *for*.
- Future contributors will propose LLM-judges. This ADR exists so the rejection is a one-line citation, not a re-litigated debate.
