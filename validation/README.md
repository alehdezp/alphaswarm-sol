# Real-World Validation (Phase 5)

This directory contains ground truth data for validating BSKG detection against real-world audit reports.

## Project Selection Criteria

Projects were selected based on:
1. **Public audit reports** from reputable auditors
2. **Accessible Solidity source code** (not just bytecode)
3. **Diverse protocol types** (lending, DEX, NFT, governance, etc.)
4. **Known vulnerabilities** documented in audit reports

## Selected Projects

| # | Project | Type | Auditor | Total | VKG-Detectable | Status |
|---|---------|------|---------|-------|----------------|--------|
| 1 | Compound V3 (Comet) | Lending | OpenZeppelin | 8 | 6 | ✓ Ground Truth |
| 2 | Uniswap V3 | DEX | ToB, ABDK | 9 | 8 | ✓ Ground Truth |
| 3 | Blur Exchange | NFT Marketplace | Spearbit, C4 | 10 | 8 | ✓ Ground Truth |
| 4 | ENS | Registry | OpenZeppelin, Consensys | 8 | 8 | ✓ Ground Truth |
| 5 | Yearn V3 | Yield Vault | ChainSecurity, StateMind | 9 | 7 | ✓ Ground Truth |
| 6 | LayerZero V2 | Bridge/Infra | Multiple | TBD | TBD | Pending |

## Directory Structure

```
validation/
├── README.md                 # This file
├── ground-truth/             # YAML ground truth files per project
│   ├── compound-v3.yaml
│   ├── uniswap-v3.yaml
│   ├── blur-exchange.yaml
│   ├── ens.yaml
│   ├── yearn-v3.yaml
│   └── layerzero-v2.yaml
├── results/                  # Validation results
│   └── <project>/
│       ├── vkg-findings.json
│       ├── match-results.json
│       └── metrics.json
└── scripts/                  # Validation scripts
    ├── validate_project.py
    └── aggregate_results.py
```

## Ground Truth Format

Each ground truth file follows this YAML schema:

```yaml
project_name: "compound-v3"
project_type: "lending"
audit_source: "OpenZeppelin"
audit_date: "2022-08-15"
audit_url: "https://..."
code_url: "https://github.com/compound-finance/comet"
code_commit: "abc123..."
solidity_version: "^0.8.15"

findings:
  - id: "C-01"
    title: "Critical finding title"
    category: "reentrancy"  # BSKG category
    severity: "critical"    # critical/high/medium/low/informational
    location:
      file: "src/Comet.sol"
      function: "supply"
      line_start: 145
      line_end: 180
    description: "..."
    recommendation: "..."
    vkg_should_find: true   # false for business logic, economic, etc.

notes: "Additional context..."
```

## BSKG Category Mapping

| BSKG Category | Audit Report Terms | BSKG Detectable |
|--------------|-------------------|----------------|
| `reentrancy` | reentrancy, cross-function reentrancy, read-only reentrancy | ✓ |
| `access_control` | access control, authorization, privilege, permission | ✓ |
| `oracle_manipulation` | oracle, price manipulation, stale price | ✓ |
| `mev_slippage` | MEV, slippage, sandwich, frontrunning, deadline | ✓ |
| `dos` | DoS, denial of service, unbounded loop, gas griefing | ✓ |
| `arithmetic` | overflow, underflow, integer overflow, rounding | ✓ |
| `signature` | ecrecover, replay attack, signature malleability | ✓ |
| `delegatecall` | delegatecall, proxy | ✓ |
| `upgrade_proxy` | upgrade, initializer, storage collision | ✓ |
| `timestamp` | block.timestamp, time manipulation | ✓ |
| `input_validation` | missing validation, zero address, input check | ✓ |
| `unchecked_return` | return value, unchecked transfer | ✓ |
| `flash_loan` | flash loan attack | ~ (partial) |
| `frontrunning` | front-running, transaction ordering | ~ (partial) |
| `business_logic` | semantic issues, protocol rules | ✗ OUT OF SCOPE |
| `economic` | market modeling, tokenomics | ✗ OUT OF SCOPE |
| `cryptographic` | complex crypto proofs, ZK | ✗ OUT OF SCOPE |
| `informational` | code quality, best practices | ✗ OUT OF SCOPE |

## Running Validation

```bash
# Validate a single project
uv run python validation/scripts/validate_project.py compound-v3

# Validate all projects
uv run python validation/scripts/validate_project.py --all

# Generate aggregate report
uv run python validation/scripts/aggregate_results.py
```

## Success Metrics

| Metric | Target | Minimum |
|--------|--------|---------|
| Precision | > 70% | > 60% |
| Recall | > 50% | > 40% |
| FP Rate | < 30% | < 40% |
| Projects | 6 | 3 |

## Important Notes

1. **Business logic bugs are OUT OF SCOPE**: BSKG cannot detect issues that require understanding business intent.

2. **Economic attacks are OUT OF SCOPE**: Flash loans, price manipulation strategies, etc. require market modeling.

3. **Matching is fuzzy**: Same file + close lines + related category = match.

4. **Audit reports are not perfect ground truth**: Auditors may miss things, and some findings may be subjective.

---

*Phase 5: Real-World Validation | BSKG 4.0*
