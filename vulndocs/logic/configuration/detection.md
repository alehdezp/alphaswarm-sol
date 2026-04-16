# Configuration Issues Detection

## Overview
Identify configuration vulnerabilities including inheritance order, initialization, and deployment issues.

## Inheritance Order (C3 Linearization)

### Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_multiple_inheritance | true | YES |
| parent_function_collision | true | YES |
| inheritance_order_matters | true | YES |

### Semantic Detection

**Vulnerable Pattern:**
- Contract inherits from multiple parents
- Parent contracts define same function name
- Child contract doesn't override to disambiguate
- Wrong parent called due to C3 linearization order

**Example (MDTCrowdsale):**
```solidity
contract CappedCrowdsale is Crowdsale {
    function validPurchase() internal constant returns (bool) {
        bool withinCap = weiRaised.add(msg.value) <= cap;
        return super.validPurchase() && withinCap;
    }
}

contract WhitelistedCrowdsale is Crowdsale {
    function validPurchase() internal constant returns (bool) {
        return super.validPurchase() || (whitelist[msg.sender] && !hasEnded());
    }
}

// VULNERABLE: Inheritance order affects which parent's validPurchase is called
contract MDTCrowdsale is CappedCrowdsale, WhitelistedCrowdsale {
    // Wrong order: WhitelistedCrowdsale.validPurchase() called first
    // Should be: MDTCrowdsale is WhitelistedCrowdsale, CappedCrowdsale
}
```

**Operations:** `INHERITS_MULTIPLE`, `FUNCTION_COLLISION`, `LINEARIZATION_ISSUE`
**Signature:** `I:multiple->F:collision->O:wrong_parent`

### Manual Checks

1. Review inheritance hierarchy for diamond problem
2. Check if multiple parents define same function
3. Verify child contract explicitly overrides to control order
4. Test with both inheritance orders to verify behavior
5. Prefer composition over multiple inheritance
6. Inherit from more general to more specific (left to right)

### False Positive Indicators

- Child contract explicitly overrides colliding functions
- Only single inheritance used
- Parents don't define conflicting functions
- Functions are virtual and properly overridden

## Initialization Issues

### Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| has_initializer | true | YES |
| initializer_protected | false | YES |
| can_reinitialize | true | NO |

### Detection Checklist

1. Proxy/upgradeable contract has initializer
2. Initializer not protected by onlyUninitialized check
3. Initializer can be called on implementation directly
4. Initializer sets critical state (owner, admin)

### Manual Checks

- F17: Check explicit `initialized` variable, don't use `owner == address(0)` as substitute
- Verify initializer has `initializer` modifier or explicit check
- Test calling initializer twice
- Check if implementation can be initialized directly
