# VulnDocs Framework Guide

**Unified vulnerability knowledge system for AlphaSwarm.sol.**

## Overview

The VulnDocs framework is a structured knowledge system that unifies vulnerability documentation, pattern definitions, and test specifications into a single source of truth. It serves both humans and LLM agents, providing comprehensive information about each vulnerability type.

### Purpose

- **Single Source of Truth**: All vulnerability knowledge lives in `vulndocs/`, not scattered across patterns/ and docs/
- **LLM-Optimized**: Structured YAML with rich context for agent comprehension
- **Graph-First**: Emphasizes BSKG semantic operations over code-reading heuristics
- **Test-Driven**: Each vulnerability includes or links to test cases demonstrating detection

### Relationship to Patterns

Every pattern in `patterns/*.yaml` MUST reference a vulndoc entry via the `vulndoc` field:

```yaml
id: reentrancy-classic
name: Classic Reentrancy
vulndoc: vulndocs/reentrancy-classic/
# ... rest of pattern
```

This creates a bidirectional link between detection logic (patterns) and knowledge (vulndocs).

## Folder Structure

```
vulndocs/
├── .meta/                        # VulnDocs framework metadata
│   ├── templates/                # Skeleton templates
│   │   ├── category.yaml
│   │   ├── pattern.yaml
│   │   ├── pattern_context_pack_v2.yaml
│   │   ├── provenance.yaml
│   │   └── subcategory/
│   │       ├── index.yaml        # Machine-readable metadata
│   │       ├── overview.md       # Human-readable description
│   │       ├── detection.md      # How to detect
│   │       ├── verification.md   # How to verify
│   │       ├── exploits.md       # Real-world exploits
│   │       └── core-pattern.md
│   └── instructions/             # Authoring guidance
│       ├── index.md
│       ├── patterns.md
│       ├── detection.md
│       ├── verification.md
│       └── exploits.md
├── reentrancy-classic/           # Example vulnerability
│   ├── index.yaml                # Main entry (REQUIRED)
│   ├── pattern.yaml              # Pattern definition (optional if pattern exists in patterns/)
│   ├── tests/                    # Phase 7 tests (optional)
│   │   ├── test_reentrancy.py
│   │   └── vulnerable.sol
│   └── research/                 # Supporting materials (optional)
│       ├── sources.md
│       └── real-exploits.md
└── ...                           # More vulnerabilities
```

### Required vs Optional Files

**Required:**
- `index.yaml` - Main vulnerability entry with metadata, description, detection strategy

**Optional but Recommended:**
- `pattern.yaml` - Pattern definition (if not in patterns/)
- `tests/` - Test files for validation
- `research/` - Source materials, exploit examples

### Special Folders

**.meta/templates/**: Starting points for new entries. Never modified directly.

**.meta/instructions/**: Authoring guidance for VulnDocs entries (index, patterns, detection, verification, exploits). This is documentation for humans and agents, not skill prompts.

## Creating New Vulnerabilities

### Method 1: Using Agent Skill (Recommended)

```bash
# Invoke the skill in your conversation with Claude
/vrs-add-vulnerability
```

The agent will:
1. Prompt for vulnerability details
2. Create folder structure
3. Generate index.yaml with proper fields
4. Scaffold pattern.yaml if needed
5. Create initial test files

**Note**: The skill is a prompt template that guides the agent's behavior. The agent will execute `uv run alphaswarm vulndocs scaffold` commands via the Bash tool.

### Method 2: Using CLI Directly

```bash
# Scaffold a new vulnerability entry
uv run alphaswarm vulndocs scaffold weak-randomness \
  --name "Weak Randomness" \
  --severity high \
  --category randomness

# This creates:
# vulndocs/weak-randomness/
# ├── index.yaml (pre-filled template)
# └── pattern.yaml (optional)
```

Then edit `vulndocs/weak-randomness/index.yaml` to fill in the details.

### Required Fields in index.yaml

```yaml
id: weak-randomness                    # Unique identifier (kebab-case)
name: Weak Randomness                   # Human-readable name
category: randomness                    # Category tag
severity: high                          # critical | high | medium | low
status: draft                           # draft | validated | excellent

description: |
  Clear explanation of the vulnerability

detection_strategy:
  graph_query: |                        # BSKG query or VQL2 (REQUIRED)
    FIND functions WHERE
      calls_blockhash OR calls_timestamp
      AND used_for_critical_decision

  semantic_operations:                  # Operations to detect (REQUIRED)
    - READS_BLOCKHASH
    - READS_TIMESTAMP
    - MAKES_CRITICAL_DECISION

  false_positive_filters:               # How to reduce FPs
    - Check if randomness source is external oracle
    - Verify if value affects funds

real_world_examples:                    # Optional but valuable
  - project: "TheDAO"
    exploit_date: "2016-06-17"
    details: "..."

related_patterns:                       # Links to pattern files
  - id: weak-randomness-blockhash
    path: patterns/randomness/weak-randomness-blockhash.yaml

phase_7:                                # Future: comprehensive testing
  test_coverage:
    - vulnerable_example: tests/vulnerable.sol
    - safe_example: tests/safe.sol
    - edge_cases: tests/edge_cases.sol
```

### Phase 7 Fields Explanation

Phase 7 is the **Final Testing (GA Gate)** milestone where we validate all patterns with comprehensive test suites. The `phase_7` section tracks:

- **test_coverage**: Vulnerable, safe, and edge case examples
- **validation_metrics**: Precision, recall, false positive rate
- **cross_project_validation**: Real-world project testing results

These fields are optional during initial creation (draft status) but required for `validated` or `excellent` status.

## Working with Patterns

### Pattern Location Options

**Option 1**: Pattern lives in `patterns/` (traditional)
```yaml
# In vulndocs/reentrancy-classic/index.yaml
related_patterns:
  - id: reentrancy-classic
    path: patterns/reentrancy/reentrancy-classic.yaml
```

**Option 2**: Pattern lives in vulndoc folder
```yaml
# In vulndocs/reentrancy-classic/index.yaml
related_patterns:
  - id: reentrancy-classic
    path: vulndocs/reentrancy-classic/pattern.yaml
```

### VulnDoc Field Requirement

Every pattern MUST have a `vulndoc` field pointing to its documentation:

```yaml
# patterns/reentrancy/reentrancy-classic.yaml
id: reentrancy-classic
name: Classic Reentrancy
vulndoc: vulndocs/reentrancy-classic/
lens: [Reentrancy]
severity: critical
# ... match logic
```

The CLI validates this bidirectional link:
```bash
uv run alphaswarm vulndocs validate vulndocs/
# Checks:
# - Every index.yaml references existing patterns
# - Every referenced pattern has vulndoc field pointing back
```

### Test Coverage Tracking

The `phase_7.test_coverage` section tracks which test files demonstrate detection:

```yaml
phase_7:
  test_coverage:
    - vulnerable_example: tests/test_reentrancy.py::test_detects_classic_reentrancy
    - safe_example: tests/test_reentrancy.py::test_ignores_safe_cei
    - edge_cases: tests/test_reentrancy.py::test_read_only_reentrancy
```

When tests pass, update validation metrics:

```yaml
phase_7:
  validation_metrics:
    precision: 0.95
    recall: 0.89
    false_positive_rate: 0.05
```

## Validation Levels

The framework uses four validation levels to track entry quality:

### MINIMAL (Level 1)
**Required:**
- `id`, `name`, `category`, `severity`, `status`
- `description` (at least 50 characters)
- `detection_strategy.graph_query` OR `detection_strategy.semantic_operations`

**Use case:** Initial draft, basic structure in place

### STANDARD (Level 2)
**Requires MINIMAL +**
- Both `graph_query` AND `semantic_operations`
- `false_positive_filters` (at least one)
- At least one `related_patterns` entry

**Use case:** Ready for testing, detection logic defined

### COMPLETE (Level 3)
**Requires STANDARD +**
- `real_world_examples` (at least one)
- `phase_7.test_coverage` (all three: vulnerable, safe, edge cases)
- All referenced patterns have `vulndoc` field

**Use case:** Validated pattern, comprehensive testing done

### EXCELLENT (Level 4)
**Requires COMPLETE +**
- `phase_7.validation_metrics` with precision ≥ 0.90
- `phase_7.cross_project_validation` with ≥ 3 projects
- At least 3 `real_world_examples`

**Use case:** Production-ready, battle-tested pattern

### Improving Validation Level

```bash
# Check current level
uv run alphaswarm vulndocs info vulndocs/weak-randomness/

# Output shows:
# Validation level: MINIMAL
# Missing for STANDARD:
#   - false_positive_filters
#   - At least one related_patterns entry

# Add missing fields to index.yaml, then re-validate
uv run alphaswarm vulndocs validate vulndocs/weak-randomness/
```

## Mandatory Validation Pipeline

**Policy:** Any change to `vulndocs/` MUST pass through the validation pipeline before merge. This is enforced by the `/vrs-validate-vulndocs` skill and CI/CD gates.

### Invoking Validation

```bash
/vrs-validate-vulndocs                      # Validate all vulndocs changes
/vrs-validate-vulndocs --mode quick         # Quick validation (prevalidator + schema only)
/vrs-validate-vulndocs --mode standard      # Standard validation (default)
/vrs-validate-vulndocs --mode thorough      # Full GA-level validation
/vrs-validate-vulndocs --category reentrancy  # Validate specific category
```

### Pipeline Stages

The validation pipeline runs these stages **sequentially**:

| Stage | Agent | Purpose | Model |
|-------|-------|---------|-------|
| 1 | vrs-test-conductor | Orchestrate validation run | opus |
| 2 | vrs-prevalidator | URL provenance, schema, duplicate checks | haiku |
| 3 | vrs-corpus-curator | Corpus integrity, ground truth | sonnet |
| 4 | vrs-pattern-verifier | Evidence gates for Tier B/C | sonnet |
| 5 | vrs-benchmark-runner | Precision/recall metrics | haiku |
| 6 | vrs-mutation-tester | Variant generation (conditional) | haiku |
| 7 | vrs-regression-hunter | Accuracy degradation check (conditional) | sonnet |
| 8 | vrs-gap-finder-lite | Coverage and FP hotspot scan | sonnet.5 |

**Cost optimization:** Default mode uses Haiku/Sonnet. Opus only for orchestration and escalated gap analysis when `vrs-gap-finder-lite` returns `escalate_to_opus: true`.

### Adaptive Pipeline Rules

The pipeline adapts based on what changed:

**New Pattern Added:**
- All stages run
- `vrs-prevalidator` enforces provenance for new entries
- `vrs-mutation-tester` generates 10x variants per new pattern
- `vrs-regression-hunter` skipped (no baseline)

**Existing Pattern Modified:**
- All stages run
- `vrs-corpus-curator` skipped if only pattern match criteria changed
- `vrs-regression-hunter` compares to previous baseline

**Metadata-Only Change:**
- Only stages 1-2 run (`vrs-test-conductor`, `vrs-prevalidator`)
- Schema validation only

### Quality Gates

| Gate | Target | Blocking |
|------|--------|----------|
| Precision | >= 85% | Yes |
| Recall (critical) | >= 95% | Yes |
| Recall (high) | >= 85% | Yes |
| Recall (medium) | >= 70% | No (warning) |
| Schema compliance | 100% | Yes |
| Provenance verified | 100% | Yes |

If any blocking gate fails, the pipeline STOPS and reports the failure.

### CLI Validation Commands

```bash
# Full validation
uv run alphaswarm vulndocs validate vulndocs/

# Schema-only validation
uv run alphaswarm vulndocs validate vulndocs/ --schema-only

# With metrics collection
uv run alphaswarm vulndocs validate vulndocs/ --metrics --baseline .vrs/baselines/latest.json

# JSON output for CI
uv run alphaswarm vulndocs validate vulndocs/ --json
```

---

## Agent Skills

The framework provides skills for LLM agents working with vulndocs. Skill prompt templates live under `src/alphaswarm_sol/skills/shipped/` (with agent-specific prompts in `src/alphaswarm_sol/skills/shipped/agents/`). See `docs/guides/skills-basics.md` for the current skill catalog and trigger rules.

**Important**: Skills are not separate executables. They are instructions that guide LLM agents (like Claude) to invoke the appropriate CLI commands via the Bash tool.

### Skill Invocation Model

```
User: "/vrs-add-vulnerability"
  ↓
Agent reads: matching skill prompt in src/alphaswarm_sol/skills/shipped/
  ↓
Agent follows instructions to:
  1. Ask user for details
  2. Execute: uv run alphaswarm vulndocs scaffold <id> --name "..." --severity ...
  3. Edit generated index.yaml with provided details
  4. Validate: uv run alphaswarm vulndocs validate vulndocs/<id>/
```

### Available Skills

| Skill | Purpose | Typical CLI Commands Used |
|-------|---------|---------------------------|
| `/vrs-discover` | Automated Exa search for new vulnerabilities | `uv run exa-search`, `vulndocs scaffold` |
| `/vrs-add-vulnerability` | Add new vulnerability with proper structure | `vulndocs scaffold`, `vulndocs validate` |
| `/vrs-refine` | Improve patterns based on test feedback | `vulndocs validate`, pattern editing |
| `/vrs-test-pattern` | Validate patterns against real projects | `build-kg`, `query`, test execution |
| `/vrs-research` | Guided vulnerability research | Exa search, knowledge aggregation |
| `/vrs-merge-findings` | Consolidate similar entries | `vulndocs list`, manual editing |
| `/vrs-generate-tests` | Create Phase 7 test cases | Test file creation, `pytest` |

### Workflow Diagram

```
[Discovery] (/vrs-discover)
    ↓
[Add Entry] (/vrs-add-vulnerability)
    ↓
[Research] (/vrs-research) ←→ [Refine] (/vrs-refine)
    ↓
[Test Pattern] (/vrs-test-pattern)
    ↓
[Generate Tests] (/vrs-generate-tests)
    ↓
[Validation Complete]
```

**When to Use Each:**

- **Starting new vulnerability**: `/vrs-add-vulnerability` or `/vrs-discover`
- **Pattern not detecting correctly**: `/vrs-refine` + `/vrs-test-pattern`
- **Need test cases**: `/vrs-generate-tests`
- **Combining similar entries**: `/vrs-merge-findings`
- **Deep dive on vulnerability**: `/vrs-research`

## CLI Commands

### Validate

Check structure and completeness of vulndoc entries:

```bash
# Validate all entries
uv run alphaswarm vulndocs validate vulndocs/

# Validate specific entry
uv run alphaswarm vulndocs validate vulndocs/reentrancy-classic/

# JSON output (for CI)
uv run alphaswarm vulndocs validate vulndocs/ --json
```

**Output:**
- Errors: Missing required fields, broken links
- Warnings: Incomplete optional fields, low validation level
- Validation level: MINIMAL, STANDARD, COMPLETE, EXCELLENT

### Scaffold

Create new vulnerability entry with template:

```bash
# Basic usage
uv run alphaswarm vulndocs scaffold weak-randomness

# With metadata
uv run alphaswarm vulndocs scaffold weak-randomness \
  --name "Weak Randomness" \
  --severity high \
  --category randomness \
  --with-pattern

# Creates:
# vulndocs/weak-randomness/
# ├── index.yaml
# └── pattern.yaml (if --with-pattern)
```

### Info

Display details about a vulndoc entry:

```bash
# Show entry details
uv run alphaswarm vulndocs info vulndocs/reentrancy-classic/

# Output includes:
# - Validation level
# - Missing fields for next level
# - Linked patterns
# - Test coverage status
```

### List

List all vulndoc entries with status:

```bash
# List all entries
uv run alphaswarm vulndocs list

# Filter by status
uv run alphaswarm vulndocs list --status validated

# Filter by category
uv run alphaswarm vulndocs list --category reentrancy

# Output format options
uv run alphaswarm vulndocs list --format json
uv run alphaswarm vulndocs list --format table
```

## Best Practices

### Graph-First Approach

**DO**: Start with BSKG semantic operations
```yaml
detection_strategy:
  semantic_operations:
    - TRANSFERS_VALUE_OUT
    - WRITES_USER_BALANCE
  graph_query: |
    FIND functions WHERE
      has_operation(TRANSFERS_VALUE_OUT)
      AND has_operation(WRITES_USER_BALANCE)
```

**DON'T**: Rely on name heuristics
```yaml
# AVOID THIS:
detection_strategy:
  description: "Look for functions with 'withdraw' in the name"
```

### Semantic Operations Usage

Leverage the 20 core semantic operations:

**Value Operations:**
- `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE`

**Access Operations:**
- `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES`

**External Operations:**
- `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE`

**State Operations:**
- `MODIFIES_CRITICAL_STATE`, `READS_ORACLE`, `INITIALIZES_STATE`

See `docs/reference/operations.md` for complete list.

### Test Generation Importance

Every vulnerability should have tests demonstrating:

1. **Vulnerable Example**: Code that should trigger detection
2. **Safe Example**: Similar code that should NOT trigger (CEI pattern, guards)
3. **Edge Cases**: Boundary conditions, subtle variants

Use `/vrs-generate-tests` skill to create initial test suite, then refine based on test results.

### Documentation Quality

Good `detection_strategy.false_positive_filters`:
```yaml
false_positive_filters:
  - Check if external call is to whitelisted contract (owner, guardian)
  - Verify if balance update precedes external call (CEI pattern)
  - Confirm if reentrancy guard is present (nonReentrant modifier)
```

Each filter should be actionable by the detection logic or human reviewer.

### Real-World Examples

When adding `real_world_examples`, include:
- Project name and GitHub link
- Exploit date (if applicable)
- Brief description of what happened
- Link to post-mortem or audit report

This provides valuable context for understanding attack vectors.

## Next Steps

- **Add First Entry**: Use `/vrs-add-vulnerability` or CLI scaffold
- **Validate Existing Patterns**: Check which patterns need vulndoc links
- **Create Test Suite**: Use `/vrs-generate-tests` for Phase 7 coverage
- **Monitor CI**: Watch `.github/workflows/vulndocs-validate.yml` results

For questions or improvements, see `.planning/phases/05.4-vulndocs-patterns-unification/` for implementation context.
