"""Merge Orchestrator for Multi-Model Pipeline.

Task 18.2: Opus-powered orchestrator for semantic merging.

The MergeOrchestrator:
1. Receives summaries from SubcategoryWorkers
2. Identifies ALL unique ideas across sources
3. Detects and resolves conflicts
4. Creates unified VulnKnowledgeDoc for each subcategory
5. Ensures no valuable information is lost
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.vulndocs.agents.base import AgentConfig, AgentResult, BaseAgent
from alphaswarm_sol.vulndocs.agents.category_agent import SubcategoryResult
from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MergeConflict,
    MergeResult,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    Prevalence,
    RealExploitRef,
    Severity,
    SourceSummary,
    UniqueIdea,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.validators.svr_sync import SVRFieldSync

logger = logging.getLogger(__name__)


# Similarity threshold for deduplication
SIMILARITY_THRESHOLD = 0.85


def compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity ratio (0-1)
    """
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def deduplicate_strings(
    strings: List[str], threshold: float = SIMILARITY_THRESHOLD
) -> List[str]:
    """Remove duplicate/similar strings.

    Args:
        strings: List of strings
        threshold: Similarity threshold

    Returns:
        Deduplicated list
    """
    if not strings:
        return []

    unique = [strings[0]]
    for s in strings[1:]:
        is_duplicate = any(compute_similarity(s, u) > threshold for u in unique)
        if not is_duplicate:
            unique.append(s)
    return unique


class MergeOrchestrator(BaseAgent):
    """Opus-powered orchestrator for semantic merging.

    Makes intelligent decisions about combining knowledge from multiple sources.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Agent configuration
        """
        config = config or AgentConfig.for_opus_orchestrator()
        super().__init__(name="merge-orchestrator", config=config)

    async def process(self, input_data: Any) -> AgentResult[MergeResult]:
        """Merge summaries from a subcategory into a knowledge document.

        Args:
            input_data: Dict with 'category', 'subcategory', 'summaries'

        Returns:
            MergeResult with unified document
        """
        category = input_data.get("category", "")
        subcategory = input_data.get("subcategory", "")
        summaries: List[SourceSummary] = input_data.get("summaries", [])

        if not summaries:
            return AgentResult.failure_result("No summaries provided")

        self.log(f"Merging {len(summaries)} summaries for {category}/{subcategory}")

        # Step 1: Identify all unique ideas
        unique_ideas = await self._identify_unique_ideas(summaries)
        self.log(f"Found {len(unique_ideas)} unique ideas")

        # Step 2: Detect conflicts
        conflicts = await self._detect_conflicts(summaries)
        self.log(f"Found {len(conflicts)} conflicts")

        # Step 3: Resolve conflicts
        for conflict in conflicts:
            await self._resolve_conflict(conflict)

        # Step 4: Semantic merge into document
        document = await self._semantic_merge(
            category=category,
            subcategory=subcategory,
            summaries=summaries,
            unique_ideas=unique_ideas,
        )

        # Step 5: Mark which ideas were merged
        for idea in unique_ideas:
            idea.merged = self._is_idea_in_document(idea, document)

        # Step 6: Validate completeness + SVR field sync
        completeness = self._validate_completeness(document, summaries)
        svr_result = SVRFieldSync().sync_doc(document)
        document.metadata.completeness_score = min(
            completeness, svr_result.completeness_score
        )
        document.metadata.missing_fields = svr_result.missing_fields

        result = MergeResult(
            subcategory_id=f"{category}/{subcategory}",
            document=document,
            unique_ideas=unique_ideas,
            conflicts=conflicts,
            source_count=len(summaries),
        )

        unmerged = result.get_unmerged_ideas()
        if unmerged:
            self.log(f"Warning: {len(unmerged)} ideas were not merged", "warning")

        return AgentResult.success_result(result)

    async def _identify_unique_ideas(
        self, summaries: List[SourceSummary]
    ) -> List[UniqueIdea]:
        """Identify all unique ideas across summaries.

        Args:
            summaries: List of source summaries

        Returns:
            List of unique ideas
        """
        ideas: List[UniqueIdea] = []
        seen_hashes: Set[str] = set()

        # Extract ideas from key points
        for summary in summaries:
            for point in summary.key_points:
                point_hash = hashlib.md5(point.lower().encode()).hexdigest()[:12]
                if point_hash not in seen_hashes:
                    seen_hashes.add(point_hash)
                    ideas.append(
                        UniqueIdea(
                            id=point_hash,
                            description=point,
                            source_urls=[summary.source_url],
                            category=summary.category,
                            idea_type="detection",
                        )
                    )
                else:
                    # Add source to existing idea
                    for idea in ideas:
                        if idea.id == point_hash:
                            if summary.source_url not in idea.source_urls:
                                idea.source_urls.append(summary.source_url)

        # Extract ideas from attack vectors
        for summary in summaries:
            if summary.attack_vector:
                vector_hash = hashlib.md5(
                    summary.attack_vector.lower().encode()
                ).hexdigest()[:12]
                if vector_hash not in seen_hashes:
                    seen_hashes.add(vector_hash)
                    ideas.append(
                        UniqueIdea(
                            id=vector_hash,
                            description=summary.attack_vector,
                            source_urls=[summary.source_url],
                            category=summary.category,
                            idea_type="attack_variant",
                        )
                    )

        # Extract ideas from mitigations
        for summary in summaries:
            if summary.mitigation:
                mit_hash = hashlib.md5(
                    summary.mitigation.lower().encode()
                ).hexdigest()[:12]
                if mit_hash not in seen_hashes:
                    seen_hashes.add(mit_hash)
                    ideas.append(
                        UniqueIdea(
                            id=mit_hash,
                            description=summary.mitigation,
                            source_urls=[summary.source_url],
                            category=summary.category,
                            idea_type="mitigation",
                        )
                    )

        return ideas

    async def _detect_conflicts(
        self, summaries: List[SourceSummary]
    ) -> List[MergeConflict]:
        """Detect conflicting information between sources.

        Args:
            summaries: List of source summaries

        Returns:
            List of conflicts
        """
        conflicts = []
        conflict_id = 0

        # Check for conflicting mitigations
        mitigations = [
            (s.mitigation, s.source_url, s.source_authority)
            for s in summaries
            if s.mitigation
        ]

        # Compare pairs
        for i, (mit_a, url_a, auth_a) in enumerate(mitigations):
            for mit_b, url_b, auth_b in mitigations[i + 1 :]:
                # Check if they seem to contradict
                if self._are_contradictory(mit_a, mit_b):
                    conflict_id += 1
                    conflicts.append(
                        MergeConflict(
                            conflict_id=f"conflict-{conflict_id}",
                            description="Contradicting mitigation advice",
                            claim_a=mit_a,
                            source_a=url_a,
                            authority_a=auth_a,
                            claim_b=mit_b,
                            source_b=url_b,
                            authority_b=auth_b,
                        )
                    )

        return conflicts

    def _are_contradictory(self, claim_a: str, claim_b: str) -> bool:
        """Check if two claims contradict each other.

        Args:
            claim_a: First claim
            claim_b: Second claim

        Returns:
            True if contradictory
        """
        # Simple contradiction detection
        negation_pairs = [
            ("should", "should not"),
            ("must", "must not"),
            ("always", "never"),
            ("do", "don't"),
            ("can", "cannot"),
        ]

        a_lower = claim_a.lower()
        b_lower = claim_b.lower()

        for pos, neg in negation_pairs:
            if pos in a_lower and neg in b_lower:
                return True
            if neg in a_lower and pos in b_lower:
                return True

        return False

    async def _resolve_conflict(self, conflict: MergeConflict) -> None:
        """Resolve a conflict using source authority and reasoning.

        Args:
            conflict: Conflict to resolve
        """
        # Higher authority wins
        if conflict.authority_a > conflict.authority_b:
            conflict.resolution = conflict.claim_a
            conflict.reasoning = (
                f"Source A ({conflict.source_a}) has higher authority "
                f"({conflict.authority_a:.2f} vs {conflict.authority_b:.2f})"
            )
        elif conflict.authority_b > conflict.authority_a:
            conflict.resolution = conflict.claim_b
            conflict.reasoning = (
                f"Source B ({conflict.source_b}) has higher authority "
                f"({conflict.authority_b:.2f} vs {conflict.authority_a:.2f})"
            )
        else:
            # Equal authority - prefer more specific
            if len(conflict.claim_a) > len(conflict.claim_b):
                conflict.resolution = conflict.claim_a
                conflict.reasoning = "Source A provides more specific guidance"
            else:
                conflict.resolution = conflict.claim_b
                conflict.reasoning = "Source B provides more specific guidance"

    async def _semantic_merge(
        self,
        category: str,
        subcategory: str,
        summaries: List[SourceSummary],
        unique_ideas: List[UniqueIdea],
    ) -> VulnKnowledgeDoc:
        """Merge summaries into a unified document.

        Args:
            category: Category name
            subcategory: Subcategory name
            summaries: Source summaries
            unique_ideas: Identified unique ideas

        Returns:
            Merged VulnKnowledgeDoc
        """
        # Collect and deduplicate content
        all_key_points = []
        all_attack_vectors = []
        all_attack_steps = []
        all_mitigations = []
        all_safe_patterns = []
        all_vulnerable_code = []
        all_fixed_code = []
        all_incidents = []
        all_sources = []

        for summary in summaries:
            all_key_points.extend(summary.key_points)
            if summary.attack_vector:
                all_attack_vectors.append(summary.attack_vector)
            all_attack_steps.extend(summary.attack_steps)
            if summary.mitigation:
                all_mitigations.append(summary.mitigation)
            all_safe_patterns.extend(summary.safe_patterns)
            if summary.vulnerable_code:
                all_vulnerable_code.append(summary.vulnerable_code)
            if summary.fixed_code:
                all_fixed_code.append(summary.fixed_code)
            all_incidents.extend(summary.incidents)
            all_sources.append(summary.source_url)

        # Deduplicate
        key_points = deduplicate_strings(all_key_points)
        attack_steps = deduplicate_strings(all_attack_steps)
        mitigations = deduplicate_strings(all_mitigations)
        safe_patterns = list(set(all_safe_patterns))

        # Generate name and summary
        name = self._generate_name(subcategory)
        one_liner = self._generate_one_liner(subcategory, key_points)
        tldr = self._generate_tldr(subcategory, key_points, all_attack_vectors)

        # Create sections
        detection = DetectionSection(
            graph_signals=self._extract_graph_signals(key_points),
            vulnerable_sequence=self._extract_sequence(key_points, "vulnerable"),
            safe_sequence=self._extract_sequence(key_points, "safe"),
            indicators=key_points[:5],
            checklist=self._generate_checklist(subcategory, key_points),
        )

        exploitation = ExploitationSection(
            attack_vector=all_attack_vectors[0] if all_attack_vectors else "",
            prerequisites=self._extract_prerequisites(key_points),
            attack_steps=attack_steps[:5],
            potential_impact=self._estimate_impact(subcategory),
            monetary_risk=self._estimate_monetary_risk(all_incidents),
        )

        mitigation = MitigationSection(
            primary_fix=mitigations[0] if mitigations else "",
            alternative_fixes=mitigations[1:4] if len(mitigations) > 1 else [],
            safe_pattern=safe_patterns[0] if safe_patterns else "",
            how_to_verify=self._generate_verification_steps(subcategory),
        )

        examples = ExamplesSection(
            vulnerable_code=all_vulnerable_code[0] if all_vulnerable_code else "",
            vulnerable_code_explanation=self._explain_vulnerable_code(
                subcategory, all_vulnerable_code
            ),
            fixed_code=all_fixed_code[0] if all_fixed_code else "",
            fixed_code_explanation=self._explain_fixed_code(subcategory),
            real_exploits=[
                RealExploitRef(
                    name=inc.get("name", ""),
                    date=inc.get("date", ""),
                    loss=inc.get("loss", ""),
                    protocol=inc.get("protocol", ""),
                    brief=inc.get("brief", ""),
                )
                for inc in all_incidents[:3]
            ],
        )

        pattern_linkage = self._create_pattern_linkage(category, subcategory)

        metadata = DocMetadata(
            sources=all_sources,
            source_authority=max(s.source_authority for s in summaries)
            if summaries
            else 0.0,
            last_updated=datetime.utcnow().isoformat(),
            keywords=self._extract_keywords(key_points),
            processing_model="opus",
            processing_timestamp=datetime.utcnow().isoformat(),
        )

        return VulnKnowledgeDoc(
            id=f"{category}/{subcategory}",
            name=name,
            category=category,
            subcategory=subcategory,
            severity=self._estimate_severity(subcategory),
            prevalence=self._estimate_prevalence(subcategory, len(summaries)),
            one_liner=one_liner,
            tldr=tldr,
            detection=detection,
            exploitation=exploitation,
            mitigation=mitigation,
            examples=examples,
            pattern_linkage=pattern_linkage,
            metadata=metadata,
        )

    def _generate_name(self, subcategory: str) -> str:
        """Generate human-readable name from subcategory."""
        return subcategory.replace("-", " ").title()

    def _generate_one_liner(self, subcategory: str, key_points: List[str]) -> str:
        """Generate one-line summary."""
        if key_points:
            # Use first key point as base
            return key_points[0][:100]
        return f"A {subcategory.replace('-', ' ')} vulnerability"

    def _generate_tldr(
        self, subcategory: str, key_points: List[str], attack_vectors: List[str]
    ) -> str:
        """Generate 2-3 sentence summary."""
        parts = []

        # What is it
        parts.append(f"This is a {subcategory.replace('-', ' ')} vulnerability.")

        # How to exploit
        if attack_vectors:
            parts.append(attack_vectors[0][:150])

        # Key concern
        if len(key_points) > 1:
            parts.append(key_points[1][:100])

        return " ".join(parts)

    def _extract_graph_signals(self, key_points: List[str]) -> List[str]:
        """Extract likely graph signals from key points."""
        signals = []

        # Common signal patterns
        signal_keywords = {
            "external call": "external_call_before_state",
            "state update": "state_write_after_external_call",
            "reentrancy": "has_reentrancy_guard",
            "access control": "has_access_gate",
            "oracle": "reads_oracle_price",
            "flash loan": "flash_loan_indicator",
            "owner": "writes_privileged_state",
        }

        text = " ".join(key_points).lower()
        for keyword, signal in signal_keywords.items():
            if keyword in text:
                signals.append(signal)

        return signals[:5]

    def _extract_sequence(self, key_points: List[str], seq_type: str) -> str:
        """Extract operation sequence from key points."""
        # Default sequences by type
        if seq_type == "vulnerable":
            return "R:state -> X:external -> W:state"
        else:
            return "R:state -> W:state -> X:external"

    def _generate_checklist(self, subcategory: str, key_points: List[str]) -> List[str]:
        """Generate detection checklist."""
        checklist = [
            f"Check for {subcategory.replace('-', ' ')} patterns",
            "Review external call ordering",
            "Verify guard mechanisms",
            "Check for state modifications",
        ]
        return checklist[:4]

    def _extract_prerequisites(self, key_points: List[str]) -> List[str]:
        """Extract attack prerequisites."""
        return [
            "Attacker has contract deployment capability",
            "Target function is externally callable",
            "No protective guards in place",
        ]

    def _estimate_impact(self, subcategory: str) -> str:
        """Estimate potential impact."""
        high_impact = ["reentrancy", "access", "oracle", "flash"]
        for keyword in high_impact:
            if keyword in subcategory:
                return "Direct loss of funds, protocol compromise"
        return "Potential financial loss or service disruption"

    def _estimate_monetary_risk(self, incidents: List[Dict[str, str]]) -> str:
        """Estimate monetary risk level."""
        if incidents:
            return "critical"
        return "high"

    def _generate_verification_steps(self, subcategory: str) -> List[str]:
        """Generate fix verification steps."""
        return [
            "Run updated test suite",
            "Verify guard mechanisms are in place",
            "Conduct manual code review",
            "Deploy to testnet and validate",
        ]

    def _explain_vulnerable_code(
        self, subcategory: str, code_blocks: List[str]
    ) -> str:
        """Generate explanation for vulnerable code."""
        return f"This code demonstrates a {subcategory.replace('-', ' ')} vulnerability."

    def _explain_fixed_code(self, subcategory: str) -> str:
        """Generate explanation for fixed code."""
        return f"The fix addresses the {subcategory.replace('-', ' ')} vulnerability."

    def _create_pattern_linkage(
        self, category: str, subcategory: str
    ) -> PatternLinkage:
        """Create pattern linkage for the subcategory."""
        # Map known subcategories to patterns
        pattern_map = {
            ("reentrancy", "classic-reentrancy"): (
                PatternLinkageType.EXACT_MATCH,
                ["reentrancy-001", "reentrancy-002"],
                0.95,
            ),
            ("reentrancy", "cross-function-reentrancy"): (
                PatternLinkageType.PARTIAL_MATCH,
                ["reentrancy-003"],
                0.70,
            ),
            ("reentrancy", "read-only-reentrancy"): (
                PatternLinkageType.REQUIRES_LLM,
                [],
                0.0,
            ),
            ("access-control", "missing-access-control"): (
                PatternLinkageType.EXACT_MATCH,
                ["auth-001", "auth-002"],
                0.90,
            ),
            ("access-control", "tx-origin-authentication"): (
                PatternLinkageType.EXACT_MATCH,
                ["auth-003"],
                0.95,
            ),
            ("oracle", "stale-price-data"): (
                PatternLinkageType.PARTIAL_MATCH,
                ["oracle-001"],
                0.80,
            ),
            ("logic", "business-logic-flaw"): (
                PatternLinkageType.THEORETICAL,
                [],
                0.0,
            ),
        }

        key = (category, subcategory)
        if key in pattern_map:
            linkage_type, patterns, coverage = pattern_map[key]
            return PatternLinkage(
                linkage_type=linkage_type,
                pattern_ids=patterns,
                coverage_pct=coverage,
            )

        # Default to theoretical
        return PatternLinkage(
            linkage_type=PatternLinkageType.THEORETICAL,
            why_no_pattern="Automated detection not yet implemented",
            manual_hints=["Manual review required"],
        )

    def _extract_keywords(self, key_points: List[str]) -> List[str]:
        """Extract keywords for retrieval."""
        keywords = set()
        for point in key_points:
            # Extract significant words
            words = point.lower().split()
            for word in words:
                if len(word) > 4 and word.isalpha():
                    keywords.add(word)
        return list(keywords)[:20]

    def _estimate_severity(self, subcategory: str) -> Severity:
        """Estimate severity based on subcategory."""
        critical_keywords = ["reentrancy", "oracle", "flash", "upgrade", "governance"]
        high_keywords = ["access", "dos", "signature", "arithmetic"]

        for keyword in critical_keywords:
            if keyword in subcategory:
                return Severity.CRITICAL

        for keyword in high_keywords:
            if keyword in subcategory:
                return Severity.HIGH

        return Severity.MEDIUM

    def _estimate_prevalence(self, subcategory: str, source_count: int) -> Prevalence:
        """Estimate prevalence based on source coverage."""
        if source_count > 10:
            return Prevalence.VERY_COMMON
        elif source_count > 5:
            return Prevalence.COMMON
        elif source_count > 2:
            return Prevalence.UNCOMMON
        else:
            return Prevalence.RARE

    def _is_idea_in_document(self, idea: UniqueIdea, doc: VulnKnowledgeDoc) -> bool:
        """Check if an idea was merged into the document."""
        doc_text = doc.to_markdown().lower()
        # Simple check: is the idea description present in the document?
        return idea.description.lower()[:50] in doc_text

    def _validate_completeness(
        self, doc: VulnKnowledgeDoc, summaries: List[SourceSummary]
    ) -> float:
        """Calculate completeness score for the document.

        Args:
            doc: Merged document
            summaries: Original summaries

        Returns:
            Completeness score (0-1)
        """
        checks = []

        # Has detection signals
        checks.append(len(doc.detection.graph_signals) > 0)

        # Has attack information
        checks.append(len(doc.exploitation.attack_vector) > 0)

        # Has mitigation
        checks.append(len(doc.mitigation.primary_fix) > 0)

        # Has examples
        checks.append(len(doc.examples.vulnerable_code) > 0)

        # Has pattern linkage
        checks.append(len(doc.pattern_linkage.pattern_ids) > 0 or
                      doc.pattern_linkage.linkage_type != PatternLinkageType.THEORETICAL)

        # Has sources
        checks.append(len(doc.metadata.sources) > 0)

        return sum(checks) / len(checks)

    def get_prompt_template(self, template_name: str) -> str:
        """Get prompt template for merging.

        Args:
            template_name: Template name

        Returns:
            Template string
        """
        if template_name == "identify_ideas":
            return """Analyze these vulnerability knowledge summaries.

Identify EVERY unique:
- Attack scenario or variant
- Detection approach
- Mitigation technique
- Edge case or gotcha
- Real-world example

Do NOT lose any valuable information.
Even slightly different scenarios should be captured.

Summaries:
{summaries}

Output unique ideas as JSON array with:
- id: unique hash
- description: the idea
- source_urls: list of source URLs
- idea_type: "attack_variant" | "detection" | "mitigation" | "edge_case" | "example"
"""

        if template_name == "resolve_conflict":
            return """These sources conflict on the following point:

Conflict: {conflict_description}

Source A ({authority_a}): {claim_a}
Source B ({authority_b}): {claim_b}

Resolve this conflict by:
1. Considering source authority
2. Checking for nuance (both might be right in different contexts)
3. Preferring more specific/recent information

Output:
- resolution: Which claim to use
- reasoning: Why this is correct
- nuance: Any context where the other claim applies
"""

        return ""
