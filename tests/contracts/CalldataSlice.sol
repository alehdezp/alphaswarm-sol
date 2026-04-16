// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract CalldataSlice {
    function sliceNoCheck() external pure returns (bytes memory) {
        return msg.data[4:];
    }

    function sliceChecked() external pure returns (bytes memory) {
        require(msg.data.length >= 36, "len");
        return msg.data[4:];
    }
}
