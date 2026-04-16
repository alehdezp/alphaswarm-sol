"""Context pack builder for orchestrating context pack generation.

The ContextPackBuilder orchestrates the generation of ProtocolContextPack
from multiple sources:
- Code analysis (via VKG KnowledgeGraph)
- Document parsing (via DocParser when available)
- Web research (via WebFetcher when available)

Per 03-CONTEXT.md decisions:
- LLM-generated, not human-authored
- Agents generate from: VKG analysis, protocol docs, web research
- Infer business impact: "what would be a disaster for the protocol"
- Review encouraged but not required; flagged as 'auto_generated' when not reviewed
- Doc-code conflicts flagged explicitly
- Confidence upgraded when code AND docs agree

Usage:
    from alphaswarm_sol.context import ContextPackBuilder, BuildConfig
    from alphaswarm_sol.kg.schema import KnowledgeGraph

    # Build from VKG graph
    graph = build_kg("contracts/")
    builder = ContextPackBuilder(
        graph=graph,
        project_path=Path("contracts/"),
        config=BuildConfig(
            protocol_name="MyProtocol",
            protocol_type="lending",
            include_code_analysis=True,
            include_doc_parsing=True,
        )
    )
    result = builder.build()

    # Access the pack
    pack = result.pack
    print(f"Roles: {[r.name for r in pack.roles]}")
    print(f"Warnings: {result.warnings}")
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from .types import (
    Assumption,
    Confidence,
    Invariant,
    OffchainInput,
    Role,
    ValueFlow,
    AcceptedRisk,
)
from .schema import ProtocolContextPack

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph
    from alphaswarm_sol.llm.client import LLMClient


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class BuildConfig:
    """Configuration for context pack building.

    Controls what sources to include and how to process them.

    Attributes:
        protocol_name: Name of the protocol being analyzed
        protocol_type: Type hint for protocol (lending, dex, nft, bridge, etc.)
        include_code_analysis: Whether to run VKG-based code analysis
        include_doc_parsing: Whether to parse documentation files
        additional_doc_sources: Extra doc URLs/paths to include
        infer_unstated_assumptions: Whether to infer assumptions from patterns
        cross_validate: Whether to validate docs against code
        generate_questions: Whether to generate investigation questions
        auto_discover_docs: Whether to auto-discover docs (README, docs/, etc.)
        web_search_enabled: Whether to search GitHub issues, forums, etc.

    Usage:
        config = BuildConfig(
            protocol_name="Aave V3",
            protocol_type="lending",
            include_code_analysis=True,
            include_doc_parsing=True,
            infer_unstated_assumptions=True,
        )
    """

    # Protocol identification
    protocol_name: str = ""
    protocol_type: str = ""  # lending, dex, nft, bridge, vault, etc.

    # Source toggles
    include_code_analysis: bool = True
    include_doc_parsing: bool = True

    # Additional sources
    additional_doc_sources: List[str] = field(default_factory=list)

    # Inference options
    infer_unstated_assumptions: bool = True
    cross_validate: bool = True
    generate_questions: bool = True

    # Discovery options
    auto_discover_docs: bool = True
    web_search_enabled: bool = False  # Requires API keys

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_name": self.protocol_name,
            "protocol_type": self.protocol_type,
            "include_code_analysis": self.include_code_analysis,
            "include_doc_parsing": self.include_doc_parsing,
            "additional_doc_sources": self.additional_doc_sources,
            "infer_unstated_assumptions": self.infer_unstated_assumptions,
            "cross_validate": self.cross_validate,
            "generate_questions": self.generate_questions,
            "auto_discover_docs": self.auto_discover_docs,
            "web_search_enabled": self.web_search_enabled,
        }


# =============================================================================
# Conflict Detection
# =============================================================================


@dataclass
class Conflict:
    """A conflict between documentation and code.

    Per 03-CONTEXT.md: "Flag conflicts between docs and code explicitly"
    and "Do NOT assume docs are outdated - docs/forums are often 'the law'"

    Attributes:
        description: What the conflict is about
        doc_claim: What the documentation says
        code_behavior: What the code actually does
        doc_source: Where the doc claim came from
        code_source: Which function/contract shows the behavior
        severity: How serious this conflict is (info, warning, critical)
        recommendation: Suggested resolution
    """

    description: str
    doc_claim: str
    code_behavior: str
    doc_source: str
    code_source: str
    severity: str = "warning"  # info, warning, critical
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "description": self.description,
            "doc_claim": self.doc_claim,
            "code_behavior": self.code_behavior,
            "doc_source": self.doc_source,
            "code_source": self.code_source,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


# =============================================================================
# Build Result
# =============================================================================


@dataclass
class BuildResult:
    """Result of context pack building.

    Contains the generated pack plus metadata about the build process.

    Attributes:
        pack: The generated ProtocolContextPack
        warnings: Warnings encountered during build
        conflicts: Doc-code conflicts detected
        questions: Investigation questions generated
        sources_used: Sources that contributed to the pack
        build_time: How long the build took (seconds)
        code_analysis_used: Whether code analysis was run
        doc_parsing_used: Whether doc parsing was run
    """

    pack: ProtocolContextPack
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    sources_used: List[Dict[str, Any]] = field(default_factory=list)
    build_time: float = 0.0
    code_analysis_used: bool = False
    doc_parsing_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pack": self.pack.to_dict(),
            "warnings": self.warnings,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "questions": self.questions,
            "sources_used": self.sources_used,
            "build_time": self.build_time,
            "code_analysis_used": self.code_analysis_used,
            "doc_parsing_used": self.doc_parsing_used,
        }

    @property
    def has_conflicts(self) -> bool:
        """Whether any conflicts were detected."""
        return len(self.conflicts) > 0

    @property
    def critical_conflicts(self) -> List[Conflict]:
        """Get only critical conflicts."""
        return [c for c in self.conflicts if c.severity == "critical"]


# =============================================================================
# Source Info
# =============================================================================


@dataclass
class SourceInfo:
    """Information about a source used in context pack generation.

    Per 03-CONTEXT.md: Sources with reliability tiers
    - Tier 1: Official docs
    - Tier 2: Audits
    - Tier 3: Community/forums

    Attributes:
        name: Source identifier
        source_type: Type (code, doc, audit, forum, etc.)
        path: File path or URL
        tier: Reliability tier (1=official, 2=audit, 3=community)
        content_hash: Hash of content for change detection
    """

    name: str
    source_type: str  # code, doc, readme, audit, forum, github
    path: str
    tier: int = 3
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "source_type": self.source_type,
            "path": self.path,
            "tier": self.tier,
            "content_hash": self.content_hash,
        }


# =============================================================================
# Changelog Entry
# =============================================================================


@dataclass
class ChangelogEntry:
    """Entry in the context pack changelog.

    Per 03-CONTEXT.md: Version tracking for protocol upgrades

    Attributes:
        version: Version number after this change
        timestamp: When the change was made
        changes: Description of what changed
        changed_by: Who/what made the change
        source_files_changed: Files that triggered this update
    """

    version: str
    timestamp: str
    changes: List[str]
    changed_by: str = "auto"  # auto or human
    source_files_changed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "changes": self.changes,
            "changed_by": self.changed_by,
            "source_files_changed": self.source_files_changed,
        }


# =============================================================================
# Context Pack Builder
# =============================================================================


class ContextPackBuilder:
    """Orchestrates context pack generation from multiple sources.

    Combines code analysis (from VKG) and document parsing to generate
    a unified ProtocolContextPack. Per 03-CONTEXT.md: LLM-generated with
    confidence tracking and conflict detection.

    Key behaviors:
    - Mark auto_generated=True, reviewed=False
    - Upgrade confidence when code AND docs agree
    - Doc trust assumptions take precedence
    - Flag doc-code conflicts explicitly

    Usage:
        from alphaswarm_sol.context import ContextPackBuilder, BuildConfig
        from alphaswarm_sol.kg.schema import KnowledgeGraph

        graph = build_kg("contracts/")
        builder = ContextPackBuilder(
            graph=graph,
            project_path=Path("contracts/"),
            config=BuildConfig(protocol_name="MyProtocol")
        )
        result = builder.build()
        pack = result.pack
    """

    def __init__(
        self,
        graph: "KnowledgeGraph",
        project_path: Path,
        config: Optional[BuildConfig] = None,
        llm_client: Optional["LLMClient"] = None,
    ) -> None:
        """Initialize the builder.

        Args:
            graph: VKG KnowledgeGraph to analyze
            project_path: Path to project root for doc discovery
            config: Build configuration options
            llm_client: Optional LLM client for inference tasks
        """
        self.graph = graph
        self.project_path = Path(project_path)
        self.config = config or BuildConfig()
        self.llm_client = llm_client

        # Build state
        self._code_roles: List[Role] = []
        self._code_assumptions: List[Assumption] = []
        self._code_invariants: List[Invariant] = []
        self._code_offchain: List[OffchainInput] = []
        self._code_flows: List[ValueFlow] = []
        self._code_critical_functions: List[str] = []

        self._doc_roles: List[Role] = []
        self._doc_assumptions: List[Assumption] = []
        self._doc_invariants: List[Invariant] = []
        self._doc_offchain: List[OffchainInput] = []
        self._doc_flows: List[ValueFlow] = []
        self._doc_accepted_risks: List[AcceptedRisk] = []
        self._doc_governance: Dict[str, Any] = {}
        self._doc_security_model: Dict[str, Any] = {}
        self._doc_tokenomics: str = ""
        self._doc_incentives: List[str] = []

        self._sources: List[SourceInfo] = []
        self._conflicts: List[Conflict] = []
        self._warnings: List[str] = []
        self._questions: List[str] = []

    async def build(self) -> BuildResult:
        """Build the context pack from all configured sources.

        Orchestrates:
        1. Code analysis (if enabled)
        2. Doc parsing (if enabled and available)
        3. Merge and conflict detection
        4. Protocol type inference
        5. Pack assembly

        Returns:
            BuildResult containing the pack and build metadata
        """
        import time

        start_time = time.time()
        code_used = False
        doc_used = False

        # Step 1: Code analysis
        if self.config.include_code_analysis:
            self._analyze_code()
            code_used = True
            self._sources.append(
                SourceInfo(
                    name="VKG Analysis",
                    source_type="code",
                    path=str(self.project_path),
                    tier=1,
                )
            )

        # Step 2: Doc parsing (if module available)
        if self.config.include_doc_parsing:
            try:
                doc_used = await self._parse_docs_async()
            except ImportError:
                self._warnings.append(
                    "Doc parsing requested but doc_parser module not available. "
                    "Run plan 03-03 to enable doc parsing."
                )
            except Exception as e:
                self._warnings.append(f"Doc parsing failed: {e}")

        # Step 3: Merge roles, assumptions, etc.
        merged_roles = self._merge_roles()
        merged_assumptions = self._merge_assumptions()
        merged_invariants = self._merge_invariants()
        merged_offchain = self._merge_offchain_inputs()
        merged_flows = self._merge_value_flows()

        # Step 4: Detect conflicts
        if self.config.cross_validate and code_used and doc_used:
            self._detect_conflicts()

        # Step 5: Infer protocol type if not specified
        protocol_type = self.config.protocol_type
        if not protocol_type:
            protocol_type = self._infer_protocol_type()

        # Step 6: Generate investigation questions
        if self.config.generate_questions:
            self._generate_questions(merged_assumptions, merged_roles)

        # Step 7: Assemble the pack
        pack = self._assemble_pack(
            roles=merged_roles,
            assumptions=merged_assumptions,
            invariants=merged_invariants,
            offchain_inputs=merged_offchain,
            value_flows=merged_flows,
            protocol_type=protocol_type,
        )

        build_time = time.time() - start_time

        return BuildResult(
            pack=pack,
            warnings=self._warnings,
            conflicts=self._conflicts,
            questions=self._questions,
            sources_used=[s.to_dict() for s in self._sources],
            build_time=build_time,
            code_analysis_used=code_used,
            doc_parsing_used=doc_used,
        )

    def _analyze_code(self) -> None:
        """Run VKG-based code analysis.

        Uses CodeAnalyzer to extract context from the KnowledgeGraph.
        """
        from .parser import CodeAnalyzer

        analyzer = CodeAnalyzer(self.graph)
        result = analyzer.analyze()

        self._code_roles = result.roles
        self._code_assumptions = result.inferred_assumptions
        self._code_invariants = result.inferred_invariants
        self._code_offchain = result.offchain_inputs
        self._code_flows = result.value_flows
        self._code_critical_functions = result.critical_functions

        # Add any warnings from analysis
        self._warnings.extend(result.warnings)

    async def _parse_docs_async(self) -> bool:
        """Parse documentation files using WebFetcher and DocParser.

        Uses WebFetcher to discover and fetch documents, then DocParser
        for LLM-driven extraction of roles, assumptions, invariants.

        Returns:
            True if doc parsing was performed, False otherwise
        """
        # Try to import doc parsing modules
        try:
            from .parser.doc_parser import DocParser, DocParseResult
            from .parser.web_fetcher import WebFetcher, FetchedDocument
        except ImportError:
            # Doc parser not yet available (plan 03-03 not complete)
            return False

        # Use WebFetcher for document discovery and fetching
        fetcher = WebFetcher(self.project_path)

        # Fetch all discovered + additional sources
        documents = await fetcher.fetch_all(
            additional_sources=self.config.additional_doc_sources,
            include_discovered=self.config.auto_discover_docs,
        )

        if not documents:
            self._warnings.append("No documentation files found for parsing")
            return False

        # Filter to valid documents only
        valid_docs = [d for d in documents if d.is_valid]
        if not valid_docs:
            self._warnings.append(
                f"Found {len(documents)} documents but none were valid: "
                + ", ".join(d.fetch_error or "unknown" for d in documents if not d.is_valid)
            )
            return False

        # Parse each fetched document
        parser = DocParser(llm_client=self.llm_client)

        for doc in valid_docs:
            try:
                # Parse document - returns DocParseResult
                result = await parser.parse(doc)

                # Collect parsed content from DocParseResult
                self._doc_roles.extend(result.roles)
                self._doc_assumptions.extend(result.assumptions)
                self._doc_invariants.extend(result.invariants)
                self._doc_flows.extend(result.value_flows)

                # Governance and security from result
                if result.governance:
                    self._doc_governance.update(result.governance)
                if result.tokenomics_summary:
                    self._doc_tokenomics = result.tokenomics_summary
                if result.incentives:
                    self._doc_incentives.extend(result.incentives)

                # Security claims become part of security model
                if result.security_claims:
                    self._doc_security_model["claims"] = result.security_claims

                # Track source with tier from document
                self._sources.append(
                    SourceInfo(
                        name=Path(doc.source_url).name if "/" in doc.source_url else doc.source_url,
                        source_type=doc.source_type.value,
                        path=doc.source_url,
                        tier=doc.tier_value,
                        content_hash=doc.content_hash,
                    )
                )

                # Add any warnings from the parse result
                self._warnings.extend(result.warnings)

                # Add generated questions
                self._questions.extend(result.questions)

            except Exception as e:
                self._warnings.append(f"Failed to parse {doc.source_url}: {e}")

        return True

    def _discover_docs(self) -> List[Path]:
        """Auto-discover documentation files in the project.

        Per 03-CONTEXT.md: Auto-discover docs (README, docs/, whitepaper links)

        Returns:
            List of discovered documentation file paths
        """
        if not self.config.auto_discover_docs:
            return []

        docs: List[Path] = []

        # Check for README files
        for readme in ["README.md", "README.rst", "README.txt", "Readme.md"]:
            readme_path = self.project_path / readme
            if readme_path.exists():
                docs.append(readme_path)

        # Check for docs directory
        docs_dir = self.project_path / "docs"
        if docs_dir.exists() and docs_dir.is_dir():
            for doc_file in docs_dir.glob("**/*.md"):
                docs.append(doc_file)
            for doc_file in docs_dir.glob("**/*.rst"):
                docs.append(doc_file)

        # Check for doc directory (singular)
        doc_dir = self.project_path / "doc"
        if doc_dir.exists() and doc_dir.is_dir():
            for doc_file in doc_dir.glob("**/*.md"):
                docs.append(doc_file)

        # Check for whitepaper
        for wp in ["whitepaper.md", "WHITEPAPER.md", "whitepaper.pdf"]:
            wp_path = self.project_path / wp
            if wp_path.exists():
                docs.append(wp_path)

        # Check for protocol.md or similar
        for protocol_doc in ["protocol.md", "PROTOCOL.md", "SPECIFICATION.md", "spec.md"]:
            doc_path = self.project_path / protocol_doc
            if doc_path.exists():
                docs.append(doc_path)

        return docs

    def _merge_roles(self) -> List[Role]:
        """Merge roles from code and doc analysis.

        Per 03-CONTEXT.md: Upgrade confidence when code AND docs agree

        Returns:
            Merged list of Role objects
        """
        merged: Dict[str, Role] = {}

        # Add code-derived roles
        for role in self._code_roles:
            merged[role.name.lower()] = role

        # Merge doc-derived roles
        for role in self._doc_roles:
            key = role.name.lower()
            if key in merged:
                existing = merged[key]
                # Both sources agree - upgrade confidence
                new_confidence = Confidence.CERTAIN if role.confidence >= Confidence.INFERRED else role.confidence

                # Combine capabilities and trust assumptions
                combined_caps = list(set(existing.capabilities + role.capabilities))
                combined_trust = list(set(existing.trust_assumptions + role.trust_assumptions))

                merged[key] = Role(
                    name=existing.name,  # Prefer existing name casing
                    capabilities=combined_caps,
                    trust_assumptions=combined_trust,
                    confidence=new_confidence,
                    description=role.description or existing.description,
                    addresses=list(set(existing.addresses + role.addresses)),
                )
            else:
                # Doc-only role, use doc's confidence
                merged[key] = role

        return list(merged.values())

    def _merge_assumptions(self) -> List[Assumption]:
        """Merge assumptions from code and doc analysis.

        Per 03-CONTEXT.md: Doc trust assumptions take precedence

        Returns:
            Merged list of Assumption objects
        """
        merged: Dict[str, Assumption] = {}

        # Add code-derived assumptions
        for assumption in self._code_assumptions:
            key = assumption.description.lower()
            merged[key] = assumption

        # Merge doc-derived assumptions (take precedence)
        for assumption in self._doc_assumptions:
            key = assumption.description.lower()
            if key in merged:
                existing = merged[key]
                # Upgrade confidence if both agree
                new_confidence = Confidence.CERTAIN if assumption.confidence >= Confidence.INFERRED else assumption.confidence

                # Combine affected functions
                combined_funcs = list(set(existing.affects_functions + assumption.affects_functions))
                combined_tags = list(set(existing.tags + assumption.tags))

                merged[key] = Assumption(
                    description=assumption.description,  # Prefer doc description
                    category=assumption.category or existing.category,
                    affects_functions=combined_funcs,
                    confidence=new_confidence,
                    source=assumption.source,  # Prefer doc source
                    tags=combined_tags,
                )
            else:
                merged[key] = assumption

        return list(merged.values())

    def _merge_invariants(self) -> List[Invariant]:
        """Merge invariants from code and doc analysis.

        Returns:
            Merged list of Invariant objects
        """
        merged: Dict[str, Invariant] = {}

        # Add code-derived invariants
        for inv in self._code_invariants:
            key = inv.natural_language.lower()
            merged[key] = inv

        # Merge doc-derived invariants
        for inv in self._doc_invariants:
            key = inv.natural_language.lower()
            if key in merged:
                existing = merged[key]
                # Upgrade confidence if both agree
                new_confidence = Confidence.CERTAIN if inv.confidence >= Confidence.INFERRED else inv.confidence

                merged[key] = Invariant(
                    formal=inv.formal or existing.formal,
                    natural_language=inv.natural_language,
                    confidence=new_confidence,
                    source=inv.source or existing.source,
                    category=inv.category or existing.category,
                    critical=inv.critical or existing.critical,
                )
            else:
                merged[key] = inv

        return list(merged.values())

    def _merge_offchain_inputs(self) -> List[OffchainInput]:
        """Merge off-chain inputs from code and doc analysis.

        Returns:
            Merged list of OffchainInput objects
        """
        merged: Dict[str, OffchainInput] = {}

        # Add code-derived inputs
        for inp in self._code_offchain:
            key = inp.name.lower()
            merged[key] = inp

        # Merge doc-derived inputs
        for inp in self._doc_offchain:
            key = inp.name.lower()
            if key in merged:
                existing = merged[key]
                # Combine trust assumptions and affected functions
                combined_trust = list(set(existing.trust_assumptions + inp.trust_assumptions))
                combined_funcs = list(set(existing.affects_functions + inp.affects_functions))
                combined_endpoints = list(set(existing.endpoints + inp.endpoints))

                new_confidence = Confidence.CERTAIN if inp.confidence >= Confidence.INFERRED else inp.confidence

                merged[key] = OffchainInput(
                    name=inp.name,
                    input_type=inp.input_type or existing.input_type,
                    description=inp.description or existing.description,
                    trust_assumptions=combined_trust,
                    affects_functions=combined_funcs,
                    confidence=new_confidence,
                    endpoints=combined_endpoints,
                )
            else:
                merged[key] = inp

        return list(merged.values())

    def _merge_value_flows(self) -> List[ValueFlow]:
        """Merge value flows from code and doc analysis.

        Returns:
            Merged list of ValueFlow objects
        """
        merged: Dict[str, ValueFlow] = {}

        # Add code-derived flows
        for flow in self._code_flows:
            key = flow.name.lower()
            merged[key] = flow

        # Merge doc-derived flows
        for flow in self._doc_flows:
            key = flow.name.lower()
            if key in merged:
                existing = merged[key]
                combined_conditions = list(set(existing.conditions + flow.conditions))

                new_confidence = Confidence.CERTAIN if flow.confidence >= Confidence.INFERRED else flow.confidence

                merged[key] = ValueFlow(
                    name=flow.name,
                    from_role=flow.from_role or existing.from_role,
                    to_role=flow.to_role or existing.to_role,
                    asset=flow.asset or existing.asset,
                    conditions=combined_conditions,
                    confidence=new_confidence,
                    description=flow.description or existing.description,
                )
            else:
                merged[key] = flow

        return list(merged.values())

    def _detect_conflicts(self) -> None:
        """Detect conflicts between documentation and code.

        Per 03-CONTEXT.md: "Flag conflicts between docs and code explicitly"
        and "Treat doc-code conflicts as potential finding source"
        """
        # Compare role capabilities
        code_role_map = {r.name.lower(): r for r in self._code_roles}
        doc_role_map = {r.name.lower(): r for r in self._doc_roles}

        for role_name, doc_role in doc_role_map.items():
            if role_name in code_role_map:
                code_role = code_role_map[role_name]
                # Check for capability mismatches
                doc_caps = set(c.lower() for c in doc_role.capabilities)
                code_caps = set(c.lower() for c in code_role.capabilities)

                doc_only = doc_caps - code_caps
                code_only = code_caps - doc_caps

                if doc_only:
                    self._conflicts.append(
                        Conflict(
                            description=f"Role '{role_name}' has documented capabilities not found in code",
                            doc_claim=f"Capabilities: {', '.join(doc_only)}",
                            code_behavior="These capabilities are not observed in code",
                            doc_source=doc_role.source if hasattr(doc_role, "source") else "documentation",
                            code_source="VKG analysis",
                            severity="warning",
                            recommendation="Verify if capabilities are missing or docs are outdated",
                        )
                    )

                if code_only:
                    self._conflicts.append(
                        Conflict(
                            description=f"Role '{role_name}' has code capabilities not documented",
                            doc_claim="Not documented",
                            code_behavior=f"Capabilities found: {', '.join(code_only)}",
                            doc_source="documentation",
                            code_source="VKG analysis",
                            severity="info",
                            recommendation="Update documentation to reflect implemented capabilities",
                        )
                    )

        # Check for roles in code but not docs (potential hidden roles)
        for role_name in code_role_map:
            if role_name not in doc_role_map:
                self._conflicts.append(
                    Conflict(
                        description=f"Role '{role_name}' found in code but not documented",
                        doc_claim="Not documented",
                        code_behavior=f"Role with capabilities: {', '.join(code_role_map[role_name].capabilities)}",
                        doc_source="documentation",
                        code_source="VKG analysis",
                        severity="warning",
                        recommendation="Document this role or verify if it's intentionally undocumented",
                    )
                )

    def _infer_protocol_type(self) -> str:
        """Infer protocol type from code analysis.

        Detects: lending, dex, nft, bridge, vault, staking, governance

        Returns:
            Inferred protocol type string
        """
        # Collect indicators from function names and operations
        indicators: Dict[str, int] = {
            "lending": 0,
            "dex": 0,
            "nft": 0,
            "bridge": 0,
            "vault": 0,
            "staking": 0,
            "governance": 0,
        }

        # Check function names and operations
        for node in self.graph.nodes.values():
            if node.type != "function":
                continue

            func_name = node.properties.get("name", node.label).lower()
            ops = node.properties.get("semantic_operations", [])
            if isinstance(ops, str):
                ops = [ops]

            # Lending indicators
            if any(kw in func_name for kw in ["borrow", "lend", "repay", "liquidate", "collateral", "health"]):
                indicators["lending"] += 2
            if "READS_ORACLE" in ops:
                indicators["lending"] += 1

            # DEX indicators
            if any(kw in func_name for kw in ["swap", "addliquidity", "removeliquidity", "getamountout", "pair"]):
                indicators["dex"] += 2

            # NFT indicators
            if any(kw in func_name for kw in ["mint", "tokenuri", "tokenofownerbyindex", "safetransferfrom"]):
                indicators["nft"] += 1
            # Check for ERC721/1155 patterns
            if "safeTransferFrom" in node.properties.get("name", ""):
                indicators["nft"] += 1

            # Bridge indicators
            if any(kw in func_name for kw in ["bridge", "relay", "finalize", "crosschain", "layerzero"]):
                indicators["bridge"] += 2

            # Vault indicators
            if any(kw in func_name for kw in ["deposit", "withdraw", "shares", "assets", "totalassets"]):
                indicators["vault"] += 1

            # Staking indicators
            if any(kw in func_name for kw in ["stake", "unstake", "claim", "reward", "delegate"]):
                indicators["staking"] += 2

            # Governance indicators
            if any(kw in func_name for kw in ["propose", "vote", "execute", "queue", "veto"]):
                indicators["governance"] += 2

        # Find highest scoring type
        if not any(indicators.values()):
            return "unknown"

        max_type = max(indicators, key=lambda k: indicators[k])
        if indicators[max_type] < 2:
            return "unknown"

        return max_type

    def _generate_questions(
        self, assumptions: List[Assumption], roles: List[Role]
    ) -> None:
        """Generate investigation questions about gaps.

        Per 03-CONTEXT.md: Generate questions about security-critical gaps

        Args:
            assumptions: Current assumptions
            roles: Current roles
        """
        # Questions about roles with unclear trust
        for role in roles:
            if not role.trust_assumptions:
                self._questions.append(
                    f"What are the trust assumptions for the '{role.name}' role? "
                    f"It has capabilities: {', '.join(role.capabilities)}"
                )

        # Questions about inferred assumptions
        inferred = [a for a in assumptions if a.confidence == Confidence.INFERRED]
        if inferred:
            high_risk_categories = {"trust", "price", "access"}
            for assumption in inferred:
                if assumption.category in high_risk_categories:
                    self._questions.append(
                        f"Please verify assumption: '{assumption.description}' "
                        f"(inferred from {assumption.source})"
                    )

        # Questions about missing invariants
        if not any(inv for inv in self._code_invariants if inv.critical):
            self._questions.append(
                "No critical invariants were detected. What are the core protocol invariants "
                "that should never be violated?"
            )

        # Questions about upgrade patterns
        upgraders = [r for r in roles if "upgrade" in r.name.lower() or any("upgrade" in c.lower() for c in r.capabilities)]
        if upgraders:
            self._questions.append(
                "Upgrade capability detected. What is the upgrade process? "
                "Is there a timelock? Who controls upgrades?"
            )

    def _assemble_pack(
        self,
        roles: List[Role],
        assumptions: List[Assumption],
        invariants: List[Invariant],
        offchain_inputs: List[OffchainInput],
        value_flows: List[ValueFlow],
        protocol_type: str,
    ) -> ProtocolContextPack:
        """Assemble the final ProtocolContextPack.

        Per 03-CONTEXT.md: Mark auto_generated=True, reviewed=False

        Args:
            roles: Merged roles
            assumptions: Merged assumptions
            invariants: Merged invariants
            offchain_inputs: Merged off-chain inputs
            value_flows: Merged value flows
            protocol_type: Inferred or specified protocol type

        Returns:
            Complete ProtocolContextPack
        """
        return ProtocolContextPack(
            version="1.0",
            schema_version="1.0",
            protocol_name=self.config.protocol_name,
            protocol_type=protocol_type,
            generated_at=datetime.utcnow().isoformat() + "Z",
            auto_generated=True,
            reviewed=False,
            roles=roles,
            value_flows=value_flows,
            incentives=self._doc_incentives,
            tokenomics_summary=self._doc_tokenomics,
            assumptions=assumptions,
            invariants=invariants,
            offchain_inputs=offchain_inputs,
            security_model=self._doc_security_model,
            critical_functions=self._code_critical_functions,
            accepted_risks=self._doc_accepted_risks,
            governance=self._doc_governance,
            sources=[s.to_dict() for s in self._sources],
            deployment={},
            notes="",
        )

    # =========================================================================
    # Incremental Update Support
    # =========================================================================

    async def update(
        self, existing_pack: ProtocolContextPack, changed_files: Optional[List[str]] = None
    ) -> BuildResult:
        """Incrementally update an existing context pack.

        Per 03-CONTEXT.md: "Incremental update workflow when code changes"

        Args:
            existing_pack: The existing pack to update
            changed_files: List of changed file paths (optional)

        Returns:
            BuildResult with updated pack
        """
        import time

        start_time = time.time()

        # Detect what sources have changed
        changes = self._detect_source_changes(existing_pack, changed_files)

        if not changes["has_changes"]:
            # No changes detected, return existing pack
            self._warnings.append("No source changes detected, returning existing pack")
            return BuildResult(
                pack=existing_pack,
                warnings=self._warnings,
                build_time=time.time() - start_time,
            )

        # Re-analyze only changed sources
        if changes["code_changed"] and self.config.include_code_analysis:
            self._analyze_code()

        if changes["docs_changed"] and self.config.include_doc_parsing:
            try:
                await self._parse_docs_async()
            except ImportError:
                pass

        # Build new pack
        new_result = await self.build()

        # Merge with existing, preserving human edits
        merged_pack = self._merge_updates(existing_pack, new_result.pack)

        # Add changelog entry
        changelog = self._add_changelog_entry(
            existing_pack, merged_pack, changes, changed_files or []
        )

        # Store changelog in pack notes
        merged_pack.notes = f"{merged_pack.notes}\n\n{changelog}" if merged_pack.notes else changelog

        return BuildResult(
            pack=merged_pack,
            warnings=new_result.warnings,
            conflicts=new_result.conflicts,
            questions=new_result.questions,
            sources_used=new_result.sources_used,
            build_time=time.time() - start_time,
            code_analysis_used=new_result.code_analysis_used,
            doc_parsing_used=new_result.doc_parsing_used,
        )

    def _detect_source_changes(
        self, existing_pack: ProtocolContextPack, changed_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Detect what sources have changed since last build.

        Args:
            existing_pack: Existing pack to compare against
            changed_files: Explicitly specified changed files

        Returns:
            Dict with change detection results
        """
        result = {
            "has_changes": False,
            "code_changed": False,
            "docs_changed": False,
            "changed_files": changed_files or [],
        }

        # If changed files specified, use them directly
        if changed_files:
            result["has_changes"] = True
            for f in changed_files:
                if f.endswith(".sol"):
                    result["code_changed"] = True
                elif f.endswith((".md", ".rst", ".txt")):
                    result["docs_changed"] = True
            return result

        # Compare content hashes from existing sources
        existing_hashes: Dict[str, str] = {}
        for source in existing_pack.sources:
            if "content_hash" in source:
                existing_hashes[source.get("path", "")] = source["content_hash"]

        # Re-hash current sources
        for doc_path in self._discover_docs():
            try:
                content = doc_path.read_text()
                current_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
                path_str = str(doc_path)

                if path_str in existing_hashes:
                    if existing_hashes[path_str] != current_hash:
                        result["has_changes"] = True
                        result["docs_changed"] = True
                else:
                    # New file
                    result["has_changes"] = True
                    result["docs_changed"] = True

            except Exception:
                pass

        # For code changes, we'd need to compare graph fingerprints
        # For now, assume code changed if explicitly rebuilding
        result["code_changed"] = True
        result["has_changes"] = True

        return result

    def _merge_updates(
        self, existing: ProtocolContextPack, new: ProtocolContextPack
    ) -> ProtocolContextPack:
        """Merge new findings while preserving human edits.

        Per 03-CONTEXT.md: Preserve human edits during incremental updates

        Args:
            existing: Existing pack with potential human edits
            new: Newly generated pack

        Returns:
            Merged pack
        """
        # Start with new pack data
        merged = new

        # Preserve human-reviewed items from existing
        if existing.reviewed:
            # Keep the reviewed flag if human reviewed
            merged.reviewed = True

        # Preserve existing assumptions with CERTAIN confidence (likely human-verified)
        for assumption in existing.assumptions:
            if assumption.confidence == Confidence.CERTAIN:
                # Check if not already in merged
                if not any(
                    a.description.lower() == assumption.description.lower()
                    for a in merged.assumptions
                ):
                    merged.assumptions.append(assumption)

        # Preserve existing invariants marked as critical (likely human-verified)
        for inv in existing.invariants:
            if inv.critical and inv.confidence == Confidence.CERTAIN:
                if not any(
                    i.natural_language.lower() == inv.natural_language.lower()
                    for i in merged.invariants
                ):
                    merged.invariants.append(inv)

        # Preserve accepted risks (always human-defined)
        for risk in existing.accepted_risks:
            if not any(
                r.description.lower() == risk.description.lower()
                for r in merged.accepted_risks
            ):
                merged.accepted_risks.append(risk)

        # Preserve governance if existing has more detail
        if existing.governance and not new.governance:
            merged.governance = existing.governance

        # Preserve security model if existing has more detail
        if existing.security_model and not new.security_model:
            merged.security_model = existing.security_model

        return merged

    def _add_changelog_entry(
        self,
        existing: ProtocolContextPack,
        updated: ProtocolContextPack,
        changes: Dict[str, Any],
        changed_files: List[str],
    ) -> str:
        """Create a changelog entry for the update.

        Args:
            existing: Previous pack version
            updated: Updated pack version
            changes: Change detection results
            changed_files: List of changed files

        Returns:
            Changelog entry as formatted string
        """
        entry = ChangelogEntry(
            version=self._increment_version(existing.version),
            timestamp=datetime.utcnow().isoformat() + "Z",
            changes=[],
            changed_by="auto",
            source_files_changed=changed_files,
        )

        # Track what changed
        old_role_names = {r.name for r in existing.roles}
        new_role_names = {r.name for r in updated.roles}

        added_roles = new_role_names - old_role_names
        if added_roles:
            entry.changes.append(f"Added roles: {', '.join(added_roles)}")

        old_assumption_count = len(existing.assumptions)
        new_assumption_count = len(updated.assumptions)
        if new_assumption_count > old_assumption_count:
            entry.changes.append(
                f"Added {new_assumption_count - old_assumption_count} new assumptions"
            )

        if changes.get("code_changed"):
            entry.changes.append("Code analysis updated")

        if changes.get("docs_changed"):
            entry.changes.append("Documentation parsing updated")

        if not entry.changes:
            entry.changes.append("Minor updates")

        # Format as markdown
        changelog_md = f"""
## Changelog Entry

**Version:** {entry.version}
**Updated:** {entry.timestamp}
**Changed by:** {entry.changed_by}

### Changes
{chr(10).join('- ' + c for c in entry.changes)}

### Source Files
{chr(10).join('- ' + f for f in entry.source_files_changed) if entry.source_files_changed else 'N/A'}
"""
        return changelog_md.strip()

    def _increment_version(self, version: str) -> str:
        """Increment version string.

        Args:
            version: Current version string (e.g., "1.0")

        Returns:
            Incremented version string
        """
        try:
            parts = version.split(".")
            if len(parts) >= 2:
                minor = int(parts[1]) + 1
                return f"{parts[0]}.{minor}"
            return f"{version}.1"
        except (ValueError, IndexError):
            return "1.1"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ContextPackBuilder",
    "BuildConfig",
    "BuildResult",
    "Conflict",
    "SourceInfo",
    "ChangelogEntry",
]
