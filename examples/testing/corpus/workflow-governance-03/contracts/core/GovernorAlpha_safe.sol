// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title GovernorAlpha (SAFE VARIANT)
contract GovernorAlpha_safe {
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
    uint256 public constant TIMELOCK_DELAY = 2 days;

    event ProposalCreated(uint256 indexed id, address proposer);
    event VoteCast(uint256 indexed id, address voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id);

    modifier onlyGuardian() {
        require(msg.sender == guardian, "Not guardian");
        _;
    }

    constructor() { guardian = msg.sender; }

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

    function castVote(uint256 proposalId, bool support) external {
        Proposal storage p = proposals[proposalId];
        require(p.state == ProposalState.Active, "Not active");
        require(block.timestamp <= p.endTime, "Voting ended");
        require(!p.hasVoted[msg.sender], "Already voted"); // FIXED
        uint256 weight = votingPower[msg.sender];
        require(weight > 0, "No voting power");
        p.hasVoted[msg.sender] = true;
        if (support) { p.forVotes += weight; } else { p.againstVotes += weight; }
        emit VoteCast(proposalId, msg.sender, support, weight);
    }

    function execute(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        require(block.timestamp > p.endTime + TIMELOCK_DELAY, "Timelock active"); // FIXED
        require(p.forVotes > p.againstVotes, "Not passed");
        require(p.forVotes >= QUORUM, "Quorum not met");
        require(p.state == ProposalState.Active, "Wrong state");
        p.state = ProposalState.Executed;
        (bool ok, ) = p.target.call(p.callData);
        require(ok, "Execution failed");
        emit ProposalExecuted(proposalId);
    }

    function setGuardian(address newGuardian) external onlyGuardian { // FIXED
        require(newGuardian != address(0), "Zero address");
        guardian = newGuardian;
    }

    function delegate(address to, uint256 amount) external {
        require(votingPower[msg.sender] >= amount, "Insufficient");
        votingPower[msg.sender] -= amount;
        votingPower[to] += amount;
    }

    function mintVotingPower(address to, uint256 amount) external onlyGuardian {
        votingPower[to] += amount;
    }

    function cancel(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        require(msg.sender == p.proposer || msg.sender == guardian, "Unauthorized");
        require(p.state != ProposalState.Executed, "Cannot cancel executed"); // FIXED
        p.state = ProposalState.Defeated;
    }
}
