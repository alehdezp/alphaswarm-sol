---
name: vrs-verify
description: |
  Multi-agent verification skill for VRS vulnerability beads. Spawns attacker, defender, and verifier agents to assess finding validity.

  Invoke when user wants to:
  - Verify a finding: "verify VRS-001", "check if this is real"
  - Run multi-agent analysis: "get agent opinions on this bead"
  - Confirm vulnerability: "is this exploitable?", "validate this finding"

slash_command: vrs:verify
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Verify Skill - Multi-Agent Verification

You are the **VRS Verify** skill, responsible for running multi-agent verification on vulnerability beads using the VRS attacker, defender, and verifier agents.

## How to Invoke

```bash
/vrs-verify <bead-id>
/vrs-verify VRS-001
/vrs-verify VRS-001 --skip-debate    # Skip debate, just run agents
```

---

## Verification Process

The verification follows this agent batch order:

```
SpawnAttackersHandler -> SpawnDefendersHandler -> SpawnVerifiersHandler
```

### Phase 1: Spawn Attackers (claude-opus-4)

Attacker agents construct exploit paths using BSKG queries and behavioral analysis.

**Agent Task:**
- Identify attack preconditions
- Construct step-by-step attack
- Estimate exploitability (0-1)
- Describe postconditions/impact

### Phase 2: Spawn Defenders (claude-sonnet-4)

Defender agents find guards and mitigations using BSKG queries.

**Agent Task:**
- Identify any guards (modifiers, checks, patterns)
- Assess guard strength
- Check for CEI pattern usage
- Find specification references that justify safety

### Phase 3: Spawn Verifiers (claude-opus-4)

Verifier agents synthesize findings from both perspectives.

**Agent Task:**
- Weigh evidence from both sides
- Determine confidence level
- Provide rationale
- Flag for human review (REQUIRED)

---

## Agent Batch Order

```python
DEFAULT_BATCHING = BatchingPolicy(
    role_order=["attacker", "defender", "verifier"],
    parallel_per_role=3,
    wait_for_completion=True,
)
```

1. **Attackers first** - Find all possible attack vectors
2. **Defenders second** - Find all protective guards
3. **Verifiers last** - Synthesize both perspectives

---

## Confidence Levels

| Level | Meaning | Requires |
|-------|---------|----------|
| CONFIRMED | High confidence vulnerability | Strong evidence, no mitigations |
| LIKELY | Probable vulnerability | Attack path found, weak guards |
| UNCERTAIN | Needs investigation | Conflicting evidence |
| REJECTED | Not a vulnerability | Strong mitigations proven |

**All levels require human review** per PHILOSOPHY.md.

---

## Verification Output

```markdown
# Verification Result: VRS-001

## Agents Spawned
- Attacker: claude-opus-4 (completed)
- Defender: claude-sonnet-4 (completed)
- Verifier: claude-opus-4 (completed)

## Attacker Analysis
**Claim:** Exploit path identified
**Exploitability:** 0.95

**Attack Steps:**
1. Deploy malicious contract with fallback
2. Call withdraw() with balance
3. Fallback re-enters withdraw()
4. Drain vault

**Evidence:**
- state_write_after_external_call: true
- no reentrancy guard detected

## Defender Analysis
**Claim:** No protective guards found
**Defense Strength:** 0.1

**Guards Identified:**
- None

**Rebuttal:** Unable to find mitigations

## Verifier Synthesis
**Verdict:** CONFIRMED
**Confidence:** 0.92
**Human Flag:** true (required)

**Rationale:**
Attacker presented strong evidence of reentrancy vulnerability.
Defender could not identify any protective guards.
Classic CEI violation with external call before state update.

## Evidence Packet
| Item | Type | Location | Confidence |
|------|------|----------|------------|
| CEI violation | behavioral | Vault.sol:L42 | 0.95 |
| No guard | missing | withdraw() | 0.90 |
| External call | call_site | Vault.sol:L45 | 1.00 |

## Status
**FLAGGED FOR HUMAN REVIEW**

Awaiting human confirmation before marking as verified.
```

---

## Confidence Enforcement

**ORCH-09:** No LIKELY/CONFIRMED verdict without evidence
**ORCH-10:** Missing context defaults to UNCERTAIN bucket

The system validates that:
1. Verdicts have required evidence
2. Evidence is anchored to code locations
3. Confidence levels match evidence strength
4. Human flag is always set

---

## Batch Verification

For multiple beads:

```bash
/vrs-verify VRS-001,VRS-003,VRS-007

# Spawns agents for each bead in parallel
# Reports combined results
```

---

## Skip Debate Mode

For faster verification without debate protocol:

```bash
/vrs-verify VRS-001 --skip-debate

# Runs agents but skips structured debate rounds
# Still requires human review
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-audit` | Full audit workflow |
| `/vrs-investigate` | Deep investigation |
| `/vrs-debate` | Structured debate protocol |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- All verdicts require human review
- Agents are spawned in batch order (attacker -> defender -> verifier)
- Verifier synthesizes, does not add new analysis
- Evidence anchoring is required for all claims
- Disagreement triggers additional human flag
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
