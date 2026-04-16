# Patterns: Price Manipulation

## Vulnerable Pattern

```solidity
// VULNERABLE: Uses spot price from Uniswap V2 reserves
function getPrice() public view returns (uint256) {
    (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
    // Spot price from reserves - easily manipulated via flash loan
    return uint256(reserve1) * 1e18 / uint256(reserve0);
}

function deposit(uint256 amount) external {
    uint256 price = getPrice();  // Manipulable price
    uint256 shares = amount * 1e18 / price;
    _mint(msg.sender, shares);
    token.transferFrom(msg.sender, address(this), amount);
}
```

## Safe Pattern (TWAP Oracle)

```solidity
// Safe: Uses Uniswap V3 TWAP oracle
function getPrice() public view returns (uint256) {
    uint32[] memory secondsAgos = new uint32[](2);
    secondsAgos[0] = 1800;  // 30 minutes ago
    secondsAgos[1] = 0;     // now

    (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
    int56 tickDelta = tickCumulatives[1] - tickCumulatives[0];
    int24 avgTick = int24(tickDelta / 1800);

    return OracleLibrary.getQuoteAtTick(avgTick, 1e18, token0, token1);
}
```

## Safe Pattern (Chainlink Oracle)

```solidity
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

function getPrice() public view returns (uint256) {
    (
        uint80 roundId,
        int256 price,
        ,
        uint256 updatedAt,
        uint80 answeredInRound
    ) = priceFeed.latestRoundData();

    require(price > 0, "Invalid price");
    require(updatedAt > block.timestamp - 3600, "Stale price");
    require(answeredInRound >= roundId, "Stale round");

    return uint256(price);
}
```

## Variations

### Flash Loan Attack Vector

```solidity
// Attack contract exploiting spot price
contract PriceManipulator {
    function attack() external {
        // 1. Flash loan large amount
        flashLender.flashLoan(1000000e18);
    }

    function onFlashLoan(uint256 amount) external {
        // 2. Swap to skew pool reserves
        router.swap(amount, 0, path);

        // 3. Interact with vulnerable protocol at manipulated price
        vulnerableProtocol.deposit(myTokens);

        // 4. Swap back to restore price
        router.swap(receivedTokens, 0, reversePath);

        // 5. Repay flash loan with profit
        token.transfer(flashLender, amount + fee);
    }
}
```
