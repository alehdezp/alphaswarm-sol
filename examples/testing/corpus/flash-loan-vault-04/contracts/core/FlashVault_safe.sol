// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title FlashVault (SAFE VARIANT)
contract FlashVault_safe {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 public totalAssets;
    address public keeper;
    uint256 public flashFeeBps;
    bool private _locked;
    uint256 public constant MIN_INITIAL_DEPOSIT = 1e15; // Prevent share inflation
    uint256 public constant DEAD_SHARES = 1000; // Burn first shares

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyKeeper() { require(msg.sender == keeper, "Not keeper"); _; }

    event Deposit(address indexed user, uint256 assets, uint256 shares_minted);
    event Withdraw(address indexed user, uint256 assets, uint256 shares_burned);
    event FlashLoan(address indexed borrower, uint256 amount, uint256 fee);

    constructor(uint256 _flashFee) { keeper = msg.sender; flashFeeBps = _flashFee; }

    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        uint256 sharesToMint;
        if (totalShares == 0) {
            require(msg.value >= MIN_INITIAL_DEPOSIT, "Below minimum"); // FIXED
            sharesToMint = msg.value - DEAD_SHARES; // Burn dead shares to prevent inflation
            totalShares += DEAD_SHARES; // Dead shares
        } else {
            sharesToMint = (msg.value * totalShares) / totalAssets;
        }
        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += msg.value;
        emit Deposit(msg.sender, msg.value, sharesToMint);
    }

    function withdraw(uint256 shareAmount) external nonReentrant { // FIXED
        require(shares[msg.sender] >= shareAmount, "Insufficient");
        uint256 assets = (shareAmount * totalAssets) / totalShares;
        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        totalAssets -= assets;
        (bool ok, ) = msg.sender.call{value: assets}("");
        require(ok, "Withdraw failed");
        emit Withdraw(msg.sender, assets, shareAmount);
    }

    function flashLoan(uint256 amount, bytes calldata data) external nonReentrant {
        require(amount <= totalAssets, "Exceeds reserves");
        uint256 balBefore = address(this).balance;
        uint256 fee = (amount * flashFeeBps) / 10000;
        require(fee > 0, "Fee required"); // FIXED
        (bool ok, ) = msg.sender.call{value: amount}(data);
        require(ok, "Flash callback failed");
        require(address(this).balance >= balBefore + fee, "Repay with fee");
        totalAssets += fee;
        emit FlashLoan(msg.sender, amount, fee);
    }

    function setFlashFee(uint256 newFee) external onlyKeeper { flashFeeBps = newFee; } // FIXED
    function setKeeper(address newKeeper) external onlyKeeper { keeper = newKeeper; } // FIXED

    receive() external payable {}
}
