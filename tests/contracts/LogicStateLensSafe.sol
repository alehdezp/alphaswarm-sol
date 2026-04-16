// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract LogicStateLensSafe {
    enum Status {
        None,
        Active,
        Closed
    }

    Status public state;
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    uint256 public collateral;
    uint256 public pool;
    bool public paused;
    bool public flag = true;
    address public owner;
    bool private locked;

    event Updated(address indexed user, uint256 value);

    modifier onlyOwner() {
        require(msg.sender == owner, "owner");
        _;
    }

    modifier nonReentrant() {
        require(!locked, "locked");
        locked = true;
        _;
        locked = false;
    }

    constructor(address _owner) {
        owner = _owner;
        state = Status.Active;
    }

    function setStateChecked(Status next) external onlyOwner {
        require(state == Status.Active, "state");
        state = next;
    }

    function cleanupState() external onlyOwner {
        state = Status.None;
    }

    function guardedExternalCall(address target) external onlyOwner nonReentrant {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
        totalSupply += 1;
    }

    function updateBalanceSafe(address user, uint256 amount) external onlyOwner {
        balances[user] += amount;
        emit Updated(user, amount);
    }

    function updateCollateralSafe(uint256 amount) external onlyOwner {
        collateral += amount;
    }

    function updatePoolSafe(uint256 amount) external onlyOwner {
        pool += amount;
    }

    function withdrawSafe(uint256 amount) external {
        require(balances[msg.sender] >= amount, "balance");
        balances[msg.sender] -= amount;
        emit Updated(msg.sender, amount);
    }

    function safeTransfer(address token, address to, uint256 amount) external onlyOwner {
        (bool ok, ) = token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
        require(ok, "transfer failed");
    }

    function updateAmountSafe(uint256 amount) external onlyOwner {
        require(amount <= 1_000_000, "bounds");
        totalSupply = amount;
    }

    function protocolCallSafe(address target) external onlyOwner {
        require(target.code.length > 0, "code");
        (bool ok, ) = target.call("");
        require(ok, "call failed");
    }

    function singleCount(address user, uint256 amount) external onlyOwner {
        balances[user] += amount;
    }

    function emitCorrect(uint256 value) external {
        emit Updated(msg.sender, value);
    }
}
