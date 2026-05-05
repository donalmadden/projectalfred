# Frontier-model-independence at the seams is a core methodology property

**Status:** accepted (2026-05-01)

The methodology had five declared core properties (document as protocol; checkpoint-gated execution; reasoning/execution isolation; inline post-mortem → forward plan; statelessness by design). In practice, advancing the canonical-handover workflow depended silently on Claude reading the demo plan, the prior handover, and the generator script and patching them into a coherent next-phase identity. When the model got it wrong (stale phase number, missing scope source, sprint goal still describing the previous phase), drafts drifted off-scope. We were marketing "frontier-model-independent at the seams" without having declared it as a property — and the codebase quietly violated it.

We promote frontier-model-independence at the seams to a sixth core property: the protocol's connective tissue (identity, scope-source bindings, ledger data, gate inputs) stays coherent without requiring a smart model. Frontier models do reasoning *inside* a stage; the boundaries between stages are deterministic and human-auditable.

## Considered options

- **Leave it implicit / fold into property #2.** Rejected: property #2 (checkpoint-gated execution) constrains gate evaluation, not the connective tissue between artifacts. The two are orthogonal and conflating them blurs both.
- **Treat it as engineering hygiene, not methodology.** Rejected: the failures it prevents are not implementation bugs, they are violations of the protocol's claim about itself. The paper depends on this distinction.

## Consequences

- Every future design decision must be checked against six properties, not five.
- Several open workflow proposals (phase ledger, structured brief, deterministic context assembly, no-LLM-judge validation chain) are now justified directly by this property rather than by ad-hoc engineering arguments.
- LLM-as-judge solutions are foreclosed in seam-adjacent positions even when they look rigorous.
