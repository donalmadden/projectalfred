"""
Task 11 dogfood: run one real BOB handover checkpoint evaluation end-to-end.

Target: BOB_HANDOVER_40, CHECKPOINT 1 — environment + data audit gate.
LLM: real Anthropic call (no mocks).
Output: data/dogfood/handover3_run1.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from alfred.agents.quality_judge import run_quality_judge
from alfred.schemas.agent import ExecutorOutput, QualityJudgeInput
from alfred.tools.rag import index_corpus, retrieve

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROVIDER = "openai"
MODEL = "gpt-4o-mini"
CORPUS_DIR = Path(os.path.expanduser("~/code/3b_EBD_MLOps/docs"))
INDEX_PATH = str(REPO / "data/dogfood/rag_index")
OUTPUT_PATH = REPO / "data/dogfood/handover3_run1.json"
DB_PATH = str(REPO / "data/dogfood/alfred_dogfood.db")

# CHECKPOINT 1 from BOB_HANDOVER_40 — environment + data audit gate
CHECKPOINT_DEFINITION = json.dumps({
    "checkpoint_id": "HO40-CHECKPOINT-1",
    "rows": [
        {
            "observation": "DINOv2, CUDA/CPU, sklearn, cv2 versions all reported; total box count > 1000; per-class balance present; event_id matches CVAT folder format; image_path points to real file",
            "verdict": "proceed",
        },
        {
            "observation": "Versions reported but box count missing or zero; event_id format unclear",
            "verdict": "pivot",
        },
        {
            "observation": "Script failed to run; no output produced; ImportError or FileNotFoundError",
            "verdict": "stop",
        },
        {
            "observation": "Output ambiguous — numbers present but inconsistent or contradictory",
            "verdict": "escalate",
        },
    ],
})

# Realistic executor output representing a successful HO40 Task 1 audit run
EXECUTOR_OUTPUT_TEXT = """
DINOv2 environment audit — BOB_HANDOVER_40 Task 1

torch==2.2.1+cu121  torchvision==0.17.1+cu121  CUDA available: True  device: cuda:0
scikit-learn==1.4.1.post1
opencv-python==4.9.0.80
facebook/dinov2-base loaded successfully

Manifest: data/manifests/cvat_boxes.json
  Total boxes: 1321
  Unique events: 276
  Median box width: 187px  height: 203px
  Per-basename coverage: 276/276 events have ≥1 box

Class balance:
  break: 238 events (86.2%)
  no_break: 38 events (13.8%)

Sample record check (first 3):
  ev=break_111_20251216231739 pre/post=pre idx=0 path=/pilot01/annotated/break_111_20251216231739/frame_000.jpg  EXISTS=True
  ev=break_111_20251216231739 pre/post=post idx=1 path=/pilot01/annotated/break_111_20251216231739/frame_001.jpg  EXISTS=True
  ev=break_114_20251217084512 pre/post=pre idx=0 path=/pilot01/annotated/break_114_20251217084512/frame_000.jpg  EXISTS=True

event_id format: matches CVAT folder pattern (break_NNN_YYYYMMDDHHMMSS) ✓
"""


def _read_handover_markdown() -> str:
    path = CORPUS_DIR / "BOB_HANDOVER_40.md"
    return path.read_text(encoding="utf-8")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print("=== Alfred Task 11 — End-to-End Dogfood ===\n")

    # 1. Index a small corpus slice (BOB_HANDOVER_40 only)
    print("Step 1: Indexing corpus slice (BOB_HANDOVER_40)...")
    t0 = time.monotonic()
    n_chunks = index_corpus(
        corpus_path=str(CORPUS_DIR / "BOB_HANDOVER_40.md"),
        index_path=INDEX_PATH,
        embedding_model="all-MiniLM-L6-v2",
    )
    print(f"  Indexed {n_chunks} chunks in {time.monotonic() - t0:.1f}s")

    # 2. Retrieve relevant context chunks
    print("Step 2: Retrieving RAG context for checkpoint query...")
    chunks = retrieve(
        query="CHECKPOINT 1 environment audit data manifest box count",
        index_path=INDEX_PATH,
        top_k=3,
    )
    print(f"  Retrieved {len(chunks)} chunks")

    # 3. Build quality judge input
    handover_md = _read_handover_markdown()
    # Trim to first ~6000 chars to keep prompt size reasonable for haiku
    handover_md_trimmed = handover_md[:6000] + "\n\n[...truncated for dogfood run...]"

    rag_context = "\n\n---\n\n".join(
        f"[RAG chunk score={c.relevance_score:.3f}]\n{c.content}" for c in chunks
    )
    full_md = handover_md_trimmed + f"\n\n## RAG Context\n\n{rag_context}"

    judge_input = QualityJudgeInput(
        handover_document_markdown=full_md,
        checkpoint_definitions=[CHECKPOINT_DEFINITION],
        executor_output=ExecutorOutput(
            task_id="HO40-task-1",
            console_output=EXECUTOR_OUTPUT_TEXT,
        ),
    )

    # 4. Run quality judge with real LLM
    print(f"Step 3: Calling quality judge (provider={PROVIDER}, model={MODEL})...")
    t1 = time.monotonic()
    result = run_quality_judge(
        judge_input,
        provider=PROVIDER,
        model=MODEL,
        db_path=DB_PATH,
    )
    elapsed = time.monotonic() - t1
    print(f"  Quality judge completed in {elapsed:.1f}s")

    # 5. Print summary
    ev = result.checkpoint_evaluations[0] if result.checkpoint_evaluations else None
    print(f"\n--- Result ---")
    print(f"  checkpoint_id:       {ev.checkpoint_id if ev else 'n/a'}")
    print(f"  verdict:             {ev.verdict if ev else 'n/a'}")
    print(f"  reasoning:           {ev.reasoning[:120] if ev else 'n/a'}...")
    print(f"  hitl_escalation:     {result.hitl_escalation_required}")
    print(f"  overall_quality:     {result.overall_quality_score}")
    print(f"  validation_issues:   {[i.description for i in result.validation_issues]}")
    print(f"  methodology_compliance: {result.methodology_compliance}")

    # 6. Save full result
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "run_metadata": {
            "target_handover": "BOB_HANDOVER_40",
            "checkpoint": "HO40-CHECKPOINT-1",
            "provider": PROVIDER,
            "model": MODEL,
            "elapsed_seconds": round(elapsed, 2),
            "rag_chunks_retrieved": len(chunks),
        },
        "checkpoint_evaluations": [e.model_dump() for e in result.checkpoint_evaluations],
        "validation_issues": [i.model_dump() for i in result.validation_issues],
        "overall_quality_score": result.overall_quality_score,
        "hitl_escalation_required": result.hitl_escalation_required,
        "hitl_escalation_reason": result.hitl_escalation_reason,
        "methodology_compliance": result.methodology_compliance,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
