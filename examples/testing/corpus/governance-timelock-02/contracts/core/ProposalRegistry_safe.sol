// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProposalRegistry (SAFE VARIANT)
contract ProposalRegistry_safe {
    enum Phase { Draft, Review, Approved, Rejected, Executed }

    struct Proposal {
        address author;
        string description;
        Phase phase;
        uint256 createdAt;
        uint256 approvalCount;
        mapping(address => bool) approvers;
    }

    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    uint256 public requiredApprovals;
    address public registrar;
    address public timelock;

    modifier onlyRegistrar() { require(msg.sender == registrar, "Not registrar"); _; }

    event ProposalSubmitted(uint256 indexed id, address author);
    event ProposalApproved(uint256 indexed id, address approver);
    event PhaseTransition(uint256 indexed id, Phase from, Phase to);

    constructor(uint256 _required) { registrar = msg.sender; requiredApprovals = _required; }

    function setTimelock(address _timelock) external onlyRegistrar { timelock = _timelock; }

    function submitProposal(string calldata desc) external returns (uint256) {
        uint256 id = proposalCount++;
        Proposal storage p = proposals[id];
        p.author = msg.sender; p.description = desc; p.phase = Phase.Draft; p.createdAt = block.timestamp;
        emit ProposalSubmitted(id, msg.sender);
        return id;
    }

    function advanceToReview(uint256 id) external {
        Proposal storage p = proposals[id];
        require(p.phase == Phase.Draft, "Not draft"); // FIXED
        p.phase = Phase.Review;
        emit PhaseTransition(id, Phase.Draft, Phase.Review);
    }

    function approveProposal(uint256 id) external {
        Proposal storage p = proposals[id];
        require(p.phase == Phase.Review, "Not in review");
        require(!p.approvers[msg.sender], "Already approved");
        p.approvers[msg.sender] = true;
        p.approvalCount++;
        if (p.approvalCount >= requiredApprovals) {
            p.phase = Phase.Approved;
            emit PhaseTransition(id, Phase.Review, Phase.Approved);
        }
        emit ProposalApproved(id, msg.sender);
    }

    function markExecuted(uint256 id) external {
        require(msg.sender == timelock, "Not timelock"); // FIXED
        Proposal storage p = proposals[id];
        require(p.phase == Phase.Approved, "Not approved");
        p.phase = Phase.Executed;
    }

    function rejectProposal(uint256 id) external onlyRegistrar {
        Proposal storage p = proposals[id];
        require(p.phase != Phase.Executed, "Cannot reject executed"); // FIXED
        p.phase = Phase.Rejected;
    }
}
