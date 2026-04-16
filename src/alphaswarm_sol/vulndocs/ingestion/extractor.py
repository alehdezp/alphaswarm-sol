"""Content extraction for URL ingestion.

Extracts vulnerability patterns, documentation, and semantic operations
from fetched URL content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class QualityLevel(Enum):
    """Quality assessment level."""

    DRAFT = "draft"
    READY = "ready"
    EXCELLENT = "excellent"


@dataclass
class ExtractedPattern:
    """Extracted vulnerability pattern."""

    id: str
    name: str | None = None
    description: str | None = None
    tier: str = "A"  # A, B, or C
    severity: str | None = None
    conditions: list[str] = field(default_factory=list)
    sequence: list[str] = field(default_factory=list)


@dataclass
class ExtractedContent:
    """Extracted content from URL.

    Contains all extracted vulnerability information including
    patterns, documentation, semantic operations, and quality assessment.
    """

    # Core identification
    vulnerability_type: str | None = None
    suggested_name: str | None = None
    description: str | None = None
    severity: str | None = None

    # Patterns
    patterns: list[ExtractedPattern] = field(default_factory=list)

    # Semantic operations identified
    semantic_ops: list[str] = field(default_factory=list)

    # Graph signals
    graph_signals: dict[str, str] = field(default_factory=dict)

    # Documentation sections
    documentation: dict[str, str] = field(default_factory=dict)

    # Quality assessment
    quality: QualityLevel = QualityLevel.DRAFT
    quality_reasons: list[str] = field(default_factory=list)

    # Source metadata
    source_url: str | None = None


class ContentExtractor:
    """Extract patterns and documentation from vulnerability content.

    Analyzes fetched content to extract:
    - Vulnerability patterns with conditions
    - Documentation (overview, detection, mitigation)
    - Semantic operations
    - Graph signals and behavioral signatures
    - Quality assessment

    Example:
        extractor = ContentExtractor()
        extracted = extractor.extract(content, url)
        print(f"Type: {extracted.vulnerability_type}")
        print(f"Quality: {extracted.quality}")
    """

    # Known BSKG semantic operations to detect
    SEMANTIC_OPERATIONS = [
        "TRANSFERS_VALUE_OUT",
        "READS_USER_BALANCE",
        "WRITES_USER_BALANCE",
        "CHECKS_PERMISSION",
        "MODIFIES_OWNER",
        "MODIFIES_ROLES",
        "CALLS_EXTERNAL",
        "CALLS_UNTRUSTED",
        "READS_EXTERNAL_VALUE",
        "MODIFIES_CRITICAL_STATE",
        "READS_ORACLE",
        "INITIALIZES_STATE",
        "USES_BLOCK_TIMESTAMP",
        "USES_BLOCK_NUMBER",
        "EMITS_EVENT",
        "REVERTS_ON_FAILURE",
        "USES_DELEGATECALL",
        "CREATES_CONTRACT",
        "SELFDESTRUCTS",
        "USES_ASSEMBLY",
    ]

    # Vulnerability type keywords for classification
    VULN_TYPE_KEYWORDS = {
        "reentrancy": ["reentrancy", "reentrant", "re-enter", "callback attack"],
        "oracle": ["oracle", "price feed", "stale price", "price manipulation"],
        "access-control": ["access control", "authorization", "privilege escalation"],
        "arithmetic": ["overflow", "underflow", "integer overflow"],
        "flash-loan": ["flash loan", "flash mint"],
        "dos": ["denial of service", "gas griefing", "unbounded"],
        "governance": ["governance attack", "voting manipulation"],
        "token": ["token approval", "ERC20", "ERC721"],
        "upgrade": ["proxy vulnerability", "upgrade attack"],
        "vault": ["vault inflation", "share manipulation"],
        "cross-chain": ["bridge attack", "cross-chain"],
        "mev": ["frontrunning", "sandwich attack", "MEV"],
        "crypto": ["signature malleability", "ECDSA"],
    }

    # Severity indicators
    SEVERITY_KEYWORDS = {
        "critical": ["critical", "severe", "total loss", "drain all", "complete compromise"],
        "high": ["high", "significant", "major loss", "steal funds"],
        "medium": ["medium", "moderate", "limited impact"],
        "low": ["low", "minor", "informational", "gas optimization"],
    }

    def extract(self, content: str, source_url: str | None = None) -> ExtractedContent:
        """Extract vulnerability information from content.

        Args:
            content: Raw content from URL.
            source_url: Source URL for metadata.

        Returns:
            ExtractedContent with all extracted information.
        """
        result = ExtractedContent(source_url=source_url)

        # Extract vulnerability type
        result.vulnerability_type = self._extract_vuln_type(content)

        # Extract suggested name
        result.suggested_name = self._extract_name(content)

        # Extract description
        result.description = self._extract_description(content)

        # Extract severity
        result.severity = self._extract_severity(content)

        # Extract semantic operations
        result.semantic_ops = self._extract_operations(content)

        # Extract graph signals
        result.graph_signals = self._extract_graph_signals(content)

        # Extract patterns
        result.patterns = self._extract_patterns(content, result)

        # Extract documentation sections
        result.documentation = self._extract_documentation(content)

        # Assess quality
        quality, reasons = self._assess_quality(content, result)
        result.quality = quality
        result.quality_reasons = reasons

        return result

    def _extract_vuln_type(self, content: str) -> str | None:
        """Extract vulnerability type from content.

        Args:
            content: Raw content.

        Returns:
            Vulnerability type or None.
        """
        content_lower = content.lower()

        # Score each type by keyword matches
        scores: dict[str, int] = {}
        for vuln_type, keywords in self.VULN_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in content_lower)
            if score > 0:
                scores[vuln_type] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def _extract_name(self, content: str) -> str | None:
        """Extract suggested vulnerability name.

        Args:
            content: Raw content.

        Returns:
            Suggested name or None.
        """
        # Look for title patterns
        title_patterns = [
            r"#\s+(.+?)(?:\n|$)",  # Markdown H1
            r"<title>(.+?)</title>",  # HTML title
            r"(?:vulnerability|attack|exploit):\s*(.+?)(?:\n|$)",  # Labeled
        ]

        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up and return if reasonable length
                if 5 <= len(title) <= 100:
                    return title

        return None

    def _extract_description(self, content: str) -> str | None:
        """Extract vulnerability description.

        Args:
            content: Raw content.

        Returns:
            Description or None.
        """
        # Look for description sections
        desc_patterns = [
            r"(?:description|overview|summary)[\s:]*\n(.+?)(?:\n\n|\n#|\Z)",
            r"(?:##\s*(?:description|overview|summary))\s*\n(.+?)(?:\n##|\Z)",
        ]

        for pattern in desc_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1).strip()
                # Return first 500 chars if too long
                return desc[:500] if len(desc) > 500 else desc

        # Fallback: first paragraph-like content
        paragraphs = re.split(r"\n\s*\n", content)
        for para in paragraphs:
            para = para.strip()
            if 50 <= len(para) <= 500:
                return para

        return None

    def _extract_severity(self, content: str) -> str | None:
        """Extract severity level.

        Args:
            content: Raw content.

        Returns:
            Severity level or None.
        """
        content_lower = content.lower()

        # Check explicit severity labels first
        explicit_patterns = [
            r"severity[\s:]+(\w+)",
            r"risk[\s:]+(\w+)",
            r"\[(\w+)\]\s*severity",
        ]

        for pattern in explicit_patterns:
            match = re.search(pattern, content_lower)
            if match:
                severity = match.group(1).lower()
                if severity in self.SEVERITY_KEYWORDS:
                    return severity

        # Score by keywords
        scores: dict[str, int] = {}
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in content_lower)
            if score > 0:
                scores[severity] = score

        if scores:
            return max(scores, key=scores.get)

        return "medium"  # Default

    def _extract_operations(self, content: str) -> list[str]:
        """Extract semantic operations from content.

        Args:
            content: Raw content.

        Returns:
            List of detected semantic operations.
        """
        operations = []
        content_upper = content.upper()

        for op in self.SEMANTIC_OPERATIONS:
            if op in content_upper:
                operations.append(op)

        # Also detect operations from behavioral descriptions
        behavior_mappings = {
            "transfer": "TRANSFERS_VALUE_OUT",
            "external call": "CALLS_EXTERNAL",
            "state update": "MODIFIES_CRITICAL_STATE",
            "balance write": "WRITES_USER_BALANCE",
            "balance read": "READS_USER_BALANCE",
            "permission check": "CHECKS_PERMISSION",
            "owner modification": "MODIFIES_OWNER",
            "oracle read": "READS_ORACLE",
            "delegatecall": "USES_DELEGATECALL",
            "selfdestruct": "SELFDESTRUCTS",
        }

        content_lower = content.lower()
        for behavior, op in behavior_mappings.items():
            if behavior in content_lower and op not in operations:
                operations.append(op)

        return operations

    def _extract_graph_signals(self, content: str) -> dict[str, str]:
        """Extract graph signals and behavioral signatures.

        Args:
            content: Raw content.

        Returns:
            Dictionary of graph signals.
        """
        signals: dict[str, str] = {}

        # Look for CEI pattern mentions
        if "checks-effects-interactions" in content.lower() or "CEI" in content:
            signals["safe_pattern"] = "checks-effects-interactions"

        # Look for behavioral signatures
        signature_patterns = [
            (r"read.+?call.+?write", "R:bal->X:out->W:bal"),
            (r"read.+?write.+?call", "R:bal->W:bal->X:out"),
            (r"external.+?state", "external_call->state_write"),
            (r"state.+?external", "state_read->external_call"),
        ]

        content_lower = content.lower()
        for pattern, signature in signature_patterns:
            if re.search(pattern, content_lower):
                signals["behavioral_signature"] = signature
                break

        # Look for vulnerable pattern description
        vuln_patterns = [
            (r"vulnerable.+?pattern[:\s]+(.+?)(?:\n|$)", "vulnerable_pattern"),
            (r"attack.+?vector[:\s]+(.+?)(?:\n|$)", "attack_vector"),
        ]

        for pattern, key in vuln_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                signals[key] = match.group(1).strip()[:100]

        return signals

    def _extract_patterns(
        self, content: str, extracted: ExtractedContent
    ) -> list[ExtractedPattern]:
        """Extract vulnerability patterns from content.

        Args:
            content: Raw content.
            extracted: Partially extracted content for context.

        Returns:
            List of extracted patterns.
        """
        patterns: list[ExtractedPattern] = []

        # If we have vulnerability type and operations, create a pattern
        if extracted.vulnerability_type and extracted.semantic_ops:
            pattern_id = self._generate_pattern_id(
                extracted.vulnerability_type,
                extracted.suggested_name,
            )

            pattern = ExtractedPattern(
                id=pattern_id,
                name=extracted.suggested_name,
                description=extracted.description,
                tier="A" if len(extracted.semantic_ops) >= 2 else "B",
                severity=extracted.severity,
                conditions=extracted.semantic_ops[:5],  # Top 5 operations
                sequence=self._extract_sequence(content),
            )
            patterns.append(pattern)

        # Look for explicit pattern definitions in content
        pattern_block_regex = r"(?:pattern|rule)[:\s]+\{([^}]+)\}"
        for match in re.finditer(pattern_block_regex, content, re.IGNORECASE):
            block = match.group(1)
            # Try to parse pattern block (simplified)
            pattern_data = self._parse_pattern_block(block)
            if pattern_data:
                patterns.append(pattern_data)

        return patterns

    def _generate_pattern_id(
        self, vuln_type: str, name: str | None
    ) -> str:
        """Generate a pattern ID.

        Args:
            vuln_type: Vulnerability type.
            name: Optional name.

        Returns:
            Pattern ID in kebab-case.
        """
        base = name or vuln_type
        # Convert to kebab-case
        result = re.sub(r"[^\w\s-]", "", base.lower())
        result = re.sub(r"[\s_]+", "-", result)
        result = re.sub(r"-+", "-", result).strip("-")
        return result[:50]  # Limit length

    def _extract_sequence(self, content: str) -> list[str]:
        """Extract operation sequence from content.

        Args:
            content: Raw content.

        Returns:
            List of operations in sequence.
        """
        sequence: list[str] = []

        # Look for numbered steps or sequence indicators
        step_patterns = [
            r"1\.\s*(.+?)(?:\n|2\.)",
            r"first[,:]?\s*(.+?)(?:then|second|next)",
            r"step\s*1[:\s]+(.+?)(?:step\s*2|\n\n)",
        ]

        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                for match in matches[:5]:
                    step = match.strip()[:50]
                    if step:
                        sequence.append(step)
                break

        return sequence

    def _parse_pattern_block(self, block: str) -> ExtractedPattern | None:
        """Parse a pattern definition block.

        Args:
            block: Pattern block content.

        Returns:
            ExtractedPattern or None if parsing fails.
        """
        # Simplified parsing - look for key-value pairs
        data: dict[str, str] = {}

        kv_pattern = r"(\w+)\s*[=:]\s*[\"']?([^\"'\n,]+)[\"']?"
        for match in re.finditer(kv_pattern, block):
            key = match.group(1).lower()
            value = match.group(2).strip()
            data[key] = value

        if not data.get("id") and not data.get("name"):
            return None

        return ExtractedPattern(
            id=data.get("id", data.get("name", "unknown")).lower().replace(" ", "-"),
            name=data.get("name"),
            description=data.get("description"),
            tier=data.get("tier", "B"),
            severity=data.get("severity"),
        )

    def _extract_documentation(self, content: str) -> dict[str, str]:
        """Extract documentation sections.

        Args:
            content: Raw content.

        Returns:
            Dictionary of documentation sections.
        """
        docs: dict[str, str] = {}

        # Section patterns to look for
        section_patterns = {
            "overview": [r"##?\s*(?:overview|introduction|about)\s*\n(.+?)(?=\n##|\Z)"],
            "detection": [r"##?\s*(?:detection|identifying|how to find)\s*\n(.+?)(?=\n##|\Z)"],
            "mitigation": [r"##?\s*(?:mitigation|fix|remediation|prevention)\s*\n(.+?)(?=\n##|\Z)"],
            "exploits": [r"##?\s*(?:exploit|attack|example|PoC)\s*\n(.+?)(?=\n##|\Z)"],
            "verification": [r"##?\s*(?:verification|testing|validate)\s*\n(.+?)(?=\n##|\Z)"],
        }

        for section, patterns in section_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    section_content = match.group(1).strip()
                    if len(section_content) >= 50:  # Minimum content threshold
                        docs[section] = section_content[:2000]  # Limit length
                    break

        return docs

    def _assess_quality(
        self, content: str, extracted: ExtractedContent
    ) -> tuple[QualityLevel, list[str]]:
        """Assess quality of extracted content.

        Args:
            content: Raw content.
            extracted: Extracted content.

        Returns:
            Tuple of (quality level, list of reasons).
        """
        score = 0
        reasons: list[str] = []

        # Check for description
        if extracted.description and len(extracted.description) >= 100:
            score += 1
            reasons.append("Has detailed description")
        else:
            reasons.append("Missing: detailed description")

        # Check for code examples
        if "```" in content or "function " in content or "contract " in content:
            score += 1
            reasons.append("Has code examples")
        else:
            reasons.append("Missing: code examples")

        # Check for semantic operations
        if len(extracted.semantic_ops) >= 2:
            score += 1
            reasons.append("Has semantic operations")
        else:
            reasons.append("Missing: semantic operations")

        # Check for patterns
        if extracted.patterns:
            score += 1
            reasons.append("Has extractable patterns")
        else:
            reasons.append("Missing: extractable patterns")

        # Check for real-world references
        real_world_indicators = ["CVE-", "exploit", "hack", "attack", "$", "million", "rekt"]
        if any(ind.lower() in content.lower() for ind in real_world_indicators):
            score += 1
            reasons.append("Has real-world references")
        else:
            reasons.append("Missing: real-world exploit reference")

        # Check for documentation sections
        if len(extracted.documentation) >= 2:
            score += 1
            reasons.append("Has multiple documentation sections")
        else:
            reasons.append("Missing: comprehensive documentation")

        # Determine quality level
        if score >= 5:
            return QualityLevel.EXCELLENT, reasons
        elif score >= 3:
            return QualityLevel.READY, reasons
        else:
            return QualityLevel.DRAFT, reasons
