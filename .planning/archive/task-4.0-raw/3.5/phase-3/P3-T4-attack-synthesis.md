# [P3-T4] Attack Path Synthesis

**Phase**: 3 - Iterative + Causal
**Task ID**: P3-T4
**Status**: NOT_STARTED
**Priority**: MEDIUM
**Estimated Effort**: 3-4 days
**Actual Effort**: -

---

## Executive Summary

Synthesize complete attack paths from iterative reasoning results. Combines multi-hop graph traversal with attack constructions to produce end-to-end exploit scenarios.

---

## Dependencies

### Required Before Starting
- [ ] [P3-T1] Iterative Query Engine
- [ ] [P2-T2] Attacker Agent

### Blocks These Tasks
- Phase 3 completion

---

## Objectives

1. Combine multi-function paths into attack chains
2. Synthesize complete exploit sequences
3. Estimate attack complexity and profitability
4. Generate PoC pseudocode

---

## Technical Design

```python
@dataclass
class AttackPath:
    """Complete attack path spanning multiple functions."""
    id: str
    entry_point: str  # Where attack starts
    steps: List["AttackStep"]
    exit_point: str  # Final vulnerable function
    total_complexity: str
    estimated_impact: str
    poc_code: Optional[str]


class AttackPathSynthesizer:
    """Synthesizes complete attack paths."""

    def synthesize(
        self,
        reasoning_result: "ReasoningResult",
        attack_constructions: List["AttackConstruction"],
    ) -> List[AttackPath]:
        """Synthesize attack paths from reasoning and attacks."""

        paths = []

        # For each vulnerable function found in reasoning
        for candidate in reasoning_result.final_candidates:
            # Find related attack constructions
            attacks = [a for a in attack_constructions if a.target_function == candidate]

            if attacks:
                # Build path from entry to vulnerable function
                path = self._build_path(candidate, attacks[0], reasoning_result)
                if path:
                    paths.append(path)

        return paths

    def _build_path(
        self,
        vulnerable_fn: str,
        attack: "AttackConstruction",
        reasoning: "ReasoningResult",
    ) -> Optional[AttackPath]:
        """Build complete attack path."""

        # Find entry points (external/public functions that lead here)
        entry_points = self._find_entry_points(vulnerable_fn, reasoning)

        if not entry_points:
            return None

        # Build steps from entry to vulnerable function
        steps = self._trace_path(entry_points[0], vulnerable_fn, reasoning)

        # Add attack steps
        steps.extend(attack.attack_steps)

        return AttackPath(
            id=f"path_{vulnerable_fn}",
            entry_point=entry_points[0],
            steps=steps,
            exit_point=vulnerable_fn,
            total_complexity=attack.feasibility.value,
            estimated_impact=attack.estimated_profit or "Unknown",
            poc_code=self._generate_poc(steps),
        )

    def _generate_poc(self, steps: List["AttackStep"]) -> str:
        """Generate PoC pseudocode."""
        poc_lines = ["// Attack PoC"]
        for i, step in enumerate(steps):
            poc_lines.append(f"// Step {i+1}: {step.description}")
            if step.transaction:
                poc_lines.append(step.transaction)
        return "\n".join(poc_lines)
```

---

## Success Criteria

- [ ] Multi-function path synthesis working
- [ ] PoC generation
- [ ] Integration with reasoning engine

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
