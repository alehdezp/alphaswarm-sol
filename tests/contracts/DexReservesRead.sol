// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IPair {
    function getReserves() external view returns (uint112, uint112, uint32);
}

contract DexReservesRead {
    IPair public pair;

    constructor(IPair pair_) {
        pair = pair_;
    }

    function spotPrice() external view returns (uint112 r0, uint112 r1) {
        (r0, r1, ) = pair.getReserves();
    }
}
