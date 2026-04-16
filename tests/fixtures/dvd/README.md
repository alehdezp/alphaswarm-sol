# Damn Vulnerable DeFi Test Fixtures

Source: https://github.com/tinchoabbate/damn-vulnerable-defi

These fixtures contain known vulnerabilities from the Damn Vulnerable DeFi challenges.
Ground truth is derived from the official solutions.

## Challenges Included

1. **naive-receiver** - Flash loan fee drain (anyone can trigger flash loans on behalf of receivers)
2. **side-entrance** - Accounting manipulation via flash loan (deposit during flash loan callback)

## Ground Truth Source

The vulnerabilities and exploit paths are documented in:
- Official DVD repository: https://github.com/tinchoabbate/damn-vulnerable-defi
- Official challenge solutions: https://www.damnvulnerabledefi.xyz/

## License

Original contracts by @tinchoabbate under MIT license.

## Usage

Each challenge directory contains:
- `src/` - Solidity contracts
- `ground-truth.yaml` - Documented vulnerabilities with expected detection criteria
