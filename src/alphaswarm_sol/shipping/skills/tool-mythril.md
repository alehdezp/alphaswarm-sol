---
name: vrs-tool-mythril
description: Run Mythril symbolic execution for deep vulnerability analysis
slash_command: vrs:tool-mythril
context: fork
disable-model-invocation: false
allowed-tools: Bash(myth:*, alphaswarm:*), Read, Glob
---

# Run Mythril Analysis

Run Mythril symbolic execution for deep vulnerability analysis on Solidity contracts.

## Purpose

Mythril is a symbolic execution tool for finding deep vulnerabilities. This skill:

- **Executes Mythril** in forked context to prevent output pollution
- **Summarizes findings** instead of returning raw output
- **Creates beads** for HIGH and CRITICAL findings
- **Integrates with VKG** for graph-based verification

## When to Use

Use this skill for:
- Complex arithmetic operations (mulDiv, FixedPoint, etc.)
- Proxy/upgradeable contracts
- After Slither identifies potential issues (deeper analysis)
- High-value contracts justifying longer analysis time
- Need concrete counterexamples for exploit verification

## When NOT to Use

- Simple view-only contracts (overkill)
- Time-constrained quick scans (5-10 min per contract)
- Already have Halmos coverage for same properties
- Mythril not installed
- Very large codebases (state explosion)

## Arguments

When invoking this skill, provide:

- **contracts_path**: Path to Solidity contracts directory or file
- **max_depth**: (Optional) Transaction depth (default: 24)
- **solver_timeout**: (Optional) SMT solver timeout in ms (default: 30000)

## Execution

**Run via AlphaSwarm:**
```bash
alphaswarm tools run mythril $CONTRACTS_PATH --json
```

**Direct mythril:**
```bash
myth analyze $CONTRACTS_PATH --json
```

**With reduced depth (faster):**
```bash
myth analyze $CONTRACTS_PATH --max-depth 12 --json
```

**With increased depth (thorough):**
```bash
myth analyze $CONTRACTS_PATH --max-depth 50 --solver-timeout 60000 --json
```

## SWC Mapping

Mythril reports issues using Smart Contract Weakness Classification (SWC):

| SWC ID | Description | BSKG Pattern | Severity |
|--------|-------------|-------------|----------|
| SWC-100 | Function Default Visibility | visibility-missing | Medium |
| SWC-101 | Integer Overflow/Underflow | arithmetic-overflow | High |
| SWC-104 | Unchecked Call Return Value | unchecked-call | Medium |
| SWC-105 | Unprotected Ether Withdrawal | access-control-permissive | Critical |
| SWC-106 | Unprotected SELFDESTRUCT | selfdestruct-unprotected | Critical |
| SWC-107 | Reentrancy | reentrancy-classic | Critical |
| SWC-110 | Assert Violation | assertion-failure | Medium |
| SWC-112 | Delegatecall to Untrusted | delegatecall-injection | Critical |
| SWC-113 | DoS with Failed Call | dos-failed-call | High |
| SWC-115 | tx.origin Authentication | tx-origin-auth | High |
| SWC-116 | Block values as time proxy | timestamp-dependence | Low |
| SWC-120 | Weak Sources of Randomness | randomness-weak | High |
| SWC-124 | Write to Arbitrary Storage | storage-arbitrary | Critical |

## Output Processing

The skill processes Mythril's JSON output and returns:

1. **Summary statistics**: Total issues, breakdown by severity
2. **High-impact findings**: Only HIGH and CRITICAL severity issues with SWC mapping
3. **Bead creation**: Automatically creates beads for findings with concrete counterexamples

### High Confidence (concrete counterexample)

Mythril findings with concrete counterexamples are **very reliable**:
- Include transaction sequences showing exact exploit path
- Action: Create CRITICAL bead with concrete exploit path

### Lower Confidence (no concrete example)

If Mythril reports potential issue without transaction sequence:
- May be path that's actually unreachable
- May require specific preconditions
- Verify manually or with BSKG graph analysis

## Error Handling

- **Timeout**: Split contracts, analyze separately (large contracts cause timeout)
- **Out of memory**: Reduce --max-depth (state explosion)
- **Compilation**: Check solc version (Mythril needs matching version)
- **No output**: Increase timeout, check logs (may still be analyzing)
- **Solver timeout**: Increase --solver-timeout (complex constraints)

## Integration with VKG

Mythril findings feed through the pipeline:

```
Mythril JSON Output -> MythrilAdapter -> VKGFinding -> Deduplication -> Bead Creation -> Multi-Agent Verification
```

## Performance

- Execution time: 5-10 minutes per contract typical
- Run in forked context to allow parallel analysis
- May timeout on very large contracts (state explosion)
- Partial results still valuable if analysis times out
