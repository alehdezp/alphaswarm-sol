# Multi-Tier Benchmark Strategy

## Overview

VKG uses a three-tier benchmark strategy to ensure comprehensive validation across different vulnerability complexity levels.

## Tier 1: DVDeFi (CTF-Style)

**Purpose**: Primary detection validation on well-understood CTF challenges

**Dataset**: Damn Vulnerable DeFi v4 (13 challenges)

**Characteristics**:
- Clear success/failure criteria
- Foundry test suite for verification
- Single dominant vulnerability per challenge
- Increasing difficulty (1-6)

**Targets**:
| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| Detection Rate | 70% | 80% | 90% |
| Recall | 60% | 75% | 90% |

**When to Run**: Every PR, every push to main

**Location**: `benchmarks/dvdefi/`

## Tier 2: SmartBugs Curated

**Purpose**: Academic-standard validation on labeled vulnerabilities

**Dataset**: 69 curated contracts from SmartBugs

**Characteristics**:
- Ground truth labels from researchers
- Multiple vulnerability types per file
- Some older Solidity versions
- Real-world patterns

**Targets**:
| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| Detection Rate | 60% | 70% | 85% |
| False Positive Rate | < 25% | < 15% | < 10% |

**When to Run**: Weekly, release validation

**Location**: `benchmarks/smartbugs/` (TODO)

## Tier 3: Safe Set (False Positive Validation)

**Purpose**: Measure false positive rate on known-clean code

**Dataset**: 50+ audited, deployed contracts

**Sources**:
- OpenZeppelin Contracts v5
- Uniswap V3 Core
- AAVE V3 Core
- Compound V3
- Known-audited DeFi protocols

**Characteristics**:
- Production-deployed
- Professionally audited
- No known vulnerabilities
- Modern Solidity

**Targets**:
| Metric | Maximum |
|--------|---------|
| False Positive Rate | 15% |
| Critical FP Rate | 5% |

**When to Run**: Weekly, release validation

**Location**: `benchmarks/safe-set/` (TODO)

## Tier 4: Real-World Audits

**Purpose**: Professional-grade validation

**Dataset**: 6+ diverse protocol audits

**Sources**:
- Public audit reports
- Bug bounty findings
- Post-mortem analyses

**Characteristics**:
- Complex multi-contract systems
- Business logic vulnerabilities
- Edge cases
- Expert-validated

**Targets**:
| Metric | Target |
|--------|--------|
| Finding Coverage | 30% |
| Unique Insights | 10% |

**When to Run**: Monthly, major releases

**Location**: `benchmarks/real-world/` (TODO)

## Execution Schedule

| Tier | Frequency | Duration | Blocking |
|------|-----------|----------|----------|
| Tier 1 | Every PR | < 5 min | Yes |
| Tier 2 | Weekly | < 30 min | Release |
| Tier 3 | Weekly | < 30 min | Release |
| Tier 4 | Monthly | 2-4 hours | Major Release |

## CI Integration

### PR Checks

```yaml
# .github/workflows/benchmark.yml
jobs:
  tier1-dvd:
    runs-on: ubuntu-latest
    steps:
      - run: uv run alphaswarm benchmark run --suite dvd
      # Must pass for merge
```

### Release Validation

```yaml
# .github/workflows/release.yml
jobs:
  tier2-smartbugs:
    steps:
      - run: uv run alphaswarm benchmark run --suite smartbugs

  tier3-safe-set:
    steps:
      - run: uv run alphaswarm benchmark run --suite safe-set
      - run: |
          FP_RATE=$(cat results.json | jq '.summary.fp_rate')
          if (( $(echo "$FP_RATE > 0.15" | bc -l) )); then
            exit 1
          fi
```

## Metrics Dashboard

Available via: `vkg benchmark dashboard`

```
╔══════════════════════════════════════════════════════════════╗
║                   BSKG Benchmark Dashboard                     ║
╠══════════════════════════════════════════════════════════════╣
║ Tier 1: DVDeFi                                                ║
║   Detection: 84.6% (11/13) ✓ Target: 80%                     ║
║   Recall: 85.0%                                               ║
║                                                               ║
║ Tier 2: SmartBugs                                            ║
║   Detection: -- (not run)                                     ║
║   FP Rate: --                                                 ║
║                                                               ║
║ Tier 3: Safe Set                                              ║
║   FP Rate: -- (not run)                                       ║
║   Critical FPs: --                                            ║
║                                                               ║
║ Last Run: 2026-01-07 12:00:00 UTC                            ║
╚══════════════════════════════════════════════════════════════╝
```

## Adding New Benchmarks

### Adding to Tier 1/2

1. Create challenge YAML in appropriate directory
2. Follow LABELING.md protocol
3. Add to suite.yaml
4. Run validation: `vkg benchmark run --suite <name> --challenge <id>`

### Adding to Tier 3 (Safe Set)

1. Verify contract is audited/deployed
2. Confirm no known vulnerabilities
3. Add to safe-set manifest
4. Document audit source

### Adding to Tier 4 (Real-World)

1. Obtain audit report
2. Extract vulnerability findings
3. Create expected results YAML
4. Validate against report
5. Document methodology

---

*TIER_STRATEGY.md | Version 1.0 | 2026-01-07*
