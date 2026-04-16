// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title FortifiedLender - Defense-in-depth lending protocol (Category C3)
/// @dev Multiple protection layers stack: reentrancy guard + CEI + access control + pausable
/// @dev KNOWN BUG: This function looks vulnerable to reentrancy (IT IS NOT)
contract FortifiedLender {
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public loans;
    uint256 public totalDeposits;
    uint256 public totalLoans;
    address public admin;
    bool public paused;
    bool private _locked;
    uint256 public collateralRatio; // 150% = 15000

    modifier nonReentrant() {
        require(!_locked, "Reentrancy guard");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Paused");
        _;
    }

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Borrowed(address indexed user, uint256 amount);
    event Repaid(address indexed user, uint256 amount);

    constructor() {
        admin = msg.sender;
        collateralRatio = 15000;
    }

    /// @notice Deposit collateral
    function deposit() external payable whenNotPaused {
        require(msg.value > 0, "Zero deposit");
        deposits[msg.sender] += msg.value;
        totalDeposits += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Withdraw collateral (LOOKS dangerous, IS safe)
    /// @dev WARNING: External call present but protected by nonReentrant + CEI
    function withdraw(uint256 amount) external nonReentrant whenNotPaused {
        require(deposits[msg.sender] >= amount, "Insufficient");
        require(loans[msg.sender] == 0, "Repay loans first"); // No withdrawal while borrowed

        // CEI: State update BEFORE external call
        deposits[msg.sender] -= amount;
        totalDeposits -= amount;

        // External call (looks vulnerable but nonReentrant + CEI = safe)
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    /// @notice Borrow against collateral (properly collateralized)
    function borrow(uint256 amount) external nonReentrant whenNotPaused {
        uint256 maxBorrow = (deposits[msg.sender] * 10000) / collateralRatio;
        require(loans[msg.sender] + amount <= maxBorrow, "Undercollateralized");

        loans[msg.sender] += amount;
        totalLoans += amount;

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Borrow failed");

        emit Borrowed(msg.sender, amount);
    }

    /// @notice Repay loan
    function repay() external payable whenNotPaused {
        require(msg.value > 0, "Zero repay");
        uint256 repayAmount = msg.value > loans[msg.sender] ? loans[msg.sender] : msg.value;
        loans[msg.sender] -= repayAmount;
        totalLoans -= repayAmount;
        if (msg.value > repayAmount) {
            // Refund excess
            (bool ok, ) = msg.sender.call{value: msg.value - repayAmount}("");
            require(ok, "Refund failed");
        }
        emit Repaid(msg.sender, repayAmount);
    }

    /// @notice Liquidate (properly access controlled + health check)
    function liquidate(address user) external onlyAdmin nonReentrant {
        uint256 maxBorrow = (deposits[user] * 10000) / collateralRatio;
        require(loans[user] > maxBorrow, "Position healthy"); // Proper health check
        uint256 seized = deposits[user];
        deposits[user] = 0;
        loans[user] = 0;
        totalDeposits -= seized;
        (bool ok, ) = msg.sender.call{value: seized}("");
        require(ok, "Liquidation failed");
    }

    /// @notice Admin functions (all properly guarded)
    function pause() external onlyAdmin { paused = true; }
    function unpause() external onlyAdmin { paused = false; }
    function setCollateralRatio(uint256 ratio) external onlyAdmin {
        require(ratio >= 10000, "Ratio too low"); // At least 100%
        collateralRatio = ratio;
    }

    receive() external payable {}
}
