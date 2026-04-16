# Pattern Forge Workflow Reference

## Quick Reference Decision Tree

```
START: User requests pattern
         │
         ▼
┌─────────────────────────┐
│ Is this a new pattern   │
│ or improving existing?  │
└──────────┬──────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
   [NEW]    [IMPROVE]
     │           │
     │           ├──► Read existing pattern YAML
     │           └──► Run pattern-tester for baseline
     │
     ▼
┌─────────────────────────┐
│ Parse target quality    │
│ from user request       │
└──────────┬──────────────┘
           │
           ├──► "excellent" / "best" / "gold" → target: excellent
           ├──► "ready" / "production" → target: ready
           └──► default → target: ready
           │
           ▼
┌─────────────────────────┐
│ FORGE LOOP START        │
│ iteration = 1           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ PHASE 1: DESIGN         │
│ Invoke: vkg-pattern-    │
│ architect               │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ PHASE 2: TEST           │
│ Invoke: pattern-tester  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ PHASE 3: EVALUATE       │
│ Parse test results      │
└──────────┬──────────────┘
           │
     ┌─────┴─────────────────────────────┐
     │                                   │
     ▼                                   ▼
[rating >= target]              [rating < target]
     │                                   │
     ▼                                   │
┌──────────┐                             │
│ COMPLETE │                             ▼
└──────────┘                  ┌─────────────────────┐
                              │ iteration < max?    │
                              └──────────┬──────────┘
                                   │
                             ┌─────┴─────┐
                             ▼           ▼
                          [YES]        [NO]
                             │           │
                             │           ▼
                             │    ┌──────────────┐
                             │    │ INCOMPLETE   │
                             │    │ Report best  │
                             │    └──────────────┘
                             │
                             ▼
                      ┌─────────────────────┐
                      │ Analyze failures    │
                      │ iteration++         │
                      │ Go to PHASE 1       │
                      └─────────────────────┘
```

## Prompt Templates

### First Iteration: vkg-pattern-architect

```
FORGE CYCLE: Iteration 1 of {max_iterations}
TARGET QUALITY: {target_level}

MISSION: Create a {severity} severity pattern to detect {vulnerability_type}

VULNERABILITY DESCRIPTION:
{description_from_user}

REQUIREMENTS:
1. Pattern MUST be implementation-agnostic
   - NO function name matching (withdraw, transfer, etc.)
   - NO variable name matching (owner, admin, etc.)
   - Use ONLY semantic properties (writes_privileged_state, has_access_gate, etc.)

2. Pattern MUST use `none` conditions
   - Exclude safe patterns (has guards, proper checks)
   - Reduce false positive surface area

3. Pattern MUST include:
   - Detailed description with attack scenario
   - fix_recommendations with code examples
   - CWE/OWASP mappings
   - attack_scenarios section

4. Pattern file location:
   - Place in vulndocs pattern folder: vulndocs/{category}/{subcategory}/patterns/
   - Must include `vulndoc:` field referencing parent vulndoc
   - Use ID format: <category>-<number>-<name>

KNOWN VULNERABLE EXAMPLES (if provided):
{vulnerable_examples}

KNOWN SAFE EXAMPLES (if provided):
{safe_examples}

After you create the pattern, I will invoke pattern-tester for brutal validation.
Pattern must achieve {target_level} status or I will return with specific failures to fix.
```

### Subsequent Iterations: vkg-pattern-architect

```
FORGE CYCLE: Iteration {n} of {max_iterations}
TARGET QUALITY: {target_level}
CURRENT STATUS: {current_rating}

MISSION: IMPROVE pattern {pattern_id} to achieve {target_level}

PREVIOUS TEST RESULTS:
- Precision: {precision}%
- Recall: {recall}%
- Variation Score: {variation_score}%
- Test Cases Run: {total_tests}

SPECIFIC FAILURES TO FIX:

FALSE POSITIVES (precision issue):
{list each false positive with explanation}
Example:
- transferOwnershipInternal() was flagged but has require(msg.sender == owner)
- safeWithdraw() was flagged but has ReentrancyGuard modifier

FALSE NEGATIVES (recall issue):
{list each false negative with explanation}
Example:
- unsafeWithdraw() not flagged despite state_write_after_external_call
- adminChange() not flagged despite writes_privileged_state without guard

VARIATION FAILURES:
{list naming/style variations that failed}
Example:
- Pattern did not detect 'controller' naming (only 'owner')
- Pattern did not detect AccessControl pattern (only Ownable)

REQUIRED CHANGES:
Based on failures above, make ONLY these specific changes:
1. {specific_change_1}
2. {specific_change_2}
...

DO NOT make unrelated changes. Focus on fixing the specific failures.
```

### Pattern-tester Invocation

```
BRUTAL TESTING REQUIRED
FORGE CYCLE: Iteration {n}
TARGET QUALITY: {target_level}

PATTERN TO TEST:
- ID: {pattern_id}
- Path: {pattern_path}
- Lens: {lens}
- Severity: {severity}

EXPECTED BEHAVIOR:
The pattern should:
- FLAG (True Positives): {description of vulnerable code}
- NOT FLAG (True Negatives): {description of safe code}

TESTING REQUIREMENTS:
1. Create MINIMUM test cases:
   - 5 True Positives (vulnerable code)
   - 3 True Negatives (safe code with guards)
   - 3 Naming variations (owner/admin/controller/governance)
   - 2 Code style variations (modifier vs require vs if)

2. Edge cases to test:
   {specific_edge_cases}

3. Test across projects:
   - Choose appropriate project from tests/projects/
   - Add functions to existing contracts, don't create new files

BE RUTHLESS:
- Assume the pattern is broken until proven otherwise
- Find every false positive you can create
- Find every vulnerability the pattern misses
- Test renamed contracts if available in tests/contracts/renamed/

REQUIRED OUTPUT FORMAT:
## Pattern Test Report: {pattern_id}

### Test Summary
- True Positives: X
- True Negatives: X
- False Positives: X (with function names)
- False Negatives: X (with function names)

### Metrics
- Precision: X.XX%
- Recall: X.XX%
- Variation Score: X.XX%

### Assigned Rating: draft|ready|excellent
Justification: {why this rating}

### Failures to Address (for next iteration)
1. {failure_1}
2. {failure_2}

### Files Created/Modified
- {file_1}
- {file_2}

### Pattern YAML Updates Made
- Updated status to: {rating}
- Updated test_coverage section
```

## Iteration Limits by Target

| Target | Max Iterations | Accept if Stuck At |
|--------|----------------|-------------------|
| `ready` | 3 | FAIL - must achieve ready |
| `excellent` | 5 | `ready` is acceptable fallback |

## Quality Gate Logic

```python
def quality_gate_decision(test_result, target, iteration, max_iter):
    rating = test_result.rating

    # Success conditions
    if rating == target:
        return "COMPLETE"
    if rating == "excellent" and target == "ready":
        return "EXCEEDED"
    if rating == "ready" and target == "excellent" and iteration >= max_iter:
        return "ACCEPTABLE_FALLBACK"

    # Failure conditions
    if iteration >= max_iter:
        if target == "ready" and rating == "draft":
            return "FAILED"
        return "MAX_ITERATIONS"

    # Continue iterating
    if has_actionable_failures(test_result):
        return "ITERATE"

    return "BLOCKED"  # No clear path to improvement
```

## Failure Analysis Patterns

### Precision Too Low (< 70%)

**Symptom**: Too many false positives

**Common Causes**:
1. Missing `none` condition for safe patterns
2. Pattern too broad (single condition)
3. Not checking for guards/modifiers

**Solutions**:
```yaml
# Add exclusion for safe patterns
none:
  - property: has_access_gate
    op: eq
    value: true
  - property: has_reentrancy_guard
    op: eq
    value: true
```

### Recall Too Low (< 50%)

**Symptom**: Missing real vulnerabilities

**Common Causes**:
1. Pattern too narrow
2. Required property not always computed
3. Missing `any` alternatives

**Solutions**:
```yaml
# Add alternative vulnerability signals
any:
  - property: state_write_after_external_call
    value: true
  - has_operation: TRANSFERS_VALUE_OUT
    sequence_after: WRITES_USER_BALANCE
```

### Variation Score Too Low (< 60%)

**Symptom**: Works with standard naming only

**Common Causes**:
1. Implicit name matching somewhere
2. Only tested with "owner" not "controller/admin"
3. Only tested with modifier not require

**Solutions**:
- Use semantic properties ONLY
- Test with renamed contracts
- Add tests for different access control styles

## State Machine

```
INITIALIZED ──► DESIGNING ──► TESTING ──► EVALUATING
      ▲              │            │             │
      │              │            │             │
      │              ▼            ▼             ▼
      │         [error]       [error]      ┌────┴────┐
      │              │            │        │         │
      │              ▼            ▼        ▼         ▼
      │           FAILED       FAILED   COMPLETE   ITERATE
      │                                              │
      └──────────────────────────────────────────────┘
```

## Reporting Templates

### Forge Complete Report

```markdown
## Forge Complete: {pattern_id}

**Target**: {target} | **Achieved**: {rating} | **Iterations**: {n}

### Final Metrics
| Metric | Value | Threshold |
|--------|-------|-----------|
| Precision | {X}% | >= {threshold}% |
| Recall | {Y}% | >= {threshold}% |
| Variation | {Z}% | >= {threshold}% |

### Quality Certification
- [x] Implementation-agnostic (no name matching)
- [x] False positives within bounds
- [x] Catches vulnerability variants
- [x] Tested across naming conventions
- [x] Edge cases handled

### Files
- Pattern: {pattern_path}
- Tests: {test_file_paths}
```

### Forge Incomplete Report

```markdown
## Forge Incomplete: {pattern_id}

**Target**: {target} | **Best Achieved**: {rating} | **Iterations**: {max}

### Current Metrics
| Metric | Value | Required |
|--------|-------|----------|
| Precision | {X}% | >= {threshold}% |
| Recall | {Y}% | >= {threshold}% |
| Variation | {Z}% | >= {threshold}% |

### Blocking Issues
1. {issue_1}
2. {issue_2}

### Recommendations
1. {recommendation_1}
2. {recommendation_2}

### Next Steps
- [ ] Manual review required
- [ ] Consider splitting pattern
- [ ] May need new builder properties

Pattern saved as {rating}. Manual improvement needed.
```
