---
name: vkg-investigate
description: |
  Deep investigation skill for BSKG vulnerability beads. Loads bead context, shows investigation guide, and provides tools for manual analysis.

  Invoke when user wants to:
  - Investigate a finding: "investigate VKG-001", "deep dive into this bead"
  - Understand a vulnerability: "explain this finding", "show me the attack path"
  - Review bead details: "what does VKG-042 mean", "show bead context"

slash_command: vkg:investigate
context: fork

tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)
  - Bash(uv run python*)

hooks:
  PreToolUse:
    - tool: Read
      match: ".vrs/beads/*.yaml"
      command: "echo 'Loading bead context...'"
---

# BSKG Investigate Skill - Deep Vulnerability Investigation

You are the **VKG Investigate** skill, responsible for deep investigation of individual vulnerability beads found during BSKG audits.

## How to Invoke

```bash
/vrs-investigate <bead-id>
/vrs-investigate VKG-001
/vrs-investigate VKG-042 --show-evidence
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

From `src/true_vkg/beads/schema.py`:

```python
@dataclass
class VulnerabilityBead:
    id: str                           # "VKG-001"
    pattern_id: str                   # "vm-001" (pattern that matched)
    severity: str                     # "critical", "high", "medium", "low"
    title: str                        # Human-readable title
    description: str                  # Detailed description

    # Evidence
    evidence: Dict[str, Any]          # Pattern match evidence
    code_locations: List[str]         # File:line references
    behavioral_signature: str         # "R:bal->X:out->W:bal"

    # Pool association (Phase 4)
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

```python
from true_vkg.beads import BeadStorage

storage = BeadStorage(Path(".vrs/beads"))
bead = storage.load(bead_id)

print(f"Pattern: {bead.pattern_id}")
print(f"Severity: {bead.severity}")
print(f"Status: {bead.status.value}")
```

### Step 2: Review Evidence

**Code Locations:**
```python
for loc in bead.code_locations:
    print(f"  {loc}")  # contracts/Vault.sol:L42

# Read the actual code
for loc in bead.code_locations:
    file_path, line = loc.rsplit(":", 1)
    # Display surrounding context
```

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

```python
from true_vkg.queries import PatternLoader

loader = PatternLoader()
pattern = loader.load(bead.pattern_id)

print(f"Pattern: {pattern.name}")
print(f"Description: {pattern.description}")
print(f"Attack Scenarios: {pattern.attack_scenarios}")
```

### Step 4: Check Guards

Look for protective measures that might prevent exploitation:

```python
# Check bead evidence for guards
guards = bead.evidence.get("guards", [])
for guard in guards:
    print(f"  Guard: {guard['type']} - {guard['name']}")
    print(f"  Location: {guard['location']}")
```

---

## Investigation Guide Output

```markdown
# Investigation: VKG-001

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
- [ ] Run /vrs-verify VKG-001 for multi-agent verification
- [ ] Check for inherited guards in base contracts
- [ ] Review related functions for cross-function reentrancy
```

---

## Investigation Commands

### Show Full Context
```bash
/vrs-investigate VKG-001 --full

# Shows:
# - Complete bead data
# - All evidence items
# - Related beads
# - Pool context
```

### Show Attack Path
```bash
/vrs-investigate VKG-001 --attack

# Shows:
# - Attack preconditions
# - Step-by-step exploit
# - Expected impact
# - Postconditions
```

### Show Guards
```bash
/vrs-investigate VKG-001 --guards

# Shows:
# - Detected guards
# - Guard strength
# - Potential bypasses
```

### Compare Similar Beads
```bash
/vrs-investigate VKG-001 --similar

# Shows:
# - Other beads with same pattern
# - Cross-function relationships
# - Related vulnerabilities
```

---

## Bead Context for LLM

From `src/true_vkg/context/integrations/bead.py`:

```python
from true_vkg.context.integrations.bead import BeadContextProvider

provider = BeadContextProvider(context_pack, token_budget=4000)
bead_context = provider.get_context(bead)

# Returns:
# - Relevant roles (owner, admin, user)
# - Applicable assumptions
# - Relevant invariants
# - Value flows touching this code
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

## Notes

- Investigation is a human-guided process
- Beads should be reviewed before verification
- Evidence anchoring helps understand context
- Check for cross-function relationships
- Consider business logic context from ProtocolContextPack
