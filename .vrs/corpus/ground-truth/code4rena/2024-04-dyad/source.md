# DYAD - Code4rena Audit Report

## Contest Information

| Field | Value |
|-------|-------|
| Contest ID | 2024-04-dyad |
| Audit Period | April 2024 |
| Prize Pool | $36,500 |
| Report URL | https://code4rena.com/reports/2024-04-dyad |
| Findings Repo | https://github.com/code-423n4/2024-04-dyad-findings |

## Protocol Overview

DYAD is a decentralized stablecoin protocol using overcollateralized vaults. Users deposit collateral to mint DYAD stablecoins, with liquidation mechanisms to maintain solvency.

## Key Contracts

- `Vault.sol` - ERC4626 vault for collateral management
- `VaultManagerV2.sol` - Manages minting, redemption, and liquidation
- `DYAD.sol` - Stablecoin token

## Vulnerability Summary

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| H-01 | High | Vault share inflation attack | Arithmetic |
| H-02 | High | Undercollateralized minting via check bypass | Logic Error |
| M-01 | Medium | No slippage protection in liquidation | Front Running |
| M-02 | Medium | Reentrancy in withdraw with ERC777 | Reentrancy |

## References

- [Full Report](https://code4rena.com/reports/2024-04-dyad)
- [GitHub Issues](https://github.com/code-423n4/2024-04-dyad-findings/issues)
