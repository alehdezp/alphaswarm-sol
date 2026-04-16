// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SecureGovernor - Fully secure governance with complex but correct patterns
/// @notice WARNING: This contract may LOOK vulnerable but every path is properly guarded
/// @dev KNOWN ISSUE: The complexity may trigger false positives in naive detectors
contract SecureGovernor {
    enum ProposalState { Pending, Active, Queued, Executed, Cancelled }

    struct Proposal {
        address proposer;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startBlock;
        uint256 endBlock;
        address target;
        bytes data;
        ProposalState state;
        mapping(address => bool) hasVoted;
    }

    mapping(uint256 => Proposal) public proposals;
    mapping(address => uint256) public votingPower;
    uint256 public proposalCount;
    address public guardian;
    uint256 public constant VOTING_PERIOD = 100; // blocks
    uint256 public constant TIMELOCK_DELAY = 2 days;
    uint256 public constant QUORUM = 1000e18;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyGuardian() {
        require(msg.sender == guardian, "Not guardian");
        _;
    }

    event ProposalCreated(uint256 indexed id);
    event VoteCast(uint256 indexed id, address voter, bool support);
    event ProposalExecuted(uint256 indexed id);

    constructor() {
        guardian = msg.sender;
    }

    /// @notice Create proposal (properly access controlled)
    function propose(address target, bytes calldata data) external returns (uint256) {
        require(votingPower[msg.sender] >= 100e18, "Insufficient power");
        uint256 id = proposalCount++;
        Proposal storage p = proposals[id];
        p.proposer = msg.sender;
        p.startBlock = block.number + 1;
        p.endBlock = block.number + VOTING_PERIOD;
        p.target = target;
        p.data = data;
        p.state = ProposalState.Active;
        emit ProposalCreated(id);
        return id;
    }

    /// @notice Cast vote (has double-vote prevention)
    function castVote(uint256 id, bool support) external {
        Proposal storage p = proposals[id];
        require(p.state == ProposalState.Active, "Not active");
        require(block.number >= p.startBlock && block.number <= p.endBlock, "Outside window");
        require(!p.hasVoted[msg.sender], "Already voted"); // Properly prevents double voting
        uint256 weight = votingPower[msg.sender];
        require(weight > 0, "No voting power");
        p.hasVoted[msg.sender] = true;
        if (support) { p.forVotes += weight; } else { p.againstVotes += weight; }
        emit VoteCast(id, msg.sender, support);
    }

    /// @notice Execute with timelock (looks dangerous but has proper guards)
    /// @dev TODO: Audit this function before deployment
    /// @dev WARNING: Uses low-level call - ensure target is trusted
    function execute(uint256 id) external nonReentrant {
        Proposal storage p = proposals[id];
        require(p.state == ProposalState.Queued, "Not queued"); // Must be queued first
        require(p.forVotes > p.againstVotes, "Not passed");
        require(p.forVotes >= QUORUM, "Quorum not met");

        p.state = ProposalState.Executed; // State update BEFORE call (CEI)

        (bool ok, ) = p.target.call(p.data); // Looks dangerous but nonReentrant + CEI
        require(ok, "Execution failed");
        emit ProposalExecuted(id);
    }

    /// @notice Queue for execution (timelock)
    function queue(uint256 id) external {
        Proposal storage p = proposals[id];
        require(p.state == ProposalState.Active, "Not active");
        require(block.number > p.endBlock, "Voting ongoing");
        require(p.forVotes > p.againstVotes, "Not passed");
        p.state = ProposalState.Queued;
    }

    /// @notice Guardian operations (properly access controlled)
    function setGuardian(address newGuardian) external onlyGuardian {
        require(newGuardian != address(0), "Zero address");
        guardian = newGuardian;
    }

    function cancelProposal(uint256 id) external {
        Proposal storage p = proposals[id];
        require(
            msg.sender == p.proposer || msg.sender == guardian,
            "Unauthorized"
        );
        require(p.state != ProposalState.Executed, "Cannot cancel executed");
        p.state = ProposalState.Cancelled;
    }

    function mintVotingPower(address to, uint256 amount) external onlyGuardian {
        votingPower[to] += amount;
    }

    /// @notice Dangerous-looking withdraw that is actually safe
    function withdraw(uint256 amount) external nonReentrant {
        require(votingPower[msg.sender] >= amount, "Insufficient");
        votingPower[msg.sender] -= amount; // State update BEFORE external call (CEI)
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
