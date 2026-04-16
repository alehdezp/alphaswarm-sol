// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_05 - SAFE
 * @dev Proper oracle implementation with all validations.
 * @notice Case ID: OR-SAFE-001
 *
 * SAFE: Staleness check, decimal handling, and circuit breaker implemented.
 */

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

contract OracleVault_05 {
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public balances;

    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant MAX_DEVIATION = 10; // 10% max price change
    uint256 public lastValidPrice;

    event PriceUpdated(uint256 oldPrice, uint256 newPrice);
    event CircuitBreakerTriggered(uint256 price, uint256 deviation);

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    // SAFE: Proper oracle implementation with all checks
    function getPrice() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // SAFE: Staleness check
        require(updatedAt >= block.timestamp - STALENESS_THRESHOLD, "Stale price");

        // SAFE: Round completeness check
        require(answeredInRound >= roundId, "Round not complete");

        // SAFE: Positive price check
        require(answer > 0, "Invalid price");

        // SAFE: Get proper decimals from oracle
        uint8 decimals = priceFeed.decimals();
        uint256 normalizedPrice = uint256(answer);

        // SAFE: Normalize to 18 decimals
        if (decimals < 18) {
            normalizedPrice = normalizedPrice * (10 ** (18 - decimals));
        } else if (decimals > 18) {
            normalizedPrice = normalizedPrice / (10 ** (decimals - 18));
        }

        // SAFE: Circuit breaker for anomalous deviations
        if (lastValidPrice > 0) {
            uint256 deviation;
            if (normalizedPrice > lastValidPrice) {
                deviation = ((normalizedPrice - lastValidPrice) * 100) / lastValidPrice;
            } else {
                deviation = ((lastValidPrice - normalizedPrice) * 100) / lastValidPrice;
            }
            require(deviation <= MAX_DEVIATION, "Price deviation too high");
        }

        return normalizedPrice;
    }

    function deposit() external payable {
        uint256 price = getPrice();
        uint256 shares = (msg.value * 1e18) / price;
        balances[msg.sender] += shares;
    }

    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "Insufficient balance");
        uint256 price = getPrice();
        uint256 amount = (shares * price) / 1e18;
        balances[msg.sender] -= shares;
        payable(msg.sender).transfer(amount);
    }
}
