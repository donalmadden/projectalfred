# Demo Project Layout

This document freezes the initial filesystem shape of the external demo project workspace Alfred operates against during the blank-project kickoff demo.

## Frozen Layout

```text
<demo-project-root>/
├── README.md
└── docs/
    ├── CHARTER.md
    └── handovers/
```

## File And Directory Purposes

- `<demo-project-root>/README.md` - one-paragraph project description shown to a human opening the repository for the first time.
- `<demo-project-root>/docs/` - Alfred's home inside the demo project and the primary source-of-truth docs surface.
- `<demo-project-root>/docs/CHARTER.md` - the kickoff charter Alfred consumes at run start.
- `<demo-project-root>/docs/handovers/` - empty at kickoff and reserved for Alfred-authored handover artifacts.

## README.md Text

`Customer Onboarding Portal is a greenfield product workspace for a financial-services team building a self-service flow for new customers to verify identity, upload KYC documents, and activate their account without branch support; the project starts intentionally blank so Alfred can turn the charter into governed kickoff documentation and a first backlog proposal.`

## CHARTER.md Source

`<demo-project-root>/docs/CHARTER.md` is a verbatim copy of [CUSTOMER_ONBOARDING_PORTAL_CHARTER.md](./CUSTOMER_ONBOARDING_PORTAL_CHARTER.md). Phase 2 workspace initialisation must copy that file's content exactly rather than rewriting or summarising it.

## Directory Decisions

- `docs/handovers/` is intentionally empty at kickoff.
- No `.gitkeep` is part of the frozen layout. Phase 2's workspace initialiser must create `docs/handovers/` at runtime so the visible project shape remains identical to the Phase 0 freeze.
- `docs/CURRENT_STATE.md` [future-doc: optional demo-workspace file; currently deferred] is not included in this demo slice. The kickoff handover's `## WHAT EXISTS TODAY` section is the explicit "what exists" anchor, so `CURRENT_STATE.md` remains deferred unless a later phase reopens that decision.
- Alfred's first persisted artifact path is `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md`.
- No `docs/canonical/` directory exists inside the demo project; canonical handover history in this repository is separate from the demo workspace.
