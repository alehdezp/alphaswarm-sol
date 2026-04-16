# [P1-T1] Intent Schema

**Phase**: 1 - Intent Annotation
**Task ID**: P1-T1
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 2 days
**Actual Effort**: -

---

## Executive Summary

Define the data structures for capturing LLM-inferred **business intent** of Solidity functions. Intent is the KEY MISSING PIECE that transforms BSKG from syntactic pattern matching to semantic understanding. With intent, we can detect when code behavior deviates from expected behavior - the essence of business logic bugs.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T1] Domain Knowledge Graph - Intent links to specs

### Blocks These Tasks
- [P1-T2] LLM Intent Annotator - Uses these schemas
- [P1-T3] Builder Integration - Stores intent in nodes

---

## Objectives

1. Define `FunctionIntent` dataclass capturing business purpose
2. Define `TrustAssumption` for security assumptions
3. Define `InferredInvariant` for expected properties
4. Create intent taxonomy (withdrawal, deposit, swap, governance, etc.)
5. Define confidence scoring for inferred intents

---

## Technical Design

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class BusinessPurpose(Enum):
    """Taxonomy of function business purposes."""
    # Value movement
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    CLAIM_REWARDS = "claim_rewards"

    # Trading
    SWAP = "swap"
    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"

    # Governance
    VOTE = "vote"
    PROPOSE = "propose"
    EXECUTE_PROPOSAL = "execute_proposal"

    # Administration
    SET_PARAMETER = "set_parameter"
    PAUSE = "pause"
    UPGRADE = "upgrade"
    TRANSFER_OWNERSHIP = "transfer_ownership"

    # Financial
    BORROW = "borrow"
    REPAY = "repay"
    LIQUIDATE = "liquidate"

    # Utility
    VIEW_ONLY = "view_only"
    CALLBACK = "callback"
    INTERNAL_HELPER = "internal_helper"

    # Unknown
    UNKNOWN = "unknown"


class TrustLevel(Enum):
    """Who can call this function safely."""
    PERMISSIONLESS = "permissionless"  # Anyone
    DEPOSITOR_ONLY = "depositor_only"  # Only users with deposits
    ROLE_RESTRICTED = "role_restricted"  # Specific roles
    OWNER_ONLY = "owner_only"  # Contract owner
    INTERNAL_ONLY = "internal_only"  # Only other contract functions


@dataclass
class TrustAssumption:
    """A security assumption the function makes."""
    id: str
    description: str  # "Oracle price is fresh"
    category: str  # "oracle", "external_contract", "caller", "timing"
    critical: bool  # If violated, is this exploitable?
    validation_check: Optional[str]  # How to verify assumption holds


@dataclass
class InferredInvariant:
    """A property that should hold after function execution."""
    id: str
    description: str  # "Caller's balance decreases by amount"
    scope: str  # "function", "transaction", "global"
    formal: Optional[str]  # Potential formal representation
    related_spec: Optional[str]  # Link to domain KG spec


@dataclass
class FunctionIntent:
    """
    LLM-inferred business intent and security context.

    This is THE KEY DATA STRUCTURE for semantic analysis.
    """
    # What business operation is this?
    business_purpose: BusinessPurpose
    purpose_confidence: float  # 0.0 to 1.0
    purpose_reasoning: str  # Why LLM inferred this

    # Who should be able to call this?
    expected_trust_level: TrustLevel
    authorized_callers: List[str]  # ["depositor", "owner", "anyone"]

    # What assumptions does this make?
    trust_assumptions: List[TrustAssumption]

    # What should be true after execution?
    inferred_invariants: List[InferredInvariant]

    # Links to domain KG
    likely_specs: List[str]  # ["erc20_transfer", "erc4626_withdraw"]
    spec_confidence: Dict[str, float]

    # Risk indicators from LLM analysis
    risk_notes: List[str]
    complexity_score: float  # How complex/risky is this function

    # Raw LLM response for debugging
    raw_llm_response: Optional[str] = None
```

---

## Success Criteria

- [ ] All dataclasses defined with serialization
- [ ] Business purpose taxonomy covers 90%+ of DeFi functions
- [ ] Trust level taxonomy is complete
- [ ] Integration with BSKG node properties
- [ ] Documentation complete

---

## Validation Tests

```python
def test_intent_creation():
    """Test creating function intent."""
    intent = FunctionIntent(
        business_purpose=BusinessPurpose.WITHDRAWAL,
        purpose_confidence=0.9,
        purpose_reasoning="Function transfers ETH to caller based on balance",
        expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
        authorized_callers=["depositor"],
        trust_assumptions=[
            TrustAssumption(
                id="balance_accurate",
                description="Balance mapping is accurate",
                category="state",
                critical=True,
                validation_check=None,
            )
        ],
        inferred_invariants=[
            InferredInvariant(
                id="balance_decrease",
                description="Caller's balance decreases by withdrawn amount",
                scope="function",
                formal="balances[msg.sender]_post == balances[msg.sender]_pre - amount",
                related_spec="erc4626_withdraw",
            )
        ],
        likely_specs=["erc4626"],
        spec_confidence={"erc4626": 0.85},
        risk_notes=["External call before state update - potential reentrancy"],
        complexity_score=0.7,
    )
    assert intent.business_purpose == BusinessPurpose.WITHDRAWAL
    assert intent.purpose_confidence == 0.9

def test_intent_serialization():
    """Test intent round-trip serialization."""
    intent = FunctionIntent(...)
    serialized = intent.to_dict()
    restored = FunctionIntent.from_dict(serialized)
    assert restored.business_purpose == intent.business_purpose
```

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
