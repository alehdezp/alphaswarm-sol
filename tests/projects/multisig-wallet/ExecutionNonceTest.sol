// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// MULTISIG-001: Multisig Execution Without Replay Protection
// =============================================================================
// Tests for pattern multisig-001-execution-without-nonce
// Replaces auth-078 (regex-based name matching)
//
// Pattern detects:
// - contract_has_multisig = true
// - public/external visibility
// - CALLS_EXTERNAL or CALLS_UNTRUSTED operations
// - has_nonce_parameter = false
// - reads_nonce_state = false
// - writes_nonce_state = false
//
// Expected Improvement over auth-078:
// - Coverage: +50-70% (detects behavior, not names)
// - False Positives: -30-40% (semantic operations filter non-execution functions)
// =============================================================================

// =============================================================================
// TRUE POSITIVES: Should be flagged (10 cases)
// =============================================================================

contract VulnerableMultisig {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TP1: Standard execute without nonce
    function executeTransaction(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data));
        require(verifySignatures(txHash, signatures), "Invalid signatures");
        (bool success,) = to.call{value: value}(data);
        require(success, "Transaction failed");
    }

    // TP2: submitTransaction without nonce
    function submitTransaction(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data));
        require(verifySignatures(txHash, signatures), "Invalid signatures");
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    // TP3: confirmAndExecute without nonce check
    function confirmAndExecute(
        uint256 txId,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(txId, data));
        require(verifySignatures(txHash, signatures), "Invalid");
        (bool success,) = msg.sender.call(data);
        require(success);
    }

    // TP4: batchExecute without nonce
    struct Transaction {
        address to;
        uint256 value;
        bytes data;
    }

    function batchExecute(
        Transaction[] memory txs,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encode(txs));
        require(verifySignatures(txHash, signatures), "Invalid");
        for (uint i = 0; i < txs.length; i++) {
            (bool success,) = txs[i].to.call{value: txs[i].value}(txs[i].data);
            require(success);
        }
    }

    // TP5: executeAfterTimelock without nonce
    mapping(bytes32 => uint256) public timelocks;

    function executeAfterTimelock(
        bytes32 proposalId,
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        require(block.timestamp >= timelocks[proposalId], "Timelock");
        bytes32 txHash = keccak256(abi.encodePacked(proposalId, to, data));
        require(verifySignatures(txHash, signatures), "Invalid");
        (bool success,) = to.call(data);
        require(success);
    }

    // TP6: Alternative naming - exec
    function exec(
        address target,
        bytes memory payload,
        bytes[] memory sigs
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, payload));
        require(verifySignatures(hash, sigs), "Invalid");
        (bool success,) = target.call(payload);
        require(success);
    }

    // TP7: Alternative naming - perform
    function performTransaction(
        address dest,
        bytes calldata callData,
        bytes[] calldata sigs
    ) external {
        bytes32 h = keccak256(abi.encodePacked(dest, callData));
        require(verifySignatures(h, sigs), "Invalid");
        (bool ok,) = dest.call(callData);
        require(ok);
    }

    // TP8: Alternative naming - run
    function runMultisig(
        address a,
        bytes memory b,
        bytes[] memory c
    ) external {
        bytes32 d = keccak256(abi.encodePacked(a, b));
        require(verifySignatures(d, c), "Invalid");
        (bool e,) = a.call(b);
        require(e);
    }

    // TP9: Emergency execution without nonce
    function executeEmergency(
        address target,
        bytes memory data
    ) external {
        // Even emergency functions need replay protection!
        require(isEmergency(), "Not emergency");
        (bool success,) = target.call(data);
        require(success);
    }

    // TP10: Multicall without nonce
    function multicall(
        bytes[] memory calls,
        bytes[] memory signatures
    ) external {
        bytes32 hash = keccak256(abi.encode(calls));
        require(verifySignatures(hash, signatures), "Invalid");
        for (uint i = 0; i < calls.length; i++) {
            (bool success,) = address(this).delegatecall(calls[i]);
            require(success);
        }
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }

    function isEmergency() internal pure returns (bool) {
        return true;
    }
}

// =============================================================================
// TRUE NEGATIVES: Should NOT be flagged (8 cases)
// =============================================================================

contract SafeMultisigWithNonce {
    address[] public owners;
    uint256 public required;
    mapping(uint256 => bool) public usedNonces;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TN1: execute WITH nonce parameter
    function executeTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint256 nonce,  // Has nonce parameter
        bytes[] memory signatures
    ) external {
        require(!usedNonces[nonce], "Nonce used");
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data, nonce));
        require(verifySignatures(txHash, signatures), "Invalid");
        usedNonces[nonce] = true;
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract SafeMultisigWithNonceMapping {
    address[] public owners;
    uint256 public required;
    mapping(address => uint256) public nonces;  // Nonce state

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TN2: submitTransaction WITH nonce mapping read/write
    function submitTransaction(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        uint256 nonce = nonces[msg.sender]++;  // Reads and writes nonce
        bytes32 txHash = keccak256(abi.encodePacked(to, value, data, nonce));
        require(verifySignatures(txHash, signatures), "Invalid");
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract SafeMultisigWithExecutedFlag {
    address[] public owners;
    uint256 public required;
    mapping(bytes32 => bool) public executed;  // Executed flag

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TN3: confirmAndExecute WITH executed flag check
    function confirmAndExecute(
        uint256 txId,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 txHash = keccak256(abi.encodePacked(txId, data));
        require(!executed[txHash], "Already executed");  // Reads executed state
        require(verifySignatures(txHash, signatures), "Invalid");
        executed[txHash] = true;  // Writes executed state
        (bool success,) = msg.sender.call(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract SafeMultisigWithProposalTracking {
    address[] public owners;
    uint256 public required;
    mapping(uint256 => bool) public proposalExecuted;  // Proposal tracking

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TN4: executeAfterTimelock WITH proposal executed check
    mapping(bytes32 => uint256) public timelocks;

    function executeAfterTimelock(
        bytes32 proposalId,
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        uint256 id = uint256(proposalId);
        require(!proposalExecuted[id], "Already executed");  // Reads executed state
        require(block.timestamp >= timelocks[proposalId], "Timelock");
        bytes32 txHash = keccak256(abi.encodePacked(proposalId, to, data));
        require(verifySignatures(txHash, signatures), "Invalid");
        proposalExecuted[id] = true;  // Writes executed state
        (bool success,) = to.call(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract MultisigViewFunctions {
    address[] public owners;

    constructor(address[] memory _owners) {
        owners = _owners;
    }

    // TN5: View function - should NOT be flagged (is_view = true)
    function getTransactionHash(
        address to,
        uint256 value,
        bytes memory data
    ) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(to, value, data));
    }

    // TN6: Pure function - should NOT be flagged (is_pure = true)
    function verifySignatureFormat(bytes memory sig) external pure returns (bool) {
        return sig.length == 65;
    }
}

contract MultisigInternalHelpers {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // TN7: Internal function - should NOT be flagged (not public/external)
    function _executeInternal(
        address to,
        bytes memory data
    ) internal {
        (bool success,) = to.call(data);
        require(success);
    }

    // Public wrapper with proper access control
    function execute(address to, bytes memory data) external {
        require(msg.sender == owners[0], "Not owner");
        _executeInternal(to, data);
    }
}

contract NotMultisigSingleOwner {
    address public owner;

    constructor(address _owner) {
        owner = _owner;
    }

    // TN8: Single-owner execute - should NOT be flagged (contract_has_multisig = false)
    function executeTransaction(
        address to,
        uint256 value,
        bytes memory data
    ) external {
        require(msg.sender == owner, "Not owner");
        (bool success,) = to.call{value: value}(data);
        require(success);
    }
}

// =============================================================================
// EDGE CASES: Boundary conditions (7 cases)
// =============================================================================

contract EdgeCaseTwoStepExecution {
    address[] public owners;
    uint256 public required;
    uint256 public proposalCount;

    struct Proposal {
        address to;
        bytes data;
        bool executed;
    }

    mapping(uint256 => Proposal) public proposals;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE1: Two-step execution (propose is safe, execute might be vulnerable)
    function proposeTransaction(
        address to,
        bytes memory data
    ) external returns (uint256) {
        uint256 id = proposalCount++;
        proposals[id] = Proposal(to, data, false);
        return id;
    }

    // This should be flagged - no nonce in execute step
    function executeProposal(
        uint256 proposalId,
        bytes[] memory signatures
    ) external {
        Proposal storage prop = proposals[proposalId];
        require(!prop.executed, "Already executed");  // Has executed check - should NOT flag
        bytes32 hash = keccak256(abi.encodePacked(proposalId, prop.to, prop.data));
        require(verifySignatures(hash, signatures), "Invalid");
        prop.executed = true;
        (bool success,) = prop.to.call(prop.data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract EdgeCaseTimelockBasedNonce {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE2: Timelock-based "nonce" (weaker replay protection)
    // Should be flagged - timestamp is not a nonce
    mapping(bytes32 => uint256) public earliestExecution;

    function executeAfterTimestamp(
        bytes32 proposalId,
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        require(block.timestamp >= earliestExecution[proposalId], "Too early");
        bytes32 hash = keccak256(abi.encodePacked(proposalId, to, data));
        require(verifySignatures(hash, signatures), "Invalid");
        // No executed flag - can replay after timelock!
        (bool success,) = to.call(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract EdgeCaseSignatureBasedReplay {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE3: Signature-based replay protection (v,r,s parameters)
    // Pattern might not detect signature params as nonce
    // Should be flagged if signature replay protection not detected
    function executeWithSignatures(
        address to,
        uint256 value,
        bytes memory data,
        uint8[] memory v,
        bytes32[] memory r,
        bytes32[] memory s
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, value, data));
        require(verifyECDSA(hash, v, r, s), "Invalid signatures");
        // No nonce - signatures could be replayed!
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifyECDSA(
        bytes32 hash,
        uint8[] memory v,
        bytes32[] memory r,
        bytes32[] memory s
    ) internal view returns (bool) {
        return v.length >= required;
    }
}

contract EdgeCaseEIP712 {
    address[] public owners;
    uint256 public required;
    bytes32 public DOMAIN_SEPARATOR;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256("MultiSig"),
                keccak256("1"),
                block.chainid,
                address(this)
            )
        );
    }

    // EDGE4: EIP-712 with nonce in domain separator (not in function)
    // Should be flagged - no nonce tracking
    function executeEIP712(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("Transaction(address to,uint256 value,bytes data)"),
                to,
                value,
                keccak256(data)
            )
        );
        bytes32 hash = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        require(verifySignatures(hash, signatures), "Invalid");
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract EdgeCaseChainIDOnly {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE5: Chain ID-based replay protection (prevents cross-chain, not same-chain replay)
    // Should be flagged - no nonce for same-chain replays
    function executeWithChainId(
        address to,
        uint256 value,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(to, value, data, block.chainid));
        require(verifySignatures(hash, signatures), "Invalid");
        // ChainId prevents cross-chain replay but NOT same-chain replay!
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract EdgeCaseDeadlineParameter {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE6: Deadline parameter (NOT a nonce - prevents late execution, not replay)
    // Should be flagged - deadline is not replay protection
    function executeWithDeadline(
        address to,
        uint256 value,
        bytes memory data,
        uint256 deadline,  // Not a nonce!
        bytes[] memory signatures
    ) external {
        require(block.timestamp <= deadline, "Expired");
        bytes32 hash = keccak256(abi.encodePacked(to, value, data, deadline));
        require(verifySignatures(hash, signatures), "Invalid");
        // Can replay before deadline expires!
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

contract EdgeCaseDiamondFacet {
    address[] public owners;
    uint256 public required;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // EDGE7: Diamond facet execute function
    // Should be flagged - no nonce
    function executeFacet(
        address facet,
        bytes memory functionCall,
        bytes[] memory signatures
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(facet, functionCall));
        require(verifySignatures(hash, signatures), "Invalid");
        (bool success,) = facet.delegatecall(functionCall);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}

// =============================================================================
// VARIATION TESTS: Different implementations (6 cases)
// =============================================================================

// VAR1: Controller naming instead of owner
contract VariationControllerNaming {
    address[] public controllers;
    uint256 public threshold;

    constructor(address[] memory _controllers, uint256 _threshold) {
        controllers = _controllers;
        threshold = _threshold;
    }

    // Should be flagged - no nonce
    function executeAction(
        address target,
        bytes memory data,
        bytes[] memory approvals
    ) external {
        bytes32 hash = keccak256(abi.encodePacked(target, data));
        require(verifyApprovals(hash, approvals), "Insufficient approvals");
        (bool success,) = target.call(data);
        require(success);
    }

    function verifyApprovals(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= threshold;
    }
}

// VAR2: Guardian naming pattern
contract VariationGuardianNaming {
    address[] public guardians;
    uint256 public quorum;

    constructor(address[] memory _guardians, uint256 _quorum) {
        guardians = _guardians;
        quorum = _quorum;
    }

    // Should be flagged - no nonce
    function executeGuardianAction(
        address destination,
        bytes memory payload,
        bytes[] memory confirmations
    ) external {
        bytes32 digest = keccak256(abi.encodePacked(destination, payload));
        require(verifyConfirmations(digest, confirmations), "Quorum not met");
        (bool ok,) = destination.call(payload);
        require(ok);
    }

    function verifyConfirmations(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= quorum;
    }
}

// VAR3: Timelock + multisig pattern
contract VariationTimelockMultisig {
    address[] public signers;
    uint256 public requiredSignatures;
    uint256 public constant TIMELOCK = 2 days;

    struct QueuedTx {
        address target;
        bytes data;
        uint256 eta;
    }

    mapping(bytes32 => QueuedTx) public queue;

    constructor(address[] memory _signers, uint256 _required) {
        signers = _signers;
        requiredSignatures = _required;
    }

    function queueTransaction(
        address target,
        bytes memory data,
        bytes[] memory signatures
    ) external returns (bytes32) {
        bytes32 txHash = keccak256(abi.encodePacked(target, data));
        require(verifySignatures(txHash, signatures), "Invalid");
        uint256 eta = block.timestamp + TIMELOCK;
        queue[txHash] = QueuedTx(target, data, eta);
        return txHash;
    }

    // Should be flagged - no nonce, only timelock
    function executeQueuedTransaction(
        bytes32 txHash,
        bytes[] memory signatures
    ) external {
        QueuedTx memory tx = queue[txHash];
        require(block.timestamp >= tx.eta, "Timelock");
        require(verifySignatures(txHash, signatures), "Invalid");
        // No executed flag - can replay!
        (bool success,) = tx.target.call(tx.data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= requiredSignatures;
    }
}

// VAR4: Governor-style voting pattern
contract VariationGovernorVoting {
    address[] public voters;
    uint256 public votesRequired;

    struct Proposal {
        address target;
        bytes data;
        uint256 votes;
    }

    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;

    constructor(address[] memory _voters, uint256 _required) {
        voters = _voters;
        votesRequired = _required;
    }

    // Should be flagged - no executed flag
    function executeProposal(
        uint256 proposalId
    ) external {
        Proposal storage prop = proposals[proposalId];
        require(prop.votes >= votesRequired, "Insufficient votes");
        // No executed flag - can execute multiple times!
        (bool success,) = prop.target.call(prop.data);
        require(success);
    }
}

// VAR5: Gnosis Safe-style pattern
contract VariationGnosisSafeStyle {
    address[] public owners;
    uint256 public threshold;

    constructor(address[] memory _owners, uint256 _threshold) {
        owners = _owners;
        threshold = _threshold;
    }

    enum Operation { Call, DelegateCall }

    // Should be flagged - no nonce
    function execTransaction(
        address to,
        uint256 value,
        bytes memory data,
        Operation operation,
        bytes memory signatures
    ) external {
        bytes32 txHash = keccak256(
            abi.encode(to, value, data, operation)
        );
        require(checkSignatures(txHash, signatures), "Invalid");

        bool success;
        if (operation == Operation.Call) {
            (success,) = to.call{value: value}(data);
        } else {
            (success,) = to.delegatecall(data);
        }
        require(success);
    }

    function checkSignatures(bytes32 hash, bytes memory sigs) internal view returns (bool) {
        // Simplified - real Gnosis Safe has complex signature checking
        return sigs.length >= threshold * 65;
    }
}

// VAR6: Sequential transaction ID pattern (alternative to nonce)
contract VariationSequentialTxId {
    address[] public owners;
    uint256 public required;
    uint256 public nextTxId;
    mapping(uint256 => bool) public executed;

    constructor(address[] memory _owners, uint256 _required) {
        owners = _owners;
        required = _required;
    }

    // Should NOT be flagged - has executed tracking
    function executeSequential(
        uint256 txId,
        address to,
        bytes memory data,
        bytes[] memory signatures
    ) external {
        require(!executed[txId], "Already executed");  // Reads executed state
        bytes32 hash = keccak256(abi.encodePacked(txId, to, data));
        require(verifySignatures(hash, signatures), "Invalid");
        executed[txId] = true;  // Writes executed state
        (bool success,) = to.call(data);
        require(success);
    }

    function verifySignatures(bytes32 hash, bytes[] memory sigs) internal view returns (bool) {
        return sigs.length >= required;
    }
}
