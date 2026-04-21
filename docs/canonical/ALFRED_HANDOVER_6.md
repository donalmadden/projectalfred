# Alfred's Handover Document #6 — Phase 7: Developer Experience & Deployment

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_6
**date:** 2026-04-21
**author:** Alfred Planner (draft — human approval required)
**previous_handover:** ALFRED_HANDOVER_5
**baseline_state:** Phase 6 is fully closed and three rounds of output-hardening (`output-hardening-2` and `output-hardening-3`) are committed; the system is functionally complete but ships no container, no implemented CLI, and no deployment surface.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_5.md` — authoritative Phase 6 close-out and baseline for this handover.
- `docs/active/ALFRED_HANDOVER_5_OUTPUT_HARDENING.md` — grounding-remediation plan that established the repo-truth and factual-validator invariants this phase must preserve.
- `docs/active/CODEX_HANDOVER_GROUNDING_REFINEMENT.md` — documents the grounding-refinement approach adopted across output-hardening-2 and output-hardening-3.
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism layer injected in output-hardening-3 phase B; governs task-granularity and placement rules.
- `docs/protocol/architecture.md` — canonical module layout and API surface this phase must not break.

This handover exists to carry Phase 7 forward from a stable, grounded baseline. Three output-hardening passes (`output-hardening-2`: repo-truth snapshot, factual validator, hardened planner prompt, grounded metadata; `output-hardening-3`: typed factual findings, planning-realism layer, critique-loop integration) were completed after the initial Phase 7 draft was promoted at commit `5fab0dc`. The repository now has the tooling necessary to keep planning drafts grounded. Phase 7 proper — Developer Experience & Deployment — begins from this refreshed handover.

---

## WHAT EXISTS TODAY

### Git History

```
4569458  output-hardening-3: phase C — critique-loop integration
79be7d4  output-hardening-3: phase B — planning-realism layer
1980e76  output-hardening-3: phase A — typed factual findings
5fab0dc  HANDOVER 6 fixed. Code changes approved
3f88354  output-hardening-2: task 4 — ground phase7 generator metadata
6530f6b  output-hardening-2: task 3 — add factual validator for planning drafts
ea37972  output-hardening-2: task 2 — harden planner against factual hallucinations
53e6e77  output-hardening-2: task 1 — add repo truth snapshot input
86efac9  fix: increase anthropic max_tokens to 8192 for planner output
d088630  phase7: add generate_phase7.py planner script
b3600e5  fix: sort imports in generate_phase6.py (ruff I001)
6f68a3d  phase6: close — post-mortem and checkpoint-6-2 evidence
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current Module & API Surface

The following items **exist today**:

- **Agent modules** (`src/alfred/agents`): `compiler.py`, `planner.py`, `quality_judge.py`, `retro_analyst.py`, `story_generator.py`
- **Tool modules** (`src/alfred/tools`): `docs_policy.py`, `git_log.py`, `github_api.py`, `llm.py`, `persistence.py`, `rag.py`, `reference_doc_validator.py`, `repo_facts.py`
- **Top-level names under `src/alfred`**: `agents`, `api`, `orchestrator`, `schemas`, `tools`
- **FastAPI application** at `src/alfred/api.py` (per API structural rule: single module, no subpackage)
- **FastAPI endpoints (9)**: `POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`, `POST /approvals/expire`, `POST /retrospective`, `POST /compile`, `GET /dashboard`
- **`pyproject.toml`**: `[project]` exists and `[project.scripts]` exists, with `alfred.cli:main` declared
- **Type checker**: `pyright` (mypy is **not** in use and must not be introduced)

The following item is **declared but unimplemented**:

- **CLI entry point** (`alfred.cli:main`): declared in `pyproject.toml` under `[project.scripts]`, but src/alfred/cli.py does not exist yet. This is the primary implementation gap Phase 7 must close.

The following items are **to be created in this phase** (do not claim they exist today):

- src/alfred/tools/logging.py — structured JSON logging module
- src/alfred/cli.py — CLI implementation
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example` — container and local-dev surface
- .github/workflows/release.yml — release workflow (per workflow placement rule: `.github/workflows`)
- `GET /healthz`, `GET /readyz` endpoints added to the existing `src/alfred/api.py`

### Key Design Decisions Inherited (Do Not Revisit)

1. **FastAPI lives in a single module**: `src/alfred/api.py` is the one and only API module. No subpackage (src/alfred/api) is permitted.
2. **Type checking is `pyright` only**: `mypy` is not in use; do not introduce it.
3. **Schemas are per-concern modules**: one module per schema concern under `src/alfred/schemas`; a single catch-all src/alfred/schemas.py is forbidden.
4. **Agent and tool modules mirror into tests**: every agent in `src/alfred/agents` must have a mirror test module in `tests/test_agents`; every tool in `src/alfred/tools` must have a mirror test module in `tests/test_tools`.
5. **Factual-validator invariants must be preserved**: the planning-realism layer and critique-loop integration from output-hardening-3 must not be degraded; all future planning drafts must pass the factual validator.
6. **No Docker before Phase 7**: this phase is the first allowed phase for containerisation.
7. **Document as protocol**: this handover is the control surface; no execution happens before human approval of each checkpoint.

---

## HARD RULES

1. **No `mypy`** — the repository uses `pyright` exclusively. Do not add `mypy` to `pyproject.toml`, CI, or any script.
2. **No Docker before Phase 7** — Phase 7 is now the active phase; containerisation is permitted and expected in this phase only.
3. **Single API module** — `src/alfred/api.py` remains the sole FastAPI module. No subpackage.
4. **Placement rules are mandatory** — workflows in `.github/workflows/` using `*.yml`; schemas in `src/alfred/schemas/{name}.py`; agents in `src/alfred/agents/{name}.py`; tools in `src/alfred/tools/{name}.py`; tests in `tests/` using `test_*.py`; scripts in `scripts/` using `*.py`; docs in `docs/` using `*.md`.
5. **No fabricated commits** — the Git History section reproduces the real log verbatim. Do not add, remove, or alter any commit hash or message.
6. **Factual-validator must stay green** — all future planning drafts must pass `scripts/validate_alfred_planning_facts.py` (or its successor). Do not remove or weaken any factual-validation hook.
7. **Three-state vocabulary** — any file or module described in this document must be classified as exactly one of: `exists today`, `declared but unimplemented`, or `to be created in this phase`. Never collapse partial state.
8. **Checkpoint-gated execution** — the executor must STOP at each checkpoint and wait for explicit human direction before continuing.

---

## WHAT THIS PHASE PRODUCES

- `GET /healthz` and `GET /readyz` endpoints added to `src/alfred/api.py`, suitable for container liveness and readiness probes.
- `src/alfred/tools/logging.py` — structured JSON logging module with request-ID middleware and `LOG_LEVEL` env-var control (per tool placement rule: `src/alfred/tools/`).
- `src/alfred/cli.py` — fully implemented CLI closing the `alfred.cli:main` declared-but-unimplemented gap; subcommands: `plan`, `evaluate`, `serve`, `validate`, `version`, each with `--help`, correct exit codes, and `--dry-run` where appropriate.
- `Dockerfile` and `.dockerignore` — rootless, multi-stage image running `alfred serve`.
- `docker-compose.yml` — development profile wiring the Alfred API, a volume-mounted workspace, and env-var injection from `.env`.
- `.env.example` — documents every environment variable the system reads.
- `.github/workflows/release.yml` — GitHub Actions release workflow building and pushing the Docker image to GHCR and publishing a wheel to PyPI on version tags (per workflow placement rule: `.github/workflows/`).
- `docs/canonical/ALFRED_HANDOVER_6.md` — this document, promoted after human approval.

Out of scope:
- Kubernetes manifests or Helm charts (post-Phase 7).
- Additional agent or tool modules beyond those listed above.
- Any change to `pyproject.toml` that introduces `mypy`.
- Subcommands not listed above for the CLI.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Health & Readiness Probes | `GET /healthz`, `GET /readyz` in `src/alfred/api.py` | CHECKPOINT-1 |
| 2 | Structured Logging & Request-ID Middleware | `src/alfred/tools/logging.py`, middleware wired into `src/alfred/api.py` | — |
| 3 | Graceful Shutdown | Lifespan handler draining in-flight approvals; integration test in `tests/` | CHECKPOINT-2 |
| 4 | CLI Implementation | `src/alfred/cli.py`; all five subcommands with `--help` and exit codes | — |
| 5 | Docker Image & Compose | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example` | CHECKPOINT-3 |
| 6 | Release Workflow | `.github/workflows/release.yml`; wheel + GHCR publish on version tag | CHECKPOINT-4 |
| 7 | Documentation | `README.md` quick-starts updated; `docs/` entries for deployment | — |

---

## TASK 1 — Health & Readiness Probes

**Goal:** Add `GET /healthz` (liveness) and `GET /readyz` (readiness) endpoints to the existing `src/alfred/api.py` so the container scheduler can probe the service.

### Implementation

1. **Add `/healthz` route** — Returns `{"status": "ok"}` with HTTP 200. No dependencies checked. This is a pure liveness signal.
2. **Add `/readyz` route** — Returns `{"status": "ready"}` with HTTP 200 when all required dependencies (e.g. persistence layer reachable) are satisfied; returns HTTP 503 with `{"status": "unavailable", "reason": "<detail>"}` otherwise.
3. **Wire into `src/alfred/api.py`** — Both routes must live in the single API module; no new subpackage or router file that conflicts with the single-module rule.
4. **Add tests** — `tests/test_api.py` (or the existing API test module) must cover: liveness always returns 200; readiness returns 200 when healthy, 503 when a dependency is down (mock the dependency).

### Verification

```bash
# Static type check (pyright only — no mypy)
pyright src/alfred/api.py

# Run existing test suite plus new probe tests
pytest tests/ -q

# Smoke test against a running dev server
uvicorn alfred.api:app --port 8000 &
curl -s http://localhost:8000/healthz   # expect {"status":"ok"}
curl -s http://localhost:8000/readyz    # expect {"status":"ready"} or 503
```

**Expected:**
- `pyright` reports zero errors.
- All tests pass.
- `/healthz` returns `{"status": "ok"}` with HTTP 200.
- `/readyz` returns `{"status": "ready"}` with HTTP 200 on a healthy instance.

**Suggested commit message:** `api: task 1 — add /healthz and /readyz probes`

### CHECKPOINT-1 — Probe Endpoints Green

**Question:** Are both probe endpoints returning correct status codes and bodies, and do all tests pass?

**Evidence required:**
- Paste the output of `pytest tests/ -q` showing zero failures.
- Paste `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz` showing `200`.
- Paste `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/readyz` showing `200`.
- Paste `pyright src/alfred/api.py` showing zero errors.

| Observation | Likely call |
|---|---|
| All tests pass, both endpoints return correct codes, pyright clean | PROCEED to Task 2 |
| Tests pass but pyright reports new errors introduced by this task | PIVOT — fix type errors before continuing |
| `/readyz` returns 503 in a known-healthy local environment | STOP — dependency detection logic incorrect; revisit before continuing |

**STOP HERE.** Wait for direction before continuing to Task 2.

---

## TASK 2 — Structured Logging & Request-ID Middleware

**Goal:** Add a `src/alfred/tools/logging.py` module providing structured JSON logging and a request-ID middleware wired into `src/alfred/api.py`.

### Implementation

1. **Create `src/alfred/tools/logging.py`** — Per tool placement rule (`src/alfred/tools/{name}.py`). Provides: a `configure_logging(level: str) -> None` function reading `LOG_LEVEL` from the environment (default `INFO`); a `get_logger(name: str) -> logging.Logger` helper; JSON formatter producing `{"timestamp": ..., "level": ..., "logger": ..., "message": ..., "request_id": ...}`.
2. **Request-ID middleware** — ASGI middleware that reads `X-Request-ID` from the incoming request (or generates a UUID4 if absent), stores it in a `contextvars.ContextVar`, and injects it into the JSON log output. Wire the middleware into `src/alfred/api.py`.
3. **Wire `LOG_LEVEL`** — On application startup, call `configure_logging(os.environ.get("LOG_LEVEL", "INFO"))`.
4. **Add tests** — `tests/test_tools/test_logging.py` (per test placement rule: `tests/test_*.py`): verify JSON output shape; verify `LOG_LEVEL` env-var is respected; verify request-ID propagation.

### Verification

```bash
pyright src/alfred/tools/logging.py src/alfred/api.py
pytest tests/test_tools/test_logging.py -v
LOG_LEVEL=DEBUG uvicorn alfred.api:app --port 8000 &
curl -s -H "X-Request-ID: test-123" http://localhost:8000/healthz
# log output should contain "request_id": "test-123"
```

**Expected:**
- `pyright` clean on both changed files.
- All logging tests pass.
- JSON log lines appear on stdout with the injected request ID.

**Suggested commit message:** `tools: task 2 — structured JSON logging and request-ID middleware`

---

## TASK 3 — Graceful Shutdown

**Goal:** Ensure in-flight approval requests are drained or safely checkpointed before the process exits, via a FastAPI lifespan handler.

### Implementation

1. **Lifespan handler in `src/alfred/api.py`** — Use FastAPI's `lifespan` context manager. On shutdown, call a `drain_approvals(timeout: float)` function that waits up to a configurable timeout (default 10 s, overridable via `SHUTDOWN_DRAIN_TIMEOUT_S` env var) for pending approvals to complete or be checkpointed.
2. **`drain_approvals` logic** — Iterates `GET /approvals/pending`-equivalent in-process; calls `POST /approvals/expire` on any approval that cannot be completed within the timeout window; logs each expiry as a structured WARNING.
3. **Integration test** — `tests/test_api_shutdown.py` (per test placement rule): simulate an in-flight approval, trigger shutdown, verify the approval is either completed or expired and logged.

### Verification

```bash
pyright src/alfred/api.py
pytest tests/test_api_shutdown.py -v
```

**Expected:**
- `pyright` clean.
- Integration test passes: approval is expired with a WARNING log line containing the request ID.

**Suggested commit message:** `api: task 3 — graceful shutdown with approval drain`

### CHECKPOINT-2 — Shutdown Safety

**Question:** Does the lifespan handler drain or expire all in-flight approvals within the timeout, and does the integration test confirm this without flakiness?

**Evidence required:**
- Paste `pytest tests/test_api_shutdown.py -v` output showing the test passes on three consecutive runs (confirm no flakiness).
- Paste `pyright src/alfred/api.py` output showing zero errors.

| Observation | Likely call |
|---|---|
| Test passes 3/3 runs, pyright clean | PROCEED to Task 4 |
| Test passes but is timing-sensitive (sleep-dependent) | PIVOT — replace sleep-based timing with a proper mock before continuing |
| Test fails intermittently | STOP — investigate race condition; do not continue until stable |

**STOP HERE.** Wait for direction before continuing to Task 4.

---

## TASK 4 — CLI Implementation

**Goal:** Implement `src/alfred/cli.py` to close the `alfred.cli:main` declared-but-unimplemented gap, providing subcommands `plan`, `evaluate`, `serve`, `validate`, and `version`.

### Implementation

1. **Create `src/alfred/cli.py`** — The entry point declared in `pyproject.toml` (`alfred.cli:main`). Use a standard CLI library (e.g. `click` or `argparse` — whichever is already in `pyproject.toml` dependencies; do not add a new dependency without human approval).
2. **Subcommands:**
   - `alfred plan` — invokes the planner pipeline; accepts `--dry-run` (prints plan without executing).
   - `alfred evaluate` — invokes the evaluation pipeline; accepts `--dry-run`.
   - `alfred serve` — starts the FastAPI server via `uvicorn`; accepts `--host`, `--port`, `--reload`.
   - `alfred validate` — runs `scripts/validate_alfred_planning_facts.py` (or its successor) against a supplied handover document path.
   - `alfred version` — prints the package version from `importlib.metadata`.
3. **Exit codes** — 0 on success, 1 on handled error, 2 on usage error (CLI convention).
4. **`--help`** — every subcommand must expose a `--help` that describes its arguments.
5. **Add tests** — `tests/test_cli.py` (per test placement rule): cover `--help` exit code 0 for each subcommand; cover `version` output; cover `--dry-run` path for `plan` and `evaluate`.

### Verification

```bash
pyright src/alfred/cli.py
pytest tests/test_cli.py -v
alfred --help
alfred version
alfred plan --dry-run
alfred serve --help
alfred validate --help
```

**Expected:**
- `pyright` clean.
- All CLI tests pass.
- Each subcommand prints coherent `--help` text.
- `alfred version` prints the version string from package metadata.
- `alfred plan --dry-run` prints a plan without side effects.

**Suggested commit message:** `cli: task 4 — implement src/alfred/cli.py with all subcommands`

---

## TASK 5 — Docker Image & Compose

**Goal:** Produce a rootless, multi-stage `Dockerfile` running `alfred serve`, a `docker-compose.yml` for local development, and supporting files.

### Implementation

1. **`Dockerfile`** — Multi-stage build: builder stage installs dependencies; final stage copies only the wheel and runtime deps. Runs as a non-root user. `CMD ["alfred", "serve"]`. Exposes port 8000.
2. **`.dockerignore`** — Excludes `.git`, `__pycache__`, `*.pyc`, `tests/`, `docs/`, `.env*`, `*.egg-info`.
3. **`docker-compose.yml`** — `version: "3.9"`. Service `alfred` built from the `Dockerfile`, ports `8000:8000`, volume-mounts the workspace as read-only for RAG access, reads env vars from `.env` (via `env_file`).
4. **`.env.example`** — Documents every env var: `LOG_LEVEL`, `SHUTDOWN_DRAIN_TIMEOUT_S`, `ANTHROPIC_API_KEY` (or equivalent), `ALFRED_WORKSPACE_PATH`, any others discovered during implementation. **Never commit real secrets.**
5. **No `mypy`** — `Dockerfile` must not install or invoke `mypy` at any build stage.

### Verification

```bash
docker build -t alfred:local .
docker run --rm alfred:local alfred version
docker run --rm -p 8000:8000 alfred:local &
curl -s http://localhost:8000/healthz   # expect {"status":"ok"}
docker compose up --build -d
docker compose ps   # alfred service should be Up
docker compose down
```

**Expected:**
- Image builds without errors.
- `alfred version` runs inside the container.
- `/healthz` returns 200 from a running container.
- `docker compose up` brings the service up cleanly.

**Suggested commit message:** `docker: task 5 — Dockerfile, docker-compose.yml, .env.example`

### CHECKPOINT-3 — Container Green

**Question:** Does the Docker image build cleanly, run `alfred serve` as a non-root user, and respond to `/healthz`?

**Evidence required:**
- Paste `docker build -t alfred:local .` output (last 10 lines, including any layer cache summary).
- Paste `docker run --rm alfred:local whoami` output confirming non-root user.
- Paste `curl -s http://localhost:8000/healthz` from a running container showing `{"status":"ok"}`.

| Observation | Likely call |
|---|---|
| Build clean, non-root confirmed, /healthz 200 | PROCEED to Task 6 |
| Build succeeds but container runs as root | PIVOT — fix USER directive before continuing |
| Build fails on dependency resolution | STOP — investigate and fix; do not continue until clean build |

**STOP HERE.** Wait for direction before continuing to Task 6.

---

## TASK 6 — Release Workflow

**Goal:** Create `.github/workflows/release.yml` — a GitHub Actions workflow that builds and pushes the Docker image to GHCR and publishes a wheel to PyPI on version tags.

### Implementation

1. **Create `.github/workflows/release.yml`** — Per workflow placement rule (`.github/workflows/`, `*.yml`). Triggered on `push` events matching tags `v*.*.*`.
2. **Jobs:**
   - `build-and-push`: checks out, logs in to GHCR (`ghcr.io`), builds and pushes `ghcr.io/${{ github.repository }}:${{ github.ref_name }}` and `:latest`.
   - `publish-wheel`: builds the wheel with `pip wheel .`; publishes to PyPI using `pypa/gh-action-pypi-publish` with a trusted-publisher (OIDC) setup.
3. **No `mypy`** — the workflow must not invoke `mypy` at any step.
4. **Secrets** — use `GITHUB_TOKEN` for GHCR; use PyPI trusted publisher (no `PYPI_TOKEN` secret hardcoded).

### Verification

```bash
# Lint the workflow locally
pip install actionlint-py
actionlint .github/workflows/release.yml

# Dry-run: confirm the workflow file is valid YAML
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
```

**Expected:**
- `actionlint` reports no errors.
- YAML is valid.
- Workflow file is present at `.github/workflows/release.yml`.

**Suggested commit message:** `ci: task 6 — release workflow for GHCR and PyPI`

### CHECKPOINT-4 — Release Workflow Valid

**Question:** Is the release workflow syntactically valid, lint-clean, and correctly scoped to version tags only?

**Evidence required:**
- Paste `actionlint .github/workflows/release.yml` output showing zero errors.
- Paste the `on:` trigger block from the workflow file confirming `tags: ['v*.*.*']` scope.

| Observation | Likely call |
|---|---|
| actionlint clean, trigger scoped to version tags | PROCEED to Task 7 |
| actionlint reports step or permission errors | PIVOT — fix before continuing |
| Workflow triggers on all pushes (not just tags) | STOP — fix trigger scope; risk of unintended releases |

**STOP HERE.** Wait for direction before continuing to Task 7.

---

## TASK 7 — Documentation

**Goal:** Update `README.md` with quick-start sections for local dev and Docker; update relevant `docs/` entries to reflect the deployed state.

### Implementation

1. **`README.md`** — Add sections: "Quick Start (local)", "Quick Start (Docker)", "Environment Variables" (linking to `.env.example`), "CLI Reference" (linking to `alfred --help` output).
2. **`docs/` updates** — Any `docs/protocol/` or `docs/active/` file that references the deployment surface (e.g. `docs/protocol/architecture.md`) should be updated to note the new `/healthz`, `/readyz` endpoints and the CLI. Per doc placement rule: `docs/*.md`.
3. **Do not create new canonical handover docs** in this task — `docs/canonical/ALFRED_HANDOVER_6.md` is produced by promotion of this draft, not by this task.

### Verification

```bash
# Ensure all referenced paths exist
grep -E '`[^`]+`' README.md | grep -v 'exists today'
# Manual review: confirm no broken relative links in docs/
```

**Expected:**
- `README.md` contains quick-start Docker and local sections.
- All file paths referenced in the README exist in the repo.

**Suggested commit message:** `docs: task 7 — README quick-starts and deployment docs update`

---

## WHAT NOT TO DO

1. **Do not introduce `mypy`** — the repository uses `pyright` exclusively. Any PR adding `mypy` to `pyproject.toml` or CI must be rejected.
2. **Do not create a `src/alfred/api/` subpackage** — the API lives in a single module `src/alfred/api.py`. A subpackage violates the structural rule.
3. **Do not create a catch-all `src/alfred/schemas.py`** — schemas live as per-concern modules inside `src/alfred/schemas/`.
4. **Do not skip checkpoints** — each CHECKPOINT is a hard gate. Do not begin the next task until the human has reviewed the evidence and issued an explicit PROCEED.
5. **Do not commit `.env` files with real secrets** — only `.env.example` with placeholder values.
6. **Do not fabricate commits** in the Git History section of any handover — use only what `git log` returns verbatim.
7. **Do not weaken factual-validation hooks** — `scripts/validate_alfred_planning_facts.py` (or its successor installed in output-hardening-3) must remain in place and green after every task.
8. **Do not add Docker-related CI to the main `ci.yml` workflow** — the release workflow is separate (`release.yml`); keep CI and release concerns in distinct workflow files.
9. **Do not place new tool modules anywhere other than `src/alfred/tools/{name}.py`** — top-level helper scripts imported as tool modules are forbidden by the structural rule.
10. **Do not use `src/alfred/cli.py` as a top-level script** — it must be imported via the `alfred.cli:main` entry point declared in `pyproject.toml`.

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
- *executor to fill*

**next_handover_id:** ALFRED_HANDOVER_7