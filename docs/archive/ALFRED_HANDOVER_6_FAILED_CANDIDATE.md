
# Alfred's Handover Document #6 — Phase 7: Developer Experience & Deployment

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** ALFRED_HANDOVER_6
**date:** 2026-04-21
**author:** Alfred Planner (draft for human approval)
**previous_handover:** ALFRED_HANDOVER_5
**baseline_state:** Phase 6 is fully closed and three rounds of output-hardening (repo-truth snapshot, factual validator, planning-realism layer, and critique-loop integration) are committed; the system is functionally complete but ships no container, no implemented CLI, and no deployment surface.

**Reference Documents:**
- `docs/canonical/ALFRED_HANDOVER_5.md` — authoritative Phase 6 close-out and the baseline from which Phase 7 departs.
- `docs/active/ALFRED_HANDOVER_5_OUTPUT_HARDENING.md` — grounding-remediation plan that established the repo-truth and factual-validator invariants this phase must preserve.
- `docs/active/ALFRED_HANDOVER_4_OUTPUT_HARDENING.md` — earlier output-hardening context; useful for understanding the progression of validator constraints.
- `docs/active/CODEX_HANDOVER_GROUNDING_REFINEMENT.md` — grounding-refinement decisions carried forward into Phase 7.
- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — planning-realism rules enforced by the factual validator; executor must not violate these.
- `docs/protocol/architecture.md` — canonical architecture reference; topology claims in this document must agree with it.

This handover exists because the canonical Phase 7 document (docs/canonical/ALFRED_HANDOVER_6.md) must be refreshed to reflect the real repository state after three `output-hardening-3` commits (phases A, B, and C) that post-date the historical snapshot. The prior draft carried stale claims about module paths, tooling, and deliverable scope. This revision corrects those claims, applies the full CLAIM TAXONOMY and THREE-STATE VOCABULARY, and establishes the forward plan for the remaining Phase 7 work: CLI implementation, health probes, structured logging, graceful shutdown, Docker packaging, and a release workflow.

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

### Module & API Inventory

The following items **exist today** in the workspace:

**Agent modules** (`src/alfred/agents`): `compiler.py`, `planner.py`, `quality_judge.py`, `retro_analyst.py`, `story_generator.py`

**Tool modules** (`src/alfred/tools`): `docs_policy.py`, `git_log.py`, `github_api.py`, `llm.py`, `persistence.py`, `rag.py`, `reference_doc_validator.py`, `repo_facts.py`

**Top-level package names under `src/alfred`**: `agents`, `api`, `orchestrator`, `schemas`, `tools`

**FastAPI application** exists today at `src/alfred/api.py` (single-module; a subpackage at src/alfred/api is forbidden by structural rules).

**FastAPI endpoints** (9 total, all exist today):
`POST /generate`, `POST /evaluate`, `POST /approvals/request`, `POST /approve`, `GET /approvals/pending`, `POST /approvals/expire`, `POST /retrospective`, `POST /compile`, `GET /dashboard`

**Packaging**: `pyproject.toml` exists today with `[project]` and `[project.scripts]` sections present-but-incomplete — the CLI entry `alfred.cli:main` is declared in `[project.scripts]` but src/alfred/cli.py **does not exist yet** (vocabulary: **declared but unimplemented**).

**Type checker**: `pyright` is in use. `mypy` is **not** in use and must not be introduced.

**Partial state**:
- src/alfred/cli.py — **declared but unimplemented**. The entry point `alfred.cli:main` is declared in `pyproject.toml [project.scripts]`; the implementation file has not been created.

**Not yet present** (to be created in this phase):
- src/alfred/tools/logging.py
- `GET /healthz` and `GET /readyz` endpoints in `src/alfred/api.py`
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`
- .github/workflows/release.yml

### Output-Hardening Invariants (Do Not Break)

Three rounds of output-hardening (`output-hardening-2` tasks 1–4, `output-hardening-3` phases A–C) have established the following invariants that every executor and planner must preserve:

1. **Repo-truth snapshot input** — the planner prompt is seeded with authoritative workspace facts; no claim about present-tense state may contradict these facts.
2. **Factual validator** — `scripts/validate_alfred_planning_facts.py` (or equivalent) gates plan promotion; any draft that contradicts repo facts fails closed.
3. **Typed factual findings** — validator output uses the CLAIM TAXONOMY categories (`METADATA`, `REFERENCE_DOC`, `CURRENT_PATH`, `CURRENT_TOPOLOGY`, `CURRENT_TOOLING`, `PARTIAL_STATE`, `PYPROJECT_STATE`, `PLACEMENT`, `HARD_RULE`, `TASK_GRANULARITY`); executor must not strip or ignore typed findings.
4. **Planning-realism layer** — tasks must name concrete file paths and verification commands; vague intent-only work items are rejected.
5. **Critique-loop integration** — the generator applies a self-critique pass against the CLAIM TAXONOMY before emitting output; no regression to un-typed findings is allowed.

### Key Design Decisions Inherited (Do Not Revisit)

1. **Single API module**: FastAPI lives exclusively at `src/alfred/api.py`; a subpackage (src/alfred/api) is forbidden.
2. **One schema per concern**: Schema modules live under `src/alfred/schemas`; a single catch-all src/alfred/schemas.py is forbidden.
3. **Agent/tool mirroring**: Every agent module in `src/alfred/agents` must have mirrored tests under `tests/test_agents`; every tool module in `src/alfred/tools` must have mirrored tests under `tests/test_tools`.
4. **`pyright` only**: `mypy` must not be introduced.
5. **No Docker before Phase 7**: Container artefacts were explicitly deferred to this phase; they are now in scope.
6. **Checkpoint-gated execution**: No task may begin until its preceding checkpoint has been approved by a human; the planner never self-approves.

---

## HARD RULES

1. **Do not use `mypy`** — the repository type-checker is `pyright`; introducing `mypy` configuration or invocations is a `HARD_RULE` violation.
2. **Do not create `src/alfred/api/`** — the FastAPI app must remain a single module at `src/alfred/api.py`; a subpackage is structurally forbidden.
3. **Do not create `src/alfred/schemas.py`** — schema concerns must be split into individual modules under `src/alfred/schemas/`.
4. **New tool modules go under `src/alfred/tools/`** — per tool placement rule; top-level helper scripts imported as tool modules are forbidden.
5. **New workflow files go under `.github/workflows/`** — per workflow placement rule; file names must be kebab-case ending in `.yml` or `.yaml`.
6. **New test files go under `tests/`** — per test placement rule; naming convention is `test_{subject}.py`.
7. **Do not fabricate commits** — the `### Git History` section must contain only the commits supplied verbatim above.
8. **Do not collapse partial state** — `src/alfred/cli.py` is declared but unimplemented; it must never be described as either fully existing or entirely absent from the plan.
9. **Planner drafts only** — this document is a draft for human approval; no executor may begin implementation before a human approves this handover.
10. **Preserve output-hardening invariants** — no change may disable or weaken the factual validator, repo-truth snapshot input, planning-realism layer, or critique-loop integration established in `output-hardening-2` and `output-hardening-3`.

---

## WHAT THIS PHASE PRODUCES

- `GET /healthz` and `GET /readyz` endpoints added to `src/alfred/api.py` (liveness and readiness probes).
- `src/alfred/tools/logging.py` — structured JSON logging module with request-ID middleware and `LOG_LEVEL` env-var control (per tool placement rule).
- `src/alfred/cli.py` — full implementation of the declared-but-unimplemented CLI entry point; subcommands: `plan`, `evaluate`, `serve`, `validate`, `version`, each with `--help`, correct exit codes, and `--dry-run` where appropriate.
- `Dockerfile` and `.dockerignore` — rootless, multi-stage image that runs `alfred serve`.
- `docker-compose.yml` — development profile wiring the Alfred API, a volume-mounted workspace, and env-var injection from `.env`.
- `.env.example` — documents every environment variable the system reads.
- `.github/workflows/release.yml` — GitHub Actions release workflow that builds and pushes the Docker image to GHCR and publishes a wheel to PyPI on version tags (per workflow placement rule: kebab-case `.yml` under `.github/workflows/`).
- `tests/test_tools/test_logging.py` — mirrored tests for `src/alfred/tools/logging.py` (per tool structural rule).
- `tests/test_agents/` — any new agent tests required by changes in this phase.

Out of scope:
- Database migrations or persistent storage backends (beyond what already exists).
- Kubernetes manifests or Helm charts.
- Load testing or performance benchmarking infrastructure.
- Any change that weakens the output-hardening invariants.

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | Health & Readiness Probes | `GET /healthz`, `GET /readyz` in `src/alfred/api.py` | CHECKPOINT-1 |
| 2 | Structured Logging & Request-ID Middleware | `src/alfred/tools/logging.py` + `tests/test_tools/test_logging.py`; middleware wired into `src/alfred/api.py` | — |
| 3 | Graceful Shutdown | Lifespan handler draining in-flight approvals; integration test in `tests/` | CHECKPOINT-2 |
| 4 | CLI Implementation | `src/alfred/cli.py` fully implemented; all subcommands with `--help`, exit codes, `--dry-run` | — |
| 5 | Docker Image & Compose | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example` | CHECKPOINT-3 |
| 6 | Release Workflow | `.github/workflows/release.yml`; wheel + GHCR publish on version tag | CHECKPOINT-4 |
| 7 | Documentation Refresh | Updated `docs/` quick-starts; `README.md` Docker and CLI usage sections | — |

---

## TASK 1 — Health & Readiness Probes

**Goal:** Add `GET /healthz` (liveness) and `GET /readyz` (readiness) endpoints to `src/alfred/api.py` so the container runtime and load balancer can probe the service.

### Implementation

1. **Add `/healthz` route** — In `src/alfred/api.py`, register a `GET /healthz` route returning `{"status": "ok"}` with HTTP 200. This is a pure liveness signal; it must not call external services.
2. **Add `/readyz` route** — Register a `GET /readyz` route that checks any critical dependencies (e.g., LLM client reachable, persistence layer responsive) and returns `{"status": "ready"}` on HTTP 200 or `{"status": "not_ready", "reason": "<detail>"}` on HTTP 503.
3. **Wire into existing app** — Both routes are added to the existing FastAPI app instance in `src/alfred/api.py`; no new file is created for these endpoints (structural rule: single module at `src/alfred/api.py`).
4. **Add tests** — Create or extend `tests/test_api.py` with test cases covering: 200 from `/healthz`; 200 from `/readyz` when dependencies are healthy; 503 from `/readyz` when a dependency is unavailable (mock the dependency).

### Verification

```bash
# Run the test suite
pytest tests/test_api.py -v -k "healthz or readyz"

# Spot-check live (requires a running server)
uvicorn alfred.api:app --port 8000 &
curl -s http://localhost:8000/healthz | python -m json.tool
curl -s http://localhost:8000/readyz  | python -m json.tool
```

**Expected:**
- `pytest` reports all new probe tests passing with no regressions in existing API tests.
- `curl /healthz` returns `{"status": "ok"}` with HTTP 200.
- `curl /readyz` returns `{"status": "ready"}` with HTTP 200 when dependencies are healthy.

**Suggested commit message:** `api: task 1 — add /healthz and /readyz probes`

### CHECKPOINT-1 — Probe Correctness

**Question:** Do both health endpoints respond correctly under nominal and degraded conditions, and do the tests pass cleanly?

**Evidence required:**
- Executor pastes the full `pytest` output for the probe tests verbatim.
- Executor pastes `curl` responses for both `/healthz` and `/readyz` from a live server.
- Executor confirms no pre-existing API tests have regressed (paste summary line).

| Observation | Likely call |
|---|---|
| All probe tests green; `/healthz` returns 200; `/readyz` returns 200 healthy / 503 degraded | PROCEED |
| `/readyz` always returns 200 regardless of dependency state (check skipped) | PIVOT — fix readiness logic before continuing |
| Pre-existing API tests regressed | STOP — fix regressions; do not proceed to Task 2 |
| `pyright` reports new type errors in `src/alfred/api.py` | STOP — resolve type errors first |

**STOP HERE.** Wait for human direction before continuing to Task 2.

---

## TASK 2 — Structured Logging & Request-ID Middleware

**Goal:** Introduce `src/alfred/tools/logging.py` (per tool placement rule: `src/alfred/tools/{name}.py`) providing structured JSON log emission and Starlette middleware that stamps every request with a unique request ID propagated through log records.

### Implementation

1. **Create `src/alfred/tools/logging.py`** — Implement a `configure_logging(level: str) -> None` function that installs a JSON formatter on the root logger. Level is read from the `LOG_LEVEL` environment variable (default: `INFO`). Per tool placement rule, this file lives at `src/alfred/tools/logging.py`.
2. **Request-ID middleware** — In `src/alfred/tools/logging.py`, implement a Starlette `BaseHTTPMiddleware` subclass `RequestIdMiddleware` that generates a `uuid4` request ID per request, injects it into the log context via `contextvars`, and echoes it back in the `X-Request-ID` response header.
3. **Wire into `src/alfred/api.py`** — Import `configure_logging` and `RequestIdMiddleware` from `src.alfred.tools.logging`; call `configure_logging` at app startup (lifespan); add `RequestIdMiddleware` to the app's middleware stack.
4. **Mirror tests** — Create `tests/test_tools/test_logging.py` (per tool structural rule: mirrored tests in `tests/test_tools/`). Cover: JSON output format; `LOG_LEVEL` env-var respected; `X-Request-ID` header present in responses; request ID appears in log output for that request.

### Verification

```bash
pytest tests/test_tools/test_logging.py -v
pyright src/alfred/tools/logging.py
```

**Expected:**
- All logging tests pass.
- `pyright` reports no errors for the new module.

**Suggested commit message:** `tools: task 2 — structured JSON logging and request-ID middleware`

---

## TASK 3 — Graceful Shutdown

**Goal:** Ensure that when the process receives `SIGTERM` (e.g., from `docker stop`), in-flight approval requests are either completed or safely checkpointed before the process exits, preventing data loss.

### Implementation

1. **Lifespan handler** — In `src/alfred/api.py`, implement or extend an `asynccontextmanager` lifespan that, on shutdown, calls a drain function on the approvals subsystem. The drain must wait up to a configurable timeout (env var `SHUTDOWN_DRAIN_TIMEOUT_S`, default `10`) for in-flight approvals to complete before forcing exit.
2. **Checkpoint fallback** — If the drain timeout expires, pending approvals are written to the persistence layer with status `interrupted` so the next startup can recover them.
3. **Integration test** — Create `tests/test_graceful_shutdown.py` (per test placement rule: `tests/test_*.py`). Simulate a shutdown signal while an approval is in flight; assert either completion or `interrupted` persistence record.

### Verification

```bash
pytest tests/test_graceful_shutdown.py -v
```

**Expected:**
- Graceful-shutdown test passes; no approvals silently dropped.

**Suggested commit message:** `api: task 3 — graceful shutdown with approval drain`

### CHECKPOINT-2 — Shutdown Safety

**Question:** Can the service be stopped without silently losing in-flight approval state?

**Evidence required:**
- Executor pastes the full `pytest` output for `tests/test_graceful_shutdown.py`.
- Executor describes (one paragraph) how the drain timeout and `interrupted` fallback were verified.

| Observation | Likely call |
|---|---|
| Shutdown test passes; interrupted approvals persisted correctly | PROCEED |
| Drain completes but `interrupted` record is malformed | PIVOT — fix persistence schema before continuing |
| Test hangs (drain never completes) | STOP — investigate deadlock; do not proceed |

**STOP HERE.** Wait for human direction before continuing to Task 4.

---

## TASK 4 — CLI Implementation

**Goal:** Fully implement `src/alfred/cli.py`, resolving the declared-but-unimplemented CLI entry point `alfred.cli:main` declared in `pyproject.toml [project.scripts]`.

### Implementation

1. **Create `src/alfred/cli.py`** — Implement a `main()` entry point using a CLI framework already present in the dependency set (e.g., `click` or `argparse`; executor must not add a new framework dependency without human approval).
2. **Subcommands** — Implement the following subcommands, each with `--help` and correct exit codes:
   - `alfred plan` — invoke the planner agent; supports `--dry-run` (print plan without committing).
   - `alfred evaluate` — invoke the quality judge; supports `--dry-run`.
   - `alfred serve` — start the FastAPI server via `uvicorn`; supports `--host`, `--port`, `--reload`.
   - `alfred validate` — run the factual validator against a supplied handover document path; exits non-zero on validation failure.
   - `alfred version` — print the package version from `importlib.metadata` and exit 0.
3. **Exit codes** — 0 for success, 1 for user error, 2 for internal/unexpected error; consistent across all subcommands.
4. **Tests** — Create `tests/test_cli.py` (per test placement rule). Cover: each subcommand `--help` exits 0; `alfred version` prints a version string; `alfred validate` exits non-zero on a known-bad document; `--dry-run` flag suppresses side effects.

### Verification

```bash
pip install -e .
alfred --help
alfred version
alfred validate --help
alfred serve --help
pytest tests/test_cli.py -v
pyright src/alfred/cli.py
```

**Expected:**
- `alfred --help` lists all subcommands.
- `alfred version` prints a non-empty version string and exits 0.
- All CLI tests pass; `pyright` clean.

**Suggested commit message:** `cli: task 4 — implement alfred.cli with plan/evaluate/serve/validate/version`

---

## TASK 5 — Docker Image & Compose

**Goal:** Produce a rootless, multi-stage `Dockerfile` that runs `alfred serve`, a `docker-compose.yml` for local development, and supporting files.

### Implementation

1. **`Dockerfile`** — Multi-stage build: builder stage installs dependencies into a virtualenv; runtime stage copies only the virtualenv and package source, drops root via `USER nonroot`, sets `CMD ["alfred", "serve"]`. File lives at the repository root.
2. **`.dockerignore`** — Excludes `.git`, `__pycache__`, `*.pyc`, `tests/`, `docs/`, `*.md` from the build context. File lives at the repository root.
3. **`docker-compose.yml`** — Defines a `alfred-api` service building from the local `Dockerfile`, exposes port `8000`, mounts the workspace as a read-only volume for the `docs/` directory, and reads secrets from `.env`. File lives at the repository root.
4. **`.env.example`** — Documents every environment variable consumed by Alfred: `LOG_LEVEL`, `SHUTDOWN_DRAIN_TIMEOUT_S`, `ANTHROPIC_API_KEY` (or equivalent LLM key), `ALFRED_PERSISTENCE_PATH`, and any others discovered during implementation. File lives at the repository root.

### Verification

```bash
docker build -t alfred:dev .
docker run --rm alfred:dev alfred version
docker compose up -d
curl -s http://localhost:8000/healthz
docker compose down
```

**Expected:**
- Image builds without error.
- `alfred version` runs correctly inside the container.
- `docker compose up` starts cleanly; `/healthz` returns `{"status": "ok"}`.

**Suggested commit message:** `docker: task 5 — Dockerfile, docker-compose.yml, .env.example`

### CHECKPOINT-3 — Container Smoke Test

**Question:** Does the Docker image build successfully, run `alfred serve`, and pass the health probe?

**Evidence required:**
- Executor pastes the final lines of `docker build` output (image ID).
- Executor pastes `curl http://localhost:8000/healthz` response verbatim.
- Executor pastes `alfred version` output from inside the container.

| Observation | Likely call |
|---|---|
| Build succeeds; `/healthz` returns 200; version prints correctly | PROCEED |
| Build succeeds but container runs as root | PIVOT — fix `USER` directive; do not push image |
| Build fails (dependency resolution error) | STOP — diagnose; do not proceed to Task 6 |
| `/healthz` returns 500 or connection refused inside container | STOP — diagnose port binding or startup failure |

**STOP HERE.** Wait for human direction before continuing to Task 6.

---

## TASK 6 — Release Workflow

**Goal:** Add `.github/workflows/release.yml` (per workflow placement rule: kebab-case `.yml` under `.github/workflows/`) that on a version tag push builds the Docker image, pushes it to GHCR, and publishes a wheel to PyPI.

### Implementation

1. **Create `.github/workflows/release.yml`** — Triggered on `push` to tags matching `v*.*.*`. Jobs:
   - `build-and-push`: Checks out the repo, logs in to GHCR via `docker/login-action`, builds and pushes image tagged with the version and `latest`.
   - `publish-wheel`: Builds the Python wheel (`python -m build`), uploads to PyPI via `pypa/gh-action-pypi-publish` using a trusted-publisher (OIDC) configuration.
2. **Secrets** — Workflow uses `secrets.GITHUB_TOKEN` for GHCR and OIDC for PyPI; no long-lived API keys stored in secrets for PyPI.
3. **Guard**: Workflow must not run on non-tag pushes or pull requests.

### Verification

```bash
# Lint the workflow locally (requires actionlint)
actionlint .github/workflows/release.yml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
```

**Expected:**
- `actionlint` reports no errors.
- YAML parses cleanly.
- (Functional test requires a real tag push — not executable in dry-run; human must review the workflow logic.)

**Suggested commit message:** `ci: task 6 — release workflow for GHCR image and PyPI wheel`

### CHECKPOINT-4 — Release Workflow Review

**Question:** Is the release workflow syntactically correct, scoped only to version tags, and using secrets/OIDC correctly?

**Evidence required:**
- Executor pastes `actionlint` output verbatim (must be clean).
- Executor confirms OIDC trusted-publisher is configured on PyPI (or notes that it must be configured by the repo owner before the first release).
- Executor pastes the YAML `on:` trigger block verbatim.

| Observation | Likely call |
|---|---|
| `actionlint` clean; OIDC documented; trigger scoped to version tags only | PROCEED |
| Workflow also triggers on branch pushes or PRs | PIVOT — fix trigger; do not merge |
| Long-lived PyPI token stored in repo secrets | STOP — switch to OIDC trusted publisher before merging |

**STOP HERE.** Wait for human direction before continuing to Task 7.

---

## TASK 7 — Documentation Refresh

**Goal:** Update `README.md` and relevant `docs/` files with quick-start instructions for Docker, CLI usage, and environment variable reference.

### Implementation

1. **`README.md`** — Add sections: "Quick Start (Docker)" using `docker compose up`; "Quick Start (local)" using `pip install -e . && alfred serve`; "CLI Reference" summarising all five subcommands; "Environment Variables" pointing to `.env.example`.
2. **`docs/` updates** — Update `docs/protocol/architecture.md` if any new modules (`src/alfred/tools/logging.py`, `src/alfred/cli.py`) affect the documented architecture. Per doc placement rule, documentation files live under `docs/` with `.md` extension.
3. **No new canonical handover** — Documentation refresh does not require a new handover document; changes are prose updates to existing files.

### Verification

```bash
# Check all internal links resolve (requires a markdown link checker)
find docs -name '*.md' -exec grep -l '\[' {} \;
# Manual review: README renders correctly on GitHub
```

**Expected:**
- README and architecture doc are internally consistent with the new module inventory.
- No broken internal links.

**Suggested commit message:** `docs: task 7 — README quick-starts, CLI reference, env-var docs`

---

## WHAT NOT TO DO

1. **Do not introduce `mypy`** — `pyright` is the sole type checker; adding `mypy` configuration or CI steps is a `HARD_RULE` violation.
2. **Do not create `src/alfred/api/`** — the FastAPI app must remain at `src/alfred/api.py`; splitting it into a subpackage breaks the structural rule and invalidates topology claims.
3. **Do not place the logging module anywhere other than `src/alfred/tools/logging.py`** — top-level helper scripts imported as tool modules are forbidden; per tool placement rule.
4. **Do not place new workflows anywhere other than `.github/workflows/`** — and file names must be kebab-case `.yml`/`.yaml`.
5. **Do not disable or weaken the factual validator** — the validator established in `output-hardening-2` and hardened in `output-hardening-3` is a non-negotiable invariant; any PR that weakens it must be rejected.
6. **Do not describe `src/alfred/cli.py` as "missing" or "not planned"** — it is **declared but unimplemented**; use that exact vocabulary.
7. **Do not self-approve checkpoints** — the executor must stop at each `STOP HERE` gate and wait for a human decision before proceeding.
8. **Do not fabricate git commits** — the `### Git History` section must reproduce only the commits supplied; invented hashes or messages are a `METADATA` violation.
9. **Do not add a new CLI framework dependency without human approval** — use frameworks already present in the dependency set (e.g., `click` or `argparse`).
10. **Do not push a Docker image that runs as root** — the `Dockerfile` must include a `USER nonroot` directive; a root-running container is a security regression.

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