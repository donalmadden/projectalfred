"""Typed three-role planner-context bundle.

See `CONTEXT.md` for the canonical role/dedup/rendering rules.
"""
from alfred.context.bundle import (
    ROLES,
    ContextBundle,
    ContextItem,
    DedupResult,
    RenderedItem,
    Role,
    summarize_canonical_handover,
)

__all__ = [
    "ROLES",
    "ContextBundle",
    "ContextItem",
    "DedupResult",
    "RenderedItem",
    "Role",
    "summarize_canonical_handover",
]
