# TraitForge - Code4rena Audit Report

## Contest Information

| Field | Value |
|-------|-------|
| Contest ID | 2024-07-traitforge |
| Audit Period | July 2024 |
| Prize Pool | $36,500 |
| Report URL | https://code4rena.com/reports/2024-07-traitforge |
| Findings Repo | https://github.com/code-423n4/2024-07-traitforge-findings |

## Protocol Overview

TraitForge is an NFT project with gamified tokenomics featuring minting, forging (merging), and nuking (burning for ETH) mechanics.

## Key Contracts

- `TraitForgeNft.sol` - Main NFT contract with mint/forge logic
- `NukeFund.sol` - Holds ETH for nuke rewards
- `EntityForging.sol` - Handles merge mechanics

## Vulnerability Summary

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| H-01 | High | Incorrect parameter ordering allows ETH theft | Access Control |
| H-02 | High | Reentrancy in nuke drains nukeFund | Reentrancy |
| M-01 | Medium | Frontrunnable forge operation | Front Running |

## References

- [Full Report](https://code4rena.com/reports/2024-07-traitforge)
- [GitHub Issues](https://github.com/code-423n4/2024-07-traitforge-findings/issues)
