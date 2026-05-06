"""Load doc-class contracts declared in ``docs/DOCS_MANIFEST.yaml``."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from alfred.tools.docs_policy import infer_repo_root

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_RELATIVE_PATH = Path("docs") / "DOCS_MANIFEST.yaml"


class DocContractLoadError(ValueError):
    """Raised when the manifest does not declare a valid doc-class contract."""


@dataclass(frozen=True)
class DocSectionContract:
    """Contract for one semantic level-2 section."""

    key: str
    headings: tuple[str, ...]
    required: bool
    semantic_class: str
    rendering_treatment: str

    @property
    def primary_heading(self) -> str:
        return self.headings[0]

    def matches_heading(self, heading: str) -> bool:
        return heading.strip() in self.headings


@dataclass(frozen=True)
class DocContract:
    """Minimal manifest-backed contract for a document class."""

    name: str
    description: str
    allow_unexpected_headings: bool
    sections: tuple[DocSectionContract, ...]

    def get_section(self, key: str) -> DocSectionContract:
        for section in self.sections:
            if section.key == key:
                return section
        raise KeyError(key)

    def match_heading(self, heading: str) -> Optional[DocSectionContract]:
        for section in self.sections:
            if section.matches_heading(heading):
                return section
        return None

    @property
    def ordered_keys(self) -> tuple[str, ...]:
        return tuple(section.key for section in self.sections)


def _manifest_path(repo_root: Path) -> Path:
    return repo_root / _MANIFEST_RELATIVE_PATH


def _resolve_repo_root(
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
) -> Path:
    if repo_root is not None:
        return Path(repo_root)

    inferred = infer_repo_root(start_path)
    if inferred is not None:
        return inferred

    return _REPO_ROOT


def _expect_mapping(value: object, path: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise DocContractLoadError(f"{path} must be a mapping.")
    return value


def _expect_list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise DocContractLoadError(f"{path} must be a list.")
    return value


def _expect_non_empty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocContractLoadError(f"{path} must be a non-empty string.")
    return value.strip()


def _expect_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DocContractLoadError(f"{path} must be a boolean.")
    return value


def _parse_section(raw: object, path: str) -> DocSectionContract:
    data = _expect_mapping(raw, path)

    key = _expect_non_empty_string(data.get("key"), f"{path}.key")
    headings = tuple(
        _expect_non_empty_string(item, f"{path}.headings[{index}]")
        for index, item in enumerate(_expect_list(data.get("headings"), f"{path}.headings"))
    )
    if not headings:
        raise DocContractLoadError(f"{path}.headings must contain at least one heading.")

    required = _expect_bool(data.get("required"), f"{path}.required")
    semantic_class = _expect_non_empty_string(
        data.get("semantic_class"),
        f"{path}.semantic_class",
    )
    rendering_treatment = _expect_non_empty_string(
        data.get("rendering_treatment"),
        f"{path}.rendering_treatment",
    )

    return DocSectionContract(
        key=key,
        headings=headings,
        required=required,
        semantic_class=semantic_class,
        rendering_treatment=rendering_treatment,
    )


def _validate_unique_sections(contract: DocContract, manifest_path: Path) -> None:
    seen_keys: dict[str, str] = {}
    seen_headings: dict[str, str] = {}

    for section in contract.sections:
        if section.key in seen_keys:
            raise DocContractLoadError(
                f"{manifest_path}: doc_classes.{contract.name} repeats section key "
                f"`{section.key}`."
            )
        seen_keys[section.key] = section.key

        for heading in section.headings:
            normalised = heading.casefold()
            if normalised in seen_headings:
                other_key = seen_headings[normalised]
                raise DocContractLoadError(
                    f"{manifest_path}: doc_classes.{contract.name} heading `{heading}` "
                    f"appears in both `{other_key}` and `{section.key}`."
                )
            seen_headings[normalised] = section.key


def load_doc_contracts(
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
) -> dict[str, DocContract]:
    """Return manifest-declared doc-class contracts keyed by class name."""
    root = _resolve_repo_root(repo_root, start_path=start_path)
    manifest_path = _manifest_path(root)
    if not manifest_path.is_file():
        raise DocContractLoadError(f"Docs manifest not found at {manifest_path}.")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise DocContractLoadError(f"{manifest_path} must parse to a mapping.")

    raw_doc_classes = data.get("doc_classes") or {}
    if not isinstance(raw_doc_classes, dict):
        raise DocContractLoadError(f"{manifest_path}: doc_classes must be a mapping.")

    contracts: dict[str, DocContract] = {}
    for doc_class_name, raw_contract in raw_doc_classes.items():
        path = f"doc_classes.{doc_class_name}"
        name = _expect_non_empty_string(doc_class_name, path)
        contract_data = _expect_mapping(raw_contract, path)
        description = _expect_non_empty_string(
            contract_data.get("description"),
            f"{path}.description",
        )
        allow_unexpected_headings = _expect_bool(
            contract_data.get("allow_unexpected_headings"),
            f"{path}.allow_unexpected_headings",
        )
        sections = tuple(
            _parse_section(raw_section, f"{path}.sections[{index}]")
            for index, raw_section in enumerate(
                _expect_list(contract_data.get("sections"), f"{path}.sections")
            )
        )
        if not sections:
            raise DocContractLoadError(f"{path}.sections must not be empty.")

        contract = DocContract(
            name=name,
            description=description,
            allow_unexpected_headings=allow_unexpected_headings,
            sections=sections,
        )
        _validate_unique_sections(contract, manifest_path)
        contracts[name] = contract

    return contracts


def get_doc_class_contract(
    doc_class: str,
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
) -> DocContract:
    """Return the requested contract or raise a precise missing-contract error."""
    contracts = load_doc_contracts(repo_root, start_path=start_path)
    try:
        return contracts[doc_class]
    except KeyError as exc:
        root = _resolve_repo_root(repo_root, start_path=start_path)
        manifest_path = _manifest_path(root)
        raise DocContractLoadError(
            f"{manifest_path}: missing doc_classes.{doc_class} contract."
        ) from exc
