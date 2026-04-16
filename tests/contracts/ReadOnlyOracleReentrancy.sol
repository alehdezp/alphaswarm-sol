// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IPriceOracle {
    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract ReadOnlyOracleReentrancy {
    IPriceOracle public oracle;
    uint256 public cachedPrice;
    uint256 public totalAssets;

    constructor(IPriceOracle _oracle) {
        oracle = _oracle;
    }

    function updatePrice(uint256 amount) external {
        (bool ok, ) = msg.sender.call("");
        require(ok, "call failed");
        cachedPrice = amount;
        totalAssets += amount;
    }

    function getPrice() external view returns (uint256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return cachedPrice + uint256(answer);
    }

    function getAssets() external view returns (uint256) {
        return totalAssets;
    }
}
