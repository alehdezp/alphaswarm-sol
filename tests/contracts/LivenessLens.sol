// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IToken {
    function balanceOf(address account) external view returns (uint256);
}

contract LivenessNoWithdraw {
    bool public paused;

    function pushPayment(address payable recipient) external payable {
        recipient.transfer(1);
    }

    function auctionBid(address payable previousBidder) external payable {
        previousBidder.transfer(1);
    }

    function pauseSensitive() external {
        require(!paused, "paused");
        paused = true;
    }
}

contract LivenessMain {
    event Processed(address indexed user, uint256 value);

    address public owner;
    address[] public recipients;
    mapping(address => uint256) public balances;
    bytes public data;
    bool public locked;
    uint256 public fee;
    IToken public token;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address tokenAddress) {
        owner = msg.sender;
        token = IToken(tokenAddress);
    }

    function loopGasExhaustion(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            recipients.push(msg.sender);
        }
    }

    function nestedLoop(uint256[] calldata inputs) external {
        for (uint256 i = 0; i < inputs.length; i++) {
            for (uint256 j = 0; j < inputs.length; j++) {
                balances[msg.sender] += 1;
            }
        }
    }

    function dynamicGas(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            balances[msg.sender] += 1;
        }
    }

    function transactionSizeAttack() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += 1;
        }
    }

    function batchNoLimit(address[] calldata recipientsInput) external {
        for (uint256 i = 0; i < recipientsInput.length; i++) {
            balances[recipientsInput[i]] += 1;
        }
    }

    function stateGrowth(address user) external {
        recipients.push(user);
    }

    function unboundedArrayOps() external view returns (uint256) {
        uint256 total;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += i;
        }
        return total;
    }

    function mappingIteration(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            balances[msg.sender] += 1;
        }
    }

    function setBytes(bytes calldata input) external {
        data = input;
    }

    function callbackGrief(address target) external {
        target.call("");
    }

    function externalDependency(address target) external {
        target.call("");
        balances[msg.sender] = 1;
    }

    function timeGrief() external {
        require(block.timestamp > 0, "time");
        balances[msg.sender] = 1;
    }

    function cascadingFailures(address targetA, address targetB) external {
        targetA.call("");
        targetB.call("");
    }

    function gasForward(address target) external {
        target.call{gas: 5000}("");
    }

    function divide(uint256 x) external pure returns (uint256) {
        return 10 / x;
    }

    function arrayBounds(uint256[] calldata arr, uint256 idx) external pure returns (uint256) {
        return arr[idx];
    }

    function assertCheck(uint256 x) external {
        assert(x > 0);
    }

    function overflowRisk(uint256 x) external pure returns (uint256) {
        return x + 1;
    }

    function storageCostAttack(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            recipients.push(msg.sender);
        }
    }

    function unboundedDeletion(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            delete balances[address(uint160(i))];
        }
    }

    function setFee(uint256 feeAmount) external {
        fee = feeAmount;
    }

    function deposit(uint256 amount) external {
        balances[msg.sender] = amount;
    }

    function depositThreshold(uint256 amount, uint256 minAmount) external {
        balances[msg.sender] = amount + minAmount;
    }

    function claimRewards(address target) external {
        uint256 bal = token.balanceOf(msg.sender);
        if (bal > 0) {
            target.call("");
            balances[msg.sender] = bal;
        }
    }

    function transitionBlock(address target) external {
        target.call("");
        balances[msg.sender] = 2;
    }

    function deadlineNoCheck(uint256 deadline) external {
        balances[msg.sender] = deadline;
    }

    function allocateMemory(uint256 n) external pure returns (uint256[] memory) {
        uint256[] memory arr = new uint256[](n);
        return arr;
    }

    function sliceCalldata(uint256 index) external pure returns (bytes1) {
        return msg.data[index];
    }

    function recursiveDoS(uint256 n) public {
        if (n > 0) {
            recursiveDoS(n - 1);
        }
    }

    function emitInLoop(uint256 n) external {
        for (uint256 i = 0; i < n; i++) {
            emit Processed(msg.sender, i);
        }
    }

    function unlockWithExternal(address target) external {
        target.call("");
        locked = false;
    }

    function timeLock(uint256 duration) external {
        locked = true;
        fee = duration;
    }

    function emergencyRecover(address target) external {
        target.call("");
    }

    function emergencyDrain(address payable recipient) external onlyOwner {
        recipient.transfer(1);
    }
}

contract MissingEmergency {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external {
        owner = newOwner;
    }
}

contract HasEmergency {
    address public owner;
    bool public paused;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function emergencyWithdraw(address payable recipient) external onlyOwner {
        recipient.transfer(1);
    }

    function pause() external onlyOwner {
        paused = true;
    }
}

contract LivenessSafe {
    address public owner;
    address[] public recipients;
    mapping(address => uint256) public balances;
    bool public paused;
    bool public locked;
    IToken public token;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address tokenAddress) {
        owner = msg.sender;
        token = IToken(tokenAddress);
    }

    function withdraw(address payable recipient) external onlyOwner {
        recipient.transfer(1);
    }

    function boundedLoop(uint256[] calldata inputs, uint256 max) external {
        require(inputs.length <= max, "bound");
        for (uint256 i = 0; i < inputs.length; i++) {
            balances[msg.sender] += 1;
        }
    }

    function nestedConstantLoop() external pure returns (uint256) {
        uint256 total;
        for (uint256 i = 0; i < 5; i++) {
            for (uint256 j = 0; j < 5; j++) {
                total += i + j;
            }
        }
        return total;
    }

    function transactionSizeSafe() external {
        for (uint256 i = 0; i < 10; i++) {
            balances[msg.sender] += 1;
        }
    }

    function batchBounded(address[] calldata recipientsInput) external {
        require(recipientsInput.length <= 5, "bound");
        for (uint256 i = 0; i < recipientsInput.length; i++) {
            balances[recipientsInput[i]] += 1;
        }
    }

    function stateGrowthSafe() external {
        balances[msg.sender] += 1;
    }

    function arrayOpsSafe(uint256[] calldata inputs) external view returns (uint256) {
        require(inputs.length <= 5, "bound");
        return inputs.length;
    }

    function mappingIterationSafe(uint256 n) external pure returns (uint256) {
        uint256 total;
        for (uint256 i = 0; i < n && i < 5; i++) {
            total += i;
        }
        return total;
    }

    function bytesSafe(bytes calldata input) external {
        require(input.length <= 32, "size");
        balances[msg.sender] = input.length;
    }

    function pushPaymentSafe(address payable recipient) external {
        (bool ok, ) = recipient.call{value: 1}("");
        require(ok, "send failed");
    }

    function auctionBidSafe(address payable previousBidder) external {
        (bool ok, ) = previousBidder.call{value: 1}("");
        require(ok, "refund failed");
    }

    function callbackSafe(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "callback failed");
    }

    function timeGriefSafe() external onlyOwner {
        require(block.timestamp > 0, "time");
        balances[msg.sender] = 1;
    }

    function externalDependencySafe(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
    }

    function cascadingFailuresSafe(address targetA, address targetB) external {
        (bool okA, ) = targetA.call("");
        require(okA, "call failed");
        (bool okB, ) = targetB.call("");
        require(okB, "call failed");
    }

    function gasForwardSafe(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
    }

    function divideSafe(uint256 x) external pure returns (uint256) {
        require(x > 0, "zero");
        return 10 / x;
    }

    function arrayBoundsSafe(uint256[] calldata arr, uint256 idx) external pure returns (uint256) {
        require(idx < arr.length, "bounds");
        return arr[idx];
    }

    function assertSafe(uint256 x) external pure returns (uint256) {
        require(x > 0, "value");
        return x;
    }

    function uncheckedSafe(uint256 x) external pure returns (uint256) {
        unchecked {
            return x + 1;
        }
    }

    function storageCostSafe() external {
        for (uint256 i = 0; i < 5; i++) {
            recipients.push(msg.sender);
        }
    }

    function deletionSafe() external {
        for (uint256 i = 0; i < recipients.length; i++) {
            delete balances[recipients[i]];
        }
    }

    function setFeeSafe(uint256 feeAmount) external {
        require(feeAmount <= 100, "fee");
        balances[msg.sender] = feeAmount;
    }

    function depositSafe(uint256 amount) external {
        require(amount <= 100, "amount");
        balances[msg.sender] = amount;
    }

    function depositThresholdSafe(uint256 amount, uint256 minAmount) external {
        require(amount >= minAmount, "min");
        balances[msg.sender] = amount;
    }

    function liquiditySafe() external {
        balances[msg.sender] += 1;
    }

    function transitionSafe(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
        balances[msg.sender] = 2;
    }

    function pauseSafe() external {
        require(!paused, "paused");
        paused = true;
    }

    function deadlineSafe(uint256 deadline) external {
        require(deadline >= block.timestamp, "deadline");
        balances[msg.sender] = deadline;
    }

    function allocateMemorySafe(uint256 n) external pure returns (uint256[] memory) {
        require(n <= 10, "size");
        uint256[] memory arr = new uint256[](n);
        return arr;
    }

    function sliceCalldataSafe(uint256 index) external pure returns (bytes1) {
        require(index < msg.data.length, "bounds");
        return msg.data[index];
    }

    function emitSafe(uint256 n) external {
        if (n > 0) {
            balances[msg.sender] = n;
        }
    }

    function lockSafe() external {
        locked = true;
    }

    function unlockSafe() external {
        locked = false;
    }

    function timeLockSafe(uint256 duration) external {
        require(duration < 100, "duration");
        locked = true;
    }

    function emergencyRecoverSafe(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "recover failed");
    }

    function emergencyPing() external {
        balances[msg.sender] += 1;
    }
}
