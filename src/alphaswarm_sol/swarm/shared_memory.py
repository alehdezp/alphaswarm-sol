"""
Shared Memory for Agent Swarm

Collective knowledge base that all agents can read from and write to.
Enables emergent collaborative behavior through shared discoveries.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory entries."""
    FINDING = "finding"                # Confirmed vulnerability
    HYPOTHESIS = "hypothesis"          # Unverified suspicion
    EVIDENCE = "evidence"              # Supporting data
    PATTERN = "pattern"                # Discovered pattern
    SAFE_ZONE = "safe_zone"            # Confirmed safe code
    ATTACK_VECTOR = "attack_vector"    # Potential exploit path
    CONTEXT = "context"                # Contract context info
    RELATIONSHIP = "relationship"      # Inter-function relationships


class Severity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Evidence:
    """Evidence supporting a finding or hypothesis."""
    evidence_id: str
    evidence_type: str  # code_snippet, trace, invariant_violation, etc.
    content: str
    source_agent: str
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "content": self.content[:500],  # Truncate for display
            "source_agent": self.source_agent,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class Hypothesis:
    """An unverified suspicion about a vulnerability."""
    hypothesis_id: str
    vulnerability_type: str
    description: str
    target_function: str
    target_contract: Optional[str] = None
    proposed_by: str = ""
    confidence: float = 0.5
    evidence: List[Evidence] = field(default_factory=list)
    supporting_agents: Set[str] = field(default_factory=set)
    opposing_agents: Set[str] = field(default_factory=set)
    status: str = "pending"  # pending, investigating, confirmed, rejected
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_support(self, agent_id: str, evidence: Optional[Evidence] = None):
        """Agent supports this hypothesis."""
        self.supporting_agents.add(agent_id)
        self.opposing_agents.discard(agent_id)
        if evidence:
            self.evidence.append(evidence)
        self._update_confidence()

    def add_opposition(self, agent_id: str, evidence: Optional[Evidence] = None):
        """Agent opposes this hypothesis."""
        self.opposing_agents.add(agent_id)
        self.supporting_agents.discard(agent_id)
        if evidence:
            self.evidence.append(evidence)
        self._update_confidence()

    def _update_confidence(self):
        """Update confidence based on support/opposition ratio."""
        total = len(self.supporting_agents) + len(self.opposing_agents)
        if total == 0:
            self.confidence = 0.5
        else:
            self.confidence = len(self.supporting_agents) / total
        self.updated_at = datetime.now()

    def get_consensus_score(self) -> float:
        """Get consensus score (agreement level)."""
        total = len(self.supporting_agents) + len(self.opposing_agents)
        if total < 2:
            return 0.0
        majority = max(len(self.supporting_agents), len(self.opposing_agents))
        return majority / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "description": self.description,
            "target_function": self.target_function,
            "confidence": round(self.confidence, 3),
            "status": self.status,
            "supporting_agents": len(self.supporting_agents),
            "opposing_agents": len(self.opposing_agents),
            "evidence_count": len(self.evidence),
        }


@dataclass
class Finding:
    """A confirmed vulnerability finding."""
    finding_id: str
    vulnerability_type: str
    severity: Severity
    title: str
    description: str
    target_function: str
    target_contract: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)
    exploit_code: Optional[str] = None
    fix_recommendation: Optional[str] = None
    discovered_by: str = ""
    verified_by: List[str] = field(default_factory=list)
    confidence: float = 0.9
    impact_score: float = 0.0
    likelihood_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    from_hypothesis: Optional[str] = None  # Original hypothesis ID

    def get_risk_score(self) -> float:
        """Calculate overall risk score."""
        severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.2,
            Severity.INFO: 0.05,
        }
        base = severity_weights.get(self.severity, 0.5)
        return base * self.confidence * (0.5 * self.impact_score + 0.5 * self.likelihood_score + 0.5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "vulnerability_type": self.vulnerability_type,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description[:500],
            "target_function": self.target_function,
            "confidence": round(self.confidence, 3),
            "risk_score": round(self.get_risk_score(), 3),
            "evidence_count": len(self.evidence),
            "verified_by": self.verified_by,
            "has_exploit": self.exploit_code is not None,
            "has_fix": self.fix_recommendation is not None,
        }


@dataclass
class MemoryEntry:
    """Generic memory entry."""
    entry_id: str
    memory_type: MemoryType
    content: Any
    source_agent: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    references: List[str] = field(default_factory=list)  # IDs of related entries


class SharedMemory:
    """
    Collective knowledge base for the agent swarm.

    Enables emergent collaborative behavior through:
    - Shared findings and hypotheses
    - Evidence accumulation
    - Pattern discovery
    - Consensus building
    """

    def __init__(self):
        self.findings: Dict[str, Finding] = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.entries: Dict[str, MemoryEntry] = {}
        self.safe_zones: Set[str] = set()  # Functions confirmed safe
        self.attack_vectors: List[Dict[str, Any]] = []
        self.patterns: Dict[str, Dict[str, Any]] = {}

        # Indexing for fast queries
        self._by_function: Dict[str, List[str]] = {}  # function -> entry_ids
        self._by_type: Dict[MemoryType, List[str]] = {}
        self._by_vuln_type: Dict[str, List[str]] = {}

    def _generate_id(self, prefix: str, content: str) -> str:
        """Generate unique ID."""
        hash_input = f"{prefix}:{content}:{datetime.now().isoformat()}"
        return f"{prefix}-{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"

    # === Finding Management ===

    def add_finding(self, finding: Finding) -> str:
        """Add a confirmed finding."""
        if not finding.finding_id:
            finding.finding_id = self._generate_id("FND", finding.title)

        self.findings[finding.finding_id] = finding

        # Index
        self._index_by_function(finding.target_function, finding.finding_id)
        self._index_by_vuln_type(finding.vulnerability_type, finding.finding_id)

        logger.info(f"Added finding: {finding.finding_id} - {finding.title}")
        return finding.finding_id

    def get_finding(self, finding_id: str) -> Optional[Finding]:
        """Get finding by ID."""
        return self.findings.get(finding_id)

    def get_findings_by_severity(self, severity: Severity) -> List[Finding]:
        """Get all findings of a severity level."""
        return [f for f in self.findings.values() if f.severity == severity]

    def get_findings_for_function(self, function_name: str) -> List[Finding]:
        """Get findings for a specific function."""
        entry_ids = self._by_function.get(function_name, [])
        return [
            self.findings[eid] for eid in entry_ids
            if eid in self.findings
        ]

    # === Hypothesis Management ===

    def add_hypothesis(self, hypothesis: Hypothesis) -> str:
        """Add a new hypothesis."""
        if not hypothesis.hypothesis_id:
            hypothesis.hypothesis_id = self._generate_id("HYP", hypothesis.description)

        self.hypotheses[hypothesis.hypothesis_id] = hypothesis

        # Index
        self._index_by_function(hypothesis.target_function, hypothesis.hypothesis_id)
        self._index_by_vuln_type(hypothesis.vulnerability_type, hypothesis.hypothesis_id)

        logger.info(f"Added hypothesis: {hypothesis.hypothesis_id}")
        return hypothesis.hypothesis_id

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        return self.hypotheses.get(hypothesis_id)

    def get_pending_hypotheses(self) -> List[Hypothesis]:
        """Get all pending hypotheses."""
        return [h for h in self.hypotheses.values() if h.status == "pending"]

    def get_high_confidence_hypotheses(self, threshold: float = 0.7) -> List[Hypothesis]:
        """Get hypotheses with high confidence."""
        return [
            h for h in self.hypotheses.values()
            if h.confidence >= threshold and h.status != "rejected"
        ]

    def promote_hypothesis_to_finding(
        self,
        hypothesis_id: str,
        severity: Severity,
        verified_by: str
    ) -> Optional[Finding]:
        """Convert a confirmed hypothesis to a finding."""
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None

        hypothesis.status = "confirmed"

        finding = Finding(
            finding_id=self._generate_id("FND", hypothesis.description),
            vulnerability_type=hypothesis.vulnerability_type,
            severity=severity,
            title=f"{hypothesis.vulnerability_type} in {hypothesis.target_function}",
            description=hypothesis.description,
            target_function=hypothesis.target_function,
            target_contract=hypothesis.target_contract,
            evidence=hypothesis.evidence.copy(),
            discovered_by=hypothesis.proposed_by,
            verified_by=[verified_by],
            confidence=hypothesis.confidence,
            from_hypothesis=hypothesis_id,
        )

        self.add_finding(finding)
        return finding

    def reject_hypothesis(self, hypothesis_id: str, reason: str = ""):
        """Reject a hypothesis."""
        hypothesis = self.hypotheses.get(hypothesis_id)
        if hypothesis:
            hypothesis.status = "rejected"
            logger.info(f"Rejected hypothesis: {hypothesis_id} - {reason}")

    # === Evidence Management ===

    def add_evidence(self, evidence: Evidence) -> str:
        """Add evidence."""
        if not evidence.evidence_id:
            evidence.evidence_id = self._generate_id("EVD", evidence.content[:50])

        self.evidence[evidence.evidence_id] = evidence
        return evidence.evidence_id

    def get_evidence_for_hypothesis(self, hypothesis_id: str) -> List[Evidence]:
        """Get all evidence for a hypothesis."""
        hypothesis = self.hypotheses.get(hypothesis_id)
        if hypothesis:
            return hypothesis.evidence
        return []

    # === Safe Zone Management ===

    def mark_safe(self, function_name: str, agent_id: str):
        """Mark a function as confirmed safe."""
        self.safe_zones.add(function_name)
        logger.debug(f"Marked safe: {function_name} by {agent_id}")

    def is_safe(self, function_name: str) -> bool:
        """Check if function is confirmed safe."""
        return function_name in self.safe_zones

    def get_safe_zones(self) -> Set[str]:
        """Get all safe functions."""
        return self.safe_zones.copy()

    # === Attack Vector Management ===

    def add_attack_vector(
        self,
        entry_point: str,
        steps: List[str],
        target: str,
        impact: str,
        agent_id: str
    ) -> str:
        """Add a potential attack vector."""
        vector = {
            "id": self._generate_id("ATK", entry_point),
            "entry_point": entry_point,
            "steps": steps,
            "target": target,
            "impact": impact,
            "discovered_by": agent_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.attack_vectors.append(vector)
        return vector["id"]

    def get_attack_vectors(self) -> List[Dict[str, Any]]:
        """Get all attack vectors."""
        return self.attack_vectors.copy()

    # === Pattern Management ===

    def add_pattern(
        self,
        pattern_name: str,
        pattern_data: Dict[str, Any],
        agent_id: str
    ):
        """Add or update a discovered pattern."""
        self.patterns[pattern_name] = {
            **pattern_data,
            "discovered_by": agent_id,
            "timestamp": datetime.now().isoformat(),
        }

    def get_pattern(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Get pattern by name."""
        return self.patterns.get(pattern_name)

    # === Generic Entry Management ===

    def add_entry(self, entry: MemoryEntry) -> str:
        """Add a generic memory entry."""
        if not entry.entry_id:
            entry.entry_id = self._generate_id("MEM", str(entry.content)[:50])

        self.entries[entry.entry_id] = entry

        # Index by type
        if entry.memory_type not in self._by_type:
            self._by_type[entry.memory_type] = []
        self._by_type[entry.memory_type].append(entry.entry_id)

        return entry.entry_id

    def get_entries_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get all entries of a type."""
        entry_ids = self._by_type.get(memory_type, [])
        return [self.entries[eid] for eid in entry_ids if eid in self.entries]

    # === Indexing Helpers ===

    def _index_by_function(self, function_name: str, entry_id: str):
        """Index entry by function name."""
        if function_name not in self._by_function:
            self._by_function[function_name] = []
        self._by_function[function_name].append(entry_id)

    def _index_by_vuln_type(self, vuln_type: str, entry_id: str):
        """Index entry by vulnerability type."""
        if vuln_type not in self._by_vuln_type:
            self._by_vuln_type[vuln_type] = []
        self._by_vuln_type[vuln_type].append(entry_id)

    # === Query Methods ===

    def query_by_function(self, function_name: str) -> Dict[str, Any]:
        """Get all memory related to a function."""
        entry_ids = self._by_function.get(function_name, [])

        return {
            "findings": [
                self.findings[eid] for eid in entry_ids
                if eid in self.findings
            ],
            "hypotheses": [
                self.hypotheses[eid] for eid in entry_ids
                if eid in self.hypotheses
            ],
            "is_safe": function_name in self.safe_zones,
        }

    def query_by_vulnerability_type(self, vuln_type: str) -> Dict[str, Any]:
        """Get all memory related to a vulnerability type."""
        entry_ids = self._by_vuln_type.get(vuln_type, [])

        return {
            "findings": [
                self.findings[eid] for eid in entry_ids
                if eid in self.findings
            ],
            "hypotheses": [
                self.hypotheses[eid] for eid in entry_ids
                if eid in self.hypotheses
            ],
        }

    # === Statistics ===

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        severity_counts = {}
        for finding in self.findings.values():
            sev = finding.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        hypothesis_status = {}
        for hyp in self.hypotheses.values():
            hypothesis_status[hyp.status] = hypothesis_status.get(hyp.status, 0) + 1

        return {
            "total_findings": len(self.findings),
            "findings_by_severity": severity_counts,
            "total_hypotheses": len(self.hypotheses),
            "hypotheses_by_status": hypothesis_status,
            "total_evidence": len(self.evidence),
            "safe_zones": len(self.safe_zones),
            "attack_vectors": len(self.attack_vectors),
            "patterns": len(self.patterns),
            "indexed_functions": len(self._by_function),
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        stats = self.get_statistics()

        lines = [
            "=== Shared Memory Summary ===",
            f"Findings: {stats['total_findings']}",
        ]

        if stats['findings_by_severity']:
            for sev, count in sorted(stats['findings_by_severity'].items()):
                lines.append(f"  - {sev}: {count}")

        lines.extend([
            f"Hypotheses: {stats['total_hypotheses']}",
            f"  - Pending: {stats['hypotheses_by_status'].get('pending', 0)}",
            f"  - Confirmed: {stats['hypotheses_by_status'].get('confirmed', 0)}",
            f"  - Rejected: {stats['hypotheses_by_status'].get('rejected', 0)}",
            f"Evidence pieces: {stats['total_evidence']}",
            f"Safe zones: {stats['safe_zones']}",
            f"Attack vectors: {stats['attack_vectors']}",
        ])

        return "\n".join(lines)

    def clear(self):
        """Clear all memory."""
        self.findings.clear()
        self.hypotheses.clear()
        self.evidence.clear()
        self.entries.clear()
        self.safe_zones.clear()
        self.attack_vectors.clear()
        self.patterns.clear()
        self._by_function.clear()
        self._by_type.clear()
        self._by_vuln_type.clear()
