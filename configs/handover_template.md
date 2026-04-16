<!--
  Handover document template.

  Canonical starting point for a new handover. Copy this file, fill in every
  <fill in> placeholder, then validate via `alfred validate <path>`.

  The five methodology properties are non-negotiable. Every section below
  exists to serve at least one of them:

    1. Document as protocol           — this file IS the control surface
    2. Checkpoint-gated execution     — checkpoints are first-class, not advisory
    3. Reasoning/execution isolation  — agents stay within their schema contracts
    4. Inline post-mortem → forward plan — failures feed the next iteration here
    5. Statelessness by design        — a fresh reader must cold-start from this file alone

  HTML comments (like this one) are ignored by from_markdown().
-->

# <AUTHOR>'s Handover Document #<N> — <Title>

## CONTEXT — READ THIS FIRST

<!-- Metadata block. All fields except Author are optional but recommended. -->
**Document Date:** <YYYY-MM-DD>
**Previous Handover:** <PREVIOUS_HANDOVER_ID or omit this line>
**Supersedes:** <comma-separated ids, or omit this line>
**Baseline State:** <one-sentence summary of what is true today>
**Reference Documents:**
- `<path/to/prior/handover.md>` — <why it matters>
- `<path/to/architecture.md>` — <why it matters>
**Author:** <Name>

---

## WHAT THIS TASK DOES

<!-- The narrative. A reader who sees only this section should understand the
     "why" of the work. Keep it to a few paragraphs; detail belongs in tasks. -->
<fill in>

**What changes:**
1. <fill in>
2. <fill in>

**What does NOT change:** `<file or area>`, `<file or area>`

---

## IMPORTANT

<!-- Anything the reader must know that is not obvious from the tasks.
     Constraints, deadlines, environmental assumptions. -->
<fill in>

---

## HARD RULES

<!-- Non-negotiable constraints. Numbered for reference from checkpoints. -->
1. <fill in>
2. <fill in>

---

## WHAT THIS HANDOVER PRODUCES

<!-- Bullet list of concrete artifacts this handover must produce. -->
- <fill in>
- <fill in>

---

## TASK OVERVIEW

<!-- One row per task. Use the four-column form when tasks have checkpoints. -->
| # | Task | Deliverable | Checkpoint decides |
|---|---|---|---|
| 1 | <fill in> | <fill in> | <CHECKPOINT-1 id or blank> |
| 2 | <fill in> | <fill in> |  |

---

## TASK 1 — <Title>

**Goal:** <one sentence>

<!-- Numbered steps. Each bolded step becomes a parsed step. -->
1. **<Step name>** — <fill in>
2. **<Step name>** — <fill in>

### Verification

```bash
<fill in>
```

**Expected:** <fill in>

**Commit message:** `phaseN: task 1 — <description>`

### CHECKPOINT-1

**Question:** <what must be true before continuing?>

**Evidence required:** <what the executor must paste verbatim>

| Observation | Likely call |
|---|---|
| <condition A> | PROCEED |
| <condition B> | PIVOT |
| <condition C> | STOP |
| <condition D> | ESCALATE |

**STOP HERE.** Wait for direction before continuing.

---

## TASK 2 — <Title>

**Goal:** <one sentence>

1. **<Step name>** — <fill in>

### Verification

```bash
<fill in>
```

**Commit message:** `phaseN: task 2 — <description>`

---

## WHAT NOT TO DO

<!-- Anti-patterns specific to this handover. -->
1. <fill in>
2. <fill in>

---

## POST-MORTEM

<!-- Populated after execution. Leave as TBD when drafting. -->
TBD

**Root causes:**
- <fill in after execution>

**What worked:**
- <fill in after execution>

**What failed:**
- <fill in after execution>

**Forward plan:**
<fill in after execution>

**next_handover_id:** <NEXT_HANDOVER_ID>
