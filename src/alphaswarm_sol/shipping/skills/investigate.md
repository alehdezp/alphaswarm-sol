---
name: vrs-investigate
description: |
  Deep investigation skill for VRS vulnerability beads. Loads bead context, shows investigation guide, and provides tools for manual analysis.

  Invoke when user wants to:
  - Investigate a finding: "investigate VRS-001", "deep dive into this bead"
  - Understand a vulnerability: "explain this finding", "show me the attack path"
  - Review bead details: "what does VRS-042 mean", "show bead context"

slash_command: vrs:investigate
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Investigate Skill - Deep Vulnerability Investigation

You are the **VRS Investigate** skill, responsible for deep investigation of individual vulnerability beads found during VRS audits.

## How to Invoke

```bash
/vrs-investigate <bead-id>
/vrs-investigate VRS-001
/vrs-investigate VRS-042 --show-evidence
```

---

## What This Skill Does

1. **Load Bead Context** - Retrieves full bead data from storage
2. **Show Investigation Guide** - Provides structured analysis framework
3. **Display Evidence** - Shows code locations, behavioral signatures
4. **Explain Attack Path** - Describes how the vulnerability could be exploited
5. **Suggest Verification** - Recommends next steps for confirmation

---

## Bead Structure

```python
@dataclass
class VulnerabilityBead:
    id: str                           # "VRS-001"
    pattern_id: str                   # "vm-001" (pattern that matched)
    severity: str                     # "critical", "high", "medium", "low"
    title: str                        # Human-readable title
    description: str                  # Detailed description

    # Evidence
    evidence: Dict[str, Any]          # Pattern match evidence
    code_locations: List[str]         # File:line references
    behavioral_signature: str         # "R:bal->X:out->W:bal"

    # Pool association
    pool_id: Optional[str]            # Parent pool

    # Debate fields
    attacker_claims: List[DebateClaim]
    defender_claims: List[DebateClaim]
    verifier_claims: List[DebateClaim]

    # Work state for agent resumption
    work_state: Dict[str, Any]
    last_agent: Optional[str]
    last_updated: Optional[datetime]

    # Status
    status: BeadStatus                # OPEN, INVESTIGATING, VERIFIED, etc.
    human_flag: bool                  # Requires human review
```

---

## Investigation Framework

### Step 1: Load Bead

```bash
# Load bead from storage
alphaswarm orchestrate bead-info VRS-001

# Output shows:
# - Pattern ID and severity
# - Code locations
# - Evidence details
# - Current status
```

### Step 2: Review Evidence

**Code Locations:**
Use Read tool to examine the actual code at the locations mentioned in the bead.

**Behavioral Signature:**
```
Signature: R:bal->X:out->W:bal

Interpretation:
  R:bal = Reads user balance
  X:out = External call (transfers value out)
  W:bal = Writes user balance

Vulnerability: CEI violation - state written AFTER external call
```

### Step 3: Understand Pattern

```bash
# Load pattern details
alphaswarm query "pattern:vm-001" --info

# Shows:
# - Pattern name and description
# - Attack scenarios
# - Detection criteria
```

### Step 4: Check Guards

Look for protective measures that might prevent exploitation:

```bash
# Use BSKG queries to check for guards
alphaswarm query "FIND functions WHERE id = '<function_id>' AND has_reentrancy_guard"
```

---

## Investigation Guide Output

```markdown
# Investigation: VRS-001

## Summary
**Pattern:** vm-001 (Classic Reentrancy)
**Severity:** Critical
**Status:** INVESTIGATING

## Code Location
**File:** contracts/Vault.sol:L42
**Function:** withdraw(uint256 amount)

```solidity
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);  // R:bal
    (bool success, ) = msg.sender.call{value: amount}("");  // X:out
    require(success);
    balances[msg.sender] -= amount;  // W:bal (AFTER external call!)
}
```

## Behavioral Signature
```
R:bal -> X:out -> W:bal
```
State is written AFTER external call - classic reentrancy pattern.

## Pattern Evidence
| Property | Value |
|----------|-------|
| visibility | external |
| has_external_calls | true |
| state_write_after_external_call | true |
| has_reentrancy_guard | false |

## Attack Scenario
1. Attacker calls withdraw() with valid balance
2. Fallback function re-enters withdraw()
3. Balance check passes (not yet updated)
4. ETH sent again
5. Repeat until vault drained

## Guards Detected
- None found

## Verification Steps
1. Confirm no reentrancy guard (nonReentrant modifier)
2. Check if CEI pattern is followed elsewhere
3. Verify external call can trigger callback
4. Test with Foundry reentrancy PoC

## Recommended Actions
- [ ] Run /vrs-verify VRS-001 for multi-agent verification
- [ ] Check for inherited guards in base contracts
- [ ] Review related functions for cross-function reentrancy
```

---

## Investigation Commands

### Show Full Context
```bash
/vrs-investigate VRS-001 --full

# Shows:
# - Complete bead data
# - All evidence items
# - Related beads
# - Pool context
```

### Show Attack Path
```bash
/vrs-investigate VRS-001 --attack

# Shows:
# - Attack preconditions
# - Step-by-step exploit
# - Expected impact
# - Postconditions
```

### Show Guards
```bash
/vrs-investigate VRS-001 --guards

# Shows:
# - Detected guards
# - Guard strength
# - Potential bypasses
```

### Compare Similar Beads
```bash
/vrs-investigate VRS-001 --similar

# Shows:
# - Other beads with same pattern
# - Cross-function relationships
# - Related vulnerabilities
```

---

## Status Transitions

| From | To | Trigger |
|------|----|---------|
| OPEN | INVESTIGATING | /vrs-investigate called |
| INVESTIGATING | NEEDS_VERIFICATION | Investigation complete |
| NEEDS_VERIFICATION | VERIFIED | /vrs-verify passes |
| VERIFIED | FLAGGED_FOR_HUMAN | Always (per PHILOSOPHY.md) |

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-audit` | Run full audit workflow |
| `/vrs-verify` | Multi-agent verification |
| `/vrs-debate` | Structured debate protocol |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Investigation is a human-guided process
- Beads should be reviewed before verification
- Evidence anchoring helps understand context
- Check for cross-function relationships
- Consider business logic context from ProtocolContextPack
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
