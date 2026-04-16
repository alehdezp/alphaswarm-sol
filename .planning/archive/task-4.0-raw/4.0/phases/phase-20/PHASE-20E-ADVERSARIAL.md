# Phase 20.E: Adversarial and Stress Testing

**Goal:** Break the system under hostile or complex conditions to expose weaknesses.

---

## E.1 Adversarial Scenarios

1. **Rename resistance**: randomize identifiers and re-run detection.
2. **Proxy maze**: multiple delegatecalls and upgradeable contracts.
3. **Multi-contract dependency chains**: external call graph across repos.
4. **Token anomalies**: fee-on-transfer, rebasing, non-standard ERC20.
5. **Oracle edge cases**: stale, manipulated, or missing oracles.
6. **Governance abuse**: time-delayed proposals, flash-loan voting.
7. **Business-logic traps**: complex invariants, hidden state machines.
8. **Malicious docs**: poisoned knowledge sources with misleading guidance.

---

## E.1b Target Protocols and Attack Scenarios (Concrete)

Use these as concrete targets in the corpus (exact repo versions selected in Phase 20.B):

| Scenario | Target Protocols (Examples) | Attack Focus |
|----------|------------------------------|--------------|
| Reentrancy across modules | Compound, Curve, Yearn, Balancer | Cross-contract call chains, shared state |
| Oracle manipulation | Uniswap v2/v3, Curve, Aave, Maker | Spot vs TWAP, staleness, update race |
| Governance flash-loan | Compound Governor, Aave Governance | Flash-loan voting, proposal timing |
| Upgradeable proxy maze | OpenZeppelin UUPS, Transparent proxies | Delegatecall context, uninitialized impl |
| Bridge message replay | Nomad, Wormhole, Ronin | Replay, validator compromise, finality |
| Token anomalies | Fee-on-transfer tokens, rebasing tokens | Invariant violations, accounting drift |
| Business-logic abuse | NFT marketplaces, staking vaults | Hidden state machines, role abuse |
| MEV manipulation | DEX aggregators, AMMs | Sandwich, backrun, time-bandit attacks |

Each scenario must document **behavioral signatures** and **semantic operations** that are expected to trigger detection.

---

## E.1c Scenario Playbooks (Concrete Examples)

- **Uniswap v2/v3 price manipulation**: flash-loan a pool, distort spot price, exploit lending collateral. Expected ops: `READS_ORACLE`, `PERFORMS_DIVISION`, `TRANSFERS_VALUE_OUT`. Signature: `R:orc -> A:div -> X:out`.
- **Compound governance flash-loan**: borrow voting power, pass proposal in same block, drain funds. Ops: `CHECKS_PERMISSION`, `CALLS_EXTERNAL`, `MODIFIES_CRITICAL_STATE`.
- **Nomad bridge replay**: replay message to mint multiple times. Ops: `CALLS_EXTERNAL`, `MODIFIES_CRITICAL_STATE`, `TRANSFERS_VALUE_OUT`.
- **Proxy init takeover**: call unprotected initializer to seize admin role. Ops: `INITIALIZES_STATE`, `MODIFIES_OWNER`.
- **Curve reentrancy**: external call before state update with shared liquidity state. Ops: `CALLS_EXTERNAL`, `WRITES_USER_BALANCE`.
- **Fee-on-transfer token drift**: deposit/withdraw mismatch causes accounting loss. Ops: `READS_USER_BALANCE`, `WRITES_USER_BALANCE`, `TRANSFERS_VALUE_OUT`.
- **Business-logic invariant break**: hidden state machine allows unauthorized transitions. Ops: `VALIDATES_INPUT`, `MODIFIES_CRITICAL_STATE` (missing/weak).

---

## E.2 Stress Conditions

- Large repo (200+ contracts)
- Deep inheritance (10+ levels)
- Heavy use of libraries and linked contracts
- Repeated runs to test determinism

---

## E.2b Adversarial Behavior-First Checks

- Rename all identifiers and ensure detection is unchanged.
- Replace function names with misleading labels; detection must still trigger.
- Inject dead-code decoys to test false-positive resilience.

---

## E.2c Required Evidence Capture

For every adversarial run, record:

- Behavioral signatures observed
- Semantic operations triggered
- Evidence packet references (code locations + graph signals)
- Bead verdicts (confirmed/likely/uncertain/rejected)

Bead lifecycle must be recorded in `task/4.0/phases/phase-20/artifacts/BEAD_LOG.md`.

---

## E.3 Output Template

Store in `task/4.0/phases/phase-20/artifacts/ADVERSARIAL_RESULTS.md`:

```
- test: rename-resistance
  protocol: <name>
  success: true|false
  failures: <summary>
  root_cause: <analysis>
```

---

## E.4 Pass/Fail Criteria

- No catastrophic failures (crashes, corrupted results)
- Maintain >= 80% detection accuracy under obfuscation
- Any failure must include root-cause classification
