# Automated Invariant Mining and Synthesis (AIMS)

**Status:** Implemented (Phase 05.11-09)
**Module:** `alphaswarm_sol.economics.invariants`

## Overview

AIMS discovers protocol invariants from transaction traces and synthesizes
`require()` statements that would have prevented past exploits. It catches
"machine un-auditable" bugs where code doesn't match implicit expectations.

The system is inspired by [Trace2Inv](https://arxiv.org/abs/2201.01220), which
demonstrated that runtime trace analysis can discover critical invariants that
static analysis misses.

## Key Features

1. **Trace-based Mining** - Learn invariants from observed transaction behavior
2. **Pattern Library** - Trace2Inv-style pattern types for common invariant forms
3. **Statistical Confidence** - Score candidates by trace coverage and counterexamples
4. **Require Synthesis** - Generate defensive Solidity code from invariants
5. **Exploit Validation** - Test if invariants would prevent known exploits
6. **Discrepancy Detection** - Compare mined vs declared invariants

## Quick Start

```python
from alphaswarm_sol.economics.invariants import (
    InvariantMiner,
    InvariantSynthesizer,
    mine_from_traces,
    synthesize_require,
)

# Mine invariants from transaction traces
miner = InvariantMiner()
result = miner.mine_from_traces("MyToken", transaction_traces)

print(f"Discovered {len(result.candidates)} invariant candidates")

# Synthesize require() statements for high-confidence invariants
synthesizer = InvariantSynthesizer()
for candidate in result.candidates:
    if candidate.confidence >= 0.9:
        require = synthesizer.synthesize_require(candidate)
        print(f"// {candidate.natural_language}")
        print(f"{require.full_code}")

# Validate against known exploits
for candidate in result.candidates:
    validation = synthesizer.validate_against_exploits(candidate, exploit_db)
    if validation.prevented_count > 0:
        print(f"{candidate.id} would prevent {validation.prevented_count} exploits")
```

## Invariant Pattern Library

AIMS includes a library of pattern types based on Trace2Inv research:

### MappingUpperBound

Ensures mapping values don't exceed a bound.

**Example:** `balance[user] <= totalSupply`

```python
from alphaswarm_sol.economics.invariants import MappingUpperBound

pattern = MappingUpperBound(
    mapping_name="balances",
    bound_expression="totalSupply",
    base_confidence=0.9,
)

# Generated require:
# require(balances[key] <= totalSupply, "Value exceeds bound");
```

### MappingLowerBound

Ensures mapping values are above a minimum.

**Example:** `balance[user] >= 0`

```python
from alphaswarm_sol.economics.invariants import MappingLowerBound

pattern = MappingLowerBound(
    mapping_name="balances",
    bound_value=0,
    base_confidence=0.95,
)
```

### SumInvariant

Conservation law: sum of values equals total.

**Example:** `sum(balances) == totalSupply`

```python
from alphaswarm_sol.economics.invariants import SumInvariant

pattern = SumInvariant(
    mapping_name="balances",
    total_variable="totalSupply",
    base_confidence=0.85,
)
```

### MonotonicProperty

Value only changes in one direction.

**Example:** `nonce' > nonce` (always increases)

```python
from alphaswarm_sol.economics.invariants import MonotonicProperty

pattern = MonotonicProperty(
    variable_name="nonce",
    direction="increasing",
    strict=True,  # Must increase, not just >=
)
```

### StateTransitionConstraint

Valid state machine transitions.

**Example:** State can only go `INIT -> ACTIVE -> PAUSED -> CLOSED`

```python
from alphaswarm_sol.economics.invariants import StateTransitionConstraint

pattern = StateTransitionConstraint(
    state_variable="state",
    valid_transitions={
        "INIT": ["ACTIVE"],
        "ACTIVE": ["PAUSED", "CLOSED"],
        "PAUSED": ["ACTIVE", "CLOSED"],
    },
)
```

### VariableRelation

Relationship between variables.

**Example:** `reserveA * reserveB >= k` (AMM constant product)

```python
from alphaswarm_sol.economics.invariants import VariableRelation

pattern = VariableRelation(
    left_expression="reserveA * reserveB",
    operator=">=",
    right_expression="k",
)
```

### CallValueUpperBound

Constrains msg.value sent in transactions.

**Example:** `msg.value <= maxDeposit`

```python
from alphaswarm_sol.economics.invariants import CallValueUpperBound

pattern = CallValueUpperBound(
    bound_variable="maxDeposit",
    function_selector="deposit()",
)
```

### RatioBound

Constrains ratio between two values.

**Example:** `0.5 <= collateral/debt <= 2.0`

```python
from alphaswarm_sol.economics.invariants import RatioBound

pattern = RatioBound(
    numerator="collateral",
    denominator="debt",
    min_ratio=0.5,
    max_ratio=2.0,
)
```

### DifferenceBound

Constrains difference between values (slippage protection).

**Example:** `|price - oraclePrice| <= 5%`

```python
from alphaswarm_sol.economics.invariants import DifferenceBound

pattern = DifferenceBound(
    variable_a="price",
    variable_b="oraclePrice",
    max_difference=5,
    relative=True,  # Percentage, not absolute
)
```

## Mining Algorithm

### Phase 1: State Variable Extraction

Scan transaction traces to identify state variables:

```python
def _extract_state_variables(traces):
    variables = set()
    for trace in traces:
        state = trace.get("state", {})
        for key in state.keys():
            variables.add(key)
    return variables
```

### Phase 2: Pattern Template Generation

Generate candidate patterns based on variable naming heuristics:

- Variables with "balance" -> MappingUpperBound, MappingLowerBound, SumInvariant
- Variables with "nonce", "counter" -> MonotonicProperty
- Variables with "state", "status" -> StateTransitionConstraint
- Variables with "reserve" -> VariableRelation (AMM patterns)

### Phase 3: Statistical Validation

Validate each pattern against all traces:

```python
for trace in traces:
    if pattern.check_trace(trace):
        supporting += 1
    else:
        counterexamples += 1

coverage = supporting / (supporting + counterexamples)
```

### Phase 4: Confidence Scoring

Calculate confidence based on:

1. **Base confidence** from pattern type (e.g., non-negative uint = 0.95)
2. **Support ratio** (supporting traces / total traces)
3. **Counterexample decay** (each counterexample reduces confidence)
4. **Sample size boost** (more traces = higher confidence)

```python
confidence = base_confidence * support_ratio
if counterexamples > 0:
    confidence *= (1 - decay_rate * counterexamples)
if total_traces >= 100:
    confidence = min(confidence * 1.1, 1.0)
```

### Phase 5: Filtering

Filter candidates by configurable thresholds:

- **min_trace_coverage**: Minimum percentage of traces that must satisfy (default 90%)
- **counterexample_tolerance**: Maximum counterexample ratio (default 0%)
- **min_confidence**: Minimum confidence score (default 0.7)

## Require Statement Synthesis

### Synthesis Rules

Each pattern type has specific synthesis rules:

| Pattern Type | Require Condition | Position |
|--------------|-------------------|----------|
| MappingUpperBound | `mapping[key] <= bound` | pre/post |
| MappingLowerBound | `mapping[key] >= bound` | pre/post |
| SumInvariant | `_sumOfMapping() == total` | post |
| MonotonicProperty | `newValue >= oldValue` | post |
| StateTransition | `validStateTransition(old, new)` | pre |
| VariableRelation | `expr1 OP expr2` | pre/post |
| CallValueUpperBound | `msg.value <= bound` | pre |
| RatioBound | `num * 1e18 / denom <= max` | pre |

### Gas Estimation

The synthesizer estimates gas overhead:

- Base require cost: ~200 gas
- Storage read (SLOAD): ~2100 gas per variable
- Comparison operations: ~3 gas each
- Arithmetic operations: ~3-5 gas each
- Sum computation: ~5000 gas (expensive!)

### Revert Messages

Generated revert messages are concise for gas efficiency:

| Pattern Type | Revert Message |
|--------------|----------------|
| MappingUpperBound | "Value exceeds bound" |
| MappingLowerBound | "Value below minimum" |
| SumInvariant | "Conservation violated" |
| MonotonicProperty | "Monotonicity violated" |
| StateTransition | "Invalid state transition" |

## Exploit Validation

### Validation Process

For each invariant candidate, test against known exploits:

```python
for exploit in exploit_db:
    for trace in exploit.traces:
        if not pattern.check_trace(trace):
            # This invariant would have caught the exploit!
            result.prevented_count += 1
            result.exploits_prevented.append(exploit.id)
            break
```

### Validation Result

```python
result = ExploitValidationResult(
    invariant_id="INV-001",
    prevented_count=5,
    missed_count=2,
    exploits_prevented=["exploit-001", "exploit-003", ...],
    exploits_missed=["exploit-002", "exploit-007"],
)

# Prevention rate: 5/7 = 71.4%
print(f"Would prevent {result.prevention_rate:.1%} of exploits")
```

### Benchmark Target

Per plan specification: **70%+ of historical exploits should be catchable**
by mined invariants.

## Discrepancy Detection

### Discrepancy Types

| Type | Description | Severity |
|------|-------------|----------|
| MISSING_DECLARED | Mined but not in docs | High (safety gap) |
| MISSING_MINED | Declared but not mined | Medium (untested) |
| CONFLICT | Contradictory invariants | Critical |
| CONFIDENCE_GAP | Declared high, mined low | High |

### Usage

```python
# Compare mined invariants with declared invariants from docs
discrepancies = synthesizer.compare_with_declared(mined_candidates, declared_invariants)

for d in discrepancies:
    if d.discrepancy_type == DiscrepancyType.MISSING_DECLARED:
        print(f"SAFETY GAP: {d.description}")
        print(f"Resolution: {d.resolution_hint}")
```

## Integration with InvariantRegistry

Mined invariants can be registered in the central InvariantRegistry:

```python
from alphaswarm_sol.context.invariant_registry import InvariantRegistry

registry = InvariantRegistry()
synthesizer = InvariantSynthesizer()

for candidate in result.candidates:
    if candidate.confidence >= 0.9:
        synthesizer.register_with_registry(candidate, registry)

# Compare mined vs declared
discrepancies = registry.compare_mined_vs_declared()
```

## Configuration

### Mining Configuration

```python
from alphaswarm_sol.economics.invariants import MiningConfig

config = MiningConfig(
    min_trace_coverage=0.9,      # 90% of traces must satisfy
    counterexample_tolerance=0.0, # No counterexamples allowed
    min_confidence=0.7,           # Minimum confidence score
    confidence_decay_rate=0.1,    # Decay per counterexample
    max_candidates=100,           # Maximum candidates to return
    enabled_pattern_types=set(),  # Empty = all types
)
```

### Synthesis Configuration

```python
from alphaswarm_sol.economics.invariants import SynthesisConfig

config = SynthesisConfig(
    min_confidence_for_require=0.8, # Min confidence to generate require()
    include_revert_messages=True,   # Include revert messages
    optimize_gas=True,              # Skip high-gas statements
    max_gas_per_require=5000,       # Maximum gas overhead
    default_position="pre",         # Default insertion position
)
```

## Transaction Trace Format

The miner expects traces in this format:

```python
trace = {
    "tx_hash": "0x...",
    "function": "transfer",
    "value": 0,  # msg.value

    # Current state (or use pre/post)
    "state": {
        "balances": {"alice": 1000, "bob": 500},
        "totalSupply": 1500,
        "nonce": 42,
    },

    # Pre-call state (for transition patterns)
    "pre_state": {
        "balances": {"alice": 1500, "bob": 0},
        "totalSupply": 1500,
        "nonce": 41,
    },

    # Post-call state
    "post_state": {
        "balances": {"alice": 1000, "bob": 500},
        "totalSupply": 1500,
        "nonce": 42,
    },
}
```

## API Reference

### Core Classes

| Class | Purpose |
|-------|---------|
| `InvariantMiner` | Mine invariants from traces |
| `InvariantCandidate` | Discovered invariant with confidence |
| `InvariantSynthesizer` | Generate require() statements |
| `RequireStatement` | Synthesized require() code |
| `ExploitValidationResult` | Exploit prevention statistics |
| `Discrepancy` | Mined vs declared difference |

### Convenience Functions

| Function | Purpose |
|----------|---------|
| `mine_from_traces(contract, traces)` | Quick mining |
| `synthesize_require(candidate)` | Quick synthesis |

### Pattern Classes

| Class | Invariant Form |
|-------|----------------|
| `MappingUpperBound` | `mapping[k] <= bound` |
| `MappingLowerBound` | `mapping[k] >= bound` |
| `SumInvariant` | `sum(mapping) == total` |
| `MonotonicProperty` | `value' >= value` |
| `StateTransitionConstraint` | Valid transitions only |
| `VariableRelation` | `expr1 OP expr2` |
| `CallValueUpperBound` | `msg.value <= bound` |
| `RatioBound` | `min <= num/denom <= max` |
| `DifferenceBound` | `|a - b| <= max` |

## Research Background

AIMS is based on research into dynamic invariant detection:

- **Trace2Inv** (2022): Automated invariant generation for DeFi
- **Daikon** (2001): Dynamic invariant detection for program analysis
- **InvCon** (2020): Invariant-based smart contract analysis

The key insight is that runtime traces capture actual program behavior,
revealing invariants that static analysis may miss due to path explosion
or complex state dependencies.

## Limitations

1. **Trace Quality**: Results depend on trace coverage of edge cases
2. **False Positives**: Some patterns may be spurious correlations
3. **Gas Cost**: Sum invariants and complex patterns are expensive
4. **Dynamic State**: Cannot capture time-dependent invariants easily
5. **Cross-Contract**: Limited to single-contract analysis currently

## Future Enhancements

- Multi-contract invariant mining
- Time-series pattern detection
- Symbolic execution integration
- Automated fuzzing feedback loop
- Gas-optimized synthesis strategies

---

*Module: `alphaswarm_sol.economics.invariants`*
*Phase: 05.11-09 (Economic Context + Agentic Workflow)*
