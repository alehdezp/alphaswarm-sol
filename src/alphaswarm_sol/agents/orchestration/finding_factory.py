"""Factory for creating finding beads from vuln-discovery results.

FindingBeadFactory produces VulnerabilityBeads with complete evidence chains,
linking findings back to their originating context beads.

Per 05.5-06 plan requirements:
- Evidence chain includes code locations, vulndoc ref, reasoning, VQL queries
- Confidence levels map to floats (confirmed=0.95, likely=0.80, uncertain=0.60, rejected=0.20)
- Finding beads saved to pool/findings/ directory
- Bidirectional linking between finding and context beads

Usage:
    from alphaswarm_sol.agents.orchestration import FindingBeadFactory, FindingInput, EvidenceChain
    from alphaswarm_sol.beads import Severity

    # Create factory
    factory = FindingBeadFactory(beads_dir=".vrs/beads")

    # Define evidence chain
    evidence = EvidenceChain(
        code_locations=["Vault.sol:52-55"],
        vulndoc_reference="reentrancy/classic",
        reasoning_steps=["1. External call found...", "2. State update after..."],
        vql_queries=["FIND functions WHERE ..."],
        protocol_context_applied=["Access risks: admin multisig"],
        confidence="confirmed",
        confidence_reason="CEI pattern violated"
    )

    # Define finding input
    finding_input = FindingInput(
        vulnerability_class="reentrancy",
        severity=Severity.CRITICAL,
        summary="Classic reentrancy in withdraw()",
        evidence_chain=evidence,
        context_bead_id="CTX-abc123",
        pool_id="POOL-001"
    )

    # Create and save finding
    bead = factory.create_finding(finding_input, context_bead)
    path = factory.save_finding(bead)
    factory.link_to_context_bead(bead, context_bead)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from alphaswarm_sol.beads.context_merge import ContextMergeBead
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    CodeSnippet,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import (
    Severity,
    BeadStatus,
    InvestigationStep,
    ExploitReference,
)


@dataclass
class EvidenceChain:
    """Complete evidence chain for a finding.

    Attributes:
        code_locations: List of locations (e.g., ["Vault.sol:52-55"])
        vulndoc_reference: Vulndoc ID (e.g., "reentrancy/classic")
        reasoning_steps: Step-by-step reasoning
        vql_queries: VQL queries executed to find evidence
        protocol_context_applied: Relevant protocol context used
        confidence: Confidence level (confirmed/likely/uncertain/rejected)
        confidence_reason: Explanation for confidence level
    """
    code_locations: List[str]
    vulndoc_reference: str
    reasoning_steps: List[str]
    vql_queries: List[str]
    protocol_context_applied: List[str]
    confidence: str  # confirmed, likely, uncertain, rejected
    confidence_reason: str


@dataclass
class FindingInput:
    """Input for creating a finding bead.

    Attributes:
        vulnerability_class: Category (e.g., "reentrancy", "access-control")
        severity: Severity level
        summary: One-line finding summary
        evidence_chain: Complete evidence chain
        context_bead_id: ID of originating context bead
        pool_id: Pool this finding belongs to
    """
    vulnerability_class: str
    severity: Severity
    summary: str
    evidence_chain: EvidenceChain
    context_bead_id: str
    pool_id: Optional[str] = None


class FindingBeadFactory:
    """Factory for creating finding beads from discovery results.

    Converts FindingInput instances into full VulnerabilityBeads with
    complete investigation context and evidence chains.

    Attributes:
        beads_dir: Base directory for storing beads
    """

    # Confidence mapping
    CONFIDENCE_MAP = {
        "confirmed": 0.95,
        "likely": 0.80,
        "uncertain": 0.60,
        "rejected": 0.20,
    }

    def __init__(self, beads_dir: Path | str):
        """Initialize factory.

        Args:
            beads_dir: Directory for storing beads
        """
        self.beads_dir = Path(beads_dir)
        self.beads_dir.mkdir(parents=True, exist_ok=True)

    def create_finding(
        self,
        finding: FindingInput,
        context_bead: ContextMergeBead,
    ) -> VulnerabilityBead:
        """Create a finding bead from discovery input.

        Args:
            finding: FindingInput with evidence chain
            context_bead: Originating context bead

        Returns:
            VulnerabilityBead with full investigation context
        """
        # Generate bead ID
        bead_id = self._generate_id(finding, context_bead)

        # Map confidence
        confidence = self.CONFIDENCE_MAP.get(
            finding.evidence_chain.confidence.lower(),
            0.60
        )

        # Extract first code location for vulnerable_code snippet
        code_location = finding.evidence_chain.code_locations[0] if finding.evidence_chain.code_locations else ""
        vulnerable_code = self._create_code_snippet(code_location, finding.summary)

        # Build pattern context from evidence chain
        pattern_context = PatternContext(
            pattern_name=finding.vulnerability_class,
            pattern_description=f"Detected via {finding.evidence_chain.vulndoc_reference}",
            why_flagged=finding.summary,
            matched_properties=finding.evidence_chain.vql_queries,
            evidence_lines=[self._extract_line_number(loc) for loc in finding.evidence_chain.code_locations],
        )

        # Build investigation guide from reasoning steps
        investigation_guide = InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=i + 1,
                    action=step,
                    look_for="",
                    evidence_needed="",
                )
                for i, step in enumerate(finding.evidence_chain.reasoning_steps)
            ],
            questions_to_answer=[
                "Is this a true positive?",
                "What is the attack scenario?",
            ],
            common_false_positives=[],
            key_indicators=finding.evidence_chain.code_locations,
            safe_patterns=[],
        )

        # Build test context (placeholder)
        test_context = TestContext(
            scaffold_code="// TODO: Add PoC test",
            attack_scenario="\n".join(finding.evidence_chain.reasoning_steps),
            setup_requirements=["Deploy target contract"],
            expected_outcome=finding.summary,
        )

        # Create bead
        bead = VulnerabilityBead(
            id=bead_id,
            vulnerability_class=finding.vulnerability_class,
            pattern_id=finding.evidence_chain.vulndoc_reference,
            severity=finding.severity,
            confidence=confidence,
            vulnerable_code=vulnerable_code,
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=pattern_context,
            investigation_guide=investigation_guide,
            test_context=test_context,
            similar_exploits=[],
            fix_recommendations=[],
            status=BeadStatus.PENDING,
            pool_id=finding.pool_id,
            metadata={
                "context_bead_id": finding.context_bead_id,
                "evidence_chain": {
                    "code_locations": finding.evidence_chain.code_locations,
                    "vulndoc_reference": finding.evidence_chain.vulndoc_reference,
                    "reasoning_steps": finding.evidence_chain.reasoning_steps,
                    "vql_queries": finding.evidence_chain.vql_queries,
                    "protocol_context_applied": finding.evidence_chain.protocol_context_applied,
                    "confidence": finding.evidence_chain.confidence,
                    "confidence_reason": finding.evidence_chain.confidence_reason,
                },
                "protocol_name": context_bead.protocol_name,
            },
        )

        return bead

    def _generate_id(
        self,
        finding: FindingInput,
        context_bead: ContextMergeBead,
    ) -> str:
        """Generate deterministic bead ID.

        Args:
            finding: FindingInput instance
            context_bead: Context bead

        Returns:
            Bead ID in format VKG-{hash}
        """
        content = f"{context_bead.id}:{finding.vulnerability_class}:{finding.summary}:{datetime.now().isoformat()}"
        return f"VKG-{hashlib.sha256(content.encode()).hexdigest()[:12].upper()}"

    def _create_code_snippet(self, location: str, summary: str) -> CodeSnippet:
        """Create a CodeSnippet from location string.

        Args:
            location: Location like "Vault.sol:52-55"
            summary: Finding summary for source

        Returns:
            CodeSnippet instance
        """
        # Parse location
        if ":" in location:
            file_part, line_part = location.split(":", 1)
            if "-" in line_part:
                start, end = line_part.split("-")
                start_line = int(start)
                end_line = int(end)
            else:
                start_line = end_line = int(line_part)
        else:
            file_part = location
            start_line = end_line = 0

        return CodeSnippet(
            source=f"// {summary}",
            file_path=file_part,
            start_line=start_line,
            end_line=end_line,
        )

    def _extract_line_number(self, location: str) -> int:
        """Extract line number from location string.

        Args:
            location: Location like "Vault.sol:52-55"

        Returns:
            Starting line number (0 if not found)
        """
        if ":" in location:
            line_part = location.split(":", 1)[1]
            if "-" in line_part:
                return int(line_part.split("-")[0])
            return int(line_part)
        return 0

    def save_finding(self, bead: VulnerabilityBead) -> Path:
        """Save finding bead to disk.

        Saves to pool-specific directory if pool_id is set,
        otherwise saves to general findings/ directory.

        Args:
            bead: VulnerabilityBead to save

        Returns:
            Path to saved bead file
        """
        # Determine save location
        if bead.pool_id:
            save_dir = self.beads_dir / bead.pool_id / "findings"
        else:
            save_dir = self.beads_dir / "findings"

        save_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        save_path = save_dir / f"{bead.id}.json"
        with open(save_path, "w") as f:
            f.write(bead.to_json())

        return save_path

    def link_to_context_bead(
        self,
        finding_bead: VulnerabilityBead,
        context_bead: ContextMergeBead,
    ) -> None:
        """Link finding bead to its context bead.

        Updates context bead's finding_bead_ids list and saves it.

        Args:
            finding_bead: Finding bead to link
            context_bead: Context bead to link to
        """
        # Add finding ID to context bead
        context_bead.add_finding_bead(finding_bead.id)

        # Save updated context bead
        if context_bead.pool_id:
            context_dir = self.beads_dir / context_bead.pool_id / "context"
        else:
            context_dir = self.beads_dir / "context"

        context_dir.mkdir(parents=True, exist_ok=True)
        context_path = context_dir / f"{context_bead.id}.json"

        with open(context_path, "w") as f:
            f.write(context_bead.to_json())
