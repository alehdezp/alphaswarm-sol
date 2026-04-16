// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IReservesPair {
    function getReserves() external view returns (uint112, uint112, uint32);
}

contract ReserveSwapSpot {
    IReservesPair public pair;
    uint256 public total;

    constructor(IReservesPair pair_) {
        pair = pair_;
    }

    function swapSpot(uint256 amountIn) external {
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        uint256 price = uint256(reserve0) * 1e18 / uint256(reserve1);
        total += amountIn * price;
    }
}
