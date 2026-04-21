# CODEX Handover — Grounding Refinement: Typed Taxonomy & Generative Constraints

**id:** CODEX_GROUNDING_REFINEMENT_001  
**date:** 2026-04-21  
**author:** Claude  
**audience:** Codex (executor); Donal (reviewer/approver)  
**adjacent_to:** `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md`, critical evaluation summary  
**phase:** 6 (infrastructure hardening)  
**scope:** Make grounding system shift from descriptive rejection to generative constraint.  

---

## CONTEXT — READ THIS FIRST

### Problem Statement

The current grounding system is **architecturally sound but strategically incomplete**:

- ✅ Correctly **rejects** bad outputs (hallucinations, wrong placement, missing references)
- ❌ Does not strongly **teach** the planner how to generate good outputs
- ❌ Typed claim taxonomy exists in validator code but is invisible to the LLM
- ❌ Placement rules communicated as rejection feedback, not as upfront constraints
- ❌ Partial-state vocabulary limited to CLI; other states unnamed

**Root cause**: Grounding is a **gatekeeper** (filter bad), not a **teacher** (guide good).

### Evidence

1. **Typed taxonomy invisible to LLM** — `ClaimCategory` enum exists in `scripts/validate_alfred_planning_facts.py` but planner receives only rendered bullet text
2. **Placement rules are reactive** — planner learns `.github/workflows/` is correct after being penalized for proposing `.github/ci/`
3. **Partial-state scope minimal** — only CLI tracked; no partial-state facts for workflows, schemas, docs
4. **Deterministic findings not structured** — planner receives "CI YAML must go under `.github/workflows/`" as rejection text, not as a typed `PlacementRule`
5. **Reference-doc validation shallow** — only path existence checked, not structural or semantic properties

### Success Criteria (HARD GATES)

Implementation counts as successful if ALL of the following are true:

1. ✅ Typed claim taxonomy is explicitly exported to planner prompt (not hidden in validator)
2. ✅ Planner receives explicit repo-growth conventions (`RepoGrowthFacts` schema)
3. ✅ Partial-state coverage expanded to 4-5 states (CLI, workflows, schemas, docs, entry points)
4. ✅ Deterministic findings are typed schemas (`PlacementRule`, `HardRule`, `PartialStateFact`)
5. ✅ No regression in current-state factual validation (all prior hallucination classes still caught)
6. ✅ Generated handover demonstrates improved placement realism (e.g., `src/alfred/schemas/health.py` cited correctly)
7. ✅ All new functionality covered by regression and edge-case tests

---

## WHAT EXISTS TODAY

### Architectural Foundations (Pre-Implemented, Solid)

| Component | Location | Status | Constraints |
|---|---|---|---|
| Typed `ClaimCategory` enum | `scripts/validate_alfred_planning_facts.py:52` | ✓ Exists (10 types) | Not exposed to LLM |
| Factual validator | `scripts/validate_alfred_planning_facts.py` | ✓ Functional | Rejects claims; doesn't guide generation |
| Future-task realism validator | `scripts/validate_alfred_planning_facts.py:829` | ✓ Functional | Placement/hard-rule/granularity checks exist |
| Repo facts layer | `src/alfred/tools/repo_facts.py` | ✓ Functional | Partial-state coverage minimal (CLI only) |
| Planner grounding prompt | `src/alfred/agents/planner.py:L138–200` | ✓ Receives repo facts | Receives text bullets, not typed claims |
| Deterministic findings integration | `src/alfred/orchestrator.py:393–450` | ✓ Integrated | Findings passed to planner; not structured |
| Negation handling | `scripts/validate_alfred_planning_facts.py:221` | ✓ Improved | Sentence-level; regex-based; 90% reliable |
| Reference-doc validation | `scripts/validate_alfred_planning_facts.py:273` | ⚠️ Basic | Path existence only; no semantic validation |

### Test Coverage (Pre-Implemented)

- **Current-state factual tests**: `tests/test_scripts/test_validate_alfred_planning_facts.py` (40+ cases)
- **Future-task realism tests**: same file (40+ cases)
- **Planner grounding tests**: `tests/test_agents/test_planner.py` (coverage of repo facts injection)
- **Gaps**: No reference-doc semantic tests; no edge-case negation; no typed-constraint adoption tests

### Known Limitations

1. **Negation heuristic brittleness** — regex word-window approach fails on complex prose with embedded clauses
2. **Reference docs under-modeled** — structural validation and cross-link discovery absent
3. **Partial-state scope tiny** — only CLI; workflows, schemas, docs, entry points not tracked
4. **Findings are text, not schemas** — placement rules communicated as human-readable rejection, not as machine-parseable rule
5. **Repo-growth conventions informal** — placement expectations exist in code but not as explicit schema

---

## TASKS (HARD GATES: All must complete for promotion)

### Task 1: Define & Export Typed Claim Taxonomy to Planner (Gate: Planner receives structured taxonomy)

**Goal**: Make claim categories (REFERENCE_DOC, CURRENT_PATH, PLACEMENT, etc.) explicit constraints in planner prompt, not hidden in validator code.

**Work**:

1. **Create `src/alfred/schemas/claim_types.py`**
   ```python
   # New file; define:
   # - enum ClaimCategory (move from validator, expand if needed)
   # - dataclass TypedClaim(category, claim_text, context, section, examples)
   # - function format_claim_taxonomy_for_prompt() -> str
   # - function format_placement_rules_for_prompt() -> str
   ```

2. **Populate placement rules** (from current code patterns + infer)
   ```python
   PLACEMENT_RULES = {
       "workflow_files": {
           "canonical_root": ".github/workflows/",
           "file_pattern": "*.yml or *.yaml",
           "naming": "kebab-case (e.g., ci.yml, release.yml)",
           "examples": [".github/workflows/ci.yml", ".github/workflows/release.yml"],
       },
       "schema_files": {
           "canonical_package": "src/alfred/schemas/",
           "structure": "package (not single .py file)",
           "file_pattern": "{name}.py",
           "examples": ["src/alfred/schemas/health.py", "src/alfred/schemas/planner_input.py"],
       },
       "doc_files": {
           "canonical_root": "docs/",
           "file_pattern": "ALFRED_HANDOVER_*.md or other protocol docs",
           "naming": "UPPERCASE_WITH_UNDERSCORES.md",
           "examples": ["docs/canonical/ALFRED_HANDOVER_5.md", "docs/protocol/architecture.md"],
       },
       # ... expand based on repo structure
   }
   ```

3. **Update `src/alfred/agents/planner.py`**
   - Inject `TypedClaim` taxonomy into prompt under new section `## CLAIM TAXONOMY & PLACEMENT RULES`
   - Include `format_claim_taxonomy_for_prompt()` output
   - Include `format_placement_rules_for_prompt()` output
   - Add instruction: "When proposing new files, cite the placement rule (e.g., 'per workflow placement rule: `.github/workflows/`')"

4. **Add planner test** `tests/test_agents/test_planner.py`
   - Verify prompt includes taxonomy section
   - Verify prompt includes explicit placement rules
   - Verify prompt mentions claim categories (reference-doc, placement, hard-rule, etc.)

**Exit Criteria**:
- ✅ `src/alfred/schemas/claim_types.py` exists with typed taxonomy and placement rules
- ✅ Planner prompt updated to include both taxonomy and rules
- ✅ Test proves planner receives structured taxonomy
- ✅ No regression in current grounding (existing tests still pass)

---

### Task 2: Expand Partial-State Modeling (Gate: 4+ partial states tracked)

**Goal**: Move beyond CLI-only partial state to a general framework tracking workflows, schemas, docs, entry points.

**Work**:

1. **Expand `src/alfred/tools/repo_facts.py`**

   a. **Replace `read_partial_state_facts()` with structured approach:**
      ```python
      # Define dataclass PartialStateFact:
      # - state_type (CLI, WORKFLOW, SCHEMA, DOC, ENTRY_POINT)
      # - is_declared (bool)
      # - is_implemented (bool)
      # - declared_location (str, e.g., "pyproject.toml")
      # - implementation_location (str, e.g., "src/alfred/cli.py")
      # - description (str)
      # - expected_vocabulary (str, e.g., "declared but unimplemented")
      
      def read_partial_state_facts() -> List[PartialStateFact]:
          states = []
          
          # CLI state (existing, refactored to use new schema)
          states.append(PartialStateFact(
              state_type="CLI",
              is_declared=check_pyproject_entry_point("alfred.cli:main"),
              is_implemented=Path("src/alfred/cli.py").exists(),
              declared_location="pyproject.toml [project.scripts]",
              implementation_location="src/alfred/cli.py",
              description="...",
              expected_vocabulary="declared but unimplemented",
          ))
          
          # Workflow state (new)
          states.append(PartialStateFact(
              state_type="WORKFLOW",
              is_declared=...,  # e.g., mentioned in docs or config
              is_implemented=Path(".github/workflows/release.yml").exists(),
              declared_location="docs/canonical/ALFRED_HANDOVER_5.md (task reference)",
              implementation_location=".github/workflows/release.yml",
              description="Release workflow declared in planning docs but not yet implemented",
              expected_vocabulary="proposed for Phase 7",
          ))
          
          # Similar for SCHEMA, DOC, ENTRY_POINT states
          
          return states
      ```

   b. **Update `build_repo_facts_summary()`** to export partial-state facts:
      ```python
      def build_repo_facts_summary(...) -> str:
          summary = "..."
          partial_states = read_partial_state_facts()
          if partial_states:
              summary += "\n### Partial-State Facts\n"
              for state in partial_states:
                  summary += f"- **{state.state_type}**: {state.description}\n"
                  summary += f"  Declared: {state.is_declared}, Implemented: {state.is_implemented}\n"
                  summary += f"  Vocabulary: \"{state.expected_vocabulary}\"\n"
          return summary
      ```

2. **Update `scripts/validate_alfred_planning_facts.py`**

   a. **Expand `_check_partial_state()`** to validate all partial-state types:
      ```python
      def _check_partial_state(draft_text, partial_states: List[PartialStateFact]) -> List[Finding]:
          findings = []
          for state in partial_states:
              # If state.expected_vocabulary is set, ensure draft uses correct phrasing
              # Example: if state.state_type == "CLI" and state.is_declared and not state.is_implemented,
              # then "declared but unimplemented" is correct; "exists" or "missing" are wrong
              wrong_phrasings = generate_wrong_phrasings(state)
              for wrong_phrase in wrong_phrasings:
                  if wrong_phrase in draft_text:
                      findings.append(Finding(
                          category=ClaimCategory.PARTIAL_STATE,
                          claim=f"{state.state_type} state incorrectly described",
                          section="WHAT EXISTS TODAY or relevant task",
                          expected=state.expected_vocabulary,
                          actual=wrong_phrase,
                          severity="ERROR",
                      ))
          return findings
      ```

3. **Add planner constraint** (in `src/alfred/agents/planner.py`)
   - Inject partial-state facts explicitly
   - Add instruction: "For partial-state facts, use the exact vocabulary provided. Do not say 'exists' for declared-but-missing features."

4. **Add validator tests** `tests/test_scripts/test_validate_alfred_planning_facts.py`
   - ✓ CLI state validation (existing)
   - ✓ Workflow state validation (new)
   - ✓ Schema state validation (new)
   - ✓ Doc state validation (new)
   - ✓ Entry-point state validation (new)

5. **Add planner tests** `tests/test_agents/test_planner.py`
   - Verify planner receives partial-state facts
   - Verify planner can generate correct vocabulary for each state type

**Exit Criteria**:
- ✅ `PartialStateFact` dataclass defined and used
- ✅ At least 4 partial-state types tracked (CLI, workflows, schemas, docs)
- ✅ Planner receives structured partial-state facts
- ✅ Validator enforces correct vocabulary for all partial-state types
- ✅ 4+ validator tests added (one per state type)
- ✅ 2+ planner tests added

---

### Task 3: Formalize Repo-Growth Conventions as Schema (Gate: `RepoGrowthFacts` schema exists & planner uses it)

**Goal**: Encode placement rules, naming conventions, and structural expectations as a first-class schema, not as inline code comments.

**Work**:

1. **Create `src/alfred/schemas/repo_conventions.py`**
   ```python
   # New file; define:
   # - dataclass PlacementRule(artifact_type, canonical_root, pattern, examples, exceptions)
   # - dataclass NamingConvention(artifact_type, pattern, examples)
   # - dataclass StructuralRule(artifact_type, required_shape, forbidden_shape, examples)
   # - dataclass RepoGrowthFacts(placement_rules, naming_conventions, structural_rules)
   # - function infer_repo_growth_facts(repo_root: Path) -> RepoGrowthFacts
   # - function format_repo_growth_facts_for_prompt() -> str
   ```

2. **Implement `infer_repo_growth_facts()`**
   - Analyze existing repo structure
   - Extract placement patterns (workflows under `.github/workflows/`, schemas under `src/alfred/schemas/`, etc.)
   - Extract naming patterns (handover docs as `ALFRED_HANDOVER_*.md`, workflows in kebab-case, etc.)
   - Extract structural rules (schemas as packages, not single files; agents as module + tests, etc.)

3. **Define canonical rules** (based on current repo state and CLAUDE.md)
   ```python
   REPO_GROWTH_FACTS = RepoGrowthFacts(
       placement_rules=[
           PlacementRule(
               artifact_type="workflow",
               canonical_root=".github/workflows/",
               pattern="*.yml",
               examples=[".github/workflows/ci.yml", ".github/workflows/release.yml"],
               exceptions=None,
           ),
           PlacementRule(
               artifact_type="schema",
               canonical_root="src/alfred/schemas/",
               pattern="{name}.py (as module, not file)",
               examples=["src/alfred/schemas/health.py", "src/alfred/schemas/checkpoint.py"],
               exceptions="pyproject.toml is at root, not under schemas",
           ),
           # ... more placement rules
       ],
       naming_conventions=[
           NamingConvention(
               artifact_type="handover_doc",
               pattern="ALFRED_HANDOVER_{N}(_REASON)?.md",
               examples=["ALFRED_HANDOVER_6.md", "ALFRED_HANDOVER_4_BUG_SCRUB.md"],
           ),
           # ... more naming conventions
       ],
       structural_rules=[
           StructuralRule(
               artifact_type="agent",
               required_shape="agent module + tests in tests/test_agents/",
               forbidden_shape="class-based agents",
               examples=["src/alfred/agents/planner.py", "tests/test_agents/test_planner.py"],
           ),
           # ... more structural rules
       ],
   )
   ```

4. **Update `src/alfred/agents/planner.py`**
   - Call `infer_repo_growth_facts()` and include formatted output in prompt
   - Add section: `## REPO GROWTH CONVENTIONS`
   - Include placement rules, naming conventions, structural rules
   - Add instruction: "When proposing new files, cite the applicable rule (e.g., 'per placement rule, workflows go in `.github/workflows/`')"

5. **Update `src/alfred/tools/repo_facts.py`**
   - `build_repo_facts_summary()` should include repo growth facts

6. **Add tests**
   - `tests/test_tools/test_repo_conventions.py` (new): verify infer_repo_growth_facts() works
   - `tests/test_agents/test_planner.py`: verify planner receives repo-growth facts

**Exit Criteria**:
- ✅ `src/alfred/schemas/repo_conventions.py` exists with typed schemas
- ✅ `infer_repo_growth_facts()` implemented and tested
- ✅ Planner prompt includes repo-growth facts
- ✅ New tests pass

---

### Task 4: Refactor Deterministic Findings to Typed Schemas (Gate: Findings are schemas, not strings)

**Goal**: Convert rejection-text findings into structured schemas so planner can parse and learn from them deterministically.

**Work**:

1. **Create `src/alfred/schemas/validator_findings.py`**
   ```python
   # New file; define:
   # - dataclass PlacementFinding(artifact_type, proposed_location, canonical_location, rule)
   # - dataclass HardRuleFinding(rule_name, violation, constraint, phase_allowed)
   # - dataclass PartialStateFinding(state_type, incorrect_phrasing, correct_vocabulary)
   # - dataclass ReferenceDocFinding(doc_path, issue_type, expected_state)
   # - dataclass StructuralFinding(artifact_type, proposed_shape, required_shape, rule)
   # - dataclass FormattedFinding(category, severity, finding_object, human_message)
   # 
   # Essentially: take Finding and split into category-specific typed objects
   ```

2. **Refactor `scripts/validate_alfred_planning_facts.py`**

   a. **Update current-state validator to return typed findings**:
      ```python
      def _check_reference_documents(...) -> List[FormattedFinding]:
          findings = []
          for bad_path in found_bad_paths:
              finding = ReferenceDocFinding(
                  doc_path=bad_path,
                  issue_type="not_found",
                  expected_state="present in docs/",
              )
              findings.append(FormattedFinding(
                  category=ClaimCategory.REFERENCE_DOC,
                  severity="ERROR",
                  finding_object=finding,
                  human_message=f"Reference doc not found: {bad_path}",
              ))
          return findings
      ```

   b. **Update future-task validator to return typed findings**:
      ```python
      def _check_placement(...) -> List[FormattedFinding]:
          findings = []
          if bad_workflow_path:
              finding = PlacementFinding(
                  artifact_type="workflow",
                  proposed_location=bad_workflow_path,
                  canonical_location=".github/workflows/",
                  rule="Workflow files must be under .github/workflows/",
              )
              findings.append(FormattedFinding(
                  category=ClaimCategory.PLACEMENT,
                  severity="ERROR",
                  finding_object=finding,
                  human_message=f"Workflow placement incorrect. Must use: .github/workflows/",
              ))
          return findings
      ```

3. **Update planner integration** in `src/alfred/orchestrator.py`
   - When feeding findings to planner, include both `human_message` (for readability) AND structured finding object (JSON serializable)
   - Planner input should include: `deterministic_findings: List[FormattedFinding]`

4. **Update planner prompt** in `src/alfred/agents/planner.py`
   - Include instruction: "Structured finding objects are provided below. Parse and address them directly."
   - For PlacementFinding: "proposed_location is wrong; must use canonical_location"
   - For PartialStateFinding: "use correct_vocabulary, not incorrect_phrasing"
   - For HardRuleFinding: "this is forbidden in current phase; constraint is [...]"

5. **Add tests**
   - `tests/test_scripts/test_validate_alfred_planning_facts.py`: verify typed findings are returned
   - `tests/test_agents/test_planner.py`: verify planner receives and parses typed findings

**Exit Criteria**:
- ✅ `src/alfred/schemas/validator_findings.py` created with typed finding schemas
- ✅ Validator refactored to return `FormattedFinding` objects
- ✅ Orchestrator passes structured findings to planner
- ✅ Planner prompt includes instructions for parsing typed findings
- ✅ Tests verify typed findings are generated and planner receives them

---

### Task 5: Strengthen Reference-Doc Validation (Gate: Reference docs validated structurally & semantically)

**Goal**: Move reference-doc validation beyond path existence to structural and semantic checks.

**Work**:

1. **Create `src/alfred/tools/reference_doc_validator.py`**
   ```python
   # New file; define:
   # - dataclass ReferenceDocMetadata(path, title, expected_handover_id, date, exists)
   # - function extract_reference_doc_metadata(doc_path) -> ReferenceDocMetadata
   # - function validate_reference_doc_structure(doc_path) -> List[Issue]
   # - function validate_reference_doc_cross_links(doc_path, all_docs) -> List[Issue]
   ```

   a. **Structural validation**: Check if reference doc exists and has expected fields
      - ALFRED_HANDOVER_*.md docs should have: `id`, `date`, `author` metadata
      - Should have section markers (`## CONTEXT`, `## TASKS`, etc.)
      - Should have clear exit criteria

   b. **Cross-link validation**: If doc A references doc B, check if B exists and is recent
      - Example: `ALFRED_HANDOVER_6.md` references `ALFRED_HANDOVER_5.md`; verify both exist and version is consistent

   c. **Freshness validation**: Flag if referenced doc is stale relative to handover date

2. **Update `scripts/validate_alfred_planning_facts.py`**
   - Expand `_check_reference_documents()` to call new validation functions
   - Return structured `ReferenceDocFinding` objects with issue type

3. **Add tests** `tests/test_tools/test_reference_doc_validator.py`
   - ✓ Valid reference doc passes
   - ✓ Missing reference doc fails
   - ✓ Reference doc without expected metadata fails
   - ✓ Stale reference doc warns (warning, not error)
   - ✓ Cross-link to nonexistent doc fails

4. **Update planner constraint** (in `src/alfred/agents/planner.py`)
   - Add instruction: "When referencing docs, ensure they exist and have expected metadata. If creating a new doc, include `id`, `date`, `author` fields."

**Exit Criteria**:
- ✅ `src/alfred/tools/reference_doc_validator.py` created
- ✅ Structural, semantic, and freshness checks implemented
- ✅ Validator updated to use new checks
- ✅ 4+ validator tests added
- ✅ No regression in existing validation

---

### Task 6: Add Regression & Edge-Case Tests (Gate: 60+ tests covering new cases)

**Goal**: Protect against repeat hallucinations and ensure new functionality is robust.

**Work**:

1. **Reference-doc regression tests** `tests/test_scripts/test_validate_alfred_planning_facts.py`
   ```python
   def test_reference_doc_with_wrong_title_rejected(): ...
   def test_reference_doc_missing_metadata_flagged(): ...
   def test_reference_doc_stale_warns_not_errors(): ...
   def test_cross_link_to_nonexistent_doc_fails(): ...
   ```

2. **Negation edge-case tests** `tests/test_scripts/test_validate_alfred_planning_facts.py`
   ```python
   def test_complex_prose_with_embedded_clauses(): ...
   def test_negation_with_unusual_punctuation(): ...
   def test_path_claim_near_imperative_negation(): ...
   ```

3. **Partial-state edge-case tests** `tests/test_scripts/test_validate_alfred_planning_facts.py`
   ```python
   def test_cli_declared_but_unimplemented_correct_vocabulary(): ...
   def test_workflow_declared_but_unimplemented_correct_vocabulary(): ...
   def test_schema_declared_but_unimplemented_correct_vocabulary(): ...
   def test_wrong_vocabulary_for_partial_state_fails(): ...
   ```

4. **Typed-finding adoption tests** `tests/test_agents/test_planner.py`
   ```python
   def test_planner_receives_typed_findings(): ...
   def test_planner_addresses_placement_finding(): ...
   def test_planner_addresses_partial_state_finding(): ...
   def test_planner_cites_placement_rule_in_output(): ...
   ```

5. **Repo-growth convention tests** `tests/test_tools/test_repo_conventions.py`
   ```python
   def test_infer_repo_growth_facts_returns_placement_rules(): ...
   def test_infer_repo_growth_facts_returns_naming_conventions(): ...
   def test_infer_repo_growth_facts_returns_structural_rules(): ...
   ```

6. **Integration tests** (new file `tests/test_grounding_refinement_integration.py`)
   ```python
   def test_end_to_end_typed_taxonomy_to_planner_to_validator(): ...
   def test_planner_respects_placement_rules(): ...
   def test_planner_uses_correct_partial_state_vocabulary(): ...
   def test_validator_catches_placement_violations_with_typed_findings(): ...
   def test_orchestrator_passes_typed_findings_to_planner(): ...
   ```

**Exit Criteria**:
- ✅ 60+ new tests written
- ✅ All tests pass
- ✅ Coverage increases in grounding-related modules
- ✅ No regression in existing tests

---

### Task 7: Generate & Validate New Handover Draft (Gate: Draft demonstrates improved grounding)

**Goal**: Prove that all improvements work end-to-end by generating a new handover and validating it against new and existing criteria.

**Work**:

1. **Run handover generation** with updated codebase
   ```bash
   source .venv/bin/activate
   python scripts/generate_phase7.py --output docs/ALFRED_HANDOVER_7_GROUNDING_REFINED.md
   ```

2. **Validate against current-state factual gate**
   ```bash
   python scripts/validate_alfred_planning_facts.py \
       docs/ALFRED_HANDOVER_7_GROUNDING_REFINED.md \
       --mode current-state
   ```
   - Expected: All current-state factual errors are caught (no regressions)

3. **Validate against future-task realism gate**
   ```bash
   python scripts/validate_alfred_planning_facts.py \
       docs/ALFRED_HANDOVER_7_GROUNDING_REFINED.md \
       --mode future-task-realism
   ```
   - Expected: No placement violations, hard-rule violations, or granularity issues

4. **Manual inspection checklist**
   - ✓ All proposed new files cite placement rules (e.g., "per workflow placement rule: `.github/workflows/`")
   - ✓ Partial-state facts use correct vocabulary ("declared but unimplemented", "proposed for Phase X", etc.)
   - ✓ Reference docs are real, recent, and properly formatted
   - ✓ Schema proposals use correct structure (packages, not single files)
   - ✓ No hallucinations of fake agent names, fake API paths, fake tooling

5. **Compare to prior draft** (ALFRED_HANDOVER_6.md)
   - Generate comparison report showing improvement areas
   - Document which specific grounding refinements helped

**Exit Criteria**:
- ✅ New draft generated without errors
- ✅ Passes both factual and realism validators
- ✅ Manual inspection passes all checkpoints
- ✅ Comparison to ALFRED_HANDOVER_6 shows measurable improvement
- ✅ Draft is promotion-ready (no hand-editing needed)

---

## CHECKPOINT GATES (HARD STOPS)

| Gate # | Title | Condition | Blocker if Failed | Reviewer Action |
|---|---|---|---|---|
| **CG1** | Typed taxonomy exported | Planner receives `ClaimCategory` enum and examples in prompt | YES | Reject PR; require redesign |
| **CG2** | Partial-state scope | 4+ partial-state types tracked; tests pass | YES | Reject PR; expand scope |
| **CG3** | Repo-growth schema | `RepoGrowthFacts` defined, planner receives it, tests pass | YES | Reject PR; complete schema |
| **CG4** | Typed findings | Validator returns `FormattedFinding` objects; planner parses them | YES | Reject PR; refactor findings |
| **CG5** | Reference-doc validation | Structural + semantic checks implemented; tests pass | NO | Merge with note; plan enhancement |
| **CG6** | Regression tests | 60+ tests added; all pass; no regression | YES | Reject PR; add missing tests |
| **CG7** | New draft valid | Handover generation succeeds; passes both validators; manual inspection passes | YES | Reject PR; iterate on generation |
| **CG8** | No hallucinations | New draft does not introduce any of the prior hallucination classes | YES | Reject PR; debug generation |

---

## WORK BREAKDOWN

### Phase A: Schema & Convention Definition (2–4 hours)
- **Task 1**: Define & export typed claim taxonomy
- **Task 3**: Formalize repo-growth conventions

**Blockers**: None (parallel work)  
**Dependencies**: None  
**Gate**: CG1, CG3

### Phase B: Validator Refactoring (3–5 hours)
- **Task 2**: Expand partial-state modeling
- **Task 4**: Refactor findings to typed schemas
- **Task 5**: Strengthen reference-doc validation

**Blockers**: Phase A must complete first  
**Dependencies**: `claim_types.py`, `repo_conventions.py` from Phase A  
**Gate**: CG2, CG4, CG5

### Phase C: Integration & Testing (2–4 hours)
- **Task 6**: Add regression & edge-case tests
- **Task 7**: Generate & validate new handover

**Blockers**: Phase B must complete first  
**Dependencies**: All new schemas, validators, and planner updates  
**Gate**: CG6, CG7, CG8

### Estimated Total Time: 7–13 hours

---

## IMPLEMENTATION NOTES & HAZARDS

### Hazard 1: Planner May Not Adopt Typed Taxonomy Without Explicit Training

**Risk**: Planner receives typed claims but ignores them; generates unstructured output anyway.  
**Mitigation**:
- Add explicit instruction: "When proposing new artifacts, use format: `per [RULE_NAME] ([reference]): [artifact]`"
- Include 2–3 examples in prompt showing correct format
- Test planner output for format compliance

### Hazard 2: Partial-State Inference May Be Incomplete

**Risk**: Other partial states exist (not just CLI/workflow/schema) and are missed.  
**Mitigation**:
- Scan `pyproject.toml` for all declared entry points, not just CLI
- Scan `.github/workflows/` for workflow descriptions in docs
- Scan `src/alfred/schemas/` for schema placeholders
- If uncertainty, err on the side of marking as "partially missing" with explicit reason

### Hazard 3: Repo-Growth Conventions May Not Be Exhaustive

**Risk**: Planner encounters a new artifact type (e.g., GitHub Actions composite actions, Docker configs) and has no rule.  
**Mitigation**:
- Infer rules from existing repo structure; document assumptions
- Add explicit note: "If you encounter an artifact type not listed here, propose placement by analogy to closest match"
- Plan post-release survey to capture missed conventions

### Hazard 4: Typed Findings May Require Major Planner Rewrite

**Risk**: Planner expects text findings; switching to schemas breaks existing retry logic.  
**Mitigation**:
- Keep human-readable `human_message` field in `FormattedFinding`; planner can parse that if needed
- Test incrementally: add typed findings to prompt alongside text; verify parser works
- Have fallback: if planner breaks, revert to text-only findings

### Hazard 5: Reference-Doc Structural Validation May Be Too Strict

**Risk**: Historical docs don't meet new standards; validator rejects valid old docs.  
**Mitigation**:
- Apply structural validation only to docs referenced in future handovers, not retroactively
- Flag failures as WARNING, not ERROR, during transition period
- Grandfather old docs; only enforce new standards on new/updated docs

### Hazard 6: Tests May Become Brittle to Prompt Changes

**Risk**: Planner prompt changes; tests expecting specific formatted output break.  
**Mitigation**:
- Test observable behavior (planner addresses findings, planner cites rules) not exact text
- Use fuzzy matching for format verification (e.g., "find `.github/workflows/` somewhere in task")
- Keep assertions focused on semantic correctness, not prose style

---

## ROLLBACK PLAN

If any gate fails and cannot be resolved in 1 iteration:

1. **Revert new schema files** — remove `claim_types.py`, `repo_conventions.py`, `validator_findings.py`
2. **Revert planner prompt changes** — restore previous prompt template
3. **Revert validator changes** — keep current validator structure; remove new checks
4. **Restore previous handover generation** — use ALFRED_HANDOVER_6.md as reference state
5. **Document failure** — create a post-mortem under `docs/scratch/` (for example, `grounding_refinement_failure_postmortem.md`)
6. **Plan re-approach** — re-evaluate scope and priority

---

## POST-MORTEM TEMPLATE (For Executor Failures)

```markdown
# Post-Mortem: [Gate Name] Failure

**Date**: [date]  
**Gate**: [CG1–CG8]  
**Symptom**: [what failed]  

## Root Cause
[why did it fail?]

## Evidence
- [log snippet]
- [test failure]
- [code issue]

## Immediate Fix
[what was done to patch]

## Structural Lesson
[what the system should have caught]

## Preventive Action
[what to add to avoid repeat]
```

---

## REFERENCES

- `docs/active/FACTUAL_VALIDATOR_FUTURE_TASK_PLANNING_REALISM.md` — original design brief (read this first)
- `scripts/validate_alfred_planning_facts.py` — current validator
- `src/alfred/agents/planner.py` — planner prompt template
- `src/alfred/tools/repo_facts.py` — repo facts layer
- `src/alfred/orchestrator.py` — deterministic integration point
- `CLAUDE.md` — methodology constraints (no classes, functions only, etc.)
- `tests/test_scripts/test_validate_alfred_planning_facts.py` — current test suite (80+ cases)
- `tests/test_agents/test_planner.py` — planner test suite

---

## SUCCESS CRITERIA (FINAL)

✅ Approved when ALL of the following are true:

1. All 8 checkpoint gates (CG1–CG8) pass
2. No regression in existing factual validation
3. New draft (ALFRED_HANDOVER_7_*) passes both validators
4. 60+ new tests added; all pass
5. Manual inspection verifies improved grounding (placement rules cited, vocabulary correct, no hallucinations)
6. Code review confirms no deviations from CLAUDE.md methodology
7. No hand-editing of generated handover required

---

## HANDOFF

**To**: Codex  
**Authority**: Executor may implement all tasks in this handover without further approval until a checkpoint gate fails.  
**Escalation**: If any gate fails, pause and create post-mortem. Do not proceed to next phase without reviewer approval.  
**Promotion**: This handover is complete when CG8 passes and the generated draft is promotion-ready.

---

**Prepared by**: Claude  
**Date**: 2026-04-21  
**Status**: Ready for execution
