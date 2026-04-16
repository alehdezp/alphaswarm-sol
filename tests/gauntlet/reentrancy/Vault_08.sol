// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-SAFE-004: Custom Mutex Lock
// SAFE: Custom reentrancy protection via locked variable
contract Vault_08 {
    mapping(address => uint256) public balances;
    bool private locked;

    modifier mutex() {
        require(!locked, "locked");
        locked = true;
        _;
        locked = false;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: protected by custom mutex
    function withdraw(uint256 amount) external mutex {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
    }

    receive() external payable {}
}
