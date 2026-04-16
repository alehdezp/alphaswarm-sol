# Revert Lend - Code4rena Audit Report

## Contest Information

| Field | Value |
|-------|-------|
| Contest ID | 2024-03-revert-lend |
| Audit Period | March 2024 |
| Prize Pool | $60,500 |
| Report URL | https://code4rena.com/reports/2024-03-revert-lend |
| Findings Repo | https://github.com/code-423n4/2024-03-revert-lend-findings |

## Protocol Overview

Revert Lend is a lending protocol built on Uniswap V3 LP positions. Users can use their Uniswap V3 NFT positions as collateral to borrow assets, with automated position management via transformers.

## Key Contracts

- `V3Vault.sol` - Main vault managing collateralized positions
- `V3Oracle.sol` - TWAP-based oracle for position valuation
- `Transformers/` - Automated position management contracts

## Vulnerability Summary

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| H-01 | High | TWAP oracle manipulation via flash loan | Oracle Manipulation |
| H-02 | High | Reentrancy in transform drains collateral | Reentrancy |
| M-01 | Medium | Missing permission check on setTransformer | Access Control |
| M-02 | Medium | Precision loss in interest calculation | Arithmetic |
| M-03 | Medium | Flash loan bypasses liquidation check | Flash Loan |

## References

- [Full Report](https://code4rena.com/reports/2024-03-revert-lend)
- [GitHub Issues](https://github.com/code-423n4/2024-03-revert-lend-findings/issues)
