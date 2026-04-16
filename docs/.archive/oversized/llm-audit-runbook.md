# LLM Audit Runbook

**Status:** Specification
**Version:** 1.0.0
**Source:** CRITIQUE-REMEDIATION.md WS1.2
**Affects:** Phase 3, 4, 5, 11

---

## Overview

This is the repeatable 8-step workflow for LLM-driven security audits using VKG. Follow this runbook for consistent, reproducible audit results.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM AUDIT WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Scope          2. Build           3. Tier A            4. Orchestrate   │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐          ┌─────────┐       │
│  │ Preflight│ ──► │ Graph   │ ──►   │ Patterns│ ──►      │ Slither │       │
│  │ Manifest │      │Fingerprint│     │ Evidence│          │ Aderyn  │       │
│  └─────────┘      └─────────┘       └─────────┘          └─────────┘       │
│                                           │                    │            │
│                                           ▼                    ▼            │
│  5. Tier B         6. Scaffold       7. Report            8. Learn         │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐          ┌─────────┐       │
│  │  LLM    │ ◄──  │  Test   │       │  SARIF  │ ──►      │ Pattern │       │
│  │ Verify  │      │ Verdict │       │  JSON   │          │ Metrics │       │
│  └─────────┘      └─────────┘       └─────────┘          └─────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

```bash
# Install VKG
pip install alphaswarm

# Install Slither (required for graph building)
pip install slither-analyzer

# Verify installation
vkg --version
slither --version
```

---

## Step 1: Scope and Configuration

**Purpose:** Identify project structure, detect framework, lock configuration.

### Commands

```bash
# Navigate to project root
cd /path/to/project

# Detect framework (Foundry, Hardhat, Brownie)
vkg detect-framework .
# Output: Detected: foundry (foundry.toml present)

# Initialize BSKG project
vkg init
# Creates: .vrs/ directory with configuration

# Lock compiler version (optional, uses detected version)
vkg config set solc_version 0.8.19

# Generate preflight manifest
vkg preflight contracts/
```

### Output: Build Manifest

`.vrs/manifest.json`:
```json
{
  "framework": "foundry",
  "solc_version": "0.8.19",
  "optimizer": true,
  "optimizer_runs": 200,
  "remappings": {
    "@openzeppelin/": "lib/openzeppelin-contracts/contracts/",
    "forge-std/": "lib/forge-std/src/"
  },
  "contracts_count": 15,
  "detected_at": "2026-01-07T10:00:00Z"
}
```

### Validation
- [ ] Framework correctly detected
- [ ] Solc version matches project
- [ ] Remappings resolved
- [ ] No missing dependencies

---

## Step 2: Deterministic Build

**Purpose:** Build knowledge graph with reproducible fingerprint.

### Commands

```bash
# Build knowledge graph
vkg build contracts/

# Verify determinism with fingerprint
vkg fingerprint
# Output: Graph fingerprint: abc123def456

# Store fingerprint for CI comparison
vkg fingerprint > .vrs/fingerprint.txt
```

### Output

```
Building knowledge graph...
  Contracts: 15
  Functions: 234
  State variables: 89
  Edges: 1,456

Graph fingerprint: abc123def456
Build time: 12.3s

Completeness: 85% (13/15 contracts analyzed)
  [!] Skipped: YulHelper.sol (inline assembly)
  [!] Skipped: ProxyAdmin.sol (proxy unresolved)
```

### Validation
- [ ] Fingerprint is stable (same code = same fingerprint)
- [ ] Completeness report generated
- [ ] Warnings explain skipped contracts

---

## Step 3: Tier A Detection

**Purpose:** Run deterministic pattern matching. No LLM calls.

### Commands

```bash
# Run Tier A analysis
vkg analyze --tier a

# Generate two-layer output
vkg report --format json > report.json
vkg report --format jsonl > evidence.jsonl

# View findings summary
vkg findings list
```

### Output: Tier A Report

```
Tier A Analysis Complete

Findings: 5
  Critical: 1 (VKG-001)
  High: 2 (VKG-002, VKG-003)
  Medium: 2 (VKG-004, VKG-005)

Pattern Coverage:
  Access Control: 3 patterns matched
  Reentrancy: 1 pattern matched
  Oracle: 0 patterns matched

Run `vkg findings next` to investigate highest priority finding.
```

### Validation
- [ ] All findings have behavioral signatures
- [ ] Evidence references valid
- [ ] Report schema validates

---

## Step 4: Cross-Tool Orchestration (Optional)

**Purpose:** Compare with Slither/Aderyn, deduplicate findings.

### Commands

```bash
# Run orchestration with multiple tools
vkg orchestrate --tools slither,aderyn

# View deduplicated results
vkg orchestrate report

# Export disagreement analysis
vkg orchestrate disagreements > disagreements.json
```

### Output

```
Orchestration Complete

VKG findings: 5
Slither findings: 12
Aderyn findings: 8

After deduplication: 18 unique findings
  VKG-only: 2
  Slither-only: 7
  Aderyn-only: 4
  VKG+Slither: 3
  All tools: 2

Disagreements: 3
  VKG-001: Confirmed by Slither, missed by Aderyn
  VKG-003: VKG-only (high confidence)
  SLI-005: Slither-only (possible FP)
```

### Validation
- [ ] Deduplication logic correct
- [ ] Disagreements flagged for review
- [ ] VKG-only findings highlighted

---

## Step 5: Tier B LLM Analysis (Optional)

**Purpose:** LLM verification of Tier A findings. Requires API key.

### Commands

```bash
# Interactive mode (for development)
vkg analyze --tier b --provider anthropic

# Noninteractive mode (for CI/batch)
vkg analyze --tier b --provider anthropic --noninteractive

# With token budget
vkg analyze --tier b --max-tokens 50000

# Offline mode disables Tier B
VKG_OFFLINE=1 vkg analyze --tier b
# Error: Tier B requires network. Run without VKG_OFFLINE=1
```

### Environment Variables

```bash
# Required for Tier B
export ANTHROPIC_API_KEY="sk-..."
# or
export OPENAI_API_KEY="sk-..."

# Optional: Force offline (disables Tier B)
export VKG_OFFLINE=1
```

### Output

```
Tier B Analysis (Claude claude-sonnet-4-20250514)

Processing 5 findings...

VKG-001 (reentrancy-classic):
  LLM Verdict: CONFIRMED
  Confidence: 0.95 (was 0.92)
  Reasoning: External call precedes state update. No reentrancy guard.

VKG-003 (access-control-missing):
  LLM Verdict: FALSE_POSITIVE
  Confidence: 0.10 (was 0.78)
  Reasoning: Function is internal, called only from guarded functions.

Tier B Complete: 4 confirmed, 1 false positive
Token usage: 12,456 tokens
```

### Validation
- [ ] Tier B respects offline mode
- [ ] Token budget enforced
- [ ] Verdicts update confidence scores

---

## Step 6: Test Scaffolding

**Purpose:** Generate and run verification tests for findings.

### Commands

```bash
# Generate scaffold for specific finding
vkg scaffold VKG-001

# Scaffold for all pending findings
vkg scaffold --all

# Run generated test (Foundry)
forge test --match-test VKG001

# Record verdict after test
vkg finding update VKG-001 --verdict confirmed --evidence "Test passed, exploit reproduced"

# Record false positive
vkg finding update VKG-003 --verdict false_positive --evidence "Internal function, not reachable"
```

### Output: Generated Scaffold

`test/VKG001_Reentrancy.t.sol`:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/Vault.sol";

contract VKG001_ReentrancyTest is Test {
    Vault vault;
    Attacker attacker;

    function setUp() public {
        vault = new Vault();
        attacker = new Attacker(address(vault));
        // Fund vault
        vm.deal(address(vault), 10 ether);
    }

    function test_VKG001_reentrancy_attack() public {
        // Record initial balance
        uint256 initialBalance = address(attacker).balance;

        // Deposit as attacker
        vm.prank(address(attacker));
        vault.deposit{value: 1 ether}();

        // Execute attack
        attacker.attack();

        // Verify drain
        assertGt(address(attacker).balance, initialBalance + 1 ether);
    }
}

contract Attacker {
    Vault vault;
    uint256 attackCount;

    constructor(address _vault) {
        vault = Vault(_vault);
    }

    function attack() external {
        vault.withdraw(1 ether);
    }

    receive() external payable {
        if (attackCount < 5 && address(vault).balance >= 1 ether) {
            attackCount++;
            vault.withdraw(1 ether);
        }
    }
}
```

### Validation
- [ ] Scaffold compiles
- [ ] Test is runnable
- [ ] Verdict recorded in finding

---

## Step 7: Report Generation

**Purpose:** Generate final audit report in multiple formats.

### Commands

```bash
# SARIF for GitHub Security tab
vkg report --format sarif > results.sarif

# JSON for programmatic use
vkg report --format json > report.json

# Human-readable summary
vkg report --format summary

# Full two-layer output
vkg report --format json+evidence --output-dir ./reports/
```

### Output: SARIF Report

GitHub Security tab integration:
```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "VKG",
        "version": "4.0.0",
        "informationUri": "https://github.com/..."
      }
    },
    "results": [{
      "ruleId": "reentrancy-classic",
      "level": "error",
      "message": { "text": "Reentrancy vulnerability in withdraw()" },
      "locations": [{
        "physicalLocation": {
          "artifactLocation": { "uri": "contracts/Vault.sol" },
          "region": { "startLine": 45, "startColumn": 9 }
        }
      }]
    }]
  }]
}
```

### Output: Summary Report

```
VKG AUDIT SUMMARY
=================

Project: MyVault
Date: 2026-01-07
VKG Version: 4.0.0
Graph Fingerprint: abc123def456

FINDINGS
--------
Total: 5
  Confirmed: 3
  False Positive: 1
  Pending: 1

CONFIRMED VULNERABILITIES
-------------------------
1. VKG-001 [CRITICAL] Reentrancy in withdraw()
   Location: Vault.sol:45
   Tier: A (deterministic)
   Verified: Test passed

2. VKG-002 [HIGH] Missing access control on setFee()
   Location: Vault.sol:78
   Tier: A (deterministic)
   Verified: Manual review

3. VKG-004 [MEDIUM] Unbounded loop in distribute()
   Location: Rewards.sol:23
   Tier: A (deterministic)
   Verified: Gas analysis

ANALYSIS COMPLETENESS
--------------------
Coverage: 85% (13/15 contracts)
Skipped: YulHelper.sol, ProxyAdmin.sol
```

### Validation
- [ ] SARIF accepted by GitHub
- [ ] JSON validates against schema
- [ ] Summary includes completeness

---

## Step 8: Learning (Optional)

**Purpose:** Record verdicts for pattern improvement.

### Commands

```bash
# Record all verdicts for learning
vkg learn record

# View pattern metrics
vkg patterns metrics

# View pattern performance by category
vkg patterns metrics --by-category
```

### Output

```
Learning Update Complete

Patterns updated: 3
  reentrancy-classic: +1 true positive
  access-control-missing: +1 false positive
  dos-unbounded-loop: +1 true positive

Pattern Metrics:
  Pattern                  | Precision | Recall | F1
  -------------------------|-----------|--------|-----
  reentrancy-classic       | 92%       | 88%    | 0.90
  access-control-missing   | 71%       | 82%    | 0.76
  dos-unbounded-loop       | 85%       | 75%    | 0.80

Recommendation: access-control-missing needs tuning (precision < 80%)
```

### Validation
- [ ] Verdicts recorded
- [ ] Metrics updated
- [ ] Low-precision patterns flagged

---

## Complete Workflow Example

```bash
# Full audit workflow
cd /path/to/defi-project

# 1. Scope
vkg init
vkg detect-framework .
vkg preflight contracts/

# 2. Build
vkg build contracts/
vkg fingerprint > .vrs/fingerprint.txt

# 3. Tier A
vkg analyze --tier a
vkg report --format json > report.json

# 4. Orchestrate (optional)
vkg orchestrate --tools slither

# 5. Tier B (optional)
export ANTHROPIC_API_KEY="sk-..."
vkg analyze --tier b --noninteractive

# 6. Scaffold and verify
vkg scaffold VKG-001
forge test --match-test VKG001
vkg finding update VKG-001 --verdict confirmed

# 7. Report
vkg report --format sarif > results.sarif
vkg report --format summary

# 8. Learn
vkg learn record
vkg patterns metrics
```

---

## CI Integration

```yaml
# .github/workflows/security-audit.yml
name: BSKG Security Audit

on:
  push:
    paths: ['contracts/**']

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install VKG
        run: pip install alphaswarm slither-analyzer

      - name: Build Graph
        run: |
          vkg build contracts/
          vkg fingerprint > fingerprint.txt

      - name: Run Tier A Analysis
        run: vkg analyze --tier a

      - name: Generate SARIF
        run: vkg report --format sarif > results.sarif

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif

      - name: Validate Report
        run: vkg validate-output report.json
```

---

## Troubleshooting

### Build Failures

```bash
# Check for missing dependencies
vkg preflight contracts/ --verbose

# Common issues:
# - Missing remappings: Add to remappings.txt
# - Wrong solc version: vkg config set solc_version X.Y.Z
# - Import errors: Check lib/ or node_modules/
```

### Tier B Errors

```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Force offline if network issues
VKG_OFFLINE=1 vkg analyze --tier a

# Reduce token budget if timeout
vkg analyze --tier b --max-tokens 10000
```

### Fingerprint Mismatch

```bash
# Compare fingerprints
diff .vrs/fingerprint.txt <(vkg fingerprint)

# Common causes:
# - Code changed since last build
# - Solc version mismatch
# - Different remappings
```

---

## Acceptance Criteria

- [ ] All 8 steps documented with CLI commands
- [ ] Each step has validation criteria
- [ ] CI integration example provided
- [ ] Troubleshooting section complete
- [ ] Tested end-to-end on sample project

---

*LLM Audit Runbook | Version 1.0.0 | 2026-01-07*
