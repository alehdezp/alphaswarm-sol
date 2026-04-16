// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VoteAggregator (SAFE VARIANT)
contract VoteAggregator_safe {
    address public governor;
    address public operator;
    mapping(address => uint256) public delegatedPower;
    bool private _locked;
    uint256 public constant MAX_BATCH = 50;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    constructor(address _governor) {
        governor = _governor;
        operator = msg.sender;
    }

    function batchVote(uint256[] calldata proposalIds, bool[] calldata supports) external {
        require(proposalIds.length == supports.length, "Length mismatch");
        require(proposalIds.length <= MAX_BATCH, "Batch too large"); // FIXED
        for (uint256 i = 0; i < proposalIds.length; i++) {
            (bool ok, ) = governor.call(
                abi.encodeWithSignature("castVote(uint256,bool)", proposalIds[i], supports[i])
            );
            require(ok, "Vote failed");
        }
    }

    function delegateTo(uint256 amount) external {
        delegatedPower[msg.sender] += amount;
    }

    function withdrawDelegation() external nonReentrant { // FIXED
        uint256 amount = delegatedPower[msg.sender];
        require(amount > 0, "Nothing delegated");
        delegatedPower[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
    }

    receive() external payable {}
}
