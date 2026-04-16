---
name: vrs-tool-slither
description: Run Slither static analysis on contracts
slash_command: vrs:tool-slither
context: fork
disable-model-invocation: false
allowed-tools: Bash(slither:*, alphaswarm:*), Read, Glob
---

# Run Slither Analysis

Run Slither static analysis on Solidity contracts in isolated context.

## Purpose

Slither is the core static analysis tool for BSKG graph construction and vulnerability detection. This skill:

- **Executes Slither** in forked context to prevent output pollution
- **Summarizes findings** instead of returning raw output
- **Creates beads** for HIGH and CRITICAL findings
- **Integrates with VKG** for graph-based verification

## When to Use

Use this skill for:
- Initial contract analysis
- Detecting common vulnerability patterns
- Validating graph construction
- Supplementing manual investigation

## Arguments

When invoking this skill, provide:

- **contracts_path**: Path to Solidity contracts directory or file
- **detectors**: (Optional) Specific Slither detectors to run
  - If omitted, runs all detectors
  - Can specify comma-separated list: `reentrancy-eth,suicidal,arbitrary-send`
  - Use `--list-detectors` to see all available

## Execution

**Run all detectors:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH --json
```

**Run specific detectors:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH \
  --detectors reentrancy-eth,suicidal,arbitrary-send \
  --json
```

**With Foundry project:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH \
  --foundry \
  --json
```

## Output Processing

The skill processes Slither's JSON output and returns:

1. **Summary statistics**:
   - Total issues found
   - Breakdown by severity (high, medium, low, informational)
   - Affected contracts and functions

2. **High-impact findings**:
   - Only HIGH and CRITICAL severity issues
   - Contract location
   - Detector name
   - Brief description

3. **Bead creation**:
   - Automatically creates beads for HIGH/CRITICAL findings
   - Links bead to Slither detector
   - Includes location and severity

## Example Output

```
Slither Analysis Complete

Summary:
  Total issues: 23
  Critical: 2
  High: 5
  Medium: 8
  Low: 6
  Informational: 2

High-Impact Findings (beads created):

[bd-a3f5b912] CRITICAL: Reentrancy in Vault.sol:withdrawAll
  Detector: reentrancy-eth
  Location: Vault.sol:45-67
  Description: External call transfers ETH before state update

[bd-c7e89f23] CRITICAL: Arbitrary send in Token.sol:transfer
  Detector: arbitrary-send
  Location: Token.sol:89-102
  Description: Function sends ETH to arbitrary destination

[bd-d4f2e1a5] HIGH: Uninitialized storage pointer in Staking.sol:stake
  Detector: uninitialized-storage
  Location: Staking.sol:134
  Description: Storage pointer used without initialization

[bd-e8b6c4d3] HIGH: Weak PRNG in Lottery.sol:pickWinner
  Detector: weak-prng
  Location: Lottery.sol:78-85
  Description: Uses block.timestamp for randomness

[bd-f1a7c9e2] HIGH: Unchecked low-level call in Bridge.sol:withdraw
  Detector: unchecked-lowlevel
  Location: Bridge.sol:203
  Description: Return value of low-level call not checked

Medium and Low findings not listed (available in full report).

Beads created: 5
Next: Use /vrs-orch-spawn to investigate findings
```

## Integration with VKG

Slither findings are integrated with BSKG by:
1. Creating beads for manual investigation
2. Linking detectors to BSKG patterns
3. Using Slither data for graph construction
4. Cross-referencing with BSKG semantic operations

## Performance

Slither execution is isolated in forked context to:
- Prevent main conversation context pollution
- Allow parallel analysis with other tools
- Handle large output without context bloat
- Enable cleanup after analysis

## Error Handling

- **Slither not installed**: Returns installation instructions
- **Compilation errors**: Returns compiler output for user to fix
- **No contracts found**: Validates path and reports error
- **Timeout**: Configurable timeout with progress reporting
- **JSON parse error**: Falls back to text parsing

## Advanced Options

**Exclude specific detectors:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH \
  --exclude reentrancy-benign,naming-convention \
  --json
```

**Filter by severity:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH \
  --filter-severity high,critical \
  --json
```

**Custom Slither config:**
```bash
alphaswarm tools run slither $CONTRACTS_PATH \
  --config slither.config.json \
  --json
```

## Output Format

JSON output structure for programmatic use:
```json
{
  "tool": "slither",
  "version": "0.10.0",
  "timestamp": "2026-01-22T12:55:00Z",
  "target": "contracts/",
  "summary": {
    "total": 23,
    "by_severity": {
      "critical": 2,
      "high": 5,
      "medium": 8,
      "low": 6,
      "informational": 2
    }
  },
  "findings": [
    {
      "detector": "reentrancy-eth",
      "severity": "critical",
      "confidence": "high",
      "location": "Vault.sol:45-67",
      "description": "...",
      "bead_id": "bd-a3f5b912"
    }
  ]
}
```
