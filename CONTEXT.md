# ProjectAlfred — Domain Context

This file is the canonical glossary for ProjectAlfred. Terms are added lazily as they get resolved in design discussions. Implementation detail does not belong here — only language meaningful to a domain expert (someone reasoning about the methodology, not the code).

## Glossary

### Seam

A connective point between protocol artifacts or stages — for example, the boundary between phase N's canonical handover and phase N+1's planner inputs, or between a scope-source declaration and the grounding block consumed by the planner. Distinct from the *content* of any stage.

Core property #6 requires seams to be **deterministic and human-auditable**. Frontier models do reasoning *inside* a stage; they do not hold seams together. If a smart model is silently keeping a seam coherent (e.g. by re-reading two docs and patching a script to match), that is a violated seam, not an acceptable convenience.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling.

### Phase Ledger

A declarative YAML file enumerating known phases and their identifying data (handover id, title, status, scope sources, scope-carry-forward). Used by the canonical-handover renderer as input.

The ledger is a **derived view**, not a protocol artifact. Authority flows: canonical handover → ledger entry, never the reverse. Any ratified phase's ledger row must be reproducible by reading that phase's canonical handover. The only ledger row that contains *non-derivable* content is the next, unratified phase — and that content is a seed which the next handover ratifies, after which the seed becomes derivable too.

Distinct from `docs/DOCS_MANIFEST.yaml`, which governs the docs registry (a different concern). Do not call the phase ledger a "manifest" — that word is taken and overloading it would blur the protocol/scaffolding boundary.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling.

### Brief

The structured editorial seed for an unratified phase, stored as that phase's ledger entry. Contains the human-authored content the planner expands into a canonical handover: title, goal, `hard_rules`, `tasks` (ordered `{id, title, intent}` triples), `out_of_scope`, `definition_of_done`, `followups_from_prior_phase`, plus the mechanical fields (`handover_id`, `previous_handover`, `scope_sources`, `scope_carry_forward`).

The brief is **not** the handover. The brief commits the human to a phase shape and task decomposition; the planner expands each task seed into Implementation / Verification / CHECKPOINT bodies, renders `WHAT EXISTS TODAY` from grounding sources, and threads hard rules through. Task slicing and protocol invariants (hard rules) are human decisions, never model-invented — that is the line property #6 draws here.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling.

### Context Roles

A canonical-handover renderer assembles planner context as a **typed bundle**, not an opaque blob. Every input doc has exactly one role:

- **`scope`** — authoritative for *this* phase. Rendered full-text. Planner cites these.
- **`carry_forward`** — authoritative-but-frozen, inherited from a prior ratified phase. Rendered full-text if a non-handover doc (charter, plan, scenario), or as a deterministic summary if a canonical handover. The summary surfaces committed surface area, not fine-grained content.
- **`continuity`** — the immediately-previous canonical handover. Always rendered as a deterministic summary (extracted level-2 sections: CONTEXT, WHAT EXISTS TODAY, WHAT THIS PHASE PRODUCES, TASK OVERVIEW).

Dedup precedence when a path appears in more than one role: `scope` > `carry_forward` > `continuity`. The lower role drops.

Three roles is a methodology-level commitment, not a config knob. Adding a fourth role requires re-arguing rendering and dedup rules.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling.

### Doc Class

A declared kind of planning document (e.g. `canonical_handover`). A doc class carries a **section contract**: the required level-2 headings, the semantic class of each (`continuity`, `current_state`, `protocol_invariant`, `deliverables`, `task_index`, `non_goals`, `retrospective`, etc.), and the rendering treatment of each (verbatim vs extracted-bullets).

Doc classes live in `docs/DOCS_MANIFEST.yaml`. Today only `canonical_handover` is declared, because it is the only class a deterministic extractor depends on. Other planning docs (charter, plan, scenario, outline) remain conventionally structured but uncontracted. New classes are added only when something downstream needs to consume them deterministically.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling. Deferred (iii) variant for non-handover classes recorded in `docs/active/FUTURE_ARCHITECTURE_DISCUSSIONS.md`.

### Reference Tags

Inline markdown annotations that mark a path as something other than "a real file in this repo today." Two canonical forms:

- `[future-doc: <path>]` — the path lives in an external or future workspace (e.g. the demo workspace), and is named intentionally. Never resolved against this repo.
- `[future-path: <path>]` — same, for non-doc paths (config files, source files in external workspaces).

The exact bracket-and-prefix form is canonical and must not vary. The validator parses these deterministically; no smart-model judgment is involved in interpreting them.

Tags live in document prose, not in side-manifests. That keeps property #1 intact — the document is self-describing about what its references mean. Moving tags into a manifest would make the document non-self-describing and is therefore disallowed.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling. A possible third tag `[deferred-doc:]` (will exist in this repo, not yet) is held until a concrete case requires it.

### No-LLM-Judge Constraint

The validation chain (pre-flight + post-generation) must contain **zero LLM-judge steps**. Every validator is deterministic code. Drift that requires semantic interpretation ("is this deliverable actually in scope?") is the human reviewer's job at the promotion gate, not a validator's.

This is a property #6 commitment. Putting an LLM-judge in the validator chain would place a smart model at a seam (between "draft generated" and "draft accepted into protocol"), which is exactly what property #6 forbids. The temptation will recur because LLM-as-judge feels rigorous; it is methodologically wrong here.

Mechanical validators handle: phase consistency, id sequencing, citation closure, task closure, hard-rule presence, reference-tag parsing. Beyond that, the human at the approval gate handles editorial judgment.

Resolved: 2026-05-01, in HANDOVER_WORKFLOW_DISCUSSION grilling.
