# Tool Maximization Matrix

**Purpose:** Define required vs optional tools per scenario type to ensure evidence coverage and dedup mapping.

## Matrix

| Scenario Type | Required Tools | Optional Tools | Notes |
|---|---|---|---|
| Reentrancy | slither, aderyn, graph/vql | mythril | Require tool outputs cited in reasoning |
| Access Control | slither, aderyn, graph/vql | mythril | Require role/permission evidence |
| Oracle/Price | slither, graph/vql | aderyn, mythril | Require context pack and pricing inputs |
| Economic (Tier C) | graph/vql, context pack | slither, aderyn | Require economic model evidence |
| Cross-Contract | graph/vql, slither | aderyn, mythril | Require cross-contract path queries |
| Governance | graph/vql, slither | aderyn | Require role/privilege evidence |

## Enforcement Rules

- Required tools must run unless explicitly disabled in settings.
- If a required tool is disabled, emit a bypass marker and flag reduced evidence.
- Tool outputs must be cited in reasoning when applicable.

## Evidence Markers

- Tool status markers: `tools status`, `tools run`
- Tool usage markers: `slither`, `aderyn`, `mythril`
- Graph usage markers: `build-kg`, `query`
