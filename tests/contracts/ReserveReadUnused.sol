// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IReservesPairUnused {
    function getReserves() external view returns (uint112, uint112, uint32);
}

contract ReserveReadUnused {
    IReservesPairUnused public pair;

    constructor(IReservesPairUnused pair_) {
        pair = pair_;
    }

    function readOnlyPrice() external view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        uint256 price = uint256(reserve0) * 1e18 / uint256(reserve1);
        return price;
    }
}
