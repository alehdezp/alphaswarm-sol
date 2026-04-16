// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CallWithValue {
    function forward(address target, bytes calldata data) external payable {
        (bool ok, ) = target.call{value: msg.value}(data);
        require(ok, "call failed");
    }
}
