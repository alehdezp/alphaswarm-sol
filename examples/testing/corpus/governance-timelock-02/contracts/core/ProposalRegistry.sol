// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProposalRegistry - Tracks governance proposals and their lifecycle
contract ProposalRegistry {
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

    event ProposalSubmitted(uint256 indexed id, address author);
    event ProposalApproved(uint256 indexed id, address approver);
    event PhaseTransition(uint256 indexed id, Phase from, Phase to);

    constructor(uint256 _required) {
        registrar = msg.sender;
        requiredApprovals = _required;
    }

    /// @notice Submit a new proposal
    function submitProposal(string calldata desc) external returns (uint256) {
        uint256 id = proposalCount++;
        Proposal storage p = proposals[id];
        p.author = msg.sender;
        p.description = desc;
        p.phase = Phase.Draft;
        p.createdAt = block.timestamp;
        emit ProposalSubmitted(id, msg.sender);
        return id;
    }

    /// @notice Advance proposal to review phase
    /// @dev VULNERABILITY: State machine violation - can advance from any phase (B3)
    function advanceToReview(uint256 id) external {
        Proposal storage p = proposals[id];
        // Missing: require(p.phase == Phase.Draft)
        p.phase = Phase.Review;
        emit PhaseTransition(id, Phase.Draft, Phase.Review);
    }

    /// @notice Approve a proposal
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

    /// @notice Mark as executed (called by timelock)
    /// @dev VULNERABILITY: Missing access control - anyone can mark executed
    function markExecuted(uint256 id) external {
        Proposal storage p = proposals[id];
        require(p.phase == Phase.Approved, "Not approved");
        p.phase = Phase.Executed;
        emit PhaseTransition(id, Phase.Approved, Phase.Executed);
    }

    /// @notice Reject proposal
    /// @dev VULNERABILITY: State machine - can reject already-executed (B3)
    function rejectProposal(uint256 id) external {
        require(msg.sender == registrar, "Not registrar");
        Proposal storage p = proposals[id];
        // Missing: require(p.phase != Phase.Executed)
        p.phase = Phase.Rejected;
    }
}
