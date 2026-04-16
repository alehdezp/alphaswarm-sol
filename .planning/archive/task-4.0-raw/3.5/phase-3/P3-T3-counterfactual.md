# [P3-T3] Counterfactual Generator

**Phase**: 3 - Iterative + Causal
**Task ID**: P3-T3
**Status**: NOT_STARTED
**Priority**: MEDIUM
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

Generate counterfactual scenarios that prove causality: "If X didn't happen, the vulnerability wouldn't exist." This provides concrete evidence for why findings are real vulnerabilities.

---

## Dependencies

### Required Before Starting
- [ ] [P3-T2] Causal Reasoning Engine

### Blocks These Tasks
- Phase 3 completion

---

## Objectives

1. Generate "what if" scenarios from causal graphs
2. Prove each counterfactual blocks the vulnerability
3. Produce fix recommendations from counterfactuals

---

## Technical Design

```python
@dataclass
class Counterfactual:
    """A counterfactual scenario."""
    id: str
    original: str  # What actually happens
    counterfactual: str  # What if this changed
    intervention: str  # Specific change
    blocks_vulnerability: bool
    expected_outcome: str
    code_diff: Optional[str]  # Suggested fix


class CounterfactualGenerator:
    """Generates counterfactuals from causal analysis."""

    def generate(self, causal_graph: CausalGraph) -> List[Counterfactual]:
        """Generate counterfactuals for each root cause."""
        counterfactuals = []

        for root in causal_graph.root_causes:
            cf = self._generate_for_root_cause(root, causal_graph)
            counterfactuals.append(cf)

        return counterfactuals

    def _generate_for_root_cause(self, root: RootCause, graph: CausalGraph) -> Counterfactual:
        """Generate counterfactual for a root cause."""

        # Use LLM to generate fix diff
        prompt = f"""Given this root cause of a vulnerability:

Root Cause: {root.description}
Intervention: {root.intervention}

Generate a minimal code change that would fix this.

Output as a diff:
```diff
- old code
+ new code
```
"""
        diff = self.llm.analyze(prompt)

        return Counterfactual(
            id=f"cf_{root.id}",
            original=root.description,
            counterfactual=f"What if {root.intervention}?",
            intervention=root.intervention,
            blocks_vulnerability=True,
            expected_outcome="Vulnerability prevented",
            code_diff=diff,
        )
```

---

## Success Criteria

- [ ] Counterfactual generation working
- [ ] Fix diffs generated
- [ ] Integration with causal engine

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
