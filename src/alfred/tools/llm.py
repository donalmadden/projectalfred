"""
Provider-agnostic LLM adapter.

Single public function: `complete(prompt, output_schema, provider, model)`.
Returns a validated instance of `output_schema`. Structured output is obtained
via the provider's native tool-use / function-calling mechanism; the model is
forced to emit a single tool call whose input matches `output_schema`. The
result is validated against the Pydantic schema before being returned.

On schema-validation failure, the call is retried up to `max_retries` times
(default 2). Each attempt is logged as an agent invocation via the persistence
tool when `db_path` is supplied.

Provider adapters are selected by dispatch table. Adding a provider means
adding one function and one dispatch entry — nothing else changes.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from alfred.tools import persistence

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when the LLM call fails after all retries."""


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------


def _complete_anthropic(
    prompt: str,
    output_schema: type[BaseModel],
    model: str,
) -> tuple[dict[str, Any], int]:
    """Anthropic adapter. Returns (tool_input_dict, total_tokens)."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set in the environment")

    client = anthropic.Anthropic(api_key=api_key)

    tool_name = "emit_" + output_schema.__name__.lower()
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        tools=[
            {
                "name": tool_name,
                "description": f"Emit a {output_schema.__name__} value.",
                "input_schema": output_schema.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_input: Optional[dict[str, Any]] = None
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            tool_input = dict(block.input)  # type: ignore[attr-defined]
            break
    if tool_input is None:
        raise LLMError("Anthropic response contained no tool_use block")

    usage = getattr(message, "usage", None)
    tokens = 0
    if usage is not None:
        tokens = int(getattr(usage, "input_tokens", 0) or 0) + int(
            getattr(usage, "output_tokens", 0) or 0
        )
    return tool_input, tokens


def _complete_openai(
    prompt: str,
    output_schema: type[BaseModel],
    model: str,
) -> tuple[dict[str, Any], int]:
    """OpenAI adapter using structured outputs (json_schema response format)."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not set in the environment")

    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": output_schema.__name__,
                "schema": output_schema.model_json_schema(),
                "strict": False,
            },
        },
    )

    import json as _json
    content = response.choices[0].message.content
    if not content:
        raise LLMError("OpenAI response contained no content")
    tool_input = _json.loads(content)

    usage = response.usage
    tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
    return tool_input, tokens


_PROVIDERS: dict[str, Callable[[str, type[BaseModel], str], tuple[dict[str, Any], int]]] = {
    "anthropic": _complete_anthropic,
    "openai": _complete_openai,
}

# Task types that route to the cheap classifier tier.
_CLASSIFY_TASKS = {"classify", "judge"}

# Task types that route to the expensive generator tier.
_GENERATE_TASKS = {"plan", "generate", "compile", "retro", "critique"}


def resolve_model(task_type: str, config: Any) -> tuple[str, str]:
    """Return (provider, model) for the given task type.

    When cost_routing is disabled, always returns the default LLM config.
    classify/judge → cheap classifier tier.
    plan/generate/compile/retro/critique → expensive generator tier.
    Unknown task_type → generator tier (with a warning).
    """
    import warnings

    cr = config.cost_routing
    if not cr.enabled:
        return config.llm.provider, config.llm.model

    provider = cr.provider if cr.provider else config.llm.provider

    if task_type in _CLASSIFY_TASKS:
        return provider, cr.classifier_model
    if task_type in _GENERATE_TASKS:
        return provider, cr.generator_model

    warnings.warn(
        f"resolve_model: unknown task_type {task_type!r}; falling back to generator tier",
        stacklevel=2,
    )
    return provider, cr.generator_model


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _describe_schema_fragment(fragment: dict[str, Any]) -> str:
    if "type" in fragment:
        if fragment["type"] == "array":
            item_type = fragment.get("items", {}).get("type", "any")
            return f"array[{item_type}]"
        return str(fragment["type"])
    if "$ref" in fragment:
        return str(fragment["$ref"]).split("/")[-1]
    if "anyOf" in fragment:
        variants = [
            _describe_schema_fragment(option)
            for option in fragment["anyOf"]
            if isinstance(option, dict)
        ]
        return " or ".join(variant for variant in variants if variant)
    return "value"


def _truncate_json(value: dict[str, Any], *, limit: int = 800) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True)
    if len(encoded) <= limit:
        return encoded
    return encoded[: limit - 3] + "..."


def _build_retry_prompt(
    base_prompt: str,
    output_schema: type[BaseModel],
    raw_output: dict[str, Any],
    validation_error: ValidationError,
    *,
    attempt: int,
) -> str:
    schema = output_schema.model_json_schema()
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_lines: list[str] = []
    for name, fragment in properties.items():
        if not isinstance(fragment, dict):
            continue
        requirement = "required" if name in required else "optional"
        field_lines.append(
            f"- `{name}` ({requirement}): {_describe_schema_fragment(fragment)}"
        )

    error_lines: list[str] = []
    for issue in validation_error.errors():
        location = ".".join(str(part) for part in issue.get("loc", ())) or "<root>"
        message = issue.get("msg", "validation error")
        error_lines.append(f"- `{location}`: {message}")

    correction = [
        "STRUCTURED OUTPUT CORRECTION:",
        f"The previous tool payload for `{output_schema.__name__}` failed validation on attempt {attempt + 1}.",
        "You MUST call the tool again with a JSON object that satisfies the schema.",
        "Do not return an empty object. If uncertain, provide best-effort values instead of omitting required fields.",
        "Validation failures:",
        *error_lines,
        "Schema fields:",
        *field_lines,
        "If an optional object is unknown, use `null`. If an optional list is unknown, use `[]`.",
        "Previous invalid tool payload:",
        "```json",
        _truncate_json(raw_output),
        "```",
    ]
    return base_prompt + "\n\n" + "\n".join(correction)


def complete(
    prompt: str,
    output_schema: type[T],
    provider: str,
    model: str,
    *,
    max_retries: int = 2,
    db_path: Optional[str] = None,
) -> T:
    """Complete a prompt into a validated instance of `output_schema`.

    Retries up to `max_retries` times on Pydantic validation failure. Each
    attempt is logged via persistence if `db_path` is supplied. Raises
    `LLMError` after all retries are exhausted or if the provider is unknown.
    """
    adapter = _PROVIDERS.get(provider)
    if adapter is None:
        raise LLMError(
            f"Unknown provider {provider!r}. Known: {sorted(_PROVIDERS)}"
        )

    input_hash = _hash(f"{provider}:{model}:{prompt}")
    last_error: Optional[Exception] = None
    last_raw: Optional[dict[str, Any]] = None
    current_prompt = prompt

    for attempt in range(max_retries + 1):
        start = time.monotonic()
        try:
            raw, tokens = adapter(current_prompt, output_schema, model)
            last_raw = raw
            validated = output_schema.model_validate(raw)
            latency_ms = int((time.monotonic() - start) * 1000)
            if db_path is not None:
                persistence.record_agent_invocation(
                    db_path,
                    agent_name=f"llm:{provider}:{model}",
                    input_hash=input_hash,
                    output_hash=_hash(validated.model_dump_json()),
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                )
            return validated
        except ValidationError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            last_error = exc
            if db_path is not None:
                persistence.record_agent_invocation(
                    db_path,
                    agent_name=f"llm:{provider}:{model}",
                    input_hash=input_hash,
                    latency_ms=latency_ms,
                    error=f"validation:attempt={attempt}",
                )
            if attempt < max_retries and last_raw is not None:
                current_prompt = _build_retry_prompt(
                    prompt,
                    output_schema,
                    last_raw,
                    exc,
                    attempt=attempt,
                )
            continue

    raw_suffix = ""
    if last_raw is not None:
        raw_suffix = f" Last raw output: {_truncate_json(last_raw)}"
    raise LLMError(
        "Failed to produce schema-valid output after "
        f"{max_retries + 1} attempts: {last_error}{raw_suffix}"
    )
