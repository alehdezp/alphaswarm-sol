# Workflow Integrity Gates Specification

**Phase:** 5.11-03
**Status:** Normative Reference
**Last Updated:** 2026-01-27

## Overview

Workflow integrity gates enforce evidence-first reasoning and prevent false certainty
in the VRS multi-agent workflow. Gates block confidence upgrades when evidence,
provenance, causal chains, or economic context is incomplete.

## Integrity Gates

### 1. Evidence Gate

**Rule:** No confidence upgrade without `evidence_refs`

**Location:** `src/alphaswarm_sol/llm/confidence.py::evidence_gate()`

**Behavior:**
- Findings without `evidence_refs` cannot upgrade to LIKELY or CONFIRMED
- Falls back to behavioral evidence (`behavioral_signature`, `operations`)
- Blocks upgrade if neither evidence source is present

**Example:**
```python
from alphaswarm_sol.llm.confidence import evidence_gate

# Finding without evidence - blocked
if not evidence_gate(finding):
    # Downgrade to UNCERTAIN
    verdict.confidence = VerdictConfidence.UNCERTAIN
```

**When it fires:**
- Finding has empty `evidence.evidence_refs` list
- Finding lacks `behavioral_signature` and `operations`

### 2. Provenance Gate

**Rule:** Only DECLARED expectations trigger misconfig findings

**Location:** `src/alphaswarm_sol/llm/confidence.py::provenance_gate()`

**Behavior:**
- Misconfiguration findings require DECLARED provenance
- INFERRED expectations emit warnings only (no finding)
- HYPOTHESIS expectations trigger probes, not findings

**Provenance Types:**

| Type | Can Trigger Finding | Action |
|------|---------------------|--------|
| DECLARED | Yes | Create finding |
| INFERRED | No | Emit warning only |
| HYPOTHESIS | No | Trigger probe task |

**Example:**
```python
from alphaswarm_sol.llm.confidence import (
    provenance_gate,
    ExpectationProvenance,
    ExpectationEvidence,
)

evidence = ExpectationEvidence(
    source_id="protocol-docs-v2",
    source_date="2026-01-15",
    source_type="docs",
    provenance=ExpectationProvenance.DECLARED,
)

passes, warning = provenance_gate(finding, evidence, is_misconfig_finding=True)
# passes=True for DECLARED, False for INFERRED/HYPOTHESIS
```

**When it fires:**
- Misconfig finding has INFERRED provenance
- Misconfig finding has HYPOTHESIS provenance
- Misconfig finding has no expectation evidence

### 3. Causal Chain Gate

**Rule:** Complete causal chain required for confidence upgrade

**Location:** `src/alphaswarm_sol/llm/confidence.py::validate_causal_chain()`

**Behavior:**
- Requires: root_cause -> exploit_steps -> financial_loss chain
- Missing links create gap nodes
- Chain probability must be > 0.1 for viability
- Incomplete chains block LIKELY/CONFIRMED upgrades

**Required Chain Links:**

| Link Type | Description | Required |
|-----------|-------------|----------|
| ROOT_CAUSE | Underlying vulnerability | Yes |
| EXPLOIT_STEP | Steps to exploit (1+) | Yes |
| FINANCIAL_LOSS | Resulting financial impact | Yes |
| COUNTERFACTUAL | Mitigation (optional) | No |

**Example:**
```python
from alphaswarm_sol.llm.confidence import validate_causal_chain

chain_data = {
    "root_cause": {
        "id": "missing-access-control",
        "probability": 0.9,
        "evidence_refs": ["audit-finding-42"],
    },
    "exploit_steps": [
        {
            "source_id": "missing-access-control",
            "target_id": "unauthorized-withdrawal",
            "probability": 0.8,
        }
    ],
    "financial_loss": {
        "source_id": "unauthorized-withdrawal",
        "target_id": "vault-drain",
        "probability": 0.95,
    },
}

result = validate_causal_chain("vuln-001", chain_data)
if result.allows_confidence_upgrade():
    # Chain is complete and viable
    pass
else:
    # Create gap nodes
    for gap_id in result.gap_nodes_needed:
        create_gap_node(gap_id)
```

**When it fires:**
- Missing root_cause attribution
- No exploit steps defined
- No financial_loss link
- Chain probability < 0.1

### 4. Stale Context Gate

**Rule:** Stale context forces unknown state

**Location:** `src/alphaswarm_sol/llm/confidence.py::stale_context_gate()`

**Behavior:**
- Context older than `max_age_days` (default 90) is stale
- Stale context forces UNKNOWN confidence
- Triggers context expansion or human review

**Example:**
```python
from alphaswarm_sol.llm.confidence import stale_context_gate

is_fresh, message = stale_context_gate(
    context_last_verified="2025-06-01T00:00:00Z",
    max_age_days=90
)
# is_fresh=False if > 90 days old
```

### 5. Economic Rationality Gate

**Rule:** EV > 0 required for prioritization

**Location:** `src/alphaswarm_sol/economics/rationality_gate.py::RationalityGate`

**Behavior:**
- Computes expected value: EV = P(success) * profit - gas - mev_risk
- EV < 0: Deprioritize (not hide) - economically irrational
- EV > escalation_threshold: Critical priority
- All filtered vulnerabilities logged for transparency

**Thresholds:**

| Threshold | Default | Meaning |
|-----------|---------|---------|
| filter_threshold | 0 USD | Below = deprioritize |
| escalation_threshold | 30,000 USD | Above = critical |

**Priority Buckets:**

| EV Range | Priority Bucket |
|----------|-----------------|
| < 0 | deprioritized |
| 0 - 9,000 | low/medium |
| 9,000 - 30,000 | high |
| > 30,000 | critical |

**Example:**
```python
from alphaswarm_sol.economics import (
    RationalityGate,
    filter_by_economic_rationality,
)

gate = RationalityGate()
result = gate.evaluate_attack_ev(vulnerability, protocol_state)

if result.is_economically_rational:
    prioritize(vulnerability)
else:
    # Still include, just lower priority
    deprioritize(vulnerability)

# Batch filter
rational, deprioritized = filter_by_economic_rationality(vulns, protocol_state)
```

### 6. Unknown Gate (ORCH-10)

**Rule:** Missing context defaults to unknown state

**Location:** `src/alphaswarm_sol/orchestration/confidence.py::ConfidenceEnforcer`

**Behavior:**
- Missing economic context -> UNCERTAIN
- Missing protocol context -> UNCERTAIN
- Conflicting evidence -> UNCERTAIN
- Unknown always requires human_flag=True

### 7. Omission Gate

**Rule:** Cut set in omission ledger requires context expansion

**Location:** `src/alphaswarm_sol/knowledge/domain_kg.py::OmissionLedger`

**Behavior:**
- Gap nodes track missing context
- Open gaps block confidence upgrades for related entities
- Gaps must be resolved or escalated to human review

**Gap Node Types:**

| Type | Description |
|------|-------------|
| MISSING_CONTEXT | Missing economic/protocol context |
| INCOMPLETE_CAUSAL | Incomplete causal chain |
| STALE_FACT | Expired TTL on fact |
| CONFLICTING_EVIDENCE | Conflicting sources |
| MISSING_EXPECTATION | No declared expectation |
| UNKNOWN_CONTROL | Unknown access control policy |
| AMBIGUOUS_INVARIANT | Unclear invariant |

### 8. Human Escalation Gate

**Rule:** Repeated unknowns trigger human review

**Behavior:**
- 3+ UNCERTAIN verdicts for same pattern -> escalate
- All debate outcomes -> human_flag=True
- All high-severity findings -> human_flag=True

## Gate Execution Order

Gates are applied in this order during verdict collection:

1. **Evidence Gate** - Block if no evidence_refs
2. **Causal Chain Gate** - Block if incomplete chain
3. **Provenance Gate** - Block misconfig if not DECLARED
4. **Stale Context Gate** - Force unknown if stale
5. **Rationality Gate** - Deprioritize if EV < 0
6. **Omission Gate** - Check for open gaps
7. **Human Escalation** - Set human_flag

## Gap Graph

The gap graph is an overlay on the domain knowledge graph that tracks missing
context. Gap nodes are created when gates detect missing information.

### Gap Node Lifecycle

```
OPEN -> EXPANDING -> RESOLVED
  |         |
  +-> HUMAN_REVIEW -> RESOLVED
            |
            +-> DISMISSED
```

### Creating Gap Nodes

```python
from alphaswarm_sol.knowledge.domain_kg import (
    OmissionLedger,
    GapNodeType,
    CausalGapNode,
)

ledger = OmissionLedger()

# Create general gap
gap = ledger.create_gap(
    gap_type=GapNodeType.MISSING_CONTEXT,
    related_entity_id="fn:Vault.withdraw",
    description="Missing economic context for value flow",
    expansion_hints=["Add protocol context pack", "Query on-chain TVL"],
)

# Create causal gap
causal_gap = ledger.create_causal_gap(
    vulnerability_id="vuln-001",
    missing_link_types=["root_cause", "financial_loss"],
    current_probability=0.0,
)

# Resolve gap
ledger.resolve_gap(gap.id, "Added context pack v2")
```

## Examples

### Example 1: Declared vs Inferred Expectations

**Declared (can trigger finding):**
```python
evidence = ExpectationEvidence(
    source_id="aave-docs-governance-v3",
    source_date="2026-01-01",
    source_type="docs",
    provenance=ExpectationProvenance.DECLARED,
)
# Finding: "Guardian role should have 48h timelock"
```

**Inferred (warning only):**
```python
evidence = ExpectationEvidence(
    source_id="pattern-analysis",
    source_date="2026-01-15",
    source_type="heuristic",
    provenance=ExpectationProvenance.INFERRED,
)
# Warning: "Based on common patterns, timelock expected"
# No finding generated
```

**Hypothesis (probe only):**
```python
evidence = ExpectationEvidence(
    source_id="researcher-speculation",
    source_date="2026-01-15",
    source_type="hypothesis",
    provenance=ExpectationProvenance.HYPOTHESIS,
)
# Probe task: "Verify if timelock is intended"
# No finding generated
```

### Example 2: Complete vs Incomplete Causal Chain

**Complete chain (allows upgrade):**
```yaml
root_cause:
  id: missing-reentrancy-guard
  probability: 0.9
  evidence_refs: [audit-001]

exploit_steps:
  - source_id: missing-reentrancy-guard
    target_id: reenter-withdraw
    probability: 0.8

financial_loss:
  source_id: reenter-withdraw
  target_id: vault-drain
  probability: 0.95

# Chain probability: 0.9 * 0.8 * 0.95 = 0.684 > 0.1 (viable)
```

**Incomplete chain (blocked):**
```yaml
root_cause:
  id: unknown
  probability: 0.0
  evidence_refs: []

# Missing exploit_steps
# Missing financial_loss

# Creates gap nodes:
# - gap:vuln-001:root_cause
# - gap:vuln-001:exploit_step
# - gap:vuln-001:financial_loss
```

### Example 3: Positive vs Negative EV

**Positive EV (prioritized):**
```python
vulnerability = {
    "id": "oracle-manipulation",
    "potential_profit_usd": 500000,
    "gas_cost_usd": 100,
    "success_probability": 0.7,
    "mev_risk": 0.2,
}
# EV = 0.7 * 500000 - 100 - (500000 * 0.2 * 0.5) = 299,900
# Priority: critical
```

**Negative EV (deprioritized):**
```python
vulnerability = {
    "id": "low-value-bug",
    "potential_profit_usd": 50,
    "gas_cost_usd": 200,
    "success_probability": 0.3,
    "mev_risk": 0.5,
}
# EV = 0.3 * 50 - 200 - (50 * 0.5 * 0.5) = -197.5
# Priority: deprioritized (still reported, just lower priority)
```

## Integration Points

### Handlers Integration

Gates are integrated into `CollectVerdictsHandler`:

```python
# src/alphaswarm_sol/orchestration/handlers.py

class CollectVerdictsHandler(BaseHandler):
    def __call__(self, pool, target_beads=None):
        # Apply gates before confidence upgrade
        if not evidence_gate(finding):
            confidence = VerdictConfidence.UNCERTAIN

        chain_result = validate_causal_chain(bead_id, chain_data)
        if not chain_result.allows_confidence_upgrade():
            confidence = VerdictConfidence.UNCERTAIN
            # Create gap nodes

        if is_misconfig and not provenance_gate(finding, evidence, True)[0]:
            confidence = VerdictConfidence.UNCERTAIN
```

### Pool Metadata

Gate failures are tracked in pool metadata:

```python
pool.metadata["integrity_gates"] = {
    "failures": [
        {"bead_id": "...", "gate": "evidence", "action": "downgrade"},
        {"bead_id": "...", "gate": "causal_chain", "gap_nodes": [...]},
    ],
    "gap_nodes_created": ["gap:vuln-001:root_cause", ...],
    "total_failures": 5,
}
```

## References

- Phase 5.11 Context: `.planning/phases/05.11-economic-context-agentic-workflow-integrity/05.11-CONTEXT.md`
- Evidence Gate: `src/alphaswarm_sol/llm/confidence.py`
- Rationality Gate: `src/alphaswarm_sol/economics/rationality_gate.py`
- Gap Graph: `src/alphaswarm_sol/knowledge/domain_kg.py`
- Handlers: `src/alphaswarm_sol/orchestration/handlers.py`
- Confidence Enforcer: `src/alphaswarm_sol/orchestration/confidence.py`

---

*Workflow Integrity Gates Specification*
*Phase 5.11-03: Economic Context + Agentic Workflow Integrity*
