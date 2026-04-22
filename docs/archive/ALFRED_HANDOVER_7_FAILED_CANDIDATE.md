# Alfred's Handover Document #7 — Phase 8: Portfolio Polish & Docs Governance Refinement

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_7
**date:** 2026-04-22
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_6
**baseline_state:** Phase 7 is fully closed; the system ships a Docker image, a release workflow, a structured-logging middleware, a graceful-shutdown handler, and an implemented CLI — the project is demo-ready at the infrastructure level but the documentation surface, operator runbooks, and the docs lifecycle governance tooling all need a final polish pass before the portfolio is presentable.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_6.md` — Phase 7 final canonical; baseline for what Phase 8 inherits
- `docs/canonical/ALFRED_HANDOVER_5.md` — Phase 6 canonical; background on agent/tool architecture
- `docs/protocol/architecture.md` — authoritative module topology; must stay in sync with any new additions
- `docs/DOCS_POLICY.md` — exists today; governs doc lifecycle (active → canonical → archive); Phase 8 refines, does not replace
- `docs/active/ALFRED_HANDOVER_4_OUTPUT_HARDENING.md` — output-hardening audit trail; relevant to validator lineage
- `docs/active/ALFRED_HANDOVER_5_OUTPUT_HARDENING.md` — output-hardening audit trail
- `docs/active/CODEX_HANDOVER_GROUNDING_REFINEMENT.md` — grounding-refinement context
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism layer; informs Phase 8 task spec quality bar

Phase 8 exists because Phase 7 delivered a deployable system but left several portfolio-facing surfaces incomplete: the docs lifecycle governance tooling exists but has not been exercised as a coherent workflow; operator-facing runbooks are absent; the `docs/active` corpus has accumulated reference documents that have not been formally promoted or archived; and the project lacks a single polished "demo entry point" document. This handover addresses all four gaps without inventing new infrastructure — it refines what already exists.

> **Note:** `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, and `docs/archive` all **exist today**. Phase 8 must refine or reference them. Creating them from scratch is explicitly out of scope. The first deliberate `docs/active` archival sweep is a future-phase deliverable and is therefore **not** a Phase 8 task.

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

### Module & API Surface

The following items **exist today**:

- Agent modules (`src/alfred/agents`): `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator`
- Tool modules (`src/alfred/tools`): `docs_policy`, `git_log`, `github_api`, `llm`, `logging`, `persistence`, `rag`, `reference_doc_validator`, `repo_facts`
- Top-level modules under `src/alfred`: `agents`, `api`, `cli`, `orchestrator`, `schemas`, `tools`
- FastAPI app: `src/alfred/api.py` (single module; no subpackage)
- FastAPI endpoints (11): `GET /healthz`, `GET /readyz`, `POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`, `POST /approvals/expire`, `POST /retrospective`, `POST /compile`, `GET /dashboard`
- `pyproject.toml`: exists; `[project]` present; `[project.scripts]` present; CLI entry declared as `alfred.cli:main`
- Type checker: `pyright` (mypy is **not** in use and must not be referenced)
- Docs governance: `docs/DOCS_POLICY.md` exists today; `docs/DOCS_MANIFEST.yaml` exists today; `docs/archive` exists today

### Docs Lifecycle State

| Path | State |
|---|---|
| `docs/DOCS_POLICY.md` | exists today |
| `docs/DOCS_MANIFEST.yaml` | exists today |
| `docs/archive` | exists today |
| `docs/active` (corpus) | exists today — accumulated during output-hardening rounds; **not yet swept/archived** |
| `docs/canonical/ALFRED_HANDOVER_6.md` | exists today — most recent canonical |
| `docs/protocol/architecture.md` | exists today |
| `docs/protocol/builder_prompt.md` | exists today |
| Operator runbook | **to be created in this phase** |
| Demo entry-point document | **to be created in this phase** |

### Key Design Decisions Inherited (Do Not Revisit)

1. **Document as protocol.** The handover document is the control surface; the executor never modifies the board or merges work without an approved handover artifact.
2. **Checkpoint-gated execution.** Every non-trivial phase transition waits for human sign-off at defined checkpoints. This is non-negotiable.
3. **Reasoning/execution isolation.** Alfred Planner produces drafts only; it never executes tasks, writes code, or modifies files.
4. **`pyright`, not `mypy`.** The repository has standardised on `pyright` for type checking. No `mypy` configuration may be introduced.
5. **Single API module.** `src/alfred/api.py` is the FastAPI app. No src/alfred/api subpackage is ever permitted.
6. **Schema-per-concern layout.** Schema modules live individually under `src/alfred/schemas`; a single catch-all src/alfred/schemas.py is forbidden.
7. **Docs governance infrastructure already exists.** `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, and `docs/archive` must be refined and referenced, never recreated.
8. **`docs/active` archival sweep is future work.** Phase 8 does not perform a bulk archival of `docs/active`; that is explicitly deferred to the next phase.

---

## HARD RULES

1. **No `mypy`.** The repo uses `pyright`. Do not add `mypy` configuration, `mypy` CI steps, or `mypy` invocations anywhere.
2. **No new API subpackage.** `src/alfred/api.py` must remain a single module. Introducing `src/alfred/api/` is a structural violation.
3. **No catch-all schema file.** `src/alfred/schemas.py` is forbidden; all schema concerns stay in individual modules under `src/alfred/schemas/`.
4. **No `docs/active/` bulk archival in Phase 8.** The sweep is explicitly deferred. Do not move, rename, or delete files under `docs/active/` as part of this phase.
5. **Do not recreate docs governance infrastructure.** `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, and `docs/archive/` already exist. Any task that proposes creating them from scratch is invalid.
6. **New workflow files must use kebab-case `.yml`/`.yaml` under `.github/workflows/`.** Per workflow placement rule: root = `.github/workflows/`, pattern = `*.yml or *.yaml`.
7. **New agent files must land in `src/alfred/agents/` with mirrored tests in `tests/test_agents/`.** Per agent structural rule.
8. **New tool files must land in `src/alfred/tools/` with mirrored tests in `tests/test_tools/`.** Per tool structural rule.
9. **New script files must land in `scripts/` using `*.py`.** Per script placement rule.
10. **New doc files must land in `docs/` using `*.md`.** Per doc placement rule.
11. **This document is a draft.** No task in this handover is authorised for execution until a human approves this artifact.

---

## WHAT THIS PHASE PRODUCES

- `docs/protocol/OPERATOR_RUNBOOK.md` — step-by-step operator guide covering local dev, Docker deployment, CLI usage, health-check verification, and release workflow; per doc placement rule (`docs/`, `*.md`).
- `docs/DEMO_GUIDE.md` — single polished "demo entry point" covering the end-to-end user journey (story generation → evaluation → approval → retrospective) with curl examples and expected outputs; per doc placement rule.
- `docs/DOCS_MANIFEST.yaml` — updated manifest entries for all new documents produced in this phase (existing file refined, not recreated).
- `docs/DOCS_POLICY.md` — minor refinement adding explicit guidance on the `docs/protocol/` subdirectory lifecycle (existing file refined, not recreated).
- `scripts/check_docs_manifest.py` — lightweight validation script asserting that every file listed in `docs/DOCS_MANIFEST.yaml` exists on disk and every new Phase 8 doc is registered; per script placement rule (`scripts/`, `*.py`).
- `.github/workflows/docs-lint.yml` — CI workflow running the manifest check script and `markdownlint` on pull requests that touch `docs/**`; per workflow placement rule (`.github/workflows/`, `*.yml`).
- `tests/test_scripts/test_check_docs_manifest.py` — unit tests for the manifest check script; per test placement rule (`tests/`, `test_*.py`).

Out of scope:
- Bulk archival sweep of `docs/active/` (deferred to Phase 9).
- New agent or tool modules (no new runtime behaviour in Phase 8).
- Docker or CI infrastructure changes beyond the `docs-lint.yml` workflow.
- Any `mypy` configuration.
- Any modification to `src/alfred/api.py` endpoints.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Operator Runbook | `docs/protocol/OPERATOR_RUNBOOK.md` | CHECKPOINT-1 |
| 2 | Demo Guide | `docs/DEMO_GUIDE.md` | — |
| 3 | Docs Policy Refinement | `docs/DOCS_POLICY.md` (refined) + `docs/DOCS_MANIFEST.yaml` (updated) | — |
| 4 | Manifest Validation Script | `scripts/check_docs_manifest.py` + `tests/test_scripts/test_check_docs_manifest.py` | CHECKPOINT-2 |
| 5 | Docs-Lint CI Workflow | `.github/workflows/docs-lint.yml` | CHECKPOINT-3 |

---

## TASK 1 — Operator Runbook

**Goal:** Produce a complete, accurate operator runbook so that a cold-start reader can run, deploy, and operate Alfred without consulting any other document.

### Implementation

1. **Create `docs/protocol/OPERATOR_RUNBOOK.md`** — per doc placement rule (`docs/`, `*.md`). The file lives under `docs/protocol/` alongside `architecture.md` and `builder_prompt.md`. Cover the following sections in order:
   - **Prerequisites** — Python version, Docker version, environment variables (cross-reference `.env.example`).
   - **Local Development** — `pip install -e ".[dev]"`, `pyright` type-check invocation, test suite (`pytest`), server start (`uvicorn src.alfred.api:app`).
   - **CLI Quick-Reference** — every subcommand declared in `alfred.cli:main` with `--help` output summary and exit-code contract.
   - **Docker Deployment** — `docker compose up`, health-check verification against `GET /healthz` and `GET /readyz`, log inspection.
   - **Release Workflow** — how the `.github/workflows/release.yml` workflow is triggered (version tag), what it publishes (wheel to PyPI, image to GHCR), and rollback procedure.
   - **Troubleshooting** — common failure modes: missing env vars, unhealthy probe responses, approval queue overflow.

2. **Register in `docs/DOCS_MANIFEST.yaml`** — add an entry for `docs/protocol/OPERATOR_RUNBOOK.md` with `status: active` and a one-line description.

### Verification

```bash
# Confirm file exists
test -f docs/protocol/OPERATOR_RUNBOOK.md && echo "EXISTS"

# Confirm manifest entry present
grep -q "OPERATOR_RUNBOOK" docs/DOCS_MANIFEST.yaml && echo "REGISTERED"

# Markdown lint (install once: npm install -g markdownlint-cli)
markdownlint docs/protocol/OPERATOR_RUNBOOK.md
```

**Expected:**
- `EXISTS` printed with exit code 0.
- `REGISTERED` printed with exit code 0.
- `markdownlint` exits 0 with no warnings.

**Suggested commit message:** `docs: task 1 — operator runbook under docs/protocol/`

### CHECKPOINT-1 — Runbook Completeness Gate

**Question:** Does the runbook allow a cold-start operator to run, deploy, and release Alfred without consulting any other document?

**Evidence required:**
- Paste the output of `markdownlint docs/protocol/OPERATOR_RUNBOOK.md` verbatim.
- Paste the `grep` output confirming manifest registration verbatim.
- Confirm (yes/no) that every CLI subcommand is documented with its exit-code contract.

| Observation | Likely call |
|---|---|
| Lint clean, manifest registered, all subcommands documented | PROCEED |
| Lint warnings present but manifest registered and subcommands covered | PIVOT — fix lint before continuing |
| Missing CLI subcommands or missing manifest entry | STOP — runbook is incomplete |

**STOP HERE.** Wait for human sign-off before proceeding to Task 2.

---

## TASK 2 — Demo Guide

**Goal:** Produce a single polished document that walks a first-time viewer through the end-to-end Alfred user journey, suitable as a portfolio demo entry point.

### Implementation

1. **Create `docs/DEMO_GUIDE.md`** — per doc placement rule (`docs/`, `*.md`). Cover:
   - **Overview** — what Alfred does in two paragraphs.
   - **Prerequisites** — server running locally (cross-reference `OPERATOR_RUNBOOK.md`).
   - **Step-by-step journey** with `curl` examples and annotated expected JSON responses for: `POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `POST /retrospective`, `POST /compile`, `GET /dashboard`.
   - **Reading the output** — what each response field means.
   - **Next steps** — pointer to `docs/protocol/architecture.md` for deeper reading.

2. **Register in `docs/DOCS_MANIFEST.yaml`** — add an entry for `docs/DEMO_GUIDE.md` with `status: active`.

### Verification

```bash
test -f docs/DEMO_GUIDE.md && echo "EXISTS"
grep -q "DEMO_GUIDE" docs/DOCS_MANIFEST.yaml && echo "REGISTERED"
markdownlint docs/DEMO_GUIDE.md
```

**Expected:**
- `EXISTS` and `REGISTERED` printed.
- `markdownlint` exits 0.

**Suggested commit message:** `docs: task 2 — demo guide and manifest registration`

---

## TASK 3 — Docs Policy Refinement

**Goal:** Extend `docs/DOCS_POLICY.md` with explicit lifecycle guidance for `docs/protocol/` documents, and ensure `docs/DOCS_MANIFEST.yaml` reflects the current corpus accurately.

### Implementation

1. **Refine `docs/DOCS_POLICY.md`** (existing file — do **not** recreate) — add a `### docs/protocol/` subsection explaining:
   - Files here are **long-lived protocol documents** (architecture, builder prompts, runbooks).
   - They are not subject to the active → canonical → archive promotion cycle.
   - They are updated in-place when the system evolves, with changes recorded in git history.
   - The manifest must always reflect their current state.

2. **Update `docs/DOCS_MANIFEST.yaml`** (existing file — do **not** recreate) — verify and correct entries for all files under `docs/protocol/`, `docs/active/`, and `docs/canonical/`. Add any missing entries. Do **not** move or delete any `docs/active/` entries (archival sweep is deferred).

### Verification

```bash
# Policy file updated
grep -q "docs/protocol" docs/DOCS_POLICY.md && echo "POLICY_UPDATED"

# Manifest coherence (all docs/protocol/ files present in manifest)
for f in docs/protocol/*.md; do
  grep -q "$(basename $f)" docs/DOCS_MANIFEST.yaml \
    && echo "OK: $f" || echo "MISSING: $f"
done
```

**Expected:**
- `POLICY_UPDATED` printed.
- No `MISSING:` lines — every `docs/protocol/` file is registered in the manifest.

**Suggested commit message:** `docs: task 3 — policy refinement for docs/protocol/ and manifest sync`

---

## TASK 4 — Manifest Validation Script

**Goal:** Provide a repeatable, automated check that every document registered in `docs/DOCS_MANIFEST.yaml` physically exists on disk, and that every new Phase 8 document is registered — runnable in CI and locally.

### Implementation

1. **Create `scripts/check_docs_manifest.py`** — per script placement rule (`scripts/`, `*.py`). The script must:
   - Parse `docs/DOCS_MANIFEST.yaml`.
   - For each registered path, assert the file exists on disk; print `MISSING: <path>` and exit non-zero if any are absent.
   - Optionally accept `--strict` flag: also assert that a curated list of required Phase 8 documents (`docs/DEMO_GUIDE.md`, `docs/protocol/OPERATOR_RUNBOOK.md`) are registered.
   - Print `ALL MANIFEST ENTRIES VERIFIED` and exit 0 on success.

2. **Create `tests/test_scripts/test_check_docs_manifest.py`** — per test placement rule (`tests/`, `test_*.py`). Tests must cover:
   - Happy path: all entries present → exit 0.
   - Missing file: one entry points to a non-existent path → non-zero exit.
   - `--strict` with missing required doc → non-zero exit.

> Note: `tests/test_scripts/` does not yet exist; create it with an `__init__.py` package marker per the test structural rule.

### Verification

```bash
# Run the script directly
python scripts/check_docs_manifest.py --strict

# Run the tests
pytest tests/test_scripts/test_check_docs_manifest.py -v

# Type-check with pyright (NOT mypy)
pyright scripts/check_docs_manifest.py
```

**Expected:**
- Script prints `ALL MANIFEST ENTRIES VERIFIED` and exits 0.
- All tests pass (`PASSED` for each).
- `pyright` reports 0 errors.

**Suggested commit message:** `scripts: task 4 — manifest validation script and tests`

### CHECKPOINT-2 — Manifest Script Gate

**Question:** Does the manifest validation script reliably detect missing files and exit non-zero, and do all tests pass under `pyright`-clean code?

**Evidence required:**
- Paste the full output of `python scripts/check_docs_manifest.py --strict` verbatim.
- Paste the full output of `pytest tests/test_scripts/test_check_docs_manifest.py -v` verbatim.
- Paste the output of `pyright scripts/check_docs_manifest.py` verbatim.

| Observation | Likely call |
|---|---|
| Script exits 0, all tests pass, `pyright` 0 errors | PROCEED |
| Script exits 0 but one or more tests fail | PIVOT — fix tests before continuing |
| `pyright` reports errors | PIVOT — resolve type errors before continuing |
| Script exits non-zero on a manifest that should be clean | STOP — logic error in script |

**STOP HERE.** Wait for human sign-off before proceeding to Task 5.

---

## TASK 5 — Docs-Lint CI Workflow

**Goal:** Add a CI workflow that runs the manifest validation script and `markdownlint` on every pull request that touches `docs/**`, providing fast feedback on documentation hygiene.

### Implementation

1. **Create `.github/workflows/docs-lint.yml`** — per workflow placement rule (`.github/workflows/`, `*.yml`). The workflow must:
   - Trigger on `pull_request` events where `paths` includes `docs/**` or `scripts/check_docs_manifest.py`.
   - Use a `ubuntu-latest` runner.
   - Steps in order:
     a. `actions/checkout@v4`
     b. `actions/setup-python@v5` with the project's minimum Python version.
     c. `pip install pyyaml` (dependency for the manifest script).
     d. `npm install -g markdownlint-cli` (for markdown lint).
     e. `python scripts/check_docs_manifest.py --strict`
     f. `markdownlint 'docs/**/*.md' --ignore node_modules`
   - Name the workflow `docs-lint`; name the job `lint`.

### Verification

```bash
# Validate workflow YAML is well-formed
python -c "import yaml; yaml.safe_load(open('.github/workflows/docs-lint.yml'))" \
  && echo "YAML_VALID"

# Confirm trigger path filter present
grep -q "docs/\*\*" .github/workflows/docs-lint.yml && echo "PATH_FILTER_PRESENT"
```

**Expected:**
- `YAML_VALID` and `PATH_FILTER_PRESENT` printed.
- On the first PR touching `docs/`, the GitHub Actions run shows both steps green.

**Suggested commit message:** `ci: task 5 — docs-lint workflow for manifest and markdownlint`

### CHECKPOINT-3 — CI Green Gate

**Question:** Does the `docs-lint` workflow pass on a PR that touches a `docs/` file, with no false positives on the current corpus?

**Evidence required:**
- Link to the first GitHub Actions run of `docs-lint` (or paste the workflow run summary).
- Confirm (yes/no) that both `check_docs_manifest.py --strict` and `markdownlint` steps show green.

| Observation | Likely call |
|---|---|
| Both steps green, no false positives | PROCEED — Phase 8 is complete |
| `markdownlint` fails on pre-existing docs not touched by Phase 8 | PIVOT — add ignore rules or fix legacy lint errors |
| Manifest script exits non-zero despite all files existing | STOP — investigate path resolution in CI environment |
| Workflow file not triggering | STOP — check `paths` filter syntax and branch protection rules |

**STOP HERE.** Phase 8 is not closed until a human confirms CI green.

---

## WHAT NOT TO DO

1. **Do not recreate `docs/DOCS_POLICY.md`, `docs/DOCS_MANIFEST.yaml`, or `docs/archive/`.** They exist today. Any task that proposes creating them is a hard rule violation.
2. **Do not perform a `docs/active/` archival sweep.** Moving, renaming, or deleting files under `docs/active/` is out of scope for Phase 8 and is deferred to Phase 9.
3. **Do not introduce `mypy`.** The project uses `pyright` exclusively. Adding `mypy` configuration or CI invocations is a hard rule violation.
4. **Do not create `src/alfred/api/` as a subpackage.** `src/alfred/api.py` is the single API module and must stay that way.
5. **Do not create a catch-all `src/alfred/schemas.py`.** All schema concerns remain in individual modules under `src/alfred/schemas/`.
6. **Do not invent new agent or tool runtime modules in Phase 8.** This phase is documentation and tooling polish only; no new runtime behaviour is introduced.
7. **Do not place workflow files anywhere other than `.github/workflows/`.** Per workflow placement rule.
8. **Do not place new script files anywhere other than `scripts/` with a `.py` extension.** Per script placement rule.
9. **Do not fabricate commits in the `### Git History` section.** The seven commits listed above are the authoritative recent history; nothing may be added or altered.
10. **Do not close Phase 8 without human sign-off at all three checkpoints.** CHECKPOINT-1, CHECKPOINT-2, and CHECKPOINT-3 are mandatory gates.

---

## POST-MORTEM

> **Instruction to executor:** After implementation, fill in this section before closing the work. The next planner or reviewer must be able to cold-start from this artifact alone.

**What worked:**
- *executor to fill*

**What was harder than expected:**
- *executor to fill*

**Decisions made during execution (deviations from this plan):**
- *executor to fill — each deviation must include: what changed, why, who approved*

**Forward plan:**
- *executor to fill — suggested Phase 9 candidates: `docs/active/` archival sweep; `docs/DOCS_MANIFEST.yaml` automation (auto-update on commit); expanding `scripts/check_docs_manifest.py` to validate front-matter schema compliance*

**next_handover_id:** ALFRED_HANDOVER_8