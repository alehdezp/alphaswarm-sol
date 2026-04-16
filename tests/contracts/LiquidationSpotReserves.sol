// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IReservePair {
    function getReserves() external view returns (uint112, uint112, uint32);
}

contract LiquidationSpotReserves {
    IReservePair public pair;

    constructor(IReservePair pair_) {
        pair = pair_;
    }

    function liquidate(address account, uint256 amount) external view returns (uint256) {
        account;
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        uint256 price = uint256(reserve0) * 1e18 / uint256(reserve1);
        return amount * price;
    }
}
