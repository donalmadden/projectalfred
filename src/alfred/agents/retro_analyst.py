"""
Retro Analyst — read-only pattern extraction across the handover corpus.

Methodology property 3 (reasoning/execution isolation): this agent is on the
reasoning side and is structurally read-only. It must not import or call
persistence write functions, github_api, or any other write-path tool.
All output is analysis and observation for human review — no write operations
of any kind.

Velocity trend analysis is computed deterministically from the velocity data
before the LLM call; the LLM is used only for qualitative pattern extraction
and the retrospective narrative.
"""
from __future__ import annotations

from typing import Optional

from alfred.schemas.agent import (
    RetroAnalystInput,
    RetroAnalystOutput,
    VelocityTrend,
)
from alfred.tools import llm


# ---------------------------------------------------------------------------
# Deterministic velocity trend computation
# ---------------------------------------------------------------------------


def _compute_velocity_trend(velocity_data: list) -> Optional[VelocityTrend]:
    if not velocity_data:
        return VelocityTrend(
            average_completion_rate=0.0,
            trend_direction="insufficient_data",
            sprints_analysed=0,
        )

    rates = [v.completion_rate for v in velocity_data]
    avg = sum(rates) / len(rates)
    n = len(rates)

    if n < 2:
        direction = "insufficient_data"
    else:
        recent = rates[-min(3, n):]
        early = rates[: min(3, n)]
        recent_avg = sum(recent) / len(recent)
        early_avg = sum(early) / len(early)
        delta = recent_avg - early_avg
        if abs(delta) < 0.05:
            direction = "stable"
        elif delta > 0:
            direction = "improving"
        else:
            direction = "declining"

    return VelocityTrend(
        average_completion_rate=round(avg, 4),
        trend_direction=direction,
        sprints_analysed=n,
    )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _build_prompt(input: RetroAnalystInput) -> str:
    parts: list[str] = []

    parts.append(
        "You are the Retro Analyst agent. Your role is READ-ONLY pattern extraction. "
        "You must not produce instructions to write, modify, or execute anything. "
        "All output is for human review only.\n\n"
        "Identify recurring patterns (failures, successes, anti-patterns, risks) "
        "across the handover corpus. Produce a retrospective summary and list of "
        "top risks and successes."
    )

    if input.analysis_focus:
        parts.append(f"ANALYSIS FOCUS:\n{input.analysis_focus}")

    if input.velocity_data:
        rows = "\n".join(
            f"  Sprint {v.sprint_number}: {v.points_completed}/{v.points_committed} "
            f"({v.completion_rate:.0%})"
            for v in input.velocity_data[-10:]
        )
        parts.append(f"VELOCITY DATA (last 10 sprints):\n{rows}")

    if input.metrics_history:
        for mh in input.metrics_history[:3]:
            vals = ", ".join(f"{label}={val}" for label, val in mh.values[-5:])
            parts.append(f"METRIC [{mh.metric_name}]: {vals}")

    if input.handover_corpus_chunks:
        chunks = []
        for c in input.handover_corpus_chunks[:8]:
            chunks.append(f"  [{c.document_id} / {c.section_header}]\n  {c.content[:400]}")
        parts.append("HANDOVER CORPUS (top RAG hits):\n\n" + "\n\n".join(chunks))

    parts.append(
        "TASK:\n"
        "1. List recurring patterns (each with type, description, frequency estimate, "
        "   example handover ids, and optional recommendation).\n"
        "2. Write a retrospective_summary (2–4 sentences).\n"
        "3. List top_risks (max 5 strings).\n"
        "4. List top_successes (max 5 strings).\n"
        "5. Set handovers_analysed to the count of distinct document_ids in the corpus."
    )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_retro_analyst(
    input: RetroAnalystInput,
    *,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    db_path: Optional[str] = None,
) -> RetroAnalystOutput:
    """Analyse the handover corpus for patterns and trends. Read-only — no writes of any kind."""
    velocity_trend = _compute_velocity_trend(input.velocity_data)
    prompt = _build_prompt(input)

    raw: RetroAnalystOutput = llm.complete(
        prompt,
        RetroAnalystOutput,
        provider=provider,
        model=model,
        db_path=db_path,
    )

    return RetroAnalystOutput(
        pattern_report=raw.pattern_report,
        velocity_trend=velocity_trend,
        retrospective_summary=raw.retrospective_summary,
        handovers_analysed=raw.handovers_analysed,
        top_risks=raw.top_risks,
        top_successes=raw.top_successes,
    )
