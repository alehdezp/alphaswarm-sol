# GAP-05, GAP-09, GAP-10, GAP-11 Resolution: Evaluation Infrastructure

**Created:** 2026-02-12
**Scope:** Orchestration scenario, adaptive escalation, workflow taxonomy, failure classification
**Status:** Resolution complete -- ready for integration into 3.1b plans

---

## REVISED: GAP-05 Orchestration Scenario (2026-02-12)

**The original GAP-05 design below (dedicated `multi-agent-reentrancy-debate/` scenario) has been replaced with a simpler approach.**

### New Approach: `modes` Field on Any Scenario

Instead of creating a separate orchestration scenario with its own contracts and team-specific ground truth, ANY existing scenario can now run in both single-agent and multi-agent mode by adding a `modes` field:

```yaml
modes: [single, team]  # run this scenario both ways
```

The evaluator runs the same contract with the same ground truth twice -- once with a single agent, once with a 3-agent team. The DIFFERENCE in output IS the orchestration test.

### What Changed (Code)

1. **`ScenarioConfig`** (`src/alphaswarm_sol/testing/scenarios/config_schema.py`): Added `modes: list[Literal["single", "team"]]` with default `["single"]`.
2. **`TestScenario`** (`src/alphaswarm_sol/testing/harness/scenario_loader.py`): Added `modes: list[str]` field, parsed from YAML with validation.
3. **`TestScenario.get_team_evaluation_questions()`**: Auto-injects team-specific evaluation questions when mode=team:
   - "Did the team find more than a single agent would?"
   - "Did evidence pass between agents via SendMessage?"
   - "Did debate improve finding confidence vs solo assessment?"

### Why This Is Better

| Aspect | Original (Dedicated Scenario) | Revised (Modes Field) |
|--------|-------------------------------|----------------------|
| Scenarios needed | 12 (10 + 2 orchestration) | 10 (any can be orchestration) |
| Maintenance | Separate contracts + ground truth for team scenario | Same contracts, same ground truth |
| Orchestration signal | "Did the team find the vuln?" | "Did the team find MORE/BETTER than solo?" (comparative) |
| Flexibility | Only reentrancy tested as team | Any scenario can be tested as team |
| Code added | ~200 LOC (contracts + YAML) | ~20 LOC (field + method + parsing) |

### What the Original Design Got Right (Preserved)

- TeamObservation model (GAP-01) is still needed for team mode evaluation
- Evidence passing between agents is still checked (via auto-injected questions)
- Escalation rules (GAP-09) still apply to team scenarios

### What the Original Design Got Wrong (Removed)

- Dedicated `LendingVault.sol` / `SafeLendingVault.sol` contracts -- unnecessary; existing corpus contracts serve the same purpose
- `expected_team_behavior` ground truth block -- too rigid; the comparative approach (single vs team output) is more informative
- `agent_team` configuration in scenario YAML -- team composition is an execution concern, not a scenario concern

**The original GAP-05 design is preserved below for reference but is no longer the implementation plan.**

---

## Table of Contents

1. [GAP-05: Orchestration Scenario](#gap-05-orchestration-scenario)
2. [GAP-09: Adaptive Escalation](#gap-09-adaptive-escalation)
3. [GAP-10: Workflow Taxonomy](#gap-10-workflow-taxonomy)
4. [GAP-11: Failure Classification](#gap-11-failure-classification)
5. [Cross-Gap Dependencies](#cross-gap-dependencies)
6. [Integration Plan](#integration-plan)
7. [Implementation Estimates](#implementation-estimates)

---

## GAP-05: Orchestration Scenario

### Problem Recap

All 10 curated scenarios are single-agent. 3.1c-11 (orchestrator flow evaluation) requires a scenario that exercises the full 3-agent team lifecycle: attacker, defender, verifier collaborating through SendMessage, with evidence passing and verdict synthesis.

### Investigation Findings

**Existing scenario infrastructure** (`src/alphaswarm_sol/testing/harness/scenario_loader.py`) supports:
- `TestScenario` with contracts, ground truth, prompt templates, allowed tools
- `ContractCase` with vulnerability expectations and ground truth findings
- Single-agent execution via `ClaudeCodeRunner.run_analysis()`

**Missing for orchestration:**
- No `agent_team` field in scenario schema
- No ground truth for team behavior (only vulnerability findings)
- No concept of inter-agent message expectations
- `WorkspaceManager` already supports transcript mapping per agent (`get_transcript_paths()`), which is a foundation

**Agent definitions examined:**
- `vrs-attacker` (catalog.yaml): Opus tier, outputs `attack_preconditions`, `attack_steps`, `exploitability`, `impact`. Must cite graph nodes.
- `vrs-defender` (catalog.yaml): Sonnet tier, outputs `guards_found`, `mitigation_analysis`, `residual_risks`. Must cite graph nodes.
- `vrs-verifier` (catalog.yaml): Opus tier, outputs `verdict`, `confidence`, `evidence_quality`, `verdict_rationale`. Synthesizes, does not analyze.

**Existing multi-agent test coverage:** `tests/e2e/test_agent_teams_harness_smoke.py` exists but is a smoke test for Agent Teams infrastructure, not a scenario-driven evaluation.

### Complete Orchestration Scenario Specification

```yaml
# Scenario ID: multi-agent-reentrancy-debate
# Location: examples/testing/scenarios/orchestration/multi-agent-reentrancy-debate/

name: multi-agent-reentrancy-debate
description: >
  Full 3-agent team lifecycle: attacker identifies reentrancy in a novel
  lending vault, defender searches for guards, verifier arbitrates with
  evidence-weighted verdict. Tests evidence passing, debate quality, and
  coordination -- not just vulnerability detection.

category: orchestration
workflow_category: orchestration  # Links to GAP-10 taxonomy

timeout: 300s

# --- Agent Team Configuration ---
agent_team:
  roles:
    - id: attacker
      agent: vrs-attacker
      model: claude-sonnet-4  # Sonnet for cost control in testing
      task: >
        Analyze the LendingVault contract for reentrancy vulnerabilities.
        Construct a concrete exploit path with preconditions, attack steps,
        and economic impact. Use BSKG queries first.
    - id: defender
      agent: vrs-defender
      model: claude-sonnet-4
      task: >
        Search for reentrancy guards, CEI pattern compliance, and other
        mitigations in the LendingVault contract. Rebut attacker claims
        if guards are found. Use BSKG queries first.
    - id: verifier
      agent: vrs-verifier
      model: claude-sonnet-4
      task: >
        Synthesize attacker and defender evidence. Weigh evidence quality,
        check graph citations, render verdict with confidence level.
        Do NOT add new analysis.
  coordination:
    protocol: sequential  # attacker -> defender -> verifier
    message_passing: true
    max_rounds: 1  # Single debate round for initial scenario

# --- Contracts Under Test ---
contracts:
  - path: contracts/LendingVault.sol
    has_vulnerability: true
    expected_pattern: reentrancy-classic
    expected_severity: critical
    ground_truth:
      - pattern: reentrancy-classic
        severity: critical
        location: "withdraw"
        line_range: [42, 58]
        behavioral_signature: "R:bal -> X:out -> W:bal"
        description: >
          External call via .call{value} before balance state update.
          No reentrancy guard. No CEI compliance.

  - path: contracts/SafeLendingVault.sol
    has_vulnerability: false
    expected_pattern: null
    ground_truth: []
    fp_control:
      guards_present:
        - type: reentrancy_guard
          location: "withdraw"
        - type: cei_pattern
          location: "withdraw"

# --- Ground Truth: Team Behavior ---
expected_team_behavior:
  # Phase 1: Attacker analysis
  attacker:
    must_execute_bskg_query: true
    must_identify_vulnerability: true
    must_produce_exploit_path: true
    must_cite_graph_nodes: true
    expected_output_fields:
      - attack_preconditions
      - attack_steps
      - exploitability
    min_evidence_items: 3

  # Phase 2: Defender analysis
  defender:
    must_execute_bskg_query: true
    must_search_for_guards: true
    must_check_cei_pattern: true
    must_cite_graph_nodes: true
    expected_output_fields:
      - guards_found
      - mitigation_analysis
    # For VulnerableVault: should find NO effective guards
    # For SafeVault: should find reentrancy guard + CEI

  # Phase 3: Verifier synthesis
  verifier:
    must_cite_both_sides: true
    must_render_verdict: true
    must_not_add_new_analysis: true
    expected_output_fields:
      - verdict
      - confidence
      - evidence_quality
      - verdict_rationale
    verdict_expectation:
      vulnerable_contract: CONFIRMED  # or LIKELY
      safe_contract: REJECTED  # or UNCERTAIN

  # Cross-agent coordination
  coordination:
    evidence_passes_between_agents: true
    min_sendmessage_count: 2  # At least attacker->verifier, defender->verifier
    all_agents_complete: true
    debate_depth:
      min_rounds: 1
      genuine_engagement: true  # Not rubber-stamping

# --- Evaluation Guidance ---
evaluation_guidance:
  reasoning_questions:
    - "Did the attacker construct a concrete exploit path with specific code locations, or just say 'reentrancy exists'?"
    - "Did the defender genuinely search for guards (CEI, mutex, access control) or just confirm the attacker's finding?"
    - "Did the verifier cite evidence from BOTH attacker and defender, or only one side?"
    - "Was the verdict grounded in evidence quality comparison, or arbitrary?"
    - "Did all agents use BSKG queries before reaching conclusions?"
    - "Did agents pass evidence through SendMessage, or work in isolation?"
  hooks_if_failed:
    - SubagentStart
    - SubagentStop
    - PreToolUse
    - PostToolUse
  check_graph_usage: true
  check_evidence_grounding: true
  check_task_lifecycle: true

  # Adaptive escalation (GAP-09 integration)
  escalation_rules:
    - condition: no_bskg_queries_any_agent
      actions:
        - flag: graph_first_violation
        - add_questions:
          - "Why did no agent execute BSKG queries? This violates graph-first mandate."
    - condition: verifier_adds_new_analysis
      actions:
        - flag: role_violation
        - add_questions:
          - "The verifier should synthesize, not analyze. Did it add new findings?"
    - condition: no_sendmessage_between_agents
      actions:
        - flag: coordination_failure
        - add_questions:
          - "Agents appear to have worked in isolation. Was evidence actually passed?"

# --- Evaluation (3.1c slot) ---
evaluation:
  contract: vrs-orchestration-debate
  run_gvs: true
  run_reasoning: true
  run_team_assessment: true

# --- Post-Run Hooks ---
post_run_hooks:
  - hooks/evaluate_reasoning.py
  - hooks/compute_gvs.py
  - hooks/assess_team_coordination.py
```

### Contract Specifications

**LendingVault.sol** (vulnerable -- novel contract, not from any public CTF):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title LendingVault - A simple lending vault with a reentrancy vulnerability
/// @notice This is a TEST CONTRACT for evaluation purposes only.
/// @dev Novel contract -- not derived from any public CTF or tutorial.
///      Business context: A peer-to-peer micro-lending vault where users
///      deposit ETH as collateral and can withdraw after loan repayment.
contract LendingVault {
    struct Account {
        uint256 deposited;
        uint256 borrowed;
        uint256 lastActivity;
    }

    mapping(address => Account) public accounts;
    uint256 public totalDeposits;
    uint256 public protocolFeesBps = 50; // 0.5%
    address public admin;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Borrowed(address indexed user, uint256 amount);
    event Repaid(address indexed user, uint256 amount);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        accounts[msg.sender].deposited += msg.value;
        accounts[msg.sender].lastActivity = block.timestamp;
        totalDeposits += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Withdraw deposited collateral
    /// @dev VULNERABLE: external call before state update (classic reentrancy)
    function withdraw(uint256 amount) external {
        Account storage acct = accounts[msg.sender];
        require(acct.deposited >= amount, "Insufficient balance");
        require(acct.borrowed == 0, "Outstanding loan");

        // BUG: External call BEFORE state update
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        // State update AFTER external call -- reentrancy window
        acct.deposited -= amount;
        totalDeposits -= amount;
        acct.lastActivity = block.timestamp;

        emit Withdrawn(msg.sender, amount);
    }

    function borrow(uint256 amount) external {
        Account storage acct = accounts[msg.sender];
        uint256 maxBorrow = acct.deposited / 2; // 50% LTV
        require(amount <= maxBorrow - acct.borrowed, "Exceeds LTV");

        acct.borrowed += amount;
        acct.lastActivity = block.timestamp;

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        emit Borrowed(msg.sender, amount);
    }

    function repay() external payable {
        Account storage acct = accounts[msg.sender];
        require(acct.borrowed > 0, "No loan");

        uint256 fee = (msg.value * protocolFeesBps) / 10000;
        uint256 repayment = msg.value - fee;

        require(repayment <= acct.borrowed, "Overpayment");
        acct.borrowed -= repayment;
        acct.lastActivity = block.timestamp;

        emit Repaid(msg.sender, repayment);
    }

    function setFee(uint256 newFeeBps) external onlyAdmin {
        require(newFeeBps <= 1000, "Fee too high"); // Max 10%
        protocolFeesBps = newFeeBps;
    }

    receive() external payable {}
}
```

**SafeLendingVault.sol** (safe -- same business logic, proper guards):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title SafeLendingVault - Secured lending vault (FP control)
contract SafeLendingVault is ReentrancyGuard {
    struct Account {
        uint256 deposited;
        uint256 borrowed;
        uint256 lastActivity;
    }

    mapping(address => Account) public accounts;
    uint256 public totalDeposits;
    uint256 public protocolFeesBps = 50;
    address public admin;

    // ... same events and constructor ...

    /// @notice Withdraw with CEI pattern + reentrancy guard
    function withdraw(uint256 amount) external nonReentrant {
        Account storage acct = accounts[msg.sender];
        require(acct.deposited >= amount, "Insufficient balance");
        require(acct.borrowed == 0, "Outstanding loan");

        // CEI: Effects before Interactions
        acct.deposited -= amount;
        totalDeposits -= amount;
        acct.lastActivity = block.timestamp;

        // Interaction after effects
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    // ... rest same but with nonReentrant on borrow() ...
}
```

### TeamObservation Integration (GAP-01 Dependency)

This scenario requires `TeamObservation` from GAP-01. The ground truth fields map directly:

| Ground Truth Field | TeamObservation Method |
|---|---|
| `evidence_passes_between_agents` | `team_obs.message_graph` has edges between agents |
| `min_sendmessage_count` | `len(team_obs.message_graph) >= 2` |
| `all_agents_complete` | All agents in `team_obs.agents` have non-empty transcripts |
| `debate_depth.genuine_engagement` | `team_obs.agreement_depth() >= 1.0` |
| Per-agent `must_execute_bskg_query` | `team_obs.agents["attacker"].transcript.has_bskg_query()` |

---

## GAP-09: Adaptive Escalation

### Problem Recap

`evaluation_guidance` is static YAML. The evaluator (Claude Code in 3.1c) would benefit from conditional rules: "if X observed, also check Y." Currently, the evaluator must manually decide what additional checks to perform when something unexpected happens.

### Investigation Findings

**Current evaluation_guidance schema** (from context.md Plan 3.1b-05):
```yaml
evaluation_guidance:
  reasoning_questions: list[str]
  hooks_if_failed: list[str]
  check_graph_usage: bool
  check_evidence_grounding: bool
  check_task_lifecycle: bool
```

**Observable conditions** from existing infrastructure:
- `ClaudeCodeResult.return_code` -- exit status
- `ClaudeCodeResult.cost_usd` -- API cost (0 = no API call)
- `ClaudeCodeResult.duration_ms` -- execution time
- `TranscriptParser.has_bskg_query()` -- graph usage
- `TranscriptParser.tool_calls` -- tool usage patterns
- `WorkspaceManager.get_transcript_paths()` -- per-agent transcripts available
- `TrajectoryMetrics` (from evaluator.py) -- efficiency, coherence, etc.

**No existing conditional evaluation logic** was found. All evaluation is currently either static (grader-based) or manual (human/Claude Code reading guidance questions).

### Escalation Rules Schema Extension

```yaml
# Optional field in evaluation_guidance
escalation_rules:
  - condition: <condition_id>
    description: <human-readable explanation>
    actions:
      - type: enable_hooks
        hooks: [<hook_event_names>]
      - type: add_questions
        questions: [<additional reasoning questions>]
      - type: flag
        flag_id: <string>
        severity: <info|warning|error>
      - type: increase_trials
        additional_trials: <int>
      - type: request_debrief
        debrief_prompt: <string>
```

### Condition Vocabulary

Conditions are string identifiers that the 3.1c evaluator resolves at runtime by inspecting `CollectedOutput`. 3.1b defines the vocabulary; 3.1c implements the resolution logic.

| Condition ID | Detection Logic (3.1c implements) | Observable Signal |
|---|---|---|
| `no_bskg_queries` | `transcript.has_bskg_query() == False` | No `alphaswarm` in Bash commands |
| `no_bskg_queries_any_agent` | All agents in `TeamObservation` lack BSKG queries | Multi-agent variant |
| `all_findings_low_confidence` | All findings have `confidence < 0.5` | Structured output inspection |
| `execution_under_10_seconds` | `output.duration_ms < 10000` | Suspiciously fast |
| `execution_over_5_minutes` | `output.duration_ms > 300000` | Possibly stuck |
| `zero_tool_calls` | `len(output.tool_calls) == 0` | No tools used at all |
| `no_sendmessage_between_agents` | `TeamObservation.message_graph` is empty | Agents worked in isolation |
| `verifier_adds_new_analysis` | Verifier transcript contains new BSKG queries | Role violation |
| `high_error_rate` | `trajectory.error_count / trajectory.tool_call_count > 0.5` | Tooling issues |
| `no_structured_output` | `output.structured_output is None` | Schema violation or crash |
| `graph_not_built` | No `build-kg` in Bash commands | Fundamental workflow skip |

### Concrete Escalation Rules

**Rule 1: Graph-First Violation**
```yaml
- condition: no_bskg_queries
  description: "Agent did not execute any BSKG queries, violating graph-first mandate"
  actions:
    - type: enable_hooks
      hooks: [PreToolUse, PostToolUse]
    - type: add_questions
      questions:
        - "Why were no graph queries executed? What alternative evidence sources were used?"
        - "Did the agent read code manually instead of querying the graph?"
    - type: flag
      flag_id: graph_first_violation
      severity: warning
```

**Rule 2: Suspiciously Fast Execution**
```yaml
- condition: execution_under_10_seconds
  description: "Execution completed in under 10 seconds -- possible fabrication or cached response"
  actions:
    - type: add_questions
      questions:
        - "Was real analysis performed or was the response pre-formed?"
        - "Did the agent actually read the contract before producing findings?"
    - type: flag
      flag_id: possible_fabrication
      severity: error
    - type: increase_trials
      additional_trials: 2
```

**Rule 3: Silent Agents (Orchestration)**
```yaml
- condition: no_sendmessage_between_agents
  description: "No inter-agent messages detected in a multi-agent scenario"
  actions:
    - type: enable_hooks
      hooks: [SubagentStart, SubagentStop, TeammateIdle]
    - type: add_questions
      questions:
        - "Agents appear to have worked in isolation. Was evidence actually passed?"
        - "Did the orchestrator correctly route findings between agents?"
    - type: flag
      flag_id: coordination_failure
      severity: error
```

**Rule 4: Low Confidence Across All Findings**
```yaml
- condition: all_findings_low_confidence
  description: "All findings have confidence below 0.5 -- agent may be uncertain or guessing"
  actions:
    - type: add_questions
      questions:
        - "Were agents given sufficient context to make confident assessments?"
        - "Is the vulnerability genuinely ambiguous, or is the agent lacking information?"
    - type: request_debrief
      debrief_prompt: >
        Your findings all had low confidence. What information would have
        increased your confidence? What were you uncertain about?
```

**Rule 5: High Tool Error Rate**
```yaml
- condition: high_error_rate
  description: "More than half of tool calls failed -- likely infrastructure issue"
  actions:
    - type: flag
      flag_id: infrastructure_degraded
      severity: warning
    - type: add_questions
      questions:
        - "Were tool failures due to misconfiguration, permissions, or actual bugs?"
        - "Did the agent recover from errors or get stuck in a loop?"
```

### Python Schema for Escalation Rules

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EscalationActionType(Enum):
    ENABLE_HOOKS = "enable_hooks"
    ADD_QUESTIONS = "add_questions"
    FLAG = "flag"
    INCREASE_TRIALS = "increase_trials"
    REQUEST_DEBRIEF = "request_debrief"


class FlagSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class EscalationAction:
    type: EscalationActionType
    hooks: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    flag_id: str | None = None
    flag_severity: FlagSeverity = FlagSeverity.INFO
    additional_trials: int = 0
    debrief_prompt: str | None = None


@dataclass
class EscalationRule:
    condition: str  # Condition ID from vocabulary
    description: str
    actions: list[EscalationAction]


@dataclass
class EvaluationGuidance:
    """Extended evaluation guidance with optional escalation rules."""
    reasoning_questions: list[str] = field(default_factory=list)
    hooks_if_failed: list[str] = field(default_factory=list)
    check_graph_usage: bool = False
    check_evidence_grounding: bool = False
    check_task_lifecycle: bool = False

    # GAP-09 extension: optional adaptive escalation
    escalation_rules: list[EscalationRule] = field(default_factory=list)
```

### Integration Point

3.1b-05 (Scenario DSL) adds `escalation_rules` as an **optional** field in the `evaluation_guidance` YAML block. The ScenarioLoader parses it into `EvaluationGuidance.escalation_rules`. 3.1c implements the condition evaluation and action execution.

**3.1b responsibility:** Parse and validate the schema. Reject unknown condition IDs at load time (optional, could also defer to 3.1c).

**3.1c responsibility:** At evaluation time, check each condition against `CollectedOutput`, execute matching actions.

---

## GAP-10: Workflow Taxonomy

### Problem Recap

Workflow categories (investigation, tool_integration, orchestration, support) exist only in prose. 3.1c's smart selection matrix needs these as structured data to map scenarios to evaluation dimensions and required hooks.

### Investigation Findings

**Existing categorization in registry.yaml:**

The skill registry already uses `category` as a field:
- `orchestration`: audit, orch-spawn, orch-resume, health-check, bead-create, bead-list, bead-update, etc.
- `investigation`: investigate, verify, debate
- `validation`: test-full, test-quick, test-component, validate-vulndocs, benchmark-model, mutate-contract
- `discovery`: discover, research, ingest-url, add-vulnerability, merge-findings
- `pattern-development`: pattern-forge, refine, test-pattern, pattern-verify, pattern-batch
- `tool-integration`: tool-slither, tool-aderyn, tool-mythril, tool-coordinator
- `context`: context-pack, evidence-audit, graph-contract-validate, ordering-proof, etc.
- `development`: test-builder, agent-skillcraft, gsd-research-context, etc.

**Key observation:** The registry categories do NOT align perfectly with the 3.1c evaluation categories. The registry is organized by function (what the skill does), while 3.1c needs categories organized by evaluation strategy (how to evaluate it).

**Agent catalog roles** provide complementary data:
- `attacker`, `defender`, `verifier` -- core investigation
- `orchestrator` -- coordination
- `triage`, `curator` -- support functions
- `tester`, `auditor` -- validation

### Complete Workflow Taxonomy

```yaml
# workflow-categories.yaml
# Source of truth for 3.1c evaluation dimension mapping
# Location: examples/testing/guidelines/workflow-categories.yaml

version: "1.0.0"
description: >
  Maps workflow categories to evaluation strategies, required hooks,
  and applicable skills/agents. Used by 3.1c smart selection matrix
  to determine WHAT to evaluate and HOW.

# --- Category Definitions ---
categories:
  investigation:
    description: >
      Deep vulnerability analysis with graph reasoning.
      Single-agent workflows that analyze contracts for security issues
      using BSKG queries, semantic operations, and evidence-based conclusions.
    evaluation_strategy: reasoning_quality
    skills:
      - investigate     # Graph-first vulnerability investigation
      - verify          # Evidence cross-checking
      - debate          # Multi-agent debate protocol
      - audit           # Full audit (when single-agent mode)
    agents:
      - vrs-attacker
      - vrs-defender
      - vrs-verifier
      - vrs-secure-reviewer
      - vrs-pattern-scout
      - vrs-pattern-verifier
      - vrs-pattern-composer
    evaluation_dimensions:
      graph_utilization:
        description: "Did the agent use BSKG queries before reaching conclusions?"
        weight: 0.25
        required: true
        metric: "graph_citation_rate >= 0.5"
      evidence_quality:
        description: "Are findings grounded in specific code locations and graph nodes?"
        weight: 0.25
        required: true
        metric: "evidence_items >= 3 per finding"
      reasoning_depth:
        description: "Did the agent follow a logical chain from observation to conclusion?"
        weight: 0.25
        required: true
        metric: "reasoning_coherence >= 0.6"
      hypothesis_testing:
        description: "Did the agent consider alternative explanations?"
        weight: 0.15
        required: false
        metric: "guards_checked OR counterarguments_considered"
      behavioral_signatures:
        description: "Did the agent identify semantic operation sequences?"
        weight: 0.10
        required: false
        metric: "behavioral_signature_referenced == true"
    required_hooks:
      - PreToolUse    # Track tool selection decisions
      - PostToolUse   # Track tool results
    optional_hooks:
      - SubagentStart  # If sub-investigation spawned
      - SubagentStop

  tool_integration:
    description: >
      External tool coordination and result synthesis.
      Workflows that run Slither, Aderyn, Mythril, etc. and interpret results.
      Evaluation focuses on tool selection, result interpretation, and dedup.
    evaluation_strategy: output_correctness
    skills:
      - tool-slither
      - tool-aderyn
      - tool-mythril
      - tool-coordinator
    agents: []  # Tools run in main agent context, not as subagents
    evaluation_dimensions:
      tool_selection:
        description: "Was the right tool chosen for the vulnerability class?"
        weight: 0.30
        required: true
        metric: "appropriate_tool_for_vuln_class == true"
      result_interpretation:
        description: "Were tool results correctly parsed and meaningful findings extracted?"
        weight: 0.30
        required: true
        metric: "findings_match_tool_output"
      finding_deduplication:
        description: "Were duplicate findings from multiple tools merged correctly?"
        weight: 0.20
        required: false
        metric: "no_exact_duplicate_findings"
      error_handling:
        description: "Were tool failures handled gracefully?"
        weight: 0.20
        required: true
        metric: "tool_failure_did_not_crash_workflow"
    required_hooks:
      - PreToolUse   # Capture tool invocation decisions
      - PostToolUse  # Capture tool output
    optional_hooks: []

  orchestration:
    description: >
      Multi-agent coordination and team lifecycle.
      Workflows involving 2+ agents collaborating through debate protocol.
      Evaluation focuses on coordination quality, evidence passing, and
      verdict grounding -- in addition to underlying vulnerability detection.
    evaluation_strategy: team_assessment
    skills:
      - audit    # Full audit with team mode
      - debate   # Structured adversarial debate
    agents:
      - vrs-attacker
      - vrs-defender
      - vrs-verifier
      - vrs-supervisor
      - vrs-integrator
    evaluation_dimensions:
      coordination_quality:
        description: "Did agents collaborate effectively through the protocol?"
        weight: 0.20
        required: true
        metric: "sendmessage_count >= expected_min"
      evidence_passing:
        description: "Was evidence correctly routed between agents?"
        weight: 0.25
        required: true
        metric: "evidence_chain_complete == true"
      verdict_grounding:
        description: "Was the final verdict grounded in evidence from both sides?"
        weight: 0.25
        required: true
        metric: "verifier_cites_both_attacker_and_defender"
      debate_depth:
        description: "Was the debate genuine or rubber-stamped?"
        weight: 0.20
        required: true
        metric: "agreement_depth >= 1.0"
      role_compliance:
        description: "Did each agent stay within their defined role?"
        weight: 0.10
        required: true
        metric: "no_role_violations"
    required_hooks:
      - SubagentStart
      - SubagentStop
      - PreToolUse
      - PostToolUse
    optional_hooks:
      - TeammateIdle
      - TaskCompleted

  support:
    description: >
      Utility workflows with deterministic or near-deterministic expected output.
      Health checks, bead management, status queries. Evaluation is primarily
      output correctness with simple graders (exact match, schema validation).
    evaluation_strategy: deterministic_check
    skills:
      - health-check
      - bead-create
      - bead-update
      - bead-list
      - orch-spawn
      - orch-resume
    agents: []
    evaluation_dimensions:
      output_correctness:
        description: "Does the output match expected schema and content?"
        weight: 0.60
        required: true
        metric: "schema_valid AND content_matches_expected"
      error_handling:
        description: "Are error cases handled with clear messages?"
        weight: 0.30
        required: true
        metric: "error_message_includes_actionable_fix"
      idempotency:
        description: "Does repeated execution produce consistent results?"
        weight: 0.10
        required: false
        metric: "output_stable_across_trials"
    required_hooks: []
    optional_hooks:
      - PreToolUse
      - PostToolUse

  discovery:
    description: >
      Knowledge acquisition workflows. Web research, URL ingestion, pattern
      creation. Evaluated on knowledge quality and novelty, not vulnerability
      detection.
    evaluation_strategy: knowledge_quality
    skills:
      - discover
      - research
      - ingest-url
      - add-vulnerability
      - merge-findings
    agents:
      - vrs-prevalidator
    evaluation_dimensions:
      source_quality:
        description: "Were sources relevant and authoritative?"
        weight: 0.30
        required: true
        metric: "sources_from_known_security_domains"
      extraction_accuracy:
        description: "Was vulnerability information correctly extracted?"
        weight: 0.35
        required: true
        metric: "pattern_fields_populated_correctly"
      novelty:
        description: "Does the extracted knowledge add something new?"
        weight: 0.20
        required: false
        metric: "not_duplicate_of_existing_pattern"
      schema_compliance:
        description: "Does output conform to VulnDocs schema?"
        weight: 0.15
        required: true
        metric: "vulndocs_validate_passes"
    required_hooks:
      - PreToolUse
    optional_hooks: []

# --- Evaluation Strategy Descriptions ---
evaluation_strategies:
  reasoning_quality:
    description: "LLM-powered assessment of reasoning chain quality"
    primary_scorer: graph_value_scorer
    secondary_scorers: [trajectory_evaluator, reasoning_coherence_scorer]
    requires_transcript: true
    requires_bskg_queries: true

  output_correctness:
    description: "Deterministic + schema-based output validation"
    primary_scorer: code_grader
    secondary_scorers: [schema_validator]
    requires_transcript: false
    requires_bskg_queries: false

  team_assessment:
    description: "Multi-agent coordination quality evaluation"
    primary_scorer: team_observation_scorer
    secondary_scorers: [graph_value_scorer, trajectory_evaluator]
    requires_transcript: true
    requires_bskg_queries: true
    requires_team_observation: true

  deterministic_check:
    description: "Simple pass/fail with exact match and schema graders"
    primary_scorer: code_grader
    secondary_scorers: []
    requires_transcript: false
    requires_bskg_queries: false

  knowledge_quality:
    description: "Quality assessment of extracted knowledge artifacts"
    primary_scorer: schema_validator
    secondary_scorers: [model_grader]
    requires_transcript: false
    requires_bskg_queries: false

# --- Scenario-to-Category Mapping ---
# Each scenario in the corpus specifies its workflow_category.
# This mapping is used by 3.1c-06 (evaluation contracts) for smart selection.
category_selection_rules:
  - if_agent_team_defined: orchestration
  - if_skill_in: [tool-slither, tool-aderyn, tool-mythril, tool-coordinator]
    then: tool_integration
  - if_skill_in: [health-check, bead-create, bead-update, bead-list]
    then: support
  - if_skill_in: [discover, research, ingest-url, add-vulnerability]
    then: discovery
  - default: investigation
```

### Rationale

The taxonomy uses two organizational axes:

1. **What the workflow does** (category) -- determines which evaluation dimensions apply
2. **How to evaluate it** (evaluation_strategy) -- determines which scorers and infrastructure to use

This separation means a single scenario can be categorized precisely. The `category_selection_rules` at the bottom provide automatic categorization for scenarios that do not explicitly declare a `workflow_category`.

### REVISED (2026-02-12): Inline Categories Instead of Separate File

**Original plan:** Create `workflow-categories.yaml` as a standalone file in `examples/testing/guidelines/`.

**Revised approach:** Add `category` field directly to the existing registries:
- `src/alphaswarm_sol/skills/registry.yaml` -- already had `category` field with 8 granular categories (orchestration, investigation, validation, discovery, pattern-development, tool-integration, context, development). These map naturally to the 5 GAP-10 workflow evaluation categories.
- `src/alphaswarm_sol/agents/catalog.yaml` -- added `category` field to all 24 agents using the 5-category taxonomy: investigation, tool_integration, orchestration, support, discovery.

**Why this is better:**
1. **No drift risk.** The taxonomy lives in the same file as the data it categorizes. A separate `workflow-categories.yaml` would need to be kept in sync with both registries -- a maintenance burden with no benefit.
2. **Already partially done.** The skill registry already had a `category` field. Only the agent catalog was missing it.
3. **Queryable from code.** Any code that loads `catalog.yaml` or `registry.yaml` gets the category for free. No need to load and cross-reference a separate file.
4. **The `category_selection_rules`** from the original taxonomy YAML are still valid as logic -- they just live in the 3.1c evaluator code rather than in a YAML file that nobody parses.

**Agent category assignments:**

| Agent | Category | Rationale |
|-------|----------|-----------|
| vrs-attacker | investigation | Core vulnerability analysis |
| vrs-defender | investigation | Core vulnerability analysis |
| vrs-verifier | investigation | Evidence cross-checking |
| vrs-secure-reviewer | investigation | Evidence-first security review |
| vrs-supervisor | orchestration | Multi-agent coordination |
| vrs-integrator | orchestration | Report synthesis |
| vrs-test-conductor | orchestration | Validation pipeline orchestration |
| vrs-pattern-scout | investigation | Fast triage for investigation pipeline |
| vrs-pattern-verifier | investigation | Pattern match verification |
| vrs-pattern-composer | investigation | Composite vulnerability discovery |
| vrs-finding-synthesizer | investigation | Evidence synthesis with confidence bounds |
| vrs-contradiction | investigation | Adversarial refutation |
| vrs-gap-finder | investigation | Deep coverage analysis with graph reasoning |
| vrs-gap-finder-lite | investigation | Fast coverage scan variant |
| vrs-context-packer | support | Context assembly utility |
| vrs-finding-merger | support | Deterministic dedup utility |
| vrs-corpus-curator | support | Corpus validation utility |
| vrs-benchmark-runner | support | Metrics collection utility |
| vrs-mutation-tester | support | Contract variant generation utility |
| vrs-regression-hunter | support | Regression detection utility |
| vrs-prevalidator | discovery | URL provenance for knowledge ingestion |
| skill-auditor | support | Development-only quality auditing |
| cost-governor | support | Budget-aware routing |
| gsd-context-researcher | discovery | Deep web research |

**Deliverable:** No new file. `category` field added to `catalog.yaml` (24 agents). `registry.yaml` unchanged (already had categories).

---

## GAP-11: Failure Classification

### Problem Recap

When a scenario fails, we need to classify WHY to route failures correctly. Without classification, every failure requires manual triage -- unsustainable at scale.

### Investigation Findings

**Available data from existing infrastructure:**

From `ClaudeCodeResult`:
- `return_code` (int) -- 0 = success
- `cost_usd` (float) -- 0 = no API call made
- `duration_ms` (int) -- execution time
- `structured_output` (dict | None) -- parsed findings
- `stderr` (str) -- error output
- `raw_output` (str) -- full stdout

From `TrajectoryMetrics` (evaluator.py):
- `tool_efficiency` (float) -- successful tool call ratio
- `error_recovery_rate` (float) -- recovery from errors
- `dead_end_ratio` (float) -- unproductive exploration

From `WorkspaceManager`:
- `get_session_info()` -- hook-written metadata
- `get_transcript_paths()` -- per-agent transcript availability

From `TranscriptParser` (planned in 3.1b-02):
- `has_bskg_query()` -- graph usage
- `tool_calls` -- all tool invocations
- Text content for reasoning analysis

**No existing classification logic** was found. Error handling in `ClaudeCodeRunner` is limited to `TimeoutError` and `RuntimeError` with no categorization.

### Failure Classification Model

```python
"""Failure classification for scenario evaluation.

Classifies WHY a scenario failed to route failures to the correct
remediation path. Integrated into OutputCollector (3.1b-02).

Design principles:
- Rule-based heuristics for speed and determinism
- Confidence scores for borderline cases
- Composable: multiple signals can reinforce a classification
- Extensible: 3.1c can add LLM-based classification on top
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureCategory(Enum):
    """Why a scenario failed.

    Categories are ordered from most actionable (infrastructure) to
    least actionable (flaky). This ordering reflects triage priority:
    fix infrastructure first, then capabilities, then reasoning.
    """

    INFRASTRUCTURE = "infrastructure"
    # Hook did not fire, CLI crashed, API unreachable, workspace setup failed.
    # Action: Fix environment, not the agent.
    # Signals: non-zero exit code, zero cost, stderr contains known error patterns.

    CAPABILITY = "capability"
    # Agent ran but could not complete the task. Wrong tools used, output
    # schema violated, agent crashed mid-execution, permissions error.
    # Action: Fix skill prompt, tool permissions, or agent configuration.
    # Signals: zero tool calls, minimal output, schema validation failure.

    REASONING = "reasoning"
    # Agent completed execution and produced output, but the analysis was
    # incorrect. Missed vulnerability, false positive, poor evidence quality,
    # graph-first violation, or weak reasoning chain.
    # Action: Improve prompts, patterns, or evaluation criteria.
    # Signals: output exists but does not match ground truth.

    GROUND_TRUTH = "ground_truth"
    # The scenario's expected findings appear to be wrong. Agent found
    # something legitimate that the ground truth does not account for,
    # or the expected vulnerability does not actually exist.
    # Action: Review and update the scenario, not the agent.
    # Signals: agent output is well-reasoned but contradicts ground truth.

    FLAKY = "flaky"
    # Non-deterministic failure. Passed in some trials, failed in others.
    # Action: Increase trials, add retry logic, or accept variance.
    # Signals: mixed pass/fail across trials for identical input.

    UNKNOWN = "unknown"
    # Cannot classify with available heuristics.
    # Action: Manual triage required.
    # Signals: none of the rule-based heuristics triggered.


@dataclass
class ClassifiedFailure:
    """A classified failure with evidence and suggested action.

    Attributes:
        category: The failure category.
        evidence: What observation led to this classification.
        suggested_action: What to do about it (human-readable).
        confidence: How confident the classification is (0.0-1.0).
        signals: Raw signal values that contributed to classification.
        secondary_category: Optional second-most-likely category.
    """

    category: FailureCategory
    evidence: str
    suggested_action: str
    confidence: float
    signals: dict[str, Any] = field(default_factory=dict)
    secondary_category: FailureCategory | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "signals": self.signals,
            "secondary_category": (
                self.secondary_category.value
                if self.secondary_category
                else None
            ),
        }


@dataclass
class FailureSignals:
    """Observable signals extracted from CollectedOutput.

    This is the input to classify_failure(). Extracted once from
    CollectedOutput, then passed to the classifier. Separating
    extraction from classification makes testing straightforward.
    """

    exit_code: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    tool_call_count: int = 0
    transcript_chars: int = 0
    structured_output_present: bool = False
    stderr_text: str = ""
    has_bskg_query: bool = False
    findings_count: int = 0
    findings_match_ground_truth: bool = False
    ground_truth_count: int = 0
    schema_valid: bool = True
    trial_results: list[bool] | None = None  # None if single trial

    @property
    def has_output(self) -> bool:
        return self.transcript_chars > 200

    @property
    def is_flaky(self) -> bool:
        if self.trial_results is None or len(self.trial_results) < 2:
            return False
        return 0 < sum(self.trial_results) < len(self.trial_results)


# --- Infrastructure Error Patterns ---
# Strings in stderr that indicate infrastructure failures, not agent failures.
INFRA_ERROR_PATTERNS = [
    "ECONNREFUSED",
    "ENOTFOUND",
    "ETIMEDOUT",
    "rate_limit",
    "Rate limit",
    "overloaded_error",
    "api_error",
    "Could not connect",
    "command not found",
    "No such file or directory",
    "Permission denied",
    "ENOMEM",
    "Killed",
    "hook_timeout",
    "bun:",  # Companion infrastructure
]

# Capability error patterns (agent-level, not infra-level).
CAPABILITY_ERROR_PATTERNS = [
    "tool not allowed",
    "Tool not allowed",
    "permission denied for tool",
    "max_turns_reached",
    "context_window_exceeded",
    "output too large",
]


def extract_signals(
    result: Any,  # ClaudeCodeResult or CollectedOutput
    ground_truth: list[dict[str, Any]] | None = None,
    trial_results: list[bool] | None = None,
) -> FailureSignals:
    """Extract classification signals from a result object.

    Accepts either ClaudeCodeResult (from harness runner) or
    CollectedOutput (from 3.1b-02 OutputCollector). Duck-typed
    to work with both.

    Args:
        result: Execution result with standard fields.
        ground_truth: Expected findings for comparison.
        trial_results: Pass/fail results across multiple trials.

    Returns:
        FailureSignals ready for classification.
    """
    # Duck-type field access for compatibility with both result types
    exit_code = getattr(result, "return_code", 0) or getattr(
        result, "exit_code", 0
    )
    cost_usd = getattr(result, "cost_usd", 0.0) or getattr(
        result, "total_cost_usd", 0.0
    )
    duration_ms = getattr(result, "duration_ms", 0)
    stderr = getattr(result, "stderr", "")

    # Tool calls -- try multiple attribute names
    tool_calls = getattr(result, "tool_calls", [])
    tool_call_count = (
        len(tool_calls) if isinstance(tool_calls, list) else 0
    )

    # Transcript / output size
    raw_output = getattr(result, "raw_output", "") or getattr(
        result, "result_text", ""
    )
    transcript_chars = len(raw_output) if raw_output else 0

    # Structured output
    structured = getattr(result, "structured_output", None)
    structured_present = structured is not None

    # BSKG query detection
    has_bskg = getattr(result, "has_bskg_query", None)
    if has_bskg is None and raw_output:
        has_bskg = "alphaswarm" in raw_output.lower()
    has_bskg = bool(has_bskg)

    # Findings
    findings = []
    if structured and isinstance(structured, dict):
        findings = structured.get("findings", [])
    findings_count = len(findings) if isinstance(findings, list) else 0

    # Ground truth comparison
    gt_count = len(ground_truth) if ground_truth else 0
    findings_match = False
    if ground_truth and findings_count > 0:
        # Simple heuristic: at least one finding matches at least one GT
        for f in findings:
            if not isinstance(f, dict):
                continue
            f_pattern = f.get("pattern", "").lower()
            for gt in ground_truth:
                gt_pattern = gt.get("pattern", "").lower()
                if gt_pattern and (
                    gt_pattern in f_pattern or f_pattern in gt_pattern
                ):
                    findings_match = True
                    break
            if findings_match:
                break

    return FailureSignals(
        exit_code=exit_code,
        cost_usd=cost_usd,
        duration_ms=duration_ms,
        tool_call_count=tool_call_count,
        transcript_chars=transcript_chars,
        structured_output_present=structured_present,
        stderr_text=stderr,
        has_bskg_query=has_bskg,
        findings_count=findings_count,
        findings_match_ground_truth=findings_match,
        ground_truth_count=gt_count,
        schema_valid=structured_present,  # If structured output parsed, schema is valid
        trial_results=trial_results,
    )


def classify_failure(signals: FailureSignals) -> ClassifiedFailure:
    """Classify a failure using rule-based heuristics.

    Rules are evaluated in priority order. The first matching rule
    determines the primary category. Lower-priority matches become
    the secondary_category for context.

    Priority order:
    1. Flaky (requires multi-trial data, highest confidence when detected)
    2. Infrastructure (environment issues, not agent issues)
    3. Capability (agent-level execution failures)
    4. Ground truth (agent seems right, ground truth seems wrong)
    5. Reasoning (default for "output exists but wrong")
    6. Unknown (nothing matched)

    Args:
        signals: Pre-extracted failure signals.

    Returns:
        ClassifiedFailure with category, evidence, and confidence.
    """
    candidates: list[ClassifiedFailure] = []

    # --- Rule 1: Flaky detection (highest priority if multi-trial) ---
    if signals.is_flaky:
        pass_count = sum(signals.trial_results)  # type: ignore[arg-type]
        total = len(signals.trial_results)  # type: ignore[arg-type]
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.FLAKY,
                evidence=(
                    f"Passed {pass_count}/{total} trials "
                    f"-- non-deterministic"
                ),
                suggested_action=(
                    "Increase trial count to establish stable pass rate. "
                    "If pass rate > 70%, mark as acceptable variance."
                ),
                confidence=0.95,
                signals={"pass_rate": pass_count / total},
            )
        )

    # --- Rule 2: Infrastructure failures ---
    if signals.exit_code != 0:
        # Check for known infra error patterns in stderr
        infra_match = _match_patterns(
            signals.stderr_text, INFRA_ERROR_PATTERNS
        )
        if infra_match:
            candidates.append(
                ClassifiedFailure(
                    category=FailureCategory.INFRASTRUCTURE,
                    evidence=(
                        f"Exit code {signals.exit_code}, "
                        f"stderr matched: '{infra_match}'"
                    ),
                    suggested_action=(
                        "Fix infrastructure: check API connectivity, "
                        "hook configuration, and CLI installation."
                    ),
                    confidence=0.90,
                    signals={
                        "exit_code": signals.exit_code,
                        "infra_pattern": infra_match,
                    },
                )
            )
        else:
            # Non-zero exit without known infra pattern -- could be capability
            candidates.append(
                ClassifiedFailure(
                    category=FailureCategory.INFRASTRUCTURE,
                    evidence=f"Exit code {signals.exit_code}",
                    suggested_action=(
                        "Check stderr for error details. "
                        "May be infrastructure or capability issue."
                    ),
                    confidence=0.60,
                    signals={"exit_code": signals.exit_code},
                )
            )

    if signals.cost_usd == 0 and signals.exit_code == 0:
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.INFRASTRUCTURE,
                evidence="Zero API cost with exit code 0 -- no LLM call made",
                suggested_action=(
                    "Check API key configuration and network connectivity."
                ),
                confidence=0.90,
                signals={"cost_usd": 0},
            )
        )

    # --- Rule 3: Capability failures ---
    cap_match = _match_patterns(
        signals.stderr_text, CAPABILITY_ERROR_PATTERNS
    )
    if cap_match:
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.CAPABILITY,
                evidence=f"Capability error pattern: '{cap_match}'",
                suggested_action=(
                    "Check skill prompt, tool permissions, or agent config."
                ),
                confidence=0.85,
                signals={"capability_pattern": cap_match},
            )
        )

    if signals.tool_call_count == 0 and signals.has_output:
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.CAPABILITY,
                evidence="Output produced but zero tool calls",
                suggested_action=(
                    "Agent may have fabricated response without using tools. "
                    "Check skill prompt and allowed tools configuration."
                ),
                confidence=0.75,
                signals={"tool_call_count": 0},
            )
        )

    if not signals.has_output and signals.exit_code == 0:
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.CAPABILITY,
                evidence=(
                    f"Minimal output ({signals.transcript_chars} chars) "
                    f"despite successful exit"
                ),
                suggested_action=(
                    "Agent may have hit context window limit or "
                    "max turns without producing output."
                ),
                confidence=0.70,
                signals={"transcript_chars": signals.transcript_chars},
            )
        )

    if not signals.schema_valid and signals.structured_output_present is False:
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.CAPABILITY,
                evidence="No structured output produced (schema violation)",
                suggested_action=(
                    "Check json_schema configuration and agent prompt "
                    "for structured output instructions."
                ),
                confidence=0.80,
                signals={"structured_output": False},
            )
        )

    # --- Rule 4: Ground truth suspect ---
    # Agent produced well-structured output with findings, but they
    # don't match ground truth. If the agent also used the graph and
    # produced evidence, the ground truth might be wrong.
    if (
        signals.has_output
        and signals.findings_count > 0
        and not signals.findings_match_ground_truth
        and signals.has_bskg_query
        and signals.tool_call_count >= 3
    ):
        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.GROUND_TRUTH,
                evidence=(
                    f"Agent produced {signals.findings_count} findings "
                    f"with graph queries and evidence, but none match "
                    f"ground truth ({signals.ground_truth_count} expected)"
                ),
                suggested_action=(
                    "Review ground truth: agent may have found legitimate "
                    "issues not in the expected set. Compare agent findings "
                    "against contract code manually."
                ),
                confidence=0.50,  # Low confidence -- needs human review
                signals={
                    "findings_count": signals.findings_count,
                    "ground_truth_count": signals.ground_truth_count,
                    "has_bskg_query": True,
                },
            )
        )

    # --- Rule 5: Reasoning failure (default for "ran but wrong") ---
    if (
        signals.has_output
        and signals.exit_code == 0
        and not signals.findings_match_ground_truth
    ):
        evidence_parts = []
        if not signals.has_bskg_query:
            evidence_parts.append("no BSKG queries executed")
        if signals.findings_count == 0:
            evidence_parts.append("no findings produced")
        elif not signals.findings_match_ground_truth:
            evidence_parts.append(
                f"{signals.findings_count} findings but none match ground truth"
            )

        candidates.append(
            ClassifiedFailure(
                category=FailureCategory.REASONING,
                evidence=(
                    "Output produced but incorrect: "
                    + "; ".join(evidence_parts)
                    if evidence_parts
                    else "Output did not match expected results"
                ),
                suggested_action=(
                    "Review agent reasoning chain. Check if graph-first "
                    "workflow was followed. Consider prompt improvements."
                ),
                confidence=0.60,
                signals={
                    "has_bskg_query": signals.has_bskg_query,
                    "findings_count": signals.findings_count,
                },
            )
        )

    # --- Select best candidate ---
    if not candidates:
        return ClassifiedFailure(
            category=FailureCategory.UNKNOWN,
            evidence="No classification heuristic matched",
            suggested_action="Manual triage required.",
            confidence=0.0,
        )

    # Sort by confidence descending
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    best = candidates[0]

    # Attach secondary category if available
    if len(candidates) > 1 and candidates[1].category != best.category:
        best.secondary_category = candidates[1].category

    return best


def _match_patterns(text: str, patterns: list[str]) -> str | None:
    """Check if text contains any of the given patterns. Return first match."""
    text_lower = text.lower()
    for pattern in patterns:
        if pattern.lower() in text_lower:
            return pattern
    return None
```

### Key Design Decisions

1. **Separate signal extraction from classification.** `extract_signals()` is a pure data extraction step that works with either `ClaudeCodeResult` or future `CollectedOutput`. `classify_failure()` is a pure function over signals. This makes both independently testable.

2. **Confidence scores, not binary decisions.** Every classification has a confidence score. Borderline cases (e.g., exit code != 0 without known infra patterns) get lower confidence, signaling that manual review may be needed.

3. **Secondary category.** When multiple heuristics fire, the second-best category is preserved. This helps when the primary classification is low-confidence: "probably INFRASTRUCTURE but possibly CAPABILITY."

4. **Composable rules.** Rules are evaluated independently and the best candidate wins. New rules can be added without modifying existing ones.

5. **Ground truth suspicion.** The GROUND_TRUTH category is deliberately conservative (confidence 0.50). It only triggers when the agent demonstrably did thorough work (used graph, produced findings with evidence) but findings do not match expectations. This protects against updating ground truth based on bad agent output.

6. **No LLM in the classifier.** The rule-based classifier is deterministic and fast. 3.1c can layer LLM-based classification on top for ambiguous cases.

### Test Plan

```python
# Test infrastructure failure: non-zero exit
signals = FailureSignals(exit_code=1, stderr_text="ECONNREFUSED")
result = classify_failure(signals)
assert result.category == FailureCategory.INFRASTRUCTURE
assert result.confidence >= 0.85

# Test capability failure: no tools used
signals = FailureSignals(
    exit_code=0, transcript_chars=500, tool_call_count=0
)
result = classify_failure(signals)
assert result.category == FailureCategory.CAPABILITY

# Test reasoning failure: output exists but wrong
signals = FailureSignals(
    exit_code=0, transcript_chars=5000, tool_call_count=10,
    findings_count=2, findings_match_ground_truth=False,
    ground_truth_count=1, has_bskg_query=False
)
result = classify_failure(signals)
assert result.category == FailureCategory.REASONING

# Test ground truth suspect: good work, wrong answer
signals = FailureSignals(
    exit_code=0, transcript_chars=8000, tool_call_count=15,
    findings_count=3, findings_match_ground_truth=False,
    ground_truth_count=1, has_bskg_query=True
)
result = classify_failure(signals)
assert result.category == FailureCategory.GROUND_TRUTH

# Test flaky: mixed trial results
signals = FailureSignals(trial_results=[True, False, True, False])
result = classify_failure(signals)
assert result.category == FailureCategory.FLAKY
assert result.confidence >= 0.90

# Test zero cost = infrastructure
signals = FailureSignals(exit_code=0, cost_usd=0.0)
result = classify_failure(signals)
assert result.category == FailureCategory.INFRASTRUCTURE

# Test unknown: no heuristics match (everything looks fine but still failed)
signals = FailureSignals(
    exit_code=0, cost_usd=0.05, duration_ms=30000,
    tool_call_count=5, transcript_chars=3000,
    structured_output_present=True, findings_count=1,
    findings_match_ground_truth=True  # Actually passed -- shouldn't classify
)
# This scenario should not be classified as failure at all;
# classify_failure should only be called on actual failures
```

---

## GAP-11: REVISED — Instrument First, Classify Later (2026-02-12)

The original GAP-11 resolution above designed a full classification engine upfront: `FailureCategory` enum (6 values), `FailureSignals` dataclass (13 fields), `ClassifiedFailure` dataclass, `extract_signals()`, `classify_failure()` with priority-ordered heuristics, error pattern lists, and ~250 LOC of production code plus ~200 LOC of tests.

**This was premature.** We have zero real failure data. The categories (INFRASTRUCTURE, CAPABILITY, REASONING, GROUND_TRUTH, FLAKY, UNKNOWN) are hypothetical. The signal weights and confidence thresholds are guesses. Building this before running real scenarios means building classification infrastructure for failure modes we have not yet observed.

### What We Did Instead

Added a single field to `ClaudeCodeResult` (the existing output dataclass):

```python
failure_notes: str = ""  # Evaluator fills this in. Free-text classification of why a scenario failed.

@property
def failed(self) -> bool:
    return bool(self.failure_notes)
```

**Total: 4 lines of code.** Located in `src/alphaswarm_sol/testing/harness/runner.py`.

### How This Works

1. After a scenario run, the evaluator (Claude Code in 3.1c) inspects the result
2. If the scenario failed, the evaluator writes a free-text note explaining why: `result.failure_notes = "CLI crashed with ECONNREFUSED — API key not configured"`
3. These notes accumulate across scenario runs in `.vrs/debug/` artifacts
4. After enough real failures, patterns emerge: "80% of notes mention infrastructure errors" or "most reasoning failures cite missing graph queries"
5. THEN we build a classifier from observed reality, not hypothetical categories

### Why This Is Better

- **Zero speculative code** — no enums, dataclasses, or heuristics for failure modes we haven't seen
- **Backward compatible** — `failure_notes` defaults to empty string; existing code unaffected
- **The evaluator IS the classifier** — Claude Code already reasons about failures in natural language during evaluation; we just capture that reasoning
- **Classification emerges from data** — when we have 50+ failure notes, the right categories will be obvious
- **Moves to `CollectedOutput` later** — when 3.1b-02 builds the OutputCollector, `failure_notes` migrates there naturally

### What Happens to the Original Design

The original GAP-11 classification model (above) is preserved as a **reference design** for when real data justifies building it. The categories may change; the confidence thresholds will be calibrated from actual failure distributions; the error pattern lists will be populated from real stderr output.

---

## Cross-Gap Dependencies

### Dependency Graph

```
GAP-05 (Orchestration Scenario)
  ├── DEPENDS ON GAP-01 (TeamObservation) -- needs team-level ground truth evaluation
  ├── DEPENDS ON GAP-10 (Workflow Taxonomy) -- scenario uses workflow_category: orchestration
  ├── DEPENDS ON GAP-09 (Escalation) -- scenario includes escalation_rules
  └── FEEDS INTO GAP-11 (Failure Classification) -- orchestration failures need team-aware classification

GAP-09 (Adaptive Escalation)
  ├── DEPENDS ON GAP-02 (BSKG Extraction) -- condition "no_bskg_queries" needs parser extension
  ├── EXTENDS 3.1b-05 (Scenario DSL) -- adds escalation_rules schema
  └── FEEDS INTO GAP-05 (Orchestration Scenario) -- scenario uses escalation rules

GAP-10 (Workflow Taxonomy)
  ├── STANDALONE -- no hard dependencies on other gaps
  ├── FEEDS INTO GAP-05 -- scenario references workflow_category
  ├── FEEDS INTO 3.1c-06 (Evaluation Contracts) -- smart selection matrix
  └── ALIGNS WITH registry.yaml categories -- but reorganized for evaluation

GAP-11 (Failure Classification) -- REVISED: instrument-first approach
  ├── IMPLEMENTED as failure_notes field on ClaudeCodeResult (4 LOC)
  ├── MOVES TO CollectedOutput when 3.1b-02 builds OutputCollector
  └── CLASSIFIER built later from accumulated failure_notes data
```

### GAP-01 Interaction

The orchestration scenario (GAP-05) CANNOT be fully evaluated without `TeamObservation` from GAP-01. However, the scenario can still be defined, loaded, and executed without it. The team behavior ground truth fields become the specification for what `TeamObservation` must provide.

**Recommended approach:** Define the scenario now (GAP-05), implement `TeamObservation` in 3.1b-02/3.1b-04 (GAP-01), then connect them in 3.1b-07 smoke test.

### GAP-02 Interaction

Escalation condition `no_bskg_queries` (GAP-09) requires `TranscriptParser.has_bskg_query()` which already exists. The richer `no_bskg_queries` + `graph_citation_rate` conditions require `get_bskg_queries()` from GAP-02. Since GAP-09 escalation is parsed in 3.1b but executed in 3.1c, the GAP-02 dependency is on 3.1c, not 3.1b.

---

## Integration Plan

| Gap | Target 3.1b Plan | What Gets Added | When |
|---|---|---|---|
| **GAP-05** | 3.1b-06 (Corpus) | Orchestration scenario directory + YAML + contracts | Wave 1 (with corpus) |
| **GAP-09** | 3.1b-05 (DSL) | `escalation_rules` schema field in EvaluationGuidance | Wave 2 (with DSL) |
| **GAP-10** | 3.1b-06 (Corpus) | `workflow-categories.yaml` in guidelines/ | Wave 1 (with corpus) |
| **GAP-11** | DONE (on ClaudeCodeResult) | `failure_notes: str` field + `failed` property (4 LOC) | COMPLETE — classifier deferred until data exists |

### Specific Integration Steps

**3.1b-02 (TranscriptParser + OutputCollector):**
- When `CollectedOutput` is built, add `failure_notes: str = ""` field (migrate from `ClaudeCodeResult`)
- The evaluator fills `failure_notes` in natural language during evaluation
- Classification infrastructure built later from accumulated failure data (see REVISED section above)

**3.1b-05 (Scenario DSL):**
- Add `escalation_rules` as optional field in `EvaluationGuidance` dataclass
- Add YAML parsing for `escalation_rules` in ScenarioLoader
- Validate condition IDs against known vocabulary at load time
- Schema validation rejects unknown action types

**3.1b-06 (Test Corpus):**
- Add orchestration scenario directory at `examples/testing/scenarios/orchestration/multi-agent-reentrancy-debate/`
- Write `LendingVault.sol` and `SafeLendingVault.sol` as novel test contracts
- Add `workflow-categories.yaml` at `examples/testing/guidelines/`
- Reference workflow_category in all 10+ scenario YAML files

---

## Implementation Estimates

| Gap | Effort | Rationale |
|---|---|---|
| **GAP-05** | **Medium** | Scenario YAML is defined above. Novel contracts need writing and compilation testing. Ground truth needs both vulnerability and team behavior fields. Contracts are ~60 LOC each. |
| **GAP-09** | **Small** | Schema extension only. 5 escalation rules are defined. Parsing is straightforward YAML->dataclass. No execution logic in 3.1b. ~100 LOC. |
| **GAP-10** | **Small** | YAML file is fully defined above. Copy and validate. Adjust scenario files to include `workflow_category`. ~50 LOC of validation code. |
| **GAP-11** | **Done** | REVISED: 4 LOC (`failure_notes` field + `failed` property on `ClaudeCodeResult`). Classification deferred until real data exists. |

**Total estimate:** ~700 LOC across all four gaps, split roughly:
- 250 LOC for failure classification (GAP-11)
- 200 LOC for scenario YAML + contracts (GAP-05)
- 100 LOC for escalation schema (GAP-09)
- 50 LOC for taxonomy validation (GAP-10)
- 200 LOC for tests across all four

---

*Resolution based on: examination of `src/alphaswarm_sol/agents/catalog.yaml` (24 agents, 71 LOC relevant), `src/alphaswarm_sol/skills/registry.yaml` (44 skills with categories), `src/alphaswarm_sol/testing/harness/` (runner.py, scenario_loader.py, output_parser.py -- 700+ LOC), `src/alphaswarm_sol/testing/trajectory/evaluator.py` (300 LOC), `tests/workflow_harness/lib/workspace.py` (222 LOC), shipping agent definitions (vrs-attacker.md, vrs-verifier.md), and the gap improvement plan.*
