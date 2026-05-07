"""Deterministic pre-flight validation for the handover generator.

Public surface is intentionally minimal: callers compose the inputs and
invoke :func:`run_preflight`, then format the resulting errors with
:func:`format_errors`. The individual ``check_*`` helpers are reachable
via ``alfred.validate.preflight`` for isolated testing but are not
re-exported from the package root, to keep the wiring contract explicit.
"""
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
    "PreflightError",
    "format_errors",
    "run_preflight",
]
