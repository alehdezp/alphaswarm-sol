# Detection: ERC777 Hooks Reentrancy

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_token_transfer | true | YES |
| has_reentrancy_guard | false | YES |
| accepts_arbitrary_tokens | true | YES |

## Detection Checklist

1. Contract accepts arbitrary ERC20 tokens
2. Token transfer before state update
3. No reentrancy guard on token-handling functions
4. Token type not validated (could be ERC777)
