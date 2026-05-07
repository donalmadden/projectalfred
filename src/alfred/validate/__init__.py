"""Deterministic validation for the handover generator.

Two gates are exposed:

- :func:`run_preflight` — Slice 7's pre-LLM gate. Hard-fails before any
  planner call when scope, continuity, ledger, role, or reference-tag
  invariants are violated.
- :func:`validate_postgen` — Slice 8's post-LLM gate. Hard-fails after
  the planner returns a draft and before the generator promotes it to
  the canonical output path.

Public surface is intentionally minimal: callers compose the inputs and
invoke the orchestrator, then format the resulting errors with the
matching ``format_*`` helper. The individual ``check_*`` helpers are
reachable via the submodules for isolated testing but are not
re-exported from the package root, to keep the wiring contract explicit.

``format_errors`` re-exports the preflight formatter for backwards
compatibility; postgen ships its own :func:`format_postgen_errors` to
avoid an ambiguous overload across two error types.
"""
from alfred.validate.postgen import (
    PostgenError,
    PostgenResult,
    validate_postgen,
)
from alfred.validate.postgen import format_errors as format_postgen_errors
from alfred.validate.preflight import (
    CHECK_IDS,
    CheckId,
    PreflightError,
    format_errors,
    run_preflight,
)

__all__ = [
    "CHECK_IDS",
    "CheckId",
    "PostgenError",
    "PostgenResult",
    "PreflightError",
    "format_errors",
    "format_postgen_errors",
    "run_preflight",
    "validate_postgen",
]
