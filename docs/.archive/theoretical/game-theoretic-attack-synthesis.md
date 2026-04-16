# Game-Theoretic Attack Synthesis Engine (GATE)

> **Phase:** 5.11-06
> **Status:** Implemented
> **Module:** `alphaswarm_sol.economics.gate`

## Overview

The Game-Theoretic Attack Synthesis Engine (GATE) differentiates AlphaSwarm from other security tools by **proving whether attacks are worth exploiting** given real economic constraints. Instead of simply flagging vulnerabilities, GATE computes expected values for exploitation and identifies conditions that make attacks economically irrational.

**Key Capabilities:**
- Model vulnerabilities as 3-player games (Attacker, Protocol, MEV Searchers)
- Compute Nash equilibria to determine stable strategy profiles
- Filter economically irrational vulnerabilities (target: 30% false positive reduction)
- Identify blocking conditions that prevent profitable attacks

## Architecture

```
Vulnerability Data
       │
       ▼
┌─────────────────────────────┐
│   AttackSynthesisEngine     │
│  - Enumerate strategies     │
│  - Build payoff tensor      │
│  - Compute expected values  │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│    AttackPayoffMatrix       │
│  - Attacker strategies      │
│  - Protocol defenses        │
│  - MEV strategies           │
│  - 3D payoff tensor         │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   NashEquilibriumSolver     │
│  - Find pure Nash           │
│  - Approximate mixed Nash   │
│  - Identify blockers        │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│        NashResult           │
│  - Equilibrium strategies   │
│  - Attacker payoff (EV)     │
│  - Blocking conditions      │
│  - is_attack_dominant       │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│    IncentiveAnalyzer        │
│  - Misalignment detection   │
│  - PoB pattern recognition  │
│  - Mitigation suggestions   │
└─────────────────────────────┘
```

## Quick Start

```python
from alphaswarm_sol.economics import (
    AttackSynthesisEngine,
    NashEquilibriumSolver,
    compute_attack_ev,
)

# Create engines
engine = AttackSynthesisEngine()
solver = NashEquilibriumSolver()

# Compute attack payoff matrix
matrix = engine.compute_attack_ev(
    vulnerability={
        "id": "reentrancy-001",
        "pattern_id": "reentrancy-classic",
        "severity": "critical",
        "potential_profit_usd": 500000,
    },
    protocol_state={
        "tvl_usd": 10_000_000,
        "gas_price_gwei": 50,
        "detection_probability": 0.3,
        "has_timelock": True,
    },
)

# Solve for Nash equilibrium
result = solver.solve_nash_equilibrium(matrix)

if result.is_attack_dominant:
    print(f"ALERT: Attack is economically rational")
    print(f"Expected Value: ${result.attacker_payoff:,.2f}")
    print(f"Attacker Strategy: {result.attacker_strategy}")
else:
    print(f"Attack is NOT profitable")
    print(f"Blocked by: {result.get_blocking_summary()}")
```

## 3-Player Game Model

GATE models vulnerabilities as strategic games between three players:

### Players

| Player | Objective | Strategy Examples |
|--------|-----------|-------------------|
| **Attacker** | Maximize profit | Direct exploit, flash loan attack, sandwich |
| **Protocol** | Minimize losses | Timelock, rate limit, pause, monitoring |
| **MEV Searcher** | Extract value | Frontrun, backrun, sandwich, copy attack |

### Attacker Strategies

```python
class AttackStrategy(Enum):
    ABSTAIN = "abstain"  # Don't attack (honest behavior)
    DIRECT_EXPLOIT = "direct_exploit"
    FLASHLOAN_EXPLOIT = "flashloan_exploit"
    MULTISTEP_EXPLOIT = "multistep_exploit"
    SANDWICH_ATTACK = "sandwich_attack"
    GOVERNANCE_EXPLOIT = "governance_exploit"
    ORACLE_MANIPULATION = "oracle_manipulation"
```

### Protocol Defenses

```python
class ProtocolDefense(Enum):
    NO_DEFENSE = "no_defense"
    TIMELOCK = "timelock"
    RATE_LIMIT = "rate_limit"
    PAUSE_MECHANISM = "pause_mechanism"
    REENTRANCY_GUARD = "reentrancy_guard"
    ACCESS_CONTROL = "access_control"
    ORACLE_VALIDATION = "oracle_validation"
    MEV_PROTECTION = "mev_protection"
    MONITORING = "monitoring"
```

### MEV Strategies

```python
class MEVStrategy(Enum):
    ABSTAIN = "abstain"
    FRONTRUN = "frontrun"
    BACKRUN = "backrun"
    SANDWICH = "sandwich"
    COPY_ATTACK = "copy_attack"  # Copy entire attack
    LIQUIDATE = "liquidate"
    PROTECT = "protect"  # Use Flashbots
```

## Payoff Computation

### Expected Value Formula

For each strategy combination, GATE computes payoffs:

```
Attacker EV = P(success) * profit - gas_cost - mev_extraction - extra_costs
```

Where:
- `P(success)` is adjusted by active defenses
- `profit` depends on TVL and severity
- `gas_cost = gas_units * gas_price_gwei * eth_price_usd / 1e9`
- `mev_extraction` depends on MEV strategy
- `extra_costs` include flash loan fees, slippage, capital requirements

### Cost Model

```python
from alphaswarm_sol.economics.gate.attack_synthesis import CostModel

model = CostModel(
    gas_price_gwei=50.0,
    eth_price_usd=2000.0,
    flashloan_fee_bps=9.0,  # 0.09% Aave/dYdX
    slippage_bps=50.0,      # 0.5%
    oracle_manipulation_cost_usd=10000.0,
)

# Calculate costs
gas_cost = model.gas_cost_usd(500_000)  # $50 at 50 gwei, $2000 ETH
flash_fee = model.flashloan_fee_usd(1_000_000)  # $90 on $1M loan
```

### Defense Effectiveness

Defenses reduce attack success probability:

| Defense | Effectiveness |
|---------|--------------|
| Reentrancy Guard | 80% reduction |
| Access Control | 60% reduction |
| Pause Mechanism | 50% reduction |
| Oracle Validation | 50% reduction |
| Rate Limit | 40% reduction |
| Timelock | 30% reduction |
| MEV Protection | 20% reduction |
| Monitoring | 30% reduction |

## Nash Equilibrium Solving

### Pure Strategy Nash

GATE first searches for pure strategy Nash equilibria where no player wants to unilaterally deviate:

```python
result = solver.find_pure_nash(matrix)
if result:
    print(f"Pure Nash found: {result.attacker_strategy}")
    print(f"Convergence: 100%")  # Pure equilibria are certain
```

### Mixed Strategy Approximation

For complex games without pure equilibria, GATE uses iterated best response:

```python
result = solver.approximate_mixed_nash(matrix)

# Access mixed strategy probabilities
for player, probs in result.mixed_strategy_probs.items():
    print(f"{player}: {probs}")
```

### 2-Player Subgames

For simpler analysis, fix MEV strategy and solve 2-player game:

```python
result = solver.solve_2player_subgame(
    matrix,
    fix_mev=MEVStrategy.ABSTAIN,
)
```

## Blocking Conditions

Blocking conditions identify defenses that make attacks irrational:

```python
for condition in result.blocking_conditions:
    print(f"Type: {condition.condition_type.value}")
    print(f"Threshold: {condition.threshold}")
    print(f"Effect: ${condition.effect_usd:,.2f}")
    print(f"Description: {condition.description}")
```

### Blocking Condition Types

| Type | Example Threshold |
|------|-------------------|
| `TIMELOCK` | `timelock > 86400 seconds` |
| `RATE_LIMIT` | `rate_limit < 50% of TVL` |
| `MEV_PROTECTION` | `mev_protection_enabled = true` |
| `GUARD` | `reentrancy_guard_active = true` |
| `ACCESS_CONTROL` | `access_control_enforced = true` |
| `GAS_COST` | `attack EV <= abstain` |
| `SLIPPAGE` | `slippage_protection <= 1%` |
| `DETECTION` | `detection_probability > 70%` |

## Incentive Analysis

The `IncentiveAnalyzer` identifies incentive misalignments:

```python
from alphaswarm_sol.economics import IncentiveAnalyzer

analyzer = IncentiveAnalyzer()

# Analyze from protocol state
report = analyzer.analyze_incentives(protocol_state={
    "tvl_usd": 10_000_000,
    "mev_exposure": "high",
    "has_staking": True,
    "has_slashing": True,
})

print(f"Honest Dominant: {report.is_honest_dominant}")
print(f"Alignment Score: {report.overall_alignment_score}/100")
print(f"Has PoB: {report.has_proof_of_behavior}")

for misalignment in report.misalignments:
    print(f"  - {misalignment.misalignment_type.value}: {misalignment.description}")

# Analyze from Nash result
report = analyzer.analyze_from_nash(nash_result, matrix)
```

### Misalignment Types

| Type | Description |
|------|-------------|
| `GRIEFING` | Profitable to cause harm to others |
| `FREE_RIDING` | Benefit without contributing |
| `MEV_EXTRACTION` | Value extraction via ordering |
| `GOVERNANCE_CAPTURE` | Control via token acquisition |
| `ORACLE_MANIPULATION` | Profit from price manipulation |
| `FLASHLOAN_AMPLIFICATION` | Capital-free attacks |
| `SANDWICH_ATTACK` | Profit from sandwiching users |
| `FRONT_RUNNING` | Profit from information asymmetry |

### Proof-of-Behavior Detection

GATE detects Proof-of-Behavior (PoB) patterns:

```python
# PoB features that improve alignment
pob_features = [
    "has_staking",      # Stake required
    "has_slashing",     # Slashing conditions
    "has_reputation",   # Reputation system
    "has_bonding",      # Bonding curves
    "has_vesting",      # Vesting schedules
    "has_escrow",       # Escrowed funds
    "has_collateral",   # Collateral requirements
]

# 2+ features = PoB classification
```

## Integration with RationalityGate

GATE results integrate with the existing `RationalityGate`:

```python
from alphaswarm_sol.economics import RationalityGate, AttackSynthesisEngine

# Use GATE for detailed analysis
engine = AttackSynthesisEngine()
solver = NashEquilibriumSolver()

matrix = engine.compute_attack_ev(vulnerability, protocol_state)
nash_result = solver.solve_nash_equilibrium(matrix)

# Feed into RationalityGate for filtering
gate = RationalityGate()
ev_result = gate.evaluate_attack_ev(
    vulnerability={
        **vulnerability,
        "potential_profit_usd": nash_result.attacker_payoff,
    },
    protocol_state=protocol_state,
)

print(f"Priority Bucket: {ev_result.priority_bucket}")
```

## Historical Exploit Validation

GATE has been validated against known historical exploits:

| Exploit | Year | Loss | GATE Classification |
|---------|------|------|---------------------|
| The DAO | 2016 | $60M | Economically Rational |
| bZx Flash Loan | 2020 | $350K | Economically Rational |
| Wormhole | 2022 | $320M | Economically Rational |
| Ronin | 2022 | $625M | Economically Rational |
| Nomad | 2022 | $190M | Economically Rational |

**Target Accuracy:** 80%+ on historical exploit classification (achieved in testing).

## Performance Considerations

- **Payoff tensor size:** `O(A * P * M * 3)` where A, P, M are strategy counts
- **Pure Nash search:** `O(A * P * M)` - checks all combinations
- **Mixed Nash approximation:** `O(iterations * A * P * M)` - iterated best response
- **Typical strategies:** ~5-8 per player = manageable computation

## API Reference

### AttackSynthesisEngine

```python
class AttackSynthesisEngine:
    def compute_attack_ev(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Optional[Dict[str, Any]] = None,
        gas_price_gwei: Optional[float] = None,
        tvl_usd: Optional[float] = None,
    ) -> AttackPayoffMatrix:
        """Compute 3-player payoff matrix for vulnerability."""
```

### NashEquilibriumSolver

```python
class NashEquilibriumSolver:
    def solve_nash_equilibrium(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> NashResult:
        """Solve for Nash equilibrium."""

    def find_pure_nash(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> Optional[NashResult]:
        """Find pure strategy Nash equilibrium."""

    def approximate_mixed_nash(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> NashResult:
        """Approximate mixed strategy equilibrium."""
```

### IncentiveAnalyzer

```python
class IncentiveAnalyzer:
    def analyze_incentives(
        self,
        protocol_state: Dict[str, Any],
    ) -> IncentiveReport:
        """Analyze incentive alignment from protocol state."""

    def analyze_from_nash(
        self,
        nash_result: NashResult,
        payoff_matrix: AttackPayoffMatrix,
    ) -> IncentiveReport:
        """Analyze incentives from Nash equilibrium."""

    def find_blocking_conditions(
        self,
        misalignments: List[IncentiveMisalignment],
    ) -> List[BlockingCondition]:
        """Find blocking conditions for misalignments."""
```

## Related Documentation

- [Economic Risk Scoring](./economic-risk-scoring.md) - Risk scoring integration
- [Economic Context Overlay](./economic-context-overlay.md) - Context types
- [Workflow Integrity Gates](./workflow-integrity-gates.md) - Gate integration
- [Contract Passport](./contract-passport.md) - Systemic risk context
