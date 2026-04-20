"""Generate the Phase 7 handover spec using Alfred's own planner pipeline."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

from alfred.schemas.config import AlfredConfig
from alfred.tools.rag import index_corpus

SPRINT_GOAL = (
    "Phase 7: Developer experience and deployment — packaging, Docker, CLI polish, "
    "operational hardening, and runtime deployment for the Alfred agent coordination system."
)
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "default.yaml"
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "ALFRED_HANDOVER_6_DRAFT.md"


def main() -> None:
    with open(CONFIG_PATH) as f:
        config = AlfredConfig.model_validate(yaml.safe_load(f))

    print("Indexing corpus...")
    n = index_corpus(
        config.rag.corpus_path,
        config.rag.index_path,
        config.rag.embedding_model,
    )
    print(f"  {n} chunks indexed from {config.rag.corpus_path!r}")

    import datetime

    from alfred.agents.planner import load_canonical_template, run_planner
    from alfred.orchestrator import _run_critique_loop
    from alfred.schemas.agent import BoardState, PlannerInput
    from alfred.schemas.handover import HandoverContext, HandoverDocument
    from alfred.tools.git_log import read_git_log
    from alfred.tools.llm import resolve_model
    from alfred.tools.persistence import get_velocity_history
    from alfred.tools.rag import retrieve

    chunks = retrieve(SPRINT_GOAL, config.rag.index_path, top_k=5)
    print(f"  {len(chunks)} RAG chunks retrieved")

    board = BoardState()
    if config.github.org and config.github.project_number:
        token = os.environ.get(config.github.token_env_var, "")
        if token:
            from alfred.tools.github_api import get_board_state

            board = get_board_state(
                config.github.org,
                config.github.project_number,
                token,
            )

    velocity = []
    if config.database.path:
        velocity = get_velocity_history(config.database.path, sprint_count=10)

    canonical_template = load_canonical_template(config.handover.template_path)
    if canonical_template:
        print(f"Loaded Alfred canonical scaffold from {config.handover.template_path}")
    else:
        print(
            f"WARNING: no canonical scaffold loaded from {config.handover.template_path!r}; "
            "generated draft will not be promotion-safe without manual fixup."
        )

    git_history = read_git_log(max_commits=12)
    if git_history:
        print(f"  {len(git_history)} git commits loaded for ### Git History")
    else:
        print("WARNING: no git history available; ### Git History will be a TBD marker")

    plan_provider, plan_model = resolve_model("plan", config)
    print(f"Calling planner ({plan_provider}/{plan_model})...")
    planner_out = run_planner(
        PlannerInput(
            board_state=board,
            velocity_history=velocity,
            sprint_goal=SPRINT_GOAL,
            prior_handover_summaries=chunks,
            canonical_template=canonical_template,
            git_history_summary=git_history,
        ),
        provider=plan_provider,
        model=plan_model,
        db_path=config.database.path,
    )

    temp_handover = HandoverDocument(
        id="ALFRED_HANDOVER_6_DRAFT",
        title="Phase 7 Draft",
        date=datetime.date.today(),
        author="alfred",
        context=HandoverContext(narrative=""),
    )
    print("Running critique loop...")
    best_draft = _run_critique_loop(
        planner_out.draft_handover_markdown,
        temp_handover,
        config,
        config.database.path,
    )

    OUTPUT_PATH.write_text(best_draft)
    print(f"\nDraft written to {OUTPUT_PATH}")
    print(f"Critique iterations: {len(temp_handover.critique_history)}")
    print("\n--- DRAFT PREVIEW (first 60 lines) ---")
    lines = best_draft.splitlines()
    print("\n".join(lines[:60]))
    if len(lines) > 60:
        print(f"\n... ({len(lines) - 60} more lines in {OUTPUT_PATH})")


if __name__ == "__main__":
    main()
