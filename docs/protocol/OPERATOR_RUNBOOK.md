# Alfred Operator Runbook

This runbook is the cold-start survival guide for operating Alfred from a fresh checkout. It covers the supported local and container startup paths, the runtime environment contract, probe checks, shutdown behavior, observability hooks, and the quickest remediations for the failure modes most likely to block an operator.

## Prerequisites

- Python 3.10 or newer. The checked-in repo contract is `requires-python = ">=3.10"`, and the shipped Docker image also uses Python 3.10.
- Docker and Docker Compose are optional; use them for the containerized path only.
- A writable local checkout of this repository.
- Provider credentials only when you intend to run live LLM-backed flows:
  - `ANTHROPIC_API_KEY` for Anthropic-backed model calls
  - `OPENAI_API_KEY` for OpenAI-backed model calls
- `GITHUB_TOKEN` only when `configs/default.yaml` is configured to read from a live GitHub Projects V2 board.

Relevant local files:

- [configs/default.yaml](/home/donal/code/projectalfred/configs/default.yaml)
- [.env.example](/home/donal/code/projectalfred/.env.example)
- [docker-compose.yml](/home/donal/code/projectalfred/docker-compose.yml)
- [Dockerfile](/home/donal/code/projectalfred/Dockerfile)

## Quick Start

### Bare Metal via `uvicorn`

Create an environment, install the package, then start the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alfred serve --host 127.0.0.1 --port 8000 --reload
```

Equivalent direct `uvicorn` invocation:

```bash
uvicorn alfred.api:app --host 127.0.0.1 --port 8000 --reload
```

### Docker Compose

Create a runtime env file, then boot the checked-in Compose service:

```bash
cp .env.example .env
docker compose up --build
```

The Compose service starts Alfred with:

```bash
alfred serve --host 0.0.0.0 --port 8000
```

The current compose file mounts `${ALFRED_WORKSPACE_PATH:-.}` read-only at `/workspace` and publishes container port `8000` on host port `8000`.

## Environment Variable Reference

The supported runtime variables are the ones documented in [.env.example](/home/donal/code/projectalfred/.env.example).

| Variable | Type | Required | Default | Used for |
|---|---|---|---|---|
| `LOG_LEVEL` | string | No | `INFO` | Root JSON log level for Alfred and routed uvicorn logs |
| `SHUTDOWN_DRAIN_TIMEOUT_S` | float seconds | No | `10` | How long shutdown waits before expiring still-pending approvals |
| `ANTHROPIC_API_KEY` | string | Conditional | none | Required when the resolved provider/model path uses Anthropic |
| `OPENAI_API_KEY` | string | Conditional | none | Required when the resolved provider/model path uses OpenAI |
| `GITHUB_TOKEN` | string | Conditional | none | Required only for board-backed flows when GitHub org/project settings are configured |
| `ALFRED_WORKSPACE_PATH` | filesystem path | No | `.` | Host checkout mounted into `/workspace` by Docker Compose |

Conditional notes:

- Alfred reads provider secrets at request time, not from config files.
- `configs/default.yaml` defaults the GitHub token env var name to `GITHUB_TOKEN`.
- If `database.path` remains at its default, Alfred uses `data/alfred.db`.
- If `rag.index_path` remains at its default, Alfred uses `data/rag_index`.

## Health & Readiness Verification

Once Alfred is running, verify the service with the built-in probes.

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

Expected healthy responses:

```json
{"status":"ok"}
```

```json
{"status":"ready"}
```

Probe semantics:

- `GET /healthz` is a liveness probe only. It returns `200` with `{"status":"ok"}` if the process is up.
- `GET /readyz` is a readiness probe. It returns `200` with `{"status":"ready"}` when critical dependencies are reachable.
- When readiness fails, Alfred returns `503` with a payload shaped like:

```json
{"status":"unavailable","reason":"Persistence layer unavailable: ..."}
```

## CLI Reference

Top-level help skeleton:

```text
usage: alfred [-h] {plan,evaluate,serve,validate,version} ...
```

Subcommands and exit behavior:

| Command | Purpose | Exit behavior |
|---|---|---|
| `alfred plan` | Generate a draft handover or print a dry-run plan | `0` on successful dry-run or generation; argparse usage errors exit `2`; runtime/provider failures propagate as non-zero process failures |
| `alfred evaluate` | Evaluate checkpoint evidence against a checkpoint definition | `0` on successful dry-run or evaluation; handled file/JSON/schema errors return `1`; missing required flags exit `2` |
| `alfred serve` | Start the FastAPI app through uvicorn | Long-running; returns `0` only if uvicorn exits cleanly; bind/startup failures terminate non-zero |
| `alfred validate` | Run the planning factual validator against a handover markdown file | `0` when validation passes; `1` on factual failure or handled CLI loader errors; `2` on validator usage or file/IO errors |
| `alfred version` | Print installed package metadata version | `0` on success; `1` if package metadata is unavailable |

Useful operator commands:

```bash
alfred --help
alfred plan --dry-run
alfred evaluate --dry-run
alfred validate docs/canonical/ALFRED_HANDOVER_7.md
alfred version
```

## Graceful Shutdown

Shutdown is tied to the FastAPI lifespan hook in [src/alfred/api.py](/home/donal/code/projectalfred/src/alfred/api.py).

How to trigger it:

- `Ctrl+C` in a foreground `alfred serve` session
- `docker compose down`
- A normal process `SIGTERM`

What Alfred does during shutdown:

1. Reads `SHUTDOWN_DRAIN_TIMEOUT_S` from the environment. Default: `10`.
2. Waits up to that many seconds for open approvals to stop being pending.
3. Marks any still-pending approvals as `expired`.
4. Emits a warning log for each approval expired during shutdown.
5. Emits a final shutdown-complete info log including `expired_count`.

Operational implication:

- Alfred drains pending approval state, not arbitrary in-flight HTTP work.
- If you need approvals to survive a restart as pending, resolve them before stopping the service or set a longer drain timeout and wait for operators to act.

## Observability

Alfred emits structured JSON logs through [src/alfred/tools/logging.py](/home/donal/code/projectalfred/src/alfred/tools/logging.py).

Default log record fields:

- `timestamp`
- `level`
- `logger`
- `message`
- `request_id`

Fields added when available:

- `method`
- `path`
- `status_code`
- `approval_id`
- `handover_id`
- `action_type`
- `expired_count`

Request correlation:

- Alfred accepts an inbound `X-Request-ID` header.
- If the caller does not send one, Alfred generates a UUID.
- Alfred echoes the active request ID back in the response header as `X-Request-ID`.

Log level control:

- Set `LOG_LEVEL=DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- Invalid values fall back to `INFO`.

Example request log:

```json
{
  "level": "INFO",
  "logger": "alfred.request",
  "message": "request completed",
  "method": "GET",
  "path": "/healthz",
  "request_id": "test-123",
  "status_code": 200,
  "timestamp": "2026-04-22T12:00:00+00:00"
}
```

## Common Failure Modes

| Symptom | Likely cause | Remediation |
|---|---|---|
| `GET /readyz` returns `503` with `Persistence layer unavailable: ...` | Alfred cannot open or initialize the SQLite database at `database.path` | Check the configured DB path, ensure its parent directory is writable, then restart and re-run `/readyz` |
| Planning or evaluation fails with `ANTHROPIC_API_KEY is not set in the environment` or `OPENAI_API_KEY is not set in the environment` | Live LLM-backed route selected, but the provider credential is missing | Export the required key, restart the shell or container, and retry |
| `docker compose up` or `alfred serve` fails because port `8000` is already in use | Another service is bound to the default port | Stop the conflicting process or run Alfred on a different host port |
| `alfred version` returns `Installed package metadata for 'alfred' was not found.` | Alfred was not installed into the current environment | Reinstall with `pip install -e '.[dev]'` from the repo root |
| The container starts but cannot see the expected repo content under `/workspace` | `ALFRED_WORKSPACE_PATH` points at the wrong host checkout | Set `ALFRED_WORKSPACE_PATH` to the correct repository path and recreate the Compose service |

## Rolling Restart Procedure

The checked-in [docker-compose.yml](/home/donal/code/projectalfred/docker-compose.yml) runs a single Alfred container on a fixed host port, so plain `docker compose restart alfred` is not truly zero-downtime. To avoid lying about that limitation, use the following handoff procedure when you need the closest available zero-downtime behavior under Compose.

Assumption for this procedure:

- You can front Alfred with a lightweight reverse proxy or temporarily switch traffic between two Alfred instances yourself.

Procedure:

1. Leave the current Alfred instance serving traffic on host port `8000`.
2. Start a second Alfred instance from the same image on a temporary host port, for example `8001`, with the same `.env` values and workspace mount.
3. Probe the replacement instance until both `GET /healthz` and `GET /readyz` succeed.
4. Send a test request with an explicit `X-Request-ID` and confirm the replacement instance responds and logs normally.
5. Move traffic from the old instance to the replacement instance.
6. Stop the old instance and confirm shutdown logs show either `expired_count: 0` or the expected approval expiry count.
7. If you need to return to the standard single-instance layout, stop the temporary instance and bring Alfred back on host port `8000` during a quiet window.

If you do not have a fronting proxy or traffic-switching layer, treat Compose restarts as planned maintenance with a brief interruption window.
