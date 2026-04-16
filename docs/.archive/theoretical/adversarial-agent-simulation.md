# Adversarial Agent Simulation

**Module:** `alphaswarm_sol.agents.adversarial`
**Phase:** 05.11-08

Adversarial Red-Blue Agent Simulation discovers vulnerabilities through competitive combat between attacker and defender agents, with a judge determining outcomes.

## Overview

The Adversarial Agent Simulation implements a game-theoretic approach to vulnerability discovery where:

1. **Red Team** (Attacker) synthesizes exploits using MCTS-style exploration
2. **Blue Team** (Defender) generates patches and mitigations
3. **Judge Agent** scores both sides and determines verdicts
4. **Improvement Loop** adapts strategies based on outcomes

### Research Basis

- Microsoft research shows 47% improvement in vulnerability discovery via adversarial combat
- Target: 20% increase in novel vulnerability discovery over cooperative verification
- Attack synthesis accuracy target: 80% viable PoCs

## Architecture

```
Finding
    |
    v
+-------------------+
|    Red Agent      |  MCTS exploration + GATE economic analysis
|  (Attack Synthesis)|
+-------------------+
    |
    v  AttackPlan
+-------------------+
|   Blue Agent      |  Causal chain analysis + patch generation
| (Defense Gen)     |
+-------------------+
    |
    v  DefensePlan
+-------------------+
|   Judge Agent     |  Score both sides + determine verdict
|   (Evaluation)    |
+-------------------+
    |
    v  Verdict
+-------------------+
| Simulation Loop   |  Multi-round + improvement tracking
+-------------------+
    |
    v
SimulationResult (novel findings, suggested patches)
```

## Components

### Red Agent

The Red Agent synthesizes attacks using MCTS-inspired exploration with economic pruning via GATE.

```python
from alphaswarm_sol.agents.adversarial import RedAgent, MCTSConfig

agent = RedAgent(use_llm=False)

config = MCTSConfig(
    max_iterations=100,
    max_depth=10,
    exploration_constant=1.414,  # UCB1 parameter
    prune_negative_ev=True,      # Skip EV < 0 branches
)

plan = agent.synthesize_attack(
    finding={"id": "vuln-1", "severity": "high", "pattern_id": "reentrancy"},
    protocol_state={"tvl_usd": 10_000_000, "gas_price_gwei": 50},
    budget=config,
)

print(f"Attack viable: {plan.is_viable}")
print(f"Expected profit: ${float(plan.expected_profit):,.2f}")
print(f"Steps: {len(plan.exploit_path.transactions)}")
```

#### AttackPlan Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier |
| `vulnerability_id` | str | Target vulnerability |
| `exploit_path` | ExploitPath | Ordered transaction steps |
| `expected_profit` | Decimal | Expected profit from GATE |
| `success_probability` | float | Probability of success |
| `required_capital` | Decimal | Capital needed (flash loans) |
| `mev_vulnerability` | bool | Can be frontrun? |
| `causal_chain` | List[str] | CEG node references |

#### MCTS Exploration

The Red Agent uses Monte Carlo Tree Search with UCB1 selection:

```
UCB1 = mean_value + c * sqrt(ln(parent_visits) / visit_count)
```

- **Selection**: UCB1 finds promising nodes to explore
- **Expansion**: LLM/heuristics generate available actions
- **Simulation**: Estimate attack outcome (profit - costs)
- **Backpropagation**: Update node values up to root

Economic pruning skips branches where expected value < 0.

### Blue Agent

The Blue Agent generates defenses that break attack causal chains.

```python
from alphaswarm_sol.agents.adversarial import BlueAgent

agent = BlueAgent()

defense = agent.generate_defense(
    attack_plan=red_agent_output,
    mitigation_db=known_mitigations,
)

print(f"Patches: {len(defense.patches)}")
print(f"Cost estimate: ${float(defense.cost_estimate):,.2f}")
print(f"Effectiveness: {defense.effectiveness:.1%}")
```

#### DefensePlan Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier |
| `attack_plan_id` | str | Attack being countered |
| `patches` | List[PatchRecommendation] | Code changes |
| `mitigations` | List[Mitigation] | Broader measures |
| `cost_estimate` | Decimal | Implementation cost |
| `effectiveness` | float | % of attack blocked |
| `side_effects` | List[str] | Potential downsides |
| `invariants_suggested` | List[str] | require() statements |

#### PatchRecommendation

```python
@dataclass
class PatchRecommendation:
    id: str
    file_path: str
    line_range: Tuple[int, int]
    description: str
    code_snippet: str           # Suggested code
    rationale: str              # Why this blocks the attack
    breaks_chain_at: str        # Causal chain node blocked
    complexity: PatchComplexity # TRIVIAL to ARCHITECTURAL
    gas_impact: int             # Gas cost change
```

### Judge Agent

The Judge Agent evaluates both teams and produces verdicts.

```python
from alphaswarm_sol.agents.adversarial import JudgeAgent

judge = JudgeAgent()

verdict = judge.evaluate(
    attack_plan=red_output,
    defense_plan=blue_output,
    ground_truth=known_vuln_data,
)

print(f"Winner: {verdict.winner.value}")
print(f"Red score: {verdict.red_score:.1f}")
print(f"Blue score: {verdict.blue_score:.1f}")
print(f"Novel findings: {len(verdict.novel_findings)}")
```

#### Scoring Criteria

**Red Team (Attack)**
| Category | Weight | Description |
|----------|--------|-------------|
| Creativity | 15% | Novel attack approach |
| Feasibility | 25% | Technical viability |
| Economic Viability | 25% | EV > 0 |
| Exploit Completeness | 20% | Full PoC vs sketch |
| Evidence Quality | 15% | Supporting evidence |

**Blue Team (Defense)**
| Category | Weight | Description |
|----------|--------|-------------|
| Effectiveness | 30% | Attack blocked? |
| Cost Efficiency | 20% | Cost vs prevented loss |
| Completeness | 20% | All vectors addressed? |
| Side Effects | 15% | Minimal collateral |
| Practicality | 15% | Easy to implement |

### Adversarial Simulation

The simulation orchestrates multi-round combat with improvement tracking.

```python
from alphaswarm_sol.agents.adversarial import (
    AdversarialSimulation,
    SimulationConfig,
)

config = SimulationConfig(
    max_rounds=3,
    min_rounds=1,
    mcts_iterations=100,
    track_improvement=True,
)

simulation = AdversarialSimulation(config=config)

result = simulation.run_round(
    finding=vulnerability_finding,
    protocol_state={"tvl_usd": 10_000_000},
)

print(f"Attack success rate: {result.attack_success_rate:.1%}")
print(f"Defense effectiveness: {result.defense_effectiveness:.1%}")
print(f"Novel vulnerabilities: {len(result.novel_vulnerabilities)}")
print(f"Suggested patches: {len(result.suggested_patches)}")
```

#### Improvement Loop

The simulation tracks and adapts strategies:

1. **Track Outcomes**: Win rates, viability rates, effectiveness
2. **Adapt Red Strategy**: Increase aggression if losing, learn from successful attacks
3. **Update Mitigation DB**: Store effective defenses for future reference
4. **Strategy Convergence**: Early stop when outcome stabilizes

```python
metrics = simulation.get_global_metrics()
print(f"Red win rate: {metrics.red_win_rate:.1%}")
print(f"Blue win rate: {metrics.blue_win_rate:.1%}")
print(f"Strategy adaptations: {metrics.strategy_adaptations}")
```

## Integration Points

### With GATE (Game-Theoretic Attack Engine)

Red Agent uses GATE for economic analysis:

```python
from alphaswarm_sol.economics.gate import AttackSynthesisEngine

gate_engine = AttackSynthesisEngine()
red_agent = RedAgent(gate_engine=gate_engine)
```

GATE provides:
- Attack payoff matrix
- Nash equilibrium analysis
- Economic viability determination

### With CEG (Causal Exploitation Graph)

Red Agent uses CEG for causal structure:

```python
from alphaswarm_sol.economics.causal import build_ceg

red_agent = RedAgent(ceg_builder=build_ceg)
```

CEG provides:
- Causal chain from root cause to loss
- Counterfactual analysis for mitigations
- Loss amplification factors

### With Existing Agents

The adversarial agents complement existing VRS agents:

| Role | VRS Agent | Adversarial Agent |
|------|-----------|-------------------|
| Attack | vrs-attacker | RedAgent (MCTS + GATE) |
| Defense | vrs-defender | BlueAgent (Patches + Cost) |
| Arbitration | vrs-verifier | JudgeAgent (Scoring) |

## Usage Examples

### Basic Simulation

```python
from alphaswarm_sol.agents.adversarial import AdversarialSimulation

simulation = AdversarialSimulation()

# Single finding
result = simulation.run_round(
    finding={"id": "vuln-1", "severity": "high", "pattern_id": "reentrancy"},
    protocol_state={"tvl_usd": 10_000_000},
)

# Access results
print(f"Winner: {result.final_verdict.winner.value}")
for patch in result.suggested_patches[:3]:
    print(f"Patch: {patch.description}")
```

### Multi-Finding Simulation

```python
findings = [
    {"id": "vuln-1", "severity": "high", "pattern_id": "reentrancy"},
    {"id": "vuln-2", "severity": "critical", "pattern_id": "access-control"},
    {"id": "vuln-3", "severity": "medium", "pattern_id": "oracle-manipulation"},
]

results = simulation.run_full_simulation(findings, protocol_state)

# Aggregate discoveries
all_novel = simulation.get_novel_discoveries()
best_patches = simulation.get_best_patches()
```

### Custom Agent Configuration

```python
from alphaswarm_sol.agents.adversarial import (
    RedAgent,
    BlueAgent,
    JudgeAgent,
    AdversarialSimulation,
    SimulationConfig,
)

# Custom agents with LLM
red = RedAgent(use_llm=True, gate_engine=my_gate)
blue = BlueAgent(use_llm=True, mitigation_db=my_db)
judge = JudgeAgent(use_llm=True, strict_evidence=True)

config = SimulationConfig(
    max_rounds=5,
    mcts_iterations=200,
    use_llm=True,
)

simulation = AdversarialSimulation(
    config=config,
    red_agent=red,
    blue_agent=blue,
    judge_agent=judge,
)
```

## Metrics and Targets

### Attack Synthesis Accuracy

Target: 80% of generated PoCs are viable (EV > 0)

```python
result = simulation.run_round(finding, protocol_state)
viability = result.improvement_metrics.attack_viability_rate
assert viability >= 0.8, f"Viability {viability:.1%} below 80% target"
```

### Novel Vulnerability Discovery

Target: 20% increase over cooperative verification

```python
# Compare with cooperative baseline
cooperative_findings = run_cooperative_verification(findings)
adversarial_findings = simulation.run_full_simulation(findings)

adversarial_novel = len(simulation.get_novel_discoveries())
cooperative_novel = len(cooperative_findings)

improvement = (adversarial_novel - cooperative_novel) / max(cooperative_novel, 1)
assert improvement >= 0.2, f"Improvement {improvement:.1%} below 20% target"
```

## Serialization

All results support dictionary serialization:

```python
result = simulation.run_round(finding, protocol_state)
result_dict = result.to_dict()

# Save to JSON
import json
with open("simulation_result.json", "w") as f:
    json.dump(result_dict, f, indent=2)
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `RedAgent` | MCTS attack synthesis |
| `BlueAgent` | Defense generation |
| `JudgeAgent` | Verdict determination |
| `AdversarialSimulation` | Orchestration |

### Data Classes

| Class | Description |
|-------|-------------|
| `AttackPlan` | Red Team output |
| `ExploitPath` | Ordered transactions |
| `Transaction` | Single exploit step |
| `DefensePlan` | Blue Team output |
| `PatchRecommendation` | Code patch |
| `Mitigation` | Broader defense |
| `Verdict` | Judge output |
| `Score` | Detailed scoring |
| `SimulationResult` | Full result |
| `RoundResult` | Single round |

### Configuration

| Class | Description |
|-------|-------------|
| `MCTSConfig` | Red Agent exploration |
| `SimulationConfig` | Orchestration settings |
| `ImprovementMetrics` | Tracking metrics |

## Related Documentation

- [Game-Theoretic Attack Synthesis (GATE)](game-theoretic-attack-synthesis.md)
- [Causal Exploitation Graph (CEG)](causal-exploitation-graph.md)
- [Economic Context Overlay](economic-context-overlay.md)
- [Agent Contracts](economic-agent-contracts.md)

---

*Phase: 05.11-08 Adversarial Red-Blue Agent Simulation*
*Created: 2026-01-27*
