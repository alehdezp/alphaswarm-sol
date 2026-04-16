// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-VULN-003: Cross-Function Reentrancy
// VULNERABLE: Attacker can re-enter via transfer() during withdraw()
contract Vault_05 {
    mapping(address => uint256) public balances;
    bool private _inWithdraw;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Withdraw has a partial guard but...
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        _inWithdraw = true;
        // External call while balance not yet updated
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
        _inWithdraw = false;
    }

    // VULNERABLE: This function can be called during withdraw callback
    // and will see the old (pre-update) balance
    function transfer(address to, uint256 amount) external {
        // This check doesn't help - attacker doesn't call withdraw again
        require(!_inWithdraw, "no transfers during withdraw");
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }

    receive() external payable {}
}
