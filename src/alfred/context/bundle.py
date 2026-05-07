"""Typed planner-context bundle with exactly three roles.

The role set, dedup precedence, and per-role rendering rules implement the
`Context Roles` definition in `CONTEXT.md`:

- `scope` renders full text.
- `carry_forward` renders full text for non-handover docs and a deterministic
  summary for canonical handovers.
- `continuity` always renders a deterministic summary.

Dedup precedence is fixed: `scope` > `carry_forward` > `continuity`. When the
same `path` appears in multiple roles, the lower-precedence instance is dropped.

The deterministic summary for canonical handovers reuses the Slice 4
contract-driven extractor (`split_markdown_by_contract` + the
`canonical_handover` doc-class contract) so this module never embeds hardcoded
heading knowledge.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional, get_args

from alfred.docs.contract_validator import split_markdown_by_contract
from alfred.docs.contracts import get_doc_class_contract

Role = Literal["scope", "carry_forward", "continuity"]

ROLES: tuple[Role, ...] = ("scope", "carry_forward", "continuity")

_PRECEDENCE: dict[Role, int] = {role: index for index, role in enumerate(ROLES)}

_CANONICAL_HANDOVER_DOC_CLASS = "canonical_handover"

# Order in which a canonical-handover summary surfaces semantic sections.
_SUMMARY_SECTION_KEYS: tuple[str, ...] = (
    "context",
    "current_state",
    "deliverables",
    "task_overview",
    "post_mortem",
)

Summarizer = Callable[["ContextItem"], str]


def _validate_role(role: object) -> Role:
    if role not in ROLES:
        raise ValueError(
            f"Unknown context role {role!r}; allowed roles are {ROLES}."
        )
    return role  # type: ignore[return-value]


@dataclass(frozen=True)
class ContextItem:
    """One path-addressed input to the planner-context bundle."""

    path: str
    role: Role
    text: str
    is_canonical_handover: bool = False

    def __post_init__(self) -> None:
        _validate_role(self.role)


@dataclass(frozen=True)
class DedupResult:
    """Outcome of applying dedup precedence to a bundle's items."""

    kept: tuple[ContextItem, ...]
    dropped: tuple[ContextItem, ...]


@dataclass(frozen=True)
class RenderedItem:
    """A bundle item paired with its role-specific rendered text."""

    item: ContextItem
    rendered_text: str
    render_mode: Literal["full", "summary"]


def summarize_canonical_handover(
    text: str,
    *,
    repo_root: Optional[Path] = None,
) -> str:
    """Deterministic canonical-handover summary via the Slice 4 contract.

    Splits the markdown by the `canonical_handover` contract and emits a
    compact, deterministic representation of each known semantic section.
    No heading strings are hardcoded here — section identity comes from the
    manifest-backed contract.
    """
    contract = get_doc_class_contract(
        _CANONICAL_HANDOVER_DOC_CLASS,
        repo_root=repo_root,
    )
    sections = split_markdown_by_contract(text, contract)
    parts: list[str] = []
    for key in _SUMMARY_SECTION_KEYS:
        body = sections.get(key, "").strip()
        if not body:
            continue
        parts.append(f"### {key}\n{body}")
    return "\n\n".join(parts)


def _default_summarizer(item: ContextItem) -> str:
    return summarize_canonical_handover(item.text)


@dataclass(frozen=True)
class ContextBundle:
    """A bundle of role-tagged context items with dedup + render semantics."""

    items: tuple[ContextItem, ...] = field(default_factory=tuple)

    def dedup(self) -> DedupResult:
        """Drop lower-precedence duplicates that share a `path` with a higher role."""
        best_role_for_path: dict[str, Role] = {}
        for item in self.items:
            current = best_role_for_path.get(item.path)
            if current is None or _PRECEDENCE[item.role] < _PRECEDENCE[current]:
                best_role_for_path[item.path] = item.role

        kept: list[ContextItem] = []
        dropped: list[ContextItem] = []
        seen_kept: set[tuple[str, Role]] = set()
        for item in self.items:
            winner = best_role_for_path[item.path]
            if item.role == winner and (item.path, item.role) not in seen_kept:
                kept.append(item)
                seen_kept.add((item.path, item.role))
            else:
                dropped.append(item)
        return DedupResult(kept=tuple(kept), dropped=tuple(dropped))

    def render(
        self,
        *,
        summarizer: Summarizer = _default_summarizer,
    ) -> tuple[RenderedItem, ...]:
        """Apply dedup, then render each surviving item per its role rules."""
        rendered: list[RenderedItem] = []
        for item in self.dedup().kept:
            mode, text = _render_one(item, summarizer)
            rendered.append(
                RenderedItem(item=item, rendered_text=text, render_mode=mode)
            )
        return tuple(rendered)


def _render_one(
    item: ContextItem,
    summarizer: Summarizer,
) -> tuple[Literal["full", "summary"], str]:
    if item.role == "scope":
        return "full", item.text
    if item.role == "carry_forward":
        if item.is_canonical_handover:
            return "summary", summarizer(item)
        return "full", item.text
    if item.role == "continuity":
        return "summary", summarizer(item)
    raise ValueError(f"Unhandled role {item.role!r}.")


# Static guard: if a future edit changes the Literal members, this will break
# at import time and force the change to be deliberate.
assert set(get_args(Role)) == set(ROLES) == {
    "scope",
    "carry_forward",
    "continuity",
}, "Context role set drift detected; see CONTEXT.md."
