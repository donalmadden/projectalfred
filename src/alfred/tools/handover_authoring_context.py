"""Deterministic section indexing and context assembly for handover authoring."""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^(?:[-*]|\d+\.)\s+")
_LABEL_LINE_RE = re.compile(r"^\*\*(.+?)\*\*:?\s*(.*)$")


def _normalise_heading(text: str) -> str:
    return " ".join(text.strip().casefold().split())


def _classify_section(path: tuple[str, ...]) -> tuple[str, ...]:
    tags: set[str] = set()
    normalized_path = tuple(_normalise_heading(part) for part in path)
    heading = normalized_path[-1] if normalized_path else ""

    if "hard rules" in heading or "what not to do" in heading:
        tags.add("hard_rules")
    if heading in {"out of scope", "explicit non-goals", "definition of failure"}:
        tags.add("constraints")
    if heading.startswith("task ") or heading in {"task overview", "board-seeding task"}:
        tags.add("task_spec")
    if "approval gate" in heading:
        tags.add("approval_gate")
    if heading.startswith("phase "):
        tags.add("phase_detail")
    if heading in {
        "phase 1 deliverables inherited (do not revisit)",
        "key design decisions inherited (do not revisit)",
    }:
        tags.add("inherited_constraints")
    if heading in {"what this phase produces", "kickoff goals", "required functional capabilities"}:
        tags.add("deliverables")
    if heading == "definition of demo-done":
        tags.add("success_criteria")
    if heading == "post-mortem":
        tags.add("post_mortem")
    if heading in {"frozen layout", "file and directory purposes", "readme.md text", "charter.md source", "directory decisions"}:
        tags.add("layout_spec")
    if heading in {"business context", "primary user", "success metric", "known constraints", "explicit non-goals"}:
        tags.add("charter")
    if heading == "module & agent inventory":
        tags.add("runtime_inventory")
    if heading == "minimal viable demo slice":
        tags.add("critical_path")
    if heading == "demo outcome we are building toward":
        tags.add("narrative_arc")
    return tuple(sorted(tags))


@dataclass(frozen=True)
class MarkdownSection:
    path: tuple[str, ...]
    normalized_path: tuple[str, ...]
    level: int
    content: str
    body: str
    start_line: int
    end_line: int
    tags: tuple[str, ...]

    @property
    def heading(self) -> str:
        return self.path[-1]

    @property
    def display_path(self) -> str:
        return " > ".join(self.path)


@dataclass(frozen=True)
class MarkdownDocumentIndex:
    source_path: Path
    title: str
    text: str
    sections: tuple[MarkdownSection, ...]
    char_count: int

    @property
    def relative_path(self) -> str:
        return self.source_path.as_posix()


@dataclass(frozen=True)
class SectionSelector:
    path_suffix: str
    reason: str
    render_mode: str = "facts_only"
    required: bool = True


@dataclass(frozen=True)
class DocumentSelectionSpec:
    source_path: Path
    selectors: tuple[SectionSelector, ...]


@dataclass(frozen=True)
class SelectedSection:
    source_path: str
    section_path: str
    reason: str
    render_mode: str
    tags: tuple[str, ...]
    char_count: int
    content: str
    body: str


@dataclass(frozen=True)
class StructuredFactBlock:
    source_path: str
    section_path: str
    reason: str
    tags: tuple[str, ...]
    points: tuple[str, ...]


@dataclass(frozen=True)
class AuthoringContextPacket:
    text: str
    source_doc_paths: tuple[str, ...]
    selected_sections: tuple[SelectedSection, ...]
    facts: tuple[StructuredFactBlock, ...]
    source_char_count: int
    packet_char_count: int


def index_markdown_document(path: Path) -> MarkdownDocumentIndex:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING_RE.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        headings.append((index, level, match.group(2).strip()))

    sections: list[MarkdownSection] = []
    stack: list[tuple[int, str]] = []
    for offset, (start_index, level, heading) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading))
        path_parts = tuple(item for _, item in stack)

        end_index = len(lines)
        for next_index, next_level, _ in headings[offset + 1 :]:
            if next_level <= level:
                end_index = next_index
                break

        content = "\n".join(lines[start_index:end_index]).strip()
        body = "\n".join(lines[start_index + 1 : end_index]).strip()
        sections.append(
            MarkdownSection(
                path=path_parts,
                normalized_path=tuple(_normalise_heading(part) for part in path_parts),
                level=level,
                content=content,
                body=body,
                start_line=start_index + 1,
                end_line=end_index,
                tags=_classify_section(path_parts),
            )
        )

    title = sections[0].heading if sections else path.name
    return MarkdownDocumentIndex(
        source_path=path,
        title=title,
        text=text,
        sections=tuple(sections),
        char_count=len(text),
    )


def _find_sections_by_path_suffix(
    document: MarkdownDocumentIndex,
    path_suffix: str,
) -> list[MarkdownSection]:
    suffix_parts = tuple(
        _normalise_heading(part)
        for part in path_suffix.split(">")
        if part.strip()
    )
    if not suffix_parts:
        return []
    return [
        section
        for section in document.sections
        if section.normalized_path[-len(suffix_parts) :] == suffix_parts
    ]


def _extract_structured_points(body: str, *, max_points: int = 6) -> tuple[str, ...]:
    points: list[str] = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        label_match = _LABEL_LINE_RE.match(stripped)
        if label_match is not None:
            label = label_match.group(1).strip().rstrip(":")
            remainder = label_match.group(2).strip()
            if remainder:
                points.append(f"{label}: {remainder}")
            else:
                points.append(f"{label}:")
        elif _BULLET_RE.match(stripped):
            points.append(_BULLET_RE.sub("", stripped, count=1))
        elif stripped.startswith(">"):
            points.append(stripped.lstrip(">").strip())
        elif not stripped.startswith(("`", "|", "#")):
            points.append(stripped)
        if len(points) >= max_points:
            break
    return tuple(points)


def build_authoring_context_packet(
    selection_specs: Iterable[DocumentSelectionSpec],
    *,
    repo_root: Path,
    intro_lines: Iterable[str],
) -> AuthoringContextPacket:
    selected_sections: list[SelectedSection] = []
    facts: list[StructuredFactBlock] = []
    source_doc_paths: list[str] = []
    source_char_count = 0

    for spec in selection_specs:
        source_path = spec.source_path
        relative_source = source_path.relative_to(repo_root).as_posix()
        document = index_markdown_document(source_path)
        source_doc_paths.append(relative_source)
        source_char_count += document.char_count

        seen_section_paths: set[str] = set()
        for selector in spec.selectors:
            matches = _find_sections_by_path_suffix(document, selector.path_suffix)
            if not matches:
                if selector.required:
                    raise ValueError(
                        f"{relative_source} missing required section path suffix: "
                        f"{selector.path_suffix}"
                    )
                continue
            if len(matches) > 1:
                raise ValueError(
                    f"{relative_source} selector is ambiguous: {selector.path_suffix}"
                )
            match = matches[0]
            display_path = match.display_path
            if display_path in seen_section_paths:
                continue
            seen_section_paths.add(display_path)
            selected = SelectedSection(
                source_path=relative_source,
                section_path=display_path,
                reason=selector.reason,
                render_mode=selector.render_mode,
                tags=match.tags,
                char_count=len(match.content),
                content=match.content,
                body=match.body,
            )
            selected_sections.append(selected)
            points = _extract_structured_points(match.body)
            if points and selector.render_mode in {"facts_only", "facts_and_verbatim"}:
                facts.append(
                    StructuredFactBlock(
                        source_path=relative_source,
                        section_path=display_path,
                        reason=selector.reason,
                        tags=match.tags,
                        points=points,
                    )
                )

    blocks: list[str] = list(intro_lines)
    blocks.extend(
        [
            "",
            "===== PASS 1 — STRUCTURED FACTS =====",
        ]
    )
    for fact in facts:
        blocks.append(f"[{fact.source_path} :: {fact.section_path} | {fact.reason}]")
        blocks.extend(f"- {point}" for point in fact.points)
        blocks.append("")

    blocks.append("===== PASS 2 — VERBATIM SOURCE SECTIONS =====")
    for section in selected_sections:
        if section.render_mode not in {"verbatim_only", "facts_and_verbatim"}:
            continue
        tags = ", ".join(section.tags) if section.tags else "none"
        blocks.extend(
            [
                (
                    f"----- BEGIN {section.source_path} :: {section.section_path} "
                    f"(reason: {section.reason}; tags: {tags}) -----"
                ),
                section.content.rstrip(),
                (
                    f"----- END {section.source_path} :: {section.section_path} -----"
                ),
                "",
            ]
        )
    blocks.append("===== END AUTHORITATIVE AUTHORING PACKET =====")

    text = "\n".join(block.rstrip() for block in blocks).rstrip()
    return AuthoringContextPacket(
        text=text,
        source_doc_paths=tuple(source_doc_paths),
        selected_sections=tuple(selected_sections),
        facts=tuple(facts),
        source_char_count=source_char_count,
        packet_char_count=len(text),
    )
