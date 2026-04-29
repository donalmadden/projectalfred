"""Initialise the Customer Onboarding Portal demo workspace.

Creates the exact filesystem layout frozen in
``docs/active/DEMO_PROJECT_LAYOUT.md`` at a caller-supplied path. The
charter file is copied verbatim from
``docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md``. The README text is
extracted verbatim from the layout spec so a single source of truth governs
both the spec and the generated workspace.

Phase 2 deliverable. See ``docs/canonical/ALFRED_HANDOVER_9.md`` Task 1.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
LAYOUT_DOC: Path = REPO_ROOT / "docs" / "active" / "DEMO_PROJECT_LAYOUT.md"
CHARTER_SRC: Path = REPO_ROOT / "docs" / "active" / "CUSTOMER_ONBOARDING_PORTAL_CHARTER.md"


def extract_readme_text(layout_doc: Path = LAYOUT_DOC) -> str:
    """Extract the verbatim README body from the layout spec.

    The spec wraps the README paragraph in single backticks under the
    ``## README.md Text`` section. This helper returns the unwrapped
    paragraph plus a trailing newline so the on-disk README is a clean
    single-line file.
    """
    text = layout_doc.read_text(encoding="utf-8")
    marker = "## README.md Text"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f"{layout_doc} is missing the '{marker}' section")
    section = text[idx + len(marker):]
    next_idx = section.find("\n## ")
    if next_idx != -1:
        section = section[:next_idx]
    body = section.strip()
    if body.startswith("`") and body.endswith("`"):
        body = body[1:-1].strip()
    if not body:
        raise RuntimeError(f"{layout_doc} README.md Text section is empty")
    return body + "\n"


def is_empty_dir(path: Path) -> bool:
    return path.is_dir() and not any(path.iterdir())


def workspace_matches_spec(workspace: Path, charter_src: Path, readme_text: str) -> bool:
    """True iff every frozen artifact is present with byte-identical content."""
    readme = workspace / "README.md"
    charter = workspace / "docs" / "CHARTER.md"
    handovers = workspace / "docs" / "handovers"
    if not (readme.is_file() and charter.is_file() and handovers.is_dir()):
        return False
    if readme.read_text(encoding="utf-8") != readme_text:
        return False
    if charter.read_bytes() != charter_src.read_bytes():
        return False
    return True


def init_workspace(
    workspace: Path,
    *,
    force: bool = False,
    charter_src: Path = CHARTER_SRC,
    layout_doc: Path = LAYOUT_DOC,
) -> str:
    """Create the frozen demo workspace layout.

    Returns a human-readable status string. Raises ``FileExistsError`` if
    ``workspace`` exists, is non-empty, does not already match the spec,
    and ``force`` is False.
    """
    readme_text = extract_readme_text(layout_doc)

    if workspace.exists():
        if workspace_matches_spec(workspace, charter_src, readme_text):
            return "Workspace already initialised — no changes made."
        if not is_empty_dir(workspace) and not force:
            raise FileExistsError(
                f"{workspace} exists and is not empty; pass --force to overwrite."
            )

    workspace.mkdir(parents=True, exist_ok=True)
    docs_dir = workspace / "docs"
    handovers_dir = docs_dir / "handovers"
    docs_dir.mkdir(parents=True, exist_ok=True)
    handovers_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "README.md").write_text(readme_text, encoding="utf-8")
    shutil.copyfile(charter_src, docs_dir / "CHARTER.md")

    return f"Workspace initialised at {workspace}."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialise the Customer Onboarding Portal demo workspace."
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="Path to the demo project root directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing non-empty workspace directory.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        message = init_workspace(args.workspace, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
