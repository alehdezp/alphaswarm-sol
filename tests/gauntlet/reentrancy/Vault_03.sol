// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-VULN-002: Guard on Wrong Function
// VULNERABLE: Guard only on deposit, not withdraw
contract Vault_03 {
    mapping(address => uint256) public balances;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked, "ReentrancyGuard: reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    // Guard applied here (unnecessary)
    function deposit() external payable nonReentrant {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: no guard on the function that actually needs it
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
    }

    receive() external payable {}
}
