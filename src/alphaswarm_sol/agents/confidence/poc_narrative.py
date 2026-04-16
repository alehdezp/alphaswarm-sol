"""PoC Narrative Generator (SDK-15).

This module generates exploit narratives for attacker claims:
- Structured narratives for report presentation
- LLM-generated narratives from bead evidence
- Synchronous fallback for offline generation

Per PHILOSOPHY.md Pool walkthrough (line 509):
- Generate exploit PoC narratives for attacker claims
- Used in debate protocol for evidence presentation

Usage:
    from alphaswarm_sol.agents.confidence import PoCNarrativeGenerator, ExploitNarrative

    generator = PoCNarrativeGenerator(runtime)
    narrative = await generator.generate_narrative(bead, test_result)

    # Or synchronous fallback
    narrative = generator.from_bead_directly(bead)

    # Render as markdown for reports
    markdown = narrative.to_markdown()
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import logging
import re

from alphaswarm_sol.agents.runtime import AgentRuntime, AgentConfig, AgentRole
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.agents.roles import GeneratedTest

logger = logging.getLogger(__name__)


@dataclass
class ExploitNarrative:
    """Structured exploit narrative for attacker claims.

    Provides a comprehensive narrative of how a vulnerability
    can be exploited, suitable for reports and debate protocol.

    Attributes:
        bead_id: ID of the bead this narrative is for
        title: Descriptive title (includes contract name)
        vulnerability_summary: 1-2 sentence summary
        attack_steps: Numbered, actionable attack steps
        prerequisites: What the attacker needs
        economic_impact: Realistic estimate of damage
        poc_reference: Path to test file (optional)
        mitigation: How to fix the vulnerability
    """

    bead_id: str
    title: str
    vulnerability_summary: str
    attack_steps: List[str]
    prerequisites: List[str]
    economic_impact: str
    poc_reference: Optional[str] = None  # Test file path
    mitigation: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead_id,
            "title": self.title,
            "vulnerability_summary": self.vulnerability_summary,
            "attack_steps": self.attack_steps,
            "prerequisites": self.prerequisites,
            "economic_impact": self.economic_impact,
            "poc_reference": self.poc_reference,
            "mitigation": self.mitigation,
        }

    def to_markdown(self) -> str:
        """Render as markdown for reports.

        Returns:
            Formatted markdown string suitable for audit reports
        """
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(self.attack_steps))
        prereqs = "\n".join(f"- {p}" for p in self.prerequisites)

        return f"""# {self.title}

## Summary
{self.vulnerability_summary}

## Attack Steps
{steps}

## Prerequisites
{prereqs}

## Economic Impact
{self.economic_impact}

## PoC
{"See: " + self.poc_reference if self.poc_reference else "No PoC available"}

## Mitigation
{self.mitigation}
"""


POC_NARRATIVE_PROMPT = """Generate an exploit narrative for the following vulnerability.

## Vulnerability
- **ID:** {bead_id}
- **Class:** {vuln_class}
- **Severity:** {severity}

## Pattern Match
{why_flagged}

## Vulnerable Code
```solidity
{code}
```

## Test Evidence
{test_evidence}

## Instructions
Create a structured exploit narrative with:
1. Title (descriptive, includes contract name)
2. Vulnerability summary (1-2 sentences)
3. Attack steps (numbered, actionable)
4. Prerequisites (what attacker needs)
5. Economic impact (realistic estimate)
6. Mitigation (how to fix)

Format as JSON:
{{
  "title": "...",
  "vulnerability_summary": "...",
  "attack_steps": ["1. ...", "2. ..."],
  "prerequisites": ["..."],
  "economic_impact": "...",
  "mitigation": "..."
}}
"""


class PoCNarrativeGenerator:
    """Generates exploit PoC narratives for attacker claims.

    Per PHILOSOPHY.md Pool walkthrough (line 509):
    - Generate exploit PoC narratives for attacker claims
    - Used in debate protocol for evidence presentation

    Can generate narratives in two ways:
    1. LLM-generated: Uses AgentRuntime to produce rich narratives
    2. Direct extraction: Synchronous fallback from bead data

    Example:
        # With LLM
        generator = PoCNarrativeGenerator(runtime)
        narrative = await generator.generate_narrative(bead, test_result)

        # Without LLM (synchronous fallback)
        narrative = generator.from_bead_directly(bead)
    """

    def __init__(self, runtime: AgentRuntime):
        """Initialize the generator.

        Args:
            runtime: AgentRuntime for LLM calls
        """
        self.runtime = runtime

    async def generate_narrative(
        self,
        bead: VulnerabilityBead,
        test_result: Optional[GeneratedTest] = None,
    ) -> ExploitNarrative:
        """Generate narrative from bead and optional test result.

        Uses LLM to produce a rich, detailed narrative based on
        the vulnerability evidence.

        Args:
            bead: The vulnerability bead
            test_result: Optional test result for evidence (optional)

        Returns:
            ExploitNarrative with structured fields
        """

        test_evidence = "No test available"
        poc_reference = None
        if test_result:
            if test_result.test_passed:
                test_evidence = f"Test PASSED: {test_result.expected_outcome}"
            else:
                test_evidence = "Test attempted but failed"
            poc_reference = test_result.test_file

        prompt = POC_NARRATIVE_PROMPT.format(
            bead_id=bead.id,
            vuln_class=bead.vulnerability_class,
            severity=bead.severity.value,
            why_flagged=bead.pattern_context.why_flagged,
            code=bead.vulnerable_code.source[:500],  # Truncate for context
            test_evidence=test_evidence,
        )

        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="You are an expert at explaining security vulnerabilities and their exploits.",
            tools=[],
        )

        response = await self.runtime.spawn_agent(config, prompt)

        # Parse JSON from response
        narrative_data = self._parse_json(response.content)

        return ExploitNarrative(
            bead_id=bead.id,
            title=narrative_data.get("title", f"Exploit: {bead.vulnerability_class}"),
            vulnerability_summary=narrative_data.get(
                "vulnerability_summary", bead.pattern_context.why_flagged
            ),
            attack_steps=narrative_data.get("attack_steps", []),
            prerequisites=narrative_data.get("prerequisites", []),
            economic_impact=narrative_data.get("economic_impact", "Unknown"),
            poc_reference=poc_reference,
            mitigation=narrative_data.get("mitigation", ""),
        )

    def _parse_json(self, response: str) -> Dict:
        """Extract JSON from LLM response.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict or empty dict if parsing fails
        """
        # Try to find JSON block - handle nested objects
        # Find the first { and last }
        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1 and end > start:
            json_str = response[start : end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Fallback: try simple pattern
        match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: try parsing entire response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def from_bead_directly(self, bead: VulnerabilityBead) -> ExploitNarrative:
        """Create narrative directly from bead without LLM (synchronous fallback).

        Extracts narrative information directly from bead fields
        without making any LLM calls. Useful for offline operation
        or when LLM is unavailable.

        Args:
            bead: The vulnerability bead

        Returns:
            ExploitNarrative with structured fields from bead data
        """
        # Parse attack steps from attack_scenario
        attack_steps = []
        if bead.test_context.attack_scenario:
            # Split by newlines or numbered patterns
            lines = bead.test_context.attack_scenario.split("\n")
            for line in lines:
                line = line.strip()
                if line:
                    # Remove leading numbers/bullets
                    cleaned = re.sub(r"^[\d\.\-\*]+\s*", "", line)
                    if cleaned:
                        attack_steps.append(cleaned)

        # Use setup_requirements as prerequisites
        prerequisites = list(bead.test_context.setup_requirements)

        # Build mitigation from recommendations
        mitigation = ""
        if bead.fix_recommendations:
            mitigation = "; ".join(bead.fix_recommendations)
        else:
            mitigation = "Apply standard mitigations for this vulnerability class"

        return ExploitNarrative(
            bead_id=bead.id,
            title=f"{bead.vulnerability_class.replace('_', ' ').title()} in {bead.vulnerable_code.contract_name}",
            vulnerability_summary=bead.pattern_context.why_flagged,
            attack_steps=attack_steps if attack_steps else ["See attack scenario in bead context"],
            prerequisites=prerequisites if prerequisites else ["Standard attacker capabilities"],
            economic_impact=f"Severity: {bead.severity.value}",
            poc_reference=None,
            mitigation=mitigation,
        )


__all__ = [
    "ExploitNarrative",
    "PoCNarrativeGenerator",
]
