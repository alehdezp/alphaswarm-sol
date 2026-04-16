# How to Write index.yaml

The `index.yaml` file is the **required** metadata file for every vulnerability subcategory. It provides machine-readable information for BSKG pattern matching, test generation, and LLM context.

## Required Fields

### Core Identification
- **id**: Unique identifier (kebab-case, e.g., `oracle-price-manipulation`)
- **category**: Parent category name (must match folder name)
- **subcategory**: Subcategory name (must match folder name)
- **severity**: One of: `critical`, `high`, `medium`, `low`
- **vulndoc**: Explicit path for validation (e.g., `oracle/price-manipulation`)

### Description
- **description**: Multi-line string explaining the vulnerability
  - What is the core issue?
  - How does it manifest?
  - Keep it clear and concise (2-4 sentences)

## Phase 7 Test Generation Fields

These fields enable automated test generation and pattern validation:

### semantic_triggers
**Purpose:** BSKG operations that indicate this vulnerability might be present.

**Format:** List of operation names (ALL CAPS)

**Example:**
```yaml
semantic_triggers:
  - READS_EXTERNAL_VALUE
  - READS_ORACLE
  - USES_IN_CALCULATION
  - TRANSFERS_VALUE_OUT
```

**Good triggers:** Semantic operations from BSKG (see `docs/reference/operations.md`)
**Bad triggers:** Function names, variable names

### vql_queries
**Purpose:** Example VQL queries that detect this vulnerability.

**Format:** List of VQL query strings

**Example:**
```yaml
vql_queries:
  - "FIND functions WHERE reads_oracle AND NOT has_staleness_check"
  - "FIND functions WHERE uses_external_value_in_calculation AND NOT has_bounds_check"
```

**Tips:**
- Test queries in BSKG CLI first: `uv run alphaswarm query "..."`
- Focus on graph properties, not code structure
- Include both positive detection and false-positive filters

### graph_patterns
**Purpose:** Structural patterns in the knowledge graph (operation sequences).

**Format:** List of arrow-notation patterns

**Example:**
```yaml
graph_patterns:
  - "external_price_read -> calculation -> state_write"
  - "read_balance -> external_call -> write_balance"
```

**Pattern syntax:**
- `operation1 -> operation2`: Sequential operations
- Use semantic operations, not implementation details

### reasoning_template
**Purpose:** Pseudocode/semantic logic that guides test generation and LLM reasoning.

**Format:** Multi-line string with numbered steps

**Example:**
```yaml
reasoning_template: |
  1. Identify oracle reads (getPrice, latestAnswer, etc.)
  2. Trace value flow to calculations
  3. Check for manipulation windows (single-block, no TWAP)
  4. Verify bounds checking or staleness checks
  5. Look for lack of reentrancy guards
```

**Good template:**
- Step-by-step detection logic
- Mentions what to look for in graph
- Includes protective measures to check
- Semantic/behavioral focus

**Bad template:**
- "Search for function named X"
- Implementation-specific details
- No mention of graph queries

## Optional Fields

### relevant_properties
List of BSKG properties used in detection (for documentation).

### graph_signals
Expected property values with criticality:
```yaml
graph_signals:
  - property: state_write_after_external_call
    expected: true
    critical: true
    description: Function writes state after making external call
```

### behavioral_signatures
Short-hand operation sequences (compact notation):
```yaml
behavioral_signatures:
  - "R:bal->X:out->W:bal"  # Read balance, external call, write balance
```

### operation_sequences
Vulnerable vs safe patterns:
```yaml
operation_sequences:
  vulnerable:
    - "READS_BALANCE -> TRANSFERS_VALUE -> WRITES_BALANCE"
  safe:
    - "READS_BALANCE -> WRITES_BALANCE -> TRANSFERS_VALUE"
```

### false_positive_indicators
Common patterns that look vulnerable but aren't:
```yaml
false_positive_indicators:
  - "Modifier present: nonReentrant"
  - "External call is to trusted contract (hardcoded)"
```

### patterns
List of pattern IDs in the `./patterns/` folder:
```yaml
patterns:
  - oracle-001-twap
  - oracle-002-spot
```

### test_coverage
Test files that cover this vulnerability:
```yaml
test_coverage:
  - tests/test_oracle_lens.py:test_price_manipulation_*
  - tests/adversarial/test_oracle_obfuscation.py
```

### related_exploits
One-line references to real-world exploits:
```yaml
related_exploits:
  - dao-hack
  - fei-rari-hack
```

## Common Mistakes

### Mistake 1: Using Function Names
Bad:
```yaml
semantic_triggers:
  - transferFrom
  - withdraw
```

Good:
```yaml
semantic_triggers:
  - TRANSFERS_VALUE_OUT
  - WRITES_USER_BALANCE
```

### Mistake 2: Implementation-Specific Reasoning
Bad:
```yaml
reasoning_template: |
  1. Search for functions named "withdraw"
  2. Check if they call transfer()
```

Good:
```yaml
reasoning_template: |
  1. Identify functions with TRANSFERS_VALUE_OUT operation
  2. Check if they lack access control (CHECKS_PERMISSION)
  3. Verify state updates happen before value transfer (CEI pattern)
```

### Mistake 3: Missing Phase 7 Fields
Vulnerability entries without `semantic_triggers`, `vql_queries`, and `reasoning_template` cannot support automated test generation. These fields are critical for Phase 7.

### Mistake 4: Forgetting Graph-First
All detection logic should reference BSKG graph queries, not manual code inspection. LLMs should use graph operations, not read source files directly.

## Examples

### Good Example (Complete)
```yaml
id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation

description: |
  Using spot price from oracle without TWAP or staleness checks allows
  price manipulation via flash loans or single-block MEV attacks.

semantic_triggers:
  - READS_EXTERNAL_VALUE
  - READS_ORACLE
  - USES_IN_CALCULATION

vql_queries:
  - "FIND functions WHERE reads_oracle AND NOT has_staleness_check"

graph_patterns:
  - "external_price_read -> calculation -> state_write"

reasoning_template: |
  1. Identify oracle reads (getPrice, latestAnswer, etc.)
  2. Trace value flow to calculations
  3. Check for manipulation windows (single-block, no TWAP)
  4. Verify bounds checking or staleness checks

patterns:
  - oracle-001-twap
  - oracle-002-spot

test_coverage:
  - tests/test_oracle_lens.py:test_price_manipulation_*
```

### Minimal Example (Acceptable)
```yaml
id: simple-reentrancy
category: reentrancy
subcategory: classic
severity: critical
vulndoc: reentrancy/classic

description: |
  State write after external call without reentrancy guard.

semantic_triggers:
  - TRANSFERS_VALUE_OUT
  - WRITES_USER_BALANCE

vql_queries:
  - "FIND functions WHERE writes_after_external_call AND NOT has_reentrancy_guard"

reasoning_template: |
  1. Identify external calls with value transfer
  2. Check if state writes happen after the call
  3. Verify lack of reentrancy guards
```

## Validation

Use the CLI to validate your index.yaml:
```bash
uv run alphaswarm vulndocs validate vulndocs/
```

Progressive validation levels:
- **MINIMAL**: Required fields present
- **STANDARD**: At least one .md file
- **COMPLETE**: All recommended .md files
- **EXCELLENT**: Patterns with test coverage

## Template Reference

See `.meta/templates/subcategory/index.yaml` for the full template.

---

*Remember: Graph-first always. LLMs use BSKG queries, not manual code reading.*
