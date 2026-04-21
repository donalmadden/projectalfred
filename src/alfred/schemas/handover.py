"""
Handover document schema — the canonical representation of a handover document.

The handover document is the control surface of the system (methodology property 1).
This schema bridges two worlds: structured enough for agents to parse deterministically,
narrative enough for humans to read and approve.
"""
from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Sub-models: populated at document creation time
# ---------------------------------------------------------------------------


class ReferenceDocument(BaseModel):
    path: str
    note: Optional[str] = None


class TaskSummaryRow(BaseModel):
    """A row in the task overview table."""

    number: str
    description: str
    deliverable: str
    checkpoint_decides: Optional[str] = None


class VerificationBlock(BaseModel):
    """Shell commands used to verify a completed task."""

    commands: str
    expected_output: Optional[str] = None


class InlinePostMortem(BaseModel):
    """A post-mortem section embedded mid-document after a checkpoint STOP."""

    trigger: str  # e.g. "CHECKPOINT-3"
    root_cause: str
    evidence: str
    pivot_description: str


# ---------------------------------------------------------------------------
# Sub-models: populated after execution
# ---------------------------------------------------------------------------


class TaskResult(BaseModel):
    """What actually happened when a task was executed."""

    completed: bool
    output_summary: str
    commits: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    pivot_taken: Optional[str] = None


# ---------------------------------------------------------------------------
# Task — the unit of work
# ---------------------------------------------------------------------------


class HandoverTask(BaseModel):
    """A single numbered task within a handover document.

    Each task is self-contained: a reader who sees only this task should be
    able to execute it without reading the rest of the document.
    """

    id: str  # "0", "0.5", "1", "2", etc.
    title: str
    goal: str
    agent_type: Optional[str] = None  # "planner" | "story_generator" | "retro_analyst"
    steps: list[str] = Field(default_factory=list)
    verification: Optional[VerificationBlock] = None
    commit_message: Optional[str] = None
    checkpoints: list["Checkpoint"] = Field(default_factory=list)

    # Populated after execution
    result: Optional[TaskResult] = None


# ---------------------------------------------------------------------------
# Context — the "READ THIS FIRST" block
# ---------------------------------------------------------------------------


class HandoverContext(BaseModel):
    """Everything the reader must know before touching anything."""

    narrative: str
    what_changes: list[str] = Field(default_factory=list)
    what_does_not_change: list[str] = Field(default_factory=list)
    important_notices: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Post-mortem — populated after execution (methodology property 4)
# ---------------------------------------------------------------------------


class CritiqueEntry(BaseModel):
    """One iteration of the planner–judge revision cycle."""

    iteration: int
    quality_score: float
    validation_issues: list[str]
    # Deterministic validator findings (formatted via Finding.format()) recorded
    # alongside the judge's validation_issues so the post-mortem captures both
    # feedback channels for the iteration. Empty when no validators were run.
    deterministic_findings: list[str] = Field(default_factory=list)
    revised_at: Optional[str] = None  # ISO timestamp


class PostMortem(BaseModel):
    """Inline failure analysis feeding the next iteration.

    Deliberately embedded in the execution artifact, not a separate process
    (methodology property 4: inline post-mortem → forward plan).
    """

    summary: str
    root_causes: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    forward_plan: Optional[str] = None
    inline_post_mortems: list[InlinePostMortem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HandoverDocument — the document IS the state (property 1 + 5)
# ---------------------------------------------------------------------------


class HandoverDocument(BaseModel):
    """The canonical representation of a single handover document.

    Five methodology properties are enforced structurally:
    1. Document as protocol — this IS the state, not a cache of it.
    2. Checkpoint-gated execution — checkpoints are first-class fields in tasks.
    3. Reasoning/execution isolation — enforced via agent boundary schemas.
    4. Inline post-mortem — PostMortem is embedded, not a separate artifact.
    5. Statelessness by design — a fresh agent can reconstruct full context from this alone.
    """

    schema_version: str = "1.0"
    id: str
    title: str
    date: date
    author: str
    previous_handover: Optional[str] = None
    supersedes: list[str] = Field(default_factory=list)
    baseline_state: Optional[str] = None
    reference_documents: list[ReferenceDocument] = Field(default_factory=list)

    context: HandoverContext
    hard_rules: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    task_overview: list[TaskSummaryRow] = Field(default_factory=list)
    tasks: list[HandoverTask] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)

    # Alfred canonical current-state fields (optional, additive).
    # Permissive parsing means absence of these fields never breaks legacy or
    # BOB-style documents — they simply remain at their empty defaults.
    what_exists_today: list[str] = Field(default_factory=list)
    git_history: list[str] = Field(default_factory=list)

    # Populated during critique loop (Phase 5)
    critique_history: list[CritiqueEntry] = Field(default_factory=list)

    # Populated after execution
    post_mortem: Optional[PostMortem] = None
    next_handover_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_markdown(self) -> str:
        """Produce human-readable markdown in BOB_HANDOVER style."""
        parts: list[str] = []

        # Title
        parts.append(f"# {_format_document_title(self.id, self.title)}\n")

        # Context / metadata block
        parts.append("## CONTEXT — READ THIS FIRST\n")
        parts.append(f"**Document Date:** {self.date.isoformat()}")
        if self.previous_handover:
            parts.append(f"**Previous Handover:** {self.previous_handover}")
        if self.supersedes:
            parts.append(f"**Supersedes:** {', '.join(self.supersedes)}")
        if self.baseline_state:
            parts.append(f"**Baseline State:** {self.baseline_state}")
        if self.reference_documents:
            parts.append("**Reference Documents:**")
            for ref in self.reference_documents:
                note = f" ({ref.note})" if ref.note else ""
                parts.append(f"- `{ref.path}`{note}")
        parts.append(f"**Author:** {self.author}")
        parts.append("")

        # Context narrative
        if self.context.narrative:
            parts.append("---\n")
            parts.append("## WHAT THIS TASK DOES\n")
            parts.append(self.context.narrative)
            parts.append("")

        if self.context.what_changes:
            parts.append("**What changes:**")
            for i, item in enumerate(self.context.what_changes, 1):
                parts.append(f"{i}. {item}")
            parts.append("")

        if self.context.what_does_not_change:
            parts.append(
                "**What does NOT change:** "
                + ", ".join(f"`{x}`" for x in self.context.what_does_not_change)
            )
            parts.append("")

        if self.context.important_notices:
            parts.append("---\n")
            parts.append("## IMPORTANT\n")
            for notice in self.context.important_notices:
                parts.append(notice)
                parts.append("")

        # WHAT EXISTS TODAY (Alfred canonical section)
        if self.git_history or self.what_exists_today:
            parts.append("---\n")
            parts.append("## WHAT EXISTS TODAY\n")
            if self.git_history:
                parts.append("### Git History\n")
                parts.append("```")
                parts.extend(self.git_history)
                parts.append("```")
                parts.append("")
            for item in self.what_exists_today:
                parts.append(f"- {item}")
            if self.what_exists_today:
                parts.append("")

        # Hard rules
        if self.hard_rules:
            parts.append("---\n")
            parts.append("## HARD RULES\n")
            for i, rule in enumerate(self.hard_rules, 1):
                parts.append(f"{i}. {rule}")
            parts.append("")

        # What this produces
        if self.produces:
            parts.append("---\n")
            parts.append("## WHAT THIS HANDOVER PRODUCES\n")
            for item in self.produces:
                parts.append(f"- {item}")
            parts.append("")

        # Task overview table
        if self.task_overview:
            parts.append("---\n")
            parts.append("## TASK OVERVIEW\n")
            has_cp = any(row.checkpoint_decides for row in self.task_overview)
            if has_cp:
                parts.append("| # | Task | Deliverable | Checkpoint decides |")
                parts.append("|---|---|---|---|")
                for row in self.task_overview:
                    cp = row.checkpoint_decides or ""
                    parts.append(f"| {row.number} | {row.description} | {row.deliverable} | {cp} |")
            else:
                parts.append("| # | Task | Deliverable |")
                parts.append("|---|---|---|")
                for row in self.task_overview:
                    parts.append(f"| {row.number} | {row.description} | {row.deliverable} |")
            parts.append("")

        # Individual tasks
        for task in self.tasks:
            parts.append("---\n")
            parts.append(f"## TASK {task.id} — {task.title}\n")
            if task.goal:
                parts.append(task.goal)
                parts.append("")
            if task.steps:
                for i, step in enumerate(task.steps, 1):
                    parts.append(f"{i}. {step}")
                parts.append("")
            if task.verification:
                parts.append("### Verification\n")
                parts.append("```bash")
                parts.append(task.verification.commands)
                parts.append("```")
                if task.verification.expected_output:
                    parts.append(f"\n**Expected:** {task.verification.expected_output}")
                parts.append("")
            if task.commit_message:
                parts.append(f"**Commit message:** `{task.commit_message}`\n")
            for cp in task.checkpoints:
                parts.extend(_render_checkpoint(cp))
            if task.result:
                parts.extend(_render_task_result(task.result))

        # Anti-patterns
        if self.anti_patterns:
            parts.append("---\n")
            parts.append("## WHAT NOT TO DO\n")
            for i, item in enumerate(self.anti_patterns, 1):
                parts.append(f"{i}. {item}")
            parts.append("")

        # Post-mortem
        if self.post_mortem:
            parts.append("---\n")
            parts.append("## POST-MORTEM\n")
            parts.append(self.post_mortem.summary)
            parts.append("")
            if self.post_mortem.root_causes:
                parts.append("**Root causes:**")
                for rc in self.post_mortem.root_causes:
                    parts.append(f"- {rc}")
                parts.append("")
            if self.post_mortem.what_worked:
                parts.append("**What worked:**")
                for item in self.post_mortem.what_worked:
                    parts.append(f"- {item}")
                parts.append("")
            if self.post_mortem.what_failed:
                parts.append("**What failed:**")
                for item in self.post_mortem.what_failed:
                    parts.append(f"- {item}")
                parts.append("")
            if self.post_mortem.forward_plan:
                parts.append("**Forward plan:**")
                parts.append(self.post_mortem.forward_plan)
                parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def from_markdown(cls, text: str, document_id: Optional[str] = None) -> "HandoverDocument":
        """Parse a handover document from markdown into the schema.

        Best-effort parser that handles the common BOB_HANDOVER structure.
        Fields that cannot be reliably parsed are left at their defaults.
        Parse failures are non-fatal — the document is always returned.
        """
        lines = text.splitlines()

        # 1. Title
        title_line = next((ln for ln in lines if ln.startswith("# ")), "")
        parsed_id, parsed_title, parsed_author = _parse_title_line(title_line)
        doc_id = document_id or parsed_id

        # 2. Metadata key-value pairs (bold markdown: **Key:** value)
        meta = _extract_metadata_block(text)

        doc_date = _parse_date(meta.get("document date") or meta.get("date", ""))
        author = meta.get("author", parsed_author) or parsed_author
        previous = meta.get("previous handover") or None
        supersedes_raw = meta.get("supersedes", "")
        supersedes = _parse_supersedes(supersedes_raw)
        baseline = meta.get("baseline state") or meta.get("baseline performance") or None

        # Reference documents (bullet list under **Reference Documents:**)
        ref_docs = _extract_reference_documents(text)

        # 3. Split into level-2 sections
        sections = _split_level2_sections(text)

        context = _parse_context_section(sections)
        hard_rules = _parse_list_section(sections, {"hard rules"})
        produces = _parse_list_section(sections, {"what this handover produces", "what this produces"})
        anti_patterns = _parse_list_section(sections, {"what not to do"})
        task_overview = _parse_task_overview(sections)
        tasks = _parse_tasks(sections)
        post_mortem = _parse_post_mortem_section(sections)
        what_exists_today, git_history = _parse_what_exists_today(sections)

        return cls(
            id=doc_id,
            title=parsed_title,
            date=doc_date or date.today(),
            author=author,
            previous_handover=previous,
            supersedes=supersedes,
            baseline_state=baseline,
            reference_documents=ref_docs,
            context=context,
            hard_rules=hard_rules,
            produces=produces,
            task_overview=task_overview,
            tasks=tasks,
            anti_patterns=anti_patterns,
            post_mortem=post_mortem,
            what_exists_today=what_exists_today,
            git_history=git_history,
        )


# ---------------------------------------------------------------------------
# Deferred import for Checkpoint (avoids circular at module load)
# ---------------------------------------------------------------------------

from alfred.schemas.checkpoint import Checkpoint  # noqa: E402

HandoverTask.model_rebuild()
HandoverDocument.model_rebuild()


# ---------------------------------------------------------------------------
# Private rendering helpers
# ---------------------------------------------------------------------------


def _format_document_title(doc_id: str, title: str) -> str:
    """Produce e.g. \"Bob's Handover Document #36 — Hyperparameter Sweep\"."""
    parts = doc_id.split("_HANDOVER_")
    if len(parts) == 2:
        subject = parts[0].title()
        number = parts[1]
        return f"{subject}'s Handover Document #{number} — {title}"
    return f"{doc_id} — {title}"


def _render_checkpoint(cp: "Checkpoint") -> list[str]:

    lines: list[str] = []
    lines.append(f"### {cp.id}\n")
    lines.append(f"**Question:** {cp.question}\n")
    lines.append(f"**Evidence required:** {cp.evidence_required}\n")
    if cp.decision_table and cp.decision_table.rules:
        lines.append("| Observation | Likely call |")
        lines.append("|---|---|")
        for rule in cp.decision_table.rules:
            lines.append(f"| {rule.condition} | {rule.likely_verdict.upper()} |")
        lines.append("")
    lines.append("**STOP HERE.** Wait for direction before continuing.\n")
    if cp.result:
        lines.append(f"**Verdict:** `{cp.result.verdict}`")
        lines.append(f"**Evidence:** {cp.result.evidence_provided}")
        lines.append(f"**Reasoning:** {cp.result.reasoning}")
        lines.append("")
    return lines


def _render_task_result(result: TaskResult) -> list[str]:
    lines: list[str] = []
    status = "COMPLETE" if result.completed else "INCOMPLETE"
    lines.append(f"\n**Result:** {status}")
    lines.append(result.output_summary)
    if result.commits:
        lines.append("**Commits:** " + ", ".join(f"`{c}`" for c in result.commits))
    if result.pivot_taken:
        lines.append(f"**Pivot:** {result.pivot_taken}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Private parsing helpers
# ---------------------------------------------------------------------------


def _parse_title_line(line: str) -> tuple[str, str, str]:
    """Return (id, title, author) from the document title line."""
    text = line.lstrip("#").strip()

    # Pattern: "Bob's Handover Document #36 — Title"
    m = re.match(r"(\w+)'s Handover Document #(\w+)\s*[—–-]+\s*(.*)", text)
    if m:
        author = m.group(1)
        number = m.group(2)
        title = m.group(3).strip()
        return f"{author.upper()}_HANDOVER_{number}", title, author

    # Pattern: "BOB HANDOVER 44 — Title"
    m = re.match(r"([A-Z]+)\s+HANDOVER\s+(\w+)\s*[—–-]+\s*(.*)", text)
    if m:
        author = m.group(1).title()
        number = m.group(2)
        title = m.group(3).strip()
        return f"{author.upper()}_HANDOVER_{number}", title, author

    # Fallback: split on em-dash / en-dash / hyphen
    parts = re.split(r"\s*[—–]\s*", text, 1)
    title = parts[1].strip() if len(parts) > 1 else text
    return "UNKNOWN_HANDOVER_0", title, "Unknown"


def _extract_metadata_block(text: str) -> dict[str, str]:
    """Extract **Key:** value pairs from the document."""
    meta: dict[str, str] = {}
    for m in re.finditer(r"\*\*([^*]+):\*\*\s*(.+)", text):
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        # Strip markdown link syntax: [text](url) → text (url)
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
        meta[key] = value
    return meta


def _parse_date(raw: str) -> Optional[date]:
    """Parse date from strings like '2026-03-10' or '2026-04-09'."""
    if not raw:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None


def _parse_supersedes(raw: str) -> list[str]:
    if not raw:
        return []
    # May be comma-separated or "X and Y"
    parts = re.split(r",\s*|\s+and\s+", raw)
    return [p.strip().strip("`") for p in parts if p.strip()]


def _extract_reference_documents(text: str) -> list[ReferenceDocument]:
    """Extract the bullet list under **Reference Documents:**."""
    docs: list[ReferenceDocument] = []
    m = re.search(
        r"\*\*Reference [Dd]oc(?:uments?|s)?:\*\*\s*\n((?:[ \t]*[-*] .+\n?)+)",
        text,
    )
    if not m:
        return docs
    for line in m.group(1).splitlines():
        line = line.strip().lstrip("-* ").strip()
        if not line:
            continue
        # Extract path from backtick or link
        path_m = re.search(r"`([^`]+)`", line)
        path = path_m.group(1) if path_m else line
        # Remaining text after the path is the note
        note_text = line.replace(f"`{path}`", "").strip(" —-()")
        docs.append(ReferenceDocument(path=path, note=note_text or None))
    return docs


def _split_level2_sections(text: str) -> dict[str, str]:
    """Split document into level-2 sections keyed by lowercase header text."""
    sections: dict[str, str] = {}
    # Split on ## headers (not ###)
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        header = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[header.lower()] = body
    return sections


def _parse_context_section(sections: dict[str, str]) -> HandoverContext:
    """Build HandoverContext from relevant sections."""
    context_keys = {
        "context — read this first",
        "context",
        "what this task does",
        "read this before you touch anything",
        "read this before touching anything",
    }
    narrative_parts: list[str] = []
    what_changes: list[str] = []
    what_does_not_change: list[str] = []
    important_notices: list[str] = []

    for key, body in sections.items():
        if key in context_keys:
            # Strip the metadata block (key-value pairs) from the narrative
            narrative = re.sub(r"\*\*[^*]+:\*\*[^\n]*\n", "", body).strip()
            # Remove reference document bullet list
            narrative = re.sub(
                r"\*\*Reference [Dd]oc(?:uments?|s)?:\*\*\s*\n(?:[ \t]*[-*] .+\n?)+",
                "",
                narrative,
            ).strip()
            if narrative:
                narrative_parts.append(narrative)

        elif "what changes" in key or "what this task does" in key:
            narrative_parts.append(body)

        elif key == "important":
            important_notices.extend(
                line.strip().lstrip("0123456789. ").strip()
                for line in body.splitlines()
                if line.strip() and not line.startswith("|")
            )

    # Also scan for "What changes:" / "What does NOT change:" within any section
    full_text = "\n".join(sections.values())
    wc_m = re.search(r"\*\*What changes?:\*\*\n((?:\d+\. .+\n?)+)", full_text)
    if wc_m:
        what_changes = [
            re.sub(r"^\d+\.\s*", "", ln).strip()
            for ln in wc_m.group(1).splitlines()
            if ln.strip()
        ]
    wnc_m = re.search(r"\*\*What does NOT change[^:]*:\*\*\s*(.+)", full_text)
    if wnc_m:
        what_does_not_change = [
            x.strip().strip("`")
            for x in wnc_m.group(1).split(",")
            if x.strip()
        ]

    narrative = "\n\n".join(narrative_parts).strip() or "See document."
    return HandoverContext(
        narrative=narrative,
        what_changes=what_changes,
        what_does_not_change=what_does_not_change,
        important_notices=important_notices,
    )


def _parse_list_section(sections: dict[str, str], keys: set[str]) -> list[str]:
    """Parse a numbered or bullet list from a named section."""
    for key, body in sections.items():
        if key in keys:
            items = []
            for line in body.splitlines():
                line = line.strip()
                # Match numbered items or bullet items
                m = re.match(r"^(?:\d+\.|[-*])\s+(.+)", line)
                if m:
                    items.append(m.group(1).strip())
            return items
    return []


def _parse_task_overview(sections: dict[str, str]) -> list[TaskSummaryRow]:
    """Parse the task overview table."""
    rows: list[TaskSummaryRow] = []
    for key in ("task overview", "the task list"):
        if key not in sections:
            continue
        body = sections[key]
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("| #") or line.startswith("|--") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            rows.append(
                TaskSummaryRow(
                    number=cells[0],
                    description=cells[1],
                    deliverable=cells[2],
                    checkpoint_decides=cells[3] if len(cells) > 3 else None,
                )
            )
        break
    return rows


def _parse_tasks(sections: dict[str, str]) -> list[HandoverTask]:
    """Parse individual task sections."""
    tasks: list[HandoverTask] = []
    task_pattern = re.compile(r"^task\s+([\w.]+)\s*[—–-]+\s*(.+)$", re.IGNORECASE)

    for key, body in sections.items():
        m = task_pattern.match(key)
        if not m:
            continue
        task_id = m.group(1)
        task_title = m.group(2).strip()

        goal = _extract_goal(body)
        steps = _extract_steps(body)
        verification = _extract_verification(body)
        commit_msg = _extract_commit_message(body)
        checkpoints = _extract_checkpoints_from_body(body)

        tasks.append(
            HandoverTask(
                id=task_id,
                title=task_title,
                goal=goal,
                steps=steps,
                verification=verification,
                commit_message=commit_msg,
                checkpoints=checkpoints,
            )
        )

    tasks.sort(key=lambda t: _task_sort_key(t.id))
    return tasks


def _task_sort_key(task_id: str) -> tuple[int, int]:
    """Sort task IDs like 0, 0.5, 1, 2, 3 numerically."""
    try:
        parts = task_id.split(".")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return 999, 0


def _extract_goal(body: str) -> str:
    """Extract the goal / introductory paragraph from a task body."""
    m = re.search(r"\*\*Goal:\*\*\s*(.+?)(?=\n\n|\n#{1,3} |\Z)", body, re.DOTALL)
    if m:
        return m.group(1).strip()
    # First non-empty paragraph before any subsection
    paragraphs = re.split(r"\n\n+", body.strip())
    for para in paragraphs:
        if para.strip() and not para.strip().startswith("#") and not para.strip().startswith("|"):
            return para.strip()
    return ""


def _extract_steps(body: str) -> list[str]:
    """Extract numbered top-level steps from a task body."""
    steps = []
    for m in re.finditer(r"^(?:#{3}|Step \d+[.:]|### \d+\.)", body, re.MULTILINE):
        pass  # subsections as steps
    # Simple numbered list items
    for line in body.splitlines():
        m = re.match(r"^(\d+)\.\s+\*\*(.+?)\*\*", line)
        if m:
            steps.append(m.group(2).strip())
    return steps


def _extract_verification(body: str) -> Optional[VerificationBlock]:
    """Extract the verification bash block from a task body."""
    m = re.search(
        r"(?:#+\s*Verification|Verification\n)\s*\n+```bash\n(.*?)```",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        m = re.search(r"```bash\n(.*?)```", body, re.DOTALL)
    if m:
        return VerificationBlock(commands=m.group(1).strip())
    return None


def _extract_commit_message(body: str) -> Optional[str]:
    """Extract the commit message from a task body."""
    m = re.search(r"\*\*Commit(?: message)?:\*\*\s*`([^`]+)`", body)
    return m.group(1).strip() if m else None


def _extract_checkpoints_from_body(body: str) -> list["Checkpoint"]:
    """Extract CHECKPOINT-N subsections from a task body."""
    from alfred.schemas.checkpoint import (
        Checkpoint,
        CheckpointResult,
        DecisionRule,
        DecisionTable,
    )

    checkpoints = []
    cp_pattern = re.compile(
        r"#{2,3}\s+(CHECKPOINT-\d+)[^\n]*\n(.*?)(?=\n#{2,3} |\Z)",
        re.DOTALL,
    )
    for m in cp_pattern.finditer(body):
        cp_id = m.group(1)
        cp_body = m.group(2)

        # Extract question (first sentence or paragraph)
        question = _extract_goal(cp_body) or f"Evaluate {cp_id}"
        evidence_required = "Paste verbatim console output."

        # Extract decision table rows
        rules: list[DecisionRule] = []
        for row_m in re.finditer(
            r"\|\s*([^|]+?)\s*\|\s*(proceed|pivot|stop|escalate|note)\s*\|",
            cp_body,
            re.IGNORECASE,
        ):
            condition = row_m.group(1).strip()
            verdict_str = row_m.group(2).strip().lower()
            if verdict_str in ("proceed", "pivot", "stop", "escalate"):
                rules.append(DecisionRule(condition=condition, likely_verdict=verdict_str))  # type: ignore[arg-type]

        dt = DecisionTable(rules=rules) if rules else DecisionTable(rules=[])

        # Extract result if present
        result = None
        verdict_m = re.search(r"\*\*Verdict:\*\*\s*`(\w+)`", cp_body)
        if verdict_m:
            v = verdict_m.group(1).lower()
            if v in ("proceed", "pivot", "stop", "escalate"):
                evidence_m = re.search(r"\*\*Evidence:\*\*\s*(.+)", cp_body)
                reasoning_m = re.search(r"\*\*Reasoning:\*\*\s*(.+)", cp_body)
                result = CheckpointResult(
                    verdict=v,  # type: ignore[arg-type]
                    evidence_provided=evidence_m.group(1).strip() if evidence_m else "",
                    reasoning=reasoning_m.group(1).strip() if reasoning_m else "",
                )

        checkpoints.append(
            Checkpoint(
                id=cp_id,
                question=question,
                evidence_required=evidence_required,
                decision_table=dt,
                result=result,
            )
        )

    return checkpoints


def _parse_what_exists_today(sections: dict[str, str]) -> tuple[list[str], list[str]]:
    """Parse ## WHAT EXISTS TODAY into (what_exists_today bullets, git_history lines).

    Permissive: if the section is absent or malformed both lists are empty.
    The ### Git History subsection is extracted first; remaining bullet lines
    become what_exists_today. Non-Alfred documents without this section are
    unaffected.
    """
    body = sections.get("what exists today", "")
    if not body:
        return [], []

    git_history: list[str] = []
    what_exists_today: list[str] = []

    # Extract ### Git History code block
    git_block_m = re.search(
        r"###\s+Git History\s*\n+```[^\n]*\n(.*?)```",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if git_block_m:
        git_history = [
            line for line in git_block_m.group(1).splitlines() if line.strip()
        ]
        # Remove the git history subsection from body before parsing bullets
        body = body[: git_block_m.start()] + body[git_block_m.end() :]

    # Remaining bullet lines (skip ### sub-headers and blank lines)
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^[-*]\s+(.+)", stripped)
        if m:
            what_exists_today.append(m.group(1).strip())

    return what_exists_today, git_history


def _parse_post_mortem_section(sections: dict[str, str]) -> Optional[PostMortem]:
    """Parse the post-mortem section if present."""
    for key in ("post-mortem", "post mortem", "postmortem"):
        if key in sections:
            body = sections[key]
            return PostMortem(summary=body.strip())
    return None
