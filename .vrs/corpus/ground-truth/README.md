# Ground Truth Corpus

This directory contains the external ground truth corpus for E2E validation of AlphaSwarm.sol vulnerability detection capabilities.

## Purpose

Ground truth data **MUST** come from sources OUTSIDE our framework to prevent circular validation. This corpus provides the "answer key" against which we measure precision and recall.

## Directory Structure

```
.vrs/corpus/ground-truth/
├── provenance.yaml              # Master registry with metadata and statistics
├── README.md                    # This file
│
├── code4rena/                   # Competitive audit findings
│   ├── sample-2024.yaml         # Consolidated findings from 10 contests
│   ├── 2024-07-traitforge/      # Contest-specific detailed data
│   │   ├── findings.yaml        # Structured findings with ground truth
│   │   └── source.md            # Report link and context
│   ├── 2024-06-badger-ebbtc/
│   ├── 2024-05-munchables/
│   ├── 2024-04-dyad/
│   └── 2024-03-revert-lend/
│
├── smartbugs/                   # Academic benchmark
│   ├── manifest.yaml            # Repository reference and subset
│   └── curated.yaml             # Full dataset (143 contracts, 207 findings)
│
├── cgt/                         # CGT (Consolidated Ground Truth)
│   └── consolidated.yaml        # 50 contracts, 207 findings
│
└── internal/                    # Internal annotations
    └── annotated/               # Test contracts with manual annotations
        ├── reentrancy-classic.yaml
        ├── no-access-gate.yaml
        ├── oracle-no-staleness.yaml
        └── tx-origin-auth.yaml
```

## IMP-B1/IMP-K2 Compliance

| Requirement | Target | Actual | Status |
|-------------|--------|--------|--------|
| Code4rena contests | >= 5 | 10 (5 detailed) | EXCEEDS |
| SmartBugs contracts | >= 3 | 143 | EXCEEDS |
| Internal annotated | >= 2 | 4 | EXCEEDS |
| Total findings | >= 30 | 448 | EXCEEDS |

## Vulnerability Class Coverage

The corpus includes ground truth for:

- **Reentrancy** (52 findings) - Classic, cross-function, read-only
- **Access Control** (24+ findings) - Missing checks, tx.origin, privilege escalation
- **Oracle Manipulation** (6+ findings) - Staleness, TWAP manipulation
- **Arithmetic** (74 findings) - Overflow, precision loss, donation attacks
- **Flash Loan** (4+ findings) - Price manipulation, collateral bypass
- **Front Running** (52 findings) - Sandwich attacks, MEV
- **Denial of Service** (9+ findings) - Gas limits, unbounded loops

## Usage

```python
# Load ground truth for a specific contract
import yaml

with open('.vrs/corpus/ground-truth/code4rena/2024-07-traitforge/findings.yaml') as f:
    ground_truth = yaml.safe_load(f)

# Compare against AlphaSwarm.sol findings
for finding in ground_truth['findings']:
    expected_class = finding['vulnerability_class']
    expected_location = finding['code_location']['file']
    # Match against tool output...
```

## Important Rules

1. **NEVER modify ground truth based on tool output** - If the tool disagrees, investigate the tool.
2. **External sources only** - All ground truth comes from Code4rena judges, academic papers, or manual expert annotation.
3. **Pin versions** - SmartBugs and CGT are pinned to specific commit hashes for reproducibility.

## Sources

| Source | Trust Level | Contracts | Findings |
|--------|-------------|-----------|----------|
| SmartBugs | High (Academic) | 143 | 207 |
| CGT | High (Academic) | 50 | 207 |
| Code4rena | High (Judge-confirmed) | 10 | 29 |
| Internal | Medium (Manual) | 4 | 5 |
| **Total** | - | **207** | **448** |

## References

- [SmartBugs Paper](https://doi.org/10.1145/3368089.3417065) - ACM ESEC/FSE 2020
- [CGT Paper](https://arxiv.org/pdf/2304.11624) - Consolidation of Ground Truth Sets
- [Code4rena Reports](https://code4rena.com/reports) - Public audit reports
