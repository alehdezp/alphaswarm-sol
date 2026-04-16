// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title UnprotectedParametersTest
 * @notice Comprehensive test contract for 9 DeFi infrastructure semantic patterns
 *
 * This contract tests detection of unprotected writes to critical protocol parameters across:
 * - circuit-001: Circuit breaker (pause/unpause)
 * - governance-001: Governance parameters (quorum, voting delay, thresholds)
 * - tokenomics-001: Reward/emission/vesting parameters
 * - bridge-001: Cross-chain bridge configuration (relayers, endpoints)
 * - defi-001: DeFi risk parameters (liquidation, collateral, fees)
 * - emergency-001: Emergency recovery functions
 * - merkle-001: Merkle root updates (airdrops, whitelists)
 * - oracle-002: Oracle/price feed configuration
 * - treasury-001: Treasury/fee recipient addresses
 *
 * All patterns share the same core detection logic:
 *   writes_privileged_state OR writes_sensitive_config
 *   + has_access_gate: false
 *   + visibility: [public, external]
 */

// =============================================================================
// SECTION 1: Circuit Breaker (circuit-001-unprotected-pause)
// =============================================================================

contract CircuitBreakerTest {
    bool public paused;
    bool public circuitBreakerActive;
    bool public emergencyStop;
    bool public halted;

    // === TRUE POSITIVES ===

    // TP1: Standard pause function without access control
    function pause() external {
        paused = true;
    }

    // TP2: Unpause function without access control
    function unpause() external {
        paused = false;
    }

    // TP3: Boolean parameter pause
    function setPaused(bool _paused) external {
        paused = _paused;
    }

    // TP4: Alternative naming - circuit breaker
    function toggleCircuitBreaker() external {
        circuitBreakerActive = !circuitBreakerActive;
    }

    // === TRUE NEGATIVES ===

    // TN1: Pause WITH onlyOwner modifier
    address public owner = msg.sender;
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function pauseProtected() external onlyOwner {
        paused = true;
    }

    // TN2: View function (can't modify state)
    function isPaused() external view returns (bool) {
        return paused;
    }

    // TN3: Internal function (not externally callable)
    function _pause() internal {
        paused = true;
    }

    // === VARIATIONS ===

    // VAR1: Different naming - emergency stop
    function activateEmergencyStop() external {
        emergencyStop = true;
    }

    // VAR2: Different naming - halt
    function halt() external {
        halted = true;
    }

    // VAR3: Protected with require check
    function unpauseWithRequire() external {
        require(msg.sender == owner, "Not authorized");
        paused = false;
    }
}

// =============================================================================
// SECTION 2: Governance (governance-001-unprotected-parameter-update)
// =============================================================================

contract GovernanceTest {
    uint256 public votingDelay;
    uint256 public votingPeriod;
    uint256 public proposalDelay;
    uint256 public governanceDelay;
    uint256 public quorum;
    uint256 public quorumBPS;
    uint256 public proposalThreshold;
    uint256 public executionDelay;
    address public timelock;

    // === TRUE POSITIVES ===

    // TP1: Voting delay setter without access control
    function setVotingDelay(uint256 _delay) external {
        votingDelay = _delay;
    }

    // TP2: Quorum setter without access control
    function setQuorum(uint256 _quorum) external {
        quorum = _quorum;
    }

    // TP3: Proposal threshold update
    function updateProposalThreshold(uint256 _threshold) external {
        proposalThreshold = _threshold;
    }

    // TP4: Execution delay modification
    function setExecutionDelay(uint256 _delay) external {
        executionDelay = _delay;
    }

    // === TRUE NEGATIVES ===

    address public governance = msg.sender;
    modifier onlyGovernance() {
        require(msg.sender == governance, "Not governance");
        _;
    }

    // TN1: Voting delay WITH governance modifier
    function setVotingDelayProtected(uint256 _delay) external onlyGovernance {
        votingDelay = _delay;
    }

    // TN2: View function
    function getVotingDelay() external view returns (uint256) {
        return votingDelay;
    }

    // TN3: Internal function
    function _setQuorum(uint256 _quorum) internal {
        quorum = _quorum;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - proposalDelay
    function setProposalDelay(uint256 _delay) external {
        proposalDelay = _delay;
    }

    // VAR2: Alternative naming - governanceDelay
    function updateGovernanceDelay(uint256 _delay) external {
        governanceDelay = _delay;
    }

    // VAR3: Alternative naming - quorumBPS (basis points)
    function setQuorumBPS(uint256 _bps) external {
        quorumBPS = _bps;
    }
}

// =============================================================================
// SECTION 3: Tokenomics (tokenomics-001-unprotected-reward-parameter)
// =============================================================================

contract TokenomicsTest {
    uint256 public rewardRate;
    uint256 public emissionRate;
    uint256 public inflationRate;
    uint256 public rewardPerBlock;
    uint256 public vestingAmount;
    uint256 public vestingDuration;

    // === TRUE POSITIVES ===

    // TP1: Reward rate setter without access control
    function setRewardRate(uint256 _rate) external {
        rewardRate = _rate;
    }

    // TP2: Emission rate modification
    function setEmissionRate(uint256 _rate) external {
        emissionRate = _rate;
    }

    // TP3: Inflation rate update
    function updateInflationRate(uint256 _rate) external {
        inflationRate = _rate;
    }

    // TP4: Vesting parameter modification
    function setVestingParams(uint256 _amount, uint256 _duration) external {
        vestingAmount = _amount;
        vestingDuration = _duration;
    }

    // === TRUE NEGATIVES ===

    address public rewardAdmin = msg.sender;
    modifier onlyRewardAdmin() {
        require(msg.sender == rewardAdmin, "Not admin");
        _;
    }

    // TN1: Reward rate WITH admin modifier
    function setRewardRateProtected(uint256 _rate) external onlyRewardAdmin {
        rewardRate = _rate;
    }

    // TN2: View function
    function currentRewardRate() external view returns (uint256) {
        return rewardRate;
    }

    // TN3: Internal function
    function _updateEmissionRate(uint256 _rate) internal {
        emissionRate = _rate;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - rewardPerBlock
    function setRewardPerBlock(uint256 _reward) external {
        rewardPerBlock = _reward;
    }

    // VAR2: Protected with require
    function setEmissionRateWithRequire(uint256 _rate) external {
        require(msg.sender == rewardAdmin, "Not authorized");
        emissionRate = _rate;
    }
}

// =============================================================================
// SECTION 4: Bridge (bridge-001-unprotected-configuration)
// CRITICAL: Poly Network ($611M), Ronin ($625M), Nomad ($190M), Wormhole ($325M)
// =============================================================================

contract BridgeTest {
    address public relayer;
    address public validator;
    address public bridgeOperator;
    address public bridgeEndpoint;
    address public l1Messenger;
    address public l2Handler;
    uint256 public chainId;

    // Cross-chain context markers
    bool private crossChainEnabled = true;

    // === TRUE POSITIVES ===

    // TP1: Relayer address update without access control (Poly Network-style)
    function setRelayer(address _relayer) external {
        relayer = _relayer;
    }

    // TP2: Bridge endpoint modification (Nomad-style)
    function setBridgeEndpoint(address _endpoint) external {
        bridgeEndpoint = _endpoint;
    }

    // TP3: Chain configuration update
    function updateChainConfig(uint256 _chainId, address _handler) external {
        chainId = _chainId;
        l2Handler = _handler;
    }

    // TP4: Validator set modification (Ronin-style)
    function setValidator(address _validator) external {
        validator = _validator;
    }

    // === TRUE NEGATIVES ===

    address public bridgeAdmin = msg.sender;
    modifier onlyBridgeAdmin() {
        require(msg.sender == bridgeAdmin, "Not bridge admin");
        _;
    }

    // TN1: Relayer update WITH admin modifier
    function setRelayerProtected(address _relayer) external onlyBridgeAdmin {
        relayer = _relayer;
    }

    // TN2: View function
    function getRelayer() external view returns (address) {
        return relayer;
    }

    // TN3: Internal function
    function _updateValidator(address _validator) internal {
        validator = _validator;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - bridgeOperator
    function setBridgeOperator(address _operator) external {
        bridgeOperator = _operator;
    }

    // VAR2: Alternative naming - l1Messenger
    function setL1Messenger(address _messenger) external {
        l1Messenger = _messenger;
    }

    // VAR3: Protected with multisig check
    address public multisig = msg.sender;
    function setRelayerMultisig(address _relayer) external {
        require(msg.sender == multisig, "Not multisig");
        relayer = _relayer;
    }
}

// =============================================================================
// SECTION 5: DeFi Risk Parameters (defi-001-unprotected-risk-parameter)
// =============================================================================

contract DeFiRiskTest {
    uint256 public liquidationThreshold;
    uint256 public collateralRatio;
    uint256 public collateralFactor;
    uint256 public LTV;  // Loan-to-Value
    uint256 public maxLTV;
    uint256 public protocolFee;
    uint256 public borrowFee;

    // === TRUE POSITIVES ===

    // TP1: Liquidation threshold update without access control
    function setLiquidationThreshold(uint256 _threshold) external {
        liquidationThreshold = _threshold;
    }

    // TP2: Collateral ratio modification
    function setCollateralRatio(uint256 _ratio) external {
        collateralRatio = _ratio;
    }

    // TP3: LTV parameter update
    function updateLTV(uint256 _ltv) external {
        LTV = _ltv;
    }

    // TP4: Fee parameter modification
    function setProtocolFee(uint256 _fee) external {
        protocolFee = _fee;
    }

    // === TRUE NEGATIVES ===

    address public riskManager = msg.sender;
    modifier onlyRiskManager() {
        require(msg.sender == riskManager, "Not risk manager");
        _;
    }

    // TN1: Liquidation threshold WITH risk manager modifier
    function setLiquidationThresholdProtected(uint256 _threshold) external onlyRiskManager {
        liquidationThreshold = _threshold;
    }

    // TN2: View function
    function getLTV() external view returns (uint256) {
        return LTV;
    }

    // TN3: Internal function
    function _setCollateralFactor(uint256 _factor) internal {
        collateralFactor = _factor;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - collateralFactor
    function setCollateralFactor(uint256 _factor) external {
        collateralFactor = _factor;
    }

    // VAR2: Alternative naming - maxLTV
    function setMaxLTV(uint256 _maxLtv) external {
        maxLTV = _maxLtv;
    }

    // VAR3: Alternative naming - borrowFee
    function updateBorrowFee(uint256 _fee) external {
        borrowFee = _fee;
    }
}

// =============================================================================
// SECTION 6: Emergency Recovery (emergency-001-unprotected-recovery)
// =============================================================================

contract EmergencyRecoveryTest {
    mapping(address => uint256) public balances;

    // === TRUE POSITIVES ===

    // TP1: Emergency withdraw without access control
    function emergencyWithdraw(address token, uint256 amount) external {
        // Affects user funds + writes state
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // TP2: Rescue tokens function
    function rescueTokens(address token) external {
        // Transfers value out
        payable(msg.sender).transfer(address(this).balance);
    }

    // TP3: Recover ETH function
    function recoverETH() external {
        payable(msg.sender).transfer(address(this).balance);
    }

    // TP4: Sweep function
    function sweep(address recipient) external {
        balances[recipient] += address(this).balance;
        payable(recipient).transfer(address(this).balance);
    }

    // === TRUE NEGATIVES ===

    address public emergencyAdmin = msg.sender;
    modifier onlyEmergencyAdmin() {
        require(msg.sender == emergencyAdmin, "Not admin");
        _;
    }

    // TN1: Emergency withdraw WITH admin modifier
    function emergencyWithdrawProtected(address token, uint256 amount) external onlyEmergencyAdmin {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // TN2: View function
    function canRecover() external view returns (bool) {
        return address(this).balance > 0;
    }

    // TN3: Internal recovery function
    function _rescue() internal {
        payable(emergencyAdmin).transfer(address(this).balance);
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - drain
    function drain() external {
        payable(msg.sender).transfer(address(this).balance);
    }

    // VAR2: Alternative naming - extractFunds
    function extractFunds() external {
        balances[msg.sender] += address(this).balance;
    }

    receive() external payable {}
}

// =============================================================================
// SECTION 7: Merkle Root (merkle-001-unprotected-root-update)
// =============================================================================

contract MerkleRootTest {
    bytes32 public merkleRoot;
    bytes32 public airdropRoot;
    bytes32 public whitelistRoot;
    bytes32 public claimRoot;
    bytes32 public proofRoot;

    // === TRUE POSITIVES ===

    // TP1: Merkle root setter without access control
    function setMerkleRoot(bytes32 _root) external {
        merkleRoot = _root;
    }

    // TP2: Update root function
    function updateRoot(bytes32 _root) external {
        merkleRoot = _root;
    }

    // TP3: Airdrop root setter
    function setAirdropRoot(bytes32 _root) external {
        airdropRoot = _root;
    }

    // TP4: Whitelist root modification
    function updateWhitelistRoot(bytes32 _root) external {
        whitelistRoot = _root;
    }

    // === TRUE NEGATIVES ===

    address public merkleAdmin = msg.sender;
    modifier onlyMerkleAdmin() {
        require(msg.sender == merkleAdmin, "Not admin");
        _;
    }

    // TN1: Merkle root WITH admin modifier
    function setMerkleRootProtected(bytes32 _root) external onlyMerkleAdmin {
        merkleRoot = _root;
    }

    // TN2: View function
    function currentRoot() external view returns (bytes32) {
        return merkleRoot;
    }

    // TN3: Internal function
    function _setRoot(bytes32 _root) internal {
        merkleRoot = _root;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - claimRoot
    function setClaimRoot(bytes32 _root) external {
        claimRoot = _root;
    }

    // VAR2: Alternative naming - proofRoot
    function updateProofRoot(bytes32 _root) external {
        proofRoot = _root;
    }

    // VAR3: Protected with require
    function setMerkleRootWithRequire(bytes32 _root) external {
        require(msg.sender == merkleAdmin, "Not authorized");
        merkleRoot = _root;
    }
}

// =============================================================================
// SECTION 8: Oracle/Price Feed (oracle-002-unprotected-feed-update)
// =============================================================================

contract OracleFeedTest {
    address public oracle;
    address public priceFeed;
    address public priceSource;
    address public chainlinkOracle;
    uint256 public priceMultiplier;
    uint256 public oracleDecimals;

    // === TRUE POSITIVES ===

    // TP1: Oracle address setter without access control
    function setOracle(address _oracle) external {
        oracle = _oracle;
    }

    // TP2: Price feed update
    function updatePriceFeed(address _feed) external {
        priceFeed = _feed;
    }

    // TP3: Price source modification
    function setPriceSource(address _source) external {
        priceSource = _source;
    }

    // TP4: Price multiplier update
    function setPriceMultiplier(uint256 _multiplier) external {
        priceMultiplier = _multiplier;
    }

    // === TRUE NEGATIVES ===

    address public oracleAdmin = msg.sender;
    modifier onlyOracleAdmin() {
        require(msg.sender == oracleAdmin, "Not admin");
        _;
    }

    // TN1: Oracle setter WITH admin modifier
    function setOracleProtected(address _oracle) external onlyOracleAdmin {
        oracle = _oracle;
    }

    // TN2: View function
    function getOracle() external view returns (address) {
        return oracle;
    }

    // TN3: Internal function
    function _updatePriceFeed(address _feed) internal {
        priceFeed = _feed;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - chainlinkOracle
    function setChainlinkOracle(address _oracle) external {
        chainlinkOracle = _oracle;
    }

    // VAR2: Oracle decimals configuration
    function setOracleDecimals(uint256 _decimals) external {
        oracleDecimals = _decimals;
    }

    // VAR3: Protected with multisig
    address public oracleMultisig = msg.sender;
    function setOracleMultisig(address _oracle) external {
        require(msg.sender == oracleMultisig, "Not multisig");
        oracle = _oracle;
    }
}

// =============================================================================
// SECTION 9: Treasury/Fee Recipient (treasury-001-unprotected-recipient-update)
// =============================================================================

contract TreasuryRecipientTest {
    address public treasury;
    address public feeRecipient;
    address public feeCollector;
    address public revenueRecipient;
    uint256 public feeRate;
    uint256 public treasuryFee;

    // === TRUE POSITIVES ===

    // TP1: Treasury address setter without access control
    function setTreasury(address _treasury) external {
        treasury = _treasury;
    }

    // TP2: Fee recipient update
    function updateTreasuryRecipient(address _recipient) external {
        treasury = _recipient;
    }

    // TP3: Fee collector modification
    function setFeeCollector(address _collector) external {
        feeCollector = _collector;
    }

    // TP4: Fee rate update (affects revenue)
    function setFeeRate(uint256 _rate) external {
        feeRate = _rate;
    }

    // === TRUE NEGATIVES ===

    address public treasuryAdmin = msg.sender;
    modifier onlyTreasuryAdmin() {
        require(msg.sender == treasuryAdmin, "Not admin");
        _;
    }

    // TN1: Treasury setter WITH admin modifier
    function setTreasuryProtected(address _treasury) external onlyTreasuryAdmin {
        treasury = _treasury;
    }

    // TN2: View function
    function getTreasury() external view returns (address) {
        return treasury;
    }

    // TN3: Internal function
    function _setFeeRecipient(address _recipient) internal {
        feeRecipient = _recipient;
    }

    // === VARIATIONS ===

    // VAR1: Alternative naming - revenueRecipient
    function setRevenueRecipient(address _recipient) external {
        revenueRecipient = _recipient;
    }

    // VAR2: Alternative naming - treasuryFee
    function updateTreasuryFee(uint256 _fee) external {
        treasuryFee = _fee;
    }

    // VAR3: Protected with governance
    address public governance = msg.sender;
    function setTreasuryGovernance(address _treasury) external {
        require(msg.sender == governance, "Not governance");
        treasury = _treasury;
    }
}
