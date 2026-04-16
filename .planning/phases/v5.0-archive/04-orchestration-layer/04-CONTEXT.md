---
phase: 04-orchestration-layer
discussion_started: 2026-01-20
discussion_completed: 2026-01-20
status: context_captured
---

# Phase 4: Orchestration Layer - Context Document

**Phase Goal:** Implement thin, deterministic orchestration with fixed execution loop, canonical artifact schemas (Scope, Evidence Packet, Bead, Pool, Verdict), work state persistence, and confidence enforcement.

## Research Summary

### Frameworks Analyzed

| Framework | Key Insight | Adopted |
|-----------|-------------|---------|
| **Gas Town** (steveyegge) | Mayor/Deacon/Witness roles, hooks as agent inboxes, git-backed beads for persistent work | Persistence model, bead tracking |
| **GSD** (glittercowboy) | Fresh 200k-token context windows per wave, STATE.md for memory, atomic commits | Context hygiene, wave execution |
| **Claude Agent SDK** | Task tool for subagent spawning, session resumption, model selection per agent | Subagent architecture |
| **Claude-Flow** (ruvnet) | Swarm intelligence with Queen/Worker hierarchy, SONA self-learning, consensus protocols | Debate protocol inspiration |
| **iMAD** | Structured debate with claim/counterclaim/rebuttal, evidence anchoring | Multi-agent debate |

### Architecture Decision: Claude-First Installation

VKG installs as skills and subagents in Claude Code:

```
.claude/
├── skills/vkg/
│   ├── audit.md           # /vkg:audit - full security audit
│   ├── investigate.md     # /vkg:investigate - deep dive on finding
│   ├── build.md           # /vkg:build - build knowledge graph
│   ├── verify.md          # /vkg:verify - multi-agent verification
│   └── debate.md          # /vkg:debate - attacker/defender session
├── agents/
│   ├── vkg-attacker.md    # Construct exploit paths (opus)
│   ├── vkg-defender.md    # Search for guards (sonnet)
│   ├── vkg-verifier.md    # Cross-check evidence (opus)
│   ├── vkg-test-builder.md # Generate Foundry tests (sonnet)
│   └── vkg-triage.md      # Classify risk (haiku)
└── commands/vkg.md

.vrs/
├── AGENTS.md              # Agent discovery spec
├── pools/
│   └── {pool-name}/
│       ├── pool.yaml      # Manifest: status, bead list, metadata
│       └── beads/
│           ├── VKG-042.yaml
│           └── ...
├── cache.db               # SQLite query cache
└── config.yaml
```

## Captured Decisions

### 1. Execution Loop Interface

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Trigger method** | Both skills AND natural language | Maximum flexibility; `/vkg:audit` for explicit, NL for exploratory |
| **Verbosity** | Phase checkpoints only | Balance: user knows progress without log spam |
| **Resume behavior** | Auto-resume from last checkpoint | No manual intervention; STATE.md tracks progress |
| **Subagent spawning** | Batch by role | All attackers first, then all defenders, then verifiers; enables parallel execution |

### 2. Artifact Schemas

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Validation strictness** | Auto-repair (infer/fill missing fields) | Pragmatic; don't block on minor schema gaps |
| **Storage format** | Hybrid (YAML + SQLite cache) | YAML for humans, SQLite for fast queries |
| **Agent transcripts** | Summary only | Token efficiency; full transcripts in debug mode only |

### 3. Naming: Pool (not Convoy)

**Decision:** Rename "convoy" to "pool" throughout.

**Rationale:**
- Crypto-native terminology (like liquidity pools, finding pools)
- Familiar to Web3 developers
- Intuitive: beads are "pooled" together for batch processing

**Update Required:** Update all references in docs/PHILOSOPHY.md, .planning/*.md

### 4. Confidence Enforcement

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Confirmed trigger** | Test OR multi-agent consensus | Either is strong enough evidence |
| **Disagreement handling** | Always spawn debate + always flag for human | No auto-resolution; human judgment preserved |

### 5. Debate Protocol

**Adopted:** Structured Debate with Evidence Anchoring

```
┌─────────────────────────────────────────────────────────────┐
│                    BSKG Debate Protocol                       │
├─────────────────────────────────────────────────────────────┤
│ 1. CLAIM ROUND                                               │
│    Attacker: "This is exploitable because [evidence]"        │
│    Defender: "This is safe because [evidence]"               │
│                                                              │
│ 2. REBUTTAL ROUND                                            │
│    Attacker challenges Defender's evidence                   │
│    Defender challenges Attacker's evidence                   │
│                                                              │
│ 3. SYNTHESIS                                                 │
│    Verifier: Weighs evidence quality, produces verdict       │
│    Always outputs: { verdict, confidence, evidence_map,      │
│                      dissenting_opinion, human_flag: true }  │
│                                                              │
│ 4. HUMAN CHECKPOINT                                          │
│    Flagged finding presented with full debate transcript     │
│    Human can: accept, reject, request deeper investigation   │
└─────────────────────────────────────────────────────────────┘
```

**Key Properties:**
- Evidence-anchored: Every argument must cite specific code locations
- Structured rounds: Claim → Rebuttal → Synthesis
- Always human-flagged: No fully autonomous verdicts
- Dissenting opinions preserved: Minority view recorded for human review

## Execution Loop (Fixed)

Based on PHILOSOPHY.md "Agentic Loop 2026":

```
Intake → Context → Beads → Pool → Execute → Verify → Integrate → Learn
  │        │         │       │        │         │         │         │
  │        │         │       │        │         │         │         └─ Update vulndocs
  │        │         │       │        │         │         └─ Merge to evidence
  │        │         │       │        │         └─ Multi-agent debate
  │        │         │       │        └─ Batch by role (parallel)
  │        │         │       └─ Group beads into pools
  │        │         └─ Create beads from targets
  │        └─ Load protocol context pack
  └─ Receive scope (files, contracts)
```

## Two Modes of Operation

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Fully Automatic** | `--auto` flag | Run all phases, write report, human reviews at end |
| **Human-in-Loop** | Interactive (default) | Checkpoint at each phase, human approves continuation |

## Storage Schema

### pool.yaml

```yaml
id: audit-wave-erc4626
status: in_progress
created: 2026-01-20T10:00:00Z
beads:
  - VKG-042
  - VKG-043
  - VKG-044
metadata:
  scope: contracts/ERC4626Vault.sol
  initiated_by: /vkg:audit
current_phase: verify
phases_complete:
  - intake
  - context
  - beads
  - execute
```

### bead.yaml (per finding)

```yaml
id: VKG-042
pool: audit-wave-erc4626
target: ERC4626Vault.deposit
status: flagged_for_human
confidence: likely
evidence:
  - type: behavioral_signature
    value: "R:bal→X:out→W:bal"
    location: "contracts/ERC4626Vault.sol:142"
debate:
  attacker_claim: "..."
  defender_claim: "..."
  rebuttal_round: [...]
  verifier_verdict: "likely"
  dissenting_opinion: "Defender notes guard at L138"
human_flag: true
```

## Requirements Mapping

| Requirement | How Addressed |
|-------------|---------------|
| ORCH-01 | Thin routing layer: orchestrator only routes, persists, enforces |
| ORCH-02 | Scope artifact schema: defined in evidence packets |
| ORCH-03 | Evidence Packet schema: extended with protocol_context |
| ORCH-04 | Bead schema: minimal, as defined above |
| ORCH-05 | Pool schema: replaces "convoy" |
| ORCH-06 | Verdict schema: includes rationale, dissent, human_flag |
| ORCH-07 | Fixed execution loop: 8 steps as defined |
| ORCH-08 | Work state in beads: pool.yaml + bead.yaml |
| ORCH-09 | "No likely/confirmed without evidence": enforced in debate |
| ORCH-10 | Missing context → uncertain: auto-bucket rule |

## Open Questions

None. All gray areas resolved.

## Next Steps

1. Update convoy → pool in all documentation
2. Create detailed plan (04-PLAN.md) with task breakdown
3. Implement skills and agents
4. Implement pool/bead storage
5. Implement debate protocol

---
*Context captured: 2026-01-20*
*Source: /gsd:discuss-phase 4 conversation*
