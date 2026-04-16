// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract LoopDos {
    address[] public recipients;
    uint256[] public data;

    function unboundedLoop(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            data.push(i);
        }
    }

    function loopWithExternalCall() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            recipients[i].call("");
        }
    }

    function unboundedDelete(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            delete data[i];
        }
    }

    function constantLoop() external {
        for (uint256 i = 0; i < 10; i++) {
            data.push(i);
        }
    }

    function boundedDelete() external {
        for (uint256 i = 0; i < data.length; i++) {
            delete data[i];
        }
    }
}
