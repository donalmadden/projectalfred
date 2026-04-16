"""
Provider-agnostic LLM adapter.

Phase 4 implementation will:
- Support multiple providers behind a single interface
- Return structured output validated against a Pydantic schema
- Log token usage and latency
"""
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def complete(prompt: str, output_schema: Type[T], provider: str, model: str) -> T:
    raise NotImplementedError
