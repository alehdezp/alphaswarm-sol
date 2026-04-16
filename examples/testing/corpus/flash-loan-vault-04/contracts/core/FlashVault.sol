// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title FlashVault - ERC-4626-style vault with flash lending
contract FlashVault {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 public totalAssets;
    address public keeper;
    uint256 public flashFeeBps; // flash loan fee in basis points

    event Deposit(address indexed user, uint256 assets, uint256 shares_minted);
    event Withdraw(address indexed user, uint256 assets, uint256 shares_burned);
    event FlashLoan(address indexed borrower, uint256 amount, uint256 fee);

    constructor(uint256 _flashFee) {
        keeper = msg.sender;
        flashFeeBps = _flashFee;
    }

    /// @notice Deposit assets and receive shares
    /// @dev VULNERABILITY: First depositor share inflation (vault-share-inflation)
    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        uint256 sharesToMint;
        if (totalShares == 0) {
            // No minimum deposit check - first depositor can manipulate share price
            sharesToMint = msg.value;
        } else {
            sharesToMint = (msg.value * totalShares) / totalAssets;
        }
        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += msg.value;
        emit Deposit(msg.sender, msg.value, sharesToMint);
    }

    /// @notice Withdraw assets by burning shares
    /// @dev VULNERABILITY: Reentrancy via encoding indirection (A6)
    function withdraw(uint256 shareAmount) external {
        require(shares[msg.sender] >= shareAmount, "Insufficient");
        uint256 assets = (shareAmount * totalAssets) / totalShares;

        // Encoding indirection: construct call data dynamically
        bytes memory payload = abi.encodeWithSignature(
            "onVaultWithdraw(uint256,address)",
            assets,
            msg.sender
        );

        // Hidden external call via encoded dispatch
        (bool ok, ) = msg.sender.call{value: assets}(payload);
        require(ok, "Withdraw failed");

        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        totalAssets -= assets;

        emit Withdraw(msg.sender, assets, shareAmount);
    }

    /// @notice Flash loan from vault reserves
    /// @dev VULNERABILITY: Flash loan enables share price manipulation
    function flashLoan(uint256 amount, bytes calldata data) external {
        require(amount <= totalAssets, "Exceeds reserves");
        uint256 balBefore = address(this).balance;
        uint256 fee = (amount * flashFeeBps) / 10000;

        (bool ok, ) = msg.sender.call{value: amount}(data);
        require(ok, "Flash callback failed");

        // VULNERABILITY: Only checks balance, not that fee was actually paid
        require(address(this).balance >= balBefore + fee, "Repay with fee");
        totalAssets += fee;

        emit FlashLoan(msg.sender, amount, fee);
    }

    /// @notice Donate assets to inflate share price
    /// @dev VULNERABILITY: Direct donation attack vector
    function donateToVault() external payable {
        totalAssets += msg.value;
    }

    /// @notice Adjust flash fee
    /// @dev VULNERABILITY: Missing access control
    function setFlashFee(uint256 newFee) external {
        flashFeeBps = newFee;
    }

    /// @notice Change keeper
    /// @dev VULNERABILITY: Missing access control
    function setKeeper(address newKeeper) external {
        keeper = newKeeper;
    }

    receive() external payable {}
}
