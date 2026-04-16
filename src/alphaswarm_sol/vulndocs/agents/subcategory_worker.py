"""Subcategory Worker for Multi-Model Pipeline.

Task 18.2: Haiku-powered worker for processing a single subcategory.

The SubcategoryWorker:
1. Receives sources for a specific subcategory
2. Extracts key information from each source
3. Creates structured SourceSummary objects
4. Returns results to the CategoryAgent
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.vulndocs.agents.base import AgentConfig, AgentResult, BaseAgent
from alphaswarm_sol.vulndocs.agents.category_agent import CategorySource, SubcategoryResult
from alphaswarm_sol.vulndocs.knowledge_doc import SourceSummary
from alphaswarm_sol.vulndocs.validators.svr_sync import SVRFieldSync

logger = logging.getLogger(__name__)

MIN_SIGNAL_FIELDS = 1


@dataclass
class ReviewDecision:
    """Result of per-doc review gate."""

    status: str
    novelty: str
    value: str
    rationale: str


# Source authority weights by source type
SOURCE_AUTHORITY_WEIGHTS: Dict[str, float] = {
    # Tier 1: Authoritative (1.0)
    "openzeppelin": 1.0,
    "trail-of-bits": 1.0,
    "consensys": 1.0,
    "ethereum-foundation": 1.0,
    # Tier 2: Highly Trusted (0.95)
    "certik": 0.95,
    "code4rena": 0.95,
    "sherlock": 0.95,
    "spearbit": 0.95,
    "solodit": 0.95,
    # Tier 3: Trusted (0.85)
    "rekt-news": 0.85,
    "peckshield": 0.85,
    "halborn": 0.85,
    "slowmist": 0.85,
    "immunefi": 0.85,
    # Tier 4: Community (0.70)
    "medium-verified": 0.70,
    "github-popular": 0.70,
    "academic-arxiv": 0.70,
    # Tier 5: General (0.50)
    "medium-general": 0.50,
    "blog-unverified": 0.50,
    "forum-post": 0.50,
}


def get_source_authority(source_name: str) -> float:
    """Get authority weight for a source.

    Args:
        source_name: Source identifier

    Returns:
        Authority weight (0-1)
    """
    source_lower = source_name.lower()
    for key, weight in SOURCE_AUTHORITY_WEIGHTS.items():
        if key in source_lower:
            return weight
    return 0.5  # Default


class SubcategoryWorker(BaseAgent):
    """Haiku-powered worker for processing a single subcategory.

    Does the heavy lifting of summarization and extraction.
    """

    def __init__(
        self,
        category: str,
        subcategory: str,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize the worker.

        Args:
            category: Parent category
            subcategory: Subcategory to process
            config: Agent configuration
        """
        config = config or AgentConfig.for_haiku_worker()
        super().__init__(name=f"worker-{category}-{subcategory}", config=config)

        self.category = category
        self.subcategory = subcategory
        self._svr_sync = SVRFieldSync()

    async def process(self, input_data: Any) -> AgentResult[SubcategoryResult]:
        """Process all sources for this subcategory.

        Args:
            input_data: List of CategorySource objects

        Returns:
            SubcategoryResult with summaries and unique ideas
        """
        sources: List[CategorySource] = input_data

        if not sources:
            return AgentResult.success_result(
                SubcategoryResult(
                    subcategory=self.subcategory,
                    summaries=[],
                    unique_ideas=[],
                    source_count=0,
                )
            )

        self.log(f"Processing {len(sources)} sources for {self.subcategory}")

        summaries = []
        unique_ideas = set()
        seen_hashes: Set[str] = set()
        rejected = 0

        for source in sources:
            try:
                summary = await self._summarize_source(source)
                decision = self._review_summary(summary, seen_hashes)
                summary.review_status = decision.status
                summary.review_novelty = decision.novelty
                summary.review_value = decision.value
                summary.review_rationale = decision.rationale
                summary.missing_fields = self._svr_sync.sync_summary(summary).missing_fields

                if decision.status == "reject":
                    rejected += 1
                    continue

                seen_hashes.add(summary.content_hash)
                summaries.append(summary)

                # Extract unique ideas from key points
                for point in summary.key_points:
                    unique_ideas.add(point)

            except Exception as e:
                self.log(f"Error processing source {source.url}: {e}", "warning")

        result = SubcategoryResult(
            subcategory=self.subcategory,
            summaries=summaries,
            unique_ideas=list(unique_ideas),
            source_count=len(summaries),
        )

        self.log(
            f"Completed {self.subcategory}: {len(summaries)} summaries, "
            f"{len(unique_ideas)} unique ideas, {rejected} rejected"
        )

        return AgentResult.success_result(result)

    async def _summarize_source(self, source: CategorySource) -> SourceSummary:
        """Create structured summary from a source.

        This is where Haiku would be called in production.
        For now, we use rule-based extraction.

        Args:
            source: Source to summarize

        Returns:
            SourceSummary object
        """
        content = source.get_content()

        # Compute content hash for deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]

        # Extract key information using rule-based approach
        # In production, this would call Haiku with the prompt template
        key_points = self._extract_key_points(content)
        attack_vector, attack_steps = self._extract_attack_info(content)
        mitigation, safe_patterns = self._extract_mitigation_info(content)
        vulnerable_code, fixed_code = self._extract_code_examples(content)
        incidents = self._extract_incidents(content)

        return SourceSummary(
            source_url=source.url,
            source_name=source.source_name,
            category=self.category,
            subcategory=self.subcategory,
            content_hash=content_hash,
            key_points=key_points,
            attack_vector=attack_vector,
            attack_steps=attack_steps,
            mitigation=mitigation,
            safe_patterns=safe_patterns,
            vulnerable_code=vulnerable_code,
            fixed_code=fixed_code,
            incidents=incidents,
            source_authority=get_source_authority(source.source_name),
            extraction_confidence=0.8,
        )

    def _review_summary(
        self,
        summary: SourceSummary,
        seen_hashes: Set[str],
    ) -> ReviewDecision:
        """Apply per-doc review gate to a summary."""
        signal_count = sum(
            [
                bool(summary.key_points),
                bool(summary.attack_vector),
                bool(summary.mitigation),
                bool(summary.vulnerable_code),
            ]
        )

        if signal_count < MIN_SIGNAL_FIELDS:
            return ReviewDecision(
                status="reject",
                novelty="low",
                value="low",
                rationale="Insufficient actionable signal",
            )

        if summary.content_hash in seen_hashes:
            return ReviewDecision(
                status="merge",
                novelty="low",
                value="medium",
                rationale="Duplicate content hash in subcategory batch",
            )

        return ReviewDecision(
            status="accept",
            novelty="medium",
            value="medium",
            rationale="Actionable signals present",
        )

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content.

        Args:
            content: Source content

        Returns:
            List of key points
        """
        points = []

        # Look for bullet points or numbered lists
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            # Bullet points
            if line.startswith(("-", "*", "•")):
                point = line.lstrip("-*• ").strip()
                if len(point) > 10 and len(point) < 200:
                    points.append(point)
            # Numbered lists
            elif line and line[0].isdigit() and "." in line[:3]:
                point = line.split(".", 1)[-1].strip()
                if len(point) > 10 and len(point) < 200:
                    points.append(point)

        # Limit to top points
        return points[:10]

    def _extract_attack_info(self, content: str) -> tuple[str, List[str]]:
        """Extract attack vector and steps from content.

        Args:
            content: Source content

        Returns:
            Tuple of (attack_vector, attack_steps)
        """
        attack_vector = ""
        attack_steps = []

        content_lower = content.lower()

        # Look for attack-related sections
        attack_keywords = [
            "attack",
            "exploit",
            "vulnerability",
            "attacker",
            "malicious",
        ]

        # Find attack vector description
        for keyword in attack_keywords:
            if keyword in content_lower:
                # Find the sentence containing the keyword
                start = content_lower.find(keyword)
                # Find sentence boundaries
                sentence_start = content.rfind(".", 0, start) + 1
                sentence_end = content.find(".", start)
                if sentence_end == -1:
                    sentence_end = len(content)

                sentence = content[sentence_start:sentence_end].strip()
                if len(sentence) > 20:
                    attack_vector = sentence
                    break

        # Look for numbered attack steps
        step_patterns = [
            "step 1",
            "step 2",
            "first,",
            "second,",
            "then,",
            "finally,",
        ]
        for pattern in step_patterns:
            if pattern in content_lower:
                idx = content_lower.find(pattern)
                sentence_end = content.find(".", idx)
                if sentence_end == -1:
                    sentence_end = len(content)
                step = content[idx:sentence_end].strip()
                if len(step) > 10 and step not in attack_steps:
                    attack_steps.append(step)

        return attack_vector[:500], attack_steps[:5]

    def _extract_mitigation_info(self, content: str) -> tuple[str, List[str]]:
        """Extract mitigation information from content.

        Args:
            content: Source content

        Returns:
            Tuple of (mitigation, safe_patterns)
        """
        mitigation = ""
        safe_patterns = []

        content_lower = content.lower()

        # Look for mitigation-related content
        mitigation_keywords = [
            "fix",
            "remediation",
            "mitigation",
            "prevention",
            "solution",
            "recommend",
            "should",
        ]

        for keyword in mitigation_keywords:
            if keyword in content_lower:
                start = content_lower.find(keyword)
                sentence_start = content.rfind(".", 0, start) + 1
                sentence_end = content.find(".", start)
                if sentence_end == -1:
                    sentence_end = len(content)

                sentence = content[sentence_start:sentence_end].strip()
                if len(sentence) > 20 and not mitigation:
                    mitigation = sentence
                    break

        # Look for safe pattern names
        pattern_keywords = [
            "CEI pattern",
            "checks-effects-interactions",
            "reentrancy guard",
            "nonReentrant",
            "mutex",
            "OpenZeppelin",
            "SafeERC20",
        ]
        for pattern in pattern_keywords:
            if pattern.lower() in content_lower:
                safe_patterns.append(pattern)

        return mitigation[:500], safe_patterns[:5]

    def _extract_code_examples(self, content: str) -> tuple[str, str]:
        """Extract code examples from content.

        Args:
            content: Source content

        Returns:
            Tuple of (vulnerable_code, fixed_code)
        """
        vulnerable_code = ""
        fixed_code = ""

        # Look for code blocks
        code_blocks = []
        in_block = False
        current_block = []

        for line in content.split("\n"):
            if "```" in line:
                if in_block:
                    # End of block
                    code_blocks.append("\n".join(current_block))
                    current_block = []
                in_block = not in_block
            elif in_block:
                current_block.append(line)

        # Try to identify vulnerable vs fixed code
        for i, block in enumerate(code_blocks):
            block_lower = block.lower()
            # Check for vulnerability indicators
            if any(
                kw in block_lower
                for kw in ["vulnerable", "bad", "// bug", "// vuln", "external"]
            ):
                if not vulnerable_code:
                    vulnerable_code = block[:1000]
            # Check for fix indicators
            elif any(
                kw in block_lower
                for kw in ["fixed", "good", "// fix", "safe", "nonReentrant"]
            ):
                if not fixed_code:
                    fixed_code = block[:1000]

        # If we only found one block, assume it's vulnerable
        if code_blocks and not vulnerable_code and not fixed_code:
            vulnerable_code = code_blocks[0][:1000]

        return vulnerable_code, fixed_code

    def _extract_incidents(self, content: str) -> List[Dict[str, str]]:
        """Extract real-world incident references.

        Args:
            content: Source content

        Returns:
            List of incident dictionaries
        """
        incidents = []

        content_lower = content.lower()

        # Known major hacks
        known_hacks = {
            "dao hack": {"name": "The DAO Hack", "date": "2016-06-17", "loss": "$60M"},
            "cream finance": {
                "name": "Cream Finance",
                "date": "2021-10-27",
                "loss": "$130M",
            },
            "beanstalk": {"name": "Beanstalk", "date": "2022-04-17", "loss": "$182M"},
            "euler": {"name": "Euler Finance", "date": "2023-03-13", "loss": "$197M"},
            "ronin": {"name": "Ronin Bridge", "date": "2022-03-29", "loss": "$625M"},
            "wormhole": {"name": "Wormhole", "date": "2022-02-02", "loss": "$320M"},
            "nomad": {"name": "Nomad Bridge", "date": "2022-08-02", "loss": "$190M"},
        }

        for keyword, info in known_hacks.items():
            if keyword in content_lower:
                incidents.append(info)

        # Look for CVE references
        import re

        cve_pattern = r"CVE-\d{4}-\d+"
        cves = re.findall(cve_pattern, content, re.IGNORECASE)
        for cve in cves[:3]:  # Limit
            incidents.append({"name": cve, "type": "CVE"})

        return incidents[:5]

    def get_prompt_template(self, template_name: str) -> str:
        """Get prompt template for summarization.

        Args:
            template_name: Template name

        Returns:
            Template string
        """
        if template_name == "summarize":
            return """Extract vulnerability knowledge from this content.
Category: {category}
Subcategory: {subcategory}

Content:
{content}

Extract:
1. Key points (5-10 bullets)
2. Attack vector (how to exploit)
3. Attack steps (numbered list)
4. Mitigation (how to fix)
5. Safe patterns (known safe implementations)
6. Code examples (vulnerable + fixed)
7. Real incidents (CVEs, hacks, losses)

Format as JSON with these keys:
- key_points: list of strings
- attack_vector: string
- attack_steps: list of strings
- mitigation: string
- safe_patterns: list of strings
- vulnerable_code: string
- fixed_code: string
- incidents: list of {name, date, loss} objects"""

        return ""
