# Ground Truth Coverage Report

**Generated:** 2026-01-30T22:59:06.680867+00:00
**Manifest:** `configs/ground_truth_manifest.yaml`
**Manifest Hash:** `2c993086ec656e69...`
**Validator Version:** 1.0.0

---

## G3 Gate Status

**Status: PASS**

- Categories Validated: 14
- Categories Passing: 14
- Categories Failing: 0
- Total Sources: 5
- Total Findings: 488

## Category Coverage

| Category | Priority | Min Findings | Actual | Min Sources | Actual | Status |
|----------|----------|--------------|--------|-------------|--------|--------|
| access_control | critical | 10 | 67 | 2 | 5 | PASS |
| reentrancy | critical | 10 | 108 | 2 | 5 | PASS |
| arithmetic | high | 5 | 132 | 1 | 3 | PASS |
| logic | high | 5 | 22 | 2 | 3 | PASS |
| oracle | high | 3 | 6 | 1 | 2 | PASS |
| dos | medium | 3 | 31 | 1 | 3 | PASS |
| flash_loan | medium | 2 | 5 | 1 | 2 | PASS |
| frontrunning | medium | 3 | 56 | 1 | 2 | PASS |
| tx_origin | medium | 2 | 20 | 1 | 3 | PASS |
| unchecked_calls | medium | 3 | 115 | 1 | 2 | PASS |
| crypto | low | 1 | 3 | 1 | 1 | PASS |
| governance | low | 0 | 0 | 0 | 0 | PASS |
| token | low | 1 | 2 | 1 | 1 | PASS |
| upgrade | low | 1 | 2 | 1 | 1 | PASS |

## Source Validation

| Source | External | Snapshot | Citation | Categories | Findings | Status |
|--------|----------|----------|----------|------------|----------|--------|
| smartbugs-curated | Yes | Yes | Yes | 8 | 207 | PASS |
| cgt | Yes | Yes | Yes | 6 | 207 | PASS |
| code4rena | Yes | Yes | Yes | 6 | 29 | PASS |
| dvdefi-v3 | Yes | Yes | Yes | 5 | 15 | PASS |
| ethernaut | Yes | Yes | Yes | 9 | 30 | PASS |

## Coverage by Source

### SmartBugs Curated Dataset

- **ID:** smartbugs-curated
- **URL:** https://github.com/smartbugs/smartbugs-curated
- **Categories:** 8
- **Findings:** 207

### Consolidated Ground Truth for Smart Contracts

- **ID:** cgt
- **URL:** https://github.com/gsalzer/cgt
- **Categories:** 6
- **Findings:** 207

### Code4rena Public Contest Reports

- **ID:** code4rena
- **URL:** https://code4rena.com
- **Categories:** 6
- **Findings:** 29

### Damn Vulnerable DeFi v3

- **ID:** dvdefi-v3
- **URL:** https://www.damnvulnerabledefi.xyz/
- **Categories:** 5
- **Findings:** 15

### OpenZeppelin Ethernaut

- **ID:** ethernaut
- **URL:** https://ethernaut.openzeppelin.com/
- **Categories:** 9
- **Findings:** 30

## Validation Rules Compliance

| Rule | Description | Status |
|------|-------------|--------|
| B1 | External Ground Truth | PASS |
| B2 | Ground Truth Separation | PASS |
| B3 | No Circular Validation | PASS |
