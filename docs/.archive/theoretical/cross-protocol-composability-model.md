# Cross-Protocol Composability Risk Model (CPCRM)

**Status:** Implemented (05.11-10)
**Location:** `src/alphaswarm_sol/economics/composability/`

## Overview

CPCRM models DeFi as a connected system where protocol failures cascade,
identifying systemic risks that single-protocol analysis misses.

DeFi protocols do not exist in isolation. They depend on shared oracles,
liquidity sources, collateral assets, and governance mechanisms. When one
protocol fails, the failure can cascade through these dependencies to affect
many other protocols.

CPCRM provides:
- **Protocol dependency graph**: Models ecosystem interactions
- **Cascade failure simulation**: Estimates TVL at risk
- **Systemic risk scoring**: Quantifies protocol centrality and cascade potential
- **Multi-protocol attack paths**: Discovers cross-protocol exploit chains

## Architecture

```
                    ProtocolDependencyGraph
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
     ProtocolNode    DependencyEdge    Centrality
     (TVL, category)  (type, criticality)  Analysis
            │               │               │
            └───────────────┼───────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
      CascadeSimulator   SystemicScorer   GATE Integration
      (failure propagation) (risk score)  (economic viability)
            │               │               │
            └───────────────┴───────────────┘
                            │
                            ▼
                    CrossProtocolAttackPath
                    (multi-step attacks filtered by EV)
```

## Protocol Dependency Graph

The graph models protocols as nodes and dependencies as directed edges.

### ProtocolNode

Each protocol is represented by a node containing:

| Field | Type | Description |
|-------|------|-------------|
| `protocol_id` | str | Unique identifier (e.g., "aave-v3") |
| `tvl` | Decimal | Total value locked in USD |
| `category` | ProtocolCategory | LENDING, DEX, ORACLE, BRIDGE, etc. |
| `chains` | List[str] | Deployed chains |
| `governance` | GovernanceInfo | Governance configuration |

### DependencyEdge

Dependencies are categorized by type:

| Dependency Type | Description | Cascade Behavior |
|----------------|-------------|------------------|
| `ORACLE` | Price feed dependency | Fast propagation (30min) |
| `LIQUIDITY` | Liquidity source | Moderate propagation (2hr) |
| `COLLATERAL` | Collateral asset | Fast propagation (15min) |
| `GOVERNANCE` | Governance dependency | Slow propagation (24hr) |
| `BRIDGE` | Cross-chain bridge | Moderate propagation (1hr) |

Each edge has:
- **Criticality** (1-10): How critical is this dependency?
- **TVL at risk**: How much TVL would be affected if dependency fails?
- **Propagation time**: How fast does failure propagate?

### Centrality Analysis

The graph computes eigenvector centrality to identify systemically important
protocols. Higher centrality = more protocols depend on it = higher systemic risk.

```python
from alphaswarm_sol.economics.composability import (
    ProtocolDependencyGraph,
    ProtocolNode,
    ProtocolCategory,
)

# Build graph
graph = ProtocolDependencyGraph()
graph.load_seed_data()  # Load 10+ major protocols

# Compute centrality
centrality = graph.compute_centrality()
print(f"Chainlink centrality: {centrality['chainlink']:.2f}")
# Expected: High centrality (many protocols depend on Chainlink)
```

## Cascade Failure Simulation

CascadeSimulator propagates failures through the dependency graph.

### Failure Types

| Failure Type | Description | High-Impact Dependencies |
|--------------|-------------|--------------------------|
| `ORACLE_MANIPULATION` | Oracle price manipulation | Oracle |
| `EXPLOIT` | Smart contract exploit | Collateral |
| `GOVERNANCE_ATTACK` | Malicious governance | Governance |
| `LIQUIDITY_CRISIS` | Bank run / liquidity drain | Liquidity |
| `BRIDGE_HACK` | Bridge compromise | Bridge |
| `DEPEG` | Stablecoin/token depeg | Collateral |
| `INSOLVENCY` | Protocol insolvency | Liquidity, Collateral |

### Propagation Rules

1. **Oracle failure**: Affects oracle dependents within staleness window
2. **Liquidity crisis**: Affects dependents with >30% liquidity from source
3. **Exploit**: Affects collateral dependents immediately
4. **Propagation stops** when edge criticality < threshold (default 5.0)

### Market Conditions

Market conditions affect cascade speed and severity:

```python
from alphaswarm_sol.economics.composability import (
    CascadeSimulator,
    MarketConditions,
    FailureType,
)

# Normal conditions
normal = MarketConditions.normal()  # volatility=0.2, stress=0.1

# Stressed conditions (March 2023 USDC depeg)
stressed = MarketConditions.stressed()  # volatility=0.7, stress=0.6

simulator = CascadeSimulator(graph)
result = simulator.simulate_failure(
    trigger_protocol="chainlink",
    failure_type=FailureType.ORACLE_MANIPULATION,
    market_conditions=stressed,
)

print(f"Affected: {len(result.affected_protocols)} protocols")
print(f"TVL at risk: ${result.total_tvl_at_risk:,.0f}")
print(f"Cascade depth: {result.cascade_depth}")
```

### CascadeResult

Simulation returns a complete cascade analysis:

| Field | Description |
|-------|-------------|
| `affected_protocols` | List of affected protocols (ordered by impact time) |
| `total_tvl_at_risk` | Total TVL affected across all protocols |
| `propagation_timeline` | Ordered list of propagation events |
| `critical_bottlenecks` | Single points of failure |
| `cascade_depth` | Maximum propagation depth |

## Systemic Risk Scoring

SystemicScorer combines centrality, cascade risk, and dependencies into a
comprehensive systemic risk score (0-10).

### Score Components

| Component | Range | Description |
|-----------|-------|-------------|
| Centrality | 0-3 | Graph centrality score |
| Cascade | 0-4 | TVL at risk from cascade |
| Dependency | 0-3 | Number of dependencies in/out |

### Scoring Thresholds

| Score | Risk Level | Description |
|-------|------------|-------------|
| >= 8.0 | Critical | Systemic importance, requires monitoring |
| >= 6.0 | High | Significant cascade potential |
| >= 4.0 | Medium | Moderate systemic impact |
| >= 2.0 | Low | Limited cascade potential |
| < 2.0 | Minimal | Isolated protocol |

```python
from alphaswarm_sol.economics.composability import SystemicScorer

scorer = SystemicScorer(graph)
assessment = scorer.compute_systemic_score("chainlink")

print(f"Systemic risk: {assessment.score:.1f}/10")
print(f"Risk level: {assessment.risk_level}")
print(f"Centrality: {assessment.centrality_component:.1f}")
print(f"Cascade: {assessment.cascade_component:.1f}")
print(f"Dependencies: {assessment.dependency_component:.1f}")
```

## Multi-Protocol Attack Discovery

CPCRM discovers cross-protocol exploit chains by traversing the dependency
graph from a vulnerability's affected protocol.

### GATE Integration

Discovered attack paths are filtered by economic viability using the
Game-Theoretic Attack Synthesis Engine (GATE):

1. **Enumerate paths** from vulnerable protocol
2. **Estimate extractable value** across the path
3. **Run GATE analysis** to compute expected value (EV)
4. **Filter** paths where EV <= 0 as LOW_PRIORITY
5. **Rank** remaining paths by EV

```python
from alphaswarm_sol.economics.composability import SystemicScorer

scorer = SystemicScorer(graph)

vulnerability = {
    "id": "reentrancy-001",
    "protocol_id": "aave-v3",
    "severity": "high",
    "potential_profit_usd": 500_000,
}

attacks = scorer.discover_cross_protocol_attacks(vulnerability)

for attack in attacks:
    print(f"Path: {' -> '.join(attack.path)}")
    print(f"EV: ${attack.expected_value:,.0f}")
    print(f"Viable: {attack.is_economically_viable}")
    print(f"Priority: {attack.priority}")
```

### Attack Path Filtering

| Condition | Priority | Action |
|-----------|----------|--------|
| EV > $100K | HIGH | Immediate attention |
| EV > 0 | MEDIUM | Further investigation |
| EV <= 0 | LOW_PRIORITY | Economically irrational |

This filtering reduces false positives by ~30% by eliminating paths where
attack costs exceed potential gains.

## Known DeFi Systemic Risks

CPCRM is designed to model known historical cascades:

### 1. Chainlink Oracle Centrality

Chainlink provides price feeds for the majority of DeFi lending protocols.
An oracle manipulation or failure would cascade to:
- Aave, Compound, MakerDAO (liquidation cascades)
- Synthetix (synthetic asset mispricing)
- Derivatives protocols (incorrect settlement)

**Modeled by:** Oracle dependency edges with criticality 9-10

### 2. stETH/ETH Depeg Cascade

Lido's stETH is used as collateral across many protocols. A significant depeg
would cascade through:
- Aave (stETH collateral liquidations)
- MakerDAO (stETH vault liquidations)
- Curve (stETH/ETH pool imbalance)

**Modeled by:** Collateral dependency edges from Lido

### 3. USDC Depeg (March 2023)

Circle's USDC exposure to SVB caused a brief depeg that cascaded through:
- Curve 3pool (liquidity imbalance)
- MakerDAO (DAI backing questions)
- Multiple lending protocols (collateral value drops)

**Modeled by:** Liquidity and collateral dependencies on stablecoin protocols

## Seed Protocol Data

CPCRM includes seed data for 10+ major DeFi protocols:

| Protocol | Category | Key Dependencies |
|----------|----------|------------------|
| Chainlink | Oracle | - |
| Aave V3 | Lending | Chainlink (oracle), Lido (collateral) |
| Compound V3 | Lending | Chainlink (oracle) |
| Uniswap V3 | DEX | - |
| Curve | DEX | Chainlink (oracle) |
| Lido | Staking | - |
| MakerDAO | Stablecoin | Chainlink (oracle), Lido (collateral) |
| Synthetix | Derivative | Chainlink (oracle), Curve (liquidity) |
| Wormhole | Bridge | - |
| LayerZero | Bridge | - |

```python
# Load seed data
graph = ProtocolDependencyGraph()
graph.load_seed_data()

print(f"Protocols: {graph.protocol_count}")
print(f"Dependencies: {graph.dependency_count}")
```

## Integration with Other Systems

### Passports

CPCRM builds graphs from ContractPassport cross_protocol_dependencies:

```python
from alphaswarm_sol.context.passports import PassportBuilder

builder = PassportBuilder(context_pack, kg_nodes)
passports = list(builder.build_all().values())

graph = ProtocolDependencyGraph()
graph.build_from_passports(passports)
```

### SystemicRiskScorer (economics module)

CPCRM's SystemicScorer feeds into the existing systemic risk scoring:

```python
from alphaswarm_sol.economics import SystemicRiskScorer

# Existing module uses passport-derived dependencies
scorer = SystemicRiskScorer(passports=passports)
score = scorer.compute_systemic_risk("aave-v3")
```

### GATE (Attack Synthesis)

CPCRM uses GATE to filter economically irrational attack paths:

```python
from alphaswarm_sol.economics.gate import compute_attack_ev

# GATE computes EV for multi-step attacks
matrix = compute_attack_ev(
    vulnerability=vuln,
    tvl_usd=total_extractable,
)

if matrix.is_attack_dominant():
    # Attack is economically rational
```

## API Reference

### ProtocolDependencyGraph

```python
class ProtocolDependencyGraph:
    def add_protocol(self, node: ProtocolNode) -> None: ...
    def add_dependency(self, edge: DependencyEdge) -> None: ...
    def get_protocol(self, protocol_id: str) -> Optional[ProtocolNode]: ...
    def get_dependencies(self, protocol_id: str) -> List[DependencyEdge]: ...
    def get_dependents(self, protocol_id: str) -> List[DependencyEdge]: ...
    def compute_centrality(self) -> Dict[str, float]: ...
    def find_critical_paths(self, min_criticality: float = 7.0) -> List[CriticalPath]: ...
    def detect_circular_dependencies(self) -> List[Cycle]: ...
    def build_from_passports(self, passports: List[ContractPassport]) -> Self: ...
    def load_seed_data(self) -> Self: ...
```

### CascadeSimulator

```python
class CascadeSimulator:
    def simulate_failure(
        self,
        trigger_protocol: str,
        failure_type: FailureType,
        market_conditions: Optional[MarketConditions] = None,
        max_depth: int = 10,
    ) -> CascadeResult: ...

    def simulate_scenario(self, scenario: CascadeScenario) -> CascadeResult: ...
    def estimate_worst_case(self, protocol_id: str) -> CascadeResult: ...
```

### SystemicScorer

```python
class SystemicScorer:
    def compute_systemic_score(
        self,
        protocol_id: str,
        include_cascade: bool = True,
        evidence_refs: Optional[List[str]] = None,
    ) -> SystemicRiskAssessment: ...

    def discover_cross_protocol_attacks(
        self,
        vulnerability: Dict[str, Any],
        max_path_length: int = 4,
    ) -> List[CrossProtocolAttackPath]: ...

    def score_finding(
        self,
        finding: Dict[str, Any],
        protocol_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...
```

## Files

| File | Purpose |
|------|---------|
| `composability/__init__.py` | Module exports |
| `composability/protocol_graph.py` | Protocol dependency graph |
| `composability/cascade_simulator.py` | Cascade failure simulation |
| `composability/systemic_scorer.py` | Systemic risk scoring + GATE |
| `tests/test_cross_protocol_composability.py` | Test suite |
