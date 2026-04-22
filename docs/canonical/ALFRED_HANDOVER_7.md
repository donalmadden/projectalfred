
# Alfred's Handover Document #7 — Phase 8: Portfolio Polish & Docs Governance

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_7
**date:** 2026-04-22
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_6
**baseline_state:** Phase 7 is fully closed; the system ships health probes, structured logging, graceful shutdown, a functional CLI, a Docker image with compose surface, a GHCR/PyPI release workflow, and updated README quick-starts — making Alfred demo-ready at the infrastructure level.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_6.md` — authoritative Phase 7 record; establishes the deployment and developer-experience baseline this phase polishes
- `docs/canonical/ALFRED_HANDOVER_5.md` — Phase 6 functional-completeness record; confirms agent/tool surface locked before Phase 7
- `docs/active/ALFRED_HANDOVER_5_OUTPUT_HARDENING.md` — output-hardening lessons; informs Phase 8 docs-governance rigour
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism constraints still in effect
- `docs/protocol/architecture.md` — canonical architecture reference
- `docs/DOCS_POLICY.md` — governance policy already in force; Phase 8 refines against it, not from scratch

This handover exists because Phase 7 delivered a fully-deployable system but left three surfaces rough: (1) the public-facing portfolio story is untold — README and docs are functional but not presentable to an external reviewer; (2) the operator runbook is absent, so someone deploying Alfred cold has no survival guide; (3) the docs lifecycle governance machinery (`docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, `docs/archive`) exists but is not exercised by any automated check, making it aspirational rather than enforced. Phase 8 closes all three gaps without introducing new runtime features. The first deliberate `docs/active` archival sweep is explicitly **out of scope** for Phase 8 — it belongs to the next phase once governance checks are green.

---

## WHAT EXISTS TODAY

### Git History

```
6b9fee6  docs: task 7 — README quick-starts and deployment docs update
1f27b2c  ci: task 6 — release workflow for GHCR and PyPI
981e20e  docker: task 5 — add image, compose, and env surface
ca3a1c6  phase7: tasks 1-4 — probes, logging, shutdown, and cli
9657d18  grounding: add policy-aware validation and canonical refresh tooling
ddf6efd  docs: reorganize handover corpus by lifecycle
4569458  output-hardening-3: phase C — critique-loop integration
79be7d4  output-hardening-3: phase B — planning-realism layer
1980e76  output-hardening-3: phase A — typed factual findings
5fab0dc  HANDOVER 6 fixed. Code changes approved
3f88354  output-hardening-2: task 4 — ground phase7 generator metadata
6530f6b  output-hardening-2: task 3 — add factual validator for planning drafts
```

<!-- Git history sourced verbatim from the repository. No commits have been added, removed, or altered. -->

### Module & API Surface

The following **exist today**:

- `src/alfred/api.py` — FastAPI application; 11 endpoints: `GET /healthz`, `GET /readyz`, `POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`, `POST /approvals/expire`, `POST /retrospective`, `POST /compile`, `GET /dashboard`
- `src/alfred/cli.py` — CLI entry point; declared in `pyproject.toml` `[project.scripts]` as `alfred.cli:main`; **exists today** (implemented in Phase 7 `ca3a1c6`)
- `src/alfred/orchestrator.py` — exists today
- `src/alfred/agents/compiler.py`, `planner.py`, `quality_judge.py`, `retro_analyst.py`, `story_generator.py` — exist today
- `src/alfred/tools/docs_policy.py`, `git_log.py`, `github_api.py`, `llm.py`, `logging.py`, `persistence.py`, `rag.py`, `reference_doc_validator.py`, `repo_facts.py` — exist today
- `src/alfred/schemas` — schema package exists today (one module per schema concern, per structural rule)
- `pyproject.toml` — `[project]` exists, `[project.scripts]` exists; packaging metadata present but may be incomplete for PyPI submission
- `docs/DOCS_POLICY.md` — exists today; governance policy in force
- `docs/DOCS_MANIFEST.yaml` — exists today; manifest file in force
- `docs/archive` — exists today; archival directory in place
- `docs/active`, `docs/canonical`, `docs/protocol` — exist today (corpus reorganised in `ddf6efd`)
- `.github/workflows/release.yml` — exists today (per workflow placement rule: `.github/workflows`)
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example` — exist today
- `README.md` — exists today; updated with quick-starts and deployment docs in `6b9fee6`

**Declared but unimplemented:**
- No new declared-but-absent items are known at Phase 8 entry. The CLI entry (`alfred.cli:main`) is declared in `pyproject.toml` and the implementation file `src/alfred/cli.py` exists today, resolving the prior partial state.

**To be created in this phase:** see `## WHAT THIS PHASE PRODUCES`.

### Docs Governance State

`docs/DOCS_POLICY.md` and `docs/DOCS_MANIFEST.yaml` exist today but no CI check enforces MANIFEST completeness or policy compliance. The `scripts/` directory has validation tooling (e.g., `scripts/validate_alfred_planning_facts.py` added in `9657d18`) but no script enforces the MANIFEST contract in CI. This is the primary governance gap Phase 8 closes.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Reasoning/execution isolation** — the Planner produces drafts only; humans approve before promotion. Do not collapse this boundary.
2. **Single FastAPI module** — the API lives exclusively in `src/alfred/api.py`; no subpackage (src/alfred/api) is permitted.
3. **Schema-per-concern** — one module per schema concern under `src/alfred/schemas`; a single catch-all `schemas.py` is forbidden.
4. **Agent/tool mirroring** — every agent module in `src/alfred/agents` must have mirrored tests under `tests/test_agents`; likewise for tools under `tests/test_tools`.
5. **`pyright` not `mypy`** — static type checking uses `pyright`; do not introduce `mypy`.
6. **No Docker before allowed phase** — Docker was introduced in Phase 7 (allowed); no further Docker infrastructure is introduced in Phase 8 unless explicitly approved.
7. **Docs lifecycle directories established** — `docs/active`, `docs/canonical`, `docs/archive`, `docs/protocol` are the four lifecycle buckets; do not add new top-level `docs/` subdirectories without policy amendment.
8. **Archival sweep is Phase 9 work** — the first deliberate `docs/active` → `docs/archive` promotion sweep is explicitly deferred past Phase 8.

---

## HARD RULES

1. **No runtime feature additions.** Phase 8 is polish, docs, and governance only. Adding new API endpoints, agents, tools, or orchestration logic is out of scope.
2. **No `mypy`.** Type checking is `pyright` throughout. Do not introduce `mypy` configuration or invocation.
3. **No new top-level `docs/` subdirectories.** The four lifecycle buckets (`active/`, `canonical/`, `archive/`, `protocol/`) are fixed. Amendments require policy update first.
4. **`docs/DOCS_POLICY.md` refines, not replaces.** Any changes to the governance policy must be additive edits to the existing file, not a replacement document at a new path.
5. **Workflow files go under `.github/workflows/` using kebab-case `*.yml` names** (placement rule: `workflow`). Do not place CI/CD config elsewhere.
6. **Script files go under `scripts/` using `*.py`** (placement rule: `script`). No top-level helper scripts.
7. **Test files go under `tests/` using `test_*.py`** (placement rule: `test`). Agent tests mirror under `tests/test_agents/`; tool tests under `tests/test_tools/`.
8. **Docs/active archival sweep is NOT a Phase 8 deliverable.** Proposing or executing that sweep in this phase is a hard violation.
9. **All handover documents follow naming convention `ALFRED_HANDOVER_\d+(_[A-Z0-9_]+)?\.md`** and are placed under `docs/` (placement rule: `doc`). The canonical copy of this draft lands at `docs/canonical/ALFRED_HANDOVER_7.md` upon promotion.
10. **DRAFT status.** This document is a Planner draft. No task may be executed until a human approves this handover.

---

## WHAT THIS PHASE PRODUCES

- `docs/canonical/ALFRED_HANDOVER_7.md` — this handover, promoted after human approval (per `doc` placement rule and `handover_doc` naming convention)
- `docs/protocol/OPERATOR_RUNBOOK.md` — operator survival guide covering cold-start, environment variables, health checks, rolling restart, and observability hooks (per `doc` placement rule)
- `scripts/check_manifest.py` — CI-executable script that validates `docs/DOCS_MANIFEST.yaml` completeness and cross-references it against the `docs/` filesystem; fails non-zero on drift (per `script` placement rule)
- `.github/workflows/docs-governance.yml` — workflow that runs `scripts/check_manifest.py` on every PR touching `docs/**` (per `workflow` placement rule: `.github/workflows/`, kebab-case `.yml`)
- `docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md` — active-lifecycle companion document capturing the portfolio narrative (what Alfred is, what it demonstrates, how to present it to an external reviewer) (per `doc` placement rule)
- `README.md` — updated with a concise "what this project demonstrates" section and a pointer to the operator runbook; existing quick-start and deployment sections are preserved

**Out of scope:**
- Any new API endpoint, agent, tool, or schema module
- `docs/active/` → `docs/archive/` archival sweep (Phase 9)
- New Docker or compose infrastructure
- `mypy` or any alternative type checker
- PyPI submission or release-tag creation

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|------|-------------|-------------------|
| 1 | Docs-Governance CI Script | `scripts/check_manifest.py` | CHECKPOINT-1 |
| 2 | Docs-Governance Workflow | `.github/workflows/docs-governance.yml` | — |
| 3 | Operator Runbook | `docs/protocol/OPERATOR_RUNBOOK.md` | CHECKPOINT-2 |
| 4 | Portfolio Narrative Doc | `docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md` | — |
| 5 | README Portfolio Section | `README.md` amendment | — |

---

## TASK 1 — Docs-Governance CI Script

**Goal:** Create `scripts/check_manifest.py` — a zero-dependency Python script that reads `docs/DOCS_MANIFEST.yaml`, walks the `docs/` filesystem, and exits non-zero with a human-readable diff when declared entries are missing or undeclared files are present.

### Implementation

1. **Create `scripts/check_manifest.py`** (per `script` placement rule: `scripts/*.py`) — the script must:
   - Accept an optional `--docs-root` argument (default: `docs/`) and `--manifest` argument (default: `docs/DOCS_MANIFEST.yaml`)
   - Load the YAML manifest; iterate declared entries
   - Walk the `docs/` tree (respecting `archive/` as a valid lifecycle bucket)
   - Report: (a) entries declared in manifest but absent on disk, (b) `.md` files on disk absent from manifest
   - Exit `0` if no drift; exit `1` with drift report printed to stdout
   - Be importable as a module (guard logic under `if __name__ == "__main__":`)

2. **Add a `[tool.pyright]` exclusion if needed** — the script uses only stdlib (`pathlib`, `sys`, `argparse`); third-party YAML library (`PyYAML`) may already be a dependency; confirm before adding. If `PyYAML` is absent, use `tomllib`-style fallback or add it to `[project.optional-dependencies]` in `pyproject.toml` rather than a hard dependency.

3. **Add a smoke test** — `tests/test_check_manifest.py` (per `test` placement rule: `tests/test_*.py`) with at least:
   - A passing case: manifest and filesystem agree
   - A drift case: manifest declares a file absent from disk → exit code 1
   - A phantom case: file on disk absent from manifest → exit code 1

### Verification

```bash
# Run the script against the live repo
python scripts/check_manifest.py

# Run the smoke test
pytest tests/test_check_manifest.py -v

# Confirm pyright is clean
pyright scripts/check_manifest.py
```

**Expected:**
- `scripts/check_manifest.py` exits `0` against the current repo state (manifest and filesystem in agreement)
- All three smoke-test cases pass
- `pyright` reports no errors

**Suggested commit message:** `governance: task 1 — add check_manifest CI script`

### CHECKPOINT-1 — Governance Script Green

**Question:** Does `scripts/check_manifest.py` exit `0` against the live repo, and do all smoke tests pass before the workflow is wired?

**Evidence required:**
- Paste verbatim output of `python scripts/check_manifest.py` (must show exit code 0 or explicit "No drift detected" message)
- Paste verbatim output of `pytest tests/test_check_manifest.py -v` (must show all tests PASSED)
- Paste verbatim output of `pyright scripts/check_manifest.py` (must show 0 errors)

| Observation | Likely call |
|---|---|
| All three outputs clean; 0 drift, all tests PASSED, 0 pyright errors | PROCEED to Task 2 |
| Script exits 1 with real drift (manifest out of date with repo) | PIVOT — update `docs/DOCS_MANIFEST.yaml` to match filesystem, then re-run; do not suppress errors |
| `PyYAML` import error | PIVOT — add `pyyaml` to `pyproject.toml` optional deps and reinstall; re-run |
| Pyright errors on the script | PIVOT — fix type annotations; re-run pyright |
| Smoke tests fail unexpectedly | STOP — paste failure output for human review before proceeding |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 2.

---

## TASK 2 — Docs-Governance Workflow

**Goal:** Wire `scripts/check_manifest.py` into CI as `.github/workflows/docs-governance.yml` so every PR touching `docs/**` or `docs/DOCS_MANIFEST.yaml` runs the manifest check automatically.

### Implementation

1. **Create `.github/workflows/docs-governance.yml`** (per `workflow` placement rule: `.github/workflows/`, kebab-case `.yml`) with:
   - Trigger: `pull_request` with `paths` filter covering `docs/**` and `scripts/check_manifest.py`
   - Single job `manifest-check` running on `ubuntu-latest`
   - Steps: checkout → `actions/setup-python@v5` (Python 3.12) → `pip install -e .[dev]` (or minimal install sufficient for `check_manifest.py`) → `python scripts/check_manifest.py`
   - Job fails if the script exits non-zero (default behaviour; no `continue-on-error`)

2. **Do not duplicate** any steps already present in the existing CI workflow. The docs-governance workflow is narrow and additive.

### Verification

```bash
# Validate YAML syntax locally
python -c "import yaml; yaml.safe_load(open('.github/workflows/docs-governance.yml'))"

# Confirm workflow file is kebab-case .yml (placement rule check)
ls .github/workflows/docs-governance.yml
```

**Expected:**
- YAML parses without error
- File exists at the canonical placement path

**Suggested commit message:** `ci: task 2 — docs-governance workflow for manifest drift`

---

## TASK 3 — Operator Runbook

**Goal:** Create `docs/protocol/OPERATOR_RUNBOOK.md` — a self-contained survival guide for someone deploying Alfred cold, covering environment setup, health verification, observability, and common failure modes.

### Implementation

1. **Create `docs/protocol/OPERATOR_RUNBOOK.md`** (per `doc` placement rule: `docs/*.md`; placed in `docs/protocol/` consistent with `docs/protocol/architecture.md`). The runbook must cover:
   - **Prerequisites** — Python ≥ 3.12, Docker (optional, for compose path), environment variables (cross-reference `.env.example`)
   - **Quick-start paths** — (a) bare-metal via `uvicorn`; (b) Docker Compose via `docker-compose up`
   - **Environment variable reference** — table of all variables with type, required/optional, and default
   - **Health & readiness verification** — `curl http://localhost:8000/healthz` and `curl http://localhost:8000/readyz` with expected responses
   - **CLI reference** — `alfred --help` output skeleton; all five subcommands with their exit-code semantics
   - **Graceful shutdown** — how to trigger and what to expect (draining in-flight approvals)
   - **Observability** — structured log format, request-ID header, log-level configuration
   - **Common failure modes** — table of symptom → likely cause → remediation for the top five operational failures
   - **Rolling restart procedure** — step-by-step for zero-downtime restart under Compose

2. **Add a manifest entry** for `docs/protocol/OPERATOR_RUNBOOK.md` in `docs/DOCS_MANIFEST.yaml` so `check_manifest.py` passes after Task 3.

### Verification

```bash
# Confirm file exists
ls docs/protocol/OPERATOR_RUNBOOK.md

# Confirm manifest check still passes after adding the new doc
python scripts/check_manifest.py

# Confirm no broken internal links (if a link-checker is available)
# python -m markdown_it docs/protocol/OPERATOR_RUNBOOK.md  # optional
```

**Expected:**
- File exists at `docs/protocol/OPERATOR_RUNBOOK.md`
- `scripts/check_manifest.py` exits `0` (manifest updated to include new file)

**Suggested commit message:** `docs: task 3 — operator runbook for cold-start deployment`

### CHECKPOINT-2 — Runbook Complete & Manifest Clean

**Question:** Is the operator runbook present, does it cover all required sections, and does the manifest check pass with the new entry included?

**Evidence required:**
- Paste verbatim output of `ls docs/protocol/OPERATOR_RUNBOOK.md`
- Paste verbatim output of `python scripts/check_manifest.py` (must be exit 0)
- Confirm (yes/no) that all eight runbook sections listed in the Implementation step are present

| Observation | Likely call |
|---|---|
| File present, manifest clean, all sections confirmed present | PROCEED to Task 4 |
| File present but manifest check exits 1 (drift) | PIVOT — add entry to `docs/DOCS_MANIFEST.yaml`; re-run check |
| One or more required sections absent from runbook | PIVOT — complete missing sections; re-confirm |
| Runbook references a file path that does not exist today | STOP — flag for human review; do not fabricate paths |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 4.

---

## TASK 4 — Portfolio Narrative Document

**Goal:** Create `docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md` — a living document (active lifecycle) that tells the portfolio story: what Alfred is, what engineering decisions it demonstrates, and how to walk an external reviewer through the codebase.

### Implementation

1. **Create `docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md`** (per `doc` placement rule: `docs/*.md`; per `handover_doc` naming convention: `ALFRED_HANDOVER_\d+(_[A-Z0-9_]+)?\.md`). The document must cover:
   - **What Alfred is** — one-paragraph executive summary suitable for a portfolio README or cover letter
   - **What it demonstrates** — bullet list of engineering capabilities: document-mediated coordination, checkpoint-gated execution, agent/tool isolation, typed schema validation, structured logging, CI/CD pipeline, Docker deployment, docs lifecycle governance
   - **Architecture tour** — ordered walk through the key modules (`src/alfred/api.py`, `src/alfred/agents/`, `src/alfred/tools/`, `src/alfred/schemas/`, `src/alfred/orchestrator.py`, `src/alfred/cli.py`) with one-sentence roles; cross-reference `docs/protocol/architecture.md`
   - **Demo script** — step-by-step instructions for a 10-minute live demo covering health check, generate → evaluate → approve flow, and CLI usage
   - **What to read next** — ordered reading list: `README.md` → `docs/protocol/architecture.md` → `docs/protocol/OPERATOR_RUNBOOK.md` → `docs/canonical/ALFRED_HANDOVER_7.md`

2. **Add a manifest entry** for `docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md` in `docs/DOCS_MANIFEST.yaml`.

### Verification

```bash
# Confirm file exists
ls docs/active/ALFRED_HANDOVER_7_PORTFOLIO_POLISH.md

# Confirm manifest check still passes
python scripts/check_manifest.py
```

**Expected:**
- File exists at canonical path
- `scripts/check_manifest.py` exits `0`

**Suggested commit message:** `docs: task 4 — portfolio narrative and architecture tour`

---

## TASK 5 — README Portfolio Section

**Goal:** Amend `README.md` to add a concise "What this project demonstrates" section and a pointer to the operator runbook, without disturbing the existing quick-start and deployment sections established in Phase 7.

### Implementation

1. **Edit `README.md`** (exists today — do not create a new file):
   - Add a `## What This Project Demonstrates` section near the top (after the project title/tagline, before Quick Start), containing a 3–5 bullet summary drawn from the portfolio narrative (Task 4)
   - Add a `## Operator Runbook` pointer section (after Deployment, before Contributing or end of file) with a one-liner and a link to `docs/protocol/OPERATOR_RUNBOOK.md`
   - Do NOT remove or rewrite existing Quick Start, Deployment, or CLI sections

2. **Update `docs/DOCS_MANIFEST.yaml`** if `README.md` is tracked there (check first; do not add a duplicate entry).

### Verification

```bash
# Confirm both new sections exist
grep -n "What This Project Demonstrates" README.md
grep -n "Operator Runbook" README.md

# Confirm manifest still passes
python scripts/check_manifest.py
```

**Expected:**
- Both `grep` commands return a line number (sections present)
- `scripts/check_manifest.py` exits `0`

**Suggested commit message:** `docs: task 5 — README portfolio section and runbook pointer`

---

## WHAT NOT TO DO

1. **Do not create `docs/DOCS_POLICY.md` or `docs/DOCS_MANIFEST.yaml` from scratch.** Both exist today. Phase 8 refines and exercises them; it does not recreate them.
2. **Do not initiate an `docs/active/` → `docs/archive/` archival sweep.** This is explicitly Phase 9 work.
3. **Do not add new API endpoints, agents, tools, or schema modules.** Phase 8 is polish-only.
4. **Do not introduce `mypy`.** The repo uses `pyright`.
5. **Do not place workflow files outside `.github/workflows/`.** The `docs-governance.yml` file belongs exactly there.
6. **Do not place scripts outside `scripts/`.** `check_manifest.py` must live at `scripts/check_manifest.py`, not at the repo root or inside `src/`.
7. **Do not fabricate file paths in the runbook.** Only reference paths confirmed to exist today (see `## WHAT EXISTS TODAY`).
8. **Do not collapse "declared but unimplemented" state into existence claims.** Use the three-state vocabulary precisely.
9. **Do not merge the portfolio narrative into the operator runbook or vice versa.** They serve different audiences and belong as separate files.
10. **Do not execute any task before human approval of this handover.** This document is a Planner draft.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section
> before closing the work. The next planner or reviewer must be able to
> cold-start from this artifact alone.

**What worked:**
- *executor to fill*

**What was harder than expected:**
- *executor to fill*

**Decisions made during execution (deviations from this plan):**
- *executor to fill — each deviation must include: what changed, why, who approved*

**Forward plan:**
- *executor to fill — suggested Phase 9 candidates: `docs/active/` → `docs/archive/` archival sweep; pyproject.toml packaging completeness for PyPI submission; integration test coverage audit*

**next_handover_id:** ALFRED_HANDOVER_8