# Alfred Portfolio Narrative — Phase 8 Polish

## What Alfred Is

Alfred is a document-mediated coordination system for software delivery: instead of hiding state in chat history or agent memory, it treats the handover document as the protocol, then layers a FastAPI surface, a packaged CLI, typed schemas, checkpoint evaluation, and human approvals around that artifact. In portfolio terms, it demonstrates how to build an AI-assisted delivery system that is inspectable, reproducible, and deliberately constrained rather than theatrically autonomous.

## What It Demonstrates

- Document-mediated coordination as a first-class engineering pattern, with markdown artifacts acting as the shared contract between planner, reviewer, and executor.
- Checkpoint-gated execution instead of open-ended autonomy, so work can pause, pivot, stop, or escalate through explicit decision tables.
- Agent and tool isolation, with planner, quality judge, retro analyst, story generator, and compiler separated by typed input/output boundaries.
- Typed schema validation across the system, including config, handover structure, agent contracts, and validator findings.
- Structured JSON logging with request correlation IDs for the HTTP surface.
- A CI/CD posture that includes linting, unit tests, property tests, evals, coverage gates, and release automation.
- Docker-based local deployment through a rootless image and a checked-in Compose path.
- Docs lifecycle governance via `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, and automated manifest drift checks.

## Architecture Tour

Read the system map first in [docs/protocol/architecture.md](../protocol/architecture.md), then use this order for a code walkthrough:

1. [src/alfred/api.py](../../src/alfred/api.py) is the runtime front door: it exposes planning, evaluation, approval, compile, dashboard, and probe endpoints, and owns startup/shutdown behavior.
2. [src/alfred/agents](../../src/alfred/agents/) contains the role-isolated reasoning modules: planner for drafts, story generator for story proposals, quality judge for checkpoint decisions, retro analyst for read-only synthesis, and compiler for approved-prose extraction.
3. [src/alfred/tools](../../src/alfred/tools/) is the integration layer for GitHub, RAG, LLM access, persistence, logging, repo facts, and docs policy enforcement.
4. [src/alfred/schemas](../../src/alfred/schemas/) encodes the typed contracts that keep agent boundaries and document structure explicit instead of implicit.
5. [src/alfred/orchestrator.py](../../src/alfred/orchestrator.py) is the coordination core: a plain-Python orchestrator that routes tasks, evaluates checkpoints, and writes outcomes back into the handover document.
6. [src/alfred/cli.py](../../src/alfred/cli.py) is the operator-friendly packaging layer that makes the API surface usable from a terminal for planning, evaluation, validation, serving, and version inspection.

## Demo Script

This is a 10-minute live walkthrough aimed at an external reviewer who wants to see both the product surface and the engineering discipline behind it.

### 1. Open with the thesis

Use the first minute to frame Alfred:

- Alfred treats the handover document as the protocol.
- Agents are separated by role and schema.
- Execution is gated by checkpoints and human approvals, not autonomous loops.

### 2. Start the service and prove it is alive

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alfred serve --reload
```

In a second terminal:

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

Talk track:

- `healthz` proves the process is up.
- `readyz` proves the critical dependencies are reachable.
- Mention that the same surface also emits structured logs with request IDs.

### 3. Show draft generation

If API keys are available, demonstrate the planner path:

```bash
curl -s http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"sprint_goal":"Prepare a portfolio-ready docs and governance polish pass."}'
```

Call out:

- The planner reads repo facts, prior handover context, velocity, and board state.
- The response returns draft markdown plus task decomposition and open questions.
- The planner drafts only; it does not execute work.

If live provider keys are not available, use the CLI dry-run path instead:

```bash
alfred plan --dry-run --sprint-goal "Prepare a portfolio-ready docs and governance polish pass."
```

### 4. Show checkpoint evaluation

Demonstrate the quality-judge surface with a small checkpoint definition and executor output:

```bash
curl -s http://127.0.0.1:8000/evaluate \
  -H 'Content-Type: application/json' \
  -d @- <<'JSON'
{
  "handover_document_markdown": "# Demo Handover\n\n## TASK OVERVIEW\n\n| # | Task | Deliverable |\n|---|---|---|\n| 1 | Validate | Passing checks |\n",
  "checkpoint_definition": "{\"checkpoint_id\":\"CHECKPOINT-1\",\"rows\":[{\"observation\":\"All checks passed\",\"verdict\":\"proceed\"},{\"observation\":\"Any failure output\",\"verdict\":\"stop\"}]}",
  "executor_output": {
    "task_id": "task-1",
    "console_output": "All checks passed"
  }
}
JSON
```

Call out:

- The evaluator returns a verdict, reasoning, evidence summary, and `hitl_required`.
- This is the checkpoint gate in action: the system is built to decide whether work continues, not just to generate prose.

### 5. Show the explicit human approval workflow

Register a pending approval:

```bash
curl -s http://127.0.0.1:8000/approvals/request \
  -H 'Content-Type: application/json' \
  -d '{"handover_id":"ALFRED_HANDOVER_7","action_type":"story_creation","item_id":"demo-item"}'
```

List pending approvals:

```bash
curl -s http://127.0.0.1:8000/approvals/pending
```

Approve one decision by substituting the returned `approval_id`:

```bash
curl -s http://127.0.0.1:8000/approve \
  -H 'Content-Type: application/json' \
  -d '{"approval_id":"<approval_id>","decision":"approved"}'
```

Talk track:

- Approval is a first-class API concept, not an implied side effect.
- This is where Alfred shows its methodology bias most clearly: humans remain in the loop at the moments that matter.

### 6. Close with the CLI surface

Wrap the demo by showing that the same system is available from the terminal:

```bash
alfred --help
alfred evaluate --dry-run
alfred validate docs/canonical/ALFRED_HANDOVER_7.md
alfred version
```

Final point to land:

- Alfred is not only an API prototype; it is packaged and operable as a local toolchain.

## What to Read Next

1. [README.md](../../README.md) for the high-level problem statement, approach, and local quick starts.
2. [docs/protocol/architecture.md](../protocol/architecture.md) for the component map and orchestration style.
3. [docs/protocol/OPERATOR_RUNBOOK.md](../protocol/OPERATOR_RUNBOOK.md) for runtime operations, probes, shutdown, and observability.
4. [docs/canonical/ALFRED_HANDOVER_7.md](../canonical/ALFRED_HANDOVER_7.md) for the current Phase 8 planning artifact and governance scope.
