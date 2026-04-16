// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-VULN-004: Read-Only Reentrancy
// VULNERABLE: View function returns inconsistent state during callback
contract Vault_07 {
    mapping(address => uint256) public balances;
    uint256 public totalShares;
    uint256 public totalAssets;

    function deposit() external payable {
        uint256 shares = msg.value; // 1:1 for simplicity
        balances[msg.sender] += shares;
        totalShares += shares;
        totalAssets += msg.value;
    }

    // VULNERABLE: external call before state is finalized
    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "insufficient");
        uint256 assets = (shares * totalAssets) / totalShares;

        // External call while totalShares/totalAssets not yet updated
        (bool ok, ) = msg.sender.call{value: assets}("");
        require(ok, "call failed");

        // State updated AFTER call - view functions return stale data during callback
        balances[msg.sender] -= shares;
        totalShares -= shares;
        totalAssets -= assets;
    }

    // This view function can return inconsistent data during reentrancy
    // External protocols relying on this value can be exploited
    function getShareValue() external view returns (uint256) {
        if (totalShares == 0) return 1e18;
        return (totalAssets * 1e18) / totalShares;
    }

    receive() external payable {}
}
