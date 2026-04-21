# Factual Validator & Future-Task Planning Realism

---

## Purpose

**status:** Canonical grounding-analysis brief for the next session  
**date:** 2026-04-20  
**author:** Codex  
**adjacent_to:** future canonical Phase 7 handover  
**primary_goal:** Turn the recent grounding discussion into an execution-ready design brief for improving (1) factual-validator reliability and (2) future-task / planning realism in Alfred-generated handovers.

This document is not a sprint handover. It is a repo-grounded design brief intended to bootstrap the next session quickly and keep the discussion anchored to the actual code, tests, and remaining failure modes.

---

## Current Baseline

The repo has already made meaningful progress on grounding:

- `src/alfred/tools/repo_facts.py` computes live repo facts from the workspace.
- `src/alfred/schemas/agent.py` carries `repo_facts_summary`, `generation_date`, `expected_handover_id`, and `expected_previous_handover` into the planner contract.
- `src/alfred/agents/planner.py` injects those facts and metadata into the planner prompt and explicitly forbids contradicting them.
- `scripts/generate_phase7.py` now computes repo facts and injects identity/date metadata instead of asking the model to infer them.
- `src/alfred/orchestrator.py` propagates the same repo facts and metadata through the critique loop.
- `scripts/validate_alfred_planning_facts.py` exists as a separate factual gate alongside the structural handover validator.
- `tests/test_tools/test_repo_facts.py`, `tests/test_agents/test_planner.py`, `tests/test_scripts/test_validate_alfred_planning_facts.py`, and `tests/test_scripts/test_generate_phase7.py` cover the first generation of grounding fixes.

That work clearly improved the outputs. The latest `ALFRED_HANDOVER_6_DRAFT.md` stopped hallucinating the old fake runtime topology, wrong agent roster, wrong FastAPI path, and wrong metadata identity.

The remaining concerns are narrower now:

- `Factual validator reliability` is no longer poor, but it is still only moderate.
- `Future-task / planning realism` improved indirectly, but it remains patchy because the current grounding layer is much better at describing what exists today than at constraining how the repo should evolve tomorrow.

---

## Problem Statement

There are now two different quality problems, and they should not be treated as one problem:

1. **Current-state truthfulness**
   The document must not misstate what exists in the repo today.

2. **Future-task realism**
   The document must not propose future work that is inconsistent with the repo's conventions, layout, partial implementation state, or likely execution path.

The first problem is mostly deterministic and should be validated strictly.
The second problem is partly deterministic and partly heuristic, and should be evaluated with a realism rubric rather than with the same blunt rules used for present-tense factual claims.

The current system partially solves problem 1 and only lightly touches problem 2.

---

## What The Current Code Actually Does

### Factual Validation Today

`scripts/validate_alfred_planning_facts.py` currently:

- scopes itself to `## CONTEXT — READ THIS FIRST` and `## WHAT EXISTS TODAY`
- validates metadata consistency (`id`, `date`, `previous_handover`)
- checks quoted local paths for existence
- rejects current-state claims about the wrong FastAPI topology
- rejects common fake agent names such as `executor`, `reviewer`, `summariser`
- rejects nonexistent top-level `src/alfred/*/` package claims
- rejects `mypy` as a current-state tool
- rejects claims that `pyproject.toml` is absent

This is useful and important, but it is still a fairly small set of targeted heuristic checks.

### Repo Truth Inputs Today

`src/alfred/tools/repo_facts.py` currently reads:

- agent modules
- tool modules
- top-level `src/alfred/` names
- API module path and endpoint list
- coarse packaging/toolchain state
- reference documents under `docs/`

However, the human-readable summary injected into the planner prompt does not yet capture all of the nuance the next step needs. In particular, it is weak on partial-state facts and repo-growth conventions.

### Planner Constraints Today

`src/alfred/agents/planner.py` currently tells the model:

- do not contradict the repository facts block
- do not invent missing files as present-tense facts
- do not claim `mypy` is in use
- do not move the FastAPI module path
- do not infer handover identity metadata from RAG context

This is a solid current-state grounding contract.

What it does **not** yet do well:

- describe how future files should be placed in this repo
- distinguish strongly between `exists today`, `declared but not implemented`, and `to be created`
- constrain future workflow locations, schema locations, doc-path conventions, and similar growth rules
- tell the model how to judge whether a proposed task is repo-consistent rather than merely plausible in generic Python terms

### Review / Critique Today

`src/alfred/agents/quality_judge.py` is not a factual validator and not a planning-realism judge. It mainly checks checkpoint structure and coarse methodology signals. The critique loop therefore improves prose and general quality, but it does not independently enforce repo truth or future-task plausibility.

That distinction matters. The system has a critique loop, but it does not yet have a real deterministic grounding-review loop.

---

## Why Factual Validator Reliability Is Still Only Moderate

### 1. Claim Detection Is Still Heuristic

The validator mostly relies on regex matches over prose rather than on typed claim extraction. That makes it brittle:

- some true claims can be missed
- some false claims can slip through
- some valid negated mentions can be misread

### 2. Negation Handling Is Too Broad

The current `_is_negated()` heuristic looks for nearby cues such as `not`, `does not exist`, `missing`, and similar phrases within a sliding character window.

This caused a real miss: a bad path claim like `docs/handovers/ALFRED_HANDOVER_5.md` slipped because surrounding prose such as `must not break` made the match appear negated when it was not.

That is a classic sign that the validator is doing context guessing rather than typed sentence-level interpretation.

### 3. Reference-Document Validation Is Not First-Class

`read_reference_documents()` exists in `repo_facts.py`, but reference-doc claims are not yet validated as their own claim type with their own truth source and section rules.

That means document references are currently treated as generic path mentions instead of as a special category with stronger expectations.

### 4. Partial-State Facts Are Under-Represented

The repo now contains important `partial state` truths, for example:

- `pyproject.toml` declares `alfred.cli:main`
- `src/alfred/cli.py` does not yet exist

This is neither `fully implemented` nor `fully absent`.

Today the repo facts layer does not strongly model this state, and the validator does not assert it directly. That leaves room for overstatement such as `the CLI exists` or understatement such as `there is no CLI packaging at all`.

### 5. The Factual Gate Is Narrow By Design

The validator intentionally ignores future-tense sections. That was the right first move, because it prevented false positives on legitimate proposals. But it also means many planning-quality issues are currently invisible to the deterministic gate.

This should remain true for strict factual validation, but it means the repo still needs a second mechanism for future-task realism.

### 6. Test Coverage Is Good For Known Failures, Not Yet For The Whole Claim Space

The existing tests cover the original hallucination classes well, but there are still notable gaps:

- false-negative cases involving nearby negation words
- reference-document path validation
- partial-state assertions
- claims about declared entry points whose implementation files are absent
- boundary cases where the same path appears in current-state and future-state contexts

---

## Claim Taxonomy For The Next Iteration

The next session should stop treating all prose claims as one blob and instead adopt a typed claim taxonomy.

| Claim class | Example | Truth source | Allowed section scope | Validation mode | Current status |
|---|---|---|---|---|---|
| Metadata claim | `**id:** ALFRED_HANDOVER_6` | generator constants / filename / expected args | `CONTEXT` | strict | partially implemented |
| Reference-doc claim | `docs/canonical/ALFRED_HANDOVER_5.md` | live `docs/*.md` inventory | `CONTEXT`, task references | strict for present-tense references | weak |
| Current path claim | `src/alfred/api.py` exists | filesystem | `CONTEXT`, `WHAT EXISTS TODAY` | strict | implemented but heuristic |
| Current topology claim | FastAPI is a single file, agents under `src/alfred/agents/` | filesystem + API parser | `WHAT EXISTS TODAY` | strict | implemented for some cases |
| Current tooling claim | `pyright` is in use; `mypy` is not | `pyproject.toml` | `WHAT EXISTS TODAY` | strict | partially implemented |
| Partial-state claim | CLI entry declared, implementation missing | filesystem + `pyproject.toml` | `WHAT EXISTS TODAY` | strict | weak |
| Future artifact claim | add `.github/workflows/release.yml` | repo conventions + realism policy | future sections only | realism rubric | mostly absent |
| Future placement claim | add `src/alfred/schemas/health.py` | repo layout conventions | future sections only | realism rubric | mostly absent |
| Future dependency claim | add package X | `pyproject.toml` + hard rules | future sections only | realism rubric | mostly absent |
| Phase-coherence claim | this phase produces X, not Y | handover scope | future sections only | realism rubric | mostly absent |

This taxonomy is the bridge between the current heuristic validator and a more reliable spec-driven system.

---

## Recommended Factual-Validator Target State

The next step should aim for the following validator behavior:

1. **Strict on current-state claims**
   If the draft says something exists today, the validator should be able to point to the exact truth source that confirms or refutes it.

2. **Typed, not generic**
   The validator should know whether it is checking:
   - metadata
   - reference docs
   - local code paths
   - API topology
   - toolchain
   - partial-state facts

3. **Narrowly negation-aware**
   Negation should be handled with tighter, more local logic so phrases like `must not break` do not accidentally negate a nearby path claim.

4. **Section-aware**
   The same string may be legal in a future-tense task proposal and illegal in `WHAT EXISTS TODAY`. That scope distinction should be explicit and central.

5. **Explainable**
   Every failure should tell the next revision exactly:
   - what claim was rejected
   - which truth source contradicted it
   - whether the fix is to move the claim to a future section, delete it, or restate it more precisely

### Factual-Validator Remediation Tracks

| ID | Remediation | Why it matters |
|---|---|---|
| FV1 | Introduce typed claim categories instead of treating all claims as free-form regex hits | improves reliability and debuggability |
| FV2 | Add first-class reference-document checks using `read_reference_documents()` | closes the path-reference blind spot |
| FV3 | Tighten or replace `_is_negated()` with more local claim-level handling | fixes the current false-negative family |
| FV4 | Add explicit partial-state checks for declared-but-missing implementations | prevents CLI-style overstatement/understatement |
| FV5 | Expand repo facts beyond coarse strings where necessary | lets validator reason about state instead of just wording |
| FV6 | Add severity labels such as `error` vs `warning` for softer borderline cases | avoids overfailing on ambiguous prose |
| FV7 | Add regression fixtures for known misses, not just known catches | protects against repeat blind spots |
| FV8 | Feed deterministic validator findings back into the revision loop | turns validator failures into actionable planner corrections |

### Concrete Partial-State Facts The System Should Be Able To Express

These are the kinds of statements the next version should support explicitly:

- `pyproject.toml` exists and contains `[project]`
- `[project.scripts]` exists
- `alfred.cli:main` is declared as a script entry
- `src/alfred/cli.py` is currently absent
- the FastAPI app exists at `src/alfred/api.py`
- `.github/workflows/ci.yml` exists
- `.github/workflows/release.yml` does not yet exist

The planner should be able to say those things precisely, and the validator should be able to check them precisely.

---

## Why Future-Task / Planning Realism Is Still Patchy

### 1. The Planner Knows What Exists, But Not How The Repo Grows

The current prompt is good at saying:

- do not invent files that exist today
- do not rename existing modules
- do not lie about the current toolchain

It is much weaker at saying:

- if you propose a new GitHub Actions workflow, put it under `.github/workflows/`
- if you add a schema, prefer the existing `src/alfred/schemas/` package shape
- if packaging already declares a CLI entry but no module exists, describe that as `declared but missing`, not as `present` or `absent`

That is why bad future proposals like `ci/release.yml` or `src/alfred/schemas.py` were still possible even after current-state grounding improved.

### 2. There Is No Planning-Realism Gate

Today the system has:

- a structural handover validator
- a current-state factual validator

It does **not** yet have a deterministic or semi-deterministic layer that says:

- this proposed new file is in the wrong place for this repo
- this task assumes the wrong existing module shape
- this proposal is too vague to be execution-ready
- this task contradicts the repo's own hard rules or naming conventions

### 3. The Prompt Lacks A Strong Partial-State Vocabulary

A lot of planning sloppiness comes from the model being forced into overly simple buckets:

- exists
- missing

But the repo has several important in-between states:

- declared but unimplemented
- implemented but undocumented
- present but advisory only
- present in one place, absent in another

Without those categories, the model tends to flatten nuance and then propose awkward or contradictory remediation tasks.

### 4. The Critique Loop Does Not Evaluate Realism

The `quality_judge` can improve general quality, but it does not score:

- placement consistency
- repo-convention consistency
- dependency realism
- task granularity
- validation completeness

So the critique loop may polish language without correcting deeper planning-quality misses.

### 5. Existing Tests Focus On Grounding Inputs, Not Proposal Quality

`tests/test_agents/test_planner.py` now proves that the prompt includes repo facts and identity metadata.
It does not yet prove that the prompt teaches the model how to produce repo-consistent future tasks.

That is the next frontier.

---

## Planning-Realism Rubric

The next session should define and use an explicit planning-realism rubric. The point is not to guarantee perfection; the point is to make future proposals legible, comparable, and reviewable.

### Rubric Dimensions

| Dimension | Score 0 | Score 1 | Score 2 |
|---|---|---|---|
| Placement consistency | proposed file path contradicts repo layout | plausible but not clearly repo-native | clearly matches existing layout/conventions |
| Partial-state accuracy | overstates or understates current implementation | mentions some nuance but still fuzzy | clearly distinguishes existing / declared / missing |
| Dependency realism | assumes tools/frameworks not in evidence | plausible but ungrounded dependency story | aligns with current stack and hard rules |
| Task granularity | vague or non-executable | understandable but underspecified | executable with clear files, tests, and exit criteria |
| Validation alignment | no obvious proof path | some test/validation hints | explicit validator/test/evidence path |
| Phase coherence | mixed phase goals or scope confusion | mostly coherent with minor drift | tightly aligned with the stated phase goal |

### Practical Reading Of The Rubric

- A task scoring `0` on any of the first three dimensions is not promotion-safe.
- A task averaging `1` is plausible but still needs human rewrite.
- A task consistently scoring `2` is close to execution-ready.

This rubric should be applied to future sections only. It is not a replacement for strict factual validation of present-tense sections.

---

## Recommended Planning-Realism Target State

The next step should aim for the following planner behavior:

1. **Use repo-growth conventions**
   Future artifacts should be proposed in locations that match the current repo shape.

2. **Use a three-state vocabulary**
   The planner should distinguish:
   - `exists today`
   - `declared / partially present`
   - `to be created in this phase`

3. **Propose execution-ready tasks**
   Tasks should mention likely files, tests, validators, and proof of completion.

4. **Respect hard rules**
   Future proposals should not quietly contradict repo decisions such as `pyright not mypy`, functions-only design, or current module ownership.

5. **Be reviewed separately from current-state truth**
   Realism should be scored or linted, not shoved into the same failure bucket as factual hallucination.

### Planning-Realism Remediation Tracks

| ID | Remediation | Why it matters |
|---|---|---|
| PR1 | Extend repo facts with repo-growth conventions, not just current inventory | teaches the planner where new things belong |
| PR2 | Add a partial-state vocabulary to prompt instructions | reduces overstatement and awkward task framing |
| PR3 | Add explicit future-artifact placement rules | prevents `ci/release.yml`-style drift |
| PR4 | Add a planning-realism linter or validator mode for future sections | gives deterministic feedback on proposal quality |
| PR5 | Add planner tests for future-placement instructions and partial-state language | ensures the prompt contract is real |
| PR6 | Feed realism findings back into the critique loop | lets the planner revise against concrete misses |
| PR7 | Define repo-specific convention facts for workflows, schemas, docs, and CLI state | removes guesswork from future proposals |
| PR8 | Separate `factual failure` from `planning weakness` in reporting | improves human review and automated retries |

---

## Strong Recommendation: Split The Two Gates

Do **not** try to solve both remaining problems by making `scripts/validate_alfred_planning_facts.py` ever more heuristic and overloaded.

The cleaner design is:

- keep the factual gate strict, narrow, and high-confidence
- add either:
  - a separate planning-realism validator, or
  - a second mode within the same script with clearly different semantics

The reasoning:

- current-state factual claims should fail hard and deterministically
- future-task realism needs a mix of deterministic checks and structured heuristics
- combining them without a clear split will make the validator harder to trust

If the implementation stays in one file, the conceptual split should still be explicit:

- `validate_current_state_facts(...)`
- `validate_future_task_realism(...)`

Even if a single CLI wrapper calls both.

---

## Recommended Sources Of Truth For The Next Iteration

| Concern | Best source of truth |
|---|---|
| handover id / previous / date | generator constants and explicit validator args |
| local code paths | filesystem |
| agent / tool inventory | directory scans |
| API surface | parsed `src/alfred/api.py` |
| packaging/toolchain | `pyproject.toml` plus file existence checks |
| reference docs | live `docs/*.md` inventory |
| workflow locations | filesystem + repo convention policy |
| schema placement | filesystem + existing `src/alfred/schemas/` package structure |
| CLI state | `pyproject.toml` plus `src/alfred/cli.py` existence check |
| future artifact placement | repo convention policy, not just generic Python intuition |

This should become an explicit matrix in the implementation and in the tests.

---

## Suggested Repo-Facts Expansion

The next session should consider expanding the repo-facts layer so it can express facts like:

- canonical docs present today
- canonical docs absent today
- workflow files present today
- expected workflow root is `.github/workflows/`
- schema package root is `src/alfred/schemas/`
- CLI script entry declared today
- CLI implementation module absent today
- current release workflow absent today

The key idea is that the repo-facts layer should not only answer `what strings exist in the repo?`
It should also answer `what state is this feature in?`

That is what unlocks better future-task realism.

---

## Suggested Test Expansion

Tomorrow's implementation work should add tests for at least these cases:

### Factual Validator

- bad reference-doc path in a current-state section is rejected
- nearby `must not` language does not falsely negate a path claim
- partial-state CLI claim is validated correctly
- `.github/workflows/release.yml` can be correctly described as absent today
- a valid negated claim remains allowed when the negation is truly local and explicit

### Planning Realism

- future workflow proposals prefer `.github/workflows/`
- future schema additions prefer `src/alfred/schemas/`
- future tasks can refer to missing files without being treated as present-tense hallucinations
- prompt instructions explicitly distinguish `exists today` vs `declared but missing` vs `to be created`
- realism failures are surfaced separately from factual failures

### Critique / Revision Integration

- deterministic factual failures are converted into revision feedback
- deterministic realism failures are converted into revision feedback
- retries preserve repo facts and identity metadata

---

## Concrete Work Package For The Next Session

If we implement this tomorrow, the likely work package is:

1. **Define the claim taxonomy in code-facing terms**
   Decide exactly which claim classes exist and which ones are strict vs heuristic.

2. **Expand repo facts for partial-state and convention facts**
   Add the specific repo truths needed for CLI state, docs inventory, workflow placement, and schema placement.

3. **Refactor factual validation into typed checks**
   Make reference-doc validation and partial-state validation first-class.

4. **Design the planning-realism layer**
   Either a new validator or a second mode with a clear rubric and output format.

5. **Integrate deterministic feedback into the critique loop**
   Revision should react to machine-found issues, not just to generic quality feedback.

6. **Add regression fixtures**
   Include both false-negative and false-positive protections.

7. **Regenerate and assess a new draft**
   The new draft should be reviewed against both current-state truth and future-task realism.

---

## Non-Goals

The next session should **not**:

- redesign Alfred's whole multi-agent architecture
- replace the structural validator
- try to build a full natural-language theorem prover
- treat generic prose elegance as the same problem as grounding
- "fix" hallucinations by manually editing every future draft

The goal is a stronger grounded generation pipeline, not a more elaborate manual review ritual.

---

## Success Criteria

The next iteration should count as successful if all of the following are true:

- current-state factual errors are rejected more reliably than today
- the reference-doc path blind spot is closed
- partial-state facts can be expressed and checked cleanly
- future task proposals are more repo-consistent
- future artifact placement errors like `ci/release.yml` are caught or strongly discouraged
- deterministic findings feed back into planner revision
- tests cover the new failure classes
- the next generated handover needs materially less human cleanup

---

## Ready-To-Paste Prompt For Tomorrow

Use this to restart the work in a new session:

```text
Please read `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` first, then inspect the current implementations of:

- `scripts/validate_alfred_planning_facts.py`
- `src/alfred/tools/repo_facts.py`
- `src/alfred/agents/planner.py`
- `src/alfred/orchestrator.py`
- `src/alfred/agents/quality_judge.py`
- `tests/test_scripts/test_validate_alfred_planning_facts.py`
- `tests/test_agents/test_planner.py`

I want you to implement the deep-dive recommendations carefully, with the following priorities:

1. Improve factual-validator reliability without weakening the current strict gate for present-tense claims.
2. Add a separate, explicit mechanism for future-task / planning realism instead of overloading the existing factual validator blindly.
3. Model partial-state facts clearly, especially cases like declared entry points whose implementation modules are still missing.
4. Ensure deterministic validator findings can feed back into the planner revision loop.
5. Add regression tests for the known blind spots and newly supported cases.

Important constraints:

- Preserve the existing structural validator.
- Do not reintroduce `mypy`.
- Do not hand-edit generated handovers as the main fix.
- Keep current-state factual validation strict and high-confidence.
- Keep future-task realism checks clearly distinguishable from factual failures.

After implementing, regenerate the relevant planning draft and assess whether both current-state grounding and future-task realism have improved materially.
```

---

## Closing View

The first grounding wave solved the biggest embarrassment class: obvious hallucinations about what exists today. The next wave should make the system more trustworthy in a subtler way: by improving the confidence of the factual gate and teaching the planner how this repo actually evolves.

That is the difference between `grounded enough to stop making things up` and `grounded enough to plan well`.
