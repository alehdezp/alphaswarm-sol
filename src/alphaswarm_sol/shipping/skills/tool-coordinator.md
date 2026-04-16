---
name: vrs-tool-coordinator
description: Analyze projects and create optimal tool execution strategies
slash_command: vrs:tool-coordinator
context: fork
disable-model-invocation: false
allowed-tools: Bash(alphaswarm:*), Read, Glob, Grep
---

# Coordinate Tool Execution

Analyze a Solidity project and create an optimal tool execution strategy.

## Purpose

This skill analyzes project characteristics and decides:
1. Which tools to run
2. In what order (parallel groups)
3. With what configuration
4. Which BSKG patterns to skip (tool coverage)

## When to Use

- Starting a new audit
- After significant code changes
- When previous tool run had issues
- Want to understand tool selection rationale

## When NOT to Use

- Quick single-file analysis (use specific tool skill directly)
- Re-running same analysis (cached results available)
- Only need one specific tool (use /vrs-tool-slither etc.)

## Arguments

When invoking this skill, provide:

- **contracts_path**: Path to Solidity contracts directory

## Execution

**Analyze project and show strategy:**
```bash
alphaswarm tools analyze $CONTRACTS_PATH
```

**List available tools:**
```bash
alphaswarm tools list --health
```

**Check tool status:**
```bash
alphaswarm tools status
```

## Decision Logic

### Project Analysis Indicators

The coordinator examines source code for these patterns:

| Indicator | Detection Method | Tool Impact |
|-----------|------------------|-------------|
| Proxy patterns | delegatecall, ERC1967, UUPS | +mythril, +halmos |
| Complex math | mulDiv, FullMath, FixedPoint | +mythril, +halmos |
| Value transfers | .transfer, .call{value, payable | +echidna, +foundry |
| Oracle usage | priceFeed, getPrice, Chainlink | +slither oracles |
| External calls | .call(, interfaces | +reentrancy focus |
| Known libraries | OpenZeppelin, Solmate, Solady | Context for FPs |

### Tool Selection Matrix

| Project Type | Baseline | Add If Complex | Add If Value |
|--------------|----------|----------------|--------------|
| Simple ERC20 | slither, aderyn | semgrep | - |
| DeFi Protocol | slither, aderyn, semgrep | mythril, halmos | echidna |
| Upgradeable | slither, aderyn | mythril | halmos |
| Oracle Consumer | slither, aderyn | mythril | - |

### Parallel Execution Groups

**Group 1 (Fast Static):** slither, aderyn, semgrep
- Execution time: < 2 min each
- Run first, always

**Group 2 (Symbolic):** mythril, halmos
- Execution time: 5-10 min each
- Run if complexity warrants

**Group 3 (Fuzzing):** echidna, foundry, medusa
- Execution time: 10+ min each
- Run if value handling detected

## Output Format

Strategy includes:
- `tools_to_run`: List of tool names
- `parallel_groups`: List of parallel execution groups
- `tool_configs`: Per-tool configuration
- `estimated_time_seconds`: Expected total time
- `rationale`: Why these tools were selected
- `skip_reasons`: Why excluded tools were skipped
- `patterns_to_skip`: BSKG patterns covered by tools
- `pattern_skip_rationale`: Per-pattern skip explanation

## Never-Skip Patterns

These patterns always run in BSKG regardless of tool coverage:

- `business-logic-violation` - Tools can't detect semantic issues
- `economic-manipulation` - Requires protocol understanding
- `governance-attack` - Context-dependent
- `cross-function-reentrancy` - Multi-step analysis
- `cross-contract-reentrancy` - Cross-contract analysis
- `oracle-manipulation` - Domain-specific
- `price-manipulation` - Economic understanding
- `flash-loan-attack` - Complex flow
- `privilege-escalation` - Access control edge cases
- `role-confusion` - Authorization complexity
- `slippage-manipulation` - DeFi-specific
- `sandwich-attack` - MEV patterns
- `front-running` - Transaction ordering

## Error Handling

- **File read error**: Skip that file, continue with others
- **Empty project**: Return error - no Solidity files found
- **Tool registry unavailable**: Use default baseline (slither, aderyn)
- **Unknown pattern**: Log warning, continue analysis

## Integration

Feed strategy into tool execution:
```bash
# Run all recommended tools
alphaswarm tools run $CONTRACTS_PATH --strategy auto
```

Or execute individual tools from the strategy:
```bash
alphaswarm tools run slither $CONTRACTS_PATH --json
alphaswarm tools run mythril $CONTRACTS_PATH --json
```
