# CODEX.md

Working agreement for Codex when operating in this repository.

This file complements `CLAUDE.md`. If they ever conflict, follow the stricter rule.

## Purpose

Codex should be a careful teammate in this repo: incremental, transparent, and safe around shared work.

## Standing Guidance

1. **Do not delete or replace shared tests as a first response to a tooling problem.**
   Treat test-harness, environment, and dependency issues as separate from application correctness unless the code is clearly at fault.

2. **Prefer the smallest reversible patch.**
   In watched or shared files, make local edits rather than rewriting the file wholesale unless explicitly asked.

3. **Debug the environment before changing functional code.**
   If tests hang, commands fail, or a harness behaves strangely, isolate the problem with minimal reproductions first.

4. **Ask before large refactors in contested areas.**
   If a fix would substantially reshape a shared file, pause and confirm before proceeding.

5. **Protect team trust.**
   When a previous step caused confusion or churn, bias toward conservative changes and clearer commentary on the next step.

6. **Keep methodology and environment concerns separate.**
   Do not weaken Alfred's architectural rules just to make local tooling or tests pass.

## Test Editing Rules

- Preserve the intent of existing tests unless the user explicitly asks to change it.
- Do not convert broad API-level tests into narrower unit tests just because the harness is inconvenient.
- If a test harness itself is broken, document the cause and propose the narrowest fix.

## Shared File Safety

- `tests/` is a shared surface: patch surgically.
- `docs/ALFRED_HANDOVER_*.md` are coordination artifacts: never rewrite casually.
- `src/alfred/schemas/` is protocol-critical: additive changes preferred unless explicitly required.

## Default Recovery Pattern

When something behaves unexpectedly:

1. Reproduce it in the smallest possible way.
2. Determine whether the fault is in environment, harness, or product code.
3. Change only the layer that is actually broken.
4. Summarize the reasoning clearly before taking any higher-impact step.
