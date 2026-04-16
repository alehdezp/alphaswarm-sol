# [P2-T1] Agent Router (GLM-Style)

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T1
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 3-4 days
**Actual Effort**: -

---

## Executive Summary

Implement GLM-style agent routing that decomposes analysis into specialized agents with **selective context sharing**. This achieves the research-proven 95.7% token reduction and 38% accuracy improvement by giving each agent only the context it needs.

**Key Innovation**: Different agents need different slices of the three knowledge graphs. The router creates optimized context for each agent type.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T3] Cross-Graph Linker - For cross-graph context
- [ ] [P1-T2] LLM Intent Annotator - For intent context
- Existing BSKG agents (src/true_vkg/agents/)

### Blocks These Tasks
- [P2-T2] Attacker Agent - Receives routed context
- [P2-T3] Defender Agent - Receives routed context
- [P2-T5] Adversarial Arbiter - Uses routed results

---

## Objectives

1. Create `AgentRouter` that dispatches to specialized agents
2. Implement context slicing per agent type
3. Reduce token usage by 80%+ through selective context
4. Support parallel agent execution
5. Enable result aggregation from multiple agents

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AGENT ROUTER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Input: Focal Nodes + Full Graph + Cross-Graph Context                      │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                      CONTEXT SLICER                                 │    │
│   │                                                                     │    │
│   │   Full Context ───► Per-Agent Optimized Slices                      │    │
│   │                                                                     │    │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │    │
│   │   │ Classifier  │  │  Attacker   │  │  Defender   │               │    │
│   │   │   Slice     │  │   Slice     │  │   Slice     │               │    │
│   │   │             │  │             │  │             │               │    │
│   │   │ • Node types│  │ • Rich edges│  │ • Specs     │               │    │
│   │   │ • Basic prop│  │ • Patterns  │  │ • Guards    │               │    │
│   │   │ • No intent │  │ • Exploits  │  │ • Invariants│               │    │
│   │   │             │  │ • Intent    │  │ • Mitigations│              │    │
│   │   │ ~200 tokens │  │ ~800 tokens │  │ ~600 tokens │               │    │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │    │
│   │          │                │                │                       │    │
│   └──────────┼────────────────┼────────────────┼───────────────────────┘    │
│              │                │                │                             │
│              ▼                ▼                ▼                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│   │ Classifier  │  │  Attacker   │  │  Defender   │  │  Verifier   │       │
│   │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │       │
│   │             │  │             │  │             │  │             │       │
│   │ "Categorize"│  │ "How would  │  │ "Why is     │  │ "Is path    │       │
│   │             │  │  I exploit?"│  │  this safe?"│  │  feasible?" │       │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│          │                │                │                │               │
│          └────────────────┴────────┬───────┴────────────────┘               │
│                                    │                                        │
│                                    ▼                                        │
│                         ┌──────────────────┐                               │
│                         │  Result Merger   │                               │
│                         │                  │                               │
│                         │  Combine agent   │                               │
│                         │  findings with   │                               │
│                         │  provenance      │                               │
│                         └──────────────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Implementation

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class AgentType(Enum):
    """Types of specialized agents."""
    CLASSIFIER = "classifier"  # Categorizes vulnerability type
    ATTACKER = "attacker"      # Thinks like attacker
    DEFENDER = "defender"      # Argues for safety
    VERIFIER = "verifier"      # Formal verification


@dataclass
class AgentContext:
    """
    Optimized context for a specific agent.

    Each agent type gets different slices to minimize tokens
    while maximizing relevant information.
    """
    agent_type: AgentType

    # Code KG slice
    focal_nodes: List[str]  # The nodes being analyzed
    subgraph: "SubGraph"    # Relevant portion of code KG

    # Cross-graph context (agent-specific)
    specs: List["Specification"]  # Domain specs (for Defender)
    patterns: List["AttackPattern"]  # Attack patterns (for Attacker)
    cross_edges: List["CrossGraphEdge"]  # Relevant links

    # Intent (for Attacker/Defender)
    intents: Dict[str, "FunctionIntent"]

    # Previous agent results (for chaining)
    upstream_results: List["AgentResult"] = field(default_factory=list)

    def estimate_tokens(self) -> int:
        """Estimate token count for this context."""
        # Rough estimation
        base = 100  # Prompt overhead
        nodes = len(self.subgraph.nodes) * 50
        specs = len(self.specs) * 100
        patterns = len(self.patterns) * 80
        edges = len(self.cross_edges) * 30
        intents = len(self.intents) * 150
        return base + nodes + specs + patterns + edges + intents


class ContextSlicer:
    """
    Creates optimized context slices for each agent type.

    This is THE KEY to achieving GLM's 95% token reduction.
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: "DomainKnowledgeGraph",
        adversarial_kg: "AdversarialKnowledgeGraph",
        linker: "CrossGraphLinker",
    ):
        self.code_kg = code_kg
        self.domain_kg = domain_kg
        self.adversarial_kg = adversarial_kg
        self.linker = linker

    def slice_for_agent(
        self,
        agent_type: AgentType,
        focal_nodes: List[str],
    ) -> AgentContext:
        """Create optimized context for specific agent type."""

        if agent_type == AgentType.CLASSIFIER:
            return self._slice_for_classifier(focal_nodes)
        elif agent_type == AgentType.ATTACKER:
            return self._slice_for_attacker(focal_nodes)
        elif agent_type == AgentType.DEFENDER:
            return self._slice_for_defender(focal_nodes)
        elif agent_type == AgentType.VERIFIER:
            return self._slice_for_verifier(focal_nodes)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def _slice_for_classifier(self, focal_nodes: List[str]) -> AgentContext:
        """
        Minimal context for classifier.

        Classifier just needs node types and basic properties.
        NO intent, NO cross-graph, NO rich edges.
        """
        subgraph = self._extract_minimal_subgraph(focal_nodes)

        return AgentContext(
            agent_type=AgentType.CLASSIFIER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],  # Not needed
            patterns=[],  # Not needed
            cross_edges=[],  # Not needed
            intents={},  # Not needed
        )

    def _slice_for_attacker(self, focal_nodes: List[str]) -> AgentContext:
        """
        Rich context for attacker agent.

        Attacker needs:
        - Rich edges (external calls, value transfers)
        - Attack patterns from adversarial KG
        - Historical exploits
        - Intent (to understand what to violate)
        - SIMILAR_TO edges
        """
        subgraph = self._extract_rich_subgraph(focal_nodes)

        # Get relevant attack patterns
        patterns = []
        for node_id in focal_nodes:
            node = self.code_kg.nodes[node_id]
            matches = self.adversarial_kg.find_similar_patterns(node, min_confidence=0.3)
            patterns.extend([m.pattern for m in matches])
        patterns = list({p.id: p for p in patterns}.values())  # Dedupe

        # Get SIMILAR_TO edges
        cross_edges = [
            e for e in self.linker.edges
            if e.source_id in focal_nodes
            and e.relation == CrossGraphRelation.SIMILAR_TO
        ]

        # Get intents
        intents = {}
        for node_id in focal_nodes:
            node = self.code_kg.nodes[node_id]
            if "intent" in node.properties:
                intents[node_id] = FunctionIntent.from_dict(node.properties["intent"])

        return AgentContext(
            agent_type=AgentType.ATTACKER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],  # Attacker doesn't care about specs
            patterns=patterns,
            cross_edges=cross_edges,
            intents=intents,
        )

    def _slice_for_defender(self, focal_nodes: List[str]) -> AgentContext:
        """
        Spec-focused context for defender agent.

        Defender needs:
        - Specifications from domain KG
        - Guard analysis (modifiers, require statements)
        - Invariants
        - IMPLEMENTS and MITIGATES edges
        """
        subgraph = self._extract_guard_focused_subgraph(focal_nodes)

        # Get relevant specs
        specs = []
        for node_id in focal_nodes:
            node = self.code_kg.nodes[node_id]
            matches = self.domain_kg.find_matching_specs(node)
            specs.extend([spec for spec, _ in matches])
        specs = list({s.id: s for s in specs}.values())  # Dedupe

        # Get IMPLEMENTS and MITIGATES edges
        cross_edges = [
            e for e in self.linker.edges
            if e.source_id in focal_nodes
            and e.relation in [CrossGraphRelation.IMPLEMENTS, CrossGraphRelation.MITIGATES]
        ]

        return AgentContext(
            agent_type=AgentType.DEFENDER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=specs,
            patterns=[],  # Defender argues from specs, not patterns
            cross_edges=cross_edges,
            intents={},  # Defender uses actual behavior, not inferred intent
        )

    def _slice_for_verifier(self, focal_nodes: List[str]) -> AgentContext:
        """
        Path-focused context for verifier agent.

        Verifier needs:
        - Execution paths
        - Data flow edges
        - Constraints for Z3
        """
        subgraph = self._extract_path_subgraph(focal_nodes)

        return AgentContext(
            agent_type=AgentType.VERIFIER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],
            patterns=[],
            cross_edges=[],
            intents={},
        )


class AgentRouter:
    """
    GLM-style agent router with selective context dispatch.

    Key innovation: 95% token reduction through context specialization.
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: "DomainKnowledgeGraph",
        adversarial_kg: "AdversarialKnowledgeGraph",
        linker: "CrossGraphLinker",
    ):
        self.slicer = ContextSlicer(code_kg, domain_kg, adversarial_kg, linker)
        self.agents = {
            AgentType.CLASSIFIER: ClassifierAgent(),
            AgentType.ATTACKER: AttackerAgent(),
            AgentType.DEFENDER: DefenderAgent(),
            AgentType.VERIFIER: VerifierAgent(),
        }

    def route(
        self,
        focal_nodes: List[str],
        agent_types: Optional[List[AgentType]] = None,
        parallel: bool = True,
    ) -> Dict[AgentType, "AgentResult"]:
        """
        Route analysis to specialized agents.

        Args:
            focal_nodes: Nodes to analyze
            agent_types: Which agents to use (default: all)
            parallel: Run agents in parallel if possible
        """
        if agent_types is None:
            agent_types = list(AgentType)

        # Create optimized contexts
        contexts = {
            agent_type: self.slicer.slice_for_agent(agent_type, focal_nodes)
            for agent_type in agent_types
        }

        # Log token savings
        total_tokens = sum(c.estimate_tokens() for c in contexts.values())
        full_context_estimate = len(focal_nodes) * 2000  # Rough baseline
        savings = 1 - (total_tokens / full_context_estimate)
        logger.info(f"Token savings: {savings:.1%} ({total_tokens} vs {full_context_estimate})")

        # Run agents
        if parallel:
            results = self._run_parallel(contexts)
        else:
            results = self._run_sequential(contexts)

        return results

    def route_with_chaining(
        self,
        focal_nodes: List[str],
    ) -> "ChainedResult":
        """
        Route with result chaining between agents.

        Pipeline: Classifier → Attacker → Defender → Verifier
        Each agent receives previous agent's findings.
        """
        results = {}

        # Stage 1: Classifier categorizes the vulnerability type
        classifier_ctx = self.slicer.slice_for_agent(AgentType.CLASSIFIER, focal_nodes)
        results[AgentType.CLASSIFIER] = self.agents[AgentType.CLASSIFIER].analyze(classifier_ctx)

        # Stage 2: Attacker tries to construct exploit
        attacker_ctx = self.slicer.slice_for_agent(AgentType.ATTACKER, focal_nodes)
        attacker_ctx.upstream_results = [results[AgentType.CLASSIFIER]]
        results[AgentType.ATTACKER] = self.agents[AgentType.ATTACKER].analyze(attacker_ctx)

        # Stage 3: Defender argues against the attack
        defender_ctx = self.slicer.slice_for_agent(AgentType.DEFENDER, focal_nodes)
        defender_ctx.upstream_results = [results[AgentType.ATTACKER]]
        results[AgentType.DEFENDER] = self.agents[AgentType.DEFENDER].analyze(defender_ctx)

        # Stage 4: Verifier checks path feasibility
        verifier_ctx = self.slicer.slice_for_agent(AgentType.VERIFIER, focal_nodes)
        verifier_ctx.upstream_results = [results[AgentType.ATTACKER], results[AgentType.DEFENDER]]
        results[AgentType.VERIFIER] = self.agents[AgentType.VERIFIER].analyze(verifier_ctx)

        return ChainedResult(
            stages=results,
            focal_nodes=focal_nodes,
        )
```

---

## Success Criteria

- [ ] Context slicing implemented for all agent types
- [ ] Token reduction >= 80% vs full context
- [ ] Parallel execution working
- [ ] Result chaining working
- [ ] Backward compatible with existing agents
- [ ] Performance: < 100ms routing overhead

---

## Validation Tests

```python
def test_token_reduction():
    """Test that context slicing achieves significant token reduction."""
    router = AgentRouter(code_kg, domain_kg, adversarial_kg, linker)

    focal_nodes = ["fn_withdraw", "fn_deposit"]

    # Measure full context
    full_context_tokens = estimate_full_context(focal_nodes)

    # Measure sliced contexts
    contexts = router.slicer.slice_for_all_agents(focal_nodes)
    sliced_tokens = sum(c.estimate_tokens() for c in contexts.values())

    reduction = 1 - (sliced_tokens / full_context_tokens)
    assert reduction >= 0.80, f"Token reduction {reduction:.1%} below 80% target"

def test_attacker_context_has_patterns():
    """Test attacker gets attack patterns."""
    slicer = ContextSlicer(code_kg, domain_kg, adversarial_kg, linker)

    # Vulnerable function
    focal = ["fn_withdraw_vuln"]
    ctx = slicer.slice_for_agent(AgentType.ATTACKER, focal)

    assert len(ctx.patterns) > 0, "Attacker should receive attack patterns"
    assert any("reentrancy" in p.id for p in ctx.patterns)

def test_defender_context_has_specs():
    """Test defender gets specifications."""
    slicer = ContextSlicer(code_kg, domain_kg, adversarial_kg, linker)

    focal = ["fn_transfer"]
    ctx = slicer.slice_for_agent(AgentType.DEFENDER, focal)

    assert len(ctx.specs) > 0, "Defender should receive specs"
    assert any("erc20" in s.id for s in ctx.specs)
```

---

## Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Token reduction | >= 80% | Compare sliced vs full context |
| Routing latency | < 100ms | Time context slicing |
| Agent coverage | 4 types | Count implemented agents |

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
