
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract NameAgnosticValueTransfer {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public funds;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // VULNERABLE: Standard naming (caught by both old and new patterns)
    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Non-standard naming (MISSED by old pattern, CAUGHT by new)
    function extract(uint256 amount) external {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Obfuscated naming (MISSED by old pattern, CAUGHT by new)
    function removeFunds(uint256 amount) external {
        funds[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABLE: Balance modification (MISSED by old pattern, CAUGHT by new)
    function adjustBalance(address user, uint256 amount) external {
        balances[user] = amount;  // WRITES_USER_BALANCE
    }

    // VULNERABLE: Bytecode-level function (MISSED by old pattern, CAUGHT by new)
    function fn_0x123abc(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }

    // SAFE: Has access control (excluded by both patterns)
    function withdrawOwner(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        payable(msg.sender).transfer(amount);
    }

    // SAFE: View function (excluded by both patterns)
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    // SAFE: Internal function (excluded by both patterns)
    function _internalTransfer(address to, uint256 amount) internal {
        payable(to).transfer(amount);
    }
}
        