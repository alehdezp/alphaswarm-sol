// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IReservePool {
    function getReserves() external view returns (uint112, uint112, uint32);
}

contract ReserveCollateralSpot {
    IReservePool public pool;

    constructor(IReservePool pool_) {
        pool = pool_;
    }

    function collateralValue(uint256 amount) external view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, ) = pool.getReserves();
        uint256 price = uint256(reserve0) * 1e18 / uint256(reserve1);
        return amount * price;
    }
}
