# [P2-T6] Agent Consensus Evolution

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T6
**Status**: NOT_STARTED
**Priority**: HIGH
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

Evolve the existing BSKG consensus system (src/true_vkg/agents/consensus.py) to integrate with the new adversarial agent architecture. Maintain backward compatibility while enabling the new attacker/defender paradigm.

---

## Dependencies

### Required Before Starting
- [ ] [P2-T5] Adversarial Arbiter
- Existing consensus.py

### Blocks These Tasks
- Phase 2 completion gate

---

## Objectives

1. Integrate ArbitrationResult with existing ConsensusResult
2. Support both old (4-agent voting) and new (adversarial) modes
3. Add configuration for choosing consensus mode
4. Deprecation path for old mode

---

## Technical Design

```python
class EnhancedAgentConsensus:
    """
    Enhanced consensus supporting both voting and adversarial modes.
    """

    def __init__(
        self,
        mode: str = "adversarial",  # "adversarial" or "voting"
        agents: Optional[List["VerificationAgent"]] = None,
    ):
        self.mode = mode
        if mode == "voting":
            self.voting_consensus = AgentConsensus(agents)
        elif mode == "adversarial":
            self.adversarial_system = AdversarialSystem()

    def analyze(self, subgraph: "SubGraph") -> "EnhancedConsensusResult":
        """Run consensus analysis."""
        if self.mode == "voting":
            return self._voting_analysis(subgraph)
        else:
            return self._adversarial_analysis(subgraph)

    def _adversarial_analysis(self, subgraph) -> "EnhancedConsensusResult":
        """New adversarial analysis pipeline."""
        # Route to agents
        router = AgentRouter(...)
        results = router.route_with_chaining(subgraph.focal_nodes)

        # Arbitrate
        arbiter = AdversarialArbiter(...)
        verdict = arbiter.arbitrate(
            results[AgentType.ATTACKER],
            results[AgentType.DEFENDER],
            results.get(AgentType.VERIFIER),
            subgraph.focal_nodes[0],
        )

        # Convert to consensus result format
        return EnhancedConsensusResult(
            verdict=self._map_verdict(verdict.verdict),
            confidence=verdict.confidence,
            mode="adversarial",
            arbitration=verdict,
        )
```

---

## Success Criteria

- [ ] Both modes working
- [ ] Backward compatible API
- [ ] Configuration via settings
- [ ] Clear deprecation warnings

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
