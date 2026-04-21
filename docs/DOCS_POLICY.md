# Docs Lifecycle Policy

This document defines how the `docs/` corpus should be managed going forward.

The immediate goal is to reduce ambiguity for humans and for automation:

- RAG/indexing should not treat every markdown file as equally trustworthy.
- The planner should not cite stale drafts, archived notes, or scratch output as authoritative protocol.
- Historical material should remain available without polluting canonical generation.

No existing documents are moved by this change. The folders below are created now so later moves can be deliberate and low-risk.

## Folder Meanings

### `docs/canonical/`

- Purpose: canonical handovers and other phase artifacts that define historical protocol state.
- Retrieval: yes
- Citation: yes
- Authority: yes

### `docs/protocol/`

- Purpose: stable, long-lived methodology and system-governing documents.
- Retrieval: yes
- Citation: yes
- Authority: yes or near-authoritative depending on the document

### `docs/active/`

- Purpose: temporary or adjacent design briefs that materially guide the current cleanup or generation pipeline.
- Retrieval: yes
- Citation: selective
- Authority: no by default

### `docs/archive/`

- Purpose: superseded drafts, failed candidates, exploratory notes, and historical supporting material kept for traceability.
- Retrieval: no by default
- Citation: no by default
- Authority: no

### `docs/scratch/`

- Purpose: local test output, experiment notes, and disposable working files.
- Retrieval: no
- Citation: no
- Authority: no

## Machine Rules

The intended machine contract is:

1. Only docs marked `indexed: true` in `docs/DOCS_MANIFEST.yaml` should enter the default RAG corpus.
2. Only docs marked `citable: true` should be treated as valid planner reference documents.
3. Only docs marked `authoritative: true` should be treated as protocol truth sources.
4. `archive` and `scratch` content remain readable for humans but should be excluded from default generation and validation flows.

## Current Migration Strategy

Phase 1:

- Create lifecycle folders.
- Classify the current corpus in a manifest.
- Keep existing file paths stable.

Phase 2:

- Update indexing / citation code to consume the manifest.
- Move files into their target folders once link churn is understood and references can be updated safely.

## Practical Heuristics

- If a doc governs current behavior, it belongs in `canonical/` or `protocol/`.
- If a doc explains an in-flight cleanup, it belongs in `active/`.
- If a doc exists mostly to remember history, it belongs in `archive/`.
- If a doc is ad hoc or disposable, it belongs in `scratch/`.
