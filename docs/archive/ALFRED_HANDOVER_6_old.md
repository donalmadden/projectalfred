# Alfred's Handover Document #6 — Phase 7: Developer Experience & Deployment

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_6
**date:** 2026-04-20
**author:** Codex (manual correction and promotion over Alfred Planner draft)
**previous_handover:** ALFRED_HANDOVER_5
**baseline_state:** Phase 6 is fully closed and the follow-on grounding remediation (`output-hardening-2`: repo-truth snapshot input, hardened planner prompt, factual validator, and grounded generator metadata) is fully committed; the system is functionally complete but ships no container, no implemented CLI, and no deployment surface.

**Reference Documents:**
- `docs/ALFRED_HANDOVER_5.md` — authoritative Phase 6 close-out and baseline for this handover.
- `docs/ALFRED_HANDOVER_5_OUTPUT_HARDENING.md` — grounding-remediation plan that established the repo-truth and factual-validator invariants this phase must preserve.

The post-Phase-6 grounding remediation hardened Alfred's planning pipeline against factual hallucinations and introduced the repo-truth snapshot as the authoritative source for all current-state claims. The system now has nine FastAPI endpoints, five agents, six tool modules, a declared CLI entry-point in `pyproject.toml`, and a functioning orchestrator — but it is still distributed only as a raw Python source tree. Phase 7 rectifies this by producing a shippable, operationally hardened package: a Docker image, an implemented CLI, structured logging, graceful shutdown, health/readiness probes, and a publish-ready PyPI wheel. Every deliverable is gated by a checkpoint that requires the executor to paste real evidence before proceeding.

---

## WHAT EXISTS TODAY

### Git History

```
3f88354  output-hardening-2: task 4 — ground phase7 generator metadata
6530f6b  output-hardening-2: task 3 — add factual validator for planning drafts
ea37972  output-hardening-2: task 2 — harden planner against factual hallucinations
53e6e77  output-hardening-2: task 1 — add repo truth snapshot input
86efac9  fix: increase anthropic max_tokens to 8192 for planner output
d088630  phase7: add generate_phase7.py planner script
b3600e5  fix: sort imports in generate_phase6.py (ruff I001)
6f68a3d  phase6: close — post-mortem and checkpoint-6-2 evidence
b7ede23  phase6: task 5 — docs update
a4e82ed  phase6: task 4 — ci pipeline
08f5f02  phase6: task 3 — coverage gates
b53f2f4  phase6: task 2 — eval harness
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### Current Module Inventory

All paths are relative to `~/code/projectalfred`.

| Layer | Names |
|---|---|
| **Agents** (`src/alfred/agents/`) | `compiler`, `planner`, `quality_judge`, `retro_analyst`, `story_generator` |
| **Tools** (`src/alfred/tools/`) | `git_log`, `github_api`, `llm`, `persistence`, `rag`, `repo_facts` |
| **Top-level** (`src/alfred/`) | `agents`, `api`, `orchestrator`, `schemas`, `tools` |
| **FastAPI module** | `src/alfred/api.py` |
| **Endpoints (9)** | `POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`, `POST /approvals/expire`, `POST /retrospective`, `POST /compile`, `GET /dashboard` |
| **Packaging** | `pyproject.toml` exists with `[project]`, `[project.scripts]`, and CLI entry `alfred.cli:main` (implementation target missing today) |
| **Type checker** | `pyright` (mypy is NOT in use) |

### Operational Gaps (What Is Missing Today)

- **No Docker image** — there is no `Dockerfile`, no `docker-compose.yml`, and no `.dockerignore`.
- **No health / readiness probes** — `GET /dashboard` exists but no `GET /healthz` or `GET /readyz` endpoints suitable for container orchestrators.
- **No structured logging** — logging is ad-hoc; no JSON formatter, no request-ID propagation, no log-level env-var control.
- **No graceful shutdown** — the uvicorn process is killed hard; in-flight approval requests are not drained.
- **CLI module is still missing** — `pyproject.toml` declares `alfred.cli:main`, but `src/alfred/cli.py` does not yet exist.
- **No published wheel** — `pyproject.toml` carries packaging metadata but no release workflow exists.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Functions only** — no classes except Pydantic models and FastAPI routers.
2. **Pyright for type-checking** — mypy is not in use and must not be introduced.
3. **Repo-truth snapshot is authoritative** — `src/alfred/tools/repo_facts` feeds all planning; nothing in this phase may bypass it.
4. **Both validators must remain green** — `scripts/validate_alfred_handover.py` (structural) and `scripts/validate_alfred_planning_facts.py` (factual) are hard gates.
5. **`src/alfred/api.py` is the FastAPI module** — do not move or rename it.

---

## HARD RULES

1. **Work in `~/code/projectalfred`.** Do not touch any sibling repository.
2. **Functions only.** No new classes except Pydantic models and FastAPI routers.
3. **Pydantic schemas for everything.** All new config, all new state, all new agent I/O.
4. **Never hardcode secrets or paths.** All credentials and environment-specific values come from environment variables with explicit defaults documented in `.env.example`.
5. **Pyright must pass.** `pyright src/` must exit 0 after every task. Do not introduce mypy.
6. **Ruff must pass.** `ruff check src/ scripts/` must exit 0 after every task.
7. **Existing tests must stay green.** No task may regress the test suite.
8. **Both validators are hard gates.** `python scripts/validate_alfred_handover.py` and `python scripts/validate_alfred_planning_facts.py` must both pass on any handover artifact produced during this phase.
9. **The Docker image must be rootless.** The container must not run as UID 0.
10. **No net-new runtime dependencies without explicit approval.** Each new `[project.dependencies]` entry must appear in the task that introduces it, with justification.

---

## WHAT THIS PHASE PRODUCES

- `Dockerfile` and `.dockerignore` producing a rootless, multi-stage image that runs `alfred serve`.
- `docker-compose.yml` (development profile) wiring the Alfred API, a volume-mounted workspace, and environment variable injection from `.env`.
- `GET /healthz` and `GET /readyz` endpoints in `src/alfred/api.py` suitable for liveness and readiness probes.
- Structured JSON logging via a `src/alfred/tools/logging.py` module, with request-ID middleware and `LOG_LEVEL` env-var control.
- Graceful shutdown: in-flight approval requests are drained (or safely checkpointed) before the process exits.
- A fully fleshed-out CLI (`src/alfred/cli.py`) with subcommands `plan`, `evaluate`, `serve`, `validate`, and `version`, each with `--help`, correct exit codes, and `--dry-run` where appropriate.
- `.env.example` documenting every environment variable the system reads.
- A GitHub Actions release workflow (`.github/workflows/release.yml`) that builds and pushes the Docker image to GHCR and publishes a wheel to PyPI on version tags.
- Updated `README.md` with Quick-start (Docker) and Quick-start (pip install) sections.

Out of scope:
- Kubernetes manifests or Helm charts (operational concern for a later phase).
- Multi-tenant or auth hardening (separate security phase).
- Changing any existing agent logic, tool implementation, or schema.
- Introducing a database; persistence remains file-backed via `src/alfred/tools/persistence`.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Health & Readiness Probes | `GET /healthz`, `GET /readyz` in `src/alfred/api.py` | CHECKPOINT-1 |
| 2 | Structured Logging & Request-ID Middleware | `src/alfred/tools/logging.py`, middleware wired into `src/alfred/api.py` | — |
| 3 | Graceful Shutdown | Lifespan handler draining approvals; integration test | CHECKPOINT-2 |
| 4 | CLI Polish | Fully fleshed `src/alfred/cli.py`; all subcommands with `--help` and exit codes | — |
| 5 | Docker Image & Compose | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example` | CHECKPOINT-3 |
| 6 | Release Workflow | `.github/workflows/release.yml`; wheel + GHCR publish on version tag | CHECKPOINT-4 |
| 7 | Documentation | `README.md` quick-starts; updated `docs/` | — |

---

## TASK 1 — Health & Readiness Probes

**Goal:** Add `GET /healthz` (liveness) and `GET /readyz` (readiness) endpoints to `src/alfred/api.py` so container orchestrators can gate traffic correctly.

### Implementation

1. **Define response schema** — Add a new `src/alfred/schemas/health.py` (preferred) or extend the existing `src/alfred/schemas/` package with:
   ```python
   class HealthResponse(BaseModel):
       status: str          # "ok" | "degraded" | "unavailable"
       version: str         # importlib.metadata version string
       checks: dict[str, str]  # named sub-checks → status string
   ```
2. **Implement `/healthz`** — Always returns `{"status": "ok", "version": "...", "checks": {}}` with HTTP 200. This is a liveness probe: if the process can respond, it is alive.
3. **Implement `/readyz`** — Runs lightweight dependency checks (e.g., can the persistence layer open its configured path? Is the LLM client importable?). Returns HTTP 200 when all checks pass, HTTP 503 when any check fails. Populate `checks` with one key per dependency.
4. **Wire into `src/alfred/api.py`** — Register both routes on the existing `app` instance. Do not create a new FastAPI sub-application.
5. **Write tests** — Add `tests/test_health.py` covering: (a) `/healthz` always 200, (b) `/readyz` 200 under nominal conditions, (c) `/readyz` 503 when a dependency is mocked to fail.

### Verification

```bash
# Static analysis
pyright src/
ruff check src/ scripts/

# Unit tests
pytest tests/test_health.py -v

# Manual smoke (requires a running server)
uvicorn alfred.api:app --port 8000 &
curl -sf http://localhost:8000/healthz | python -m json.tool
curl -sf http://localhost:8000/readyz  | python -m json.tool
kill %1
```

**Expected:**
- `pyright` exits 0, no new errors.
- `ruff` exits 0.
- `pytest tests/test_health.py` — all tests green.
- `curl /healthz` returns `{"status": "ok", ...}` with HTTP 200.
- `curl /readyz` returns `{"status": "ok", ...}` with HTTP 200 under normal conditions.

**Suggested commit message:** `phase7: task 1 — health and readiness probes`

### CHECKPOINT-1 — Probe Contracts

**Question:** Do both probe endpoints return correct status codes and schema-valid bodies before we build the container that depends on them?

**Evidence required:**
- Paste the full output of `pytest tests/test_health.py -v` (all lines, no truncation).
- Paste `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz` (must be `200`).
- Paste `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/readyz` (must be `200`).
- Paste `pyright src/` exit-code line.

| Observation | Likely call |
|---|---|
| All tests green, both curls return 200, pyright exits 0 | PROCEED to Task 2 |
| `/readyz` returns 503 under nominal conditions | PIVOT — fix dependency check logic before proceeding |
| pyright reports new errors | PIVOT — fix type errors before proceeding |
| Any test fails | STOP — do not proceed until root cause is identified and approved |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 2.

---

## TASK 2 — Structured Logging & Request-ID Middleware

**Goal:** Replace ad-hoc `print`/`logging` calls with a consistent JSON logging layer and inject a `X-Request-ID` header on every request/response pair.

### Implementation

1. **Create `src/alfred/tools/logging.py`** — Provide:
   - `configure_logging(level: str = "INFO") -> None` — sets up a `logging.StreamHandler` with a JSON formatter (use `python-json-logger` if approved, otherwise hand-roll a `logging.Formatter` subclass).
   - `get_logger(name: str) -> logging.Logger` — thin wrapper around `logging.getLogger`.
2. **Request-ID middleware** — Add a Starlette `BaseHTTPMiddleware` subclass (one function is acceptable via `@app.middleware("http")`) that: (a) reads `X-Request-ID` from the incoming request or generates a UUID4, (b) stores it in a `contextvars.ContextVar`, (c) injects it into the JSON log records via a `logging.Filter`, (d) echoes it back in the response header.
3. **Environment-variable control** — Read `LOG_LEVEL` from `os.environ` (default `"INFO"`) and call `configure_logging` in the FastAPI lifespan startup hook.
4. **Migrate existing log calls** — Replace any bare `print()` statements and `logging.basicConfig()` calls in `src/alfred/` with `get_logger(__name__)`.
5. **Tests** — Add `tests/test_logging_middleware.py`: assert that a response to any endpoint carries `X-Request-ID` in its headers, and that repeated calls with the same ID in the request are echoed back.

### Verification

```bash
pyright src/
ruff check src/ scripts/
pytest tests/test_logging_middleware.py -v
LOG_LEVEL=DEBUG uvicorn alfred.api:app --port 8000 &
curl -H "X-Request-ID: test-abc-123" http://localhost:8000/healthz -v 2>&1 | grep -i request-id
kill %1
```

**Expected:**
- Response headers include `x-request-id: test-abc-123`.
- Log output is JSON (one object per line) when piped to a file.
- All new tests green; no regressions.

**Suggested commit message:** `phase7: task 2 — structured logging and request-id middleware`

---

## TASK 3 — Graceful Shutdown

**Goal:** Ensure that when the process receives `SIGTERM` (as Docker/Kubernetes sends on `docker stop`), in-flight approval requests are either completed or safely checkpointed rather than dropped mid-write.

### Implementation

1. **Audit the lifespan** — `src/alfred/api.py` must use FastAPI's `lifespan` context manager (not deprecated `on_event`). Confirm this is already the case; if not, migrate.
2. **Approval drain** — In the lifespan shutdown block, call a `drain_pending_approvals(timeout: float = 10.0) -> None` function (implement in `src/alfred/tools/persistence.py` or a new `src/alfred/orchestrator.py` helper). This function: (a) reads all pending approvals from the persistence layer, (b) marks each as `expired` with reason `"shutdown"` if it cannot be safely completed, (c) flushes to disk before returning.
3. **SIGTERM wiring** — Uvicorn handles SIGTERM → lifespan shutdown automatically. Verify this end-to-end in the integration test.
4. **Integration test** — Add `tests/test_graceful_shutdown.py`: spawn a uvicorn subprocess, POST a pending approval, send SIGTERM, wait for process exit, assert the approval file on disk is either resolved or marked `expired/shutdown` (not corrupt/missing).

### Verification

```bash
pyright src/
ruff check src/ scripts/
pytest tests/test_graceful_shutdown.py -v --timeout=30
```

**Expected:**
- Integration test passes within 30 s.
- No approval state files are left in an inconsistent state after SIGTERM.

**Suggested commit message:** `phase7: task 3 — graceful shutdown with approval drain`

### CHECKPOINT-2 — Shutdown Safety

**Question:** Is the approval-drain logic provably safe before we wrap this process in a container that will receive SIGTERM on every `docker stop`?

**Evidence required:**
- Paste the full output of `pytest tests/test_graceful_shutdown.py -v --timeout=30`.
- Paste the content of the approval state file written during the test (must show `expired` or resolved, not raw/corrupt).
- Paste `pyright src/` exit-code line.

| Observation | Likely call |
|---|---|
| Test passes, file shows clean terminal state, pyright exits 0 | PROCEED to Task 4 |
| Test passes but file is corrupt or missing | STOP — data-loss risk; escalate before containerising |
| Test times out | PIVOT — investigate blocking I/O in drain path |
| pyright reports errors | PIVOT — fix before proceeding |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 4.

---

## TASK 4 — CLI Polish

**Goal:** Make the `alfred` CLI a first-class tool with discoverable subcommands, correct exit codes, and `--dry-run` guards on destructive actions.

### Implementation

1. **Subcommand inventory** — `src/alfred/cli.py` must expose:
   | Subcommand | Action | Dry-run? |
   |---|---|---|
   | `alfred serve` | Start uvicorn on configured host/port | No |
   | `alfred plan` | Call `POST /generate` and print the draft handover | Yes |
   | `alfred evaluate` | Call `POST /evaluate` and print the result | Yes |
   | `alfred validate` | Run `scripts/validate_alfred_handover.py` and `scripts/validate_alfred_planning_facts.py` against a local file | No |
   | `alfred version` | Print package version and exit 0 | No |
2. **Exit codes** — `0` = success, `1` = user error (bad args), `2` = upstream error (API call failed), `3` = validation failure.
3. **`--dry-run`** — For `plan` and `evaluate`, `--dry-run` prints the request payload that would be sent without making the HTTP call. Exit code 0.
4. **`--help` quality** — Every subcommand must have a one-line description and every argument must have a help string.
5. **Use `argparse`.** It is in the standard library and avoids introducing a new CLI dependency just to implement the missing module.
6. **Tests** — Add `tests/test_cli.py` covering: `alfred version` exit 0, `alfred validate --help` exit 0, `alfred plan --dry-run` prints JSON and exits 0.

### Verification

```bash
pyright src/
ruff check src/ scripts/
pytest tests/test_cli.py -v
alfred --help
alfred version
alfred plan --dry-run --sprint-goal "test"
alfred validate --help
```

**Expected:**
- All subcommands reachable via `alfred <subcommand> --help`.
- `alfred version` prints a semver string and exits 0.
- `alfred plan --dry-run` prints valid JSON and exits 0 (no network call).
- All new tests green.

**Suggested commit message:** `phase7: task 4 — cli polish`

---

## TASK 5 — Docker Image & Compose

**Goal:** Produce a reproducible, rootless Docker image and a development compose file so contributors can run Alfred with a single command.

### Implementation

1. **`Dockerfile`** — Multi-stage build:
   - **Stage 1 (`builder`):** `python:3.12-slim`, install build dependencies, run `pip wheel --no-deps -w /wheels .` to produce a wheel.
   - **Stage 2 (`runtime`):** `python:3.12-slim`, create a non-root user (`alfred`, UID 1000), copy wheels from builder, `pip install --no-index --find-links /wheels alfred`, set `USER alfred`, expose port 8080, `CMD ["alfred", "serve"]`.
2. **`.dockerignore`** — Exclude `.git`, `__pycache__`, `*.pyc`, `.env`, `tests/`, `docs/`, `*.egg-info`.
3. **`docker-compose.yml`** — Single service `alfred-api`, build from `.`, env-file `.env`, port `8080:8080`, volume-mount `./workspace:/home/alfred/workspace` (for persistence layer), healthcheck using `/healthz`.
4. **`.env.example`** — Document every env var: `LOG_LEVEL`, `ALFRED_WORKSPACE`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `ALFRED_HOST`, `ALFRED_PORT`.
5. **Tests** — Add `tests/test_docker_build.py` (skipped unless `DOCKER_AVAILABLE=1`): assert `docker build` exits 0, `docker run --rm alfred-local alfred version` exits 0 and prints a semver string.

### Verification

```bash
docker build -t alfred-local .
docker run --rm alfred-local alfred version
docker run --rm --env-file .env alfred-local alfred serve &
curl -sf http://localhost:8080/healthz
docker stop $(docker ps -q --filter ancestor=alfred-local)
```

**Expected:**
- `docker build` exits 0 with no warnings about running as root.
- `alfred version` inside the container prints a semver string.
- `/healthz` returns HTTP 200 from the containerised process.

**Suggested commit message:** `phase7: task 5 — dockerfile and compose`

### CHECKPOINT-3 — Container Integrity

**Question:** Does the image build cleanly, run rootless, and pass its own health probe before we publish a release workflow that pushes it to GHCR?

**Evidence required:**
- Paste `docker build` final line (must include image ID, no error).
- Paste `docker inspect alfred-local --format '{{.Config.User}}'` (must be `alfred` or UID `1000`, not empty/root).
- Paste `curl -s http://localhost:8080/healthz` JSON body.
- Paste `pyright src/` exit-code line.

| Observation | Likely call |
|---|---|
| Build succeeds, user is non-root, `/healthz` returns 200 | PROCEED to Task 6 |
| Build succeeds but container runs as root | PIVOT — fix USER directive before publishing |
| `/healthz` returns non-200 inside container | PIVOT — investigate missing env vars or path issues |
| Build fails | STOP — paste full build log for diagnosis |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 6.

---

## TASK 6 — Release Workflow

**Goal:** Automate wheel publication to PyPI and Docker image push to GHCR on every version tag push.

### Implementation

1. **`.github/workflows/release.yml`** — GitHub Actions workflow triggered by `push: tags: ['v*.*.*']`:
   - **Job `build-wheel`:** `pip install build`, `python -m build`, upload dist as artifact.
   - **Job `push-image`:** `docker/build-push-action`, authenticate to GHCR using `GITHUB_TOKEN`, tag as `ghcr.io/${{ github.repository }}:${{ github.ref_name }}` and `:latest`.
   - **Job `publish-pypi`:** download wheel artifact, `twine upload` using `PYPI_TOKEN` secret (must be pre-configured in repo settings — document this in the workflow file comment).
2. **Version source of truth** — version string lives in `pyproject.toml` `[project] version`; the tag must match it. Add a workflow step that installs the package and asserts `alfred version` matches the git tag, failing fast if they diverge.
3. **No secrets in source** — `PYPI_TOKEN` and `ANTHROPIC_API_KEY` are GitHub Actions secrets, never in the workflow YAML values.

### Verification

```bash
# Local pre-flight (no actual publish)
python -m build
twine check dist/*
act push --eventpath ci/test-tag-event.json --dry-run   # if 'act' is available
```

**Expected:**
- `python -m build` exits 0, produces `dist/alfred-*.whl` and `dist/alfred-*.tar.gz`.
- `twine check dist/*` exits 0 with no warnings.
- Workflow YAML is valid (no `act` required; `yamllint .github/workflows/release.yml` exits 0).

**Suggested commit message:** `phase7: task 6 — release workflow`

### CHECKPOINT-4 — Release Readiness

**Question:** Is the release pipeline safe to merge — i.e., does it correctly gate on version consistency and avoid secret leakage — before we tag `v1.0.0`?

**Evidence required:**
- Paste `twine check dist/*` output (must be `PASSED`).
- Paste `yamllint .github/workflows/release.yml` output (must exit 0).
- Confirm (yes/no): `PYPI_TOKEN` secret is configured in GitHub repo settings.
- Confirm (yes/no): workflow YAML contains no literal secret values.

| Observation | Likely call |
|---|---|
| `twine check` passes, YAML valid, secrets confirmed external | PROCEED to Task 7 |
| `twine check` reports metadata errors | PIVOT — fix `pyproject.toml` before tagging |
| YAML invalid | PIVOT — fix workflow syntax |
| Any secret value appears literally in YAML | STOP — security issue; do not merge |

**STOP HERE.** Paste evidence and wait for direction before continuing to Task 7.

---

## TASK 7 — Documentation

**Goal:** Update `README.md` and `docs/` so a new contributor can be productive in under five minutes using either Docker or pip.

### Implementation

1. **`README.md` Quick-start (Docker):**
   ```bash
   cp .env.example .env   # fill in ANTHROPIC_API_KEY
   docker compose up
   curl http://localhost:8080/healthz
   ```
2. **`README.md` Quick-start (pip):**
   ```bash
   pip install alfred
   alfred serve
   ```
3. **Environment variable reference table** — one row per var: name, default, required?, description.
4. **CLI reference** — one paragraph per subcommand, auto-generated from `alfred <cmd> --help` output (paste verbatim, fenced).
5. **Architecture diagram** — update any existing diagram to show the new `/healthz`, `/readyz` endpoints and the structured-logging middleware layer.
6. **`docs/operations.md`** — new file covering: how to read JSON logs, how to set `LOG_LEVEL`, how to run `docker compose down`, how `SIGTERM` drain works.

### Verification

```bash
# Markdown lint (if markdownlint-cli is available)
markdownlint README.md docs/
# Otherwise: manual review for broken links and unfenced code blocks
```

**Expected:**
- `README.md` opens with a Quick-start that a reader can follow without prior context.
- Every env var in `.env.example` has a matching row in the reference table.
- No broken internal links.

**Suggested commit message:** `phase7: task 7 — documentation`

---

## WHAT NOT TO DO

1. **Do not move or rename `src/alfred/api.py`.** The FastAPI module path is a hard contract; the Docker `CMD` and all internal imports depend on it.
2. **Do not introduce mypy.** The type checker is `pyright`. Adding mypy config will cause confusion and CI conflicts.
3. **Do not add new classes outside Pydantic models and FastAPI routers.** The functions-only rule is non-negotiable.
4. **Do not run as root in the container.** The Dockerfile must set `USER alfred` (UID 1000) in the runtime stage. A rootful image will be rejected at CHECKPOINT-3.
5. **Do not embed secrets or API keys in any source file, Dockerfile, or workflow YAML.** All secrets are injected at runtime via environment variables or GitHub Actions secrets.
6. **Do not change any existing agent, tool, or schema logic.** This phase is purely operational hardening and developer experience. Any behaviour change requires a separate handover.
7. **Do not skip checkpoints.** Each CHECKPOINT requires pasted evidence. Self-certifying ("I checked, it's fine") is not acceptable.
8. **Do not add a second CLI framework.** Use `argparse` unless a different single framework is explicitly approved. Mixing frameworks will be rejected at code review.
9. **Do not publish a release (tag `v*.*.*`) before CHECKPOINT-4 is approved.** Premature tagging cannot be undone on PyPI.
10. **Do not bypass either validator.** `scripts/validate_alfred_handover.py` and `scripts/validate_alfred_planning_facts.py` must both pass on any planning artifact produced during this phase.

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
- *executor to fill*

**next_handover_id:** ALFRED_HANDOVER_7
