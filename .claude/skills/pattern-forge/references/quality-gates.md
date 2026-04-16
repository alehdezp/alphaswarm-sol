# Quality Gates Reference

## Rating Thresholds

### Excellent (Gold Standard)

```
Precision >= 90%
Recall    >= 85%
Variation >= 85%
```

**What it means:**
- Minimal false positives (< 10% of findings are wrong)
- Catches vast majority of vulnerabilities (> 85%)
- Works across all common implementation styles

**Production use:**
- Can be used with minimal human review
- High confidence in findings
- Suitable for automated pipelines

### Ready (Silver Standard)

```
Precision >= 70%
Recall    >= 50%
Variation >= 60%
```

**What it means:**
- Acceptable false positive rate (< 30% of findings are wrong)
- Catches majority of vulnerabilities (> 50%)
- Works across most implementation styles

**Production use:**
- Requires human review of findings
- Good for audit assistance
- Not suitable for fully automated enforcement

### Draft (Bronze / Development)

```
Precision < 70% OR
Recall    < 50% OR
Variation < 60%
```

**What it means:**
- High false positive rate OR
- Misses many real vulnerabilities OR
- Too implementation-specific

**Production use:**
- NOT suitable for production
- Development/experimental only
- Requires significant improvement

---

## Metric Definitions

### Precision

```
Precision = True Positives / (True Positives + False Positives)
```

**Interpretation:**
- "When the pattern flags something, how often is it actually vulnerable?"
- High precision = few false alarms
- Low precision = crying wolf

**Example:**
```
Pattern flags 10 functions
- 7 are actually vulnerable (TP)
- 3 are safe code (FP)
Precision = 7/10 = 70%
```

### Recall

```
Recall = True Positives / (True Positives + False Negatives)
```

**Interpretation:**
- "Of all the actual vulnerabilities, how many does the pattern catch?"
- High recall = few missed vulnerabilities
- Low recall = false sense of security

**Example:**
```
There are 10 vulnerable functions total
- Pattern catches 8 (TP)
- Pattern misses 2 (FN)
Recall = 8/10 = 80%
```

### Variation Score

```
Variation Score = Variations Passed / Total Variations Tested
```

**Interpretation:**
- "How well does the pattern work across different implementation styles?"
- High variation = implementation-agnostic
- Low variation = relies on specific naming/style

**Variations to test:**
1. **Naming**: owner/admin/controller/governance/authority
2. **Modifier style**: onlyOwner vs require(msg.sender == owner)
3. **Access control**: Ownable vs AccessControl vs custom
4. **Visibility**: public vs external
5. **Inheritance**: direct vs inherited

**Example:**
```
Tested 5 naming variations
- owner: PASS
- admin: PASS
- controller: FAIL (not detected)
- governance: PASS
- authority: PASS
Variation = 4/5 = 80%
```

---

## Quality Gate Decision Matrix

| Precision | Recall | Variation | Result |
|-----------|--------|-----------|--------|
| >= 90% | >= 85% | >= 85% | EXCELLENT |
| >= 70% | >= 50% | >= 60% | READY |
| < 70% | any | any | DRAFT (precision fail) |
| any | < 50% | any | DRAFT (recall fail) |
| any | any | < 60% | DRAFT (variation fail) |

### Edge Cases

**High Precision, Low Recall:**
```
Precision: 95%
Recall: 40%
Rating: DRAFT
```
Pattern is accurate but too conservative. Needs to catch more cases.

**High Recall, Low Precision:**
```
Precision: 50%
Recall: 90%
Rating: DRAFT
```
Pattern catches everything but has too many false positives. Needs more `none` conditions.

**Good Precision/Recall, Low Variation:**
```
Precision: 85%
Recall: 80%
Variation: 50%
Rating: DRAFT
```
Pattern works but only with standard naming. Needs to be more semantic.

---

## Minimum Test Case Requirements

### For DRAFT evaluation:
- 3 True Positives
- 2 True Negatives
- 2 Variations

### For READY evaluation:
- 5 True Positives
- 3 True Negatives
- 3 Variations
- 2 Edge cases

### For EXCELLENT evaluation:
- 8+ True Positives
- 5+ True Negatives
- 5+ Variations
- 4+ Edge cases
- Renamed contract test (if available)

---

## False Positive Categories

When documenting false positives, categorize them:

### FP-1: Missing Guard Detection
```
Pattern flagged function with require(msg.sender == owner)
but didn't detect it as access control.
```
**Fix**: Check if has_access_gate is computed correctly

### FP-2: Safe Pattern Not Excluded
```
Pattern flagged function with ReentrancyGuard
but didn't exclude it.
```
**Fix**: Add `none` condition for the guard

### FP-3: Context Not Considered
```
Pattern flagged internal helper function
that's only called by protected functions.
```
**Fix**: Check visibility constraint, consider call chain

### FP-4: Edge Case Handling
```
Pattern flagged constructor which sets owner
but this is intentional initialization.
```
**Fix**: Add `none` condition for is_constructor

---

## False Negative Categories

When documenting false negatives, categorize them:

### FN-1: Condition Too Strict
```
Pattern requires writes_privileged_state
but function writes to a rate/fee variable
which has 'config' tag, not 'privileged'.
```
**Fix**: Use writes_sensitive_config or broader condition

### FN-2: Property Not Computed
```
Pattern checks for has_external_calls
but the call is through a library wrapper
and not detected.
```
**Fix**: May need builder enhancement, or use alternative signal

### FN-3: Implementation Variant
```
Pattern checks for modifier-based access
but this contract uses require() statements.
```
**Fix**: Use has_access_gate (covers both)

### FN-4: Cross-Contract Issue
```
Vulnerability spans two contracts
but pattern only analyzes single function.
```
**Fix**: May need path-based matching, or split pattern

---

## Improvement Strategies by Metric

### Improving Precision (Reducing FPs)

1. **Add `none` conditions:**
```yaml
none:
  - property: has_access_gate
    value: true
  - property: is_constructor
    value: true
  - property: has_reentrancy_guard
    value: true
```

2. **Add more `all` conditions:**
```yaml
all:
  - property: visibility
    op: in
    value: [public, external]
  - property: writes_privileged_state
    value: true
  - property: is_state_changing
    value: true  # Additional filter
```

3. **Use severity-appropriate conditions:**
```yaml
# For 'critical' severity, be more specific
- property: writes_privileged_state
  value: true
# Instead of
- property: writes_state
  value: true
```

### Improving Recall (Reducing FNs)

1. **Use `any` for alternatives:**
```yaml
any:
  - property: writes_privileged_state
    value: true
  - property: writes_sensitive_config
    value: true
```

2. **Remove overly restrictive conditions:**
```yaml
# Remove if too strict
- property: is_payable
  value: true  # Not all vulnerable functions are payable
```

3. **Check property computation:**
```bash
# Verify property is set correctly
uv run alphaswarm query "FIND functions" --path contract.sol --explain
```

### Improving Variation Score

1. **Use semantic properties only:**
```yaml
# BAD - name matching
- label:
    regex: ".*withdraw.*"

# GOOD - semantic property
- property: is_withdraw_like
  value: true
```

2. **Test across naming conventions:**
- owner/admin/controller/governance/authority
- withdraw/removeFunds/extractValue/pull

3. **Test different access control patterns:**
- Ownable (onlyOwner)
- AccessControl (onlyRole)
- Custom (require statements)

---

## Quality Certification Checklist

Before declaring a pattern READY or EXCELLENT:

### Pattern Design
- [ ] No function name regex matching
- [ ] No variable name string matching
- [ ] Uses semantic boolean properties
- [ ] Has at least one `none` condition
- [ ] Severity matches actual risk

### Test Coverage
- [ ] Minimum TP/TN requirements met
- [ ] Naming variations tested
- [ ] Code style variations tested
- [ ] Edge cases documented and tested

### Documentation
- [ ] Description explains the vulnerability
- [ ] Attack scenario provided
- [ ] Fix recommendations with code
- [ ] CWE/OWASP mapping

### Metrics
- [ ] Precision calculated and recorded
- [ ] Recall calculated and recorded
- [ ] Variation score calculated and recorded
- [ ] Status updated in pattern YAML

---

## Rating Assignment Authority

**pattern-tester agent** has FINAL authority on ratings:

1. Calculates metrics from test results
2. Applies rating thresholds strictly
3. Cannot be overridden by pattern-architect
4. Updates pattern YAML with official rating

**Pattern Forge** respects tester's rating:
- If tester says DRAFT, iterate
- If tester says READY, can accept or aim higher
- If tester says EXCELLENT, forge complete

**Manual override:**
- Only user can request accepting a lower rating
- "accept pattern as draft for now" = allowed
- Default behavior = iterate until target met
