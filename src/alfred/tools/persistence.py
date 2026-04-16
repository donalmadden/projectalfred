"""
SQLite operational bookkeeping.

Phase 4 implementation will:
- Store sprint metadata and velocity history
- Log agent invocation traces (input hash, output hash, tokens, latency)
- Record checkpoint evaluation history
"""
from alfred.schemas.agent import VelocityRecord


def record_velocity(db_path: str, record: VelocityRecord) -> None:
    raise NotImplementedError


def get_velocity_history(db_path: str, sprint_count: int) -> list[VelocityRecord]:
    raise NotImplementedError
