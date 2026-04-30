# Phase 5 Demo Script - Customer Onboarding Portal Kickoff

## Purpose

This document is the operator-facing rehearsal script for Alfred's blank-project kickoff demo. It packages the existing Phase 2-4 runtime into a single, repeatable flow that starts from a fresh external demo workspace and a blank GitHub Project V2 board, then ends with 6-8 visible draft items created only after approval.

## Runtime Truth Today

- The external demo workspace path contract is:
  - `<demo-project-root>/README.md`
  - `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]
  - `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace]
- The kickoff harness persists the first handover at `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the external demo workspace].
- The kickoff harness calls the compiler and `orchestrate(...)` directly. Keep the API service running as an evidence surface for probes and dashboard reads, but do not claim the API is the runtime path for the kickoff harness today.
- The default kickoff harness path uses the compiler and story-generator defaults from code, so the live LLM-backed path expects `ANTHROPIC_API_KEY` unless the harness is invoked programmatically with a different config.
- There is only one runtime-enforced approval gate in the current implementation: the board-write gate before GitHub Project mutation.
- The kickoff handover review boundary is still manual today. The runtime does not expose a separate approval endpoint that blocks persistence or compile of `ALFRED_HANDOVER_1.md`.
- The checked-in `scripts/run_kickoff_demo.py --phase4` path does not accept board-target flags on the CLI today. For a truthful live demo, use the config-bearing Python invocation below when it is time to write to GitHub.

## Operator Surfaces

- Terminal A: Alfred API and probe evidence.
- Terminal B: demo workspace creation, kickoff harness, and board-write arc.
- Browser: target GitHub Project V2 board.

## Assumptions

- Run every command from the repository root with Alfred already installed into the active shell environment.
- Export `ANTHROPIC_API_KEY` before Step 7 so the kickoff harness can compile the handover and generate the proposal batch.
- Export `GITHUB_TOKEN` before Step 11 so the board-write arc can create draft items in the target GitHub Project V2 board.

## Frozen Inputs

- Scenario: `Customer Onboarding Portal`
- Charter source: `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`
- Charter copy rule: the external demo workspace must contain a verbatim copy at `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]
- Required external workspace shape:
  - `<demo-project-root>/README.md`
  - `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]
  - `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace]
- First Alfred-authored artifact path: `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the external demo workspace]
- Target GitHub Project identity: record the exact board URL, owner, and project number before rehearsal. This identifier is human-supplied and must remain fixed across clean runs.

## Preflight Checklist

- [ ] Scenario is still `Customer Onboarding Portal`; no domain substitution has been introduced.
- [ ] The charter source is `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`, and the external workspace will receive it verbatim at `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace].
- [ ] The target GitHub Project V2 board URL/name is written down for the rehearsal and confirmed to be the intended blank board.
- [ ] The target GitHub Project V2 board currently shows `0` items in the browser.
- [ ] `DEMO_PROJECT_ROOT`, `ALFRED_DEMO_GITHUB_ORG`, and `ALFRED_DEMO_GITHUB_PROJECT_NUMBER` are exported in Terminal B.
- [ ] `ANTHROPIC_API_KEY` is exported for the checked-in kickoff harness path.
- [ ] `GITHUB_TOKEN` is exported for the Phase 4 board-write arc.
- [ ] Alfred's API starts locally with `alfred serve --host 127.0.0.1 --port 8000`.
- [ ] `GET /healthz` responds with HTTP 200 and `{"status":"ok"}`.
- [ ] `GET /readyz` responds with HTTP 200 and `{"status":"ready"}`.
- [ ] `GET /dashboard` responds and shows `pending_approvals_count` as `0` before the rehearsal begins.
- [ ] Optional helper check passes:

```bash
python scripts/demo_preflight.py --base-url http://127.0.0.1:8000
```

- [ ] If you intentionally change the harness or API model routing away from the checked-in defaults, confirm the replacement provider env var is exported before continuing.

## Evidence To Point To

### Evidence - Pre-Approval

Use these surfaces before any board-write approval is granted:

```bash
ls "$DEMO_PROJECT_ROOT/docs/handovers/ALFRED_HANDOVER_1.md"
sed -n '1,40p' "$DEMO_PROJECT_ROOT/docs/handovers/ALFRED_HANDOVER_1.md"
python scripts/run_kickoff_demo.py --workspace "$DEMO_PROJECT_ROOT" --review-only
```

What to show:
- the persisted kickoff artifact exists at `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the external demo workspace]
- the compile confirmation already appeared in the kickoff harness transcript:
  - `[COMPILE] HandoverDocument compiled; tasks: ['TASK-SEED-BOARD-001']`
- the persisted proposal batch is reviewable from workspace-local runtime state
- the GitHub Project V2 board is still blank in the browser

Narration anchor:
- "The markdown handover and the persisted proposal batch exist before any GitHub mutation. The board is still empty because approval has not been granted."

### Evidence - Approval Pending

The standard Phase 4 fast path - the `run_phase4_arc(...)` invocation used later in Step 11 - records approval and writes in one transcript. It is good enough for the main demo, but it does not pause long enough to make a pending approval row easy to point to live.

If you need a visible pending approval record during rehearsal, use the workspace-local persistence surface instead of the default API startup path. The default `alfred serve` path points at `data/alfred.db`, while the kickoff harness persists its runtime state under `<demo-project-root>/.alfred/state.sqlite3`.

Create a pending approval row in the workspace-local database:

```bash
export ALFRED_DEMO_APPROVAL_ID=approval-kickoff-board-1

python - <<'PY'
from pathlib import Path
import json
import os
import sys

repo_root = Path.cwd()
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "scripts"))

import run_kickoff_demo as rk
from alfred.tools.board_write_contract import BOARD_WRITE_ACTION
from alfred.tools.persistence import create_pending_approval, get_pending_approvals

workspace = Path(os.environ["DEMO_PROJECT_ROOT"])
db_path = str(rk.workspace_db_path(workspace))
approval_id = os.environ["ALFRED_DEMO_APPROVAL_ID"]

create_pending_approval(
    db_path,
    approval_id=approval_id,
    handover_id=rk.KICKOFF_HANDOVER_ID,
    action_type=BOARD_WRITE_ACTION,
    item_id=rk.KICKOFF_TASK_ID,
    timeout_seconds=3600,
)

rows = get_pending_approvals(db_path)
print(json.dumps(rows, indent=2))
PY
```

What to show:
- `approval_id`
- `handover_id`
- `action_type=WRITE_GITHUB_PROJECT_V2`
- `item_id=TASK-SEED-BOARD-001`
- `requested_at` and `expires_at`
- `decision` is still unset while the request is pending

Narration anchor:
- "Approval is now recorded as runtime state, but nothing has been written yet. The request is visible and reviewable before any downstream board mutation."

If you use this paused approval lane, do not jump back to the standard `--phase4` fast path afterward. Approve the same row and continue with the post-write evidence lane below.

### Evidence - Post-Write

Approve the pending row, dispatch the existing board-writer flow against that approved row, then print the persisted write receipts:

```bash
python - <<'PY'
from pathlib import Path
import os
import sys

repo_root = Path.cwd()
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "scripts"))

import run_kickoff_demo as rk
from alfred.tools.persistence import record_approval_decision

workspace = Path(os.environ["DEMO_PROJECT_ROOT"])
db_path = str(rk.workspace_db_path(workspace))
approval_id = os.environ["ALFRED_DEMO_APPROVAL_ID"]

record_approval_decision(db_path, approval_id, "approved")
print(f"approved {approval_id}")
PY
```

```bash
python - <<'PY'
from pathlib import Path
import json
import os
import sys

repo_root = Path.cwd()
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "scripts"))

import run_kickoff_demo as rk
from alfred.orchestrator import orchestrate
from alfred.tools.persistence import list_write_receipts

workspace = Path(os.environ["DEMO_PROJECT_ROOT"])
db_path = str(rk.workspace_db_path(workspace))

cfg = rk.default_demo_config(workspace)
cfg.github.org = os.environ["ALFRED_DEMO_GITHUB_ORG"]
cfg.github.project_number = int(os.environ["ALFRED_DEMO_GITHUB_PROJECT_NUMBER"])
cfg.github.token_env_var = "GITHUB_TOKEN"

handover = rk._board_writer_handover(rk.KICKOFF_HANDOVER_ID, rk.KICKOFF_TASK_ID)
orchestrate(handover, cfg, db_path=db_path)

print(handover.tasks[0].result.output_summary)
print(json.dumps(
    list_write_receipts(
        db_path,
        handover_id=rk.KICKOFF_HANDOVER_ID,
        task_id=rk.KICKOFF_TASK_ID,
    ),
    indent=2,
))
PY
```

What to show:
- the board-writer result summary showing proposal-to-item mappings
- persisted write receipts in the workspace-local database
- the GitHub Project V2 board now showing 6-8 draft items
- title agreement between the reviewed proposal batch and the created GitHub items

Narration anchor:
- "GitHub is the projection shown after approval. The primary evidence is still the handover file, the persisted proposal batch, the approval state, and the write receipts."

## Evidence Bundle

Capture this minimum bundle during rehearsal:

- the persisted kickoff handover artifact at `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the external demo workspace]
- the kickoff harness compile confirmation line:
  - `[COMPILE] HandoverDocument compiled; tasks: ['TASK-SEED-BOARD-001']`
- the review-only proposal listing from `python scripts/run_kickoff_demo.py --workspace "$DEMO_PROJECT_ROOT" --review-only`
- the pending approval listing from the workspace-local persistence surface if you run the paused approval lane
- the write receipt listing from the workspace-local persistence surface after approval
- one screenshot of the blank GitHub Project before approval
- one screenshot of the populated GitHub Project after approval
- the final board-writer transcript line showing proposal-to-item mappings

## Rehearsal Acceptance Standard

The demo is only "demo-grade" when all of the following are true:

- two clean end-to-end rehearsal runs have completed against the same named GitHub Project V2 target, with the board reset to blank between runs
- each clean run follows the checked-in operator flow without off-script recovery steps
- the operator can show the full evidence bundle from this document for each run
- the operator does not need to explain any architecture caveat that is not already written in this script
- the board remains blank before approval and shows 6-8 draft items only after approval
- the reviewed proposal batch and the final GitHub item titles still match at the end of the run

Record the rehearsal timing thresholds before calling the package demo-grade:

- Kickoff harness target: human-supplied threshold `<= ______ minutes`
- Approval-to-write arc target: human-supplied threshold `<= ______ minutes`
- Full narrated demo target: human-supplied threshold `<= ______ minutes`

Pass/Fail rule:
- If both rehearsals stay within the agreed thresholds and produce the same evidence shape, mark Phase 5 rehearsal readiness as `PASS`.
- If timing is unstable, evidence is incomplete, or the operator needed unscripted caveats, mark it `PIVOT` and update this document before the next rehearsal.

## Fallback Plan

Use these branches exactly as written. Do not substitute manual outputs or board edits.

### Fallback - LLM Provider Failure During Kickoff

Trigger:
- the kickoff harness fails during compile or story generation
- the compiler or story generator returns an error
- the provider credential is missing or the model request fails

Response:
1. Retry the failed kickoff step once.
2. If the second attempt succeeds, continue with the standard flow and note the transient failure in rehearsal notes.
3. If the second attempt also fails, stop the demo and say that Alfred cannot truthfully continue because the governed proposal batch was never generated.

Do not do this:
- do not hand-write backlog items
- do not swap in an old proposal batch from a previous run
- do not skip directly to GitHub writes

Narration anchor:
- "The system stops here because the governing artifact was not successfully generated. We do not substitute manual output for a failed agent step."

### Fallback - GitHub Write Failure After Approval

Trigger:
- approval is recorded, but the board-writer step fails
- GitHub rejects the mutation
- rate limiting, auth failure, or project-target mismatch blocks draft-item creation

Response:
1. Do not regenerate proposals.
2. Preserve the reviewed proposal batch, approval state, board-writer transcript, and any partial write receipts already recorded.
3. Show that approval was granted but the downstream projection failed honestly.
4. If the failure was partial, keep the recorded receipts and rerun only the remaining write step after the cause is fixed.
5. If the failure was total, stop and explain that the checkpoint-gated flow prevented Alfred from pretending the board write succeeded.

Do not do this:
- do not clear or rewrite the proposal batch
- do not manually add GitHub items to mimic success
- do not hide partial receipts if some writes already landed

Narration anchor:
- "Approval exists, but the downstream board projection failed. The source artifact and approval record remain intact, so we can resume honestly instead of faking completion."

### Fallback - Board Not Blank At Start

Trigger:
- the target GitHub Project V2 board shows any existing items before the rehearsal begins

Response:
1. Stop before Step 5.
2. Reset or replace the board until it is visibly blank again.
3. Restart the rehearsal from the beginning so the blank-board proof remains truthful.

Do not do this:
- do not continue on a dirty board
- do not ask the audience to mentally subtract old items

Narration anchor:
- "The empty board is part of the proof. If the starting state is wrong, we reset it instead of weakening the story."

## Demo Narrator Notes

This demo shows Alfred using project docs as the governing protocol, not GitHub or hidden chat state. Alfred turns a fixed charter into a persisted kickoff handover, compiles that handover into structured work, generates the first governed backlog proposal through the orchestrator, pauses at a visible approval gate, and only then projects the approved result onto a blank GitHub Project. The important thing to emphasize is not raw autonomy but controlled coordination: the docs artifact comes first, approvals are explicit, and the board changes only after the governed checkpoint has been passed.

## Step-By-Step Operator Flow

1. Define the live demo variables in Terminal B.

```bash
export DEMO_PROJECT_ROOT=/tmp/cop_demo
export ALFRED_DEMO_GITHUB_ORG="<github-org>"
export ALFRED_DEMO_GITHUB_PROJECT_NUMBER="<project-number>"
```

Observable evidence: the operator can say exactly which external workspace path and which blank GitHub Project are in scope for this run.

2. Start Alfred's API in Terminal A from the repository root.

```bash
alfred serve --host 127.0.0.1 --port 8000
```

Observable evidence: the API process stays running and logs `application startup`.

3. Verify liveness and readiness in Terminal B.

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
curl -s http://127.0.0.1:8000/dashboard
```

Observable evidence:
- `/healthz` returns `{"status":"ok"}`
- `/readyz` returns `{"status":"ready"}`
- `/dashboard` returns a JSON payload and should show `pending_approvals_count` as `0` before the demo begins

4. Confirm the GitHub Project is blank in the browser before Alfred does anything.

Action: open the target Project V2 board and verify it contains `0` items.

Observable evidence: the board UI is visibly empty. This is the baseline "before approval, before write" screen.

5. Initialise the external demo workspace in Terminal B.

```bash
python scripts/init_demo_workspace.py --workspace "$DEMO_PROJECT_ROOT"
```

Observable evidence:
- the command prints `Workspace initialised at ...`
- the new workspace contains `<demo-project-root>/docs/CHARTER.md` [future-doc: path inside the external demo workspace]
- `<demo-project-root>/docs/handovers/` [future-path: directory inside the external demo workspace] exists and is empty at kickoff

6. Verify the frozen workspace shape before Alfred generates anything.

```bash
find "$DEMO_PROJECT_ROOT" -maxdepth 2 -print | sort
```

Observable evidence:
- `README.md` exists at the workspace root
- `docs/CHARTER.md` exists and is the copied charter source
- `docs/handovers/` exists with no pre-existing handover files

7. Run the kickoff harness in Terminal B.

```bash
python scripts/run_kickoff_demo.py --workspace "$DEMO_PROJECT_ROOT"
```

Observable evidence:
- `[INIT] Workspace verified at ...`
- `[PERSIST] Wrote .../docs/handovers/ALFRED_HANDOVER_1.md`
- `[COMPILE] HandoverDocument compiled; tasks: ['TASK-SEED-BOARD-001']`
- `[ORCHESTRATE] Dispatching TASK-SEED-BOARD-001 via orchestrate(...)`
- `[STORIES] N proposals persisted:` where `N` is between 6 and 8
- `APPROVAL GATE`

8. Show the persisted kickoff artifact and keep the board untouched.

```bash
ls "$DEMO_PROJECT_ROOT/docs/handovers/ALFRED_HANDOVER_1.md"
sed -n '1,40p' "$DEMO_PROJECT_ROOT/docs/handovers/ALFRED_HANDOVER_1.md"
```

Observable evidence:
- the first governed handover now exists at `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` [future-doc: first handover path inside the external demo workspace]
- the operator can point to the markdown artifact as source of truth
- the GitHub Project is still blank at this moment

9. Prove the review surface survives pause/resume without regenerating proposals.

```bash
python scripts/run_kickoff_demo.py --workspace "$DEMO_PROJECT_ROOT" --review-only
```

Observable evidence:
- `[REVIEW] Reading persisted proposals from .../.alfred/state.sqlite3`
- the same proposal batch is rendered from persistence
- the board is still blank because review-only mode does not write to GitHub

10. State the approval boundary clearly before any board mutation.

Use this wording when asking for permission to proceed:

> Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

Observable evidence:
- pre-approval state is still visible in three places at once: persisted proposal list, persisted handover file, and blank GitHub Project board
- the operator can truthfully say that the kickoff handover review was manual, but the board write is still gated by runtime checks

11. After explicit human approval, run the Phase 4 approval-to-write arc from Terminal B.

If you already used the paused approval lane from `Evidence - Approval Pending`, skip this fast path and continue with `Evidence - Post-Write` instead so you keep the same approval row all the way through the write.

```bash
python - <<'PY'
from pathlib import Path
import os
import sys

repo_root = Path.cwd()
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "scripts"))

import run_kickoff_demo as rk

workspace = Path(os.environ["DEMO_PROJECT_ROOT"])
cfg = rk.default_demo_config(workspace)
cfg.github.org = os.environ["ALFRED_DEMO_GITHUB_ORG"]
cfg.github.project_number = int(os.environ["ALFRED_DEMO_GITHUB_PROJECT_NUMBER"])
cfg.github.token_env_var = "GITHUB_TOKEN"

raise SystemExit(rk.run_phase4_arc(workspace, config=cfg))
PY
```

Observable evidence:
- `[PRE] proposal status counts: pending=N approved=0 written=0`
- `[PHASE4] Dispatching board_writer with no approval - expecting refusal`
- `[PHASE4] Refused: Board write refused ...`
- `[PHASE4] Approval recorded: id=... action=WRITE_GITHUB_PROJECT_V2 target=TASK-SEED-BOARD-001`
- `[PHASE4] Dispatching board_writer with approval - expecting writes`
- `[POST] proposal status counts: pending=0 approved=0 written=N`
- one `proposal_id -> github_item_id` receipt line per written story

12. Refresh the GitHub Project board in the browser and close the demo loop.

Action: reload the Project V2 board and compare the visible draft item titles against the receipt lines printed in Terminal B.

Observable evidence:
- the board now shows 6-8 draft items
- the titles match the persisted proposal batch that was reviewed before approval
- the docs artifact in `<demo-project-root>/docs/handovers/ALFRED_HANDOVER_1.md` remains the governing source, with GitHub shown as the downstream projection

## Key Narration Lines

- "The docs artifact came first; the board stayed empty until the approval step."
- "The proposal review surface survives pause/resume because Alfred reads it back from persistence, not by regenerating."
- "The only runtime-enforced approval gate today is the GitHub board write. That is deliberate, visible, and auditable."
