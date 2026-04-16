# Use Case Scenario Framework (Phase 3.1d)

Use case scenarios define **expected end-to-end behaviors** for AlphaSwarm.sol
workflows. Each scenario is a YAML file that specifies: what to run, what should
happen, what must not happen, and how to evaluate the result.

## What Scenarios Are

A scenario is a declarative test specification. It describes:

1. **Input** -- A contract, a command, and context about what the contract contains.
2. **Expected behavior** -- Specific observable steps that must happen (graph queries,
   tool calls, findings), and anti-patterns that must not happen (false positives,
   crashes, skipped steps).
3. **Evaluation criteria** -- Dimensions to score, pass threshold, and regression
   signals.
4. **Links** -- Connections to workflow docs, evaluation contracts, and related
   scenarios.

Scenarios are organized by category in subdirectories:

```
use-cases/
  _schema.yaml          # Schema definition
  README.md             # This file
  audit/                # Full audit workflow scenarios
  agents/               # Individual agent scenarios (attacker, defender, etc.)
  verify/               # Verification workflow scenarios
  failure/              # Graceful failure scenarios
```

## How to Add a New Scenario

1. **Pick the right subdirectory** based on the workflow being tested.

2. **Create a YAML file** following the naming convention:
   `UC-<CATEGORY>-<NNN>-<short-description>.yaml`

   Example: `UC-AUDIT-006-flash-loan-exploit.yaml`

3. **Fill in all required fields** per the schema (`_schema.yaml`). At minimum:
   - `id`, `name`, `workflow`, `category`, `tier`
   - `input` with `contract`, `command`, `context`
   - `expected_behavior` with `summary`, `must_happen`, `must_not_happen`
   - `evaluation` with `pass_threshold`, `key_dimensions`, `regression_signals`
   - `status` (start with `draft`)

4. **Validate** by running:
   ```bash
   python scripts/validate_scenarios.py
   ```

5. **Done.** The scenario is automatically discovered by pytest via
   `tests/scenarios/conftest.py`.

## Schema Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID matching `UC-[A-Z]+-\d{3}` |
| `name` | string | Human-readable name |
| `workflow` | enum | One of: vrs-audit, vrs-investigate, vrs-verify, vrs-debate, vrs-attacker, vrs-defender, vrs-health-check, graph-build, tool-run, failure |
| `category` | enum | One of: audit, investigate, verify, debate, agents, tools, graph, failure, cross-workflow |
| `tier` | enum | core, important, or mechanical |
| `input` | object | Contains `contract`, `command`, `context` |
| `expected_behavior` | object | Contains `summary`, `must_happen`, `must_not_happen` |
| `evaluation` | object | Contains `pass_threshold`, `key_dimensions`, `regression_signals` |
| `status` | enum | draft, ready, validated, or broken |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `expected_behavior.expected_tools` | object | `ordered` and `required` tool lists |
| `expected_behavior.expected_findings` | object | `min_count`, `must_include_category`, `severity` |
| `links` | object | `workflow_doc`, `evaluation_contract`, `test_contract`, `related_scenarios` |
| `last_validated` | string/null | ISO 8601 date or null |
| `notes` | string | Free-form notes |

### Tier Definitions

- **core** -- Must pass for any release. Tests critical reasoning and detection paths.
- **important** -- Should pass. Tests common workflows and expected behaviors.
- **mechanical** -- Nice-to-have. Tests edge cases, error handling, rare paths.

## Integration with pytest

Scenarios are auto-discovered by `tests/scenarios/conftest.py` and exposed as
parametrized test cases. Run them with:

```bash
# Run all scenarios
pytest tests/scenarios/ -v

# Run a specific scenario
pytest tests/scenarios/ -k "UC-AUDIT-001"

# Run only core-tier scenarios
pytest tests/scenarios/ -k "core"

# Run only audit scenarios
pytest tests/scenarios/ -k "audit"
```

Each scenario runs in **simulated mode** by default (no real Claude Code session).
The evaluation pipeline validates YAML structure, checks field constraints, and
produces a structured feedback report.

To run scenarios against real Claude Code sessions (headless mode), use:
```bash
pytest tests/scenarios/ --run-mode=headless
```

## Scenario Lifecycle

```
draft  -->  ready  -->  validated
  ^           |             |
  |           v             v
  +------- broken <--------+
```

- **draft**: Scenario written but not yet verified against a real run.
- **ready**: Scenario passes validation and is structurally correct.
- **validated**: Scenario has been run successfully with pass threshold met.
- **broken**: Scenario fails due to infrastructure or contract changes.
