# Coverage Baseline — Phase 6 Open

**Measured:** 2026-04-20  
**Commit:** `b53f2f4` (phase6: task 2 — eval harness)  
**Command:** `pytest --cov=alfred --cov-report=json --cov-report=term-missing`  
**Total statements:** 1726 | **Missed:** 330 | **Global:** 80.9%

---

## Per-Module Coverage

| Module | Stmts | Miss | Cover | Gate |
|---|---|---|---|---|
| `src/alfred/__init__.py` | 0 | 0 | 100% | — |
| `src/alfred/agents/__init__.py` | 0 | 0 | 100% | — |
| `src/alfred/agents/compiler.py` | 14 | 0 | 100% | — |
| `src/alfred/agents/planner.py` | 62 | 6 | 90% | ≥ 80% ✓ |
| `src/alfred/agents/quality_judge.py` | 75 | 2 | 97% | — |
| `src/alfred/agents/retro_analyst.py` | 47 | 3 | 94% | — |
| `src/alfred/agents/story_generator.py` | 41 | 0 | 100% | — |
| `src/alfred/api.py` | 237 | 48 | 80% | — |
| `src/alfred/orchestrator.py` | 168 | 35 | 79% | ≥ 79% ✓ |
| `src/alfred/schemas/__init__.py` | 0 | 0 | 100% | — |
| `src/alfred/schemas/agent.py` | 134 | 0 | 100% | — |
| `src/alfred/schemas/checkpoint.py` | 35 | 7 | 80% | — |
| `src/alfred/schemas/config.py` | 68 | 5 | 93% | — |
| `src/alfred/schemas/handover.py` | 489 | 178 | 64% | — |
| `src/alfred/tools/__init__.py` | 0 | 0 | 100% | — |
| `src/alfred/tools/git_log.py` | 12 | 1 | 92% | — |
| `src/alfred/tools/github_api.py` | 99 | 7 | 93% | — |
| `src/alfred/tools/llm.py` | 84 | 33 | 61% | — |
| `src/alfred/tools/persistence.py` | 75 | 1 | 99% | — |
| `src/alfred/tools/rag.py` | 86 | 4 | 95% | — |
| **TOTAL** | **1726** | **330** | **80.9%** | **≥ 80% ✓** |

Gates enforced by `scripts/check_coverage.py` with `scripts/coverage_thresholds.json`.  
Global gate enforced by `pytest --cov-fail-under=80`.

---

## Coverage Gaps (below 80%)

### `src/alfred/tools/llm.py` — 61%

**Uncovered:** Lines 46–83, 92–121 (`_complete_anthropic`, `_complete_openai`).

These are the live provider adapters. Tests mock the LLM at the `_PROVIDERS` dispatch table (see `test_orchestrator.py`) so the real API adapter bodies are never executed. No API key is available in CI; covering these would require either a live key or a deeper mock of the `anthropic`/`openai` SDK objects. This gap is intentional and acceptable — the dispatch contract is covered, the adapter implementation is not.

### `src/alfred/schemas/handover.py` — 64%

**Uncovered:** Lines 199–346, 455–824 — the `from_markdown()` parser and markdown render helpers.

These parsing routines are exercised by `scripts/validate_alfred_handover.py` and the handover compiler, but integration paths that drive the full parse→render→validate cycle are not yet covered by unit tests. Phase 7 should add a dedicated `test_handover_parsing.py`.

### `src/alfred/orchestrator.py` — 79%

**Uncovered:** Lines 71–82, 93–108, 116–125, 145–149, 155, 162, 166–167, 263–274.

The missing lines are `_get_board_state()`, `_get_velocity_history()`, and `_retrieve_rag()` — functions that make live external calls (GitHub Projects API, SQLite, ChromaDB). Tests disable these paths by setting `config.github.org = ""`, `config.database.path = ""`, and `config.rag.index_path = ""`. The orchestrator per-module gate is set to 79% (current level) rather than 80% to reflect this structural gap. Raising it to 80%+ requires either integration test infrastructure or finer-grained mocking of the external calls.

---

## Exclusion Policy

Lines are left uncovered (not marked with `# pragma: no cover`) only in the following cases:

1. **Live API adapters** — `_complete_anthropic`, `_complete_openai` in `llm.py`. Require secrets unavailable in CI. The dispatch table and retry logic above them are covered.

2. **Live external I/O** — `_get_board_state`, `_get_velocity_history`, `_retrieve_rag` in `orchestrator.py`. Require real GitHub token, SQLite file, or ChromaDB index. Tests short-circuit these by zeroing the relevant config fields.

3. **Parse/render helpers in `handover.py`** — Complex markdown-to-model parsing. Not yet driven by a dedicated test; coverage to be improved in Phase 7.

No `if TYPE_CHECKING:` blocks exist in the codebase at this phase. If added in future, they are legitimately excluded (unreachable at runtime).

---

## Threshold Configuration

Thresholds are stored in `scripts/coverage_thresholds.json` (committed). Any change to thresholds requires a PR with updated documentation in this file.

| Scope | Threshold | Rationale |
|---|---|---|
| Global | 80% | User-approved Phase 6 floor |
| `src/alfred/orchestrator.py` | 79% | Current coverage; external-I/O gap acknowledged |
| `src/alfred/agents/planner.py` | 80% | Well above threshold at 90%; guards against regression |
