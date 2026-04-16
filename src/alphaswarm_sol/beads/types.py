"""Foundation types for the Beads system.

The Beads system provides rich context packages for LLM-driven vulnerability
investigation. These foundation types are used by all other Phase 6 components.

Types defined here:
- Severity: Vulnerability severity levels (reused from adversarial_kg)
- BeadStatus: Status of a vulnerability bead during investigation
- VerdictType: Type of verdict on a finding
- CodeSnippet: A snippet of code with metadata
- InvestigationStep: A single step in an investigation guide
- ExploitReference: Reference to a real-world exploit
- Verdict: A verdict on a finding
- Finding: A potential vulnerability finding from pattern matching

Usage:
    from alphaswarm_sol.beads import Finding, CodeSnippet, Verdict, Severity

    snippet = CodeSnippet(
        source="function withdraw() external { ... }",
        file_path="/path/to/Vault.sol",
        start_line=45,
        end_line=55,
        function_name="withdraw",
        contract_name="Vault"
    )

    finding = Finding(
        id="VKG-001",
        pattern_id="vm-001",
        function_id="func_vault_withdraw",
        contract_name="Vault",
        function_name="withdraw",
        file_path="/path/to/Vault.sol",
        line_number=45,
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerability_class="reentrancy",
        description="State update after external call"
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


class Severity(Enum):
    """Vulnerability severity levels.

    Aligned with industry standards (CVSS, Immunefi):
    - CRITICAL: Immediate exploitation possible, high impact
    - HIGH: Exploitation likely, significant impact
    - MEDIUM: Exploitation requires specific conditions
    - LOW: Minor impact or difficult to exploit
    - INFO: Informational, best practice suggestions

    Usage:
        from alphaswarm_sol.beads import Severity

        severity = Severity.CRITICAL
        severity_str = severity.value  # "critical"
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Create Severity from string, case-insensitive.

        Args:
            value: Severity string ("critical", "CRITICAL", etc.)

        Returns:
            Severity enum value

        Raises:
            ValueError: If value is not a valid severity

        Usage:
            severity = Severity.from_string("high")  # Severity.HIGH
        """
        normalized = value.lower().strip()
        # Handle common aliases
        aliases = {
            "crit": "critical",
            "hi": "high",
            "med": "medium",
            "lo": "low",
            "informational": "info",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)


class BeadStatus(Enum):
    """Status of a vulnerability bead during investigation.

    Lifecycle:
    PENDING -> INVESTIGATING -> CONFIRMED/REJECTED/NEEDS_INFO/FLAGGED_FOR_HUMAN

    - PENDING: Initial state, not yet reviewed
    - INVESTIGATING: Currently being analyzed
    - CONFIRMED: Verified as true positive
    - REJECTED: Determined to be false positive
    - NEEDS_INFO: Requires additional context
    - FLAGGED_FOR_HUMAN: Debate outcome requires human review (ORCH-08)

    Usage:
        status = BeadStatus.PENDING
        if analysis_complete:
            status = BeadStatus.CONFIRMED
        if debate_inconclusive:
            status = BeadStatus.FLAGGED_FOR_HUMAN
    """
    PENDING = "pending"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"
    FLAGGED_FOR_HUMAN = "flagged_for_human"


class VerdictType(Enum):
    """Type of verdict on a finding.

    Used in final determination of a finding's validity:
    - TRUE_POSITIVE: Real vulnerability
    - FALSE_POSITIVE: Not actually vulnerable
    - INCONCLUSIVE: Unable to determine

    Usage:
        verdict = VerdictType.TRUE_POSITIVE
        if not vulnerable:
            verdict = VerdictType.FALSE_POSITIVE
    """
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE = "inconclusive"


@dataclass
class CodeSnippet:
    """A snippet of code with metadata.

    Represents a piece of source code from a Solidity file with location
    information and optional context about the containing function/contract.

    Attributes:
        source: The actual source code text
        file_path: Absolute path to the source file
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        function_name: Name of the containing function (optional)
        contract_name: Name of the containing contract (optional)

    Usage:
        snippet = CodeSnippet(
            source="(bool success, ) = recipient.call{value: amount}(\"\");",
            file_path="/path/to/Vault.sol",
            start_line=52,
            end_line=52,
            function_name="withdraw",
            contract_name="Vault"
        )

        # Serialize
        data = snippet.to_dict()

        # Deserialize
        restored = CodeSnippet.from_dict(data)
    """
    source: str
    file_path: str
    start_line: int
    end_line: int
    function_name: Optional[str] = None
    contract_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON encoding
        """
        return {
            "source": self.source,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "function_name": self.function_name,
            "contract_name": self.contract_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeSnippet":
        """Create CodeSnippet from dictionary.

        Args:
            data: Dictionary with snippet fields

        Returns:
            CodeSnippet instance
        """
        return cls(
            source=str(data.get("source", "")),
            file_path=str(data.get("file_path", "")),
            start_line=int(data.get("start_line", 0)),
            end_line=int(data.get("end_line", 0)),
            function_name=data.get("function_name"),
            contract_name=data.get("contract_name"),
        )

    @property
    def line_count(self) -> int:
        """Number of lines in this snippet."""
        return max(1, self.end_line - self.start_line + 1)

    @property
    def location(self) -> str:
        """Human-readable location string.

        Returns:
            Location like "Vault.sol:52-55" or "Vault.sol:52"
        """
        from pathlib import Path
        filename = Path(self.file_path).name
        if self.start_line == self.end_line:
            return f"{filename}:{self.start_line}"
        return f"{filename}:{self.start_line}-{self.end_line}"


@dataclass
class InvestigationStep:
    """A single step in an investigation guide.

    Investigation steps guide auditors through verifying a potential
    vulnerability. Each step describes what to look for and what
    evidence would confirm or refute the finding.

    Attributes:
        step_number: Order of this step in the investigation
        action: What action to take (e.g., "Check the external call pattern")
        look_for: What to search for (e.g., "call/send/transfer to external address")
        evidence_needed: What would confirm this step (e.g., "External call found before state update")
        red_flag: Pattern indicating vulnerability (optional)
        safe_if: Pattern indicating safe code (optional)

    Usage:
        step = InvestigationStep(
            step_number=1,
            action="Identify external calls",
            look_for="call, send, or transfer to external address",
            evidence_needed="External call found in function body",
            red_flag="External call before state variable update",
            safe_if="Has nonReentrant modifier or CEI pattern"
        )
    """
    step_number: int
    action: str
    look_for: str
    evidence_needed: str
    red_flag: Optional[str] = None
    safe_if: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON encoding
        """
        return {
            "step_number": self.step_number,
            "action": self.action,
            "look_for": self.look_for,
            "evidence_needed": self.evidence_needed,
            "red_flag": self.red_flag,
            "safe_if": self.safe_if,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationStep":
        """Create InvestigationStep from dictionary.

        Args:
            data: Dictionary with step fields

        Returns:
            InvestigationStep instance
        """
        return cls(
            step_number=int(data.get("step_number", 0)),
            action=str(data.get("action", "")),
            look_for=str(data.get("look_for", "")),
            evidence_needed=str(data.get("evidence_needed", "")),
            red_flag=data.get("red_flag"),
            safe_if=data.get("safe_if"),
        )


@dataclass
class ExploitReference:
    """Reference to a real-world exploit.

    Links findings to historical exploits, providing context about
    real-world impact and attack methodology.

    Attributes:
        id: Unique identifier (e.g., "the-dao-2016")
        name: Human-readable name (e.g., "The DAO Hack")
        date: Date of exploit in ISO format (e.g., "2016-06-17")
        loss: Estimated loss amount (e.g., "$60M")
        pattern_id: ID of the VKG pattern this exploit matches
        vulnerable_code: Relevant code snippet from the exploit
        exploit_summary: Brief description of what happened
        fix: How to prevent similar attacks
        source_url: Reference link (postmortem, analysis article)

    Usage:
        exploit = ExploitReference(
            id="the-dao-2016",
            name="The DAO Hack",
            date="2016-06-17",
            loss="$60M",
            pattern_id="reentrancy-classic",
            vulnerable_code="function splitDAO(...) { ... }",
            exploit_summary="Recursive call in splitDAO before balance update",
            fix="Use nonReentrant modifier or Checks-Effects-Interactions",
            source_url="https://hackingdistributed.com/..."
        )
    """
    id: str
    name: str
    date: str
    loss: str
    pattern_id: str
    vulnerable_code: str
    exploit_summary: str
    fix: str
    source_url: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON encoding
        """
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "loss": self.loss,
            "pattern_id": self.pattern_id,
            "vulnerable_code": self.vulnerable_code,
            "exploit_summary": self.exploit_summary,
            "fix": self.fix,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExploitReference":
        """Create ExploitReference from dictionary.

        Args:
            data: Dictionary with exploit fields

        Returns:
            ExploitReference instance
        """
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            date=str(data.get("date", "")),
            loss=str(data.get("loss", "")),
            pattern_id=str(data.get("pattern_id", "")),
            vulnerable_code=str(data.get("vulnerable_code", "")),
            exploit_summary=str(data.get("exploit_summary", "")),
            fix=str(data.get("fix", "")),
            source_url=str(data.get("source_url", "")),
        )

    @classmethod
    def from_exploit_record(
        cls,
        record: Any,  # ExploitRecord from adversarial_kg
        pattern_id: str,
        vulnerable_code: str = "",
        fix: str = "",
    ) -> "ExploitReference":
        """Create ExploitReference from an ExploitRecord.

        Integration point with adversarial_kg.ExploitRecord.

        Args:
            record: ExploitRecord from adversarial_kg
            pattern_id: VKG pattern ID to link
            vulnerable_code: Code snippet (optional, may not be in record)
            fix: Remediation guidance (optional)

        Returns:
            ExploitReference instance
        """
        return cls(
            id=record.id,
            name=record.name,
            date=record.date,
            loss=f"${record.loss_usd:,}",
            pattern_id=pattern_id,
            vulnerable_code=vulnerable_code,
            exploit_summary=record.attack_summary,
            fix=fix or "See postmortem for remediation guidance",
            source_url=record.postmortem_url or "",
        )


@dataclass
class Verdict:
    """A verdict on a finding.

    Represents the final determination about whether a finding is a
    true vulnerability, false positive, or inconclusive.

    Attributes:
        type: Type of verdict (TRUE_POSITIVE, FALSE_POSITIVE, INCONCLUSIVE)
        reason: Human-readable explanation of the verdict
        confidence: Confidence score from 0.0 to 1.0
        evidence: List of supporting evidence for the verdict
        timestamp: When the verdict was made (defaults to now)
        auditor_id: Identifier of the auditor/agent making the verdict

    Usage:
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed via PoC execution",
            confidence=0.99,
            evidence=[
                "External call to user-controlled address",
                "State update occurs after external call",
                "No reentrancy guard present"
            ],
            auditor_id="vkg-tier-b"
        )
    """
    type: VerdictType
    reason: str
    confidence: float
    evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    auditor_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON encoding
        """
        return {
            "type": self.type.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
            "auditor_id": self.auditor_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Verdict":
        """Create Verdict from dictionary.

        Args:
            data: Dictionary with verdict fields

        Returns:
            Verdict instance
        """
        timestamp_str = data.get("timestamp")
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = datetime.now()

        return cls(
            type=VerdictType(data.get("type", "inconclusive")),
            reason=str(data.get("reason", "")),
            confidence=float(data.get("confidence", 0.0)),
            evidence=list(data.get("evidence", [])),
            timestamp=timestamp,
            auditor_id=data.get("auditor_id"),
        )

    @property
    def is_positive(self) -> bool:
        """Whether this is a true positive verdict."""
        return self.type == VerdictType.TRUE_POSITIVE

    @property
    def is_negative(self) -> bool:
        """Whether this is a false positive verdict."""
        return self.type == VerdictType.FALSE_POSITIVE


@dataclass
class Finding:
    """A potential vulnerability finding from pattern matching.

    This is the INPUT to the Beads system - what the pattern engine produces.
    Findings are the raw output that gets enriched into VulnerabilityBeads
    (defined in Task 6.1).

    Attributes:
        id: Unique identifier (e.g., "VKG-001")
        pattern_id: Which pattern matched (e.g., "vm-001")
        function_id: Function node ID in the knowledge graph
        contract_name: Name of the contract
        function_name: Name of the function
        file_path: Path to the source file
        line_number: Primary line number of the finding
        severity: Severity level
        confidence: Confidence score from pattern (0.0-1.0)
        vulnerability_class: Category (e.g., "reentrancy", "access-control")
        description: Human-readable description
        evidence: List of supporting evidence strings

    Usage:
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_vault_withdraw",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.CRITICAL,
            confidence=0.95,
            vulnerability_class="reentrancy",
            description="State update after external call detected",
            evidence=["External call at line 48", "Balance write at line 52"]
        )
    """
    id: str
    pattern_id: str
    function_id: str
    contract_name: str
    function_name: str
    file_path: str
    line_number: int
    severity: Severity
    confidence: float
    vulnerability_class: str
    description: str
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON encoding
        """
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "function_id": self.function_id,
            "contract_name": self.contract_name,
            "function_name": self.function_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "vulnerability_class": self.vulnerability_class,
            "description": self.description,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Create Finding from dictionary.

        Args:
            data: Dictionary with finding fields

        Returns:
            Finding instance
        """
        severity = data.get("severity", "medium")
        if isinstance(severity, str):
            severity = Severity.from_string(severity)
        elif isinstance(severity, Severity):
            pass
        else:
            severity = Severity.MEDIUM

        return cls(
            id=str(data.get("id", "")),
            pattern_id=str(data.get("pattern_id", "")),
            function_id=str(data.get("function_id", "")),
            contract_name=str(data.get("contract_name", "")),
            function_name=str(data.get("function_name", "")),
            file_path=str(data.get("file_path", "")),
            line_number=int(data.get("line_number", 0)),
            severity=severity,
            confidence=float(data.get("confidence", 0.0)),
            vulnerability_class=str(data.get("vulnerability_class", "")),
            description=str(data.get("description", "")),
            evidence=list(data.get("evidence", [])),
        )

    @classmethod
    def from_pattern_match(
        cls,
        match: Dict[str, Any],
        graph: "KnowledgeGraph",
        finding_id: Optional[str] = None,
    ) -> "Finding":
        """Create a Finding from a PatternEngine match result.

        Integration point: This is how pattern matching connects to beads.

        Args:
            match: Match result from PatternEngine.run()
            graph: KnowledgeGraph containing the matched node
            finding_id: Optional custom ID (auto-generated if not provided)

        Returns:
            Finding instance

        Usage:
            engine = PatternEngine()
            matches = engine.run(graph, patterns)
            findings = [Finding.from_pattern_match(m, graph) for m in matches]
        """
        from pathlib import Path
        import hashlib

        node_id = match.get("node_id", "")
        node = graph.nodes.get(node_id)

        if node is None:
            raise ValueError(f"Node not found in graph: {node_id}")

        props = node.properties

        # Extract location from evidence
        file_path = ""
        line_number = 0
        if node.evidence:
            ev = node.evidence[0]
            file_path = ev.file
            line_number = ev.line_start or 0

        # Generate finding ID if not provided
        if finding_id is None:
            # Create deterministic ID from pattern + node
            hash_input = f"{match.get('pattern_id', '')}:{node_id}"
            hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
            finding_id = f"VKG-{hash_hex.upper()}"

        # Map severity
        severity_str = match.get("severity", "medium")
        try:
            severity = Severity.from_string(severity_str)
        except ValueError:
            severity = Severity.MEDIUM

        # Extract evidence from explain if available
        evidence = []
        if "explain" in match and match["explain"]:
            explain = match["explain"]
            for key in ["all", "any", "ops_all", "ops_any"]:
                if key in explain:
                    for item in explain[key]:
                        if isinstance(item, dict) and item.get("matched"):
                            evidence.append(
                                f"{item.get('property', item.get('condition_type', 'unknown'))}: "
                                f"{item.get('actual', item.get('expected', 'matched'))}"
                            )

        # Get contract name from node properties or label
        contract_name = props.get("contract_name", "")
        if not contract_name and "." in node.label:
            contract_name = node.label.split(".")[0]

        # Get function name
        function_name = props.get("name", node.label)
        if "." in function_name:
            function_name = function_name.split(".")[-1]

        # Map pattern lens to vulnerability class
        lens = match.get("lens", [])
        vuln_class = lens[0].lower().replace("-", "_") if lens else "unknown"

        return cls(
            id=finding_id,
            pattern_id=match.get("pattern_id", ""),
            function_id=node_id,
            contract_name=contract_name,
            function_name=function_name,
            file_path=file_path,
            line_number=line_number,
            severity=severity,
            confidence=props.get("confidence", 0.8),
            vulnerability_class=vuln_class,
            description=f"Pattern '{match.get('pattern_name', match.get('pattern_id', ''))}' matched",
            evidence=evidence,
        )

    @property
    def location(self) -> str:
        """Human-readable location string.

        Returns:
            Location like "Vault.withdraw():45"
        """
        return f"{self.contract_name}.{self.function_name}():{self.line_number}"

    @property
    def is_critical(self) -> bool:
        """Whether this is a critical severity finding."""
        return self.severity == Severity.CRITICAL

    @property
    def is_high_severity(self) -> bool:
        """Whether this is critical or high severity."""
        return self.severity in (Severity.CRITICAL, Severity.HIGH)
