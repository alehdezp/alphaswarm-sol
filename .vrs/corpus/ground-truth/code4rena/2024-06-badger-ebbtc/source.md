# Badger eBTC - Code4rena Audit Report

## Contest Information

| Field | Value |
|-------|-------|
| Contest ID | 2024-06-badger-ebbtc |
| Audit Period | June 2024 |
| Prize Pool | $100,000 |
| Report URL | https://code4rena.com/reports/2024-06-badger-ebbtc |
| Findings Repo | https://github.com/code-423n4/2024-06-badger-findings |

## Protocol Overview

eBTC is a decentralized synthetic Bitcoin on Ethereum, backed by staked ETH collateral. It uses a CDP-based system similar to Liquity for minting and managing positions.

## Key Contracts

- `EbtcBorrowingManager.sol` - Manages CDP operations and liquidations
- `CdpManager.sol` - Core CDP logic and redemption mechanism
- `PriceFeed.sol` - Chainlink oracle integration with L2 awareness

## Vulnerability Summary

| ID | Severity | Title | Class |
|----|----------|-------|-------|
| H-01 | High | Incorrect fee accounting causes bad debt | Arithmetic |
| M-01 | Medium | Oracle staleness bypass during sequencer downtime | Oracle Manipulation |
| M-02 | Medium | Flash loan redemption manipulation | Flash Loan |

## References

- [Full Report](https://code4rena.com/reports/2024-06-badger-ebbtc)
- [GitHub Issues](https://github.com/code-423n4/2024-06-badger-findings/issues)
