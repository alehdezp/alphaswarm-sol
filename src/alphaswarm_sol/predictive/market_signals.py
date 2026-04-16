"""
Market Signal Analysis

Analyzes market conditions that correlate with exploit likelihood:
- TVL growth patterns (rapid growth attracts attackers)
- Protocol lifecycle phase (launch window = high risk)
- Ecosystem events (competitor exploits, market volatility)
- Incentive dynamics (unsustainable yields = potential exploit target)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of market signals."""
    TVL_SPIKE = "tvl_spike"               # Sudden TVL increase
    TVL_DECLINE = "tvl_decline"           # TVL dropping (whale exit?)
    COMPETITOR_EXPLOIT = "competitor_exploit"  # Similar protocol hacked
    HIGH_YIELD = "high_yield"             # Unsustainably high APY
    TOKEN_UNLOCK = "token_unlock"         # Major token unlock coming
    GOVERNANCE_CHANGE = "governance_change"  # Major governance proposal
    MARKET_VOLATILITY = "market_volatility"  # High market volatility
    WHALE_MOVEMENT = "whale_movement"     # Large wallet activity


class ProtocolPhase(Enum):
    """Protocol lifecycle phases with associated risk."""
    LAUNCH = "launch"           # 0-30 days: HIGHEST RISK
    GROWTH = "growth"           # 30-180 days: HIGH RISK
    ESTABLISHED = "established" # 180-365 days: MODERATE RISK
    MATURE = "mature"           # 365+ days: LOWER RISK


@dataclass
class MarketSignal:
    """A market signal that may indicate risk."""
    signal_type: SignalType
    protocol_id: str
    strength: float             # 0.0 to 1.0
    description: str
    detected_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Risk multiplier when this signal is present
    risk_multiplier: float = 1.0

    def is_active(self) -> bool:
        """Check if signal is still active."""
        if self.expires_at:
            return datetime.now() < self.expires_at
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "protocol_id": self.protocol_id,
            "strength": round(self.strength, 3),
            "description": self.description,
            "is_active": self.is_active(),
            "risk_multiplier": self.risk_multiplier,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ProtocolMarketProfile:
    """Market profile for a protocol."""
    protocol_id: str
    protocol_name: Optional[str] = None

    # TVL data
    current_tvl: float = 0.0
    tvl_7d_ago: float = 0.0
    tvl_30d_ago: float = 0.0
    tvl_ath: float = 0.0

    # Protocol phase
    launch_date: Optional[datetime] = None
    phase: ProtocolPhase = ProtocolPhase.LAUNCH

    # Yield data
    current_apy: float = 0.0
    sustainable_apy: float = 10.0  # What's considered sustainable

    # Active signals
    signals: List[MarketSignal] = field(default_factory=list)

    def __post_init__(self):
        if self.launch_date:
            self._update_phase()

    def _update_phase(self):
        """Update protocol phase based on age."""
        if not self.launch_date:
            return

        days_old = (datetime.now() - self.launch_date).days

        if days_old <= 30:
            self.phase = ProtocolPhase.LAUNCH
        elif days_old <= 180:
            self.phase = ProtocolPhase.GROWTH
        elif days_old <= 365:
            self.phase = ProtocolPhase.ESTABLISHED
        else:
            self.phase = ProtocolPhase.MATURE

    def get_tvl_growth_7d(self) -> float:
        """Get 7-day TVL growth percentage."""
        if self.tvl_7d_ago == 0:
            return 0.0
        return ((self.current_tvl - self.tvl_7d_ago) / self.tvl_7d_ago) * 100

    def get_tvl_growth_30d(self) -> float:
        """Get 30-day TVL growth percentage."""
        if self.tvl_30d_ago == 0:
            return 0.0
        return ((self.current_tvl - self.tvl_30d_ago) / self.tvl_30d_ago) * 100

    def get_active_signals(self) -> List[MarketSignal]:
        """Get currently active signals."""
        return [s for s in self.signals if s.is_active()]

    def get_phase_risk_multiplier(self) -> float:
        """Get risk multiplier based on protocol phase."""
        multipliers = {
            ProtocolPhase.LAUNCH: 2.0,
            ProtocolPhase.GROWTH: 1.5,
            ProtocolPhase.ESTABLISHED: 1.0,
            ProtocolPhase.MATURE: 0.7,
        }
        return multipliers[self.phase]

    def get_market_risk_score(self) -> float:
        """Calculate market-based risk score."""
        score = 0.0

        # Phase risk
        phase_scores = {
            ProtocolPhase.LAUNCH: 0.4,
            ProtocolPhase.GROWTH: 0.25,
            ProtocolPhase.ESTABLISHED: 0.1,
            ProtocolPhase.MATURE: 0.05,
        }
        score += phase_scores[self.phase]

        # TVL growth risk
        growth_30d = self.get_tvl_growth_30d()
        if growth_30d > 500:
            score += 0.3
        elif growth_30d > 200:
            score += 0.2
        elif growth_30d > 100:
            score += 0.1

        # High yield risk
        if self.current_apy > self.sustainable_apy * 5:
            score += 0.2
        elif self.current_apy > self.sustainable_apy * 2:
            score += 0.1

        # Active signals
        for signal in self.get_active_signals():
            score += signal.strength * 0.1

        return min(1.0, score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "protocol_name": self.protocol_name,
            "current_tvl": self.current_tvl,
            "tvl_growth_7d": round(self.get_tvl_growth_7d(), 2),
            "tvl_growth_30d": round(self.get_tvl_growth_30d(), 2),
            "phase": self.phase.value,
            "current_apy": self.current_apy,
            "active_signals": len(self.get_active_signals()),
            "market_risk_score": round(self.get_market_risk_score(), 3),
        }


class MarketSignalAnalyzer:
    """
    Analyzes market conditions and generates risk signals.
    """

    # Thresholds
    TVL_SPIKE_THRESHOLD = 50     # 50% increase in 7 days
    TVL_DECLINE_THRESHOLD = -20  # 20% decrease in 7 days
    HIGH_YIELD_MULTIPLIER = 3    # 3x sustainable APY
    WHALE_THRESHOLD_PCT = 5      # 5% of TVL in single tx

    def __init__(self):
        self.profiles: Dict[str, ProtocolMarketProfile] = {}
        self.competitor_exploits: List[Dict[str, Any]] = []
        self.market_volatility: float = 0.0

    def create_profile(
        self,
        protocol_id: str,
        protocol_name: Optional[str] = None,
        launch_date: Optional[datetime] = None
    ) -> ProtocolMarketProfile:
        """Create a market profile for a protocol."""
        profile = ProtocolMarketProfile(
            protocol_id=protocol_id,
            protocol_name=protocol_name,
            launch_date=launch_date,
        )
        self.profiles[protocol_id] = profile
        return profile

    def update_tvl(
        self,
        protocol_id: str,
        current_tvl: float,
        tvl_7d_ago: Optional[float] = None,
        tvl_30d_ago: Optional[float] = None
    ):
        """Update TVL data and check for signals."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            profile = self.create_profile(protocol_id)

        # Save previous for calculation
        old_tvl = profile.current_tvl

        profile.current_tvl = current_tvl
        if tvl_7d_ago is not None:
            profile.tvl_7d_ago = tvl_7d_ago
        if tvl_30d_ago is not None:
            profile.tvl_30d_ago = tvl_30d_ago

        if current_tvl > profile.tvl_ath:
            profile.tvl_ath = current_tvl

        # Check for TVL signals
        self._check_tvl_signals(profile)

    def update_yield(self, protocol_id: str, current_apy: float):
        """Update yield data and check for signals."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            profile = self.create_profile(protocol_id)

        profile.current_apy = current_apy
        self._check_yield_signals(profile)

    def _check_tvl_signals(self, profile: ProtocolMarketProfile):
        """Check for TVL-related signals."""
        growth_7d = profile.get_tvl_growth_7d()

        # Remove old TVL signals
        profile.signals = [
            s for s in profile.signals
            if s.signal_type not in [SignalType.TVL_SPIKE, SignalType.TVL_DECLINE]
        ]

        # TVL spike
        if growth_7d >= self.TVL_SPIKE_THRESHOLD:
            signal = MarketSignal(
                signal_type=SignalType.TVL_SPIKE,
                protocol_id=profile.protocol_id,
                strength=min(1.0, growth_7d / 200),
                description=f"TVL increased {growth_7d:.0f}% in 7 days",
                risk_multiplier=1.3,
                expires_at=datetime.now() + timedelta(days=14),
                metadata={"growth_pct": growth_7d},
            )
            profile.signals.append(signal)

        # TVL decline (whale exit?)
        elif growth_7d <= self.TVL_DECLINE_THRESHOLD:
            signal = MarketSignal(
                signal_type=SignalType.TVL_DECLINE,
                protocol_id=profile.protocol_id,
                strength=min(1.0, abs(growth_7d) / 50),
                description=f"TVL decreased {abs(growth_7d):.0f}% in 7 days (whale exit?)",
                risk_multiplier=1.2,
                expires_at=datetime.now() + timedelta(days=7),
                metadata={"decline_pct": growth_7d},
            )
            profile.signals.append(signal)

    def _check_yield_signals(self, profile: ProtocolMarketProfile):
        """Check for yield-related signals."""
        # Remove old yield signals
        profile.signals = [
            s for s in profile.signals
            if s.signal_type != SignalType.HIGH_YIELD
        ]

        if profile.current_apy > profile.sustainable_apy * self.HIGH_YIELD_MULTIPLIER:
            signal = MarketSignal(
                signal_type=SignalType.HIGH_YIELD,
                protocol_id=profile.protocol_id,
                strength=min(1.0, profile.current_apy / (profile.sustainable_apy * 10)),
                description=f"Unsustainably high APY: {profile.current_apy:.0f}%",
                risk_multiplier=1.4,
                metadata={"apy": profile.current_apy},
            )
            profile.signals.append(signal)

    def record_competitor_exploit(
        self,
        exploited_protocol: str,
        exploit_type: str,
        amount_lost: float,
        similar_protocols: List[str]
    ):
        """Record a competitor exploit and alert similar protocols."""
        exploit = {
            "exploited_protocol": exploited_protocol,
            "exploit_type": exploit_type,
            "amount_lost": amount_lost,
            "timestamp": datetime.now(),
            "similar_protocols": similar_protocols,
        }
        self.competitor_exploits.append(exploit)

        # Add signals to similar protocols
        for protocol_id in similar_protocols:
            profile = self.profiles.get(protocol_id)
            if not profile:
                profile = self.create_profile(protocol_id)

            signal = MarketSignal(
                signal_type=SignalType.COMPETITOR_EXPLOIT,
                protocol_id=protocol_id,
                strength=0.8,
                description=f"Similar protocol {exploited_protocol} exploited for ${amount_lost/1e6:.1f}M via {exploit_type}",
                risk_multiplier=1.5,
                expires_at=datetime.now() + timedelta(days=30),
                metadata=exploit,
            )
            profile.signals.append(signal)

    def record_whale_movement(
        self,
        protocol_id: str,
        amount: float,
        is_deposit: bool
    ):
        """Record significant whale movement."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return

        pct_of_tvl = (amount / profile.current_tvl * 100) if profile.current_tvl > 0 else 0

        if pct_of_tvl >= self.WHALE_THRESHOLD_PCT:
            direction = "deposit" if is_deposit else "withdrawal"
            signal = MarketSignal(
                signal_type=SignalType.WHALE_MOVEMENT,
                protocol_id=protocol_id,
                strength=min(1.0, pct_of_tvl / 20),
                description=f"Large whale {direction}: {pct_of_tvl:.1f}% of TVL",
                risk_multiplier=1.2 if not is_deposit else 1.0,
                expires_at=datetime.now() + timedelta(days=7),
                metadata={
                    "amount": amount,
                    "pct_of_tvl": pct_of_tvl,
                    "is_deposit": is_deposit,
                },
            )
            profile.signals.append(signal)

    def set_market_volatility(self, volatility: float):
        """Set current market volatility (0-100)."""
        self.market_volatility = volatility

        # Add volatility signals to all profiles
        for profile in self.profiles.values():
            # Remove old volatility signals
            profile.signals = [
                s for s in profile.signals
                if s.signal_type != SignalType.MARKET_VOLATILITY
            ]

            if volatility > 50:
                signal = MarketSignal(
                    signal_type=SignalType.MARKET_VOLATILITY,
                    protocol_id=profile.protocol_id,
                    strength=volatility / 100,
                    description=f"High market volatility: {volatility:.0f}/100",
                    risk_multiplier=1.0 + (volatility / 200),
                    expires_at=datetime.now() + timedelta(hours=24),
                    metadata={"volatility": volatility},
                )
                profile.signals.append(signal)

    def get_protocol_phase(self, protocol_id: str) -> ProtocolPhase:
        """Get protocol lifecycle phase."""
        profile = self.profiles.get(protocol_id)
        if not profile:
            return ProtocolPhase.LAUNCH
        return profile.phase

    def get_high_risk_protocols(self, threshold: float = 0.5) -> List[ProtocolMarketProfile]:
        """Get protocols above market risk threshold."""
        return [
            p for p in self.profiles.values()
            if p.get_market_risk_score() >= threshold
        ]

    def get_recent_exploits(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent competitor exploits."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            e for e in self.competitor_exploits
            if e["timestamp"] >= cutoff
        ]

    def get_profile(self, protocol_id: str) -> Optional[ProtocolMarketProfile]:
        """Get market profile for a protocol."""
        return self.profiles.get(protocol_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        if not self.profiles:
            return {"total_profiles": 0}

        risk_scores = [p.get_market_risk_score() for p in self.profiles.values()]
        phase_counts = {phase: 0 for phase in ProtocolPhase}
        for p in self.profiles.values():
            phase_counts[p.phase] += 1

        total_signals = sum(len(p.get_active_signals()) for p in self.profiles.values())

        return {
            "total_profiles": len(self.profiles),
            "avg_market_risk": round(sum(risk_scores) / len(risk_scores), 3),
            "high_risk_count": len(self.get_high_risk_protocols()),
            "total_active_signals": total_signals,
            "protocols_by_phase": {k.value: v for k, v in phase_counts.items()},
            "recent_exploits": len(self.get_recent_exploits()),
            "market_volatility": self.market_volatility,
        }
