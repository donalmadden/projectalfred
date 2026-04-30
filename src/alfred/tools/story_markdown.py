"""Render persisted story proposals into GitHub-friendly markdown."""
from __future__ import annotations

from alfred.schemas.story_proposal import StoryProposalRecord


def render_story_proposal_body(record: StoryProposalRecord) -> str:
    """Return the draft-issue body Alfred writes to GitHub Projects.

    The body stays intentionally compact so a draft card opens with the
    business-readable summary first, followed by acceptance criteria and
    the original story-point estimate.
    """

    lines: list[str] = []

    description = record.description.strip()
    if description:
        lines.append(description)

    if record.acceptance_criteria:
        if lines:
            lines.append("")
        lines.append("Acceptance Criteria")
        for criterion in record.acceptance_criteria:
            lines.append(f"- {criterion}")

    if lines:
        lines.append("")
    lines.append(f"Story Points: {record.story_points}")

    return "\n".join(lines).strip()
