"""T1.3 — Tool contract invariants.

Three boundary types are tested:
1. Pydantic model boundaries — invalid types are rejected before execution.
2. llm.complete() — raises LLMError on unknown provider or exhausted retries.
3. API layer — invalid request shapes produce FastAPI 422 responses.
"""
from __future__ import annotations

from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from alfred.schemas.agent import PlannerOutput, RAGChunk
from alfred.schemas.handover import TaskResult
from alfred.tools import llm
from alfred.tools.llm import LLMError

# ---------------------------------------------------------------------------
# T1.3a — Pydantic model boundaries
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(st.one_of(st.lists(st.text()), st.fixed_dictionaries({"k": st.text()})))
def test_rag_chunk_rejects_non_numeric_relevance_score(bad_value: Any) -> None:
    """RAGChunk.relevance_score rejects list/dict values that cannot coerce to float."""
    with pytest.raises(ValidationError):
        RAGChunk.model_validate(
            {
                "document_id": "d",
                "section_header": "s",
                "content": "c",
                "relevance_score": bad_value,
            }
        )


@settings(max_examples=100)
@given(st.fixed_dictionaries({"nested": st.text()}))
def test_task_result_rejects_dict_as_completed(bad_value: dict) -> None:
    """TaskResult.completed rejects dict values that cannot coerce to bool."""
    with pytest.raises(ValidationError):
        TaskResult.model_validate({"completed": bad_value, "output_summary": "x"})


# ---------------------------------------------------------------------------
# T1.3b — LLMError propagation
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=50,
    )
)
def test_llm_complete_raises_error_for_unknown_provider(provider: str) -> None:
    """llm.complete() raises LLMError immediately for any unregistered provider."""
    assume(provider not in llm._PROVIDERS)
    with pytest.raises(LLMError, match="Unknown provider"):
        llm.complete(
            prompt="test",
            output_schema=PlannerOutput,
            provider=provider,
            model="m",
        )


def test_llm_error_raised_after_retries_exhausted() -> None:
    """complete() raises LLMError when all attempts produce schema-validation failures."""
    original = dict(llm._PROVIDERS)

    # Provider returns a dict that is missing required PlannerOutput fields.
    def bad_schema_provider(
        prompt: str, output_schema: Any, model: str
    ) -> tuple[dict[str, Any], int]:
        return {"unexpected_field": True}, 0

    llm._PROVIDERS["bad_schema"] = bad_schema_provider
    try:
        with pytest.raises(LLMError):
            llm.complete(
                prompt="test",
                output_schema=PlannerOutput,
                provider="bad_schema",
                model="m",
                max_retries=1,
            )
    finally:
        llm._PROVIDERS.clear()
        llm._PROVIDERS.update(original)


# ---------------------------------------------------------------------------
# T1.3c — API layer 422 on invalid request shapes
# ---------------------------------------------------------------------------


def test_compile_endpoint_returns_422_for_missing_fields() -> None:
    """POST /compile with missing required fields returns HTTP 422."""
    from fastapi.testclient import TestClient

    from alfred.api import app, set_config
    from alfred.schemas.config import AlfredConfig

    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    set_config(cfg)
    try:
        client = TestClient(app)
        response = client.post("/compile", json={"invalid_field": "payload"})
        assert response.status_code == 422
    finally:
        set_config(None)  # type: ignore[arg-type]


@settings(max_examples=100)
@given(
    st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=50,
    )
)
def test_compile_endpoint_returns_422_for_non_json_string_body(bad_body: str) -> None:
    """POST /compile with a plain text body (not JSON object) returns HTTP 422."""
    from fastapi.testclient import TestClient

    from alfred.api import app, set_config
    from alfred.schemas.config import AlfredConfig

    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    set_config(cfg)
    try:
        client = TestClient(app)
        response = client.post(
            "/compile",
            content=bad_body.encode(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
    finally:
        set_config(None)  # type: ignore[arg-type]
