# Vulnerability Labeling Protocol

## Purpose

This document defines the labeling protocol for benchmark contracts. Consistent labeling ensures accurate metrics and fair tool comparison.

## Label Categories

### Detection Status

| Status | Meaning |
|--------|---------|
| `detected` | BSKG correctly identifies the vulnerability |
| `not-detected` | BSKG fails to identify the vulnerability |
| `not-applicable` | Outside BSKG scope (e.g., purely off-chain compromise without on-chain or documented evidence) |
| `error` | BSKG errors during analysis |

### Vulnerability Types

Standardized vulnerability type identifiers:

| ID | Category | Description |
|----|----------|-------------|
| `reentrancy-*` | Reentrancy | Cross-function/contract reentrancy |
| `access-*` | Access Control | Missing/weak authorization |
| `oracle-*` | Oracle | Price/data manipulation |
| `dos-*` | DoS | Denial of service conditions |
| `mev-*` | MEV | Front-running, sandwich attacks |
| `upgrade-*` | Upgradeability | Proxy/upgrade vulnerabilities |
| `token-*` | Token | ERC20/721 edge cases |
| `flash-*` | Flash Loan | Flash loan exploits |
| `governance-*` | Governance | Voting/proposal manipulation |
| `callback-*` | Callback | Callback exploitation |
| `arbitrary-*` | Arbitrary Execution | Arbitrary calls/delegatecalls |

### Severity

| Level | Criteria |
|-------|----------|
| `critical` | Direct fund loss possible |
| `high` | Significant impact, exploitable |
| `medium` | Limited impact or complex exploit |
| `low` | Informational or edge case |

## Labeling Workflow

### 1. Initial Assessment

```yaml
# In challenge YAML
vulnerability:
  type: <type-id>
  description: |
    Clear description of the vulnerability
  cwe: CWE-XXX  # If applicable
  severity: critical|high|medium|low
```

### 2. Expected Detections

For each vulnerability, specify which patterns should match:

```yaml
expected_detections:
  - pattern: pattern-id
    contract: ContractName
    function: functionName
    property: property_that_matches
    confidence: high|medium|low
```

### 3. Function Classification

Classify all functions:

```yaml
expected_functions:
  vulnerable:
    - Contract.function1
    - Contract.function2
  safe:
    - Contract.function3
```

### 4. False Positive Exclusions

Document known non-issues:

```yaml
false_positive_exclusions:
  - description: "Why this match is not a vulnerability"
    reason: "Technical explanation"
```

## Quality Criteria

### Accurate Labels

1. **Verified exploitation**: Label only if exploit is proven (test or documented)
2. **Root cause identification**: Label the root cause, not symptoms
3. **Single responsibility**: One vulnerability type per expected detection

### Consistent Patterns

1. **Pattern coverage**: Every detectable vulnerability has an expected pattern
2. **Contract specificity**: Match to specific contract/function pairs
3. **Confidence calibration**: High = always match, Medium = context-dependent

### Documentation

1. **Clear descriptions**: Layperson-understandable vulnerability description
2. **Exploit summary**: One-line attack description
3. **Fix summary**: One-line remediation

## Dispute Resolution

If labeling is contested:

1. Document both interpretations
2. Review against source code
3. Consult audit reports if available
4. Default to "detected" if any pattern matches

## Metrics Calculation

### Detection Rate (Recall)

```
Detection Rate = Detected / (Detected + Not-Detected)
                = TP / (TP + FN)
```

Excludes `not-applicable` challenges.

### False Positive Rate

```
FP Rate = False Positives / Total Matches
```

Requires safe set with known-clean contracts.

### Precision

```
Precision = True Positives / (True Positives + False Positives)
```

## Review Process

1. **Initial label**: Create challenge YAML with labels
2. **Peer review**: Second person validates labels
3. **Tool validation**: Run BSKG to verify expected results
4. **Update on changes**: Re-validate after pattern/builder changes

## Examples

### Well-Labeled Challenge

```yaml
id: dvd-truster
name: Truster

vulnerability:
  type: arbitrary-external-call
  description: |
    flashLoan allows arbitrary call with pool as msg.sender,
    enabling approve() calls to steal tokens.
  cwe: CWE-94
  severity: critical

expected_detections:
  - pattern: arbitrary-call-target
    contract: TrusterLenderPool
    function: flashLoan
    property: arbitrary_call_target
    confidence: high

expected_functions:
  vulnerable:
    - TrusterLenderPool.flashLoan
  safe: []

verification:
  exploit_summary: "Borrow 0 tokens, pass approve() calldata"
  fix_summary: "Remove arbitrary call or restrict targets"

status: detected
```

---

*LABELING.md | Version 1.0 | 2026-01-07*
