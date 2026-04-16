// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112, uint112, uint32);
}

interface ITwapOracle {
    function consult(address token, uint32 secondsAgo) external view returns (uint256);
}

contract ExternalInfluenceLensSafe {
    IUniswapV2Pair public pair;
    ITwapOracle public twapOracle;
    mapping(address => uint256) public balances;

    constructor(IUniswapV2Pair pair_, ITwapOracle twapOracle_) {
        pair = pair_;
        twapOracle = twapOracle_;
    }

    function safeSpotPrice(address to, uint32 window) external {
        require(window >= 60, "window");
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        uint256 spot = uint256(reserve0) * 1e18 / uint256(reserve1);
        uint256 twap = twapOracle.consult(address(pair), window);
        uint256 price = (spot + twap) / 2;
        balances[to] += price;
    }
}
