# [P1-T4] Intent Validation

**Phase**: 1 - Intent Annotation
**Task ID**: P1-T4
**Status**: NOT_STARTED
**Priority**: MEDIUM
**Estimated Effort**: 2 days
**Actual Effort**: -

---

## Executive Summary

Implement validation layer that cross-checks LLM-inferred intents against BSKG properties to detect hallucinations and ensure intent accuracy. This is critical for trusting intent-based analysis.

---

## Dependencies

### Required Before Starting
- [ ] [P1-T3] Builder Integration

### Blocks These Tasks
- Phase 1 completion gate

---

## Objectives

1. Cross-validate intent against semantic operations
2. Detect inconsistencies (e.g., "view_only" with WRITES_STATE)
3. Flag low-confidence intents for manual review
4. Compute intent reliability score

---

## Technical Design

### Validation Rules

```python
INTENT_VALIDATION_RULES = {
    BusinessPurpose.WITHDRAWAL: {
        "required_ops": ["TRANSFERS_VALUE_OUT"],
        "expected_ops": ["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.DEPOSITOR_ONLY, TrustLevel.PERMISSIONLESS],
    },
    BusinessPurpose.VIEW_ONLY: {
        "required_ops": [],
        "expected_ops": [],
        "forbidden_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE", "MODIFIES_CRITICAL_STATE"],
        "expected_trust": [TrustLevel.PERMISSIONLESS],
    },
    # ... more rules
}


class IntentValidator:
    """Validates LLM-inferred intents against BSKG properties."""

    def validate(self, fn_node: Node, intent: FunctionIntent) -> ValidationResult:
        """Validate intent against function properties."""
        issues = []
        score = 1.0

        # Get actual operations
        actual_ops = set(fn_node.properties.get("semantic_ops", []))

        # Get rules for this purpose
        rules = INTENT_VALIDATION_RULES.get(intent.business_purpose, {})

        # Check required operations
        required = set(rules.get("required_ops", []))
        if required and not required.issubset(actual_ops):
            missing = required - actual_ops
            issues.append(f"Missing required ops for {intent.business_purpose}: {missing}")
            score -= 0.3

        # Check forbidden operations
        forbidden = set(rules.get("forbidden_ops", []))
        if forbidden & actual_ops:
            present = forbidden & actual_ops
            issues.append(f"Has forbidden ops for {intent.business_purpose}: {present}")
            score -= 0.4

        # Check trust level consistency
        expected_trust = rules.get("expected_trust", [])
        if expected_trust and intent.expected_trust_level not in expected_trust:
            issues.append(f"Unexpected trust level: {intent.expected_trust_level}")
            score -= 0.2

        return ValidationResult(
            is_valid=len(issues) == 0,
            confidence_adjustment=score,
            issues=issues,
            recommendation="manual_review" if score < 0.7 else "accept",
        )
```

---

## Success Criteria

- [ ] Validation rules for all business purposes
- [ ] Catches obvious hallucinations
- [ ] Provides confidence adjustment
- [ ] Flags for manual review when needed

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
