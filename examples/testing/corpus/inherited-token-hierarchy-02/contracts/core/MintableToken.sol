// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BaseToken.sol";

/// @title MintableToken - Token with minting capability
abstract contract MintableToken is BaseToken {
    address public minter;
    uint256 public maxSupply;

    modifier onlyMinter() {
        require(msg.sender == minter, "Not minter");
        _;
    }

    function _initMintable(address _minter, uint256 _maxSupply) internal {
        minter = _minter;
        maxSupply = _maxSupply;
    }

    /// @notice Mint new tokens
    function mint(address to, uint256 amount) external virtual onlyMinter {
        require(_totalSupply + amount <= maxSupply, "Exceeds max supply");
        _totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    /// @notice Burn tokens
    function burn(uint256 amount) external virtual {
        require(_balances[msg.sender] >= amount, "Insufficient");
        _balances[msg.sender] -= amount;
        _totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }

    /// @notice Change minter
    /// @dev VULNERABILITY: Missing access control (inherited by children)
    function setMinter(address newMinter) external virtual {
        minter = newMinter;
    }
}
