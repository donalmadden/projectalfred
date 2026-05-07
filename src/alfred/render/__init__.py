"""Deterministic renderers for canonical-handover generator inputs.

Slice 6 seam: replaces hand-edited identity constants in
``scripts/generate_next_canonical_handover.py`` with a pure function over
``PhaseLedger`` + active ``Brief``. No LLM, no network, no implicit state.
"""
from alfred.render.handover_inputs import (
    ArgparseDefaults,
    HandoverInputs,
    NoActivePhaseError,
    render_handover_inputs,
    select_active_phase,
)

__all__ = [
    "ArgparseDefaults",
    "HandoverInputs",
    "NoActivePhaseError",
    "render_handover_inputs",
    "select_active_phase",
]
