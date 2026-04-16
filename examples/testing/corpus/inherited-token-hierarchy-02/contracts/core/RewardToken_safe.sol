// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BaseToken.sol";

/// @title RewardToken (SAFE VARIANT - flattened, no inheritance vulnerabilities)
contract RewardToken_safe is BaseToken {
    address public minter;
    uint256 public maxSupply;
    uint256 public transferFeeBps;
    address public feeCollector;
    address public admin;
    mapping(address => bool) public feeExempt;

    modifier onlyMinter() { require(msg.sender == minter, "Not minter"); _; }
    modifier onlyAdmin() { require(msg.sender == admin, "Not admin"); _; }

    constructor(string memory _name, string memory _symbol, address _minter, uint256 _maxSupply, uint256 _feeBps) {
        name = _name; symbol = _symbol; decimals = 18;
        minter = _minter; maxSupply = _maxSupply;
        transferFeeBps = _feeBps; feeCollector = msg.sender; admin = msg.sender;
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        require(amount == 0 || _allowances[msg.sender][spender] == 0, "Reset first"); // FIXED
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        uint256 fee = (!feeExempt[msg.sender] && transferFeeBps > 0) ? (amount * transferFeeBps) / 10000 : 0;
        uint256 netAmount = amount - fee;
        _safeTransfer(msg.sender, to, netAmount);
        if (fee > 0) { _safeTransfer(msg.sender, feeCollector, fee); }
        return true;
    }

    function mint(address to, uint256 amount) external onlyMinter {
        require(_totalSupply + amount <= maxSupply, "Exceeds max supply");
        _totalSupply += amount; _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function setMinter(address newMinter) external onlyAdmin { minter = newMinter; } // FIXED
    function setFeeExempt(address account, bool exempt) external onlyAdmin { feeExempt[account] = exempt; } // FIXED
    function setFeeCollector(address newCollector) external onlyAdmin { feeCollector = newCollector; } // FIXED
    function setTransferFee(uint256 newFeeBps) external onlyAdmin { // FIXED
        require(newFeeBps <= 1000, "Fee too high");
        transferFeeBps = newFeeBps;
    }
}
