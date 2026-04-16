# Cross-Chain Replay Attack

## Vulnerability Pattern

**Core Issue:** Message replay across bridge adapters due to per-adapter deduplication instead of global message tracking.

**Vulnerable Pattern:**
```solidity
mapping(bytes32 => mapping(address => bool)) public processedByAdapter;

function receiveMessage(bytes32 msgHash, address adapter) external {
    require(!processedByAdapter[msgHash][adapter], "Already processed");
    processedByAdapter[msgHash][adapter] = true;  // Only marks THIS adapter
    _execute(msgHash);
    // Attacker: replay same message through different adapter
}
```

**Why Vulnerable:**
- Deduplication is per-adapter, not global
- Same message can be executed via adapter A, then adapter B
- Cross-adapter replay extracts funds multiple times

**Safe Pattern:**
```solidity
mapping(bytes32 => bool) public processedGlobally;

function receiveMessage(bytes32 msgHash, address adapter) external {
    require(!processedGlobally[msgHash], "Already processed");
    processedGlobally[msgHash] = true;  // Global deduplication
    require(trustedAdapters[adapter], "Untrusted adapter");
    _execute(msgHash);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `checks_processed_status: true`
- `dedup_scope: per_adapter` (not global)
- `has_multiple_adapters: true`
- `supports_multiple_adapters: true`
- `has_global_message_tracking: false`

**Behavioral Signature:**
```
RECEIVE_MSG(A) -> CHECK_SEEN(A) -> MARK(A) -> RECEIVE_MSG(B) -> CHECK_SEEN(B) -> DOUBLE_PROCESS
```

(Short form: `RECEIVE_MSG(adapter_A) -> MARK_SEEN(adapter_A) -> REPLAY_VIA(adapter_B)`)

## Fix

1. Global message deduplication (not per-adapter)
2. Include source chain ID in message hash
3. Monotonic nonce per source chain
4. Verify adapter is in trusted set

**Real-world:** Nomad Bridge ($190M, 2022), Folks Finance (2024)
