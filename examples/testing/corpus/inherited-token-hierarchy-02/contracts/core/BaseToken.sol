// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title BaseToken - Abstract base for token implementations
abstract contract BaseToken {
    mapping(address => uint256) internal _balances;
    mapping(address => mapping(address => uint256)) internal _allowances;
    uint256 internal _totalSupply;
    string public name;
    string public symbol;
    uint8 public decimals;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);

    /// @notice Safe transfer with balance check
    function _safeTransfer(address from, address to, uint256 amount) internal virtual {
        require(_balances[from] >= amount, "Insufficient balance");
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }

    /// @notice Approve spender
    /// @dev VULNERABILITY: Approval race condition (token-006)
    function approve(address spender, uint256 amount) external virtual returns (bool) {
        // Missing: require(amount == 0 || _allowances[msg.sender][spender] == 0)
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    /// @notice Transfer from approved allowance
    function transferFrom(address from, address to, uint256 amount) external virtual returns (bool) {
        require(_allowances[from][msg.sender] >= amount, "Allowance exceeded");
        _allowances[from][msg.sender] -= amount;
        _safeTransfer(from, to, amount);
        return true;
    }

    function balanceOf(address account) external view returns (uint256) { return _balances[account]; }
    function totalSupply() external view returns (uint256) { return _totalSupply; }
}
