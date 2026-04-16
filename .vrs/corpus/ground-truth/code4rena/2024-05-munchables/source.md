# Munchables - Code4rena Audit Report

## Contest Information

| Field | Value |
|-------|-------|
| Contest ID | 2024-05-munchables |
| Audit Period | May 2024 |
| Prize Pool | $24,500 |
| Report URL | https://code4rena.com/reports/2024-05-munchables |
| Findings Repo | https://github.com/code-423n4/2024-05-munchables-findings |

## Protocol Overview

Munchables is a GameFi protocol with NFT creatures that can be fed, evolved, and staked for rewards. The LockManager handles token locking for in-game benefits.

## Key Contracts

- `LockManager.sol` - Token locking and lockdrop management
- `RewardsManager.sol` - Staking rewards distribution
- `MunchablesNFT.sol` - Core NFT logic

## Vulnerability Summary

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| H-01 | High | Lock duration reset traps tokens | Logic Error |
| H-02 | High | Admin price manipulation in lockdrop | Oracle Manipulation |
| M-01 | Medium | DoS in reward calculation loop | Denial of Service |
| M-02 | Medium | Missing access control on setUSDPrice | Access Control |

## References

- [Full Report](https://code4rena.com/reports/2024-05-munchables)
- [GitHub Issues](https://github.com/code-423n4/2024-05-munchables-findings/issues)
