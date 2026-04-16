---
name: vrs-track-gap
description: |
  Gap tracking skill. Records testing gaps with proper categorization
  and links to backlog items.

  Invoke when user wants to:
  - Record gap: "track this gap", "/vrs-track-gap"
  - Log limitation: "document this limitation"
  - Note detection failure: "we missed this, track it"

  This skill creates gap entries:
  1. Capture gap details
  2. Categorize by type and severity
  3. Create YAML file in gap inventory
  4. Link to BACKLOG.md if actionable

slash_command: vrs:track-gap
context: inline
disable-model-invocation: false

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# VRS Track Gap - Gap Tracking

You are the **VRS Track Gap** skill, responsible for recording testing gaps with proper categorization. This skill maintains a brutally honest inventory of all known gaps, failure modes, and root causes.

## Philosophy

From Test Forge Context:
- **Brutally honest documentation** - No hiding limitations
- **Categorized by type** - Enables prioritization and research planning
- **Linked to actionables** - Gaps become backlog items or research themes
- **Gap tracking is not failure** - It's progress toward improvement

**Gap Tracking Goals:**
1. Document what we miss
2. Understand why we miss it
3. Prioritize improvements
4. Track progress over time

## How to Invoke

```bash
/vrs-track-gap "<title>" --category <category> --severity <severity>
/vrs-track-gap "Cross-contract reentrancy" --category detection --severity high
/vrs-track-gap "Proxy storage collision" --category technical --severity medium
```

---

## Gap Categories

| Category | Description | Example |
|----------|-------------|---------|
| `detection` | Vulnerabilities we miss | Cross-contract reentrancy |
| `false_positive` | Incorrect findings | Safe modifier flagged as weak |
| `technical` | Builder/pattern/VQL limitations | No support for assembly blocks |
| `agent` | Reasoning failures, context issues | Agent hallucinates non-existent guard |
| `scalability` | Performance bottlenecks | Timeout on 1000+ function contracts |
| `ux` | CLI/workflow problems | Confusing error messages |

## Severity Levels

| Severity | Impact | Example |
|----------|--------|---------|
| `critical` | Missing critical vulnerabilities | Reentrancy not detected |
| `high` | Missing high-severity or common issues | Flash loan detection gap |
| `medium` | Missing medium-severity or edge cases | Uncommon proxy pattern |
| `low` | Minor gaps, rarely encountered | Obscure EVM feature |

---

## Gap Schema

```yaml
gap_id: GAP-001
category: detection  # detection, false_positive, technical, agent, scalability, ux
severity: high  # critical, high, medium, low
title: "Cross-contract reentrancy via callback"
description: |
  Detection fails when reentrancy occurs through
  external callback to different contract.
root_cause: "CallTracker doesn't follow callback paths across contracts"
affected_component: builder.calls
test_case: tests/adversarial/test_cross_contract_reentrancy.py
status: open  # open, investigating, fixed, wontfix
roadmap_item: BACKLOG-023  # If actionable
research_theme: cross-contract-analysis  # If systemic
discovered_date: 2026-01-22
discovered_by: vrs-gap-finder  # or username
```

---

## Usage Examples

### Basic Gap Recording
```bash
/vrs-track-gap "Cross-contract reentrancy" --category detection --severity high

# Output:
# Gap Recorded
# ============
# Gap ID: GAP-012
# Title: Cross-contract reentrancy
# Category: detection
# Severity: high
# Status: open
#
# File: .vrs/testing/gaps/GAP-012.yaml
```

### With Description
```bash
/vrs-track-gap "Cross-contract reentrancy" --category detection --severity high \
  --description "Detection fails when reentrancy occurs through external callback to different contract" \
  --root-cause "CallTracker doesn't follow callback paths across contracts"
```

### With Test Case
```bash
/vrs-track-gap "Proxy storage collision" --category technical --severity medium \
  --test-case "tests/adversarial/test_proxy_storage.py"
```

### Link to Backlog
```bash
/vrs-track-gap "Flash loan attack pattern" --category detection --severity high \
  --backlog BACKLOG-045
```

---

## Output Format

### Gap YAML File
```yaml
# .vrs/testing/gaps/GAP-012.yaml
gap_id: GAP-012
category: detection
severity: high
title: "Cross-contract reentrancy via callback"
description: |
  Detection fails when reentrancy occurs through
  external callback to different contract.

  Example scenario:
  1. Contract A calls Contract B
  2. Contract B calls back to Contract A
  3. Reentrancy in A is not detected

root_cause: "CallTracker doesn't follow callback paths across contracts"
affected_component: builder.calls
test_case: tests/adversarial/test_cross_contract_reentrancy.py
status: open
roadmap_item: null
research_theme: cross-contract-analysis
discovered_date: 2026-01-22
discovered_by: vrs-gap-finder
```

### Gap Recording Confirmation
```markdown
# Gap Recorded

**Gap ID:** GAP-012
**Category:** detection
**Severity:** high

## Details

**Title:** Cross-contract reentrancy via callback

**Description:**
Detection fails when reentrancy occurs through external callback to different contract.

**Root Cause:**
CallTracker doesn't follow callback paths across contracts

**Affected Component:** builder.calls

## Status

- Status: OPEN
- Test Case: tests/adversarial/test_cross_contract_reentrancy.py
- Roadmap Item: None (add with --backlog flag)
- Research Theme: cross-contract-analysis

## File

Gap saved to: `.vrs/testing/gaps/GAP-012.yaml`
```

---

## Gap Inventory

### Location
```
.vrs/
└── testing/
    └── gaps/
        ├── GAP-001.yaml
        ├── GAP-002.yaml
        ├── GAP-003.yaml
        └── ...
```

### Querying Gaps
```bash
# List all open gaps
ls .vrs/testing/gaps/

# Find high-severity detection gaps
grep -l "severity: high" .vrs/testing/gaps/*.yaml | xargs grep -l "category: detection"

# Count gaps by category
grep "^category:" .vrs/testing/gaps/*.yaml | sort | uniq -c
```

---

## Status Transitions

| From | To | When |
|------|----|------|
| open | investigating | Work begins on fix |
| investigating | fixed | Fix implemented and tested |
| investigating | wontfix | Gap accepted as limitation |
| open | wontfix | Gap accepted (won't address) |

### Updating Status
```bash
# Manual update in YAML file:
status: fixed
fixed_date: 2026-02-15
fixed_by: plan-07.2-05
```

---

## Integration

### BACKLOG.md Link
When a gap is actionable, link to BACKLOG.md:

```yaml
roadmap_item: BACKLOG-023
```

Then in `.planning/BACKLOG.md`:
```markdown
### BACKLOG-023: Fix cross-contract reentrancy detection
- **Gap:** GAP-012
- **Priority:** P1
- **Effort:** Medium
- **Description:** Extend CallTracker to follow callback paths across contracts
```

### Research Themes
When a gap represents a systemic issue:

```yaml
research_theme: cross-contract-analysis
```

Research themes inform future milestone planning.

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-full` | Gap analysis in Phase 8 |
| `/vrs-test-quick` | Quick gap identification |
| `/vrs-benchmark-model` | Model-specific gaps |

---

## Write Boundaries

This skill is restricted to writing in:
- `.vrs/testing/gaps/` - Gap inventory YAML files

All other directories are read-only.

---

## Notes

- Gap IDs are auto-incremented (GAP-001, GAP-002, etc.)
- Gaps are git-tracked for history
- Brutally honest documentation is expected
- Gaps are NOT failures - they're progress
- Link to BACKLOG.md for actionable items
- Use research_theme for systemic issues
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
