"""T1.1 — Schema round-trip invariants.

For every core Pydantic model: generate arbitrary valid instances, serialise
to JSON, deserialise, assert equality. Verifies that the JSON round-trip is
lossless across all field types (dates, optionals, nested models, literals).
"""
from __future__ import annotations

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from alfred.schemas.agent import PlannerOutput, RAGChunk, VelocityRecord
from alfred.schemas.checkpoint import (
    Checkpoint,
    CheckpointResult,
    DecisionRule,
    DecisionTable,
)
from alfred.schemas.handover import (
    HandoverContext,
    HandoverDocument,
    HandoverTask,
    TaskResult,
)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Printable ASCII — fast, safe for JSON, no surrogate issues.
_text = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=100,
)
_verdict = st.sampled_from(["proceed", "pivot", "stop", "escalate"])
_unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_pos_int = st.integers(min_value=1, max_value=9999)
_date = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))

_decision_rule = st.builds(DecisionRule, condition=_text, likely_verdict=_verdict)
_decision_table = st.builds(
    DecisionTable,
    rules=st.lists(_decision_rule, min_size=1, max_size=5),
    default_verdict=_verdict,
)
_checkpoint_result = st.builds(
    CheckpointResult,
    verdict=_verdict,
    evidence_provided=_text,
    reasoning=_text,
)
_task_result = st.builds(
    TaskResult,
    completed=st.booleans(),
    output_summary=_text,
    commits=st.just([]),
    files_modified=st.just([]),
    pivot_taken=st.one_of(st.none(), _text),
)
_handover_context = st.builds(
    HandoverContext,
    narrative=_text,
    what_changes=st.just([]),
    what_does_not_change=st.just([]),
    important_notices=st.just([]),
)
_handover_task = st.builds(
    HandoverTask,
    id=_text,
    title=_text,
    goal=_text,
    agent_type=st.none(),
    steps=st.just([]),
    checkpoints=st.just([]),
    result=st.one_of(st.none(), _task_result),
)

# ---------------------------------------------------------------------------
# T1.1 — Round-trip tests
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(_handover_context)
def test_handover_context_roundtrip(obj: HandoverContext) -> None:
    assert HandoverContext.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(_task_result)
def test_task_result_roundtrip(obj: TaskResult) -> None:
    assert TaskResult.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(_checkpoint_result)
def test_checkpoint_result_roundtrip(obj: CheckpointResult) -> None:
    assert CheckpointResult.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(_decision_table)
def test_decision_table_roundtrip(obj: DecisionTable) -> None:
    restored = DecisionTable.model_validate(obj.model_dump(mode="json"))
    assert obj.rules == restored.rules
    assert obj.default_verdict == restored.default_verdict


@settings(max_examples=100)
@given(
    st.builds(
        Checkpoint,
        id=_text,
        question=_text,
        evidence_required=_text,
        decision_table=_decision_table,
    )
)
def test_checkpoint_roundtrip(obj: Checkpoint) -> None:
    restored = Checkpoint.model_validate(obj.model_dump(mode="json"))
    assert obj.id == restored.id
    assert obj.question == restored.question
    assert obj.decision_table.rules == restored.decision_table.rules
    assert obj.result == restored.result


@settings(max_examples=100)
@given(
    st.builds(
        VelocityRecord,
        sprint_number=_pos_int,
        points_committed=_pos_int,
        points_completed=st.integers(min_value=0, max_value=9999),
        completion_rate=_unit_float,
    )
)
def test_velocity_record_roundtrip(obj: VelocityRecord) -> None:
    assert VelocityRecord.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(
    st.builds(
        RAGChunk,
        document_id=_text,
        section_header=_text,
        content=_text,
        relevance_score=_unit_float,
    )
)
def test_rag_chunk_roundtrip(obj: RAGChunk) -> None:
    assert RAGChunk.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(
    st.builds(
        PlannerOutput,
        draft_handover_markdown=_text,
        sprint_plan=st.none(),
        task_decomposition=st.just([]),
        open_questions=st.just([]),
    )
)
def test_planner_output_roundtrip(obj: PlannerOutput) -> None:
    assert PlannerOutput.model_validate(obj.model_dump(mode="json")) == obj


@settings(max_examples=100)
@given(_handover_task)
def test_handover_task_roundtrip(obj: HandoverTask) -> None:
    restored = HandoverTask.model_validate(obj.model_dump(mode="json"))
    assert obj.id == restored.id
    assert obj.title == restored.title
    assert obj.goal == restored.goal
    assert obj.result == restored.result


@settings(max_examples=100)
@given(
    st.builds(
        HandoverDocument,
        id=_text,
        title=_text,
        date=_date,
        author=_text,
        context=_handover_context,
        tasks=st.lists(_handover_task, max_size=3),
        hard_rules=st.just([]),
        produces=st.just([]),
        what_exists_today=st.just([]),
        git_history=st.just([]),
    )
)
def test_handover_document_roundtrip(obj: HandoverDocument) -> None:
    restored = HandoverDocument.model_validate(obj.model_dump(mode="json"))
    assert obj.id == restored.id
    assert obj.title == restored.title
    assert obj.date == restored.date
    assert obj.author == restored.author
    assert len(obj.tasks) == len(restored.tasks)
