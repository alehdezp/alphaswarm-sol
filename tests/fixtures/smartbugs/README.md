# SmartBugs Curated Test Fixtures

Source: https://github.com/smartbugs/smartbugs-curated

This fixture contains contracts from the SmartBugs curated dataset,
which provides labeled vulnerabilities for benchmarking smart contract
analysis tools.

## Dataset Overview

SmartBugs is a curated dataset of Solidity smart contracts with known
vulnerabilities. Each contract is labeled with:
- Vulnerability type (reentrancy, access_control, arithmetic, etc.)
- Line numbers where vulnerabilities occur
- Expected detection outcomes

## Import Script

Run `scripts/import_smartbugs.sh` to fetch and prepare the dataset:

```bash
./scripts/import_smartbugs.sh
```

This will:
1. Clone the SmartBugs curated repository
2. Copy contracts organized by vulnerability type
3. Generate ground-truth.yaml files from labels

## Vulnerability Categories

The dataset includes vulnerabilities across these categories:
- **reentrancy** - Reentrancy vulnerabilities (external call before state update)
- **access_control** - Missing or weak access control
- **arithmetic** - Integer overflow/underflow
- **unchecked_low_level_calls** - Unchecked return values
- **denial_of_service** - DoS vulnerabilities
- **front_running** - Front-running susceptible patterns
- **time_manipulation** - Block timestamp dependence
- **short_addresses** - Short address attacks

## Ground Truth Format

Each vulnerability type directory contains:
- `src/` - Solidity contracts
- `ground-truth.yaml` - Labeled vulnerabilities with line numbers

## License

SmartBugs dataset is provided under academic use terms.
See: https://github.com/smartbugs/smartbugs-curated/blob/master/LICENSE

## References

- SmartBugs Paper: https://arxiv.org/abs/1910.10601
- SmartBugs GitHub: https://github.com/smartbugs/smartbugs
- SmartBugs Curated: https://github.com/smartbugs/smartbugs-curated
