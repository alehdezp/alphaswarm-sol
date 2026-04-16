# Benchmark Research Notes (R2.1)

## Overview

This document captures research on existing benchmark approaches for smart contract vulnerability detection tools.

## Existing Benchmark Datasets

### 1. Damn Vulnerable DeFi (DVDeFi) v4
- **Source**: https://www.damnvulnerabledefi.xyz/
- **Challenges**: 18 CTF-style challenges
- **Strengths**:
  - Real-world DeFi vulnerability patterns
  - Clear success/failure criteria via test files
  - Active community and updates
- **Weaknesses**:
- Some challenges require off-chain context/assumptions (compromised)
  - Complex multi-contract setups
  - Not all challenges are pure code vulnerabilities

**Our Focus (13 challenges):**
| Challenge | Vulnerability Type | BSKG Detection |
|-----------|-------------------|---------------|
| unstoppable | Strict equality DoS | ✅ |
| naive-receiver | Callback exploitation | ✅ |
| truster | Arbitrary external call | ✅ |
| side-entrance | Callback reentrancy | ✅ |
| the-rewarder | Flash loan reward manipulation | ✅ |
| selfie | Governance flash loan | ✅ |
| puppet | Oracle manipulation (V1) | ✅ |
| puppet-v2 | Oracle manipulation (V2) | ✅ |
| puppet-v3 | Oracle manipulation (V3) | ✅ |
| free-rider | msg.value loop reuse | ✅ |
| backdoor | Callback-controlled recipient | ✅ |
| compromised | Off-chain key leak | ❌ (needs off-chain trust modeling) |
| climber | Complex state manipulation | ❌ (needs builder changes) |

### 2. SmartBugs Curated
- **Source**: https://github.com/smartbugs/smartbugs-curated
- **Contracts**: 143 contracts with known vulnerabilities
- **Categories**: Reentrancy, Access Control, Arithmetic, DoS, Front-running, etc.
- **Strengths**:
  - Labeled ground truth
  - Wide vulnerability coverage
  - Used by academic research
- **Weaknesses**:
  - Some older Solidity versions
  - Some false positives in labels
  - Limited DeFi-specific patterns

### 3. DeFiHackLabs
- **Source**: https://github.com/SunWeb3Sec/DeFiHackLabs
- **Contracts**: Real exploit reproductions
- **Strengths**:
  - Real-world exploits with actual damages
  - Foundry test suite for each
  - Continuously updated
- **Weaknesses**:
  - Complex multi-transaction exploits
  - Some require external state (forks)
  - Not all are code vulnerabilities (admin key compromises)

### 4. Not So Smart Contracts
- **Source**: https://github.com/crytic/not-so-smart-contracts
- **Contracts**: Simple vulnerable examples
- **Strengths**:
  - Clear, isolated vulnerabilities
  - Good for basic testing
- **Weaknesses**:
  - Too simple for real-world evaluation
  - Limited coverage

## Benchmark Methodology

### Metrics

1. **Detection Rate (Recall)**
   - True Positives / (True Positives + False Negatives)
   - Target: >= 80% for DVDeFi, >= 70% for SmartBugs

2. **False Positive Rate**
   - False Positives / (False Positives + True Negatives)
   - Target: < 15% on safe set

3. **Precision**
   - True Positives / (True Positives + False Positives)
   - Target: >= 70%

4. **F1 Score**
   - 2 * (Precision * Recall) / (Precision + Recall)
   - Target: >= 75%

### Evaluation Protocol

1. **Per-Challenge YAML Definition**
   - Expected vulnerability type
   - Expected vulnerable functions
   - Expected patterns to match
   - False positive exclusions

2. **Automated Benchmark Runner**
   - Build graph for challenge
   - Run pattern queries
   - Compare to expected results
   - Calculate metrics

3. **Regression Prevention**
   - Baseline comparison in CI
   - Block PRs that reduce detection rate
   - Track metrics over time

## Tool Comparison

### Slither
- Static analysis, pattern-based
- High recall, moderate precision
- Fast execution
- Good baseline

### Aderyn
- Rust-based, newer
- Focus on precision
- Growing pattern library

### Mythril
- Symbolic execution
- Deep analysis
- Slower execution
- Good for complex bugs

### BSKG (Our Tool)
- Knowledge graph approach
- Semantic operations (name-agnostic)
- Pattern packs for extensibility
- LLM integration (Tier B)

## Recommended Benchmark Strategy

### Tier 1: DVDeFi (13 challenges)
- Well-understood CTF format
- Clear success criteria
- Our primary validation

### Tier 2: SmartBugs Curated (69 contracts)
- Labeled ground truth
- Academic standard
- Secondary validation

### Tier 3: Safe Set (50+ contracts)
- Known-safe contracts (OpenZeppelin, Uniswap V3)
- False positive measurement
- Precision validation

### Tier 4: Real-World Audits
- Actual audit reports
- Professional validation
- Gap identification

## Next Steps

1. Create expected results YAML for each DVDeFi challenge
2. Implement benchmark runner CLI
3. Add baseline comparison
4. Integrate with CI
5. Curate SmartBugs subset (69 contracts)
6. Build safe set for FP measurement

---

*Research completed: 2026-01-07*
*Version: 1.0*
