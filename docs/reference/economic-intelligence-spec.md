# Economic Intelligence (EI) and Context Trust Level (CTL) Specification

**Status:** CANONICAL
**Created:** 2026-02-04
**Purpose:** Define EI outputs and CTL gating for Tier C patterns (IMP-A4)

---

## Overview

Economic Intelligence (EI) and Context Trust Level (CTL) are gating mechanisms that control when high-context vulnerability patterns (Tier C) can execute. Without proper economic context, Tier C patterns may produce false positives or miss protocol-specific vulnerabilities.

---

## Economic Intelligence (EI)

### Definition

Economic Intelligence is the structured analysis of a protocol's economic model that enables detection of economically-motivated attacks. EI answers: "How could an attacker profit from exploiting this protocol?"

### Trigger Conditions

EI runs when:
1. Target contract has value-handling functions (`TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`)
2. Target is identified as DeFi protocol (lending, DEX, oracle, vault, etc.)
3. Tier C patterns are in scope
4. `--with-economic-context` flag is set (default: true)

### Required Outputs

EI MUST produce the following artifacts:

```yaml
economic_context:
  # 1. Actor Analysis
  actors:
    - role: "depositor"
      actions: ["deposit", "withdraw"]
      assets: ["ETH", "USDC"]
    - role: "liquidator"
      actions: ["liquidate"]
      incentive: "liquidation_bonus"
    - role: "oracle"
      actions: ["update_price"]
      trust_level: "external"

  # 2. Asset Flows
  flows:
    - source: "depositor"
      destination: "pool"
      asset: "collateral"
      trigger: "deposit()"
    - source: "pool"
      destination: "borrower"
      asset: "borrowed_asset"
      trigger: "borrow()"

  # 3. Attack Profitability Analysis
  attack_scenarios:
    - name: "price_manipulation"
      cost_estimate: "flash_loan_fee + gas"
      profit_potential: "pool_tvl * price_delta"
      profitable_if: "profit_potential > cost_estimate"
      numeric_threshold: "> $1000 profit"

  # 4. Incentive Alignment
  incentive_analysis:
    aligned:
      - "Liquidators profit from maintaining solvency"
    misaligned:
      - "Oracle update has no penalty for manipulation"
    neutral:
      - "Depositor incentive depends on yield"
```

### Output File

EI produces: `.vrs/context/economic-context.json`

### Verification Method

EI ran successfully if:
```python
def verify_ei_complete(context_path: str) -> bool:
    with open(context_path) as f:
        ctx = json.load(f)

    return all([
        len(ctx.get('actors', [])) >= 2,          # At least 2 actors
        len(ctx.get('flows', [])) >= 1,           # At least 1 flow
        'attack_scenarios' in ctx,                 # Attack analysis present
        'profitable_if' in str(ctx),              # Profitability reasoning
        'incentive_analysis' in ctx,               # Incentive analysis present
    ])
```

### Quality Levels

| Level | Criteria | Tier C Impact |
|-------|----------|---------------|
| **complete** | All 4 outputs with concrete numbers/reasoning | Full Tier C execution |
| **partial** | Actors + flows present; profitability vague | Low-risk Tier C only |
| **absent** | No economic analysis | Tier C blocked |

---

## Context Trust Level (CTL)

### Definition

Context Trust Level indicates the reliability of protocol context used for analysis. Higher trust enables more confident Tier C pattern execution.

### Trust Levels

| Level | Definition | Source Requirements | Tier C Permission |
|-------|------------|---------------------|-------------------|
| **high** | Official docs + externally verified | Official documentation, audit reports, verified on-chain data | Full Tier C |
| **medium** | Official docs, not independently verified | Official documentation only | Partial Tier C |
| **low** | Inferred from code only | No external documentation | Tier C blocked |
| **simulated** | Fabricated for testing | Test-only context | Tier C blocked (requires bypass marker) |

### CTL Determination

```python
def determine_ctl(context: dict) -> str:
    sources = context.get('sources', [])

    has_official = any(s['type'] == 'official_docs' for s in sources)
    has_audit = any(s['type'] == 'audit_report' for s in sources)
    has_verified = any(s['verified'] for s in sources)

    if has_official and (has_audit or has_verified):
        return 'high'
    elif has_official:
        return 'medium'
    elif sources:
        return 'low'
    else:
        return 'simulated'
```

### CTL in Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      Context Loading                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Load context pack                                           │
│  2. Determine CTL based on sources                              │
│  3. Emit marker: [CONTEXT_READY protocol={name} ctl={level}]    │
│  4. If CTL = low|simulated:                                     │
│     - Emit: [TIER_C_BLOCKED reason=insufficient_context]        │
│     - Skip Tier C patterns                                      │
│  5. If CTL = medium:                                            │
│     - Enable low-risk Tier C only                               │
│  6. If CTL = high:                                              │
│     - Enable all Tier C patterns                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Gate Conditions (Boolean)

| Condition | Expression | Outcome |
|-----------|------------|---------|
| Full Tier C | `ctl == 'high' AND ei_quality == 'complete'` | PASS |
| Partial Tier C | `ctl == 'medium' AND ei_quality >= 'partial'` | PASS (limited) |
| Blocked | `ctl in ['low', 'simulated'] OR ei_quality == 'absent'` | FAIL |
| Bypass (test only) | `[CONTEXT_SIMULATED_BYPASS reason={reason}]` | PASS (test) |

### Pass/Fail Outcomes

**PASS (Full Tier C):**
- All Tier C patterns execute
- Economic context informs severity scoring
- Attack profitability included in reports

**PASS (Partial Tier C):**
- Low-risk Tier C patterns only (no economic exploitation patterns)
- Warning in report: "Limited economic context"
- Recommendation to provide full context

**FAIL (Blocked):**
- Tier C patterns skipped
- Marker emitted: `[TIER_C_BLOCKED reason={reason}]`
- Report notes: "Tier C analysis unavailable due to {reason}"

---

## Required Context Fields

For Tier C execution, these fields must be present:

| Field | Description | Measurement |
|-------|-------------|-------------|
| `protocol_type` | Protocol category (lending, DEX, etc.) | String, non-empty |
| `trust_boundaries` | Trust assumptions between components | List, >=1 item |
| `asset_types` | Types of assets handled | List, >=1 item |
| `upgradeability` | Upgrade mechanism if any | Object with `type` field |
| `economic_model` | Core economic mechanics | Object with `actors`, `flows` |

### Field Presence Check

```python
def check_tier_c_fields(context: dict) -> tuple[int, list[str]]:
    required = ['protocol_type', 'trust_boundaries', 'asset_types',
                'upgradeability', 'economic_model']
    missing = [f for f in required if f not in context or not context[f]]
    return len(required) - len(missing), missing
```

---

## Simulated Context Bypass

For testing purposes, simulated context can bypass CTL checks.

### Bypass Marker

```
[CONTEXT_SIMULATED_BYPASS reason=testing_tier_c_patterns]
```

### Allowed Bypass Reasons

| Reason | When Allowed |
|--------|--------------|
| `testing_tier_c_patterns` | Unit testing Tier C pattern logic |
| `synthetic_scenario` | Synthetic test environment |
| `regression_test` | Regression testing with known outcomes |

### Anti-Production Rule

- Bypass markers MUST NOT appear in production runs
- CI should fail if bypass marker appears outside `tests/` scope

---

## Integration with Workflow

### Context Workflow Contract

**Inputs:**
- Target contracts path
- Optional: external context file

**Outputs:**
- `.vrs/context/economic-context.json`
- `.vrs/context/protocol-context.json`
- CTL determination

**Success Criteria (Observable):**
- `[CONTEXT_READY ...]` marker in transcript
- Context files exist and are valid JSON
- CTL field populated

**Failure Criteria:**
- `[CONTEXT_INCOMPLETE ...]` marker
- Missing required fields
- Invalid JSON output

---

## Example Test Assertions

Based on these definitions, tests can assert:

```python
# Test: EI produces required outputs
def test_ei_outputs():
    run_audit("contracts/Vault.sol")
    ctx = load_json(".vrs/context/economic-context.json")
    assert len(ctx['actors']) >= 2
    assert len(ctx['flows']) >= 1
    assert 'profitable_if' in str(ctx['attack_scenarios'])

# Test: CTL gates Tier C correctly
def test_ctl_gates_tier_c():
    # Low CTL should block Tier C
    ctx = {"sources": [{"type": "code_only", "verified": False}]}
    assert determine_ctl(ctx) == 'low'
    assert not tier_c_enabled(ctx)

    # High CTL should enable Tier C
    ctx = {"sources": [{"type": "official_docs", "verified": True}]}
    assert determine_ctl(ctx) == 'high'
    assert tier_c_enabled(ctx)

# Test: Bypass marker works in test mode
def test_simulated_bypass():
    transcript = run_audit("tests/contracts/...", simulated=True)
    assert "[CONTEXT_SIMULATED_BYPASS" in transcript
    # Tier C should run despite simulated context
```

---

## Document Maintenance

- Update when EI outputs change
- Update when CTL levels change
- Cross-reference with workflow-context.md
- Version with date

**Last Updated:** 2026-02-04
