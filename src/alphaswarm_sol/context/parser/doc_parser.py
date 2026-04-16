"""LLM-driven document parser for protocol context extraction.

This module provides LLM-powered extraction of protocol context from
documentation. It parses various document formats to extract:
- Roles and capabilities
- Assumptions and trust requirements
- Invariants (formal + natural language)
- Economic context (incentives, value flows, tokenomics)
- Governance details
- Security claims and questions

Per 03-CONTEXT.md: "Fully LLM-driven (most flexible, handles varied doc formats)"

The parser uses the existing LLMClient infrastructure and returns
typed context objects with confidence levels based on source tier.

Usage:
    from alphaswarm_sol.context.parser import DocParser, DocParseResult
    from alphaswarm_sol.context.parser import WebFetcher, FetchedDocument

    # Fetch documents
    fetcher = WebFetcher(Path("/path/to/project"))
    docs = await fetcher.fetch_all()

    # Parse with LLM
    parser = DocParser()
    for doc in docs:
        result = await parser.parse(doc)
        for role in result.roles:
            print(f"Role: {role.name}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..types import (
    Assumption,
    Confidence,
    Invariant,
    OffchainInput,
    Role,
    ValueFlow,
)

if TYPE_CHECKING:
    from alphaswarm_sol.llm.client import LLMClient
    from .web_fetcher import FetchedDocument, SourceTier


# =============================================================================
# DocParseResult
# =============================================================================


@dataclass
class DocParseResult:
    """Result of LLM-driven document parsing.

    Contains all context elements extracted from a document using
    LLM reasoning. Each element includes confidence levels based
    on source tier and extraction certainty.

    Attributes:
        roles: Extracted protocol roles with capabilities
        assumptions: Protocol assumptions with metadata
        invariants: Both formal and natural language invariants
        incentives: Economic incentive descriptions
        value_flows: Economic value movement patterns
        governance: Governance-related information
        tokenomics_summary: Summary of tokenomics if found
        security_claims: Claims about security properties
        questions: Generated questions for security gaps
        source: Source document URL/path
        source_tier: Reliability tier of source
        warnings: Issues found during parsing
        raw_extraction: Raw LLM output for debugging

    Usage:
        result = await parser.parse(doc)
        print(f"Extracted {len(result.roles)} roles")
        print(f"Questions: {result.questions}")
    """
    roles: List[Role] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    invariants: List[Invariant] = field(default_factory=list)
    incentives: List[str] = field(default_factory=list)
    value_flows: List[ValueFlow] = field(default_factory=list)
    governance: Dict[str, Any] = field(default_factory=dict)
    tokenomics_summary: str = ""
    security_claims: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    source: str = ""
    source_tier: int = 3
    warnings: List[str] = field(default_factory=list)
    raw_extraction: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "roles": [r.to_dict() for r in self.roles],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "invariants": [i.to_dict() for i in self.invariants],
            "incentives": self.incentives,
            "value_flows": [v.to_dict() for v in self.value_flows],
            "governance": self.governance,
            "tokenomics_summary": self.tokenomics_summary,
            "security_claims": self.security_claims,
            "questions": self.questions,
            "source": self.source,
            "source_tier": self.source_tier,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocParseResult":
        """Create DocParseResult from dictionary.

        Args:
            data: Dictionary with result data

        Returns:
            DocParseResult instance
        """
        return cls(
            roles=[Role.from_dict(r) for r in data.get("roles", [])],
            assumptions=[Assumption.from_dict(a) for a in data.get("assumptions", [])],
            invariants=[Invariant.from_dict(i) for i in data.get("invariants", [])],
            incentives=list(data.get("incentives", [])),
            value_flows=[ValueFlow.from_dict(v) for v in data.get("value_flows", [])],
            governance=dict(data.get("governance", {})),
            tokenomics_summary=str(data.get("tokenomics_summary", "")),
            security_claims=list(data.get("security_claims", [])),
            questions=list(data.get("questions", [])),
            source=str(data.get("source", "")),
            source_tier=int(data.get("source_tier", 3)),
            warnings=list(data.get("warnings", [])),
        )

    def merge(self, other: "DocParseResult") -> "DocParseResult":
        """Merge another DocParseResult into this one.

        Combines results from multiple document parses, deduplicating
        where appropriate.

        Args:
            other: Another DocParseResult to merge

        Returns:
            New merged DocParseResult
        """
        # Merge roles by name
        role_map: Dict[str, Role] = {r.name: r for r in self.roles}
        for role in other.roles:
            if role.name in role_map:
                existing = role_map[role.name]
                combined_caps = list(set(existing.capabilities + role.capabilities))
                combined_trust = list(set(existing.trust_assumptions + role.trust_assumptions))
                role_map[role.name] = Role(
                    name=role.name,
                    capabilities=combined_caps,
                    trust_assumptions=combined_trust,
                    confidence=min(existing.confidence, role.confidence),
                    description=existing.description or role.description,
                )
            else:
                role_map[role.name] = role

        # Merge assumptions (dedupe by description)
        seen_assumptions: set[str] = {a.description for a in self.assumptions}
        combined_assumptions = list(self.assumptions)
        for assumption in other.assumptions:
            if assumption.description not in seen_assumptions:
                combined_assumptions.append(assumption)
                seen_assumptions.add(assumption.description)

        # Merge invariants (dedupe by natural language)
        seen_invariants: set[str] = {i.natural_language for i in self.invariants}
        combined_invariants = list(self.invariants)
        for invariant in other.invariants:
            if invariant.natural_language not in seen_invariants:
                combined_invariants.append(invariant)
                seen_invariants.add(invariant.natural_language)

        # Merge value flows (dedupe by name)
        seen_flows: set[str] = {v.name for v in self.value_flows}
        combined_flows = list(self.value_flows)
        for flow in other.value_flows:
            if flow.name not in seen_flows:
                combined_flows.append(flow)
                seen_flows.add(flow.name)

        # Merge other fields
        combined_incentives = list(set(self.incentives + other.incentives))
        combined_security = list(set(self.security_claims + other.security_claims))
        combined_questions = list(set(self.questions + other.questions))
        combined_warnings = list(set(self.warnings + other.warnings))

        # Merge governance (prefer non-empty)
        combined_governance = self.governance.copy()
        for key, value in other.governance.items():
            if key not in combined_governance or not combined_governance[key]:
                combined_governance[key] = value

        # Use higher-tier tokenomics summary
        tokenomics = self.tokenomics_summary
        if not tokenomics or (other.tokenomics_summary and other.source_tier < self.source_tier):
            tokenomics = other.tokenomics_summary

        return DocParseResult(
            roles=list(role_map.values()),
            assumptions=combined_assumptions,
            invariants=combined_invariants,
            incentives=combined_incentives,
            value_flows=combined_flows,
            governance=combined_governance,
            tokenomics_summary=tokenomics,
            security_claims=combined_security,
            questions=combined_questions,
            source=self.source,  # Keep original source
            source_tier=min(self.source_tier, other.source_tier),  # Use best tier
            warnings=combined_warnings,
        )


# =============================================================================
# Extraction Prompts
# =============================================================================


ROLE_EXTRACTION_SYSTEM = """You are a protocol security analyst extracting role information from documentation.

Extract ALL roles mentioned in the documentation, including:
- Administrative roles (owner, admin, governance)
- Operational roles (keeper, liquidator, oracle updater)
- User types (depositor, borrower, trader)
- Special roles (guardian, multisig, timelock)

For each role, identify:
1. The role name (lowercase, snake_case)
2. Capabilities: What can this role DO?
3. Trust assumptions: What trust is placed in this role?

Return JSON with this EXACT structure:
{
  "roles": [
    {
      "name": "role_name",
      "capabilities": ["capability1", "capability2"],
      "trust_assumptions": ["assumption1"],
      "description": "Brief description of the role"
    }
  ]
}

Be comprehensive. If a role can "pause the protocol", that's a capability.
If "the admin is a multisig", that's a trust assumption about the admin role."""


ASSUMPTION_EXTRACTION_SYSTEM = """You are a protocol security analyst extracting assumptions from documentation.

Extract ALL assumptions the protocol makes, including:
- Trust assumptions about external systems (oracles, bridges)
- Economic assumptions (liquidity, incentive alignment)
- Timing assumptions (block times, finality)
- Behavioral assumptions (users, admins, governance)

For each assumption, identify:
1. The assumption description
2. Category: trust, economic, timing, access, price, or other
3. Which functions/features this affects
4. Tags for categorization

Return JSON with this EXACT structure:
{
  "assumptions": [
    {
      "description": "Full description of the assumption",
      "category": "category",
      "affects_functions": ["function1", "function2"],
      "tags": ["tag1", "tag2"]
    }
  ]
}

Be thorough. If the docs say "oracle prices are updated every heartbeat", that's an assumption about timing AND price accuracy."""


INVARIANT_EXTRACTION_SYSTEM = """You are a protocol security analyst extracting invariants from documentation.

Extract ALL invariants mentioned or implied in the documentation:
- Supply invariants (totalSupply == sum of balances)
- Balance invariants (user balance >= 0)
- Economic invariants (collateral >= debt)
- Access invariants (only owner can pause)

For each invariant, provide:
1. A semi-formal representation (what, must, value)
2. Natural language description
3. Category: supply, balance, economic, access, or other
4. Whether it's critical (violation = protocol failure)

Return JSON with this EXACT structure:
{
  "invariants": [
    {
      "formal": {"what": "property", "must": "operator", "value": "expression"},
      "natural_language": "Human readable description",
      "category": "category",
      "critical": true
    }
  ]
}

Operators for formal: eq, neq, gt, gte, lt, lte, in, notin

Example: {"what": "collateralValue", "must": "gte", "value": "debtValue"}"""


ECONOMICS_EXTRACTION_SYSTEM = """You are a protocol security analyst extracting economic information from documentation.

Extract ALL economic-relevant information:
- Incentive mechanisms (fees, rewards, penalties)
- Value flows (deposits, withdrawals, distributions)
- Tokenomics (supply, emissions, burns)
- Governance economics (voting power, timelock)

Return JSON with this EXACT structure:
{
  "incentives": [
    "Description of incentive mechanism"
  ],
  "value_flows": [
    {
      "name": "flow_name",
      "from": "source_role",
      "to": "destination_role",
      "asset": "asset_type",
      "conditions": ["condition1"],
      "description": "Description of the flow"
    }
  ],
  "tokenomics_summary": "Brief summary of tokenomics model",
  "governance": {
    "voting_threshold": "value if mentioned",
    "timelock_duration": "duration if mentioned",
    "upgrade_mechanism": "how upgrades work"
  }
}

Be specific about who pays, who receives, and under what conditions."""


SECURITY_EXTRACTION_SYSTEM = """You are a protocol security analyst extracting security claims and identifying gaps.

Extract ALL security-related claims from the documentation:
- Claimed security properties ("funds are never at risk")
- Mentioned protections ("reentrancy guards on all state-changing functions")
- Security assumptions ("oracle cannot be manipulated")

Also identify GAPS - questions about security that the documentation doesn't answer.

Return JSON with this EXACT structure:
{
  "security_claims": [
    "Specific security claim from documentation"
  ],
  "questions": [
    "Security-critical question not answered by docs"
  ]
}

Questions should be specific and actionable, like:
- "What happens if oracle returns 0?"
- "Who can upgrade the implementation contract?"
- "Is there a maximum withdrawal limit?"

NOT vague like "Is the protocol secure?"""


# =============================================================================
# Cross-Validation
# =============================================================================


@dataclass
class CrossValidationResult:
    """Result of cross-validating doc claims against code.

    Attributes:
        matches: Claims that match code behavior
        conflicts: Claims that conflict with code
        undetermined: Claims that couldn't be verified
    """
    matches: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, str]] = field(default_factory=list)
    undetermined: List[str] = field(default_factory=list)


# =============================================================================
# DocParser
# =============================================================================


class DocParser:
    """LLM-driven document parser for protocol context extraction.

    Uses LLMClient to extract structured protocol context from
    documentation. Supports various document formats and handles
    confidence scoring based on source tiers.

    Per 03-CONTEXT.md: "Fully LLM-driven (most flexible, handles varied doc formats)"

    Features:
    - Role and capability extraction
    - Assumption extraction with categorization
    - Invariant extraction (formal + natural language)
    - Economic context (incentives, value flows, tokenomics)
    - Governance details extraction
    - Cross-validation with code analysis
    - Security gap question generation

    Usage:
        from alphaswarm_sol.llm.client import LLMClient

        client = LLMClient()
        parser = DocParser(client)

        result = await parser.parse(document)
        for role in result.roles:
            print(f"Role: {role.name}, caps: {role.capabilities}")
    """

    def __init__(
        self,
        llm_client: Optional["LLMClient"] = None,
        max_content_length: int = 50000,
    ) -> None:
        """Initialize the document parser.

        Args:
            llm_client: LLMClient instance (created if not provided)
            max_content_length: Max chars to send to LLM at once
        """
        self._llm_client = llm_client
        self.max_content_length = max_content_length

    @property
    def llm_client(self) -> "LLMClient":
        """Get or create LLM client."""
        if self._llm_client is None:
            from alphaswarm_sol.llm.client import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    async def parse(
        self,
        document: "FetchedDocument",
        code_context: Optional[Dict[str, Any]] = None,
    ) -> DocParseResult:
        """Parse a document to extract protocol context.

        This is the main entry point for document parsing. It:
        1. Extracts roles using LLM
        2. Extracts assumptions using LLM
        3. Extracts invariants using LLM
        4. Extracts economic context using LLM
        5. Extracts security claims and generates questions
        6. Optionally cross-validates with code context

        Args:
            document: FetchedDocument to parse
            code_context: Optional code analysis results for cross-validation

        Returns:
            DocParseResult with all extracted context

        Usage:
            result = await parser.parse(doc)
            print(f"Roles: {[r.name for r in result.roles]}")
        """
        if not document.is_valid:
            return DocParseResult(
                source=document.source_url,
                source_tier=document.tier_value,
                warnings=[f"Invalid document: {document.fetch_error}"],
            )

        content = self._prepare_content(document.content)
        source_tier = document.tier_value

        # Run all extractions
        roles = await self.extract_roles(content, source_tier)
        assumptions = await self.extract_assumptions(content, source_tier)
        invariants = await self.extract_invariants(content, source_tier)
        economics = await self.extract_economics(content, source_tier)
        security = await self.extract_security(content)
        questions = await self.identify_gaps(content)

        # Build result
        result = DocParseResult(
            roles=roles,
            assumptions=assumptions,
            invariants=invariants,
            incentives=economics.get("incentives", []),
            value_flows=economics.get("value_flows", []),
            governance=economics.get("governance", {}),
            tokenomics_summary=economics.get("tokenomics_summary", ""),
            security_claims=security.get("security_claims", []),
            questions=questions,
            source=document.source_url,
            source_tier=source_tier,
        )

        # Cross-validate if code context provided
        if code_context:
            validation = await self.cross_validate(result, code_context)
            if validation.conflicts:
                result.warnings.extend([
                    f"Doc-code conflict: {c['claim']} vs {c['code']}"
                    for c in validation.conflicts
                ])

        return result

    def _prepare_content(self, content: str) -> str:
        """Prepare content for LLM processing.

        Truncates if needed and removes excessive whitespace.

        Args:
            content: Raw document content

        Returns:
            Prepared content string
        """
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)

        # Truncate if too long
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "\n\n[TRUNCATED]"

        return content

    def _tier_to_confidence(self, source_tier: int) -> Confidence:
        """Convert source tier to confidence level.

        Args:
            source_tier: Numeric tier (1=official, 2=audit, 3=community)

        Returns:
            Confidence level
        """
        if source_tier == 1:
            return Confidence.CERTAIN
        elif source_tier == 2:
            return Confidence.INFERRED  # Audits are good but external
        else:
            return Confidence.INFERRED  # Community sources need verification

    async def extract_roles(
        self,
        content: str,
        source_tier: int,
    ) -> List[Role]:
        """Extract roles from document content using LLM.

        Args:
            content: Document content
            source_tier: Source reliability tier

        Returns:
            List of extracted Role objects

        Usage:
            roles = await parser.extract_roles(content, 1)
            for role in roles:
                print(f"{role.name}: {role.capabilities}")
        """
        prompt = f"""Analyze this protocol documentation and extract all roles mentioned.

DOCUMENT:
{content}

Extract all roles with their capabilities and trust assumptions.
Return valid JSON."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=ROLE_EXTRACTION_SYSTEM,
            )

            confidence = self._tier_to_confidence(source_tier)
            roles: List[Role] = []

            for role_data in result.get("roles", []):
                role = Role(
                    name=str(role_data.get("name", "")).lower().replace(" ", "_"),
                    capabilities=list(role_data.get("capabilities", [])),
                    trust_assumptions=list(role_data.get("trust_assumptions", [])),
                    confidence=confidence,
                    description=str(role_data.get("description", "")),
                    source=f"doc:tier{source_tier}",
                )
                if role.name:  # Skip empty roles
                    roles.append(role)

            return roles

        except Exception as e:
            # Return empty list on error, don't crash
            return []

    async def extract_assumptions(
        self,
        content: str,
        source_tier: int,
    ) -> List[Assumption]:
        """Extract assumptions from document content using LLM.

        Args:
            content: Document content
            source_tier: Source reliability tier

        Returns:
            List of extracted Assumption objects

        Usage:
            assumptions = await parser.extract_assumptions(content, 1)
            for a in assumptions:
                print(f"{a.category}: {a.description}")
        """
        prompt = f"""Analyze this protocol documentation and extract all assumptions.

DOCUMENT:
{content}

Extract all assumptions the protocol makes about trust, economics, timing, etc.
Return valid JSON."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=ASSUMPTION_EXTRACTION_SYSTEM,
            )

            confidence = self._tier_to_confidence(source_tier)
            assumptions: List[Assumption] = []

            for ass_data in result.get("assumptions", []):
                assumption = Assumption(
                    description=str(ass_data.get("description", "")),
                    category=str(ass_data.get("category", "other")),
                    affects_functions=list(ass_data.get("affects_functions", [])),
                    confidence=confidence,
                    source=f"doc:tier{source_tier}",
                    tags=list(ass_data.get("tags", [])),
                )
                if assumption.description:  # Skip empty assumptions
                    assumptions.append(assumption)

            return assumptions

        except Exception as e:
            return []

    async def extract_invariants(
        self,
        content: str,
        source_tier: int,
    ) -> List[Invariant]:
        """Extract invariants from document content using LLM.

        Args:
            content: Document content
            source_tier: Source reliability tier

        Returns:
            List of extracted Invariant objects

        Usage:
            invariants = await parser.extract_invariants(content, 1)
            for inv in invariants:
                print(f"{inv.natural_language} ({inv.formal})")
        """
        prompt = f"""Analyze this protocol documentation and extract all invariants.

DOCUMENT:
{content}

Extract all invariants (properties that must always hold) mentioned or implied.
Return valid JSON."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=INVARIANT_EXTRACTION_SYSTEM,
            )

            confidence = self._tier_to_confidence(source_tier)
            invariants: List[Invariant] = []

            for inv_data in result.get("invariants", []):
                invariant = Invariant(
                    formal=dict(inv_data.get("formal", {})),
                    natural_language=str(inv_data.get("natural_language", "")),
                    confidence=confidence,
                    source=f"doc:tier{source_tier}",
                    category=str(inv_data.get("category", "")),
                    critical=bool(inv_data.get("critical", False)),
                )
                if invariant.natural_language:  # Skip empty invariants
                    invariants.append(invariant)

            return invariants

        except Exception as e:
            return []

    async def extract_economics(
        self,
        content: str,
        source_tier: int,
    ) -> Dict[str, Any]:
        """Extract economic context from document content.

        Extracts incentives, value flows, tokenomics, and governance details.

        Args:
            content: Document content
            source_tier: Source reliability tier

        Returns:
            Dict with incentives, value_flows, tokenomics_summary, governance

        Usage:
            economics = await parser.extract_economics(content, 1)
            print(f"Tokenomics: {economics['tokenomics_summary']}")
        """
        prompt = f"""Analyze this protocol documentation and extract economic information.

DOCUMENT:
{content}

Extract incentives, value flows, tokenomics, and governance details.
Return valid JSON."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=ECONOMICS_EXTRACTION_SYSTEM,
            )

            confidence = self._tier_to_confidence(source_tier)

            # Convert value flows to ValueFlow objects
            value_flows: List[ValueFlow] = []
            for flow_data in result.get("value_flows", []):
                flow = ValueFlow(
                    name=str(flow_data.get("name", "")),
                    from_role=str(flow_data.get("from", "")),
                    to_role=str(flow_data.get("to", "")),
                    asset=str(flow_data.get("asset", "")),
                    conditions=list(flow_data.get("conditions", [])),
                    confidence=confidence,
                    description=str(flow_data.get("description", "")),
                )
                if flow.name:
                    value_flows.append(flow)

            return {
                "incentives": list(result.get("incentives", [])),
                "value_flows": value_flows,
                "tokenomics_summary": str(result.get("tokenomics_summary", "")),
                "governance": dict(result.get("governance", {})),
            }

        except Exception as e:
            return {
                "incentives": [],
                "value_flows": [],
                "tokenomics_summary": "",
                "governance": {},
            }

    async def extract_governance(
        self,
        content: str,
    ) -> Dict[str, Any]:
        """Extract governance details from document content.

        This is included in extract_economics, but can be called separately
        for focused governance extraction.

        Args:
            content: Document content

        Returns:
            Dict with governance details

        Usage:
            governance = await parser.extract_governance(content)
            print(f"Timelock: {governance.get('timelock_duration')}")
        """
        economics = await self.extract_economics(content, 1)
        return economics.get("governance", {})

    async def extract_security(
        self,
        content: str,
    ) -> Dict[str, Any]:
        """Extract security claims from document content.

        Identifies security-related claims made in documentation.

        Args:
            content: Document content

        Returns:
            Dict with security_claims list

        Usage:
            security = await parser.extract_security(content)
            for claim in security['security_claims']:
                print(f"Claim: {claim}")
        """
        prompt = f"""Analyze this protocol documentation and extract security claims.

DOCUMENT:
{content}

Extract all security-related claims made by the documentation.
Return valid JSON."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=SECURITY_EXTRACTION_SYSTEM,
            )

            return {
                "security_claims": list(result.get("security_claims", [])),
            }

        except Exception as e:
            return {"security_claims": []}

    async def identify_gaps(
        self,
        content: str,
    ) -> List[str]:
        """Generate security-critical questions about documentation gaps.

        Per 03-CONTEXT.md: "Generate questions about security-critical gaps"

        Args:
            content: Document content

        Returns:
            List of security-critical questions

        Usage:
            questions = await parser.identify_gaps(content)
            for q in questions:
                print(f"Question: {q}")
        """
        prompt = f"""Analyze this protocol documentation and identify security gaps.

DOCUMENT:
{content}

What security-critical questions does this documentation NOT answer?
Focus on questions that would be important for security analysis.
Return valid JSON with a 'questions' array."""

        try:
            result = await self.llm_client.analyze_json(
                prompt=prompt,
                system=SECURITY_EXTRACTION_SYSTEM,
            )

            return list(result.get("questions", []))

        except Exception as e:
            return []

    async def cross_validate(
        self,
        doc_result: DocParseResult,
        code_context: Dict[str, Any],
    ) -> CrossValidationResult:
        """Cross-validate doc claims against code analysis.

        Per 03-CONTEXT.md: "Cross-validate doc claims against code: verify
        documented behaviors exist. Flag conflicts between docs and code."

        Args:
            doc_result: Parsed documentation result
            code_context: Code analysis results (from CodeAnalyzer)

        Returns:
            CrossValidationResult with matches, conflicts, undetermined

        Usage:
            validation = await parser.cross_validate(doc_result, code_context)
            if validation.conflicts:
                print("Warning: doc-code conflicts found!")
        """
        validation = CrossValidationResult()

        # Check roles against code-detected roles
        code_roles = {r.get("name", "").lower() for r in code_context.get("roles", [])}
        for doc_role in doc_result.roles:
            if doc_role.name.lower() in code_roles:
                validation.matches.append(f"Role '{doc_role.name}' found in code")
            else:
                validation.undetermined.append(
                    f"Role '{doc_role.name}' from docs not found in code"
                )

        # Check assumptions against code operations
        code_operations = set(code_context.get("semantic_operations", []))
        for assumption in doc_result.assumptions:
            # Check if related operations exist
            related = False
            if assumption.category == "price" and any("oracle" in op.lower() for op in code_operations):
                related = True
            if assumption.category == "trust" and any("external" in op.lower() for op in code_operations):
                related = True

            if related:
                validation.matches.append(f"Assumption '{assumption.description[:50]}...' has related code")

        # Check for obvious conflicts
        code_claims = code_context.get("security_properties", {})
        for claim in doc_result.security_claims:
            claim_lower = claim.lower()

            # Check reentrancy claims
            if "reentrancy" in claim_lower and "protected" in claim_lower:
                if not code_claims.get("all_have_reentrancy_guard", True):
                    validation.conflicts.append({
                        "claim": claim,
                        "code": "Not all functions have reentrancy guards",
                    })

            # Check access control claims
            if "access control" in claim_lower or "only admin" in claim_lower:
                if not code_claims.get("critical_functions_gated", True):
                    validation.conflicts.append({
                        "claim": claim,
                        "code": "Not all critical functions have access controls",
                    })

        return validation


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "DocParser",
    "DocParseResult",
    "CrossValidationResult",
    "ROLE_EXTRACTION_SYSTEM",
    "ASSUMPTION_EXTRACTION_SYSTEM",
    "INVARIANT_EXTRACTION_SYSTEM",
    "ECONOMICS_EXTRACTION_SYSTEM",
    "SECURITY_EXTRACTION_SYSTEM",
]
