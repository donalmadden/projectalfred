<!--
  Alfred canonical handover scaffold.

  This file is the house-style contract for Alfred canonical handovers. The
  planner prompt injects its contents and requires every `##` and `###`
  heading below to appear verbatim in generated drafts. The promotion
  validator (`scripts/validate_alfred_handover.py`) fails closed if a
  canonical draft is missing any required section.

  Scope: Alfred canonical promotion only. Legacy BOB documents continue to
  parse via `HandoverDocument.from_markdown()` without this strictness;
  the generic reference template at `configs/handover_template.md` covers
  the BOB-style path. Do not conflate the two.

  Placeholders:
    <angle-bracket placeholders> are substituted by the planner.
    Headings are NOT placeholders — leave them exactly as written.
-->

# Alfred's Handover Document #<N> — <Title>

---

## CONTEXT — READ THIS FIRST

**schema_version:** 1.0
**id:** <ALFRED_HANDOVER_N>
**date:** <YYYY-MM-DD>
**author:** <name>
**previous_handover:** <previous id or omit this line>
**baseline_state:** <one-sentence summary of what is true today>

**Reference Documents:**
- `<path/to/prior/handover.md>` — <why it matters>

<narrative paragraph establishing why this handover exists>

---

## WHAT EXISTS TODAY

### Git History

```
<commit-hash>  <commit-message>
<commit-hash>  <commit-message>
```

<!-- Git history MUST come from the repository. Do not fabricate commits. -->

### <Relevant current-state subsection>

<current-state recap: pipelines, contracts, invariants>

### Key Design Decisions Inherited (Do Not Revisit)

1. <inherited decision>

---

## HARD RULES

1. <non-negotiable rule>

---

## WHAT THIS PHASE PRODUCES

- <concrete deliverable>

Out of scope:
- <explicit non-goal>

---

## TASK OVERVIEW

| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | <title> | <deliverable> | <CHECKPOINT-N or blank> |

---

## TASK 1 — <Title>

**Goal:** <one sentence>

### Implementation

1. **<Step name>** — <fill in>

### Verification

```bash
<commands>
```

**Expected:**
- <outcome>

**Suggested commit message:** `<area>: task 1 — <description>`

### CHECKPOINT-1 — <Name>

**Question:** <what must be true before continuing?>

**Evidence required:**
- <what the executor must paste verbatim>

| Observation | Likely call |
|---|---|
| <condition A> | PROCEED |
| <condition B> | PIVOT |
| <condition C> | STOP |

**STOP HERE.** Wait for direction before continuing.

---

## WHAT NOT TO DO

1. <anti-pattern specific to this handover>

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

**next_handover_id:** <NEXT_HANDOVER_ID>
