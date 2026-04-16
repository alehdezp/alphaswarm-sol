---
name: vrs-audit
description: |
  Main VRS security audit skill. Triggers the full execution loop for automated vulnerability detection with human checkpoints.

  Invoke when user wants to:
  - Run security audit: "audit these contracts", "check for vulnerabilities", "/vrs-audit"
  - Start new audit workflow: "scan this codebase", "analyze for security issues"
  - Create audit pool: "start security analysis", "begin audit"

  This skill orchestrates the complete VRS pipeline:
  1. Initialize pool with scope
  2. Build knowledge graph from Solidity
  3. Load protocol context
  4. Detect patterns and create beads
  5. Run multi-agent verification (attacker/defender/verifier)
  6. Flag findings for human review
  7. Generate final report

slash_command: vrs:audit
context: fork
disable-model-invocation: true

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Audit Skill - Security Audit Orchestration

You are the **VRS Audit** skill, responsible for orchestrating complete security audits of Solidity codebases using the VRS (Vulnerability Research Skills) system.

## Philosophy

From PHILOSOPHY.md:
- **No autonomous verdicts** - All findings require human review
- **Evidence-linked findings** - Every vulnerability has code location + behavioral signature
- **Semantic detection** - Detect operations, not function names
- **Two-tier detection** - Tier A (deterministic) + Tier B (LLM-verified)

## How to Invoke

```bash
/vrs-audit <path-to-contracts>
/vrs-audit ./contracts/
/vrs-audit --scope "Vault,Token" ./src/
```

---

## Execution Flow

The audit follows the ExecutionLoop phases:

```
INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE
```

### Phase 1: INTAKE
**Initialize audit pool and scope**

```bash
# Create pool with scope
alphaswarm orchestrate start audit-001 --scope contracts/
```

### Phase 2: CONTEXT
**Build knowledge graph and load protocol context**

```bash
# Build BSKG from Solidity
alphaswarm build-kg contracts/ --output .vrs/graph.json

# Load protocol context (if available)
alphaswarm context show
```

### Phase 3: BEADS
**Run pattern detection and create investigation beads**

```bash
# Run pattern detection
alphaswarm query "pattern:*" --graph .vrs/graph.json

# Create beads for findings
# This happens automatically during pool execution
```

### Phase 4: EXECUTE
**Spawn multi-agent verification**

Use the orchestration system to spawn verification agents:
- Attackers - construct exploit paths
- Defenders - find guards and mitigations
- Verifiers - synthesize verdicts

### Phase 5: VERIFY
**Run structured debate protocol**

For each bead requiring verification, run debate protocol with evidence anchoring.

### Phase 6: INTEGRATE
**Collect verdicts and prepare report**

Enforce confidence rules and collect all verdicts.

### Phase 7: COMPLETE
**Generate final report with human checkpoints**

All findings are flagged for human review.

---

## Usage Examples

### Basic Audit
```bash
/vrs-audit ./contracts/

# Output:
# Initializing audit pool...
# Building knowledge graph from 15 Solidity files...
# Detected 8 potential vulnerabilities
# Spawning attacker agents...
# Spawning defender agents...
# Running verification debates...
#
# HUMAN CHECKPOINT: 3 findings require review
# - VRS-001: Reentrancy in withdraw() [LIKELY]
# - VRS-003: Missing access control [CONFIRMED]
# - VRS-007: Oracle manipulation [UNCERTAIN]
```

### Scoped Audit
```bash
/vrs-audit --scope "Vault,LendingPool" ./contracts/

# Only analyzes Vault and LendingPool contracts
```

### Resume from Checkpoint
```bash
/vrs-audit --resume audit-001

# Resumes from last checkpoint after human review
```

---

## Output Format

### Audit Summary
```markdown
# VRS Audit Report: my-defi-protocol

**Pool ID:** audit-001
**Scope:** contracts/*.sol (15 files)
**Duration:** 4m 32s

## Findings Summary

| Confidence | Count | Status |
|------------|-------|--------|
| CONFIRMED  | 1     | Human Review Required |
| LIKELY     | 2     | Human Review Required |
| UNCERTAIN  | 3     | Human Review Required |
| REJECTED   | 4     | No action needed |

## Critical Findings

### VRS-003: Missing Access Control
**Confidence:** CONFIRMED
**Location:** contracts/Vault.sol:L42
**Function:** setOwner(address)

**Attack Path:**
1. Call setOwner() with attacker address
2. Attacker becomes owner
3. Drain funds via withdrawAll()

**Evidence:**
- writes_privileged_state: true
- has_access_gate: false
- visibility: public

**Debate Summary:**
- Attacker: Exploit path identified, exploitability: 0.95
- Defender: No guards identified
- Verdict: CONFIRMED (human review required)
```

---

## Checkpoint Handling

The audit pauses at these checkpoints:

1. **Human Flag Checkpoint** - When findings need review
2. **Confidence Checkpoint** - When evidence is uncertain
3. **Debate Disagreement** - When attacker/defender can't resolve

### Resuming After Review
```bash
# After human reviews flagged findings:
/vrs-audit --resume audit-001 --approved VRS-001,VRS-003

# Continue with remaining work
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-investigate` | Deep-dive into specific bead |
| `/vrs-verify` | Run multi-agent verification on bead |
| `/vrs-debate` | Run structured debate on bead |
| `/vrs-health-check` | Validate VRS installation |

---

## Architecture Reference

```
Audit Pool
    |
    +-- Scope (files, contracts)
    |
    +-- Beads (VulnerabilityBead[])
    |       |
    |       +-- pattern_id, severity, evidence
    |       +-- attacker_claims, defender_claims, verifier_claims
    |       +-- work_state (agent resumption)
    |
    +-- Verdicts (Verdict[])
    |       |
    |       +-- confidence: CONFIRMED | LIKELY | UNCERTAIN | REJECTED
    |       +-- evidence_packet with code locations
    |       +-- debate_record
    |       +-- human_flag: True (always)
    |
    +-- Status: INTAKE -> ... -> COMPLETE
```

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Error Handling

| Error | Resolution |
|-------|------------|
| No Solidity files found | Verify path contains .sol files |
| Graph build failed | Check Slither installation with /vrs-health-check |
| Agent spawn failed | Check model availability |
| Pool not found | Use alphaswarm orchestrate list to see available pools |

---

## Notes

- All verdicts require human review per PHILOSOPHY.md
- Debate outcomes are always human-flagged
- Evidence anchoring is required (code locations)
- Batch spawning: attackers -> defenders -> verifiers
- Checkpoints pause for human interaction
- This is a USER-CONTROLLED skill (disable-model-invocation: true)
