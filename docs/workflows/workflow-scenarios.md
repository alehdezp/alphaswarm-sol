# Workflow: Use Case Scenarios

**Purpose:** Define how use case scenarios work and how to add new ones.

> **v6.0 Status:** 32+ scenarios authored. Framework validates YAML schema and runs scenarios through evaluation pipeline. Pytest plugin enables `-k` filtering and parallel execution.

## What Are Scenarios?

Use case scenarios are **human-reviewable YAML files** that define expected behavior for every workflow. They are the contract between human and AI about what "correct behavior" means.

Each scenario specifies:
- **Input:** What contract/command to run
- **Expected behavior:** What must happen and must not happen
- **Evaluation:** How to score the result
- **Regression signals:** When to flag a regression

## Where They Live

```
.planning/testing/scenarios/use-cases/
├── README.md                          # Schema docs, how to add scenarios
├── _schema.yaml                       # YAML validation schema
├── audit/                             # /vrs-audit workflow scenarios
├── investigate/                       # /vrs-investigate scenarios
├── verify/                            # /vrs-verify scenarios
├── debate/                            # /vrs-debate scenarios
├── agents/                            # Agent-specific scenarios
├── tools/                             # Tool workflow scenarios
├── graph/                             # Graph building scenarios
├── failure/                           # Failure and edge cases
└── cross-workflow/                    # Multi-workflow integration
```

## Scenario YAML Structure

```yaml
id: UC-AUDIT-001
name: "Audit detects classic reentrancy"
workflow: vrs-audit
category: audit
tier: core

input:
  contract: "tests/contracts/ReentrancyClassic.sol"
  command: "/vrs-audit tests/contracts/ReentrancyClassic.sol"
  context: "Single contract with textbook reentrancy"

expected_behavior:
  summary: "The audit should detect the reentrancy vulnerability."
  must_happen:
    - "Graph is built successfully with build-kg"
    - "Attacker queries for reentrancy patterns via BSKG"
  must_not_happen:
    - "Agent skips graph building and reads code directly"
  expected_tools:
    ordered: ["Bash(build-kg)", "Bash(query)"]
    required: ["Bash", "Read"]
  expected_findings:
    min_count: 1
    must_include_category: "reentrancy"
    severity: "high"

evaluation:
  pass_threshold: 60
  key_dimensions:
    - name: graph_utilization
      description: "Did agents use BSKG queries?"
  regression_signals:
    - "Score drops below 60 → REGRESSION"

links:
  workflow_doc: "docs/workflows/workflow-audit.md"
  test_contract: "tests/contracts/ReentrancyClassic.sol"
  related_scenarios: ["UC-AUDIT-002"]

status: draft
last_validated: null
notes: ""
```

## How To Add a Scenario

1. **Write the YAML** — Copy an existing scenario, modify for your case
2. **Validate** — Run `python scripts/validate_scenarios.py`
3. **Run it** — `uv run pytest tests/scenarios/ -k "YOUR-SCENARIO-ID"`
4. **Review feedback** — Check what passed, what failed, why
5. **Iterate** — Update expected_behavior if needed

No code changes required. The framework auto-discovers new YAML files.

## Running Scenarios

```bash
# Run one scenario
uv run pytest tests/scenarios/ -k "UC-AUDIT-001"

# Run all audit scenarios
uv run pytest tests/scenarios/ -k "audit"

# Run all failure scenarios
uv run pytest tests/scenarios/ -k "fail"

# Run full regression suite
uv run pytest tests/scenarios/

# Run with verbose output
uv run pytest tests/scenarios/ -k "UC-AUDIT-001" -v
```

## Scenario Tiers

| Tier | Count | Depth | When |
|------|-------|-------|------|
| **core** | ~10 | Full evaluation (GVS + reasoning + debrief) | Every run |
| **important** | ~12 | Standard evaluation (GVS + reasoning) | Weekly/PR |
| **mechanical** | ~10 | Basic capability checks only | On demand |

## Adding Scenarios for New Capabilities

Before implementing a new capability, write the scenario YAML first:

1. Define what the capability should do (`must_happen`)
2. Define what it should not do (`must_not_happen`)
3. Review with human — align on expected behavior
4. Implement the capability
5. Run the scenario — verify it passes
6. Commit scenario + implementation together

## Integration with Testing Skills

| Skill | How Scenarios Are Used |
|-------|----------------------|
| `/vrs-test-scenario` | Loads single YAML, runs evaluation, produces feedback |
| `/vrs-test-regression` | Runs ALL scenarios, compares to baseline |
| `/vrs-test-affected` | Maps changed files → affected scenario IDs |
| `/vrs-test-suggest` | Analyzes scenario failures, suggests improvements |

## Scenario Status Lifecycle

```
draft → ready → validated → (broken → draft)
```

- **draft**: Written but not yet human-reviewed
- **ready**: Human reviewed `must_happen` lists, approved expected behavior
- **validated**: Passes in evaluation pipeline with score >= threshold
- **broken**: Previously validated but now failing (needs investigation)
