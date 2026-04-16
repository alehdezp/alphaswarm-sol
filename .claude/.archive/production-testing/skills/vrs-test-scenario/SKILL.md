---
name: vrs-test-scenario
description: Create and manage real-world test scenarios for the testing framework
---

# /vrs-test-scenario — Test Scenario Management

## Purpose

Create, list, and manage test scenarios in the testing framework registry. Each scenario defines a realistic project setup, a user prompt, and expectations for agent behavior.

## Usage

```
/vrs-test-scenario create                    # Interactive scenario creation
/vrs-test-scenario create --category <cat>   # Create in specific category
/vrs-test-scenario list                      # List all scenarios
/vrs-test-scenario list --tag <tag>          # Filter by tag
/vrs-test-scenario show <scenario-id>        # Show scenario details
/vrs-test-scenario delete <scenario-id>      # Remove a scenario
```

## Create Process

### Step 1: Gather Scenario Information

Ask the user or determine from context:

1. **Category**: What type of test?
   - `pattern-detection` — Test that a specific pattern triggers correctly
   - `orchestration` — Test workflow mechanics (spawning, task pickup, state)
   - `agent-reasoning` — Test agent quality (graph-first, evidence, reasoning)
   - `tool-usage` — Test static analysis tool integration
   - `e2e-pipeline` — Test full audit flow
   - `skill-execution` — Test specific skill invocation
   - `graph-value` — Test that graph improves agent reasoning

2. **Name**: Human-readable description

3. **Contracts**: Which Solidity files to include
   - Can reference existing test contracts (`tests/contracts/*.sol`)
   - Can reference DVDeFi challenges (`examples/damm-vuln-defi/`)
   - Can create new custom contracts for specific patterns

4. **Prompt**: What would a real user ask? This is sent to the worker agent.
   - Must be natural — no hints about expected behavior
   - Examples: "Audit these contracts", "Check for reentrancy issues", "Run a security analysis"

5. **Expectations**: What should the observer check? (natural language)
   - "Agent should build a knowledge graph"
   - "Agent should detect the reentrancy vulnerability in withdraw()"
   - "Agent should use graph queries, not just read source code"

6. **Failure Conditions**: What would make this test fail?
   - "Agent doesn't use the graph at all"
   - "Agent reports false positives on safe code"
   - "Agent misses the known vulnerability"

7. **Tags**: For filtering and selection
   - Tier: `CT`, `BT`
   - Type: `smoke`, `regression`, `e2e`
   - Feature: `access-control`, `reentrancy`, `oracle`, etc.

### Step 2: Generate Scenario YAML

Create the scenario file at `.vrs/testing/scenarios/<category>/<id>.yaml`.

### Step 3: Register

Add the scenario to `.vrs/testing/scenarios/registry.yaml`.

### Step 4: Validate

Verify the scenario:
- Referenced contracts exist
- Expectations are specific enough for the observer to evaluate
- Tags are consistent with existing conventions
- Category directory exists

## Scenario File Format

```yaml
id: <unique-id>
name: "<human-readable name>"
category: <category>
tier: <CT|BT|E2E>
created: <date>

project:
  contracts:
    - source: <path-in-repo>
      path: <path-in-test-project>
  additional_files: []
  config:
    install_skills: true
    install_agents: true

prompt: "<what a real user would type>"

expectations:
  - "<natural language expectation 1>"
  - "<natural language expectation 2>"

failure_conditions:
  - "<what would fail this test>"

tags: [<tag1>, <tag2>]
timeout: 300  # seconds
```

## List Process

Read the registry and display:

```
## Test Scenarios

### pattern-detection (12 scenarios)
- ct-access-control-001 [CT, smoke] — CT pattern detects missing access control
- bt-reentrancy-001 [BT, regression] — BT pattern detects cross-function reentrancy
...

### e2e-pipeline (3 scenarios)
- e2e-dvdefi-unstoppable [e2e, dvdefi] — Full audit on DVDeFi Unstoppable
...

Total: 15 scenarios | Last regression: 2026-02-09 | 12 pass, 2 fail, 1 new
```
