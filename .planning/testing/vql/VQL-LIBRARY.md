# VQL Library (Tier B/C)

**Purpose:** Provide a minimum, security-focused query set and cross-contract path queries for Tier B/C scenarios.

## Usage Rules (Required)
- The **minimum query set MUST execute before any conclusions** are written.
- Transcripts MUST include the markers listed below so reviewers can confirm ordering.
- Each Tier B/C scenario family MUST run at least one cross-contract path query.

## Transcript Marker Requirements
- Begin the minimum set with: `[VQL_MIN_SET_START]`
- Emit a marker for each query: `[VQL-MIN-01]`, `[VQL-MIN-02]`, `[VQL-MIN-03]`, `[VQL-MIN-04]`, `[VQL-MIN-05]`
- End the minimum set with: `[VQL_MIN_SET_END]`
- Cross-contract queries MUST emit their marker (e.g., `[VQL-XCON-01]`).

## Evidence Capture Requirements (B10 core / B10.D / B10.E)
- Record minimum-set results under `VQL Minimum Set Output`.
- Record attack surface inventory under `Attack Surface` using VQL-MIN-01/02/05.
- Record cross-contract paths under `Cross-Contract Paths` using VQL-XCON-01 or VQL-XCON-02.
- If no paths exist, emit the marker and record `NO_PATHS`.

## B10 Coverage Map
| B10 item | Required VQL IDs | Evidence section |
|---|---|---|
| B10 core | VQL-MIN-01..05 | VQL Minimum Set Output |
| B10.D (Attack surface) | VQL-MIN-01, VQL-MIN-02, VQL-MIN-05 | Attack Surface |
| B10.E (Cross-contract) | VQL-XCON-01 or VQL-XCON-02 | Cross-Contract Paths |

## Minimum Query Set (Required)

| ID | Purpose | VQL Query | Marker | Expected Signal |
|---|---|---|---|---|
| VQL-MIN-01 | Attack surface discovery | `FIND functions WHERE visibility IN ['public','external'] AND (writes_state OR has_external_calls OR has_all_operations([TRANSFERS_VALUE_OUT]))` | `[VQL-MIN-01]` | Public/external functions that touch critical operations |
| VQL-MIN-02 | Privileged mutation inventory | `FIND functions WHERE has_any_operations([MODIFIES_OWNER, MODIFIES_ROLES, MODIFIES_CRITICAL_STATE])` | `[VQL-MIN-02]` | Functions that change ownership, roles, or critical state |
| VQL-MIN-03 | Access gate gaps | `FIND functions WHERE visibility IN ['public','external'] AND has_any_operations([MODIFIES_CRITICAL_STATE, TRANSFERS_VALUE_OUT]) AND NOT has_access_gate` | `[VQL-MIN-03]` | Public functions with critical writes and no access gate |
| VQL-MIN-04 | CEI/order risk | `FIND functions WHERE sequence_order(before: TRANSFERS_VALUE_OUT, after: WRITES_USER_BALANCE)` | `[VQL-MIN-04]` | Potential CEI violations |
| VQL-MIN-05 | External call + state write | `MATCH (f:Function)-[:CALLS_EXTERNAL]->(t:Function) WHERE f.writes_state RETURN f, t` | `[VQL-MIN-05]` | External callsites that also write state |

## Cross-Contract Path Queries (Required Per Scenario Family)

| ID | Purpose | VQL Query | Marker | Expected Signal |
|---|---|---|---|---|
| VQL-XCON-01 | Cross-contract call path | `MATCH (src:Function)-[:CALLS_EXTERNAL*1..3]->(dst:Function) WHERE src.visibility IN ['public','external'] AND src.contract != dst.contract RETURN src, dst` | `[VQL-XCON-01]` | Path crosses at least two contracts |
| VQL-XCON-02 | Cross-contract critical write | `MATCH (src:Function)-[:CALLS_EXTERNAL*1..3]->(dst:Function) WHERE dst.has_any_operations([MODIFIES_CRITICAL_STATE, TRANSFERS_VALUE_OUT]) AND src.contract != dst.contract RETURN src, dst` | `[VQL-XCON-02]` | External path reaches critical state mutation |

## Scenario-Specific Query Bundles
Add queries tailored to the vulnerability class. Include the query ID, purpose, and expected signal.

### Access Control Drift
- `FIND functions WHERE visibility IN ['public','external'] AND writes_state AND NOT has_access_gate`
- `MATCH (f:Function)-[:USES_MODIFIER]->(m:Modifier) WHERE m.label CONTAINS 'onlyOwner' RETURN f, m`

### Oracle Manipulation
- `FIND functions WHERE reads_oracle = true AND writes_state = true`
- `MATCH (f:Function)-[:READS_EXTERNAL_VALUE]->(o:Oracle) RETURN f, o`

### Reentrancy / Callback Risk
- `FIND functions WHERE has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]) AND NOT has_reentrancy_guard`
- `MATCH (f:Function)-[:CALLS_EXTERNAL]->(t:Function) WHERE t.visibility IN ['public','external'] RETURN f, t`

## Example Output (Illustrative)
```
[VQL_MIN_SET_START]
[VQL-MIN-01] 12 results: Vault.withdraw, Pool.flashLoan, Treasury.sweep...
[VQL-MIN-02] 5 results: Vault.setOwner, Pool.setFee, Treasury.setGuardian...
[VQL-MIN-03] 2 results: Pool.flashLoan, Treasury.emergencyWithdraw...
[VQL-MIN-04] 1 result: Vault.withdraw (TRANSFER before balance write)
[VQL-MIN-05] 4 results: Pool.flashLoan -> Borrower.execute, Vault.withdraw -> Token.transfer...
[VQL_MIN_SET_END]
[VQL-XCON-01] Path: Vault.withdraw -> Token.transfer -> Receiver.onTokenReceived
```

## Notes
- Adjust query predicates to match the current graph schema if property names differ.
- Minimum query set and cross-contract path queries are **non-negotiable** for Tier B/C runs.
