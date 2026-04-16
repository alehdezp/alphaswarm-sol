# Economic Agent Contracts Reference

**Version:** 1.0.0
**Phase:** 05.11 Economic Context + Agentic Workflow Integrity
**Last Updated:** 2026-01-27

## Overview

Economic Agent Contracts define the required outputs and validation rules for agents
reasoning about smart contract vulnerabilities. They enforce game-theoretic awareness,
causal reasoning, and evidence-backed citations.

## Contract Requirements

All agents must meet these requirements when producing findings:

### 1. Lens Tags (Required)

Every finding must be tagged with at least one economic reasoning lens:

| Lens | Focus | Examples |
|------|-------|----------|
| `VALUE` | Value flow analysis | deposits, withdrawals, custody, transfers |
| `CONTROL` | Access control | who can pause, upgrade, change params |
| `INCENTIVE` | Profit motivation | who gains from breaking invariants |
| `TRUST` | Off-chain inputs | oracles, keepers, relayers, admins |
| `TIMING` | Temporal windows | delays, auctions, timelocks, front-running |
| `CONFIG` | Configuration issues | mis-set params, wrong role assignments |

**Example:**
```yaml
finding:
  description: "Oracle price manipulation enables profitable liquidation"
  lens_tags:
    - value     # Value extraction
    - trust     # Oracle dependency
    - timing    # Front-running window
```

### 2. Causal Chain (Required for HIGH/CRITICAL)

Findings rated HIGH or CRITICAL must include a complete causal chain showing the
exploitation path from root cause to financial loss:

```yaml
causal_chain:
  - step_type: root_cause
    description: "Oracle price not validated for staleness"
    evidence_refs: ["EVD-12345678"]
    probability: 1.0
    node_id: "func_Vault_liquidate_abc123"

  - step_type: exploit
    description: "Attacker front-runs oracle update with stale price"
    probability: 0.8

  - step_type: amplifier   # Optional
    description: "Flash loan magnifies extractable value"
    probability: 0.9

  - step_type: loss
    description: "$500,000 extracted from vault reserves"
    probability: 1.0
```

**Chain Validity Rules:**
- Must have at least one `root_cause`, one `exploit`, and one `loss`
- Chain probability (product of all steps) must be >= 0.1
- Each step should include `evidence_refs` where available

### 3. Counterfactual Scenarios (Required: 2+)

Each finding must explore at least 2 "what if" scenarios to evaluate mitigations:

```yaml
counterfactuals:
  - scenario_type: guard_exists
    description: "What if a staleness check was present?"
    would_prevent: true
    impact: "Attack blocked at oracle read - price rejected as stale"
    evidence_refs: ["EVD-87654321"]

  - scenario_type: param_different
    description: "What if heartbeat timeout was 10 minutes?"
    would_prevent: false
    impact: "Window reduced but MEV bots could still exploit"

  - scenario_type: invariant_enforced
    description: "What if price deviation > 5% triggered pause?"
    would_prevent: true
    impact: "Anomaly detection would halt before loss"
```

**Scenario Types:**
- `guard_exists` - A protective guard or check is present
- `param_different` - A configuration parameter has a different value
- `role_change` - A role or permission is different
- `timing_change` - A delay or timelock is different
- `invariant_enforced` - An invariant check is enforced

### 4. Provenance (Required on Assumptions)

All cited assumptions must include source attribution with dates:

```yaml
assumptions:
  - description: "Admin is a trusted 3-of-5 multisig"
    source_date: "2025-01-15"
    source_id: "governance-doc-v2"
    source_type: "governance"
    provenance: "declared"

  - description: "Oracle price updates within 1 hour"
    source_date: "2025-01-10"
    source_id: "chainlink-docs"
    source_type: "docs"
    provenance: "declared"
```

**Provenance Types:**
- `declared` - Explicit in official docs/governance (can trigger findings)
- `inferred` - Deduced from code patterns (can trigger warnings)
- `hypothesis` - Unconfirmed guess (triggers probes only)

### 5. Cross-Protocol Awareness (Recommended)

When external protocol dependencies exist, note them explicitly:

```yaml
cross_protocol_dependencies:
  - protocol: "Chainlink ETH/USD"
    dependency_type: "oracle"
    criticality: 9
    failure_impact: "Stale prices enable liquidation arbitrage"

  - protocol: "Aave V3"
    dependency_type: "liquidity"
    criticality: 7
    failure_impact: "Flash loan source - attack capital"

systemic_risk_mentioned: true
```

## Role-Specific Contracts

### Attacker Contract

Attacker agents focus on constructing exploit paths:

- **Primary Lenses:** VALUE, INCENTIVE, TIMING
- **Requires:** Causal chain, counterfactuals
- **Input:** Dossier, passport, attack EV

```python
contract = EconomicPromptContract.for_attacker(
    dossier_summary="AMM protocol with $50M TVL...",
    passport_snippet="Vault.sol handles ETH custody...",
    policy_diff="Expected: onlyOwner on upgrade, Actual: no modifier",
    attack_ev=PayoffMatrix(scenario="oracle_manipulation", ...),
)
```

### Defender Contract

Defender agents focus on identifying protections:

- **Primary Lenses:** CONTROL, CONFIG
- **Requires:** Counterfactuals (what guards would help)
- **Input:** Dossier, passport, policy diff

```python
contract = EconomicPromptContract.for_defender(
    dossier_summary="AMM protocol with $50M TVL...",
    passport_snippet="Vault.sol handles ETH custody...",
    policy_diff="Expected: onlyOwner on upgrade, Actual: no modifier",
)
```

### Verifier Contract

Verifier agents focus on cross-checking evidence:

- **Primary Lenses:** All (validates others' claims)
- **Requires:** Causal chain validation, counterfactual review
- **Input:** Dossier, passport, attack EV

```python
contract = EconomicPromptContract.for_verifier(
    dossier_summary="AMM protocol with $50M TVL...",
    passport_snippet="Vault.sol handles ETH custody...",
    attack_ev=PayoffMatrix(scenario="oracle_manipulation", ...),
)
```

## Validation

Use `PromptValidator` to validate agent outputs:

```python
from alphaswarm_sol.agents.prompts import PromptValidator, ValidationResult

validator = PromptValidator()
result: ValidationResult = validator.validate(agent_output)

if not result.valid:
    for failure in result.failures:
        print(f"VALIDATION FAILURE: {failure}")

if result.warnings:
    for warning in result.warnings:
        print(f"WARNING: {warning}")

# Check specific validations
print(f"Lens tags found: {[t.value for t in result.lens_tags_found]}")
print(f"Causal chain valid: {result.causal_chain_valid}")
print(f"Counterfactuals: {result.counterfactual_count}")
```

## Output Schema

Complete finding output should follow this structure:

```yaml
finding:
  # Core fields
  id: "FIND-001"
  description: "Oracle price manipulation..."
  severity: "high"

  # Required: Lens tags
  lens_tags:
    - value
    - trust

  # Required for HIGH/CRITICAL: Causal chain
  causal_chain:
    - step_type: root_cause
      description: "..."
      evidence_refs: ["EVD-..."]
      probability: 1.0
    - step_type: exploit
      description: "..."
      probability: 0.8
    - step_type: loss
      description: "..."
      probability: 1.0

  # Required: Counterfactuals (min 2)
  counterfactuals:
    - scenario_type: guard_exists
      description: "..."
      would_prevent: true
      impact: "..."
    - scenario_type: param_different
      description: "..."
      would_prevent: false
      impact: "..."

  # Required on cited assumptions
  assumptions:
    - description: "..."
      source_date: "2025-01-15"
      source_id: "..."
      provenance: "declared"

  # Recommended
  cross_protocol_dependencies:
    - protocol: "Chainlink"
      dependency_type: "oracle"
      criticality: 9
```

## Integration Points

Economic prompt contracts integrate with:

1. **Context Linker** (05.11-02): Provides passport and policy diff
2. **Economics Module** (05.11-01): Provides PayoffMatrix for attack EV
3. **Routing** (05.11-02): Attaches economic context to agent contexts
4. **Skills** (05.11-05): Skills invoke prompt contracts for reasoning

## Failure Modes

### Validation Failures (Block Finding)

| Failure | Cause | Resolution |
|---------|-------|------------|
| No lens tags | Finding lacks economic reasoning lens | Add appropriate lens tag |
| Incomplete causal chain | Missing root_cause/exploit/loss | Complete the chain |
| Low chain probability | Product < 0.1 | Review step probabilities |
| Missing provenance | Assumption lacks source_date | Add source attribution |

### Validation Warnings (Non-Blocking)

| Warning | Cause | Recommendation |
|---------|-------|----------------|
| Insufficient counterfactuals | < 2 scenarios | Add more "what if" analysis |
| No cross-protocol mention | Missing dependency awareness | Note external deps |
| Incomplete causal chain (MEDIUM) | Non-critical missing chain | Consider adding for completeness |

## Best Practices

1. **Start with lenses** - Tag the economic reasoning type before writing
2. **Build chains forward** - root_cause -> exploit -> loss
3. **Explore both sides** - Include counterfactuals that would AND would not prevent
4. **Date everything** - All assumptions need provenance dates
5. **Note dependencies** - External protocols increase systemic risk
6. **Probability calibration** - Use realistic probabilities (0.7-0.9 for likely, 0.1-0.3 for unlikely)

## Related Documentation

- [Economic Context Overlay](./economic-context-overlay.md) - Schema 1.1 reference
- [Contract Passport](./contract-passport.md) - Per-contract economic summary
- [Pattern Context Pack v2](./pattern-context-pack-v2.md) - Pattern detection context

---

*Economic Agent Contracts - Part of AlphaSwarm.sol Phase 5.11*
*Created: 2026-01-27*
