"""Deterministic validation for manifest-declared doc-class contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from alfred.docs.contracts import DocContract


@dataclass(frozen=True)
class ObservedHeading:
    """One observed level-2 heading in a markdown document."""

    text: str
    line: int


@dataclass(frozen=True)
class ContractFinding:
    """Validation result for one contract mismatch."""

    severity: str
    code: str
    message: str
    line: Optional[int] = None
    section_key: Optional[str] = None
    heading: Optional[str] = None

    def format(self) -> str:
        if self.line is None:
            return self.message
        return f"line {self.line}: {self.message}"


def extract_level2_headings(markdown: str) -> list[ObservedHeading]:
    """Return all ``##`` headings outside fenced code blocks."""
    headings: list[ObservedHeading] = []
    in_fence = False

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            headings.append(ObservedHeading(text=line[3:].strip(), line=line_number))

    return headings


def split_markdown_by_contract(markdown: str, contract: DocContract) -> dict[str, str]:
    """Split markdown into contract section bodies keyed by semantic section key."""
    sections: dict[str, list[str]] = {}
    current_key: Optional[str] = None
    in_fence = False

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current_key is not None:
                sections.setdefault(current_key, []).append(line)
            continue

        if not in_fence and line.startswith("## "):
            heading = line[3:].strip()
            section = contract.match_heading(heading)
            current_key = section.key if section is not None else None
            if current_key is not None:
                sections.setdefault(current_key, [])
            continue

        if current_key is not None:
            sections[current_key].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def validate_doc_against_contract(markdown: str, contract: DocContract) -> list[ContractFinding]:
    """Return deterministic findings for required-heading and order mismatches."""
    findings: list[ContractFinding] = []
    observed_headings = extract_level2_headings(markdown)
    matched: dict[str, ObservedHeading] = {}
    contract_index = {section.key: index for index, section in enumerate(contract.sections)}

    for observed in observed_headings:
        section = contract.match_heading(observed.text)
        if section is None:
            if not contract.allow_unexpected_headings:
                findings.append(
                    ContractFinding(
                        severity="error",
                        code="unexpected_heading",
                        message=f"Unexpected level-2 heading `{observed.text}`.",
                        line=observed.line,
                        heading=observed.text,
                    )
                )
            continue

        if section.key in matched:
            findings.append(
                ContractFinding(
                    severity="error",
                    code="duplicate_heading",
                    message=(
                        f"Duplicate contract heading for section `{section.key}`: "
                        f"`{observed.text}`."
                    ),
                    line=observed.line,
                    section_key=section.key,
                    heading=observed.text,
                )
            )
            continue

        matched[section.key] = observed

    for section in contract.sections:
        if not section.required or section.key in matched:
            continue

        accepted = ", ".join(f"`{heading}`" for heading in section.headings)
        findings.append(
            ContractFinding(
                severity="error",
                code="missing_heading",
                message=(
                    f"Missing required level-2 heading for section `{section.key}`. "
                    f"Accepted headings: {accepted}."
                ),
                section_key=section.key,
            )
        )

    ordered_matches = [
        (contract_index[section.key], section.key, observed)
        for observed in observed_headings
        if (section := contract.match_heading(observed.text)) is not None
        and section.key in matched
        and matched[section.key] == observed
    ]

    last_index = -1
    last_key: Optional[str] = None
    for current_index, current_key, observed in ordered_matches:
        if current_index < last_index:
            findings.append(
                ContractFinding(
                    severity="error",
                    code="out_of_order_heading",
                    message=(
                        f"Section `{current_key}` appears after `{last_key}` in the "
                        "contract but before it in the document."
                    ),
                    line=observed.line,
                    section_key=current_key,
                    heading=observed.text,
                )
            )
            break
        last_index = current_index
        last_key = current_key

    return findings
