---
name: vrs-health-check
description: |
  Validate VRS installation and configuration. Checks CLI installation, external tools, vulndocs, and skills availability.

  Invoke when user wants to:
  - Check installation: "is VRS installed correctly?", "/vrs-health-check"
  - Troubleshoot issues: "why isn't audit working?", "check my setup"
  - Validate configuration: "verify my environment", "test VRS"

slash_command: vrs:health-check
disable-model-invocation: true

allowed-tools:
  - Bash(alphaswarm*)
  - Read
  - Glob
---

# VRS Health Check Skill - Installation Validation

You are the **VRS Health Check** skill, responsible for validating VRS installation and configuration.

## How to Invoke

```bash
/vrs-health-check
/vrs-health-check --verbose    # Detailed output
/vrs-health-check --json       # Machine-readable output
```

---

## What This Skill Checks

### 1. CLI Installation
- alphaswarm CLI is installed and accessible
- Version is compatible (>= 1.0.0)
- Python environment is correct

### 2. External Tools
- Slither (CORE tier - required)
- Aderyn (CORE tier - required)
- Mythril (RECOMMENDED tier - optional)
- Echidna (RECOMMENDED tier - optional)
- Foundry (RECOMMENDED tier - optional)
- Semgrep (OPTIONAL tier - optional)
- Halmos (OPTIONAL tier - optional)

### 3. VulnDocs
- VulnDocs directory exists
- Core patterns are present
- Validation passes

### 4. Skills
- All 5 shipped skills are present
- Skills have correct frontmatter
- Skills are loadable

### 5. Configuration
- .vrs/ directory exists
- Permissions are correct
- Storage structure is valid

---

## Running the Health Check

```bash
# Run basic health check
alphaswarm health-check

# Run with JSON output for parsing
alphaswarm health-check --json
```

---

## Output Format

### Console Output
```
VRS Health Check
================

✓ CLI Installation
  Version: 1.0.0
  Python: 3.11.5
  Location: /usr/local/bin/alphaswarm

✓ Core Tools (2/2)
  ✓ Slither 0.10.0
  ✓ Aderyn 0.2.0

⚠ Recommended Tools (2/3)
  ✓ Mythril 0.24.0
  ✓ Foundry (forge 0.2.0)
  ✗ Echidna (not installed)

⚠ Optional Tools (1/2)
  ✓ Semgrep 1.45.0
  ✗ Halmos (not installed)

✓ VulnDocs
  Location: vulndocs/
  Patterns: 44 core, 21 label-dependent
  Status: Validated

✓ Skills
  5 skills loaded:
  - audit.md
  - investigate.md
  - verify.md
  - debate.md
  - health-check.md

✓ Configuration
  .vrs/ directory: present
  Permissions: correct
  Storage: valid

Overall Status: READY (2 optional tools missing)

Recommendations:
- Install Echidna for property-based testing
- Install Halmos for symbolic execution
```

### JSON Output
```json
{
  "status": "ready",
  "timestamp": "2026-01-22T12:55:11Z",
  "cli": {
    "installed": true,
    "version": "1.0.0",
    "compatible": true,
    "location": "/usr/local/bin/alphaswarm"
  },
  "tools": {
    "core": {
      "total": 2,
      "installed": 2,
      "tools": {
        "slither": {"installed": true, "version": "0.10.0"},
        "aderyn": {"installed": true, "version": "0.2.0"}
      }
    },
    "recommended": {
      "total": 3,
      "installed": 2,
      "tools": {
        "mythril": {"installed": true, "version": "0.24.0"},
        "echidna": {"installed": false},
        "foundry": {"installed": true, "version": "0.2.0"}
      }
    },
    "optional": {
      "total": 2,
      "installed": 1,
      "tools": {
        "semgrep": {"installed": true, "version": "1.45.0"},
        "halmos": {"installed": false}
      }
    }
  },
  "vulndocs": {
    "present": true,
    "location": "vulndocs/",
    "core_patterns": 44,
    "label_patterns": 21,
    "validated": true
  },
  "skills": {
    "present": true,
    "count": 5,
    "skills": [
      "audit.md",
      "investigate.md",
      "verify.md",
      "debate.md",
      "health-check.md"
    ]
  },
  "configuration": {
    "vrs_dir": true,
    "permissions": "correct",
    "storage": "valid"
  },
  "recommendations": [
    "Install Echidna for property-based testing",
    "Install Halmos for symbolic execution"
  ]
}
```

---

## Status Levels

| Status | Meaning | Action |
|--------|---------|--------|
| READY | All core components working | None |
| DEGRADED | Core working, some optional missing | Consider installing missing tools |
| BROKEN | Core components missing | Install required tools |
| ERROR | CLI not installed | Install alphaswarm CLI |

---

## Common Issues

### Issue: CLI Not Found
```
Error: alphaswarm command not found

Solution:
1. Install via: pip install alphaswarm
2. Or: uvx alphaswarm
3. Verify: which alphaswarm
```

### Issue: Slither Not Found
```
Error: Slither not installed (CORE tool required)

Solution:
1. Install via: pip install slither-analyzer
2. Or: Follow https://github.com/crytic/slither#installation
3. Verify: slither --version
```

### Issue: VulnDocs Missing
```
Error: vulndocs/ directory not found

Solution:
1. Run: alphaswarm init
2. Or: Clone from repository
3. Verify: ls vulndocs/
```

### Issue: Permissions Error
```
Error: Cannot write to .vrs/ directory

Solution:
1. Check permissions: ls -la .vrs/
2. Fix: chmod 755 .vrs/
3. Create if missing: mkdir -p .vrs/
```

---

## Automated Fixes

Some issues can be auto-fixed:

```bash
# Auto-fix missing directories
/vrs-health-check --fix

# Creates:
# - .vrs/ if missing
# - .beads/ if missing
# - .claude/vrs/ if missing
```

---

## Integration with Other Skills

Health check is automatically run before:
- `/vrs-audit` - Ensures all tools available
- First skill invocation - Validates setup

Manual health check recommended:
- After VRS installation
- After system updates
- When troubleshooting errors

---

## Related Commands

```bash
# Check tool status only
alphaswarm tools status

# Install missing tools
alphaswarm tools install

# Validate vulndocs
alphaswarm vulndocs validate

# List skills
alphaswarm skills list
```

---

## Notes

- This is a USER-CONTROLLED skill (disable-model-invocation: true)
- Runs in main context (no fork needed)
- Quick inline execution
- No write operations except with --fix flag
- Safe to run repeatedly
