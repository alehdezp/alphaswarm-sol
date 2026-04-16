---
name: vrs-orch-spawn
description: Spawn a worker subagent for delegated work
slash_command: vrs:orch-spawn
context: fork
disable-model-invocation: false
allowed-tools: Bash(alphaswarm:*), Task
---

# Spawn Worker Subagent

Spawn a specialized worker subagent for delegated security investigation work.

## Purpose

Orchestrators delegate complex work to specialized worker agents. This skill enables:

- **Context isolation**: Workers operate in forked contexts to prevent pollution
- **Specialization**: Each worker type has specific capabilities
- **Concurrency control**: Respect system limits on parallel workers
- **Result aggregation**: Workers report back via bead updates

## Worker Types

Available worker types:

### attacker
- **Purpose**: Construct exploit paths for suspected vulnerabilities
- **Capabilities**: Graph queries, exploit analysis, proof-of-concept construction
- **Model**: claude-opus-4 (high reasoning capability)
- **Output**: Exploit path, attack vector, severity assessment

### defender
- **Purpose**: Find guards, mitigations, and protective patterns
- **Capabilities**: Pattern matching, control flow analysis, guard detection
- **Model**: claude-sonnet-4 (efficient for pattern recognition)
- **Output**: Guard locations, mitigation effectiveness, coverage gaps

### verifier
- **Purpose**: Cross-check evidence and validate findings
- **Capabilities**: Evidence validation, false positive detection, confidence scoring
- **Model**: claude-opus-4 (critical reasoning required)
- **Output**: Verification verdict, confidence score, evidence assessment

### investigator
- **Purpose**: General-purpose deep investigation
- **Capabilities**: Multi-tool analysis, code tracing, dependency analysis
- **Model**: claude-sonnet-4 (balanced capability)
- **Output**: Investigation summary, findings, recommendations

## Arguments

When invoking this skill, provide:

- **worker_type**: attacker | defender | verifier | investigator
- **bead_id**: Target bead for investigation
- **context_bundle**: Minimal, focused context for the worker
  - BSKG graph subset
  - Relevant pattern definitions
  - Contract locations
  - Prior findings (if any)

## Concurrency Limits

System enforces these limits:
- **Max 5 subagents total** (all types combined)
- **Max 2 sub-orchestrators** (workers that spawn other workers)

If limits are exceeded, skill will queue work or fail gracefully.

## Execution

```bash
# Spawn attacker agent for bead investigation
alphaswarm orch spawn attacker $BEAD_ID \
  --context "$CONTEXT_BUNDLE"
```

Worker is spawned via Task tool with:
- Isolated forked context
- Minimal context bundle (not full conversation history)
- Bead ID for work tracking
- Result reporting mechanism

## Context Bundle Format

Minimal bundle to prevent context bloat:

```json
{
  "bead_id": "bd-a3f5b912",
  "investigation_type": "reentrancy",
  "target": {
    "contract": "Vault.sol",
    "function": "withdrawAll",
    "location": "line 45-67"
  },
  "graph_subset": {
    "node_id": "Vault.withdrawAll",
    "properties": { /* relevant properties */ },
    "edges": [ /* relevant edges */ ]
  },
  "patterns": ["reentrancy-classic"],
  "prior_findings": []
}
```

## Worker Reporting

Workers report back by:
1. Updating bead status via `/vrs-bead-update`
2. Storing investigation results in bead work state
3. Returning summary to orchestrator

## Example Usage

```bash
# Spawn attacker to verify reentrancy
alphaswarm orch spawn attacker bd-a3f5b912 \
  --context '{"target": "Vault.sol:withdrawAll", "pattern": "reentrancy-classic"}'

# Spawn defender to find guards
alphaswarm orch spawn defender bd-a3f5b912 \
  --context '{"target": "Vault.sol", "find_guards": true}'

# Spawn verifier to validate finding
alphaswarm orch spawn verifier bd-a3f5b912 \
  --context '{"attack_path": "...", "verify_exploitability": true}'
```

## Error Handling

- **Concurrency limit exceeded**: Queues worker or returns error
- **Invalid worker type**: Returns error with valid types
- **Bead not found**: Returns error
- **Context bundle too large**: Warns and truncates to essential fields only
- **Worker spawn failure**: Updates bead to blocked status
