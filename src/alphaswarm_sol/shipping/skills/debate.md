---
name: vrs-debate
description: |
  Structured debate skill for VRS vulnerability beads. Runs iMAD-inspired attacker/defender debate protocol with evidence anchoring.

  Invoke when user wants to:
  - Run structured debate: "debate VRS-001", "run debate protocol"
  - Resolve conflicting evidence: "attacker and defender disagree"
  - Get detailed analysis: "deep adversarial analysis"

slash_command: vrs:debate
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Debate Skill - Structured Adversarial Debate

You are the **VRS Debate** skill, responsible for running the structured debate protocol between attacker and defender agents for vulnerability assessment.

## How to Invoke

```bash
/vrs-debate <bead-id>
/vrs-debate VRS-001
/vrs-debate VRS-001 --max-rounds 3
```

---

## Debate Protocol

iMAD-inspired protocol:

```
CLAIM ROUND -> REBUTTAL ROUND(S) -> SYNTHESIS -> HUMAN CHECKPOINT
```

### Phase 1: CLAIM
Both sides present initial evidence-anchored arguments.

### Phase 2: REBUTTAL (configurable rounds)
Each side challenges the other's evidence.

### Phase 3: SYNTHESIS
Verifier weighs evidence, produces verdict.

### Phase 4: HUMAN CHECKPOINT
**Always flagged for human review** per PHILOSOPHY.md.

---

## Debate Configuration

```python
@dataclass
class DebateConfig:
    max_rebuttal_rounds: int = 2    # Back-and-forth rounds
    require_evidence: bool = True    # Claims must have code locations
    auto_flag_human: bool = True     # Always flag (required)
```

---

## Debate Phases

### DebatePhase Enum

```python
class DebatePhase(Enum):
    CLAIM = "claim"         # Initial claims
    REBUTTAL = "rebuttal"   # Challenge evidence
    SYNTHESIS = "synthesis" # Verifier weighs
    COMPLETE = "complete"   # Debate finished
```

---

## DebateClaim Structure

```python
@dataclass
class DebateClaim:
    role: str              # "attacker" or "defender"
    claim: str             # Main assertion
    evidence: List[EvidenceItem]  # Code locations, values
    reasoning: str         # Justification
```

**Evidence Anchoring Required:**
Every claim must reference specific code locations.

```python
EvidenceItem(
    type="behavioral",
    value="state_write_after_external_call",
    location="contracts/Vault.sol:L42",
    confidence=0.95,
    source="attacker_agent",
)
```

---

## Debate Workflow

### Step 1: Attacker Claim Round

```
ATTACKER CLAIM:
"Exploit path identified: reentrancy"

EVIDENCE:
1. [attack_step] "Re-enter via fallback" @ Vault.sol:L45 (0.95)
2. [attack_postcondition] "Drain vault balance" @ Vault.sol:L42 (0.90)

REASONING:
"Attack feasibility: HIGH, exploitability: 0.95"
```

### Step 2: Defender Claim Round

```
DEFENDER CLAIM:
"No protective guards found"

EVIDENCE:
(none)

REASONING:
"Unable to identify mitigations"
```

### Step 3: Attacker Rebuttal

```
ATTACKER REBUTTAL:
"Defender provided no guards - attack path remains open"

EVIDENCE:
1. [rebuttal] "No guards identified" (0.80)

REASONING:
"Defender failed to identify any protective guards"
```

### Step 4: Defender Rebuttal

```
DEFENDER REBUTTAL:
"Attack preconditions cannot be satisfied"

EVIDENCE:
1. [precondition_analysis] "Requires privileged access" (0.60)

REASONING:
"Attack requires conditions that cannot be met by external caller"
```

### Step 5: Synthesis

```
SYNTHESIS:
Attacker strength: 0.92
Defender strength: 0.40

Delta: 0.52 (exceeds threshold 0.2)

VERDICT: LIKELY (attacker wins)
RATIONALE: "Attacker: Exploit path identified | Defender: No guards | Rebuttals: 2 rounds"
DISSENT: None (defender evidence too weak)
```

---

## Debate Output

```markdown
# Debate Result: VRS-001

## Summary
**Rounds:** 3 (1 claim + 2 rebuttal)
**Duration:** 45s
**Verdict:** LIKELY
**Human Flag:** true (required)

## Round 1: CLAIM

### Attacker
**Claim:** Exploit path identified: reentrancy
**Evidence:**
- [attack_step] Re-enter via fallback @ Vault.sol:L45 (0.95)
- [attack_postcondition] Drain vault balance @ Vault.sol:L42 (0.90)

### Defender
**Claim:** No protective guards found
**Evidence:** (none)

## Round 2: REBUTTAL

### Attacker
**Claim:** Defender provided no guards - attack path remains open
**Challenge:** Defender's lack of evidence

### Defender
**Claim:** Attack preconditions cannot be satisfied
**Challenge:** Attack requires privileged access

## Round 3: REBUTTAL

### Attacker
**Claim:** Precondition analysis is speculative
**Evidence:** [code_analysis] Function is external, no access gate (0.95)

### Defender
**Claim:** (no further rebuttal)

## Synthesis

| Metric | Attacker | Defender |
|--------|----------|----------|
| Evidence count | 4 | 1 |
| Avg confidence | 0.92 | 0.40 |
| Strength | 0.92 | 0.40 |

**Outcome:** Attacker wins (delta: 0.52)
**Confidence:** LIKELY

## Status
**FLAGGED FOR HUMAN REVIEW**
```

---

## Confidence Assessment

```python
# Calculate evidence strength
attacker_strength = avg(e.confidence for e in attacker.evidence)
defender_strength = avg(e.confidence for e in defender.evidence)

# Determine outcome
if abs(attacker_strength - defender_strength) < 0.2:
    return VerdictConfidence.UNCERTAIN  # Close contest

if attacker_strength > defender_strength:
    return VerdictConfidence.LIKELY     # Attacker wins

return VerdictConfidence.REJECTED       # Defender wins
```

---

## Dissent Recording

When defender has strong evidence (avg > 0.7) but loses:

```python
dissent = f"Defender notes: {defender_claim.claim}"
```

Dissent is recorded in the debate record for human review.

---

## Early Exit

Debate exits early when no new arguments:

```python
for i in range(config.max_rebuttal_rounds):
    rebuttal = run_rebuttal_round(...)

    # Early exit if no new arguments
    if not rebuttal.attacker_argument and not rebuttal.defender_argument:
        break
```

---

## Configuration Options

```bash
# Default (2 rebuttal rounds)
/vrs-debate VRS-001

# Extended debate (3 rounds)
/vrs-debate VRS-001 --max-rounds 3

# Quick debate (1 round)
/vrs-debate VRS-001 --max-rounds 1
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-audit` | Full audit workflow |
| `/vrs-investigate` | Deep investigation |
| `/vrs-verify` | Multi-agent verification |

---

## Key Principles

1. **Evidence Anchoring** - All claims reference code locations
2. **Structured Protocol** - Fixed phases, not free-form
3. **Verifier Synthesizes** - Does not add new analysis
4. **Human Always Reviews** - Debate outcomes are never autonomous
5. **Dissent Recording** - Strong losing arguments preserved

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Debate is the most thorough verification method
- Use for high-severity or uncertain findings
- All debate outcomes require human review
- Disagreement triggers additional scrutiny
- Evidence quality matters more than quantity
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
