# Tier B/C Scenario Library

**Purpose:** Catalog complex, real-world scenarios for Tier B/C evaluation. Use `TEMPLATE.md` for full details.

## Index

| scenario_id | vulnerability_class | source | protocol_type | scope | notes |
|---|---|---|---|---|---|
| tierbc-001 | flash-loan accounting | Damn Vulnerable DeFi (Side Entrance) | lending | cross-contract | repayment check bypass via deposit during callback |
| tierbc-002 | oracle manipulation | public audit report | dex/lending | cross-module | TWAP manipulation impacts collateral |
| tierbc-003 | governance takeover | public exploit report | governance | cross-contract | flash-loan voting power exploit |

## Notes

- Every scenario must include vulnerable, safe, and counterfactual cases.
- Each scenario must include VQL minimum set + cross-contract query.
- Provenance is required for all entries.
