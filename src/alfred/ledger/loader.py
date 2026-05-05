"""Phase Ledger YAML loader.

Reads the seed ledger YAML and returns a validated ``PhaseLedger`` model.
Errors surface as ``LedgerLoadError`` with a path-prefixed message so the
caller can show the operator exactly which file failed.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from alfred.ledger.models import PhaseLedger


class LedgerLoadError(Exception):
    """Raised when a ledger YAML file cannot be parsed or validated."""


def load_ledger(path: str | Path) -> PhaseLedger:
    p = Path(path)
    if not p.exists():
        raise LedgerLoadError(f"{p}: file not found")

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LedgerLoadError(f"{p}: invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise LedgerLoadError(
            f"{p}: ledger root must be a mapping, got {type(raw).__name__}"
        )

    try:
        return PhaseLedger.model_validate(raw)
    except ValidationError as exc:
        raise LedgerLoadError(f"{p}: ledger validation failed:\n{exc}") from exc
