// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title GovernorAlpha - Simple governance with proposal lifecycle
contract GovernorAlpha {
    enum ProposalState { Pending, Active, Defeated, Succeeded, Executed }

    struct Proposal {
        address proposer;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startTime;
        uint256 endTime;
        address target;
        bytes callData;
        ProposalState state;
        mapping(address => bool) hasVoted;
    }

    mapping(uint256 => Proposal) public proposals;
    mapping(address => uint256) public votingPower;
    uint256 public proposalCount;
    address public guardian;
    uint256 public constant VOTING_PERIOD = 3 days;
    uint256 public constant QUORUM = 1000e18;

    event ProposalCreated(uint256 indexed id, address proposer);
    event VoteCast(uint256 indexed id, address voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id);

    constructor() {
        guardian = msg.sender;
    }

    /// @notice Create a new proposal
    function propose(address target, bytes calldata data) external returns (uint256) {
        require(votingPower[msg.sender] >= 100e18, "Insufficient voting power");
        uint256 id = proposalCount++;
        Proposal storage p = proposals[id];
        p.proposer = msg.sender;
        p.startTime = block.timestamp;
        p.endTime = block.timestamp + VOTING_PERIOD;
        p.target = target;
        p.callData = data;
        p.state = ProposalState.Active;
        emit ProposalCreated(id, msg.sender);
        return id;
    }

    /// @notice Cast a vote
    /// @dev VULNERABILITY: No double-vote prevention check
    function castVote(uint256 proposalId, bool support) external {
        Proposal storage p = proposals[proposalId];
        require(p.state == ProposalState.Active, "Not active");
        require(block.timestamp <= p.endTime, "Voting ended");

        uint256 weight = votingPower[msg.sender];
        require(weight > 0, "No voting power");

        // Missing: p.hasVoted[msg.sender] check
        if (support) {
            p.forVotes += weight;
        } else {
            p.againstVotes += weight;
        }

        emit VoteCast(proposalId, msg.sender, support, weight);
    }

    /// @notice Execute a passed proposal
    /// @dev VULNERABILITY: No timelock delay before execution
    function execute(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        require(block.timestamp > p.endTime, "Voting ongoing");
        require(p.forVotes > p.againstVotes, "Not passed");
        require(p.forVotes >= QUORUM, "Quorum not met");
        require(p.state == ProposalState.Active, "Wrong state");

        p.state = ProposalState.Executed;

        (bool ok, ) = p.target.call(p.callData);
        require(ok, "Execution failed");

        emit ProposalExecuted(proposalId);
    }

    /// @notice Set guardian
    /// @dev VULNERABILITY: Missing access control
    function setGuardian(address newGuardian) external {
        guardian = newGuardian;
    }

    /// @notice Delegate voting power
    function delegate(address to, uint256 amount) external {
        require(votingPower[msg.sender] >= amount, "Insufficient");
        votingPower[msg.sender] -= amount;
        votingPower[to] += amount;
    }

    /// @notice Mint voting tokens (admin)
    function mintVotingPower(address to, uint256 amount) external {
        require(msg.sender == guardian, "Not guardian");
        votingPower[to] += amount;
    }

    /// @notice Cancel proposal
    /// @dev VULNERABILITY: State machine violation - can cancel executed proposals
    function cancel(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        require(msg.sender == p.proposer || msg.sender == guardian, "Unauthorized");
        // Missing: require(p.state != ProposalState.Executed)
        p.state = ProposalState.Defeated;
    }
}
