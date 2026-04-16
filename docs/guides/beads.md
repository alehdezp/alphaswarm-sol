# Beads Guide

Beads are self-contained investigation packages for tracking security work. This guide explains how VRS uses beads to manage vulnerability investigations.

## What Are Beads?

A bead represents a single unit of security investigation work:
- Potential vulnerability to investigate
- Finding to verify
- Test to write
- Attack path to construct
- Mitigation to validate

Beads follow the [steveyegge/beads](https://github.com/steveyegge/beads) pattern for AI-optimized task tracking. They enable agents to:
- Resume work across sessions
- Track dependencies between investigations
- Prioritize work by severity
- Store investigation state for handoff

## Bead Storage

Beads are stored in `.beads/index.jsonl`:
- **JSONL format:** One JSON object per line
- **Git-friendly:** Append-only, line-based diffs
- **Survives restarts:** Persists across agent sessions
- **Human-readable:** JSON structure is easy to inspect

Example bead:
```json
{
  "id": "bd-a1b2c3d4",
  "title": "Reentrancy in withdraw function",
  "status": "in_progress",
  "severity": "high",
  "priority": 0,
  "pattern_id": "reentrancy-classic",
  "location": "Vault.sol:withdraw",
  "blockers": [],
  "work_state": {
    "attacker_claim": "...",
    "defender_claim": "..."
  },
  "created_at": "2026-01-22T12:00:00Z",
  "updated_at": "2026-01-22T12:15:00Z"
}
```

## Bead Lifecycle

```
open -> in_progress -> complete
          |
          v
       blocked -> open (when blocker completes)
```

### Status Definitions

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `open` | Ready for work | Start investigation |
| `in_progress` | Currently being investigated | Continue work |
| `blocked` | Waiting on dependency | Work on blocker |
| `complete` | Investigation finished | Review results |

## Using Beads

Primary usage is via Claude Code skills (`/vrs-bead-create`, `/vrs-bead-update`, `/vrs-bead-list`). Direct CLI commands are optional tool-level operations for automation and debugging.

### Create a Bead (Preferred: Skill)

```text
/vrs-bead-create "Check reentrancy in withdraw" --severity high
```

### Create a Bead (Developer CLI)

```bash
# Create via CLI
uv run alphaswarm bead create "Check reentrancy in withdraw" --severity high

# Create with pattern and location
uv run alphaswarm bead create "Missing access control" \
  --severity critical \
  --pattern "weak-access-control" \
  --location "Vault.sol:setOwner"
```

Returns bead ID: `bd-a1b2c3d4`

### List Beads (Developer CLI)

```bash
# List all beads
uv run alphaswarm bead list

# Filter by status
uv run alphaswarm bead list --status open
uv run alphaswarm bead list --status in_progress

# Show only ready beads (open and not blocked)
uv run alphaswarm bead list --ready

# Filter by severity
uv run alphaswarm bead list --severity high
uv run alphaswarm bead list --severity critical

# Combine filters
uv run alphaswarm bead list --status open --severity high
```

### Show Bead Details (Developer CLI)

```bash
# Show full bead details
uv run alphaswarm bead show bd-a1b2c3d4

# JSON output
uv run alphaswarm bead show bd-a1b2c3d4 --json
```

### Update Bead Status (Developer CLI)

```bash
# Start investigation
uv run alphaswarm bead update bd-a1b2c3d4 --status in_progress

# Mark complete
uv run alphaswarm bead update bd-a1b2c3d4 --status complete

# Block on another bead
uv run alphaswarm bead update bd-a1b2c3d4 --status blocked --blocker bd-xyz789

# Unblock and reopen
uv run alphaswarm bead update bd-a1b2c3d4 --status open
```

### Update Bead Fields (Developer CLI)

```bash
# Change severity
uv run alphaswarm bead update bd-a1b2c3d4 --severity critical

# Add notes
uv run alphaswarm bead update bd-a1b2c3d4 --notes "Found exploit path via flash loan"

# Update location
uv run alphaswarm bead update bd-a1b2c3d4 --location "Vault.sol:withdrawAll"
```

## Bead Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (bd-{hash}) |
| `title` | string | Brief description |
| `status` | enum | open/in_progress/complete/blocked |
| `severity` | enum | critical/high/medium/low |
| `priority` | int | 0 = highest, higher numbers = lower priority |
| `pattern_id` | string | Pattern that triggered this bead |
| `location` | string | File:function location |
| `blockers` | string[] | IDs of blocking beads |
| `work_state` | object | State for agent resumption |
| `created_at` | timestamp | Creation time |
| `updated_at` | timestamp | Last update time |

### Work State

The `work_state` field stores investigation progress for agent resumption:

```json
{
  "work_state": {
    "phase": "verification",
    "attacker_claim": "Reentrancy is exploitable via withdraw->callback->withdraw",
    "defender_claim": "No guards found, CEI pattern violated",
    "verifier_claim": null,
    "debate_round": 1,
    "evidence": {
      "vulnerable_pattern": "R:bal→X:out→W:bal",
      "code_location": "Vault.sol:42-48"
    }
  }
}
```

## Beads in Skills

Skills create and update beads automatically during workflows.

### During Audit (`/vrs-audit`)

```
/vrs-audit contracts/

1. Pattern detection runs
2. Beads created for each finding
   - bd-001: Reentrancy in withdraw
   - bd-002: Missing access control in setOwner
   - bd-003: Oracle manipulation risk
3. Beads queued for investigation
```

### During Investigation (`/vrs-investigate`)

```
/vrs-investigate bd-001

1. Bead status -> in_progress
2. Investigation work performed
3. work_state updated with findings
4. Bead status -> complete
```

### During Verification (`/vrs-verify`)

```
/vrs-verify bd-001

1. Spawns attacker agent
2. Attacker updates work_state.attacker_claim
3. Spawns defender agent
4. Defender updates work_state.defender_claim
5. Spawns verifier agent
6. Verifier updates work_state.verifier_claim
7. Bead status -> complete
```

### During Debate (`/vrs-debate`)

```
/vrs-debate bd-001

1. Loads attacker and defender claims
2. Runs claim/counterclaim rounds
3. Updates work_state.debate_round
4. Produces verdict
5. Bead status -> complete
```

## Bead Priorities

Beads are prioritized by:

1. **Severity** (critical > high > medium > low)
2. **Status** (blocked beads deprioritized)
3. **Priority field** (lower number = higher priority)
4. **Dependencies** (blockers resolved first)

Priority calculation:
```python
priority = 0  # Highest priority

# Add penalty for lower severity
if severity == "high": priority += 10
if severity == "medium": priority += 20
if severity == "low": priority += 30

# Add penalty for blocked status
if status == "blocked": priority += 100

# Manual priority adjustment
priority += manual_priority
```

## JSON Output

All bead commands support `--json` for programmatic use:

```bash
# List beads as JSON array
uv run alphaswarm bead list --json

# Show single bead as JSON object
uv run alphaswarm bead show bd-a1b2c3d4 --json
```

Example JSON output:
```json
{
  "beads": [
    {
      "id": "bd-a1b2c3d4",
      "title": "Reentrancy in withdraw",
      "status": "complete",
      "severity": "high",
      "priority": 0,
      "pattern_id": "reentrancy-classic",
      "location": "Vault.sol:withdraw",
      "blockers": [],
      "created_at": "2026-01-22T12:00:00Z",
      "updated_at": "2026-01-22T12:30:00Z"
    }
  ],
  "count": 1
}
```

## Git Integration

The `.beads/` directory can be:

- **Tracked:** Share investigation state with team
  ```bash
  git add .beads/
  git commit -m "Add beads for audit findings"
  ```

- **Ignored:** Keep local only
  ```bash
  echo ".beads/" >> .gitignore
  ```

### Recommendations

| Scenario | Recommendation |
|----------|----------------|
| Team audit | Track `.beads/` for collaboration |
| Solo exploration | Ignore `.beads/` for cleaner git history |
| CI/CD integration | Ignore `.beads/` to avoid build artifacts |
| Audit trails | Track `.beads/` for compliance documentation |

## Bead Scope

Beads are created ONLY for security-related Solidity investigation work:

**Valid bead work:**
- Vulnerability investigations
- Exploit path construction
- Mitigation verification
- Pattern validation
- Attack surface analysis
- Access control audits

**Invalid bead work:**
- Documentation tasks
- Code formatting
- Non-security refactoring
- Build configuration
- Deployment scripts

## Advanced Usage

### Dependency Tracking

```bash
# Create dependent beads
uv run alphaswarm bead create "Verify fix for reentrancy" \
  --severity medium \
  --blocker bd-a1b2c3d4

# This bead won't start until bd-a1b2c3d4 is complete
```

### Batch Operations

```bash
# List all critical open beads
uv run alphaswarm bead list --severity critical --status open --json | \
  jq -r '.beads[].id'

# Mark multiple beads complete
for bead in bd-001 bd-002 bd-003; do
  uv run alphaswarm bead update $bead --status complete
done
```

### Work State Queries

```bash
# Show beads in verification phase
uv run alphaswarm bead list --json | \
  jq '.beads[] | select(.work_state.phase == "verification")'

# Show beads with attacker claims
uv run alphaswarm bead list --json | \
  jq '.beads[] | select(.work_state.attacker_claim != null)'
```

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-bead-create` | Create new bead |
| `/vrs-bead-update` | Update bead status/fields |
| `/vrs-bead-list` | List and filter beads |
| `/vrs-investigate` | Investigate bead findings |
| `/vrs-verify` | Verify bead with multi-agent |

## Related Documentation

- [Skills Guide](skills.md) - VRS skills documentation
- [Installation Guide](../getting-started/installation.md) - Setup instructions
- [steveyegge/beads](https://github.com/steveyegge/beads) - Original beads pattern

## Support

If beads are not working correctly:

1. Check `.beads/` directory exists and is writable
2. Verify `.beads/index.jsonl` is valid JSON-Lines format
3. Run `/vrs-health-check` to diagnose issues
4. Check bead IDs are in correct format (bd-{hash})

## License

Part of the VRS (Vulnerability Research System) for Solidity security analysis.
