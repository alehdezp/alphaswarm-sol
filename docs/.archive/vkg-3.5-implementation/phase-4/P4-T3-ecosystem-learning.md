# [P4-T3] Ecosystem Learning

**Phase**: 4 - Cross-Project Transfer
**Task ID**: P4-T3
**Status**: NOT_STARTED
**Priority**: LOW
**Estimated Effort**: 3 days
**Actual Effort**: -

---

## Executive Summary

Implement continuous learning from the Solidity ecosystem - new exploits, audit reports, and CVEs. Keeps the adversarial KG up-to-date with emerging threats.

---

## Dependencies

### Required Before Starting
- [ ] [P4-T2] Transfer Engine
- [ ] [P0-T2] Adversarial Knowledge Graph

### Blocks These Tasks
- Phase 4 completion

---

## Objectives

1. Import exploits from Solodit/Rekt
2. Extract patterns from new audit reports
3. Track pattern effectiveness over time
4. Deprecate outdated patterns

---

## Technical Design

```python
class EcosystemLearner:
    """Learns from the Solidity ecosystem."""

    def __init__(self, adversarial_kg):
        self.adversarial_kg = adversarial_kg

    def import_from_solodit(self, data_path: Path) -> int:
        """Import exploits from Solodit export."""
        # Parse Solodit JSON/CSV
        # Extract patterns
        # Add to adversarial KG
        pass

    def import_from_rekt(self, data_path: Path) -> int:
        """Import from Rekt.news database."""
        pass

    def extract_pattern_from_audit(
        self,
        audit_report: str,
        vulnerable_code: str,
    ) -> Optional[AttackPattern]:
        """Extract attack pattern from audit finding."""
        # Use LLM to extract pattern
        prompt = f"""Extract an attack pattern from this audit finding.

Finding: {audit_report}

Vulnerable code:
```
{vulnerable_code}
```

Output the pattern in this format:
{{
    "name": "<pattern name>",
    "category": "<category>",
    "required_operations": ["<op1>", "<op2>"],
    "operation_sequence": "<regex pattern>",
    "preconditions": ["<condition>"],
    "false_positive_indicators": ["<indicator>"]
}}
"""
        response = self.llm.analyze(prompt, response_format="json")
        return self._parse_pattern(response)

    def track_effectiveness(self) -> Dict[str, float]:
        """Track pattern detection effectiveness."""
        # For each pattern, track:
        # - True positive rate
        # - False positive rate
        # - Usage frequency
        pass
```

---

## Success Criteria

- [ ] Solodit import working
- [ ] Pattern extraction from audits
- [ ] Effectiveness tracking

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
