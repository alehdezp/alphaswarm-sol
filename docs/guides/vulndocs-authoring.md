# VulnDocs Authoring Guide

**Validation pipeline, authoring skills, and advanced VulnDocs topics.**

**Prerequisites:** [VulnDocs Basics](vulndocs-basics.md)

---

## Mandatory Validation Pipeline

**Policy:** Any change to `vulndocs/` MUST pass validation before merge.

> **Workflow-first rule:** Invoke validation through Claude Code skills first. Use CLI commands as subordinate tool calls for CI/dev automation.

### Invoking Validation

```bash
/vrs-validate-vulndocs                    # Standard validation
/vrs-validate-vulndocs --mode quick       # Quick (schema only)
/vrs-validate-vulndocs --mode thorough    # Full validation contract
/vrs-validate-vulndocs --category reentrancy  # Specific category
```

### Pipeline Stages (Target Contract)

| Stage | Agent | Purpose | Model |
|-------|-------|---------|-------|
| 1 | vrs-test-conductor | Orchestrate | opus |
| 2 | vrs-prevalidator | URL provenance, schema | haiku |
| 3 | vrs-corpus-curator | Ground truth | sonnet |
| 4 | vrs-pattern-verifier | Evidence gates | sonnet |
| 5 | vrs-benchmark-runner | Precision/recall | haiku |
| 6 | vrs-mutation-tester | Variant generation | haiku |
| 7 | vrs-regression-hunter | Accuracy check | sonnet |
| 8 | vrs-gap-finder-lite | Coverage scan | sonnet.5 |

### Adaptive Pipeline Rules

**New Pattern Added:**
- All stages run
- `vrs-prevalidator` enforces provenance
- `vrs-mutation-tester` generates 10x variants

**Existing Pattern Modified:**
- All stages run
- `vrs-regression-hunter` compares to baseline

**Metadata-Only Change:**
- Only stages 1-2 run

### Quality Gates

| Gate | Target | Blocking |
|------|--------|----------|
| Precision | >= 85% | Yes |
| Recall (critical) | >= 95% | Yes |
| Recall (high) | >= 85% | Yes |
| Schema compliance | 100% | Yes |
| Provenance verified | 100% | Yes |

---

## Agent Skills

**Location:** `src/alphaswarm_sol/shipping/skills/`

Skills guide Claude Code and subagents to execute reproducible VulnDocs workflows. CLI commands are tool-level calls used under the same workflow contract.

```
User: "/vrs-add-vulnerability"
  ↓
Agent reads skill prompt
  ↓
Agent executes:
  1. Ask user for details
  2. Run: uv run alphaswarm vulndocs scaffold <id>
  3. Edit generated index.yaml
  4. Validate: uv run alphaswarm vulndocs validate
```

### Available Skills

| Skill | Purpose | Tool Calls Used |
|-------|---------|-----------------|
| `/vrs-discover` | Exa search for vulnerabilities | `exa-search`, `vulndocs scaffold` |
| `/vrs-add-vulnerability` | Add new vulnerability | `vulndocs scaffold`, `validate` |
| `/vrs-refine` | Improve patterns | `vulndocs validate`, editing |
| `/vrs-test-pattern` | Validate patterns | `build-kg`, `query` |
| `/vrs-research` | Guided research | Exa search |
| `/vrs-merge-findings` | Consolidate entries | `vulndocs list`, editing |
| `/vrs-generate-tests` | Create test cases | Test file creation |

### Workflow

```
[Discovery] (/vrs-discover)
    ↓
[Add Entry] (/vrs-add-vulnerability)
    ↓
[Research] (/vrs-research) ←→ [Refine] (/vrs-refine)
    ↓
[Test Pattern] (/vrs-test-pattern)
    ↓
[Generate Tests] (/vrs-generate-tests)
    ↓
[Validation Complete]
```

---

## Phase 7 Fields

Phase 7 is the **Final Testing (GA Gate)** milestone. The `phase_7` section tracks:

```yaml
phase_7:
  test_coverage:
    - vulnerable_example: tests/vulnerable.sol
    - safe_example: tests/safe.sol
    - edge_cases: tests/edge_cases.sol
  validation_metrics:
    precision: 0.95
    recall: 0.89
    false_positive_rate: 0.05
```

These are optional during `draft` but required for `validated` or `excellent` status.

---

## VulnDoc Field Requirement

Every pattern MUST have a `vulndoc` field pointing to documentation:

```yaml
# patterns/reentrancy/reentrancy-classic.yaml
id: reentrancy-classic
name: Classic Reentrancy
vulndoc: vulndocs/reentrancy-classic/
lens: [Reentrancy]
```

Validator tooling checks this bidirectional link:

```bash
uv run alphaswarm vulndocs validate vulndocs/
```

---

## Tool-Level Validation Commands (CI/Dev)

```bash
# Full validation
uv run alphaswarm vulndocs validate vulndocs/

# Schema-only
uv run alphaswarm vulndocs validate vulndocs/ --schema-only

# With metrics
uv run alphaswarm vulndocs validate vulndocs/ --metrics --baseline .vrs/baselines/latest.json

# JSON output for CI
uv run alphaswarm vulndocs validate vulndocs/ --json
```

---

## Test Generation

Every vulnerability should have tests demonstrating:

1. **Vulnerable Example**: Code that triggers detection
2. **Safe Example**: Similar code that should NOT trigger (CEI, guards)
3. **Edge Cases**: Boundary conditions, subtle variants

Use `/vrs-generate-tests` to create initial test suite.

---

## Documentation Quality

### Good `false_positive_filters`:

```yaml
false_positive_filters:
  - Check if external call is to whitelisted contract
  - Verify if balance update precedes external call (CEI)
  - Confirm if reentrancy guard is present (nonReentrant)
```

Each filter should be actionable by detection logic or human reviewer.

### Real-World Examples

When adding `real_world_examples`, include:
- Project name and GitHub link
- Exploit date (if applicable)
- Brief description
- Link to post-mortem

---

## Next Steps

1. **Add First Entry**: Use `/vrs-add-vulnerability` or CLI scaffold
2. **Validate Existing Patterns**: Check which need vulndoc links
3. **Create Test Suite**: Use `/vrs-generate-tests`
4. **Monitor CI**: Watch `.github/workflows/vulndocs-validate.yml`

---

## Related Documentation

- [VulnDocs Basics](vulndocs-basics.md) - Getting started
- [Pattern Basics](patterns-basics.md) - Creating patterns
- [Testing Basics](testing-basics.md) - Pattern testing

---

*Updated February 2026*
