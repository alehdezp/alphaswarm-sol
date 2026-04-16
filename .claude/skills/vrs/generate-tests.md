---
name: vrs-generate-tests
description: |
  Generate Phase 7 test cases from vulndoc reasoning templates. Creates test contracts
  for semantic complexity, real-world patterns, and adversarial scenarios.

  Invoke when user wants to:
  - Generate test cases: "generate tests for reentrancy/classic"
  - Create Phase 7 tests: "/vrs-generate-tests oracle/stale-data"
  - Build test corpus: "generate all tests for category oracle"

  This skill:
  1. Loads vulndoc (index.yaml, reasoning_template, exploits)
  2. Generates test contracts (vulnerable, safe, adversarial, edge cases)
  3. Creates test assertions and VQL queries
  4. Outputs properly structured test files
  5. Updates vulndoc test_coverage
  6. Validates test quality

slash_command: vrs:generate-tests
context: fork

tools:
  - Read
  - Write
  - Glob
  - Bash(uv run alphaswarm build-kg, validate)

model_tier: sonnet

---

# VRS Generate Tests Skill - Phase 7 Test Case Generation

You are the **VRS Generate Tests** skill, responsible for generating comprehensive test cases from vulndoc reasoning templates. You create test contracts that validate pattern detection across semantic complexity, real-world patterns, and adversarial scenarios.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "build knowledge graph," you invoke the Bash tool with `uv run alphaswarm build-kg`. When it says "read reasoning_template," you use the Read tool on the index.yaml file. When it says "write test contract," you use the Write tool. This skill file IS the prompt that guides your behavior - you execute it using your standard tools (Bash, Read, Write).

## Purpose

- **Generate test contracts** from vulndoc reasoning templates
- **Support all three test quality focuses**:
  1. Semantic complexity (graph-based reasoning required)
  2. Real-world patterns (derived from documented exploits)
  3. Adversarial scenarios (obfuscation, edge cases, false-positive traps)
- **Create test assertions** with expected detection outcomes
- **Enable Phase 7 validation** of pattern accuracy
- **Track test coverage** in vulndoc metadata

## How to Invoke

```bash
/vrs-generate-tests
/vrs-generate-tests oracle/stale-data
/vrs-generate-tests --category oracle --all
```

**Arguments:**

- `target` - Specific vulndoc to generate tests for (category/subcategory)
- `--category` - Generate tests for all entries in category
- `--all` - Generate tests for all VulnDocs
- `--types` - Test types to generate (default: all)
  - `vulnerable` - Basic vulnerable variant
  - `safe` - Mitigated variant
  - `adversarial` - Obfuscated but vulnerable
  - `edge` - Edge cases and boundary conditions

**Interactive mode** (default):
- Prompts for target vulndoc
- Shows reasoning_template
- Generates all test types

---

## Execution Workflow

### Step 1: Load Vulndoc Context

**Goal:** Extract all information needed for test generation.

**Actions:**

1. **Read index.yaml** (via Read tool):
   ```yaml
   # Target: vulndocs/oracle/stale-data/index.yaml
   id: oracle-stale-data
   category: oracle
   subcategory: stale-data
   severity: high

   # Critical fields for test generation:
   semantic_triggers:
     - READS_ORACLE
     - MISSING_STALENESS_CHECK
     - USES_UNVALIDATED_TIMESTAMP

   vql_queries:
     - "FIND functions WHERE reads_oracle AND NOT checks_timestamp"

   graph_patterns:
     - oracle_read → calculation → state_write (vulnerable)
     - oracle_read → timestamp_check → calculation → state_write (safe)

   reasoning_template: |
     1. Identify oracle data reads (getLatestPrice, latestAnswer, etc.)
     2. Check for staleness validation:
        - Chainlink: updatedAt field check
        - Pyth: publishTime check
     3. Verify staleness threshold appropriate for use case
     4. Check for fallback mechanisms
   ```

2. **Read exploits.md** (via Read tool):
   - Extract real-world exploit patterns
   - Identify actual vulnerable code structures
   - Note exploitation techniques

3. **Read detection.md** (via Read tool):
   - Understand detection logic
   - Identify edge cases mentioned
   - Note common false positives to avoid

4. **Read vulndocs/{category}/{subcategory}/patterns/*.yaml** (via Glob + Read):
   - Load all pattern YAMLs for this vulnerability
   - Extract pattern conditions for test validation

**Parsed Context Example:**

```python
context = {
    "id": "oracle-stale-data",
    "category": "oracle",
    "subcategory": "stale-data",
    "semantic_triggers": [
        "READS_ORACLE",
        "MISSING_STALENESS_CHECK",
    ],
    "vql_queries": [
        "FIND functions WHERE reads_oracle AND NOT checks_timestamp",
    ],
    "reasoning_template": """
        1. Identify oracle reads
        2. Check for staleness validation
        3. Verify threshold
        4. Check fallback
    """,
    "exploits": [
        {
            "name": "Venus Protocol Price Manipulation",
            "code_pattern": "price = oracle.latestAnswer();  // No staleness check",
        }
    ],
    "patterns": [
        {
            "id": "oracle-stale-001",
            "conditions": "reads_oracle AND NOT checks_timestamp",
        }
    ],
}
```

### Step 2: Generate Vulnerable Test Contract

**Goal:** Create basic vulnerable variant that patterns should detect.

**Template:**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * Test for: oracle/stale-data
 * Pattern: oracle-stale-001
 * Expected: MATCH (vulnerable to stale oracle data)
 *
 * Semantic reasoning:
 * - READS_ORACLE: latestRoundData() call
 * - MISSING_STALENESS_CHECK: No updatedAt validation
 * - USES_IN_CALCULATION: Price used directly in withdraw calculation
 *
 * Graph pattern:
 * getPrice() -> latestRoundData() -> calculation -> state_write
 * No timestamp check between oracle read and usage
 */
contract VulnerableStaleOracle {
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public deposits;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    /**
     * VULNERABLE: Uses oracle price without staleness check
     * Pattern should detect: READS_ORACLE + MISSING_STALENESS_CHECK
     */
    function withdraw(uint256 amount) public {
        // Get price from oracle
        (, int256 price, , , ) = priceFeed.latestRoundData();
        // VULNERABLE: No check on updatedAt timestamp!

        // Calculate withdrawal amount using potentially stale price
        uint256 value = (amount * uint256(price)) / 1e8;

        require(deposits[msg.sender] >= value, "Insufficient balance");
        deposits[msg.sender] -= value;

        (bool success, ) = msg.sender.call{value: value}("");
        require(success, "Transfer failed");
    }

    // Helper function for deposits
    function deposit() public payable {
        deposits[msg.sender] += msg.value;
    }
}
```

**Generation Logic:**

```python
def generate_vulnerable_contract(context):
    """
    Generate vulnerable test contract from vulndoc context.
    """
    contract_name = f"Vulnerable{to_pascal_case(context['subcategory'])}"

    # Extract key operations from reasoning_template
    operations = parse_reasoning_template(context['reasoning_template'])

    # Build contract structure
    contract = ContractBuilder(name=contract_name)

    # Add state variables relevant to vulnerability
    contract.add_state_vars(infer_state_vars(context))

    # Add vulnerable function implementing the pattern
    vulnerable_func = build_vulnerable_function(
        semantic_triggers=context['semantic_triggers'],
        graph_pattern=context['graph_patterns'][0],  # Vulnerable pattern
        operations=operations,
    )

    contract.add_function(vulnerable_func)

    # Add helper functions if needed
    contract.add_helpers(infer_helpers(context))

    # Add detailed comments explaining vulnerability
    contract.add_header_comment(
        vulnerability=context['id'],
        patterns=[p['id'] for p in context['patterns']],
        expected="MATCH",
        semantic_triggers=context['semantic_triggers'],
        graph_pattern=context['graph_patterns'][0],
    )

    return contract.render()
```

### Step 3: Generate Safe Test Contract

**Goal:** Create mitigated variant that patterns should NOT detect.

**Template:**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * Test for: oracle/stale-data
 * Pattern: oracle-stale-001
 * Expected: NO MATCH (properly validates staleness)
 *
 * Semantic reasoning:
 * - READS_ORACLE: latestRoundData() call
 * - CHECKS_STALENESS: Validates updatedAt timestamp
 * - SAFE_PATTERN: Timestamp check before using price
 *
 * Graph pattern:
 * getPrice() -> latestRoundData() -> timestamp_check -> calculation -> state_write
 * Staleness validation present, pattern should NOT match
 */
contract SafeStaleOracle {
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public deposits;

    uint256 public constant STALENESS_THRESHOLD = 3600; // 1 hour

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    /**
     * SAFE: Validates oracle staleness before using price
     * Pattern should NOT detect: Has CHECKS_STALENESS
     */
    function withdraw(uint256 amount) public {
        // Get price from oracle WITH timestamp
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();

        // SAFE: Check staleness before using price
        require(
            block.timestamp - updatedAt <= STALENESS_THRESHOLD,
            "Price data is stale"
        );

        // Safe to use price now
        uint256 value = (amount * uint256(price)) / 1e8;

        require(deposits[msg.sender] >= value, "Insufficient balance");
        deposits[msg.sender] -= value;

        (bool success, ) = msg.sender.call{value: value}("");
        require(success, "Transfer failed");
    }

    function deposit() public payable {
        deposits[msg.sender] += msg.value;
    }
}
```

**Generation Logic:**

```python
def generate_safe_contract(context):
    """
    Generate safe (mitigated) test contract from vulndoc context.
    """
    # Start with vulnerable contract structure
    contract = generate_vulnerable_contract(context)

    # Apply mitigations from detection.md
    mitigations = extract_mitigations(context['detection'])

    for mitigation in mitigations:
        contract = apply_mitigation(contract, mitigation)

    # Update comments to reflect safe state
    contract.set_expected_result("NO MATCH")
    contract.add_mitigation_comments(mitigations)

    return contract
```

### Step 4: Generate Adversarial Test Contract

**Goal:** Create obfuscated variant that's still vulnerable but harder to detect.

**Purpose:** Tests pattern robustness against:
- Misleading function names
- Indirect control flow
- Wrapped oracle calls
- Multiple code paths

**Template:**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * Test for: oracle/stale-data
 * Pattern: oracle-stale-001
 * Expected: MATCH (vulnerable despite obfuscation)
 * Type: ADVERSARIAL
 *
 * Obfuscation techniques:
 * - Misleading function name (validateAndWithdraw suggests safety)
 * - Oracle call wrapped in helper function
 * - Fake timestamp check (checks wrong value)
 * - Multiple code paths to vulnerability
 *
 * Semantic reasoning MUST detect:
 * - READS_ORACLE: getTrustedPrice() internally calls oracle
 * - MISSING_STALENESS_CHECK: validationPassed checks wrong timestamp
 * - Pattern should match despite misleading names
 */
contract AdversarialStaleOracle {
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public deposits;

    // Misleading: suggests staleness check exists
    uint256 public lastValidationTimestamp;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        lastValidationTimestamp = block.timestamp;
    }

    /**
     * ADVERSARIAL: Vulnerable despite misleading name
     * Function name suggests validation, but doesn't check oracle staleness
     */
    function validateAndWithdraw(uint256 amount) public {
        // Misleading: validates wrong thing
        require(validationPassed(), "Validation failed");

        // Oracle call hidden in helper
        uint256 price = getTrustedPrice();  // Misleading name

        uint256 value = (amount * price) / 1e8;

        require(deposits[msg.sender] >= value, "Insufficient balance");
        deposits[msg.sender] -= value;

        (bool success, ) = msg.sender.call{value: value}("");
        require(success, "Transfer failed");
    }

    /**
     * MISLEADING: Name suggests trusted/validated price
     * Actually just reads oracle without staleness check
     */
    function getTrustedPrice() internal view returns (uint256) {
        (, int256 price, , , ) = priceFeed.latestRoundData();
        // VULNERABLE: No staleness check!
        return uint256(price);
    }

    /**
     * MISLEADING: Checks lastValidationTimestamp, not oracle updatedAt
     * False sense of security
     */
    function validationPassed() internal view returns (bool) {
        // Checks wrong timestamp (contract state, not oracle freshness)
        return block.timestamp - lastValidationTimestamp < 3600;
    }

    function deposit() public payable {
        deposits[msg.sender] += msg.value;
    }
}
```

**Generation Logic:**

```python
def generate_adversarial_contract(context):
    """
    Generate adversarial test contract with obfuscation.
    """
    contract = generate_vulnerable_contract(context)

    # Apply obfuscation techniques
    obfuscations = [
        "misleading_names",      # Suggest safety that doesn't exist
        "wrapped_calls",         # Hide oracle calls in helpers
        "fake_checks",           # Check wrong values
        "indirect_flow",         # Multiple paths to vulnerability
    ]

    for obfuscation in obfuscations:
        contract = apply_obfuscation(contract, obfuscation)

    # Update comments to note adversarial nature
    contract.set_test_type("ADVERSARIAL")
    contract.add_obfuscation_notes(obfuscations)

    return contract
```

### Step 5: Generate Edge Case Test Contract

**Goal:** Test boundary conditions and corner cases.

**Edge Cases to Test:**

1. **Zero-state handling**: Empty vault, first user
2. **Precision edge cases**: Very small/large values
3. **Timestamp boundaries**: Exact threshold values
4. **Multiple oracle feeds**: Disagreement handling
5. **Fallback scenarios**: What if oracle fails?

**Template Example:**

```solidity
/**
 * Test for: oracle/stale-data
 * Pattern: oracle-stale-001
 * Expected: MATCH (edge case: staleness check off by one)
 * Type: EDGE CASE
 *
 * Edge case:
 * Staleness check uses <= instead of <, allowing exactly stale data
 */
contract EdgeCaseStaleOracle {
    AggregatorV3Interface public priceFeed;
    uint256 public constant STALENESS_THRESHOLD = 3600;

    function withdraw(uint256 amount) public {
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();

        // EDGE CASE: <= allows data exactly at threshold (should be <)
        require(
            block.timestamp - updatedAt <= STALENESS_THRESHOLD,
            "Stale"
        );
        // Pattern might not catch this subtle bug

        // ... rest of withdrawal logic
    }
}
```

### Step 6: Generate Test File with Assertions

**Goal:** Create Python test file with BSKG assertions.

**Test File Template:**

```python
# tests/contracts/oracle/stale_data/test_stale_oracle.py

"""
Test suite for oracle/stale-data vulnerability detection.

Generated from: vulndocs/oracle/stale-data/
Patterns tested: oracle-stale-001
"""

import pytest
from tests.graph_cache import load_graph

class TestStaleOracleDetection:
    """Test pattern detection for stale oracle data vulnerability."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Load knowledge graph for stale oracle test contracts."""
        return load_graph("oracle_stale_data")

    def test_vulnerable_detected(self, graph):
        """
        Vulnerable contract should be detected.

        Contract: VulnerableStaleOracle
        Expected: Pattern oracle-stale-001 matches withdraw()
        Semantic: READS_ORACLE + MISSING_STALENESS_CHECK
        """
        # Find vulnerable function
        vulnerable_funcs = [
            f for f in graph["functions"]
            if f["contract"] == "VulnerableStaleOracle"
            and f["name"] == "withdraw"
        ]

        assert len(vulnerable_funcs) == 1, "Should find withdraw function"
        func = vulnerable_funcs[0]

        # Check semantic triggers
        assert "READS_ORACLE" in func["operations"], \
            "Should detect oracle read operation"

        assert "MISSING_STALENESS_CHECK" not in func["operations"], \
            "Negative trigger - absence of check detected differently"

        # Check pattern match via VQL query
        from true_vkg.queries import execute_vql
        results = execute_vql(
            graph,
            "FIND functions WHERE reads_oracle AND NOT checks_timestamp"
        )

        assert any(r["id"] == func["id"] for r in results), \
            "VQL query should match vulnerable function"

    def test_safe_not_detected(self, graph):
        """
        Safe contract should NOT be detected.

        Contract: SafeStaleOracle
        Expected: Pattern oracle-stale-001 does NOT match withdraw()
        Semantic: READS_ORACLE + CHECKS_STALENESS
        """
        safe_funcs = [
            f for f in graph["functions"]
            if f["contract"] == "SafeStaleOracle"
            and f["name"] == "withdraw"
        ]

        assert len(safe_funcs) == 1
        func = safe_funcs[0]

        # Should have staleness check
        assert func.get("checks_timestamp") or func.get("checks_staleness"), \
            "Should detect staleness validation"

        # VQL query should NOT match
        from true_vkg.queries import execute_vql
        results = execute_vql(
            graph,
            "FIND functions WHERE reads_oracle AND NOT checks_timestamp"
        )

        assert not any(r["id"] == func["id"] for r in results), \
            "VQL query should NOT match safe function"

    def test_adversarial_detected(self, graph):
        """
        Adversarial contract should still be detected despite obfuscation.

        Contract: AdversarialStaleOracle
        Expected: Pattern matches despite misleading names
        Semantic: Graph-based detection transcends naming
        """
        adversarial_funcs = [
            f for f in graph["functions"]
            if f["contract"] == "AdversarialStaleOracle"
            and f["name"] == "validateAndWithdraw"
        ]

        assert len(adversarial_funcs) == 1
        func = adversarial_funcs[0]

        # Should detect oracle read even through helper function
        assert "READS_ORACLE" in func["operations"] or \
               func.get("calls_oracle_internally"), \
            "Should detect oracle read through getTrustedPrice helper"

        # VQL query should match despite obfuscation
        from true_vkg.queries import execute_vql
        results = execute_vql(
            graph,
            "FIND functions WHERE reads_oracle AND NOT checks_timestamp"
        )

        assert any(r["id"] == func["id"] for r in results), \
            "Pattern should detect vulnerability despite misleading names"

    def test_edge_case_handling(self, graph):
        """
        Edge case contract tests boundary conditions.

        Contract: EdgeCaseStaleOracle
        Expected: Depends on pattern sophistication
        """
        # Test implementation depends on specific edge case
        pass
```

**Test Generation Logic:**

```python
def generate_test_file(context, contracts):
    """
    Generate pytest file with assertions for all test contracts.
    """
    test_file = TestFileBuilder(
        vulnerability=context['id'],
        patterns=[p['id'] for p in context['patterns']],
    )

    # Add fixtures
    test_file.add_graph_fixture(infer_graph_name(context))

    # Generate test for each contract
    for contract_type, contract_code in contracts.items():
        test_func = build_test_function(
            contract_type=contract_type,
            contract_code=contract_code,
            context=context,
        )
        test_file.add_test(test_func)

    return test_file.render()
```

### Step 7: Write Test Files to Disk

**Goal:** Save generated tests to proper locations.

**File Structure:**

```
tests/contracts/{category}/{subcategory}/
├── test_{subcategory}_vulnerable.sol
├── test_{subcategory}_safe.sol
├── test_{subcategory}_adversarial.sol
├── test_{subcategory}_edge.sol
└── README.md  # Explains test purpose

tests/test_{category}_{subcategory}.py  # Python test file
```

**Actions:**

1. **Write Solidity test contracts** (via Write tool):
   ```python
   # Vulnerable variant
   Write(
       file_path=f"tests/contracts/{category}/{subcategory}/test_{subcategory}_vulnerable.sol",
       content=vulnerable_contract,
   )

   # Safe variant
   Write(
       file_path=f"tests/contracts/{category}/{subcategory}/test_{subcategory}_safe.sol",
       content=safe_contract,
   )

   # Adversarial variant
   Write(
       file_path=f"tests/contracts/{category}/{subcategory}/test_{subcategory}_adversarial.sol",
       content=adversarial_contract,
   )

   # Edge case variant
   Write(
       file_path=f"tests/contracts/{category}/{subcategory}/test_{subcategory}_edge.sol",
       content=edge_case_contract,
   )
   ```

2. **Write test README** (via Write tool):
   ```markdown
   # Test Contracts: oracle/stale-data

   Generated from: vulndocs/oracle/stale-data/
   Patterns tested: oracle-stale-001

   ## Test Variants

   - **test_stale_data_vulnerable.sol**: Basic vulnerable pattern
   - **test_stale_data_safe.sol**: Properly mitigated
   - **test_stale_data_adversarial.sol**: Obfuscated but vulnerable
   - **test_stale_data_edge.sol**: Edge cases and boundaries

   ## Semantic Triggers

   - READS_ORACLE
   - MISSING_STALENESS_CHECK

   ## Expected Detection

   | Contract | Pattern Match | Reasoning |
   |----------|---------------|-----------|
   | Vulnerable | YES | No staleness validation |
   | Safe | NO | Validates updatedAt timestamp |
   | Adversarial | YES | Hidden oracle call without check |
   | Edge | DEPENDS | Tests pattern robustness |
   ```

3. **Write Python test file** (via Write tool):
   ```python
   Write(
       file_path=f"tests/test_{category}_{subcategory}.py",
       content=test_file,
   )
   ```

### Step 8: Update Vulndoc Test Coverage

**Goal:** Track generated tests in vulndoc metadata.

**Actions:**

1. **Read current index.yaml** (via Read tool)

2. **Update test_coverage field** (via Write tool):
   ```yaml
   test_coverage:
     contracts:
       - tests/contracts/oracle/stale-data/test_stale_data_vulnerable.sol
       - tests/contracts/oracle/stale-data/test_stale_data_safe.sol
       - tests/contracts/oracle/stale-data/test_stale_data_adversarial.sol
       - tests/contracts/oracle/stale-data/test_stale_data_edge.sol
     tests:
       - tests/test_oracle_stale_data.py
     generated: 2025-01-22T10:45:00Z
     quality_focus:
       - semantic_complexity: "Graph-based detection through helper functions"
       - real_world: "Based on Venus Protocol exploit pattern"
       - adversarial: "Misleading names, wrapped calls, fake checks"
   ```

3. **Update validation level**:
   ```yaml
   validation_level: tested  # Upgraded from documented
   ```

### Step 9: Validate Generated Tests

**Goal:** Ensure tests are valid and work correctly.

**Actions:**

1. **Build knowledge graphs** (via Bash tool):
   ```bash
   uv run alphaswarm build-kg tests/contracts/oracle/stale-data/ \
     --output /tmp/test-graph.json
   ```

2. **Run generated tests** (via Bash tool):
   ```bash
   pytest tests/test_oracle_stale_data.py -v
   ```

3. **Verify test outcomes**:
   - Vulnerable contract: Pattern matches ✅
   - Safe contract: Pattern does NOT match ✅
   - Adversarial contract: Pattern matches ✅
   - Edge case contract: Expected behavior ✅

4. **Check for compilation errors**:
   ```bash
   solc tests/contracts/oracle/stale-data/*.sol --combined-json abi
   ```

**Validation Checklist:**
- [ ] All Solidity contracts compile
- [ ] Knowledge graph builds successfully
- [ ] Python tests execute without errors
- [ ] Vulnerable variants detected
- [ ] Safe variants not detected
- [ ] Adversarial variants detected
- [ ] Comments explain semantic reasoning
- [ ] Test coverage updated in vulndoc

### Step 10: Report and Summary

**Goal:** Present test generation results to user.

**Report Format:**

```yaml
# Test Generation Report
timestamp: 2025-01-22T10:45:00Z
vulndoc: oracle/stale-data

tests_generated:
  contracts:
    - path: tests/contracts/oracle/stale-data/test_stale_data_vulnerable.sol
      lines: 87
      type: vulnerable
      expected_detection: true

    - path: tests/contracts/oracle/stale-data/test_stale_data_safe.sol
      lines: 95
      type: safe
      expected_detection: false

    - path: tests/contracts/oracle/stale-data/test_stale_data_adversarial.sol
      lines: 112
      type: adversarial
      expected_detection: true
      obfuscations: [misleading_names, wrapped_calls, fake_checks]

    - path: tests/contracts/oracle/stale-data/test_stale_data_edge.sol
      lines: 78
      type: edge_case
      expected_detection: depends

  test_file:
    path: tests/test_oracle_stale_data.py
    test_functions: 4
    assertions: 12

quality_focus:
  semantic_complexity:
    description: "Tests require graph-based reasoning to detect oracle calls through helper functions"
    challenge_level: medium

  real_world:
    description: "Derived from Venus Protocol exploit (2023)"
    real_world_patterns: 1

  adversarial:
    description: "Multiple obfuscation techniques test pattern robustness"
    obfuscation_types: 3

validation:
  compilation: passed
  knowledge_graph: built successfully
  pytest: 4/4 tests passed
  pattern_match_vulnerable: true
  pattern_match_safe: false (correct)
  pattern_match_adversarial: true

vulndoc_updated:
  test_coverage: updated
  validation_level: tested

next_steps:
  - "Run full test suite: pytest tests/test_oracle_stale_data.py -v"
  - "Add to Phase 7 test corpus"
  - "Use for pattern validation with /vrs-test-pattern"
```

---

## Key Rules

### 1. Tests Must Use Semantic Operations, Not Names
- Vulnerable function can be named anything
- Detection must work via graph properties
- Test comments explain semantic reasoning

### 2. Reasoning Template Is Source of Truth
- Parse reasoning_template from index.yaml
- Generate tests that match reasoning logic
- Validate that VQL queries align with reasoning

### 3. All Three Quality Focuses Required
- **Semantic complexity**: Graph reasoning, not name matching
- **Real-world patterns**: Derived from exploits.md
- **Adversarial**: Obfuscation to test robustness

### 4. Always Include Both Positive and Negative Tests
- Vulnerable: Pattern SHOULD match
- Safe: Pattern should NOT match
- This validates both precision and recall

### 5. Adversarial Tests Must Be Truly Challenging
- Not just variable renaming
- Structural obfuscation: wrapped calls, fake checks
- Should stress-test pattern logic

### 6. Track All Tests in Vulndoc
- Update test_coverage in index.yaml
- Link to all generated files
- Note quality focus per test

### 7. Validate Before Completion
- Compile all Solidity contracts
- Build knowledge graphs
- Run pytest to verify assertions
- Don't ship broken tests

---

## Example Invocation

```bash
# User invokes
/vrs-generate-tests oracle/stale-data

# You (Claude Code agent) execute:
1. Load vulndoc context:
   - Read: vulndocs/oracle/stale-data/index.yaml
   - Read: vulndocs/oracle/stale-data/exploits.md
   - Read: vulndocs/oracle/stale-data/detection.md
   - Glob + Read: Load patterns from vulndocs/oracle/stale-data/patterns/*.yaml

2. Parse reasoning_template:
   - Extract detection steps
   - Identify semantic operations
   - Map to graph patterns

3. Generate test contracts:
   - Write: test_stale_data_vulnerable.sol
   - Write: test_stale_data_safe.sol
   - Write: test_stale_data_adversarial.sol
   - Write: test_stale_data_edge.sol

4. Generate test file:
   - Write: tests/test_oracle_stale_data.py
   - Include 4 test functions with assertions

5. Update vulndoc:
   - Read: vulndocs/oracle/stale-data/index.yaml
   - Update test_coverage field
   - Write: updated index.yaml

6. Validate:
   - Bash: solc compile contracts
   - Bash: uv run alphaswarm build-kg
   - Bash: pytest tests/test_oracle_stale_data.py

7. Report:
   - Present test generation summary
   - Show validation results
   - Provide next steps
```

---

## Tools Reference

**CLI Commands (via Bash tool):**
```bash
uv run alphaswarm build-kg tests/contracts/oracle/stale-data/  # Build test graph
uv run alphaswarm vulndocs validate vulndocs/oracle/stale-data/  # Validate vulndoc
pytest tests/test_oracle_stale_data.py -v  # Run tests
solc tests/contracts/oracle/stale-data/*.sol --combined-json abi  # Compile
```

**File Operations:**
```python
# Read vulndoc context
Read(file_path="vulndocs/oracle/stale-data/index.yaml")
Read(file_path="vulndocs/oracle/stale-data/exploits.md")

# Write test contracts
Write(
    file_path="tests/contracts/oracle/stale-data/test_stale_data_vulnerable.sol",
    content=contract_code,
)

# Update vulndoc test coverage
Write(
    file_path="vulndocs/oracle/stale-data/index.yaml",
    content=updated_yaml,
)
```

---

## Output Locations

**Test Contracts:**
```
tests/contracts/{category}/{subcategory}/
├── test_{subcategory}_vulnerable.sol
├── test_{subcategory}_safe.sol
├── test_{subcategory}_adversarial.sol
└── test_{subcategory}_edge.sol
```

**Test Files:**
```
tests/test_{category}_{subcategory}.py
```

**Generation Report:**
```
.vrs/test-generation/report-{timestamp}.yaml
```

Present summary to user in terminal with validation results.
