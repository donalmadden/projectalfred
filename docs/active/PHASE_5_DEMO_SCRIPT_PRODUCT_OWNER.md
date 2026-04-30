# Phase 5 Demo Script - Product Owner Version

## Start Here

This is the simple version of the Alfred demo script.

You do **not** need to explain code, databases, or architecture in detail.
Your job is just to guide people through the story:

1. We start with a blank GitHub board.
2. Alfred creates a written kickoff plan from the charter.
3. Alfred pauses before changing the board.
4. Only after approval does Alfred add the first draft backlog items to GitHub.

That is the whole point of the demo.

## What Success Looks Like

By the end of the demo, the audience should clearly see:

- the project starts blank
- Alfred creates a written handover first
- Alfred pauses for approval before touching GitHub
- after approval, 6-8 draft backlog items appear on the GitHub board

## The One-Sentence Story

If you want a short, non-technical way to explain Alfred, say this:

> Alfred turns a project charter into a written kickoff plan, shows the proposed backlog for review, and only updates GitHub after a human says yes.

## What You Need Open

- Browser tab: `https://github.com/users/donalmadden/projects/5`
- Terminal A: for starting Alfred
- Terminal B: for running the demo steps

## Important Reassurance

- You do not need to memorise anything.
- You can copy and paste every command in this document.
- If something fails twice, stop calmly and say we are pausing rather than faking the result.

## Before The Demo

Make sure these are true:

- the GitHub Project is `Alfred Demo Sample`
- the GitHub Project is empty before you begin
- someone has already given you the required logins and API keys
- you are in the project root folder before running any commands

## Step 1 - Show The Blank Board

Open this page in your browser:

`https://github.com/users/donalmadden/projects/5`

Check that the board has **0 items**.

What to say:

> We are starting from a blank project board so everyone can clearly see what Alfred adds and when.

## Step 2 - Start Alfred

In Terminal A, paste this:

```bash
alfred serve --host 127.0.0.1 --port 8000
```

What you should see:

- Alfred starts running
- the terminal stays open

What to say:

> Alfred is now running locally and ready for the kickoff flow.

## Step 3 - Set The Demo Variables

In Terminal B, paste this:

```bash
export DEMO_PROJECT_ROOT=/tmp/cop_demo
export ALFRED_DEMO_GITHUB_ORG="donalmadden"
export ALFRED_DEMO_GITHUB_PROJECT_NUMBER="5"
```

What to say:

> These settings tell Alfred which demo workspace to use and which GitHub Project to update.

## Step 4 - Run The Safety Check

In Terminal B, paste this:

```bash
python scripts/demo_preflight.py --base-url http://127.0.0.1:8000
```

What you should see:

- `PASS` lines for the environment checks
- `PASS` lines for `/healthz` and `/readyz`

What to say:

> This is just a quick safety check so we know the demo is ready before we start.

If the check fails:

- retry once after fixing the obvious issue
- if it still fails, stop the demo and ask for technical help

## Step 5 - Create The Demo Workspace

In Terminal B, paste this:

```bash
python scripts/init_demo_workspace.py --workspace "$DEMO_PROJECT_ROOT"
```

What you should see:

- a message saying the workspace was initialised

What to say:

> Alfred is creating the starting project workspace. This is the blank project it will work from.

## Step 6 - Run The Kickoff

In Terminal B, paste this:

```bash
python scripts/run_kickoff_demo.py --workspace "$DEMO_PROJECT_ROOT"
```

What you should see:

- Alfred writes the first handover file
- Alfred compiles that handover
- Alfred generates the first set of proposed backlog items
- Alfred stops at `APPROVAL GATE`

What to say:

> Alfred has now created the written kickoff handover and proposed the first backlog items, but it has not changed GitHub yet.

## Step 7 - Say The Approval Line

When the approval gate appears, say this exact sentence:

> Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

Then pause briefly so the audience feels the checkpoint.

What to say next:

> This pause is the key control point. Alfred can prepare the work, but it does not update the board until a human approves it.

## Step 8 - Run The Board Update

After approval, in Terminal B, paste this whole block:

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

What you should see:

- Alfred first shows that it refuses to write without approval
- then it records the approval
- then it writes the draft items to GitHub
- then it prints the write receipts

What to say:

> Alfred is now using the approved plan to populate the GitHub board. The board is the output, not the source of truth.

## Step 9 - Refresh GitHub

Refresh this page:

`https://github.com/users/donalmadden/projects/5`

What you should see:

- 6-8 draft backlog items on the board

What to say:

> Now you can see the result on GitHub. The important thing is that the written handover came first, the approval happened in the middle, and the board changed only at the end.

## The Three Things To Emphasise

If you get flustered, come back to these:

- Alfred writes the plan first
- Alfred pauses before changing GitHub
- Alfred only updates GitHub after approval

## Simple Fallback Lines

If the kickoff step fails twice:

> We’re going to pause here rather than fake the output. Alfred only works from a real generated handover and proposal set.

If the GitHub write fails:

> Approval was recorded, but the board update failed. We can show the approved plan and the checkpoint honestly without pretending the write worked.

If the board is not blank at the start:

> We need to reset the board first, because the empty starting point is part of the proof.

## Things Not To Do

- do not manually add items to the GitHub board
- do not continue if the board is not blank at the start
- do not invent backlog items by hand if Alfred fails
- do not worry about explaining every command

## Tiny Glossary

- **Charter**: the short project brief
- **Handover**: the written kickoff plan Alfred creates
- **Approval gate**: the pause before GitHub is updated
- **GitHub Project**: the board the audience sees at the end

## Final Closing Line

If you want a clean final sentence, use this:

> Alfred helps the team start from a clear written plan, keeps a human in control, and only turns that plan into GitHub work after approval.
