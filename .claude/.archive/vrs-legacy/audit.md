---
name: vkg-audit
description: |
  Main BSKG security audit skill. Triggers the full execution loop for automated vulnerability detection with human checkpoints.

  Invoke when user wants to:
  - Run security audit: "audit these contracts", "check for vulnerabilities", "/vrs-audit"
  - Start new audit workflow: "scan this codebase", "analyze for security issues"
  - Create audit pool: "start security analysis", "begin audit"

  This skill orchestrates the complete BSKG pipeline:
  1. Initialize pool with scope
  2. Build knowledge graph from Solidity
  3. Load protocol context
  4. Detect patterns and create beads
  5. Run multi-agent verification (attacker/defender/verifier)
  6. Flag findings for human review
  7. Generate final report

slash_command: vkg:audit
context: fork

tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run alphaswarm*)
  - Bash(ls*)
  - Task
  - TodoWrite

hooks:
  PreToolUse:
    - tool: Task
      match: "*vkg-attacker*"
      command: "echo 'Spawning attacker agent...'"
    - tool: Task
      match: "*vkg-defender*"
      command: "echo 'Spawning defender agent...'"
    - tool: Task
      match: "*vkg-verifier*"
      command: "echo 'Spawning verifier agent...'"
  PostToolUse:
    - tool: Bash
      match: "*alphaswarm*"
      command: "echo 'VKG command complete'"
---

# BSKG Audit Skill - Security Audit Orchestration

You are the **VKG Audit** skill, responsible for orchestrating complete security audits of Solidity codebases using the BSKG (Vulnerability Knowledge Graph) system.

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

The audit follows the ExecutionLoop phases from `src/true_vkg/orchestration/loop.py`:

```
INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE
```

### Phase 1: INTAKE
**Initialize audit pool and scope**

```python
from true_vkg.orchestration import Pool, Scope, PoolManager

# Create scope from user input
scope = Scope(
    files=["contracts/*.sol"],
    contracts=["Vault", "Token"],  # Optional: specific contracts
)

# Create pool
pool = Pool(id="audit-001", scope=scope)

# Save to storage
manager = PoolManager(Path(".vrs/pools"))
manager.save_pool(pool)
```

### Phase 2: CONTEXT
**Build knowledge graph and load protocol context**

```python
from true_vkg.kg.builder import VKGBuilder

# Build BSKG from Solidity
builder = VKGBuilder()
graph = builder.build(scope.files)

# Load protocol context (if available)
from true_vkg.context import ContextPackStorage
context_storage = ContextPackStorage(Path(".vrs/context"))
protocol_context = context_storage.load(pool.id)
```

### Phase 3: BEADS
**Run pattern detection and create investigation beads**

```python
from true_vkg.queries import PatternExecutor
from true_vkg.beads import VulnerabilityBead, BeadStorage

executor = PatternExecutor(graph)
findings = executor.run_all_patterns()

# Create beads for each finding
bead_storage = BeadStorage(Path(".vrs/beads"))
for finding in findings:
    bead = VulnerabilityBead.from_pattern_match(finding)
    bead.pool_id = pool.id
    bead_storage.save(bead)
    pool.add_bead(bead.id)
```

### Phase 4: EXECUTE
**Spawn multi-agent verification**

```python
from true_vkg.orchestration import ExecutionLoop, create_default_handlers

loop = ExecutionLoop(manager)
handlers = create_default_handlers(manager)

# Register handlers
for action, handler in handlers.items():
    loop.register_handler(action, handler)

# Batch spawning order per PHILOSOPHY.md:
# 1. Attackers - construct exploit paths
# 2. Defenders - find guards and mitigations
# 3. Verifiers - synthesize verdicts
```

**Agent spawning:**
```
Use Task tool with:
  subagent_type: "vkg-attacker"   # Model: claude-opus-4
  subagent_type: "vkg-defender"   # Model: claude-sonnet-4
  subagent_type: "vkg-verifier"   # Model: claude-opus-4
```

### Phase 5: VERIFY
**Run structured debate protocol**

```python
from true_vkg.orchestration import DebateOrchestrator, run_debate

# For each bead requiring verification
for bead_id in pool.beads:
    verdict = run_debate(
        bead_id=bead_id,
        evidence=bead.evidence,
        attacker_context={"agent_context": ctx},
        defender_context={"agent_context": ctx},
    )

    # Verdict is ALWAYS human-flagged
    assert verdict.human_flag == True
```

### Phase 6: INTEGRATE
**Collect verdicts and prepare report**

```python
from true_vkg.orchestration import ConfidenceEnforcer

enforcer = ConfidenceEnforcer()
for bead_id in pool.beads:
    verdict = pool.get_verdict(bead_id)

    # Enforce confidence rules (ORCH-09, ORCH-10)
    validated_verdict = enforcer.enforce(verdict)
```

### Phase 7: COMPLETE
**Generate final report with human checkpoints**

```python
from true_vkg.orchestration import generate_report, format_markdown_report

report = generate_report(pool)
markdown = format_markdown_report(report)

# All findings flagged for human review
print(f"Findings requiring review: {len(pool.get_flagged_beads())}")
```

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
# - VKG-001: Reentrancy in withdraw() [LIKELY]
# - VKG-003: Missing access control [CONFIRMED]
# - VKG-007: Oracle manipulation [UNCERTAIN]
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
# BSKG Audit Report: my-defi-protocol

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

### VKG-003: Missing Access Control
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

## Configuration Options

### LoopConfig
```python
from true_vkg.orchestration import LoopConfig

config = LoopConfig(
    auto_advance=True,          # Auto-advance phases when ready
    pause_on_human_flag=True,   # Pause for human review (required)
    max_iterations=100,         # Safety limit
    verbose=True,               # Detailed logging
)
```

### DebateConfig
```python
from true_vkg.orchestration import DebateConfig

debate_config = DebateConfig(
    max_rebuttal_rounds=2,      # Attacker/defender back-and-forth
    require_evidence=True,      # Claims must have code locations
    auto_flag_human=True,       # Always flag for human (required)
)
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
/vrs-audit --resume audit-001 --approved VKG-001,VKG-003

# Continue with remaining work
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-investigate` | Deep-dive into specific bead |
| `/vrs-verify` | Run multi-agent verification on bead |
| `/vrs-debate` | Run structured debate on bead |
| `/pattern-forge` | Create/improve detection patterns |

---

## Architecture Reference

```
Audit Pool (Pool)
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

## Key Modules

| Module | Purpose |
|--------|---------|
| `orchestration/loop.py` | ExecutionLoop with fixed phase sequence |
| `orchestration/pool.py` | PoolManager and PoolStorage |
| `orchestration/router.py` | Thin status-based routing |
| `orchestration/debate.py` | DebateOrchestrator (iMAD protocol) |
| `orchestration/handlers.py` | Phase handlers (13 handlers) |
| `orchestration/confidence.py` | ConfidenceEnforcer validation |

---

## Error Handling

| Error | Resolution |
|-------|------------|
| No Solidity files found | Verify path contains .sol files |
| Graph build failed | Check Slither installation |
| Agent spawn failed | Check model availability |
| Pool not found | Use --list to see available pools |

---

## Notes

- All verdicts require human review per PHILOSOPHY.md
- Debate outcomes are always human-flagged
- Evidence anchoring is required (code locations)
- Batch spawning: attackers -> defenders -> verifiers
- Checkpoints pause for human interaction
