# Patterns: Read-Only Reentrancy

## Vulnerable Pattern

```solidity
// Lending protocol using Curve LP price
function getCollateralValue(address user) public view returns (uint256) {
    uint256 lpBalance = lpToken.balanceOf(user);
    // VULNERABLE: Reading price during callback
    uint256 price = curvePool.get_virtual_price();
    return lpBalance * price / 1e18;
}

function borrow(uint256 amount) external {
    require(getCollateralValue(msg.sender) >= amount * 2, "Undercollateralized");
    // ... borrow logic
}
```

## Safe Pattern

```solidity
function getCollateralValue(address user) public view returns (uint256) {
    uint256 lpBalance = lpToken.balanceOf(user);
    // Use oracle with manipulation resistance
    uint256 price = priceOracle.getPrice(address(lpToken));
    return lpBalance * price / 1e18;
}
```
