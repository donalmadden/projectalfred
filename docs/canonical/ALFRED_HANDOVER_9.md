
# Alfred's Handover Document #9 — Phase 2: Execution Harness & Orchestrator Close

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_9
**date:** 2026-04-29
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_8
**baseline_state:** Phase 0 (scenario freeze) and Phase 1 (kickoff charter, demo-project layout, kickoff handover outline) are fully ratified and locked; this handover executes Phase 2 only — closing the narrow execution harness that takes a compiled `HandoverDocument` and runs it through `orchestrate(...)` against the demo workspace, halting cleanly at the approval gate.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_8.md` — Phase 1 canonical baseline; confirms charter, layout, and handover-outline freeze decisions that Phase 2 inherits
- `docs/active/ALFRED_BLANK_PROJECT_KICKOFF_DEMO_PLAN.md` — multi-phase build plan; authoritative scope brief for all phases
- The archived Phase 0 freeze record for the blank-project kickoff demo — all five decisions are locked
- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — frozen charter text the harness copies verbatim into the demo workspace
- `docs/active/DEMO_PROJECT_LAYOUT.md` — frozen Phase 1 filesystem spec the harness must reproduce exactly
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — frozen Phase 1 kickoff-handover structure, including `TASK-SEED-BOARD-001` and the verbatim approval-gate wording
- `docs/protocol/architecture.md` — Alfred runtime architecture; orchestrator contract and agent roster
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism constraints in effect

Phase 2 is the first handover that touches executable code. Its scope is tightly bounded: one script, one workspace initialiser, one orchestrated run that halts at the approval gate. Phase 3 (proposal-persistence schema), Phase 4 (GitHub Project V2 write path), and Phase 5 (rehearsal runbook) are explicitly out of scope and must not be pre-empted here.

The charter text the harness will consume (`docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`) and the target filesystem shape (`docs/active/DEMO_PROJECT_LAYOUT.md`) are both frozen Phase 1 artifacts that already exist today. The harness must treat them as read-only inputs.

---

## WHAT EXISTS TODAY

### Git History

```
e465cfd  updated for handover 9
b8e822e  tidied up docs
7101379  added postmortem to handover and updated script
3013445  demo: implement phase 1 kickoff docs
362c189  docs: register ALFRED_HANDOVER_8 in manifest
87fa16b  added first demo handover
08d4e4b  validator: generalize toolchain checks and ignore deferred doc links
35bde4a  demo: phase 0 freeze + repurpose canonical generator for kickoff demo
9309c68  docs: refine Alfred docs-native kickoff direction
994bcb3  docs: add Alfred operationalisation brief
6a71006  chore: ignore local remember state
a75bf85  docs: phase 8 portfolio polish and governance
```

### Module & Agent Inventory

The following modules **exist today** in the Alfred repository and are relevant to Phase 2:

- `src/alfred/api.py` — FastAPI application (11 endpoints); exists today
- `src/alfred/orchestrator.py` — runtime coordinator exposing `orchestrate(...)`; exists today (per `src/alfred` top-level names)
- `src/alfred/cli.py` — CLI entry point declared in `pyproject.toml` as `alfred.cli:main`; exists today
- `src/alfred/agents/story_generator.py` — Story Generator agent; exists today (named in frozen `KICKOFF_HANDOVER_OUTLINE.md` `TASK-SEED-BOARD-001`)
- `src/alfred/agents/compiler.py` — Handover compiler; exists today
- `src/alfred/agents/planner.py` — Planner agent; exists today
- `src/alfred/agents/quality_judge.py` — Quality Judge agent; exists today
- `src/alfred/agents/retro_analyst.py` — Retro Analyst agent; exists today
- `src/alfred/tools/persistence.py` — persistence layer; exists today
- `src/alfred/tools/github_api.py` — GitHub API tool; exists today (Phase 4 will use it for board writes; Phase 2 does not call it)
- `src/alfred/tools/llm.py` — LLM tool; exists today
- `src/alfred/tools/rag.py` — RAG tool; exists today
- `src/alfred/tools/docs_policy.py` — docs-policy tool; exists today
- `src/alfred/tools/git_log.py` — git-log tool; exists today
- `src/alfred/tools/logging.py` — logging tool; exists today
- `src/alfred/tools/reference_doc_validator.py` — reference-doc validator tool; exists today
- `src/alfred/tools/repo_facts.py` — repo-facts tool; exists today
- `src/alfred/schemas` — schema package; exists today (one module per schema concern)

**Partial state / declared-but-unimplemented:**

- The demo execution harness (scripts/run_kickoff_demo.py) is **declared but unimplemented** — it is planned for Phase 2 and does not exist yet.
- The demo workspace initialiser (scripts/init_demo_workspace.py) is **declared but unimplemented** — planned for Phase 2.

**Phase 1 frozen docs that exist today:**

- `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` — exists today
- `docs/active/DEMO_PROJECT_LAYOUT.md` — exists today
- `docs/active/KICKOFF_HANDOVER_OUTLINE.md` — exists today

### Phase 1 Deliverables Inherited (Do Not Revisit)

Phase 1 produced three frozen artifacts that Phase 2 consumes as read-only inputs:

1. **Charter content** — `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` defines the exact text the harness copies into `<demo-project-root>/docs/CHARTER.md` [future-path: file inside the external demo workspace].
2. **Demo-project layout** — `docs/active/DEMO_PROJECT_LAYOUT.md` defines the exact filesystem tree (`README.md`, docs/CHARTER.md, docs/handovers) the workspace initialiser must reproduce.
3. **Kickoff handover outline** — `docs/active/KICKOFF_HANDOVER_OUTLINE.md` defines the sections, `TASK-SEED-BOARD-001`, and the verbatim approval-gate wording the orchestrated run must honour.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Demo scenario is `Customer Onboarding Portal` — locked.** No domain substitution before the slice works end-to-end.
2. **Demo project starts with exactly `README.md`, docs/CHARTER.md, and empty docs/handovers.** No `src/`, no tests, no CI in the demo workspace.
3. **6–8 story proposals is the success criterion.** Fewer than 6 or more than 8 is a task failure, not a redefinition.
4. **Approval gate is verbatim-locked.** The wording from `KICKOFF_HANDOVER_OUTLINE.md` must be used exactly (with `N` replaced by count).
5. **Board writes are Phase 4.** Phase 2 must halt at the approval gate; calling `github_api` to write items is explicitly forbidden here.
6. **Document as protocol.** The project `docs/` surface (inside the demo workspace) is the source of truth; the GitHub Project board is a downstream projection.
7. **`orchestrate(...)` is the primary execution surface.** No direct agent calls may bypass the orchestrator in the main demo execution path.
8. **Pyright is the type checker** — `mypy` is not used.

---

## HARD RULES

1. **Do not revisit any Phase 0 or Phase 1 freeze decision.** Scenario name, demo-project shape, board target, success criterion, narrated arc, charter text, demo-project layout, kickoff handover outline, approval-gate wording, and `TASK-SEED-BOARD-001` spec are all locked. If implementation creates an apparent conflict, surface it as an open question.
2. **Do not implement the GitHub Project V2 write path.** Phase 4 owns that. Phase 2 must demonstrate that the run halts cleanly at the gate without calling `github_api` for board mutations.
3. **Do not build proposal-persistence schema or approval records.** Phase 3 owns that. Phase 2 only needs to surface the `StoryProposal` items at the gate in human-readable form; durable structured persistence is deferred.
4. **The orchestrator must be the primary execution surface.** No direct agent calls may compose the main execution path. `orchestrate(...)` is called; agents are dispatched through it.
5. **The demo workspace is external to this repository.** The harness writes into a path the operator supplies (e.g. `--workspace /path/to/demo-project`). It must never write into Alfred's own `docs/` tree.
6. **Charter content is copied verbatim.** The harness must not rewrite, summarise, or truncate the charter text when populating `<demo-project-root>/docs/CHARTER.md` [future-path: file inside the external demo workspace].
7. **Script files belong under `scripts/` using `*.py`.** Per the `script` placement rule: `scripts/run_kickoff_demo.py` and `scripts/init_demo_workspace.py` are the correct canonical locations.
8. **No `mypy`.** The repository uses `pyright` for type-checking; any CI or verification commands must invoke `pyright`, not `mypy`.
9. **No Docker in Phase 2.** Docker usage is not authorised for this phase.
10. **Harness must not write to `docs/canonical/` in this repo.** The canonical promotion of `ALFRED_HANDOVER_9.md` is a documentation task, not part of the execution harness.

---

## WHAT THIS PHASE PRODUCES

- `scripts/init_demo_workspace.py` — **to be created in this phase**; workspace initialiser that creates the frozen demo-project layout (per `script` placement rule: `scripts/`, `*.py`)
- `scripts/run_kickoff_demo.py` — **to be created in this phase**; the narrow execution harness that compiles the kickoff handover and dispatches it through `orchestrate(...)`, halting at the approval gate (per `script` placement rule)
- `tests/test_scripts/test_init_demo_workspace.py` — **to be created in this phase**; unit tests for the workspace initialiser (per `test` placement rule: `tests/`, `test_*.py`)
- `tests/test_scripts/test_run_kickoff_demo.py` — **to be created in this phase**; unit/integration tests for the demo harness (per `test` placement rule)
- `docs/canonical/ALFRED_HANDOVER_9.md` — **to be created in this phase**; this handover promoted after human approval (per `handover_doc` naming convention: `ALFRED_HANDOVER_\d+`)

**Out of scope:**
- Proposal-persistence schema or approval records → Phase 3
- GitHub Project V2 write path → Phase 4
- Rehearsal runbook and demo script → Phase 5
- Any changes to `src/alfred/api.py` endpoints beyond what is needed to expose the orchestrator path already available
- Multi-sprint planning, retrospectives, dashboards, story editing

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Implement workspace initialiser | `scripts/init_demo_workspace.py` + tests | CHECKPOINT-1 |
| 2 | Implement demo execution harness | `scripts/run_kickoff_demo.py` + tests | CHECKPOINT-2 |
| 3 | Verify end-to-end orchestrated run halts at gate | Observable log output + printed approval prompt | CHECKPOINT-2 |
| 4 | Promote this handover | `docs/canonical/ALFRED_HANDOVER_9.md` | — |

---

## TASK 1 — Workspace Initialiser

**Goal:** Produce `scripts/init_demo_workspace.py` that creates the exact frozen demo-project filesystem layout from `docs/active/DEMO_PROJECT_LAYOUT.md` at a caller-supplied path, copying charter content verbatim.

### Implementation

1. **Accept `--workspace PATH` argument** — The script takes a single required argument: the absolute or relative path to the demo-project root directory. It must refuse to overwrite an existing non-empty directory without `--force`.

2. **Create the frozen layout** — Materialise exactly:
   ```
   <workspace>/
   ├── README.md
   └── docs/
       ├── CHARTER.md
       └── handovers/
   ```
   - `README.md` content: verbatim from `DEMO_PROJECT_LAYOUT.md` ("Customer Onboarding Portal is a greenfield product workspace…").
   - `docs/CHARTER.md` [future-path: file inside the external demo workspace]: verbatim copy of `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`. **Do not summarise or truncate.**
   - `docs/handovers/` [future-path: directory inside the external demo workspace]: created as an empty directory. No `.gitkeep` per `DEMO_PROJECT_LAYOUT.md`.

3. **Idempotency guard** — If `--workspace` already has the correct layout (all three paths present, charter content matches), print `Workspace already initialised — no changes made.` and exit 0.

4. **Type annotations + pyright compliance** — All functions must carry full type annotations. Verify with `pyright scripts/init_demo_workspace.py`.

5. **Per placement rule** — File lands at `scripts/init_demo_workspace.py` (script placement rule: `scripts/`, `*.py`). Mirrored tests at `tests/test_scripts/test_init_demo_workspace.py` (test placement rule: `tests/`, `test_*.py`).

### Verification

```bash
# Create a fresh workspace
python scripts/init_demo_workspace.py --workspace /tmp/cop_demo

# Confirm layout
ls /tmp/cop_demo/
ls /tmp/cop_demo/docs/
ls /tmp/cop_demo/docs/handovers/

# Confirm charter content is verbatim (no truncation)
diff /tmp/cop_demo/docs/CHARTER.md docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md

# Confirm idempotency
python scripts/init_demo_workspace.py --workspace /tmp/cop_demo
# Expected: "Workspace already initialised — no changes made."

# Type check
pyright scripts/init_demo_workspace.py

# Unit tests
python -m pytest tests/test_scripts/test_init_demo_workspace.py -v
```

**Expected:**
- `ls /tmp/cop_demo/` shows `README.md` and `docs/`
- `ls /tmp/cop_demo/docs/` shows `CHARTER.md` and `handovers/`
- `ls /tmp/cop_demo/docs/handovers/` shows an empty directory (no `.gitkeep`)
- `diff` exits 0 (files are byte-identical)
- Second invocation prints idempotency message and exits 0
- `pyright` reports zero errors
- All unit tests pass

**Suggested commit message:** `scripts: task 1 — demo workspace initialiser`

### CHECKPOINT-1 — Workspace Layout Verified

**Question:** Does the initialised demo workspace exactly match the Phase 1 frozen spec in `DEMO_PROJECT_LAYOUT.md`, with verbatim charter content and an empty `docs/handovers/` directory?

**Evidence required:**

Paste verbatim:
1. Output of `ls /tmp/cop_demo/ && ls /tmp/cop_demo/docs/ && ls /tmp/cop_demo/docs/handovers/`
2. Output of `diff /tmp/cop_demo/docs/CHARTER.md docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md` (must show no diff)
3. Output of second `init_demo_workspace.py` invocation (idempotency message)
4. `pyright` exit code and error count
5. Pytest summary line

| Observation | Likely call |
|---|---|
| All files present, `diff` clean, tests pass, pyright zero errors | PROCEED to Task 2 |
| Charter content differs (truncated or rewritten) | STOP — charter must be verbatim per HARD RULE 6 |
| `.gitkeep` present in `docs/handovers/` | PIVOT — remove it; DEMO_PROJECT_LAYOUT.md forbids it |
| pyright reports errors | PIVOT — fix type errors before proceeding |
| Tests fail | STOP — do not proceed until tests are green |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 2.

---

## TASK 2 — Demo Execution Harness

**Goal:** Produce `scripts/run_kickoff_demo.py` that accepts a compiled `HandoverDocument` (or compiles one from the demo workspace's kickoff handover draft), dispatches it through `orchestrate(...)`, and halts cleanly at the approval gate, printing the verbatim approval prompt with the actual `N` story-proposal count.

### Implementation

1. **Accept `--workspace PATH` and `--handover PATH` arguments** — `--workspace` points to the demo-project root. `--handover` (optional) points to a pre-written draft handover markdown file; if omitted, the script must locate `docs/canonical/ALFRED_HANDOVER_1.md` [future-path: first handover path inside the demo workspace] inside the workspace or generate a draft using the compiler agent from the workspace's `docs/CHARTER.md` [future-path: file inside the external demo workspace].

2. **Persist the kickoff handover draft** — Before compiling, the script must write the kickoff handover draft to `<workspace>/docs/handovers/ALFRED_HANDOVER_1.md` [future-path: first handover path inside the demo workspace] using the outline from `KICKOFF_HANDOVER_OUTLINE.md`. This is the first Alfred artifact persisted to the demo project's docs surface.

3. **Compile to `HandoverDocument`** — Call the compiler (via `src/alfred/agents/compiler.py`) to turn the persisted markdown into a structured `HandoverDocument`. The compiler must be invoked through the existing module interface, not called directly as a subprocess.

4. **Dispatch through `orchestrate(...)`** — Pass the compiled `HandoverDocument` to `orchestrate(...)` from `src/alfred/orchestrator.py`. The orchestrator must dispatch `TASK-SEED-BOARD-001` to `src/alfred/agents/story_generator.py` as specified in `KICKOFF_HANDOVER_OUTLINE.md`.

5. **Halt at approval gate** — After story generation, the script must:
   - Collect the `StoryProposal` list returned/emitted by the story-generator dispatch
   - Verify the count is within 6–8; if not, print an error message and exit non-zero
   - Print the verbatim approval prompt from `KICKOFF_HANDOVER_OUTLINE.md` with `N` replaced by the actual count:
     > `Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.`
   - Print a human-readable listing of each `StoryProposal` (title, description, acceptance criteria, story points)
   - Exit 0 after printing the gate prompt — **do not call `github_api` or perform any board writes**

6. **No board writes in Phase 2** — Any call to `src/alfred/tools/github_api.py` for board mutation is forbidden in this script. Per HARD RULE 2.

7. **Type annotations + pyright compliance** — Full type annotations on all functions. Verify with `pyright scripts/run_kickoff_demo.py`.

8. **Per placement rule** — File lands at `scripts/run_kickoff_demo.py` (script placement rule). Mirrored tests at `tests/test_scripts/test_run_kickoff_demo.py` (test placement rule).

### Implementation Notes on the Orchestrator Interface

- The executor must inspect `src/alfred/orchestrator.py` to understand the current `orchestrate(...)` signature before writing the harness. Do not assume a specific function signature — read the existing module first.
- If the orchestrator does not yet have a path that accepts a `HandoverDocument` and dispatches a named task to a specific agent, the smallest honest adapter is: a thin wrapper function in `scripts/run_kickoff_demo.py` itself that calls `orchestrate(...)` with the task spec derived from the compiled handover. This adapter must still route through `orchestrate(...)`, not bypass it.
- If the compiler agent does not yet expose a simple `compile(markdown: str) -> HandoverDocument` interface, document the gap as an open question in the post-mortem rather than inventing a workaround.

### Verification

```bash
# Initialise workspace (Task 1 must be complete)
python scripts/init_demo_workspace.py --workspace /tmp/cop_demo

# Run the demo harness
python scripts/run_kickoff_demo.py --workspace /tmp/cop_demo

# Expected terminal output includes:
#   1. Log lines showing orchestrate(...) dispatch
#   2. "APPROVAL GATE REACHED" or equivalent section header
#   3. The verbatim approval prompt with N substituted
#   4. A numbered listing of N StoryProposal items (6–8)
#   5. Exit 0

# Verify handover was persisted
ls /tmp/cop_demo/docs/handovers/
# Expected: ALFRED_HANDOVER_1.md present

# Verify no board writes occurred (no github_api mutation call in logs)
python scripts/run_kickoff_demo.py --workspace /tmp/cop_demo 2>&1 | grep -i "github\|board\|write\|create_story"
# Expected: no mutation log lines; only the approval prompt mentions the board

# Type check
pyright scripts/run_kickoff_demo.py

# Unit/integration tests
python -m pytest tests/test_scripts/test_run_kickoff_demo.py -v
```

**Expected:**
- `ALFRED_HANDOVER_1.md` [future-path: first handover path inside the demo workspace] is present under `<workspace>/docs/handovers/`
- Terminal shows the verbatim approval prompt with `N` in range 6–8
- Terminal shows a human-readable proposal listing with all required fields (title, description, acceptance criteria, story points)
- No `github_api` board-mutation calls appear in output or logs
- `pyright` reports zero errors
- All tests pass

**Suggested commit message:** `scripts: task 2 — demo execution harness (orchestrate + gate)`

### CHECKPOINT-2 — Orchestrated Run Halts at Gate

**Question:** Does the demo execution harness visibly route through `orchestrate(...)`, produce 6–8 `StoryProposal` items, print the verbatim approval prompt, and halt without any board writes?

**Evidence required:**

Paste verbatim:
1. Full terminal output of `python scripts/run_kickoff_demo.py --workspace /tmp/cop_demo`
2. Output of `ls /tmp/cop_demo/docs/handovers/` (must show `ALFRED_HANDOVER_1.md`)
3. The exact approval-prompt line printed, with `N` replaced by the actual count
4. Confirmation that the count N is between 6 and 8 (inclusive)
5. Output of the `grep` command checking for board-mutation log lines (must be empty)
6. `pyright` exit code and error count
7. Pytest summary line

| Observation | Likely call |
|---|---|
| All evidence clean, N in 6–8, no board writes, tests pass | PROCEED to Task 3 (promote handover) |
| Orchestrator is bypassed (direct agent calls compose the path) | STOP — violates HARD RULE 4; must route through `orchestrate(...)` |
| N < 6 or N > 8 | STOP — story-generator output out of bounds; do not advance to Phase 3 |
| Board-mutation log lines present | STOP — violates HARD RULE 2; remove any `github_api` write calls |
| Approval prompt wording differs from frozen spec | PIVOT — replace with verbatim wording from `KICKOFF_HANDOVER_OUTLINE.md` |
| `ALFRED_HANDOVER_1.md` absent from workspace | PIVOT — harness must persist the handover draft before compiling |
| pyright errors | PIVOT — fix before proceeding |
| Tests fail | STOP — do not proceed until green |

**STOP HERE.** Paste evidence and wait for direction before proceeding to Task 3.

---

## TASK 3 — Verify End-to-End and Register in Manifest

**Goal:** Confirm observable Phase 2 completion evidence and register the two new scripts in `docs/DOCS_MANIFEST.yaml` if policy requires it (check `docs/DOCS_POLICY.md`).

### Implementation

1. **Run both scripts in sequence from a clean `/tmp` path** — delete `/tmp/cop_demo` (if present), re-run `init_demo_workspace.py`, then `run_kickoff_demo.py`, and capture the full output.
2. **Check manifest policy** — Read `docs/DOCS_POLICY.md` to determine whether `scripts/` files require manifest entries. If yes, add entries for both scripts in `docs/DOCS_MANIFEST.yaml`.
3. **No new `## WHAT EXISTS TODAY` claims need to be invented** — the scripts did not exist at handover-write time; they become real only after Task 1 and Task 2 are executed.

### Verification

```bash
rm -rf /tmp/cop_demo
python scripts/init_demo_workspace.py --workspace /tmp/cop_demo
python scripts/run_kickoff_demo.py --workspace /tmp/cop_demo

# Full regression
python -m pytest tests/test_scripts/ -v

# Pyright full check
pyright scripts/init_demo_workspace.py scripts/run_kickoff_demo.py
```

**Expected:** Clean run, all tests pass, pyright zero errors.

**Suggested commit message:** `demo: phase 2 complete — execution harness verified`

---

## TASK 4 — Promote This Handover

**Goal:** Promote the approved draft to `docs/canonical/ALFRED_HANDOVER_9.md` and register it in `docs/DOCS_MANIFEST.yaml`.

### Implementation

1. Copy the approved draft to `docs/canonical/ALFRED_HANDOVER_9.md` (per `handover_doc` naming convention: `ALFRED_HANDOVER_\d+`).
2. Add the manifest entry per `docs/DOCS_POLICY.md`.
3. Run the promotion validator: `python scripts/validate_alfred_handover.py docs/canonical/ALFRED_HANDOVER_9.md` (if the validator script exists today).

### Verification

```bash
ls docs/canonical/ALFRED_HANDOVER_9.md
grep ALFRED_HANDOVER_9 docs/DOCS_MANIFEST.yaml
```

**Expected:** File exists, manifest entry present.

**Suggested commit message:** `docs: promote ALFRED_HANDOVER_9 canonical handover`

---

## WHAT NOT TO DO

1. **Do not call `github_api` for board mutations in Phase 2.** The approval gate must halt the run. Board writes belong to Phase 4 exclusively.
2. **Do not bypass `orchestrate(...)`.** Composing the execution path from direct agent calls is a demo-integrity failure per HARD RULE 4 and the demo plan's Hard Rule 1.
3. **Do not rewrite or summarise the charter text.** `CHARTER.md` [future-path: file inside the external demo workspace] must be a byte-identical copy of `docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md`.
4. **Do not add `.gitkeep` to `docs/handovers/`.** `DEMO_PROJECT_LAYOUT.md` explicitly forbids it.
5. **Do not write into Alfred's own `docs/` tree.** The harness targets the demo workspace path, not this repository's documentation.
6. **Do not implement proposal-persistence schema or approval records.** Phase 3 owns that. Phase 2 only needs human-readable output at the gate.
7. **Do not use `mypy`.** The repository uses `pyright`; CI verification commands must invoke `pyright`.
8. **Do not pre-empt Phase 3–5 scope.** If it is tempting to "just wire in" GitHub writes or approval records while the harness is open, resist. The slice must close cleanly at Phase 2 before Phase 3 begins.
9. **Do not place scripts anywhere other than `scripts/`.** Per the `script` placement rule, both new files belong at `scripts/init_demo_workspace.py` and `scripts/run_kickoff_demo.py`; placing them at the repo root or under `src/` is wrong.
10. **Do not invent orchestrator or compiler interfaces without inspecting the actual modules first.** Read `src/alfred/orchestrator.py` and `src/alfred/agents/compiler.py` before writing the harness; adapters must match real signatures, not assumed ones.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section before closing the work. The next planner or reviewer must be able to cold-start from this artifact alone.

**What worked:**
- The split into `scripts/init_demo_workspace.py` and `scripts/run_kickoff_demo.py` (vs. the failed candidate's single combined script) kept each module under one responsibility and made test isolation trivial. Idempotency in the initialiser was straightforward because the spec is small enough to verify by content equality.
- The compiler (`run_compiler` via `alfred.agents.compiler`) extracted `TASK-SEED-BOARD-001` correctly on the first live run from the explicit `## TASK TASK-SEED-BOARD-001 — Generate Kickoff Backlog` markdown block plus an inline `**Agent type:** story_generator` line. No retry loop or revised prompt was needed.
- Dependency-injecting the compile and inner-story-runner functions into `run_demo` let the entire harness be exercised end-to-end in unit tests without any LLM credentials. The live LLM run on `/tmp/cop_demo` produced 8 structured `Story` items with full title/description/acceptance_criteria/story_points fields, the verbatim approval prompt, and a clean exit 0.
- All five methodology properties held: the document was the protocol, the approval gate was the checkpoint (no board write without human approval), reasoning agents (story generator) ran under their schemas, the post-mortem (this section) is embedded in the artifact, and the run is fully reconstructable from the workspace state on a cold start.

**What was harder than expected:**
- The orchestrator's default `_story_runner` discards structured `StoryGeneratorOutput`: only a count summary survives in `TaskResult.output_summary`. The Phase 2 acceptance criterion ("surface structured `StoryProposal` items at the gate") therefore could not be met by reading `task.result` after orchestration. This was solved without core changes — see deviations below — but it is a real friction point that Phase 3 should address explicitly when designing the persistence schema.
- `AlfredConfig.llm.model` defaults to the empty string. The first live run failed at the Anthropic adapter with `model: String should have at least 1 character`. The harness now sets a default in `default_demo_config()`, but the broader pattern (a default config that cannot actually drive an LLM call without further setup) is a footgun for future demo callers and should be tightened.
- The pre-existing failing tests in `tests/test_scripts/test_generate_next_canonical_handover.py` (3 failures, stale assertions about Phase 1 sprint goal and HANDOVER_8 source path) are unrelated to Phase 2 work but make a "full pytest" reading noisy. They should be fixed during a future docs-tooling phase.

**Decisions made during execution (deviations from this plan):**
- **Capture structured story output via `set_agent_runner`.** Reason: the orchestrator's default `_story_runner` only persists a summary string, but the approval gate requires structured fields. The harness installs a custom `story_generator` runner via the documented `set_agent_runner` hook (the same hook the orchestrator's own test suite uses). The runner mirrors the default's input construction and call to `run_story_generator`, then stashes the structured `StoryGeneratorOutput` into a closure list before returning the same `TaskResult` shape. The orchestrator remains the dispatcher (HARD RULE 4 satisfied); the captured output is a side-channel for human display only. Approved by: human reviewer at CHECKPOINT-2.
- **Set `AlfredConfig.llm.model = "claude-sonnet-4-6"` in `default_demo_config`.** Reason: the schema default is empty and the first live run died at the Anthropic adapter validation. Phase 2 doesn't introduce a config-resolution pattern; the harness simply provides a working default for the demo path. Approved by: human reviewer at CHECKPOINT-2.
- **Manifest registration for scripts is a no-op.** Reason: `docs/DOCS_MANIFEST.yaml` and `docs/DOCS_POLICY.md` cover markdown lifecycle only — no `scripts/` entries exist for any sibling script (`generate_next_canonical_handover.py`, `dogfood_run.py`, etc.). Task 3 step 2 was therefore satisfied by reading the policy and concluding no entry is required. Approved by: human reviewer at CHECKPOINT-2.

**Forward plan:**

Phase 3 scope is proposal-persistence schema and approval-record linkage. The captured `StoryGeneratorOutput` from Phase 2's harness already carries the structured fields the persistence schema needs (title, description, acceptance_criteria, story_points, plus rubric metadata) — Phase 3 can lift that shape directly into a Pydantic `StoryProposal` schema and an SQLite table that links each proposal to a handover_id, an approval verdict, and a board-write outcome (Phase 4). Two orchestrator-level gaps surfaced in Phase 2 that Phase 3 should address while it has the schema layer open:

1. The orchestrator's `_story_runner` should persist structured output back onto `TaskResult` (e.g., a typed `result.payload` slot), not only a count summary, so consumers don't need a `set_agent_runner` side-channel.
2. `AlfredConfig` should fail fast when an LLM-dependent code path is invoked with an empty model string, rather than producing a runtime 400 from the provider adapter.

Phase 4 (GitHub Project V2 write path) and Phase 5 (rehearsal runbook) remain out of scope. The structured-proposal capture pattern from Phase 2 is the natural anchor for Phase 4's board-write gate: the same captured list can drive the actual mutation calls once the human approval is recorded.

**next_handover_id:** ALFRED_HANDOVER_10
