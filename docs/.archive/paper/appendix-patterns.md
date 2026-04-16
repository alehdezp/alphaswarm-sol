# Appendix B: Pattern Examples

This appendix provides example patterns for each tier of the AlphaSwarm.sol pattern system, demonstrating the structure and matching logic used for vulnerability detection.

---

## B.1 Tier A Pattern: Classic Reentrancy

Tier A patterns are fully deterministic, operating on graph properties and behavioral signatures without LLM reasoning.

```yaml
id: reentrancy-classic
name: Classic Reentrancy
severity: critical
lens: [Reentrancy]
tier: A
description: |
  Detects the classic reentrancy vulnerability where external calls
  occur before state updates. This pattern matches the behavioral
  signature R:bal -> X:out -> W:bal without a reentrancy guard.

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations:
          - TRANSFERS_VALUE_OUT
          - WRITES_USER_BALANCE
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

evidence:
  required:
    - behavioral_signature
    - code_locations
  optional:
    - call_graph_path

test_guidance:
  foundry: |
    Create attacker contract with receive() that re-enters.
    Verify balance can be drained beyond legitimate amount.
```

### Pattern Explanation

This pattern detects functions that:
1. Are publicly accessible (`visibility in [public, external]`)
2. Transfer value out AND write user balances
3. Transfer value BEFORE writing balances (signature ordering)
4. Do NOT have a reentrancy guard

The `sequence_order` condition is critical: it ensures the external call happens before the state update, which is the precise condition enabling reentrancy attacks.

---

## B.2 Tier A Pattern: Permissive Access Control

```yaml
id: access-control-permissive
name: Permissive Access Control on Critical State
severity: high
lens: [AccessControl]
tier: A
description: |
  Detects functions that modify privileged state (owner, fees, paused)
  without any access control. Matches M:crit signature without C:auth.

match:
  tier_a:
    all:
      - property: writes_privileged_state
        value: true
      - property: visibility
        op: in
        value: [public, external]
    none:
      - property: has_access_gate
        value: true

evidence:
  required:
    - state_variables_modified
    - function_visibility
  optional:
    - modifier_list

test_guidance:
  foundry: |
    Call function from non-owner address.
    Verify critical state is modified without revert.
```

### Pattern Explanation

This pattern identifies functions that:
1. Write to privileged state variables (owner, fees, admin, paused)
2. Are publicly callable
3. Lack any access control (no modifiers, no require statements checking msg.sender)

Functions matching this pattern allow any caller to modify critical contract state, potentially enabling complete protocol takeover.

---

## B.3 Tier A Pattern: Unprotected Initializer

```yaml
id: initializer-unprotected
name: Unprotected Initializer Function
severity: critical
lens: [AccessControl]
tier: A
description: |
  Detects initializer functions that can be called multiple times
  or by unauthorized callers. Matches I:init without proper guards.

match:
  tier_a:
    all:
      - property: is_initializer
        value: true
      - property: visibility
        op: in
        value: [public, external]
    any:
      - property: has_initializer_guard
        value: false
      - property: can_reinitialize
        value: true

evidence:
  required:
    - function_name
    - modifier_analysis
    - state_initialization_targets
```

---

## B.4 Tier B Pattern: Oracle Manipulation

Tier B patterns are exploratory, requiring LLM verification to assess context and validate findings.

```yaml
id: oracle-manipulation
name: Oracle Manipulation Vulnerability
severity: high
lens: [Oracle]
tier: B
description: |
  Exploratory pattern for oracle manipulation. Detects functions that
  read oracle values and use them in value transfers without sufficient
  validation. Requires LLM verification to assess oracle trust and
  validation adequacy.

match:
  tier_b:
    all:
      - has_operation: READS_ORACLE
      - has_operation: TRANSFERS_VALUE_OUT
    context_questions:
      - Is the oracle trusted (Chainlink, TWAP)?
      - Is there sufficient staleness checking?
      - Can the oracle be manipulated within a single block?
      - What is the maximum value at risk from manipulation?
    verification_required: true

evidence:
  required:
    - oracle_address_or_interface
    - value_calculation_logic
  optional:
    - staleness_check_present
    - price_bounds_check

llm_guidance: |
  Evaluate the oracle source and validation logic. Chainlink feeds with
  proper staleness checks are generally safe. Spot prices or single-block
  TWAP are high risk. Look for checks on price bounds, heartbeat, and
  sequencer status.
```

### Pattern Explanation

This Tier B pattern:
1. Identifies functions using oracle data for value transfers
2. Generates context questions for LLM verification
3. Does not automatically flag as vulnerable (requires verification)
4. Provides guidance for the verifying agent

The pattern catches potential oracle manipulation but acknowledges that proper validation may make the code safe.

---

## B.5 Tier B Pattern: Flash Loan Attack Vector

```yaml
id: flash-loan-attack-vector
name: Flash Loan Attack Vector
severity: high
lens: [MEV, Oracle]
tier: B
description: |
  Identifies functions that may be vulnerable to flash loan attacks
  through price manipulation or liquidity manipulation. Requires
  analysis of economic preconditions.

match:
  tier_b:
    all:
      - any:
          - has_operation: READS_ORACLE
          - has_operation: READS_EXTERNAL_VALUE
      - has_operation: TRANSFERS_VALUE_OUT
    context_questions:
      - Can the oracle/price source be manipulated with borrowed funds?
      - Is there a time delay or TWAP that would prevent single-block manipulation?
      - What is the minimum capital required for profitable manipulation?
      - Are there circuit breakers or slippage protections?
    verification_required: true

attack_narrative_template: |
  1. Attacker takes flash loan of $X
  2. Manipulates {oracle_or_price_source} via {mechanism}
  3. Calls {vulnerable_function} with manipulated price
  4. Extracts {value_at_risk}
  5. Repays flash loan with profit

evidence:
  required:
    - price_dependency_chain
    - manipulable_source_identification
```

---

## B.6 Tier B Pattern: Weak Authorization

```yaml
id: weak-authorization
name: Weak Authorization on Sensitive Operations
severity: medium
lens: [AccessControl]
tier: B
description: |
  Detects functions with authorization that may be insufficient for
  the sensitivity of the operation. Requires LLM analysis of whether
  the access control matches the impact.

match:
  tier_b:
    all:
      - property: has_access_gate
        value: true
      - any:
          - has_operation: MODIFIES_CRITICAL_STATE
          - has_operation: TRANSFERS_VALUE_OUT
          - has_operation: MODIFIES_ROLES
    context_questions:
      - Is the authorization level appropriate for the operation?
      - Could a compromised authorized address cause significant harm?
      - Are there timelock or multi-sig requirements?
      - Is there an upgrade path that could bypass authorization?
    verification_required: true
```

---

## B.7 Tier C Pattern: State Machine Violation

Tier C patterns require semantic labels from an LLM labeling pass, enabling detection of policy and invariant violations.

```yaml
id: state-machine-invalid-transition
name: Invalid State Machine Transition
severity: medium
lens: [Logic]
tier: C
description: |
  Label-dependent pattern that detects invalid state machine transitions.
  Requires semantic labels from the LLM labeling pass to identify
  state variables and valid transition rules.

match:
  tier_c:
    requires_labels: true
    conditions:
      - has_label: state_mutation.state_variable_update
      - missing_label: control_flow.state_transition_check
    context_questions:
      - What are the valid state transitions?
      - Is this transition allowed from the current state?
      - Can an invalid transition cause economic harm?

labels_required:
  - state_mutation.state_variable_update
  - control_flow.state_transition_check
  - invariant.state_machine_invariant

evidence:
  required:
    - state_variable_identified
    - transition_logic_analysis
```

### Pattern Explanation

This Tier C pattern:
1. Requires semantic labels from the labeling pass
2. Detects state updates without proper transition validation
3. Identifies potential state machine invariant violations
4. Cannot run without prior labeling (label-dependent)

---

## B.8 Tier C Pattern: Invariant Violation

```yaml
id: invariant-violation-balance
name: Balance Invariant Violation
severity: high
lens: [Logic]
tier: C
description: |
  Detects potential violations of balance invariants where total
  balances should equal contract holdings. Requires labels identifying
  balance-related state and invariant expectations.

match:
  tier_c:
    requires_labels: true
    conditions:
      - has_label: state_mutation.balance_update
      - has_any_label:
          - missing: invariant.balance_conservation
          - missing: invariant.sum_check
    context_questions:
      - Is there an invariant that sum(balances) == contract.balance?
      - Can this function violate the balance invariant?
      - Is the violation exploitable for profit?

labels_required:
  - state_mutation.balance_update
  - invariant.balance_conservation
```

---

## B.9 Tier C Pattern: Policy Mismatch

```yaml
id: policy-mismatch-withdrawal
name: Withdrawal Policy Mismatch
severity: medium
lens: [Logic, AccessControl]
tier: C
description: |
  Detects mismatches between documented withdrawal policies and
  implementation. Requires labels from documentation analysis.

match:
  tier_c:
    requires_labels: true
    conditions:
      - has_label: value_flow.withdrawal
      - any:
          - label_conflict:
              doc_label: policy.withdrawal_limit
              code_label: implementation.withdrawal_unlimited
          - label_conflict:
              doc_label: policy.cooldown_required
              code_label: implementation.no_cooldown
    context_questions:
      - What withdrawal limits are documented?
      - Does the implementation enforce those limits?
      - What is the impact of the policy mismatch?

labels_required:
  - value_flow.withdrawal
  - policy.withdrawal_limit
  - implementation.withdrawal_unlimited
```

---

## B.10 Pattern Tier Summary

| Tier | Characteristics | Input Requirements | Verification | Confidence |
|------|-----------------|-------------------|--------------|------------|
| A | Graph-only, deterministic | BSKG properties and signatures | None required | HIGH |
| B | Exploratory, complex | BSKG + context questions | LLM verification | MEDIUM |
| C | Label-dependent, semantic | BSKG + semantic labels | Labels + LLM | MEDIUM |

### When to Use Each Tier

**Tier A**: Well-understood vulnerability patterns with deterministic detection criteria. Classic reentrancy, missing access control, unprotected initializers.

**Tier B**: Complex vulnerabilities requiring contextual analysis. Oracle manipulation, flash loan vectors, authorization adequacy. High recall, requires verification to filter false positives.

**Tier C**: Semantic vulnerabilities requiring understanding of intent. State machine violations, invariant preservation, policy compliance. Requires prior labeling pass to annotate code with semantic information.

---

## B.11 Pattern Rating Criteria

Patterns are rated based on precision and recall metrics from testing:

| Status | Precision | Recall | Description |
|--------|-----------|--------|-------------|
| draft | < 70% | < 50% | Under development, not for production |
| ready | >= 70% | >= 50% | Production use with known limitations |
| excellent | >= 90% | >= 85% | Validated extensively, high confidence |

### Precision vs Recall Tradeoffs

- **Tier A patterns** target high precision (minimize false positives)
- **Tier B patterns** target high recall (catch edge cases, verify later)
- **Tier C patterns** depend on label quality (label precision drives pattern precision)

---

## B.12 Pattern YAML Structure Reference

```yaml
# Required fields
id: string                    # Unique pattern identifier
name: string                  # Human-readable name
severity: critical|high|medium|low|info
lens: [string]                # Vulnerability categories
tier: A|B|C                   # Pattern tier

# Match conditions (tier-specific)
match:
  tier_a:                     # For Tier A patterns
    all: []                   # All conditions must match
    any: []                   # At least one must match
    none: []                  # None must match

  tier_b:                     # For Tier B patterns
    all: []
    context_questions: []     # Questions for LLM verification
    verification_required: true

  tier_c:                     # For Tier C patterns
    requires_labels: true
    conditions: []
    labels_required: []

# Evidence specification
evidence:
  required: []                # Must be present in finding
  optional: []                # Nice to have

# Optional fields
description: string           # Detailed explanation
test_guidance: {}             # How to test/verify
llm_guidance: string          # Instructions for verifier
attack_narrative_template: string  # For Tier B attack paths
```
