# Flexible Workflow Design for AlphaSwarm.sol

## Executive Summary

This design introduces **20 new/enhanced skills** and CLI commands organized into **6 control categories** for granular workflow control:

1. **Stage Control** - Pipeline stage filtering
2. **Pattern Control** - Pattern selection and execution
3. **Finding Management** - Finding lifecycle operations
4. **Investigation Control** - Targeted investigation
5. **Workflow Control** - Session management
6. **Tier B/C Control** - Verification triggers

---

## New Skills & Commands

### 1. Stage Control

| Command | Description |
|---------|-------------|
| `/vrs-audit --skip-stages 3,6` | Skip context and debate stages |
| `/vrs-audit --only-stages 2,4` | Run only graph and patterns |
| `/vrs-audit --stop-after 4` | Stop after patterns stage |
| `/vrs-run-stage 2` | Run single stage in isolation |

### 2. Pattern Control

| Command | Description |
|---------|-------------|
| `/vrs-run-pattern reentrancy-classic contracts/Vault.sol` | Run single pattern |
| `/vrs-run-patterns --category access-control contracts/` | Run by category |
| `/vrs-list-patterns --tier A` | List available patterns |

### 3. Finding Management

| Command | Description |
|---------|-------------|
| `/vrs-discard-finding <id> --reason "..."` | Mark as false positive |
| `/vrs-prioritize-finding <id>` | Escalate to agent investigation |
| `/vrs-list-findings --status pending` | List findings by status |

### 4. Investigation Control

| Command | Description |
|---------|-------------|
| `/vrs-investigate --vulnerability-type oracle contracts/` | Target by vuln type |
| `/vrs-investigate --function withdraw Vault.sol` | Target specific function |
| `/vrs-skip-investigation <bead-id>` | Skip bead investigation |

### 5. Workflow Control

| Command | Description |
|---------|-------------|
| `/vrs-pause` | Pause current workflow |
| `/vrs-resume` | Resume paused workflow |
| `/vrs-status` | Show current state |
| `/vrs-reset` | Clear and restart |

### 6. Tier B/C Control

| Command | Description |
|---------|-------------|
| `/vrs-verify-finding <id>` | Trigger Tier B verification |
| `/vrs-apply-labels contracts/` | Run labeling for Tier C |
| `/vrs-skip-verification <id>` | Skip verification |

---

## CLI Command Tree

```
alphaswarm
├── orchestrate
│   ├── start <path>
│   │   ├── --skip-stages       # NEW
│   │   ├── --only-stages       # NEW
│   │   └── --stop-after        # NEW
│   ├── pause <pool-id>         # NEW
│   ├── resume <pool-id>
│   ├── reset [pool-id]         # NEW
│   └── status <pool-id>
│
├── patterns                     # NEW APP
│   ├── list [--tier] [--category]
│   ├── run <pattern-id> <target>
│   └── run-category <cat> <target>
│
├── findings
│   ├── discard <id> --reason   # NEW
│   ├── prioritize <id>         # NEW
│   ├── verify <id>             # NEW
│   └── skip-verify <id>        # NEW
│
├── beads
│   ├── skip <id>               # NEW
│   └── investigate <id>        # NEW
│
└── label
    └── apply <target>          # NEW
```

---

## Data Model Extensions

### StageFilter

```python
@dataclass
class StageFilter:
    skip_stages: Set[int] = field(default_factory=set)
    only_stages: Optional[Set[int]] = None
    stop_after: Optional[int] = None

    def should_run(self, stage: int) -> bool:
        if self.only_stages is not None:
            return stage in self.only_stages
        return stage not in self.skip_stages
```

### PatternFilter

```python
@dataclass
class PatternFilter:
    pattern_ids: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    tiers: Optional[List[str]] = None
    severities: Optional[List[str]] = None
```

---

## Implementation Priority

| Priority | Feature | Effort |
|----------|---------|--------|
| **P0** | Stage skipping (`--skip-stages`) | 2 days |
| **P0** | Pattern filtering (`--tier`, `--category`) | 2 days |
| **P0** | Agent selection | 1 day |
| **P0** | Debate control (`--no-debate`) | 1 day |
| **P1** | Finding discard/prioritize | 2 days |
| **P1** | Pause/resume commands | 1 day |
| **P2** | Tool coordination | 2 days |
| **P2** | Budget control | 1 day |

---

## Critical Files to Modify

| File | Changes |
|------|---------|
| `src/alphaswarm_sol/orchestration/loop.py` | Add StageFilter |
| `src/alphaswarm_sol/cli/orchestrate.py` | Add stage control flags |
| `src/alphaswarm_sol/cli/patterns.py` | New CLI app (create) |
| `src/alphaswarm_sol/cli/findings.py` | Add discard/prioritize |
| `.claude/skills/vrs-audit.md` | Add stage options |
