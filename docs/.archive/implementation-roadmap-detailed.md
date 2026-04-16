# Semantic BSKG Implementation Roadmap

## Document Purpose

This document provides a comprehensive, phase-by-phase implementation roadmap for the
Semantic BSKG system. Each phase contains:
- Detailed task breakdowns
- Specific implementation guidance
- Acceptance criteria and tests
- Dependencies and blockers
- Estimated effort

**Total Phases:** 12
**Estimated Total Duration:** 16-20 weeks

---

## Phase 0: Foundation & Baseline Assessment

**Duration:** 1 week
**Goal:** Establish baseline metrics and prepare infrastructure for changes.
**Blockers:** None - this is the starting point.

### Task 0.1: Audit Current Pattern Name Dependencies

**Description:** Systematically analyze all existing patterns to identify which ones
depend on identifier names (variable names, function names) vs structural properties.

**Implementation:**
1. Create script `scripts/audit_pattern_names.py`:
```python
"""Audit patterns for name-based dependencies."""
import yaml
import re
from pathlib import Path

NAME_INDICATORS = [
    r'label.*matches',
    r'label.*regex',
    r'label.*contains',
    r'name.*eq',
    r'name.*in',
    r'\.\*.*\[.*\]',  # Regex patterns like .*[Oo]wner
]

def audit_pattern(pattern_path: Path) -> dict:
    """Check pattern for name dependencies."""
    with open(pattern_path) as f:
        content = f.read()
        pattern = yaml.safe_load(content)

    name_deps = []
    for indicator in NAME_INDICATORS:
        matches = re.findall(indicator, content, re.IGNORECASE)
        if matches:
            name_deps.extend(matches)

    return {
        'pattern_id': pattern.get('id'),
        'file': str(pattern_path),
        'has_name_dependency': len(name_deps) > 0,
        'name_dependencies': name_deps,
        'total_conditions': count_conditions(pattern),
    }

def main():
    patterns_dir = Path('patterns')
    results = []
    for yaml_file in patterns_dir.rglob('*.yaml'):
        results.append(audit_pattern(yaml_file))

    # Generate report
    name_dependent = [r for r in results if r['has_name_dependency']]
    print(f"Total patterns: {len(results)}")
    print(f"Name-dependent patterns: {len(name_dependent)}")
    print(f"Name-dependency rate: {len(name_dependent)/len(results)*100:.1f}%")

    for r in name_dependent:
        print(f"  - {r['pattern_id']}: {r['name_dependencies']}")
```

2. Run audit and document results in `docs/baseline-audit.md`

**Acceptance Tests:**
- [ ] Script successfully parses all patterns without errors
- [ ] Report generated showing count of name-dependent patterns
- [ ] Each name-dependent pattern identified with specific dependencies
- [ ] Baseline documented: X% of patterns depend on names

**Deliverables:**
- `scripts/audit_pattern_names.py`
- `docs/baseline-audit.md`

---

### Task 0.2: Create Renamed Test Contract Suite

**Description:** Create copies of existing vulnerable test contracts with renamed
identifiers to measure detection degradation.

**Implementation:**
1. Create directory `tests/contracts/renamed/`
2. For each vulnerable contract, create a renamed version:

```python
"""Generate renamed versions of test contracts."""
import re
from pathlib import Path

RENAMES = {
    # Standard → Non-standard
    'owner': 'controller',
    'admin': 'supervisor',
    'balances': 'userDeposits',
    'withdraw': 'removeFunds',
    'deposit': 'addFunds',
    'transfer': 'moveFunds',
    'approve': 'authorize',
    'allowance': 'permitted',
    'mint': 'create',
    'burn': 'destroy',
    'pause': 'halt',
    'unpause': 'resume',
    'upgrade': 'migrate',
    'implementation': 'logic',
    'proxy': 'forwarder',
    'initialize': 'setup',
    'onlyOwner': 'onlyController',
    'onlyAdmin': 'onlySupervisor',
}

def rename_contract(source: Path, dest: Path):
    """Create renamed version of contract."""
    content = source.read_text()

    for original, renamed in RENAMES.items():
        # Case-sensitive replace
        content = content.replace(original, renamed)
        # Also handle capitalized versions
        content = content.replace(original.capitalize(), renamed.capitalize())

    # Update contract name to include "Renamed"
    content = re.sub(
        r'contract (\w+)',
        r'contract \1Renamed',
        content
    )

    dest.write_text(content)
```

3. Create mapping file `tests/contracts/renamed/mapping.json`:
```json
{
    "ReentrancyVulnerable.sol": {
        "renamed_file": "ReentrancyVulnerableRenamed.sol",
        "renames_applied": {
            "withdraw": "removeFunds",
            "balances": "userDeposits"
        },
        "expected_detections": ["reentrancy-classic"]
    }
}
```

**Acceptance Tests:**
- [ ] At least 10 vulnerable contracts have renamed versions
- [ ] Renamed contracts compile successfully with `solc`
- [ ] Mapping file documents all renames applied
- [ ] Renamed contracts maintain same vulnerability patterns (manual verification)

**Deliverables:**
- `tests/contracts/renamed/*.sol` (10+ files)
- `tests/contracts/renamed/mapping.json`
- `scripts/generate_renamed_contracts.py`

---

### Task 0.3: Measure Baseline Detection Rate

**Description:** Run current patterns against both original and renamed contracts
to measure detection degradation.

**Implementation:**
1. Create test file `tests/test_rename_baseline.py`:
```python
"""Measure pattern detection on renamed contracts."""
import unittest
from tests.graph_cache import load_graph
from src.true_vkg.queries.patterns import PatternEngine

class RenameBaselineTests(unittest.TestCase):
    """Baseline measurement for renamed contract detection."""

    @classmethod
    def setUpClass(cls):
        cls.engine = PatternEngine()
        cls.results = {
            'original': {},
            'renamed': {},
        }

    def test_reentrancy_original(self):
        """Test reentrancy detection on original contract."""
        graph = load_graph("ReentrancyVulnerable")
        matches = self.engine.run_pattern("reentrancy-classic", graph)
        self.results['original']['reentrancy'] = len(matches)
        self.assertGreater(len(matches), 0)

    def test_reentrancy_renamed(self):
        """Test reentrancy detection on renamed contract."""
        graph = load_graph("ReentrancyVulnerableRenamed")
        matches = self.engine.run_pattern("reentrancy-classic", graph)
        self.results['renamed']['reentrancy'] = len(matches)
        # This may fail - that's the baseline we're measuring

    @classmethod
    def tearDownClass(cls):
        """Generate baseline report."""
        report = []
        for pattern in cls.results['original']:
            orig = cls.results['original'][pattern]
            renamed = cls.results['renamed'].get(pattern, 0)
            degradation = (orig - renamed) / orig * 100 if orig > 0 else 0
            report.append({
                'pattern': pattern,
                'original_matches': orig,
                'renamed_matches': renamed,
                'degradation_pct': degradation
            })

        # Write report
        with open('docs/baseline-detection-report.md', 'w') as f:
            f.write("# Baseline Detection Report\n\n")
            for r in report:
                f.write(f"- {r['pattern']}: {r['degradation_pct']:.1f}% degradation\n")
```

**Acceptance Tests:**
- [ ] Tests run successfully on both original and renamed contracts
- [ ] Degradation report generated showing % drop per pattern
- [ ] Baseline metrics documented:
  - Original detection rate: X%
  - Renamed detection rate: Y%
  - Degradation: Z%

**Deliverables:**
- `tests/test_rename_baseline.py`
- `docs/baseline-detection-report.md`

---

### Task 0.4: Set Up Performance Benchmarking

**Description:** Create infrastructure to measure build time and memory usage
for future comparison.

**Implementation:**
1. Create benchmarking module `scripts/benchmark.py`:
```python
"""Benchmark BSKG build performance."""
import time
import tracemalloc
import json
from pathlib import Path
from datetime import datetime

class Benchmark:
    def __init__(self, name: str):
        self.name = name
        self.stages = []

    def stage(self, stage_name: str):
        """Context manager for timing a stage."""
        return BenchmarkStage(self, stage_name)

    def save(self, output_path: Path):
        """Save benchmark results."""
        results = {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': sum(s['duration'] for s in self.stages),
            'peak_memory_mb': max(s['memory_mb'] for s in self.stages),
            'stages': self.stages
        }
        output_path.write_text(json.dumps(results, indent=2))

class BenchmarkStage:
    def __init__(self, benchmark, name):
        self.benchmark = benchmark
        self.name = name

    def __enter__(self):
        tracemalloc.start()
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        duration = time.perf_counter() - self.start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.benchmark.stages.append({
            'name': self.name,
            'duration': duration,
            'memory_mb': peak / 1024 / 1024
        })

# Usage in builder:
# benchmark = Benchmark("vkg-build")
# with benchmark.stage("slither_analysis"):
#     run_slither()
# with benchmark.stage("graph_construction"):
#     build_graph()
# benchmark.save(Path("benchmarks/build-baseline.json"))
```

2. Create baseline benchmark by running on test contracts

**Acceptance Tests:**
- [ ] Benchmark module correctly measures time and memory
- [ ] Baseline benchmark saved for test contract suite
- [ ] Results include per-stage breakdown (slither, graph build, etc.)

**Deliverables:**
- `scripts/benchmark.py`
- `benchmarks/baseline-YYYYMMDD.json`

---

## Phase 1: Semantic Operations Core

**Duration:** 2 weeks
**Goal:** Implement the 20 core semantic operations in the builder.
**Blockers:** Phase 0 complete (baseline established)

### Task 1.1: Define Operation Enumeration

**Description:** Create the formal enumeration of all semantic operations.

**Implementation:**
1. Create `src/true_vkg/kg/operations.py`:
```python
"""Semantic operation definitions for behavioral analysis."""
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Callable, Optional

class SemanticOperation(Enum):
    """Enumeration of all semantic operations."""

    # Value Movement
    TRANSFERS_VALUE_OUT = auto()
    RECEIVES_VALUE_IN = auto()
    READS_USER_BALANCE = auto()
    WRITES_USER_BALANCE = auto()

    # Access Control
    CHECKS_PERMISSION = auto()
    MODIFIES_OWNER = auto()
    MODIFIES_ROLES = auto()

    # External Interaction
    CALLS_EXTERNAL = auto()
    CALLS_UNTRUSTED = auto()
    READS_EXTERNAL_VALUE = auto()

    # State Management
    MODIFIES_CRITICAL_STATE = auto()
    INITIALIZES_STATE = auto()
    READS_ORACLE = auto()

    # Control Flow
    LOOPS_OVER_ARRAY = auto()
    USES_TIMESTAMP = auto()
    USES_BLOCK_DATA = auto()

    # Arithmetic
    PERFORMS_DIVISION = auto()
    PERFORMS_MULTIPLICATION = auto()

    # Validation
    VALIDATES_INPUT = auto()
    EMITS_EVENT = auto()


@dataclass
class OperationDefinition:
    """Definition of how to detect an operation."""
    operation: SemanticOperation
    description: str
    detection_logic: str  # Human-readable description
    detector: Callable  # Actual detection function


OPERATION_DEFINITIONS: List[OperationDefinition] = [
    OperationDefinition(
        operation=SemanticOperation.TRANSFERS_VALUE_OUT,
        description="Sends ETH or tokens to external address",
        detection_logic="Has transfer(), send(), call{value}, or token transfer",
        detector=None,  # Implemented in Task 1.2
    ),
    # ... all 20 operations
]
```

**Acceptance Tests:**
- [ ] All 20 operations defined in enum
- [ ] Each operation has description and detection_logic documented
- [ ] Enum can be serialized to/from string for storage
- [ ] Unit test verifies enum completeness

**Deliverables:**
- `src/true_vkg/kg/operations.py`
- `tests/test_operations.py` (enum tests)

---

### Task 1.2: Implement Operation Detectors (Value Movement)

**Description:** Implement detectors for the 4 value movement operations.

**Implementation:**
1. Add to `src/true_vkg/kg/operations.py`:
```python
"""Detectors for value movement operations."""
from slither.core.declarations import Function
from slither.slithir.operations import (
    Transfer, Send, LowLevelCall, HighLevelCall,
    InternalCall, SolidityCall
)

def detect_transfers_value_out(function: Function) -> bool:
    """Detect if function transfers ETH or tokens out."""
    for node in function.nodes:
        for ir in node.irs:
            # ETH transfers
            if isinstance(ir, (Transfer, Send)):
                return True
            if isinstance(ir, LowLevelCall) and ir.call_value:
                return True

            # Token transfers (ERC20)
            if isinstance(ir, HighLevelCall):
                if ir.function_name in ('transfer', 'transferFrom', 'safeTransfer'):
                    # Check if transferring OUT (not receiving)
                    # This requires analyzing the arguments
                    if is_outgoing_transfer(ir, function):
                        return True
    return False


def detect_receives_value_in(function: Function) -> bool:
    """Detect if function receives ETH or tokens."""
    # Check payable modifier
    if function.payable:
        return True

    # Check for token receipt patterns
    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, HighLevelCall):
                if ir.function_name in ('transferFrom', 'safeTransferFrom'):
                    # Check if receiving (to == this contract)
                    if is_incoming_transfer(ir, function):
                        return True
    return False


def detect_reads_user_balance(function: Function) -> bool:
    """Detect if function reads a user-keyed balance mapping."""
    for node in function.nodes:
        for ir in node.irs:
            # Look for mapping reads where key is msg.sender or address param
            if is_mapping_read(ir):
                mapping_var = get_mapping_variable(ir)
                if is_user_keyed_mapping(mapping_var, function):
                    return True
    return False


def detect_writes_user_balance(function: Function) -> bool:
    """Detect if function writes to a user-keyed balance mapping."""
    for node in function.nodes:
        for ir in node.irs:
            if is_mapping_write(ir):
                mapping_var = get_mapping_variable(ir)
                if is_user_keyed_mapping(mapping_var, function):
                    return True
    return False


def is_user_keyed_mapping(var, function: Function) -> bool:
    """Check if mapping is keyed by user address."""
    # Check if mapping type is address => X
    if not hasattr(var, 'type') or not hasattr(var.type, 'type_from'):
        return False

    from_type = str(var.type.type_from)
    if from_type != 'address':
        return False

    # Check usage patterns - is key msg.sender or parameter?
    # This requires dataflow analysis
    return True  # Simplified - full implementation needs taint tracking
```

**Acceptance Tests:**
```python
class TestValueMovementOperations(unittest.TestCase):
    """Test value movement operation detection."""

    def test_transfers_value_out_eth_transfer(self):
        """Detect ETH transfer via transfer()."""
        graph = load_graph("ValueMovementTokens")
        func = get_function(graph, "withdrawETH")
        self.assertTrue(detect_transfers_value_out(func))

    def test_transfers_value_out_token(self):
        """Detect ERC20 token transfer."""
        graph = load_graph("ValueMovementTokens")
        func = get_function(graph, "withdrawTokens")
        self.assertTrue(detect_transfers_value_out(func))

    def test_no_transfer_internal_only(self):
        """Internal function without transfers."""
        graph = load_graph("ValueMovementTokens")
        func = get_function(graph, "_calculateFee")
        self.assertFalse(detect_transfers_value_out(func))

    def test_receives_value_payable(self):
        """Detect payable function receives value."""
        graph = load_graph("ValueMovementTokens")
        func = get_function(graph, "deposit")
        self.assertTrue(detect_receives_value_in(func))

    def test_reads_user_balance(self):
        """Detect reading balances[msg.sender]."""
        graph = load_graph("ReentrancyVulnerable")
        func = get_function(graph, "withdraw")
        self.assertTrue(detect_reads_user_balance(func))

    def test_writes_user_balance(self):
        """Detect writing balances[msg.sender]."""
        graph = load_graph("ReentrancyVulnerable")
        func = get_function(graph, "withdraw")
        self.assertTrue(detect_writes_user_balance(func))
```

- [ ] All 4 value movement detectors implemented
- [ ] Each detector has at least 3 test cases (positive, negative, edge case)
- [ ] Detectors handle both ETH and ERC20 patterns
- [ ] False positive rate < 10% on test suite

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_value_movement.py`

---

### Task 1.3: Implement Operation Detectors (Access Control)

**Description:** Implement detectors for the 3 access control operations.

**Implementation:**
```python
"""Detectors for access control operations."""

def detect_checks_permission(function: Function) -> bool:
    """Detect if function verifies caller authorization."""
    # Check for access control modifiers
    for modifier in function.modifiers:
        modifier_name = modifier.name.lower()
        if any(kw in modifier_name for kw in ['only', 'auth', 'require', 'check']):
            return True

    # Check for inline msg.sender comparisons
    for node in function.nodes:
        if node.contains_require_or_assert():
            # Check if require/assert involves msg.sender
            for ir in node.irs:
                if involves_msg_sender_comparison(ir):
                    return True

    return False


def detect_modifies_owner(function: Function) -> bool:
    """Detect if function modifies ownership."""
    owner_patterns = ['owner', 'admin', 'controller', 'governance']

    for node in function.nodes:
        for ir in node.irs:
            if is_state_write(ir):
                var_name = get_written_variable_name(ir).lower()
                if any(pattern in var_name for pattern in owner_patterns):
                    return True
    return False


def detect_modifies_roles(function: Function) -> bool:
    """Detect if function modifies role assignments."""
    for node in function.nodes:
        for ir in node.irs:
            if is_mapping_write(ir):
                mapping_var = get_mapping_variable(ir)
                # Check if it's a role mapping (address => bool) or similar
                if is_role_mapping(mapping_var):
                    return True
    return False


def involves_msg_sender_comparison(ir) -> bool:
    """Check if IR involves comparing msg.sender."""
    # Look for: msg.sender == X, X == msg.sender, require(msg.sender == owner)
    from slither.slithir.operations import Binary, Condition
    from slither.slithir.variables import Constant

    if isinstance(ir, (Binary, Condition)):
        operands = [ir.variable_left, ir.variable_right] if hasattr(ir, 'variable_left') else []
        for op in operands:
            if str(op) == 'msg.sender':
                return True
    return False
```

**Acceptance Tests:**
```python
class TestAccessControlOperations(unittest.TestCase):
    """Test access control operation detection."""

    def test_checks_permission_modifier(self):
        """Detect onlyOwner modifier."""
        graph = load_graph("AccessControl")
        func = get_function(graph, "adminFunction")
        self.assertTrue(detect_checks_permission(func))

    def test_checks_permission_inline(self):
        """Detect inline require(msg.sender == owner)."""
        graph = load_graph("AccessControl")
        func = get_function(graph, "inlineAuthFunction")
        self.assertTrue(detect_checks_permission(func))

    def test_no_permission_check(self):
        """Public function without auth."""
        graph = load_graph("MissingAuthVulnerable")
        func = get_function(graph, "withdraw")
        self.assertFalse(detect_checks_permission(func))

    def test_modifies_owner(self):
        """Detect transferOwnership."""
        graph = load_graph("AccessControl")
        func = get_function(graph, "transferOwnership")
        self.assertTrue(detect_modifies_owner(func))

    def test_modifies_roles_mapping(self):
        """Detect role mapping modification."""
        graph = load_graph("RoleBasedAccess")
        func = get_function(graph, "grantRole")
        self.assertTrue(detect_modifies_roles(func))
```

- [ ] All 3 access control detectors implemented
- [ ] Handles both modifier-based and inline auth checks
- [ ] Detects common ownership patterns regardless of naming
- [ ] Each detector has 3+ test cases

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_access_control.py`

---

### Task 1.4: Implement Operation Detectors (External Interaction)

**Description:** Implement detectors for the 3 external interaction operations.

**Implementation:**
```python
"""Detectors for external interaction operations."""

def detect_calls_external(function: Function) -> bool:
    """Detect if function makes any external call."""
    return (
        function.external_calls_as_expressions or
        has_low_level_calls(function)
    )


def detect_calls_untrusted(function: Function) -> bool:
    """Detect if function calls user-controlled address."""
    for node in function.nodes:
        for ir in node.irs:
            # delegatecall is always potentially untrusted
            if isinstance(ir, LowLevelCall) and ir.function_name == 'delegatecall':
                return True

            # call/staticcall to non-constant address
            if isinstance(ir, LowLevelCall):
                target = ir.destination
                if not is_constant_address(target, function):
                    return True

            # High-level call to parameter address
            if isinstance(ir, HighLevelCall):
                if is_parameter_derived(ir.destination, function):
                    return True

    return False


def detect_reads_external_value(function: Function) -> bool:
    """Detect if function uses return value from external call."""
    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, (HighLevelCall, LowLevelCall)):
                # Check if return value is used
                if ir.lvalue and is_value_used_after(ir.lvalue, node, function):
                    return True
    return False


def is_constant_address(target, function: Function) -> bool:
    """Check if target address is a compile-time constant."""
    # Constant addresses
    if hasattr(target, 'value') and isinstance(target.value, str):
        return True  # Literal address

    # Immutable state variables
    if hasattr(target, 'is_immutable') and target.is_immutable:
        return True

    # State variable that's never written (effectively constant)
    if is_readonly_state_var(target, function.contract):
        return True

    return False
```

**Acceptance Tests:**
```python
class TestExternalInteractionOperations(unittest.TestCase):
    """Test external interaction operation detection."""

    def test_calls_external_high_level(self):
        """Detect high-level external call."""
        graph = load_graph("ExternalCalls")
        func = get_function(graph, "callOtherContract")
        self.assertTrue(detect_calls_external(func))

    def test_calls_external_low_level(self):
        """Detect low-level call."""
        graph = load_graph("ExternalCalls")
        func = get_function(graph, "lowLevelCall")
        self.assertTrue(detect_calls_external(func))

    def test_calls_untrusted_delegatecall(self):
        """Detect delegatecall as untrusted."""
        graph = load_graph("DelegatecallVulnerable")
        func = get_function(graph, "delegate")
        self.assertTrue(detect_calls_untrusted(func))

    def test_calls_untrusted_param_address(self):
        """Detect call to parameter address."""
        graph = load_graph("ExternalCalls")
        func = get_function(graph, "callArbitraryAddress")
        self.assertTrue(detect_calls_untrusted(func))

    def test_trusted_immutable_address(self):
        """Call to immutable address is trusted."""
        graph = load_graph("ExternalCalls")
        func = get_function(graph, "callImmutableContract")
        self.assertFalse(detect_calls_untrusted(func))

    def test_reads_external_value(self):
        """Detect using external call return value."""
        graph = load_graph("OracleCalls")
        func = get_function(graph, "getPrice")
        self.assertTrue(detect_reads_external_value(func))
```

- [ ] All 3 external interaction detectors implemented
- [ ] Correctly distinguishes trusted vs untrusted call targets
- [ ] Handles both high-level and low-level calls
- [ ] Each detector has 3+ test cases

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_external.py`

---

### Task 1.5: Implement Operation Detectors (State Management)

**Description:** Implement detectors for the 3 state management operations.

**Implementation:**
```python
"""Detectors for state management operations."""

CRITICAL_STATE_PATTERNS = [
    'owner', 'admin', 'implementation', 'beacon', 'proxy',
    'paused', 'frozen', 'emergency', 'fee', 'rate',
    'treasury', 'vault', 'governance', 'timelock'
]


def detect_modifies_critical_state(function: Function) -> bool:
    """Detect if function modifies privileged state variables."""
    for node in function.nodes:
        for ir in node.irs:
            if is_state_write(ir):
                var = get_written_variable(ir)

                # Check by name pattern
                var_name = var.name.lower() if hasattr(var, 'name') else ''
                if any(p in var_name for p in CRITICAL_STATE_PATTERNS):
                    return True

                # Check by storage slot (EIP-1967)
                if is_eip1967_slot(var):
                    return True

                # Check by type (address that controls behavior)
                if is_controller_type_variable(var):
                    return True

    return False


def detect_initializes_state(function: Function) -> bool:
    """Detect if function is an initializer."""
    # Check for initializer patterns
    func_name = function.name.lower()
    if any(p in func_name for p in ['init', 'setup', 'configure']):
        # Verify it writes state
        if has_state_writes(function):
            return True

    # Check for initializer modifier
    for modifier in function.modifiers:
        if 'initializer' in modifier.name.lower():
            return True

    # Check for constructor-like guard pattern
    # require(!initialized); initialized = true;
    if has_initialization_guard(function):
        return True

    return False


def detect_reads_oracle(function: Function) -> bool:
    """Detect if function reads from price oracle."""
    oracle_patterns = [
        'latestRoundData', 'latestAnswer', 'getPrice',
        'consult', 'observe', 'slot0', 'getReserves'
    ]

    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, HighLevelCall):
                if ir.function_name in oracle_patterns:
                    return True

                # Check interface type
                if is_oracle_interface(ir.destination):
                    return True

    return False


def is_eip1967_slot(var) -> bool:
    """Check if variable uses EIP-1967 storage slot."""
    eip1967_slots = [
        '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc',  # impl
        '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103',  # admin
        '0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50',  # beacon
    ]
    # Check if variable is stored at one of these slots
    if hasattr(var, 'slot') and var.slot in eip1967_slots:
        return True
    return False
```

**Acceptance Tests:**
```python
class TestStateManagementOperations(unittest.TestCase):
    """Test state management operation detection."""

    def test_modifies_critical_owner(self):
        """Detect owner modification."""
        graph = load_graph("AccessControl")
        func = get_function(graph, "transferOwnership")
        self.assertTrue(detect_modifies_critical_state(func))

    def test_modifies_critical_implementation(self):
        """Detect implementation slot modification."""
        graph = load_graph("ProxyTypes")
        func = get_function(graph, "upgradeTo")
        self.assertTrue(detect_modifies_critical_state(func))

    def test_modifies_non_critical(self):
        """Regular state update is not critical."""
        graph = load_graph("ValueMovementTokens")
        func = get_function(graph, "deposit")
        self.assertFalse(detect_modifies_critical_state(func))

    def test_initializes_with_modifier(self):
        """Detect initializer modifier."""
        graph = load_graph("InitializerVulnerable")
        func = get_function(graph, "initialize")
        self.assertTrue(detect_initializes_state(func))

    def test_initializes_with_guard(self):
        """Detect initialization guard pattern."""
        graph = load_graph("InitializerGuard")
        func = get_function(graph, "setup")
        self.assertTrue(detect_initializes_state(func))

    def test_reads_oracle_chainlink(self):
        """Detect Chainlink oracle read."""
        graph = load_graph("OracleCalls")
        func = get_function(graph, "getLatestPrice")
        self.assertTrue(detect_reads_oracle(func))

    def test_reads_oracle_uniswap(self):
        """Detect Uniswap TWAP read."""
        graph = load_graph("UniswapOracle")
        func = get_function(graph, "consultPrice")
        self.assertTrue(detect_reads_oracle(func))
```

- [ ] All 3 state management detectors implemented
- [ ] Handles EIP-1967 slot detection
- [ ] Recognizes common oracle interfaces
- [ ] Each detector has 3+ test cases

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_state.py`

---

### Task 1.6: Implement Operation Detectors (Control Flow)

**Description:** Implement detectors for the 3 control flow operations.

**Implementation:**
```python
"""Detectors for control flow operations."""

def detect_loops_over_array(function: Function) -> bool:
    """Detect if function loops over dynamic array."""
    for node in function.nodes:
        if node.type in [NodeType.STARTLOOP, NodeType.IFLOOP]:
            # Check loop bound
            bound = get_loop_bound(node)
            if bound and is_array_length(bound):
                return True
    return False


def detect_uses_timestamp(function: Function) -> bool:
    """Detect if function uses block.timestamp."""
    for node in function.nodes:
        for ir in node.irs:
            # Check for block.timestamp read
            if references_solidity_variable(ir, 'block.timestamp'):
                return True
            # Also check 'now' (deprecated alias)
            if references_solidity_variable(ir, 'now'):
                return True
    return False


def detect_uses_block_data(function: Function) -> bool:
    """Detect if function uses block data (number, hash, etc.)."""
    block_vars = [
        'block.number', 'block.difficulty', 'block.prevrandao',
        'block.gaslimit', 'block.coinbase', 'blockhash'
    ]
    for node in function.nodes:
        for ir in node.irs:
            for var in block_vars:
                if references_solidity_variable(ir, var):
                    return True
    return False


def get_loop_bound(node) -> Optional[Any]:
    """Extract the bound expression from a loop node."""
    # Parse loop condition to find upper bound
    # For: for(i=0; i < arr.length; i++)
    # Return: arr.length
    if hasattr(node, 'condition'):
        return extract_comparison_operand(node.condition)
    return None


def is_array_length(expr) -> bool:
    """Check if expression is an array.length access."""
    if hasattr(expr, 'member_name') and expr.member_name == 'length':
        return True
    return False
```

**Acceptance Tests:**
```python
class TestControlFlowOperations(unittest.TestCase):
    """Test control flow operation detection."""

    def test_loops_over_array(self):
        """Detect for loop over array."""
        graph = load_graph("UnboundedLoop")
        func = get_function(graph, "processAll")
        self.assertTrue(detect_loops_over_array(func))

    def test_no_loop(self):
        """Function without loops."""
        graph = load_graph("SimpleContract")
        func = get_function(graph, "getValue")
        self.assertFalse(detect_loops_over_array(func))

    def test_fixed_bound_loop(self):
        """Loop with fixed bound is not flagged."""
        graph = load_graph("FixedLoop")
        func = get_function(graph, "processFixed")
        # Fixed bound loops (for i=0; i<10; i++) are not array loops
        self.assertFalse(detect_loops_over_array(func))

    def test_uses_timestamp(self):
        """Detect block.timestamp usage."""
        graph = load_graph("TimestampUsage")
        func = get_function(graph, "isExpired")
        self.assertTrue(detect_uses_timestamp(func))

    def test_uses_block_number(self):
        """Detect block.number usage."""
        graph = load_graph("BlockDataUsage")
        func = get_function(graph, "getBlockNumber")
        self.assertTrue(detect_uses_block_data(func))
```

- [ ] All 3 control flow detectors implemented
- [ ] Correctly identifies array-bounded loops
- [ ] Handles all block data variants
- [ ] Each detector has 3+ test cases

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_control_flow.py`

---

### Task 1.7: Implement Operation Detectors (Arithmetic + Validation)

**Description:** Implement detectors for the remaining 4 operations.

**Implementation:**
```python
"""Detectors for arithmetic and validation operations."""

def detect_performs_division(function: Function) -> bool:
    """Detect if function performs division."""
    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, Binary) and ir.type == BinaryType.DIVISION:
                return True
    return False


def detect_performs_multiplication(function: Function) -> bool:
    """Detect if function performs multiplication."""
    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, Binary) and ir.type == BinaryType.MULTIPLICATION:
                return True
    return False


def detect_validates_input(function: Function) -> bool:
    """Detect if function validates its parameters."""
    params = {p.name for p in function.parameters}

    for node in function.nodes:
        if node.contains_require_or_assert():
            # Check if require/assert references a parameter
            for ir in node.irs:
                referenced_vars = get_referenced_variables(ir)
                if any(v.name in params for v in referenced_vars if hasattr(v, 'name')):
                    return True
    return False


def detect_emits_event(function: Function) -> bool:
    """Detect if function emits an event."""
    for node in function.nodes:
        for ir in node.irs:
            if isinstance(ir, EventCall):
                return True
    return False
```

**Acceptance Tests:**
```python
class TestArithmeticValidationOperations(unittest.TestCase):
    """Test arithmetic and validation operation detection."""

    def test_performs_division(self):
        """Detect division operation."""
        graph = load_graph("ArithmeticLens")
        func = get_function(graph, "divide")
        self.assertTrue(detect_performs_division(func))

    def test_performs_multiplication(self):
        """Detect multiplication operation."""
        graph = load_graph("ArithmeticLens")
        func = get_function(graph, "multiply")
        self.assertTrue(detect_performs_multiplication(func))

    def test_validates_input(self):
        """Detect parameter validation."""
        graph = load_graph("InputValidation")
        func = get_function(graph, "setAmount")
        self.assertTrue(detect_validates_input(func))

    def test_no_validation(self):
        """Function without input validation."""
        graph = load_graph("NoValidation")
        func = get_function(graph, "unsafeSet")
        self.assertFalse(detect_validates_input(func))

    def test_emits_event(self):
        """Detect event emission."""
        graph = load_graph("Events")
        func = get_function(graph, "transfer")
        self.assertTrue(detect_emits_event(func))
```

- [ ] All 4 remaining detectors implemented
- [ ] Each detector has 2+ test cases
- [ ] Arithmetic detectors work with Solidity 0.8+ checked math

**Deliverables:**
- Updated `src/true_vkg/kg/operations.py`
- `tests/test_operations_arithmetic.py`

---

### Task 1.8: Integrate Operations into Builder

**Description:** Add operation detection to the BSKG builder pipeline.

**Implementation:**
1. Update `src/true_vkg/kg/builder.py`:
```python
"""Integration of semantic operations into BSKG builder."""

from .operations import (
    SemanticOperation, detect_transfers_value_out, detect_receives_value_in,
    # ... all detectors
)

OPERATION_DETECTORS = {
    SemanticOperation.TRANSFERS_VALUE_OUT: detect_transfers_value_out,
    SemanticOperation.RECEIVES_VALUE_IN: detect_receives_value_in,
    SemanticOperation.READS_USER_BALANCE: detect_reads_user_balance,
    SemanticOperation.WRITES_USER_BALANCE: detect_writes_user_balance,
    SemanticOperation.CHECKS_PERMISSION: detect_checks_permission,
    SemanticOperation.MODIFIES_OWNER: detect_modifies_owner,
    SemanticOperation.MODIFIES_ROLES: detect_modifies_roles,
    SemanticOperation.CALLS_EXTERNAL: detect_calls_external,
    SemanticOperation.CALLS_UNTRUSTED: detect_calls_untrusted,
    SemanticOperation.READS_EXTERNAL_VALUE: detect_reads_external_value,
    SemanticOperation.MODIFIES_CRITICAL_STATE: detect_modifies_critical_state,
    SemanticOperation.INITIALIZES_STATE: detect_initializes_state,
    SemanticOperation.READS_ORACLE: detect_reads_oracle,
    SemanticOperation.LOOPS_OVER_ARRAY: detect_loops_over_array,
    SemanticOperation.USES_TIMESTAMP: detect_uses_timestamp,
    SemanticOperation.USES_BLOCK_DATA: detect_uses_block_data,
    SemanticOperation.PERFORMS_DIVISION: detect_performs_division,
    SemanticOperation.PERFORMS_MULTIPLICATION: detect_performs_multiplication,
    SemanticOperation.VALIDATES_INPUT: detect_validates_input,
    SemanticOperation.EMITS_EVENT: detect_emits_event,
}


def derive_semantic_operations(slither_function) -> List[str]:
    """Derive all semantic operations for a function."""
    operations = []
    for op, detector in OPERATION_DETECTORS.items():
        try:
            if detector(slither_function):
                operations.append(op.name)
        except Exception as e:
            logger.warning(f"Operation detection failed for {op.name}: {e}")
    return operations


class VKGBuilder:
    def _build_function_node(self, func, contract_node):
        """Build function node with semantic operations."""
        # ... existing code ...

        # NEW: Add semantic operations
        function_node.properties['semantic_ops'] = derive_semantic_operations(func)

        # ... rest of existing code ...
```

2. Update schema in `src/true_vkg/kg/schema.py`:
```python
@dataclass
class FunctionNode(Node):
    # ... existing fields ...

    # NEW: Semantic operations
    semantic_ops: List[str] = field(default_factory=list)
```

**Acceptance Tests:**
```python
class TestBuilderOperationIntegration(unittest.TestCase):
    """Test operation integration in builder."""

    def test_function_has_semantic_ops(self):
        """Built function node has semantic_ops property."""
        graph = load_graph("ReentrancyVulnerable")
        func_node = get_function_node(graph, "withdraw")
        self.assertIn('semantic_ops', func_node.properties)
        self.assertIsInstance(func_node.properties['semantic_ops'], list)

    def test_withdraw_operations(self):
        """Withdraw function has expected operations."""
        graph = load_graph("ReentrancyVulnerable")
        func_node = get_function_node(graph, "withdraw")
        ops = func_node.properties['semantic_ops']

        self.assertIn('READS_USER_BALANCE', ops)
        self.assertIn('TRANSFERS_VALUE_OUT', ops)
        self.assertIn('WRITES_USER_BALANCE', ops)

    def test_operations_serialization(self):
        """Operations serialize/deserialize correctly."""
        graph = load_graph("ReentrancyVulnerable")
        serialized = graph.to_json()
        restored = KnowledgeGraph.from_json(serialized)

        original_ops = get_function_node(graph, "withdraw").properties['semantic_ops']
        restored_ops = get_function_node(restored, "withdraw").properties['semantic_ops']

        self.assertEqual(original_ops, restored_ops)

    def test_all_functions_have_operations(self):
        """All function nodes have semantic_ops (may be empty)."""
        graph = load_graph("ReentrancyVulnerable")
        for node in graph.nodes:
            if node.type == 'Function':
                self.assertIn('semantic_ops', node.properties)
```

- [ ] Builder adds semantic_ops to all function nodes
- [ ] Operations persist through serialization/deserialization
- [ ] Build time increase < 20% (benchmark against baseline)
- [ ] No exceptions thrown for any test contract

**Deliverables:**
- Updated `src/true_vkg/kg/builder.py`
- Updated `src/true_vkg/kg/schema.py`
- `tests/test_builder_operations.py`

---

## Phase 2: Operation Sequencing

**Duration:** 1.5 weeks
**Goal:** Add temporal ordering to operations.
**Blockers:** Phase 1 complete (all operations implemented)

### Task 2.1: Implement CFG Traversal for Ordering

**Description:** Extract operation ordering from control flow graph.

**Implementation:**
```python
"""Extract operation ordering from CFG."""
from typing import List, Tuple
from collections import defaultdict

@dataclass
class OperationOccurrence:
    """Single occurrence of an operation in code."""
    operation: str
    cfg_order: int  # Order in CFG traversal
    node_id: int    # Slither node ID
    line_number: int


def extract_operation_sequence(function) -> List[OperationOccurrence]:
    """Extract all operations with their CFG ordering."""
    occurrences = []
    order = 0

    # Traverse CFG in execution order
    for node in function.nodes:
        node_ops = detect_operations_at_node(node)
        for op in node_ops:
            occurrences.append(OperationOccurrence(
                operation=op,
                cfg_order=order,
                node_id=node.node_id,
                line_number=node.source_mapping.lines[0] if node.source_mapping else 0
            ))
        if node_ops:
            order += 1

    return occurrences


def detect_operations_at_node(node) -> List[str]:
    """Detect which operations occur at a specific CFG node."""
    operations = []

    for ir in node.irs:
        # Check each operation type
        if is_external_call(ir):
            operations.append('CALLS_EXTERNAL')
            if is_value_transfer(ir):
                operations.append('TRANSFERS_VALUE_OUT')

        if is_state_read(ir) and is_user_balance_var(ir):
            operations.append('READS_USER_BALANCE')

        if is_state_write(ir) and is_user_balance_var(ir):
            operations.append('WRITES_USER_BALANCE')

        # ... check other operations

    return operations


def compute_operation_ordering(sequence: List[OperationOccurrence]) -> List[Tuple[str, str]]:
    """Compute before/after relationships between operations."""
    ordering = []

    for i, op1 in enumerate(sequence):
        for op2 in sequence[i+1:]:
            if op1.cfg_order < op2.cfg_order:
                ordering.append((op1.operation, op2.operation))

    return ordering
```

**Acceptance Tests:**
```python
class TestOperationSequencing(unittest.TestCase):
    """Test operation sequence extraction."""

    def test_reentrancy_sequence(self):
        """Vulnerable withdrawal has external call before state update."""
        func = get_slither_function("ReentrancyVulnerable", "withdraw")
        sequence = extract_operation_sequence(func)

        # Find positions
        transfer_pos = next(o.cfg_order for o in sequence if o.operation == 'TRANSFERS_VALUE_OUT')
        write_pos = next(o.cfg_order for o in sequence if o.operation == 'WRITES_USER_BALANCE')

        # External call should come BEFORE state update (vulnerable)
        self.assertLess(transfer_pos, write_pos)

    def test_safe_withdrawal_sequence(self):
        """Safe withdrawal has state update before external call."""
        func = get_slither_function("ReentrancySafe", "withdraw")
        sequence = extract_operation_sequence(func)

        transfer_pos = next(o.cfg_order for o in sequence if o.operation == 'TRANSFERS_VALUE_OUT')
        write_pos = next(o.cfg_order for o in sequence if o.operation == 'WRITES_USER_BALANCE')

        # State update should come BEFORE external call (safe)
        self.assertLess(write_pos, transfer_pos)

    def test_ordering_relationships(self):
        """Compute before/after relationships."""
        func = get_slither_function("ReentrancyVulnerable", "withdraw")
        sequence = extract_operation_sequence(func)
        ordering = compute_operation_ordering(sequence)

        # Should have (TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE) meaning transfer before write
        self.assertIn(('TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE'), ordering)
```

- [ ] Sequence extraction follows CFG order correctly
- [ ] Handles branching (if/else) appropriately
- [ ] Handles loops (operations inside loops)
- [ ] Ordering relationships computed correctly

**Deliverables:**
- `src/true_vkg/kg/sequencing.py`
- `tests/test_sequencing.py`

---

### Task 2.2: Add Sequence to Function Nodes

**Description:** Store operation sequence on function nodes.

**Implementation:**
1. Update schema:
```python
@dataclass
class FunctionNode(Node):
    # Existing
    semantic_ops: List[str] = field(default_factory=list)

    # NEW: Operation sequence with ordering
    op_sequence: List[Dict] = field(default_factory=list)
    # Format: [{"op": "READS_USER_BALANCE", "order": 0}, ...]

    # NEW: Before/after relationships
    op_ordering: List[Tuple[str, str]] = field(default_factory=list)
    # Format: [("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"), ...]
```

2. Update builder:
```python
def _build_function_node(self, func, contract_node):
    # ... existing code ...

    # Derive operations
    function_node.properties['semantic_ops'] = derive_semantic_operations(func)

    # NEW: Extract sequence
    sequence = extract_operation_sequence(func)
    function_node.properties['op_sequence'] = [
        {'op': occ.operation, 'order': occ.cfg_order, 'line': occ.line_number}
        for occ in sequence
    ]

    # NEW: Compute ordering relationships
    function_node.properties['op_ordering'] = compute_operation_ordering(sequence)
```

**Acceptance Tests:**
- [ ] op_sequence stored on all function nodes
- [ ] op_ordering contains correct before/after pairs
- [ ] Serialization preserves sequence and ordering
- [ ] Build time increase < 10% from Phase 1

**Deliverables:**
- Updated `src/true_vkg/kg/schema.py`
- Updated `src/true_vkg/kg/builder.py`
- `tests/test_builder_sequencing.py`

---

### Task 2.3: Compute Behavioral Signature

**Description:** Create canonical signature from operation sequence.

**Implementation:**
```python
"""Behavioral signature computation."""

# Short codes for operations
OP_CODES = {
    'TRANSFERS_VALUE_OUT': 'X:out',
    'RECEIVES_VALUE_IN': 'X:in',
    'READS_USER_BALANCE': 'R:bal',
    'WRITES_USER_BALANCE': 'W:bal',
    'CHECKS_PERMISSION': 'C:auth',
    'MODIFIES_OWNER': 'W:own',
    'MODIFIES_ROLES': 'W:role',
    'CALLS_EXTERNAL': 'X:call',
    'CALLS_UNTRUSTED': 'X:untrust',
    'READS_EXTERNAL_VALUE': 'R:ext',
    'MODIFIES_CRITICAL_STATE': 'W:crit',
    'INITIALIZES_STATE': 'W:init',
    'READS_ORACLE': 'R:oracle',
    'LOOPS_OVER_ARRAY': 'L:arr',
    'USES_TIMESTAMP': 'R:time',
    'USES_BLOCK_DATA': 'R:block',
    'PERFORMS_DIVISION': 'A:div',
    'PERFORMS_MULTIPLICATION': 'A:mul',
    'VALIDATES_INPUT': 'V:input',
    'EMITS_EVENT': 'E:event',
}


def compute_behavioral_signature(op_sequence: List[Dict]) -> str:
    """Create canonical signature from operation sequence."""
    if not op_sequence:
        return ""

    # Sort by order
    sorted_ops = sorted(op_sequence, key=lambda x: x['order'])

    # Map to short codes, deduplicate consecutive same ops
    codes = []
    prev_code = None
    for op_info in sorted_ops:
        code = OP_CODES.get(op_info['op'])
        if code and code != prev_code:
            codes.append(code)
            prev_code = code

    return '→'.join(codes)


# Example signatures:
# Vulnerable withdrawal: "R:bal→X:out→W:bal"
# Safe withdrawal: "R:bal→W:bal→X:out"
# Protected admin: "C:auth→W:crit"
# Unprotected admin: "W:crit"
```

**Acceptance Tests:**
```python
class TestBehavioralSignature(unittest.TestCase):
    """Test behavioral signature computation."""

    def test_reentrancy_vulnerable_signature(self):
        """Vulnerable withdrawal has read→external→write signature."""
        graph = load_graph("ReentrancyVulnerable")
        func = get_function_node(graph, "withdraw")
        sig = func.properties['behavioral_signature']

        # External call (X:out) comes before write (W:bal)
        self.assertIn('X:out', sig)
        self.assertIn('W:bal', sig)
        self.assertLess(sig.index('X:out'), sig.index('W:bal'))

    def test_reentrancy_safe_signature(self):
        """Safe withdrawal has read→write→external signature."""
        graph = load_graph("ReentrancySafe")
        func = get_function_node(graph, "withdraw")
        sig = func.properties['behavioral_signature']

        # Write (W:bal) comes before external (X:out)
        self.assertIn('W:bal', sig)
        self.assertIn('X:out', sig)
        self.assertLess(sig.index('W:bal'), sig.index('X:out'))

    def test_protected_admin_signature(self):
        """Protected admin function has auth check first."""
        graph = load_graph("AccessControl")
        func = get_function_node(graph, "setOwner")
        sig = func.properties['behavioral_signature']

        self.assertTrue(sig.startswith('C:auth'))

    def test_unprotected_admin_signature(self):
        """Unprotected admin function lacks auth check."""
        graph = load_graph("MissingAuthVulnerable")
        func = get_function_node(graph, "setOwner")
        sig = func.properties['behavioral_signature']

        self.assertNotIn('C:auth', sig)
        self.assertIn('W:', sig)  # Has some write

    def test_signature_determinism(self):
        """Same function always produces same signature."""
        sig1 = compute_behavioral_signature([
            {'op': 'READS_USER_BALANCE', 'order': 0},
            {'op': 'TRANSFERS_VALUE_OUT', 'order': 1},
        ])
        sig2 = compute_behavioral_signature([
            {'op': 'READS_USER_BALANCE', 'order': 0},
            {'op': 'TRANSFERS_VALUE_OUT', 'order': 1},
        ])
        self.assertEqual(sig1, sig2)
```

- [ ] Signature computed for all functions
- [ ] Signatures are deterministic (same input = same output)
- [ ] Signatures distinguish vulnerable from safe patterns
- [ ] Signature stored on function node

**Deliverables:**
- `src/true_vkg/kg/signature.py`
- Updated builder to compute and store signature
- `tests/test_signature.py`

---

## Phase 3: Pattern Engine Updates

**Duration:** 2 weeks
**Goal:** Update pattern engine to support operation-based matching.
**Blockers:** Phase 2 complete (operations and sequences in graph)

### Task 3.1: Add Operation Matchers

**Description:** Add pattern matching operators for semantic operations.

**Implementation:**
1. Update `src/true_vkg/queries/patterns.py`:
```python
"""Operation-based pattern matching."""

class PatternMatcher:
    """Extended pattern matcher with operation support."""

    def evaluate_condition(self, condition: dict, node: Node) -> bool:
        """Evaluate a single condition against a node."""

        # Existing matchers
        if 'property' in condition:
            return self._match_property(condition, node)

        # NEW: Operation matchers
        if 'has_operation' in condition:
            return self._match_has_operation(condition, node)

        if 'has_all_operations' in condition:
            return self._match_has_all_operations(condition, node)

        if 'has_any_operation' in condition:
            return self._match_has_any_operation(condition, node)

        if 'sequence_order' in condition:
            return self._match_sequence_order(condition, node)

        if 'signature_matches' in condition:
            return self._match_signature(condition, node)

        return False

    def _match_has_operation(self, condition: dict, node: Node) -> bool:
        """Check if node has a specific operation."""
        op = condition['has_operation']
        node_ops = node.properties.get('semantic_ops', [])
        return op in node_ops

    def _match_has_all_operations(self, condition: dict, node: Node) -> bool:
        """Check if node has ALL specified operations."""
        required = set(condition['has_all_operations'])
        node_ops = set(node.properties.get('semantic_ops', []))
        return required.issubset(node_ops)

    def _match_has_any_operation(self, condition: dict, node: Node) -> bool:
        """Check if node has ANY of the specified operations."""
        required = set(condition['has_any_operation'])
        node_ops = set(node.properties.get('semantic_ops', []))
        return bool(required.intersection(node_ops))

    def _match_sequence_order(self, condition: dict, node: Node) -> bool:
        """Check if operations occur in specified order."""
        before_op = condition['sequence_order']['before']
        after_op = condition['sequence_order']['after']

        ordering = node.properties.get('op_ordering', [])
        return (before_op, after_op) in ordering

    def _match_signature(self, condition: dict, node: Node) -> bool:
        """Match against behavioral signature pattern."""
        pattern = condition['signature_matches']
        signature = node.properties.get('behavioral_signature', '')
        return re.match(pattern, signature) is not None
```

**Acceptance Tests:**
```python
class TestOperationMatchers(unittest.TestCase):
    """Test operation-based pattern matching."""

    def test_has_operation(self):
        """Match node with specific operation."""
        node = create_test_node(semantic_ops=['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE'])
        condition = {'has_operation': 'TRANSFERS_VALUE_OUT'}
        self.assertTrue(matcher.evaluate_condition(condition, node))

    def test_has_operation_missing(self):
        """No match when operation missing."""
        node = create_test_node(semantic_ops=['READS_USER_BALANCE'])
        condition = {'has_operation': 'TRANSFERS_VALUE_OUT'}
        self.assertFalse(matcher.evaluate_condition(condition, node))

    def test_has_all_operations(self):
        """Match node with all required operations."""
        node = create_test_node(semantic_ops=['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE', 'READS_USER_BALANCE'])
        condition = {'has_all_operations': ['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE']}
        self.assertTrue(matcher.evaluate_condition(condition, node))

    def test_has_any_operation(self):
        """Match node with any of the operations."""
        node = create_test_node(semantic_ops=['READS_USER_BALANCE'])
        condition = {'has_any_operation': ['TRANSFERS_VALUE_OUT', 'READS_USER_BALANCE']}
        self.assertTrue(matcher.evaluate_condition(condition, node))

    def test_sequence_order(self):
        """Match operation ordering."""
        node = create_test_node(
            semantic_ops=['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE'],
            op_ordering=[('TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE')]
        )
        condition = {'sequence_order': {'before': 'TRANSFERS_VALUE_OUT', 'after': 'WRITES_USER_BALANCE'}}
        self.assertTrue(matcher.evaluate_condition(condition, node))

    def test_sequence_order_wrong(self):
        """No match when order is reversed."""
        node = create_test_node(
            semantic_ops=['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE'],
            op_ordering=[('WRITES_USER_BALANCE', 'TRANSFERS_VALUE_OUT')]  # Safe order
        )
        condition = {'sequence_order': {'before': 'TRANSFERS_VALUE_OUT', 'after': 'WRITES_USER_BALANCE'}}
        self.assertFalse(matcher.evaluate_condition(condition, node))

    def test_signature_matches(self):
        """Match behavioral signature pattern."""
        node = create_test_node(behavioral_signature='R:bal→X:out→W:bal')
        condition = {'signature_matches': r'.*X:out.*W:bal'}
        self.assertTrue(matcher.evaluate_condition(condition, node))
```

- [ ] All 5 operation matchers implemented
- [ ] Each matcher has positive and negative tests
- [ ] Matchers handle missing properties gracefully
- [ ] Pattern engine validates new condition types

**Deliverables:**
- Updated `src/true_vkg/queries/patterns.py`
- `tests/test_pattern_operations.py`

---

### Task 3.2: Update Pattern Schema

**Description:** Define and validate new pattern schema with operation support.

**Implementation:**
1. Create JSON Schema for validation:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VKG Pattern Schema v2",
  "type": "object",
  "required": ["id", "name", "scope", "match"],
  "properties": {
    "id": {"type": "string"},
    "name": {"type": "string"},
    "description": {"type": "string"},
    "scope": {"enum": ["Function", "Contract", "StateVariable"]},
    "lens": {"type": "array", "items": {"type": "string"}},
    "severity": {"enum": ["critical", "high", "medium", "low", "info"]},
    "match": {
      "type": "object",
      "properties": {
        "all": {"$ref": "#/definitions/conditionList"},
        "any": {"$ref": "#/definitions/conditionList"},
        "none": {"$ref": "#/definitions/conditionList"}
      }
    }
  },
  "definitions": {
    "conditionList": {
      "type": "array",
      "items": {"$ref": "#/definitions/condition"}
    },
    "condition": {
      "type": "object",
      "oneOf": [
        {"required": ["property"]},
        {"required": ["has_operation"]},
        {"required": ["has_all_operations"]},
        {"required": ["has_any_operation"]},
        {"required": ["sequence_order"]},
        {"required": ["signature_matches"]}
      ]
    }
  }
}
```

2. Add schema validation to pattern loader:
```python
def load_pattern(path: Path) -> Pattern:
    """Load and validate pattern from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    # Validate against schema
    validate_pattern_schema(data)

    return Pattern.from_dict(data)
```

**Acceptance Tests:**
- [ ] Schema validates all existing patterns
- [ ] Schema rejects invalid patterns with clear errors
- [ ] New operation conditions are validated
- [ ] Pattern loader uses schema validation

**Deliverables:**
- `patterns/schema/pattern-v2.json`
- Updated `src/true_vkg/queries/patterns.py` with validation
- `tests/test_pattern_schema.py`

---

### Task 3.3: Rewrite Core Patterns Using Operations

**Description:** Migrate high-impact patterns from name-based to operation-based.

**Implementation:**
1. Identify top 10 name-dependent patterns from Phase 0 audit
2. Rewrite each using operations

Example migration:
```yaml
# BEFORE (name-dependent)
id: reentrancy-classic
match:
  all:
    - property: label
      op: matches
      value: ".*[Ww]ithdraw.*"
    - property: state_write_after_external_call
      value: true

# AFTER (operation-based)
id: reentrancy-classic-v2
match:
  all:
    - property: visibility
      op: in
      value: [public, external]
    - has_all_operations:
        - TRANSFERS_VALUE_OUT
        - WRITES_USER_BALANCE
    - sequence_order:
        before: TRANSFERS_VALUE_OUT
        after: WRITES_USER_BALANCE
  none:
    - property: has_reentrancy_guard
      value: true
```

**Acceptance Tests:**
```python
class TestMigratedPatterns(unittest.TestCase):
    """Test migrated patterns work correctly."""

    def test_reentrancy_original_contract(self):
        """Migrated pattern detects original vulnerable contract."""
        graph = load_graph("ReentrancyVulnerable")
        matches = run_pattern("reentrancy-classic-v2", graph)
        self.assertGreater(len(matches), 0)

    def test_reentrancy_renamed_contract(self):
        """Migrated pattern detects RENAMED vulnerable contract."""
        graph = load_graph("ReentrancyVulnerableRenamed")
        matches = run_pattern("reentrancy-classic-v2", graph)
        self.assertGreater(len(matches), 0, "Pattern should work on renamed contract!")

    def test_reentrancy_safe_not_detected(self):
        """Migrated pattern does NOT flag safe contract."""
        graph = load_graph("ReentrancySafe")
        matches = run_pattern("reentrancy-classic-v2", graph)
        self.assertEqual(len(matches), 0)
```

- [ ] Top 10 patterns migrated
- [ ] All migrated patterns pass on original contracts
- [ ] All migrated patterns pass on renamed contracts
- [ ] No increase in false positives

**Deliverables:**
- Updated patterns in `patterns/core/`
- `tests/test_migrated_patterns.py`
- Migration report documenting changes

---

### Task 3.4: Implement Boolean Aggregation

**Description:** Implement voting and boolean logic for tier aggregation.

**Implementation:**
```python
"""Boolean aggregation for multi-tier matching."""

@dataclass
class TierResult:
    """Result from evaluating one tier."""
    matched: bool
    conditions_met: List[str]
    conditions_failed: List[str]


@dataclass
class AggregatedResult:
    """Combined result from all tiers."""
    matched: bool
    tiers_matched: List[str]  # e.g., ["A", "B"]
    aggregation_mode: str
    details: Dict[str, TierResult]


def aggregate_tier_results(
    tier_a: TierResult,
    tier_b: Optional[TierResult],
    mode: str,
    config: dict
) -> AggregatedResult:
    """Aggregate tier results according to mode."""

    if mode == "tier_a_only":
        return AggregatedResult(
            matched=tier_a.matched,
            tiers_matched=["A"] if tier_a.matched else [],
            aggregation_mode=mode,
            details={"A": tier_a}
        )

    if mode == "tier_a_required":
        matched = tier_a.matched  # Tier A must match
        tiers = []
        if tier_a.matched:
            tiers.append("A")
        if tier_b and tier_b.matched:
            tiers.append("B")
        return AggregatedResult(
            matched=matched,
            tiers_matched=tiers,
            aggregation_mode=mode,
            details={"A": tier_a, "B": tier_b}
        )

    if mode == "voting":
        min_tiers = config.get('minimum_tiers', 1)
        matched_count = sum([
            1 if tier_a.matched else 0,
            1 if tier_b and tier_b.matched else 0
        ])
        matched = matched_count >= min_tiers
        tiers = []
        if tier_a.matched:
            tiers.append("A")
        if tier_b and tier_b.matched:
            tiers.append("B")
        return AggregatedResult(
            matched=matched,
            tiers_matched=tiers,
            aggregation_mode=mode,
            details={"A": tier_a, "B": tier_b}
        )

    raise ValueError(f"Unknown aggregation mode: {mode}")
```

**Acceptance Tests:**
```python
class TestBooleanAggregation(unittest.TestCase):
    """Test tier aggregation modes."""

    def test_tier_a_only(self):
        """tier_a_only ignores Tier B."""
        tier_a = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        tier_b = TierResult(matched=False, conditions_met=[], conditions_failed=[])
        result = aggregate_tier_results(tier_a, tier_b, "tier_a_only", {})
        self.assertTrue(result.matched)
        self.assertEqual(result.tiers_matched, ["A"])

    def test_tier_a_required_both_match(self):
        """tier_a_required reports both when both match."""
        tier_a = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        tier_b = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        result = aggregate_tier_results(tier_a, tier_b, "tier_a_required", {})
        self.assertTrue(result.matched)
        self.assertEqual(result.tiers_matched, ["A", "B"])

    def test_tier_a_required_a_fails(self):
        """tier_a_required fails if Tier A fails."""
        tier_a = TierResult(matched=False, conditions_met=[], conditions_failed=[])
        tier_b = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        result = aggregate_tier_results(tier_a, tier_b, "tier_a_required", {})
        self.assertFalse(result.matched)

    def test_voting_one_tier(self):
        """voting matches if minimum tiers agree."""
        tier_a = TierResult(matched=False, conditions_met=[], conditions_failed=[])
        tier_b = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        result = aggregate_tier_results(tier_a, tier_b, "voting", {'minimum_tiers': 1})
        self.assertTrue(result.matched)
        self.assertEqual(result.tiers_matched, ["B"])

    def test_voting_both_required(self):
        """voting with minimum_tiers=2 requires both."""
        tier_a = TierResult(matched=True, conditions_met=[], conditions_failed=[])
        tier_b = TierResult(matched=False, conditions_met=[], conditions_failed=[])
        result = aggregate_tier_results(tier_a, tier_b, "voting", {'minimum_tiers': 2})
        self.assertFalse(result.matched)
```

- [ ] All 3 aggregation modes implemented
- [ ] Each mode has comprehensive tests
- [ ] Results include detailed tier breakdown
- [ ] Pattern schema supports aggregation config

**Deliverables:**
- `src/true_vkg/queries/aggregation.py`
- `tests/test_aggregation.py`

---

## Phase 4: Testing Infrastructure

**Duration:** 2 weeks
**Goal:** Build comprehensive test framework with negative tests.
**Blockers:** Phase 3 complete (pattern engine updated)

### Task 4.1: Create Safe Contract Variants

**Description:** For each vulnerable test contract, create a "safe" version.

**Implementation:**
1. Create directory structure:
```
tests/contracts/
├── reentrancy/
│   ├── vulnerable/
│   │   ├── ReentrancyClassic.sol
│   │   └── ReentrancyCrossFunction.sol
│   └── safe/
│       ├── ReentrancyGuarded.sol
│       ├── ReentrancyCEI.sol
│       └── ReentrancyPullPayment.sol
├── access_control/
│   ├── vulnerable/
│   │   ├── MissingAuth.sol
│   │   └── TxOrigin.sol
│   └── safe/
│       ├── OnlyOwner.sol
│       └── RoleBased.sol
...
```

2. Create safe variants of each vulnerability:
```solidity
// tests/contracts/reentrancy/safe/ReentrancyCEI.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Safe Reentrancy - CEI Pattern
/// @notice This contract is SAFE - uses Check-Effects-Interactions pattern
/// @dev Should NOT be flagged by reentrancy patterns
contract ReentrancyCEI {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    /// @notice Safe withdrawal using CEI pattern
    /// @dev State update BEFORE external call - NOT vulnerable
    function withdraw(uint256 amount) external {
        // Check
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Effects (state update FIRST)
        balances[msg.sender] -= amount;

        // Interactions (external call LAST)
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
```

**Acceptance Tests:**
- [ ] At least 30 safe contract variants created
- [ ] Each vulnerable pattern has 2+ safe counterparts
- [ ] All safe contracts compile without warnings
- [ ] Safe contracts documented with why they're safe

**Deliverables:**
- 30+ safe contracts in `tests/contracts/*/safe/`
- Documentation comments in each contract

---

### Task 4.2: Implement Pattern Test Template

**Description:** Create reusable test template for pattern validation.

**Implementation:**
```python
"""Pattern test template with positive and negative cases."""
from dataclasses import dataclass, field
from typing import List, Dict
import unittest


@dataclass
class PatternTestSpec:
    """Specification for pattern tests."""
    pattern_id: str

    # Functions that MUST match (true positives)
    must_match: List[str] = field(default_factory=list)
    # Format: "ContractName.functionName"

    # Functions that MUST NOT match (true negatives)
    must_not_match: List[str] = field(default_factory=list)

    # Contracts to test (loaded automatically)
    test_contracts: List[str] = field(default_factory=list)

    # Maximum acceptable false positive rate
    max_fp_rate: float = 0.05  # 5%


class PatternTestCase(unittest.TestCase):
    """Base class for pattern tests."""

    spec: PatternTestSpec = None  # Override in subclass

    @classmethod
    def setUpClass(cls):
        if cls.spec is None:
            raise ValueError("Must define spec in subclass")

        cls.engine = PatternEngine()
        cls.graphs = {}
        for contract in cls.spec.test_contracts:
            cls.graphs[contract] = load_graph(contract)

    def test_true_positives(self):
        """Pattern matches all must_match functions."""
        for func_ref in self.spec.must_match:
            contract, func_name = func_ref.split('.')
            graph = self.graphs[contract]
            matches = self.engine.run_pattern(self.spec.pattern_id, graph)
            matched_funcs = [m.node.label for m in matches]

            self.assertIn(
                func_name, matched_funcs,
                f"Pattern {self.spec.pattern_id} should match {func_ref}"
            )

    def test_true_negatives(self):
        """Pattern does NOT match must_not_match functions."""
        for func_ref in self.spec.must_not_match:
            contract, func_name = func_ref.split('.')
            graph = self.graphs[contract]
            matches = self.engine.run_pattern(self.spec.pattern_id, graph)
            matched_funcs = [m.node.label for m in matches]

            self.assertNotIn(
                func_name, matched_funcs,
                f"Pattern {self.spec.pattern_id} should NOT match {func_ref}"
            )

    def test_false_positive_rate(self):
        """Pattern stays within acceptable FP rate on safe contracts."""
        safe_funcs = []
        matches_on_safe = []

        for contract in self.spec.test_contracts:
            if '/safe/' in contract or 'Safe' in contract:
                graph = self.graphs[contract]
                funcs = [n for n in graph.nodes if n.type == 'Function']
                safe_funcs.extend(funcs)

                matches = self.engine.run_pattern(self.spec.pattern_id, graph)
                matches_on_safe.extend(matches)

        if safe_funcs:
            fp_rate = len(matches_on_safe) / len(safe_funcs)
            self.assertLessEqual(
                fp_rate, self.spec.max_fp_rate,
                f"FP rate {fp_rate:.1%} exceeds max {self.spec.max_fp_rate:.1%}"
            )


# Example usage:
class TestReentrancyPattern(PatternTestCase):
    spec = PatternTestSpec(
        pattern_id="reentrancy-classic-v2",
        must_match=[
            "ReentrancyClassic.withdraw",
            "ReentrancyClassic.withdrawAll",
            "ReentrancyClassicRenamed.removeFunds",  # Renamed version
        ],
        must_not_match=[
            "ReentrancyCEI.withdraw",
            "ReentrancyGuarded.withdraw",
            "ReentrancyPullPayment.withdraw",
        ],
        test_contracts=[
            "ReentrancyClassic",
            "ReentrancyClassicRenamed",
            "ReentrancyCEI",
            "ReentrancyGuarded",
            "ReentrancyPullPayment",
        ],
        max_fp_rate=0.05,
    )
```

**Acceptance Tests:**
- [ ] Template correctly identifies true positives
- [ ] Template correctly identifies true negatives
- [ ] FP rate calculation works correctly
- [ ] Clear error messages on failures

**Deliverables:**
- `tests/pattern_test_template.py`
- `tests/test_reentrancy_patterns.py` (example using template)

---

### Task 4.3: Create Comprehensive Pattern Tests

**Description:** Create tests for all major pattern categories.

**Implementation:**
Create test files for each lens:
- `tests/test_patterns_reentrancy.py`
- `tests/test_patterns_access_control.py`
- `tests/test_patterns_oracle.py`
- `tests/test_patterns_arithmetic.py`
- `tests/test_patterns_dos.py`
- `tests/test_patterns_upgrade.py`

Each file follows the template pattern with comprehensive positive/negative cases.

**Acceptance Tests:**
- [ ] Every pattern has dedicated test
- [ ] Each pattern test has 3+ positive cases
- [ ] Each pattern test has 3+ negative cases
- [ ] All tests pass on current codebase
- [ ] CI pipeline runs all pattern tests

**Deliverables:**
- 6+ test files covering all lenses
- Updated CI configuration to run pattern tests

---

### Task 4.4: Implement Precision Dashboard

**Description:** Create dashboard showing pattern precision metrics.

**Implementation:**
```python
"""Pattern precision dashboard generator."""
from dataclasses import dataclass
from typing import List, Dict
import json
from datetime import datetime


@dataclass
class PatternMetrics:
    """Metrics for a single pattern."""
    pattern_id: str
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


def generate_precision_dashboard(patterns: List[PatternMetrics], output_path: str):
    """Generate markdown dashboard with precision metrics."""
    content = [
        "# Pattern Precision Dashboard",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        "| Pattern | Precision | Recall | F1 Score | Status |",
        "|---------|-----------|--------|----------|--------|",
    ]

    for p in sorted(patterns, key=lambda x: x.f1_score):
        status = "✅" if p.precision >= 0.9 and p.recall >= 0.8 else "⚠️"
        content.append(
            f"| {p.pattern_id} | {p.precision:.1%} | {p.recall:.1%} | {p.f1_score:.2f} | {status} |"
        )

    content.extend([
        "",
        "## Patterns Needing Improvement",
        "",
    ])

    poor_patterns = [p for p in patterns if p.precision < 0.9 or p.recall < 0.8]
    for p in poor_patterns:
        content.append(f"- **{p.pattern_id}**: Precision={p.precision:.1%}, Recall={p.recall:.1%}")
        if p.false_positives > 0:
            content.append(f"  - {p.false_positives} false positives - review pattern conditions")
        if p.false_negatives > 0:
            content.append(f"  - {p.false_negatives} false negatives - pattern may be too strict")

    with open(output_path, 'w') as f:
        f.write('\n'.join(content))
```

**Acceptance Tests:**
- [ ] Dashboard generates correctly from test results
- [ ] Metrics calculated accurately
- [ ] Poor-performing patterns highlighted
- [ ] Dashboard updates on CI runs

**Deliverables:**
- `scripts/generate_precision_dashboard.py`
- `docs/precision-dashboard.md` (generated)
- CI job to generate dashboard

---

## Phase 5-12: Continued Implementation

Due to length constraints, I'll summarize the remaining phases:

---

## Phase 5: LLM Integration Infrastructure (3 weeks)

### Tasks:
- 5.1: Design LLM annotation schema
- 5.2: Implement annotation pipeline with caching
- 5.3: Create step-back prompting templates
- 5.4: Implement RAG with pattern library
- 5.5: Add `--semantic` CLI flag
- 5.6: Test annotation quality on sample contracts

---

## Phase 6: Risk Tag Taxonomy (2 weeks)

### Tasks:
- 6.1: Define hierarchical tag taxonomy based on OpenSCV
- 6.2: Create tag assignment prompts for LLM
- 6.3: Implement tag storage on nodes
- 6.4: Add tag-based pattern matching
- 6.5: Validate tags against manual auditor labels

---

## Phase 7: Tier B Pattern Integration (2 weeks)

### Tasks:
- 7.1: Extend pattern schema for tier_b conditions
- 7.2: Implement `has_risk_tag` matcher
- 7.3: Implement `llm_context` field matchers
- 7.4: Create Tier B enhanced patterns
- 7.5: Test tier aggregation end-to-end

---

## Phase 8: Advanced Detection Features (3 weeks)

### Tasks:
- 8.1: Implement cross-contract intent tracking
- 8.2: Implement behavioral regression detection
- 8.3: Implement compositional vulnerability chains
- 8.4: Add economic model extraction (experimental)

---

## Phase 9: Performance Optimization (2 weeks)

### Tasks:
- 9.1: Profile build pipeline
- 9.2: Implement incremental graph builds
- 9.3: Parallelize operation detection
- 9.4: Optimize LLM call batching
- 9.5: Add caching layers

---

## Phase 10: Enterprise Features (2 weeks)

### Tasks:
- 10.1: Add configuration profiles (fast, standard, thorough)
- 10.2: Implement multi-project support
- 10.3: Add report generation (PDF, HTML)
- 10.4: Create CI/CD integration examples

---

## Phase 11: Validation & Benchmarking (2 weeks)

### Tasks:
- 11.1: Benchmark against known vulnerability datasets
- 11.2: Compare with Slither, Mythril, Semgrep
- 11.3: Calculate final precision/recall metrics
- 11.4: Document performance characteristics

---

## Phase 12: Documentation Update (1 week)

### Tasks:
- 12.1: Update CLAUDE.md with new features
- 12.2: Create pattern authoring guide
- 12.3: Document LLM integration
- 12.4: Create API documentation
- 12.5: Write migration guide from v1 patterns
- 12.6: Update README with new capabilities

---

## Appendix: Test Contract Requirements

Each vulnerability category needs:

| Category | Vulnerable Contracts | Safe Contracts | Renamed Variants |
|----------|---------------------|----------------|------------------|
| Reentrancy | 5 | 5 | 5 |
| Access Control | 5 | 5 | 5 |
| Oracle | 3 | 3 | 3 |
| Arithmetic | 3 | 3 | 3 |
| DoS | 3 | 3 | 3 |
| Upgrade | 5 | 5 | 5 |
| Value Movement | 3 | 3 | 3 |
| Logic | 3 | 3 | 3 |
| **Total** | **30** | **30** | **30** |

---

## Appendix: Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Pattern name-dependency | < 10% | Phase 0 audit |
| Detection on renamed | > 90% | Renamed contract tests |
| Precision | > 90% | FP rate on safe contracts |
| Recall | > 80% | FN rate on vulnerable contracts |
| Build time (Tier A) | < 2x baseline | Benchmark suite |
| Build time (Tier A+B) | < 5x baseline | Benchmark suite |
| LLM tag accuracy | > 85% | Manual validation |
