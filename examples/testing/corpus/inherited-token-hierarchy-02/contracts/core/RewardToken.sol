// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MintableToken.sol";

/// @title RewardToken - Staking reward token with fee-on-transfer
/// @dev VULNERABILITY: Inherits setMinter without access control (B4)
contract RewardToken is MintableToken {
    uint256 public transferFeeBps;
    address public feeCollector;
    mapping(address => bool) public feeExempt;

    constructor(
        string memory _name,
        string memory _symbol,
        address _minter,
        uint256 _maxSupply,
        uint256 _feeBps
    ) {
        name = _name;
        symbol = _symbol;
        decimals = 18;
        _initMintable(_minter, _maxSupply);
        transferFeeBps = _feeBps;
        feeCollector = msg.sender;
    }

    /// @notice Override transfer to add fee
    /// @dev VULNERABILITY: Fee-on-transfer not accounted for by callers (token-001)
    function transfer(address to, uint256 amount) external returns (bool) {
        uint256 fee = 0;
        if (!feeExempt[msg.sender] && transferFeeBps > 0) {
            fee = (amount * transferFeeBps) / 10000;
        }
        uint256 netAmount = amount - fee;

        _safeTransfer(msg.sender, to, netAmount);
        if (fee > 0) {
            _safeTransfer(msg.sender, feeCollector, fee);
        }
        return true;
    }

    /// @notice Set fee exemption
    /// @dev VULNERABILITY: Missing access control
    function setFeeExempt(address account, bool exempt) external {
        feeExempt[account] = exempt;
    }

    /// @notice Change fee collector
    /// @dev VULNERABILITY: Missing access control
    function setFeeCollector(address newCollector) external {
        feeCollector = newCollector;
    }

    /// @notice Update transfer fee
    /// @dev VULNERABILITY: Missing access control, no upper bound
    function setTransferFee(uint256 newFeeBps) external {
        transferFeeBps = newFeeBps;
    }

    // Note: setMinter from MintableToken is INHERITED without access control (B4)
}
