---
name: vrs-tool-aderyn
description: Run Aderyn static analysis on contracts
slash_command: vrs:tool-aderyn
context: fork
disable-model-invocation: false
allowed-tools: Bash(aderyn:*, alphaswarm:*), Read, Glob
---

# Run Aderyn Analysis

Run Aderyn static analysis on Solidity contracts in isolated context.

## Purpose

Aderyn is a Rust-based static analyzer focusing on gas optimization and code quality. This skill:

- **Executes Aderyn** in forked context to prevent output pollution
- **Summarizes findings** instead of returning raw output
- **Creates beads** for HIGH and CRITICAL findings
- **Complements Slither** with different detector coverage

## When to Use

Use this skill for:
- Gas optimization analysis
- Code quality checks
- Detecting patterns Slither might miss
- Supplementing multi-tool analysis

## Arguments

When invoking this skill, provide:

- **contracts_path**: Path to Solidity contracts directory
- **severity**: (Optional) Minimum severity filter
  - If omitted, includes all severities
  - Options: `critical`, `high`, `medium`, `low`

## Execution

**Run all detectors:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH --json
```

**Filter by severity:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH \
  --severity high \
  --json
```

**With Foundry project:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH \
  --foundry \
  --json
```

## Output Processing

The skill processes Aderyn's JSON output and returns:

1. **Summary statistics**:
   - Total issues found
   - Breakdown by severity
   - Affected contracts and functions

2. **High-impact findings**:
   - Only HIGH and CRITICAL severity issues
   - Contract location
   - Detector name
   - Brief description

3. **Bead creation**:
   - Automatically creates beads for HIGH/CRITICAL findings
   - Links bead to Aderyn detector
   - Includes location and severity

## Example Output

```
Aderyn Analysis Complete

Summary:
  Total issues: 18
  Critical: 1
  High: 4
  Medium: 7
  Low: 6

High-Impact Findings (beads created):

[bd-g2h8d1f4] CRITICAL: Centralization risk in Admin.sol:updateConfig
  Detector: centralization-risk
  Location: Admin.sol:45-52
  Description: Single admin can change critical parameters

[bd-h3i9e2g5] HIGH: Unprotected upgrade in Proxy.sol:upgradeTo
  Detector: unprotected-upgrade
  Location: Proxy.sol:78-85
  Description: Upgrade function lacks access control

[bd-i4j1f3h6] HIGH: Denial of service in Auction.sol:placeBid
  Detector: dos-unbounded-loop
  Location: Auction.sol:123-145
  Description: Unbounded loop over user array

[bd-j5k2g4i7] HIGH: Timestamp dependence in Vesting.sol:claim
  Detector: timestamp-dependence
  Location: Vesting.sol:89-102
  Description: Uses block.timestamp for critical logic

Medium and Low findings not listed (available in full report).

Beads created: 4
Next: Use /vrs-orch-spawn to investigate findings
```

## Detector Coverage

Aderyn specializes in:
- **Gas optimizations**: Inefficient patterns, storage access, loop optimizations
- **Access control**: Missing modifiers, centralization risks
- **Upgradeability**: Proxy patterns, storage collisions
- **DoS vectors**: Unbounded loops, gas griefing
- **Best practices**: Code style, naming conventions

## Integration with VKG

Aderyn findings are integrated with BSKG by:
1. Creating beads for manual investigation
2. Linking detectors to BSKG patterns
3. Cross-referencing with Slither findings (deduplication)
4. Using Aderyn data to enrich graph

## Performance

Aderyn execution is isolated in forked context to:
- Prevent main conversation context pollution
- Allow parallel analysis with other tools (e.g., Slither)
- Handle large output without context bloat
- Enable cleanup after analysis

## Error Handling

- **Aderyn not installed**: Returns installation instructions with Rust setup
- **Compilation errors**: Returns compiler output for user to fix
- **No contracts found**: Validates path and reports error
- **Timeout**: Configurable timeout with progress reporting
- **JSON parse error**: Falls back to text parsing

## Advanced Options

**Exclude specific detectors:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH \
  --exclude naming-convention,style-guide \
  --json
```

**Custom config:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH \
  --config aderyn.toml \
  --json
```

**Output to file:**
```bash
alphaswarm tools run aderyn $CONTRACTS_PATH \
  --output report.json \
  --json
```

## Output Format

JSON output structure for programmatic use:
```json
{
  "tool": "aderyn",
  "version": "0.3.0",
  "timestamp": "2026-01-22T12:55:00Z",
  "target": "contracts/",
  "summary": {
    "total": 18,
    "by_severity": {
      "critical": 1,
      "high": 4,
      "medium": 7,
      "low": 6
    }
  },
  "findings": [
    {
      "detector": "centralization-risk",
      "severity": "critical",
      "confidence": "high",
      "location": "Admin.sol:45-52",
      "description": "...",
      "bead_id": "bd-g2h8d1f4"
    }
  ]
}
```

## Comparison with Slither

| Aspect | Slither | Aderyn |
|--------|---------|--------|
| **Language** | Python | Rust |
| **Speed** | Moderate | Fast |
| **Focus** | Security vulnerabilities | Gas + security |
| **Coverage** | 90+ detectors | 40+ detectors |
| **Upgradeability** | Basic | Advanced |
| **Gas optimization** | Limited | Extensive |

**Best practice**: Run both tools for comprehensive coverage. BSKG automatically deduplicates findings across tools.
