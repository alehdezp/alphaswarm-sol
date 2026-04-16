---
name: vkg-verify
description: |
  Multi-agent verification skill for BSKG vulnerability beads. Spawns attacker, defender, and verifier agents to assess finding validity.

  Invoke when user wants to:
  - Verify a finding: "verify VKG-001", "check if this is real"
  - Run multi-agent analysis: "get agent opinions on this bead"
  - Confirm vulnerability: "is this exploitable?", "validate this finding"

slash_command: vkg:verify
context: fork

tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)
  - Task

hooks:
  PreToolUse:
    - tool: Task
      match: "*vkg-attacker*"
      command: "echo 'Spawning attacker agent (claude-opus-4)...'"
    - tool: Task
      match: "*vkg-defender*"
      command: "echo 'Spawning defender agent (claude-sonnet-4)...'"
    - tool: Task
      match: "*vkg-verifier*"
      command: "echo 'Spawning verifier agent (claude-opus-4)...'"
---

# BSKG Verify Skill - Multi-Agent Verification

You are the **VKG Verify** skill, responsible for running multi-agent verification on vulnerability beads using the BSKG attacker, defender, and verifier agents.

## How to Invoke

```bash
/vrs-verify <bead-id>
/vrs-verify VKG-001
/vrs-verify VKG-001 --skip-debate    # Skip debate, just run agents
```

---

## Verification Process

Per `src/true_vkg/orchestration/handlers.py`:

```
SpawnAttackersHandler -> SpawnDefendersHandler -> SpawnVerifiersHandler
```

### Phase 1: Spawn Attackers (claude-opus-4)

Attacker agents construct exploit paths:

```python
from true_vkg.agents import AttackerAgent, AgentContext

# Create agent context from bead
context = AgentContext.from_bead(bead, graph)

# Spawn attacker
attacker = AttackerAgent(model="claude-opus-4")
attack_result = attacker.analyze(context)

if attack_result.matched and attack_result.attack:
    print(f"Attack: {attack_result.attack.category.value}")
    print(f"Exploitability: {attack_result.attack.exploitability_score}")
    for step in attack_result.attack.attack_steps:
        print(f"  Step: {step.action}")
```

### Phase 2: Spawn Defenders (claude-sonnet-4)

Defender agents find guards and mitigations:

```python
from true_vkg.agents import DefenderAgent

defender = DefenderAgent(model="claude-sonnet-4")
defense_result = defender.analyze(context)

if defense_result.matched and defense_result.defenses:
    print(f"Defenses: {len(defense_result.defenses)}")
    for defense in defense_result.defenses:
        print(f"  Guard: {defense.guards_identified}")
        print(f"  Strength: {defense.strength}")
```

### Phase 3: Spawn Verifiers (claude-opus-4)

Verifier agents synthesize findings:

```python
from true_vkg.agents import VerifierAgent

verifier = VerifierAgent(model="claude-opus-4")
verification = verifier.verify(context, attack_result, defense_result)

print(f"Verdict: {verification.verdict}")
print(f"Confidence: {verification.confidence}")
print(f"Rationale: {verification.rationale}")
```

---

## Agent Batch Order

From `src/true_vkg/orchestration/rules.py`:

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

## Agent Spawning

Use Task tool to spawn each agent:

### Attacker Agent
```
Use Task tool with:
  subagent_type: "vkg-attacker"
  description: "Construct exploit path for VKG-001"
  prompt: |
    Analyze this vulnerability bead and construct an exploit path.

    Bead: VKG-001
    Pattern: vm-001 (Classic Reentrancy)
    Severity: Critical

    Code Location: contracts/Vault.sol:L42
    Function: withdraw(uint256 amount)

    Evidence:
    - state_write_after_external_call: true
    - has_reentrancy_guard: false
    - visibility: external

    Your task:
    1. Identify attack preconditions
    2. Construct step-by-step attack
    3. Estimate exploitability (0-1)
    4. Describe postconditions/impact
```

### Defender Agent
```
Use Task tool with:
  subagent_type: "vkg-defender"
  description: "Find defenses for VKG-001"
  prompt: |
    Analyze this vulnerability bead and find protective guards.

    Bead: VKG-001
    Pattern: vm-001 (Classic Reentrancy)

    Attacker Claims:
    - {summarize attacker findings}

    Your task:
    1. Identify any guards (modifiers, checks, patterns)
    2. Assess guard strength
    3. Check for CEI pattern usage
    4. Find specification references that justify safety
```

### Verifier Agent
```
Use Task tool with:
  subagent_type: "vkg-verifier"
  description: "Synthesize verdict for VKG-001"
  prompt: |
    Synthesize attacker and defender arguments into a verdict.

    Bead: VKG-001

    Attacker Position:
    {attacker_claim}

    Defender Position:
    {defender_claim}

    Your task:
    1. Weigh evidence from both sides
    2. Determine confidence level
    3. Provide rationale
    4. Flag for human review (REQUIRED)
```

---

## Confidence Levels

From `src/true_vkg/orchestration/schemas.py`:

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
# Verification Result: VKG-001

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

From `src/true_vkg/orchestration/confidence.py`:

```python
from true_vkg.orchestration import ConfidenceEnforcer

enforcer = ConfidenceEnforcer()

# Validate verdict has required evidence
validation = enforcer.validate(verdict)
if not validation.valid:
    for error in validation.errors:
        print(f"Validation error: {error.message}")

# Enforce rules (ORCH-09, ORCH-10)
enforced_verdict = enforcer.enforce(verdict)
```

**ORCH-09:** No LIKELY/CONFIRMED verdict without evidence
**ORCH-10:** Missing context defaults to UNCERTAIN bucket

---

## Batch Verification

For multiple beads:

```bash
/vrs-verify VKG-001,VKG-003,VKG-007

# Spawns agents for each bead in parallel
# Reports combined results
```

---

## Skip Debate Mode

For faster verification without debate protocol:

```bash
/vrs-verify VKG-001 --skip-debate

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

## Notes

- All verdicts require human review
- Agents are spawned in batch order (attacker -> defender -> verifier)
- Verifier synthesizes, does not add new analysis
- Evidence anchoring is required for all claims
- Disagreement triggers additional human flag
