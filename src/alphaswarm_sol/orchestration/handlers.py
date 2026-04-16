"""Phase handlers for execution loop.

Handlers implement the actual work for each RouteAction.
They are injected into ExecutionLoop to keep it thin.

Each handler:
- Takes a Pool and optional target_beads
- Returns PhaseResult with success/failure and artifacts
- Delegates to actual VKG modules (builder, pattern engine, agents)

Phase 5.9 Skills Integration:
    Graph interface hardening skills should be invoked at appropriate points:
    - /vrs-graph-contract-validate - After BUILD_GRAPH to validate contract compliance
    - /vrs-evidence-audit - Before COLLECT_VERDICTS to validate evidence IDs
    - /vrs-ordering-proof - During SPAWN_VERIFIERS for path-qualified ordering
    - /vrs-taint-extend - During DETECT_PATTERNS for taint analysis
    - /vrs-taxonomy-migrate - During BUILD_GRAPH for ops registry validation
    - /vrs-slice-unify - During investigation for unified slicing

    See: src/alphaswarm_sol/shipping/README.md for skill catalog.

Phase 5.11-03 Integrity Gates:
    Handlers integrate workflow integrity gates:
    - evidence_gate: No confidence upgrade without evidence_refs
    - provenance_gate: Only DECLARED expectations trigger misconfig findings
    - validate_causal_chain: Complete causal chain required for upgrade
    - Economic rationality gate: EV > 0 required for prioritization

    See: src/alphaswarm_sol/llm/confidence.py for gate implementations.

Phase 07.1.1-02 Idempotency:
    Handlers derive deterministic idempotency keys from pool/bead/action.
    - make_idempotency_key() generates SHA256-based keys
    - Tool/agent actions use IdempotencyStore for caching
    - Retry/backoff bounded by IdempotentRetryConfig

    See: src/alphaswarm_sol/orchestration/idempotency.py for implementation.

Usage:
    from alphaswarm_sol.orchestration.handlers import (
        create_default_handlers, HandlerConfig,
        BuildGraphHandler, DetectPatternsHandler,
    )

    manager = PoolManager(Path(".vrs/pools"))
    config = HandlerConfig(project_root=Path("."))

    handlers = create_default_handlers(manager, config)

    # Use with ExecutionLoop
    loop = ExecutionLoop(manager)
    for action, handler in handlers.items():
        loop.register_handler(action, handler)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import hashlib
import logging

from .schemas import (
    DeltaEntry,
    DeltaType,
    EvidencePacket,
    MergeBatch,
    MergeConflict,
    MergeResult,
    Pool,
    PoolStatus,
    Verdict,
    VerdictConfidence,
)
from .loop import LoopPhase, PhaseResult
from .router import RouteAction
from .pool import PoolManager
from .debate import DebateOrchestrator
from .confidence import ConfidenceEnforcer
from .dedup import merge_batch_deltas
from .idempotency import IdempotencyStore

# Phase 5.11-03: Import integrity gates
from alphaswarm_sol.llm.confidence import (
    evidence_gate,
    provenance_gate,
    validate_causal_chain,
    ExpectationProvenance,
    ExpectationEvidence,
)

logger = logging.getLogger(__name__)


def make_idempotency_key(
    pool_id: str,
    bead_id: str,
    action: str,
    payload_hash: Optional[str] = None,
) -> str:
    """Generate deterministic idempotency key for handler actions.

    Phase 07.1.1-02: Handlers use this to derive keys for tool/agent calls.

    Args:
        pool_id: Pool identifier
        bead_id: Bead identifier (or "*" for pool-level actions)
        action: Action type (e.g., "attacker", "defender", "tool:slither")
        payload_hash: Optional hash of the action payload

    Returns:
        16-character hex string key (SHA256 prefix)
    """
    combined = f"{pool_id}:{bead_id}:{action}:{payload_hash or ''}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def hash_payload(payload: Any) -> str:
    """Hash a payload for idempotency key generation.

    Args:
        payload: Any JSON-serializable payload

    Returns:
        16-character hex hash
    """
    import json
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


@dataclass
class HandlerConfig:
    """Configuration for phase handlers.

    Attributes:
        project_root: Root directory of the project being analyzed
        pattern_dir: Optional path to pattern YAML files
        use_llm: Whether to enable LLM-based analysis
        verbose: Enable verbose logging

    Usage:
        config = HandlerConfig(
            project_root=Path("."),
            use_llm=True,
            verbose=True,
        )
    """

    project_root: Path = Path(".")
    pattern_dir: Optional[Path] = None
    use_llm: bool = False
    verbose: bool = False


class BaseHandler:
    """Base class for phase handlers.

    Handlers are callables that execute phase work and return results.
    All handlers receive the pool manager and config for dependency access.

    Subclasses implement __call__ to do the actual work.
    """

    def __init__(self, manager: PoolManager, config: Optional[HandlerConfig] = None):
        """Initialize handler with manager and config.

        Args:
            manager: Pool manager for persistence
            config: Handler configuration
        """
        self.manager = manager
        self.config = config or HandlerConfig()

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Execute handler. Subclasses implement this.

        Args:
            pool: Pool to process
            target_beads: Optional list of specific beads to process

        Returns:
            PhaseResult with success status and artifacts
        """
        raise NotImplementedError("Subclasses must implement __call__")


class BuildGraphHandler(BaseHandler):
    """Handler for BUILD_GRAPH action.

    Builds the VKG knowledge graph from scope files.

    Phase 5.9 Skills:
        After graph construction, agents should invoke:
        - /vrs-graph-contract-validate - Validate Graph Interface Contract v2 compliance
        - /vrs-taxonomy-migrate - Validate ops registry and SARIF compatibility
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Build knowledge graph from scope.

        Args:
            pool: Pool with scope defining files to analyze
            target_beads: Ignored for graph building

        Returns:
            PhaseResult with graph metadata
        """
        try:
            # Import VKG builder
            from alphaswarm_sol.kg.builder import VKGBuilder
            from alphaswarm_sol.kg.store import GraphStore

            if not pool.scope:
                return PhaseResult(
                    success=False,
                    phase=LoopPhase.INTAKE,
                    message="No scope defined for pool",
                )

            if not pool.scope.files:
                return PhaseResult(
                    success=False,
                    phase=LoopPhase.INTAKE,
                    message="No files in scope",
                )

            # Build graph from scope files
            project_root = self.config.project_root
            builder = VKGBuilder(project_root)

            graph = None
            for file_path in pool.scope.files:
                target = project_root / file_path
                if target.exists():
                    graph = builder.build(target)
                    break

            if graph is None:
                return PhaseResult(
                    success=False,
                    phase=LoopPhase.INTAKE,
                    message="No valid files in scope",
                )

            # Save graph to project storage with identity-based isolation
            from datetime import datetime, timezone

            from alphaswarm_sol.kg.graph_hash import compute_source_hash
            from alphaswarm_sol.kg.identity import contract_identity

            output_dir = project_root / ".vrs" / "graphs"
            output_dir.mkdir(parents=True, exist_ok=True)

            sol_files = [project_root / f for f in pool.scope.files if str(f).endswith(".sol")]
            ident = contract_identity(sol_files) if sol_files else None

            store = GraphStore(output_dir)
            meta = None
            if ident is not None:
                source_hash = compute_source_hash([str(p) for p in sol_files]) if sol_files else ""
                meta = {
                    "schema_version": 1,
                    "built_at": datetime.now(timezone.utc).isoformat(),
                    "graph_hash": source_hash,
                    "contract_paths": [str(p) for p in sol_files],
                    "stem": sol_files[0].stem if sol_files else "unknown",
                    "source_contract": str(sol_files[0]) if sol_files else "unknown",
                    "slither_version": graph.metadata.get("slither_version") or "unknown",
                    "project_root_type": "directory",
                }
            saved_path = store.save(graph, identity=ident, meta=meta, force=True)

            # Update pool metadata
            pool.metadata["graph_built"] = True
            pool.metadata["graph_nodes"] = len(graph.nodes)
            pool.metadata["graph_edges"] = len(graph.edges)
            pool.metadata["graph_identity"] = ident
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.INTAKE,
                message=f"Built graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges",
                artifacts={
                    "graph_path": str(saved_path),
                    "identity": ident,
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                },
            )

        except ImportError as e:
            logger.error(f"Import error in BuildGraphHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.INTAKE,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Build graph failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.INTAKE,
                message=f"Build failed: {e}",
            )


class LoadContextHandler(BaseHandler):
    """Handler for LOAD_CONTEXT action.

    Loads protocol context pack for the pool.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Load protocol context pack.

        Args:
            pool: Pool to load context for
            target_beads: Ignored for context loading

        Returns:
            PhaseResult with context metadata
        """
        try:
            from alphaswarm_sol.context.storage import ContextPackStorage

            storage = ContextPackStorage(self.config.project_root / ".vrs" / "context")

            # Try to load existing context pack
            context_packs = storage.list_packs()

            if context_packs:
                # Use most recent context pack
                latest_pack = context_packs[0]
                pool.metadata["context_loaded"] = True
                pool.metadata["context_pack_id"] = latest_pack.id
                self.manager.storage.save_pool(pool)

                return PhaseResult(
                    success=True,
                    phase=LoopPhase.CONTEXT,
                    message=f"Loaded context pack: {latest_pack.id}",
                    artifacts={"context_pack_id": latest_pack.id},
                )

            # No context pack found - continue without
            pool.metadata["context_loaded"] = False
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.CONTEXT,
                message="No context pack found, proceeding without",
            )

        except ImportError as e:
            logger.warning(f"Context module not available: {e}")
            pool.metadata["context_loaded"] = False
            self.manager.storage.save_pool(pool)
            return PhaseResult(
                success=True,
                phase=LoopPhase.CONTEXT,
                message="Context module not available",
            )
        except Exception as e:
            logger.error(f"Load context failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.CONTEXT,
                message=f"Context load failed: {e}",
            )


class DetectPatternsHandler(BaseHandler):
    """Handler for DETECT_PATTERNS action.

    Runs pattern engine on the knowledge graph.

    Phase 5.9 Skills:
        During pattern detection, agents should invoke:
        - /vrs-taint-extend - Taint source/sink/sanitizer analysis
        - /vrs-slice-unify - Unified slicing pipeline for investigation context
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Run pattern detection on graph.

        Args:
            pool: Pool to detect patterns for
            target_beads: Ignored for pattern detection

        Returns:
            PhaseResult with matches found
        """
        try:
            from alphaswarm_sol.kg.store import GraphStore
            from alphaswarm_sol.queries.patterns import PatternEngine

            # Load graph (uses identity from pool metadata if available)
            graphs_dir = self.config.project_root / ".vrs" / "graphs"
            store = GraphStore(graphs_dir)
            graph_identity = pool.metadata.get("graph_identity")
            graph = store.load(identity=graph_identity)

            if graph is None:
                return PhaseResult(
                    success=False,
                    phase=LoopPhase.CONTEXT,
                    message="No graph found to analyze",
                )

            # Run pattern engine
            pattern_dir = self.config.pattern_dir or (self.config.project_root / "patterns")
            engine = PatternEngine(pattern_dir=pattern_dir)
            matches = engine.run_all_patterns(graph)

            # Update pool metadata
            pool.metadata["patterns_detected"] = True
            pool.metadata["match_count"] = len(matches)
            pool.metadata["matches"] = [
                {"pattern_id": m["pattern_id"], "node_id": m["node_id"], "severity": m["severity"]}
                for m in matches[:50]  # Limit stored matches
            ]
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.CONTEXT,
                message=f"Detected {len(matches)} pattern matches",
                artifacts={
                    "match_count": len(matches),
                    "matches": matches,
                },
            )

        except ImportError as e:
            logger.error(f"Import error in DetectPatternsHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.CONTEXT,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.CONTEXT,
                message=f"Detection failed: {e}",
            )


class CreateBeadsHandler(BaseHandler):
    """Handler for CREATE_BEADS action.

    Creates beads from pattern matches.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Create beads from pattern matches.

        Args:
            pool: Pool with pattern matches in metadata
            target_beads: Ignored for bead creation

        Returns:
            PhaseResult with created bead IDs
        """
        try:
            from alphaswarm_sol.beads.storage import BeadStorage
            from alphaswarm_sol.beads.schema import VulnerabilityBead

            # Get matches from pool metadata
            matches = pool.metadata.get("matches", [])
            if not matches:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.BEADS,
                    message="No matches to create beads from",
                )

            # Create beads from matches
            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            created_beads = []

            for match in matches:
                # Create bead for each match
                bead = VulnerabilityBead(
                    function_id=match.get("node_id", ""),
                    pattern_id=match.get("pattern_id", ""),
                    severity=match.get("severity", "medium"),
                    pool_id=pool.id,
                )

                # Save bead
                bead_storage.save(bead)
                created_beads.append(bead.id)
                pool.add_bead(bead.id)

            pool.metadata["beads_created"] = True
            pool.metadata["bead_count"] = len(created_beads)
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.BEADS,
                message=f"Created {len(created_beads)} beads",
                artifacts={"bead_ids": created_beads},
            )

        except ImportError as e:
            logger.error(f"Import error in CreateBeadsHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.BEADS,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Bead creation failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.BEADS,
                message=f"Creation failed: {e}",
            )


class SpawnAttackersHandler(BaseHandler):
    """Handler for SPAWN_ATTACKERS action.

    Spawns attacker agents for beads.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Spawn attacker agents for beads.

        Args:
            pool: Pool with beads to analyze
            target_beads: Optional subset of beads to process

        Returns:
            PhaseResult with processed bead IDs
        """
        try:
            from alphaswarm_sol.agents.attacker import AttackerAgent
            from alphaswarm_sol.beads.storage import BeadStorage

            beads_to_process = target_beads or pool.bead_ids
            if not beads_to_process:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.EXECUTE,
                    message="No beads to process",
                )

            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            attacker = AttackerAgent(use_llm=self.config.use_llm)
            processed = []

            for bead_id in beads_to_process:
                bead = bead_storage.load(bead_id)
                if not bead:
                    continue

                # Build simplified agent context
                context = self._build_agent_context(bead)

                try:
                    # Run attacker analysis
                    result = attacker.analyze(context)

                    # Update bead work_state
                    bead_storage.update_work_state(
                        bead_id,
                        {
                            "attacker_matched": result.matched,
                            "attacker_summary": getattr(result, "summary", None),
                            "attacker_confidence": result.confidence,
                        },
                        agent="attacker",
                    )
                    processed.append(bead_id)
                except Exception as e:
                    logger.warning(f"Attacker analysis failed for {bead_id}: {e}")

            # Track processed beads in pool metadata
            existing_processed = pool.metadata.get("attacker_processed", [])
            pool.metadata["attacker_processed"] = list(set(existing_processed + processed))
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.EXECUTE,
                message=f"Attacker analyzed {len(processed)} beads",
                artifacts={"processed": processed},
            )

        except ImportError as e:
            logger.error(f"Import error in SpawnAttackersHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Attacker spawn failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Spawn failed: {e}",
            )

    def _build_agent_context(self, bead: Any) -> Any:
        """Build AgentContext from bead.

        Creates a minimal context object for agent analysis.

        Args:
            bead: VulnerabilityBead to create context for

        Returns:
            Minimal context object with focal_nodes
        """
        return type(
            "AgentContext",
            (),
            {
                "focal_nodes": [bead.function_id],
                "subgraph": None,
                "upstream_results": [],
            },
        )()


class SpawnDefendersHandler(BaseHandler):
    """Handler for SPAWN_DEFENDERS action.

    Spawns defender agents for beads.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Spawn defender agents for beads.

        Args:
            pool: Pool with beads to analyze
            target_beads: Optional subset of beads to process

        Returns:
            PhaseResult with processed bead IDs
        """
        try:
            from alphaswarm_sol.agents.defender import DefenderAgent
            from alphaswarm_sol.beads.storage import BeadStorage

            beads_to_process = target_beads or pool.bead_ids
            if not beads_to_process:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.EXECUTE,
                    message="No beads to process",
                )

            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            defender = DefenderAgent(use_llm=self.config.use_llm)
            processed = []

            for bead_id in beads_to_process:
                bead = bead_storage.load(bead_id)
                if not bead:
                    continue

                context = self._build_agent_context(bead)

                try:
                    result = defender.analyze(context)

                    # Merge with existing work_state
                    existing_state = bead.work_state or {}
                    bead_storage.update_work_state(
                        bead_id,
                        {
                            **existing_state,
                            "defender_matched": result.matched,
                            "defender_summary": result.summary,
                            "defender_confidence": result.confidence,
                        },
                        agent="defender",
                    )
                    processed.append(bead_id)
                except Exception as e:
                    logger.warning(f"Defender analysis failed for {bead_id}: {e}")

            # Track processed beads
            existing_processed = pool.metadata.get("defender_processed", [])
            pool.metadata["defender_processed"] = list(set(existing_processed + processed))
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.EXECUTE,
                message=f"Defender analyzed {len(processed)} beads",
                artifacts={"processed": processed},
            )

        except ImportError as e:
            logger.error(f"Import error in SpawnDefendersHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Defender spawn failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Spawn failed: {e}",
            )

    def _build_agent_context(self, bead: Any) -> Any:
        """Build AgentContext from bead."""
        return type(
            "AgentContext",
            (),
            {
                "focal_nodes": [bead.function_id],
                "subgraph": None,
                "upstream_results": [],
            },
        )()


class SpawnVerifiersHandler(BaseHandler):
    """Handler for SPAWN_VERIFIERS action.

    Spawns verifier agents to synthesize attacker/defender results.

    Phase 5.9 Skills:
        During verification, agents should invoke:
        - /vrs-ordering-proof - Dominance-based path-qualified ordering verification
        - /vrs-evidence-audit - Deterministic evidence ID validation
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Spawn verifier agents for beads.

        Synthesizes attacker/defender results into preliminary confidence.

        Args:
            pool: Pool with beads that have attacker/defender analysis
            target_beads: Optional subset of beads to process

        Returns:
            PhaseResult with processed bead IDs
        """
        try:
            from alphaswarm_sol.beads.storage import BeadStorage

            beads_to_process = target_beads or pool.bead_ids
            if not beads_to_process:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.EXECUTE,
                    message="No beads to process",
                )

            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            processed = []

            for bead_id in beads_to_process:
                bead = bead_storage.load(bead_id)
                if not bead:
                    continue

                # Get attacker/defender results from work_state
                work_state = bead.work_state or {}
                attacker_matched = work_state.get("attacker_matched", False)
                defender_matched = work_state.get("defender_matched", False)
                attacker_conf = work_state.get("attacker_confidence", 0.0)
                defender_conf = work_state.get("defender_confidence", 0.0)

                # Simple synthesis logic
                if attacker_matched and not defender_matched:
                    confidence = "likely"
                elif defender_matched and not attacker_matched:
                    confidence = "rejected"
                elif attacker_conf > defender_conf + 0.2:
                    confidence = "likely"
                elif defender_conf > attacker_conf + 0.2:
                    confidence = "rejected"
                else:
                    confidence = "uncertain"

                bead_storage.update_work_state(
                    bead_id,
                    {
                        **work_state,
                        "verifier_confidence": confidence,
                        "verifier_processed": True,
                    },
                    agent="verifier",
                )
                processed.append(bead_id)

            # Track processed beads
            existing_processed = pool.metadata.get("verifier_processed", [])
            pool.metadata["verifier_processed"] = list(set(existing_processed + processed))
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.EXECUTE,
                message=f"Verifier processed {len(processed)} beads",
                artifacts={"processed": processed},
            )

        except ImportError as e:
            logger.error(f"Import error in SpawnVerifiersHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Verifier spawn failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.EXECUTE,
                message=f"Spawn failed: {e}",
            )


class RunDebateHandler(BaseHandler):
    """Handler for RUN_DEBATE action.

    Runs structured debate for disagreement cases.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Run structured debate for specified beads.

        Args:
            pool: Pool with beads that need debate
            target_beads: Beads with disagreement requiring debate

        Returns:
            PhaseResult with debate outcomes, always checkpoints for human review
        """
        try:
            from alphaswarm_sol.beads.storage import BeadStorage

            beads_to_debate = target_beads or []
            if not beads_to_debate:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.VERIFY,
                    message="No beads require debate",
                )

            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            orchestrator = DebateOrchestrator()
            debated = []

            for bead_id in beads_to_debate:
                bead = bead_storage.load(bead_id)
                if not bead:
                    continue

                # Run debate with empty context (agents not connected in handler)
                evidence = EvidencePacket(finding_id=bead_id)
                verdict = orchestrator.run_debate(
                    bead_id=bead_id,
                    evidence=evidence,
                    attacker_context={},
                    defender_context={},
                )

                # Record verdict in pool
                self.manager.record_verdict(pool.id, verdict)
                debated.append(bead_id)

            return PhaseResult(
                success=True,
                phase=LoopPhase.VERIFY,
                message=f"Debated {len(debated)} beads",
                checkpoint=True,  # Always pause after debate for human review
                artifacts={"debated_beads": debated},
            )

        except Exception as e:
            logger.error(f"Run debate failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.VERIFY,
                message=f"Debate failed: {e}",
            )


class CollectVerdictsHandler(BaseHandler):
    """Handler for COLLECT_VERDICTS action.

    Collects and finalizes all verdicts for the pool.

    Phase 5.9 Skills:
        Before finalizing verdicts, agents should invoke:
        - /vrs-evidence-audit - Validate evidence completeness and build hash
        - /vrs-graph-contract-validate - Final contract compliance check

    Phase 5.11-03 Integrity Gates:
        Before confidence upgrade, checks:
        - evidence_gate: Blocks upgrade without evidence_refs
        - provenance_gate: Only DECLARED expectations trigger misconfig findings
        - validate_causal_chain: Complete causal chain required for upgrade
        - Economic rationality gate: EV > 0 required for prioritization (via RationalityGate)
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Collect and finalize all verdicts.

        Creates verdicts from bead work_state for beads that don't have verdicts yet.
        Applies Phase 5.11-03 integrity gates before confidence upgrades.

        Args:
            pool: Pool with beads to collect verdicts for
            target_beads: Ignored, collects for all beads without verdicts

        Returns:
            PhaseResult with verdict count
        """
        try:
            from alphaswarm_sol.beads.storage import BeadStorage
            from alphaswarm_sol.findings.model import Finding, FindingConfidence, Location, Evidence

            bead_storage = BeadStorage(self.config.project_root / ".vrs" / "beads")
            enforcer = ConfidenceEnforcer()
            collected = 0
            gate_failures = []
            gap_nodes_created = []

            # Try to import rationality gate (may not exist yet)
            try:
                from alphaswarm_sol.economics.rationality_gate import RationalityGate, filter_by_economic_rationality
                rationality_gate = RationalityGate()
                has_rationality_gate = True
            except ImportError:
                rationality_gate = None
                has_rationality_gate = False
                logger.debug("RationalityGate not available, skipping economic filtering")

            for bead_id in pool.bead_ids:
                # Skip beads that already have verdicts
                if bead_id in pool.verdicts:
                    continue

                bead = bead_storage.load(bead_id)
                if not bead:
                    continue

                # Create verdict from work_state
                work_state = bead.work_state or {}
                confidence_str = work_state.get("verifier_confidence", "uncertain")

                confidence_map = {
                    "confirmed": VerdictConfidence.CONFIRMED,
                    "likely": VerdictConfidence.LIKELY,
                    "uncertain": VerdictConfidence.UNCERTAIN,
                    "rejected": VerdictConfidence.REJECTED,
                }
                confidence = confidence_map.get(confidence_str, VerdictConfidence.UNCERTAIN)

                # Phase 5.11-03: Apply integrity gates before confidence upgrade
                original_confidence = confidence
                gate_warnings = []

                # Create a Finding object for gate checks
                finding = Finding(
                    pattern=bead.pattern_id or "unknown",
                    severity=FindingConfidence.MEDIUM,
                    confidence=FindingConfidence.MEDIUM,
                    location=Location(file="", line=0),
                    description="",
                    id=bead_id,
                    evidence=Evidence(
                        evidence_refs=work_state.get("evidence_refs", []),
                        behavioral_signature=work_state.get("behavioral_signature", ""),
                    ),
                )

                # Gate 1: Evidence gate - block upgrade without evidence
                if confidence in (VerdictConfidence.CONFIRMED, VerdictConfidence.LIKELY):
                    if not evidence_gate(finding):
                        confidence = VerdictConfidence.UNCERTAIN
                        gate_warnings.append(f"Evidence gate: downgraded {bead_id} from {original_confidence.value} to uncertain (no evidence_refs)")
                        gate_failures.append({
                            "bead_id": bead_id,
                            "gate": "evidence",
                            "action": "downgrade_to_uncertain",
                        })

                # Gate 2: Causal chain validation - block upgrade without complete chain
                if confidence in (VerdictConfidence.CONFIRMED, VerdictConfidence.LIKELY):
                    chain_data = work_state.get("causal_chain")
                    chain_result = validate_causal_chain(bead_id, chain_data)

                    if not chain_result.allows_confidence_upgrade():
                        confidence = VerdictConfidence.UNCERTAIN
                        gate_warnings.append(f"Causal chain gate: downgraded {bead_id} (incomplete chain: {chain_result.missing_links})")

                        # Create gap nodes for missing links
                        for gap_id in chain_result.gap_nodes_needed:
                            gap_nodes_created.append(gap_id)
                            logger.info(f"Gap node needed: {gap_id}")

                        gate_failures.append({
                            "bead_id": bead_id,
                            "gate": "causal_chain",
                            "action": "downgrade_to_uncertain",
                            "gap_nodes": chain_result.gap_nodes_needed,
                        })

                # Gate 3: Provenance gate for misconfig findings
                is_misconfig = "misconfig" in (bead.pattern_id or "").lower()
                if is_misconfig and confidence.is_positive():
                    expectation_evidence = work_state.get("expectation_evidence")
                    if expectation_evidence:
                        exp_ev = ExpectationEvidence(
                            source_id=expectation_evidence.get("source_id", ""),
                            source_date=expectation_evidence.get("source_date", ""),
                            source_type=expectation_evidence.get("source_type", ""),
                            provenance=ExpectationProvenance(expectation_evidence.get("provenance", "hypothesis")),
                        )
                        passes, warning = provenance_gate(finding, exp_ev, is_misconfig_finding=True)
                        if not passes:
                            confidence = VerdictConfidence.UNCERTAIN
                            gate_warnings.append(f"Provenance gate: {warning}")
                            gate_failures.append({
                                "bead_id": bead_id,
                                "gate": "provenance",
                                "action": "downgrade_to_uncertain",
                                "reason": warning,
                            })
                    else:
                        # No expectation evidence for misconfig - downgrade
                        confidence = VerdictConfidence.UNCERTAIN
                        gate_warnings.append(f"Provenance gate: misconfig finding {bead_id} has no expectation evidence")

                # Log gate warnings
                for warning in gate_warnings:
                    logger.warning(warning)

                # Build rationale from attacker/defender summaries
                attacker_summary = work_state.get("attacker_summary", "N/A")
                defender_summary = work_state.get("defender_summary", "N/A")
                rationale = f"Attacker: {attacker_summary} | Defender: {defender_summary}"

                # Add gate failure info to rationale if any
                if gate_warnings:
                    rationale += f" | Integrity gates: {'; '.join(gate_warnings)}"

                verdict = Verdict(
                    finding_id=bead_id,
                    confidence=confidence,
                    is_vulnerable=confidence.is_positive(),
                    rationale=rationale,
                    human_flag=True,
                    created_by="collect_verdicts_handler",
                )

                # Enforce confidence rules
                verdict = enforcer.enforce(verdict)

                # Record verdict
                self.manager.record_verdict(pool.id, verdict)
                collected += 1

            # Store gate failure summary in pool metadata
            pool.metadata["integrity_gates"] = {
                "failures": gate_failures,
                "gap_nodes_created": gap_nodes_created,
                "total_failures": len(gate_failures),
            }
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.VERIFY,
                message=f"Collected {collected} verdicts, total: {len(pool.verdicts)}, gate failures: {len(gate_failures)}",
                artifacts={
                    "collected": collected,
                    "total_verdicts": len(pool.verdicts),
                    "gate_failures": len(gate_failures),
                    "gap_nodes_created": gap_nodes_created,
                },
            )

        except ImportError as e:
            logger.error(f"Import error in CollectVerdictsHandler: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.VERIFY,
                message=f"Import error: {e}",
            )
        except Exception as e:
            logger.error(f"Collect verdicts failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.VERIFY,
                message=f"Collection failed: {e}",
            )


class MergeResultsHandler(BaseHandler):
    """Handler for merging batch results with conflict quarantine.

    Phase 5.10-10: Implements append-only merge with:
    - Deterministic ordering via ordering_key
    - Conflict detection and quarantine for resolver agent
    - Idempotent replay verification
    - Full audit trail preservation
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Merge batch results into pool with conflict quarantine.

        Merges deltas from all batches associated with the pool.
        Conflicts are quarantined for resolver agent review.

        Args:
            pool: Pool to merge results into
            target_beads: Ignored (merges all batches)

        Returns:
            PhaseResult with merge statistics and conflicts
        """
        try:
            # Get batches from pool metadata
            batch_data = pool.metadata.get("pending_batches", [])
            if not batch_data:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.INTEGRATE,
                    message="No pending batches to merge",
                )

            # Convert to MergeBatch objects
            batches: List[MergeBatch] = []
            for bd in batch_data:
                if isinstance(bd, dict):
                    batches.append(MergeBatch.from_dict(bd))
                elif isinstance(bd, MergeBatch):
                    batches.append(bd)

            # Get existing merged deltas for incremental merge
            existing_deltas_data = pool.metadata.get("merged_deltas", [])
            existing_deltas = [
                DeltaEntry.from_dict(d) if isinstance(d, dict) else d
                for d in existing_deltas_data
            ]

            # Execute merge
            result = merge_batch_deltas(batches, existing_deltas)

            # Store merged deltas back to pool metadata
            pool.metadata["merged_deltas"] = [d.to_dict() for d in result.merged_deltas]
            pool.metadata["merge_output_hash"] = result.output_hash
            pool.metadata["merge_audit_trail"] = result.audit_trail

            # Quarantine conflicts for resolver agent
            if result.conflicts:
                self._quarantine_conflicts(pool, result.conflicts)

            # Clear pending batches (now merged)
            pool.metadata["pending_batches"] = []
            self.manager.storage.save_pool(pool)

            # Checkpoint if conflicts need resolver
            checkpoint = len(result.conflicts) > 0

            return PhaseResult(
                success=True,
                phase=LoopPhase.INTEGRATE,
                checkpoint=checkpoint,
                message=f"Merged {len(result.merged_deltas)} deltas, {len(result.conflicts)} conflicts quarantined",
                artifacts={
                    "merged_count": len(result.merged_deltas),
                    "conflict_count": len(result.conflicts),
                    "output_hash": result.output_hash,
                    "idempotent": result.idempotent,
                    "conflicts": [c.to_dict() for c in result.conflicts],
                },
            )

        except Exception as e:
            logger.error(f"Merge results failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.INTEGRATE,
                message=f"Merge failed: {e}",
            )

    def _quarantine_conflicts(self, pool: Pool, conflicts: List[MergeConflict]) -> None:
        """Quarantine conflicts for resolver agent.

        Preserves both deltas for audit and routes to resolver.

        Args:
            pool: Pool to store conflicts in
            conflicts: List of detected conflicts
        """
        quarantined = pool.metadata.get("quarantined_conflicts", [])

        for conflict in conflicts:
            quarantine_entry = {
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "delta_a_id": conflict.delta_a.delta_id,
                "delta_b_id": conflict.delta_b.delta_id,
                "description": conflict.description,
                "timestamp": conflict.timestamp,
                # Preserve full deltas for audit
                "delta_a": conflict.delta_a.to_dict(),
                "delta_b": conflict.delta_b.to_dict(),
                "status": "pending_resolution",
            }
            quarantined.append(quarantine_entry)

        pool.metadata["quarantined_conflicts"] = quarantined
        pool.metadata["has_unresolved_conflicts"] = len(quarantined) > 0

        logger.info(
            "conflicts_quarantined",
            pool_id=pool.id,
            conflict_count=len(conflicts),
        )


class ResolveConflictsHandler(BaseHandler):
    """Handler for resolver agent to process quarantined conflicts.

    Phase 5.10-10: Processes conflicts and produces resolution decisions.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Process quarantined conflicts via resolver agent.

        Args:
            pool: Pool with quarantined conflicts
            target_beads: Optional specific conflict IDs to resolve

        Returns:
            PhaseResult with resolution outcomes
        """
        try:
            quarantined = pool.metadata.get("quarantined_conflicts", [])
            if not quarantined:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.VERIFY,
                    message="No conflicts to resolve",
                )

            # Filter to target conflicts if specified
            conflicts_to_resolve = [
                c for c in quarantined
                if not target_beads or c.get("conflict_id") in target_beads
            ]

            resolved = []
            for conflict in conflicts_to_resolve:
                # Simple resolution: prefer higher evidence count
                delta_a = conflict.get("delta_a", {})
                delta_b = conflict.get("delta_b", {})

                evidence_a = len(delta_a.get("evidence_ids", []))
                evidence_b = len(delta_b.get("evidence_ids", []))

                if evidence_a >= evidence_b:
                    winning_delta = "delta_a"
                    reason = f"More evidence ({evidence_a} vs {evidence_b})"
                else:
                    winning_delta = "delta_b"
                    reason = f"More evidence ({evidence_b} vs {evidence_a})"

                conflict["status"] = "resolved"
                conflict["resolution"] = {
                    "winning_delta": winning_delta,
                    "reason": reason,
                    "resolver": "auto_evidence_count",
                }
                resolved.append(conflict["conflict_id"])

            # Update metadata
            pool.metadata["quarantined_conflicts"] = quarantined
            pool.metadata["has_unresolved_conflicts"] = any(
                c.get("status") == "pending_resolution"
                for c in quarantined
            )
            self.manager.storage.save_pool(pool)

            return PhaseResult(
                success=True,
                phase=LoopPhase.VERIFY,
                message=f"Resolved {len(resolved)} conflicts",
                artifacts={"resolved_conflicts": resolved},
            )

        except Exception as e:
            logger.error(f"Resolve conflicts failed: {e}")
            return PhaseResult(
                success=False,
                phase=LoopPhase.VERIFY,
                message=f"Resolution failed: {e}",
            )


class GenerateReportHandler(BaseHandler):
    """Handler for GENERATE_REPORT action.

    Generates final audit report from pool verdicts.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Generate final audit report.

        Args:
            pool: Pool with verdicts to report
            target_beads: Ignored for report generation

        Returns:
            PhaseResult with report summary
        """
        # Build report summary
        report = {
            "pool_id": pool.id,
            "beads_analyzed": len(pool.bead_ids),
            "verdicts_count": len(pool.verdicts),
            "verdicts": {},
            "summary": {
                "confirmed": 0,
                "likely": 0,
                "uncertain": 0,
                "rejected": 0,
            },
        }

        for bead_id, verdict in pool.verdicts.items():
            report["verdicts"][bead_id] = {
                "confidence": verdict.confidence.value,
                "is_vulnerable": verdict.is_vulnerable,
                "rationale": verdict.rationale[:200],  # Truncate for summary
                "human_flag": verdict.human_flag,
            }

            # Count by confidence
            report["summary"][verdict.confidence.value] += 1

        # Store report in pool metadata
        pool.metadata["report_generated"] = True
        pool.metadata["report"] = report
        self.manager.storage.save_pool(pool)

        return PhaseResult(
            success=True,
            phase=LoopPhase.INTEGRATE,
            message=f"Report generated: {report['summary']}",
            artifacts={"report": report},
        )


class FlagForHumanHandler(BaseHandler):
    """Handler for FLAG_FOR_HUMAN action.

    Flags beads for human review and pauses the loop.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Flag beads for human review.

        Args:
            pool: Pool with beads to flag
            target_beads: Beads requiring human review

        Returns:
            PhaseResult with checkpoint=True
        """
        beads_for_review = target_beads or []

        # Store in pool metadata
        existing_flagged = pool.metadata.get("flagged_for_human", [])
        pool.metadata["flagged_for_human"] = list(set(existing_flagged + beads_for_review))
        self.manager.storage.save_pool(pool)

        return PhaseResult(
            success=True,
            phase=LoopPhase.VERIFY,
            checkpoint=True,
            message=f"Human review required for {len(beads_for_review)} beads",
            artifacts={"beads_for_review": beads_for_review},
        )


class CompleteHandler(BaseHandler):
    """Handler for COMPLETE action.

    Marks the audit as complete.
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Mark audit as complete.

        Args:
            pool: Pool to complete
            target_beads: Ignored

        Returns:
            PhaseResult indicating completion
        """
        return PhaseResult(
            success=True,
            phase=LoopPhase.COMPLETE,
            message="Audit complete",
        )


class WaitHandler(BaseHandler):
    """Handler for WAIT action.

    Returns waiting status (no-op).
    """

    def __call__(self, pool: Pool, target_beads: Optional[List[str]] = None) -> PhaseResult:
        """Wait for next action.

        Args:
            pool: Pool in waiting state
            target_beads: Ignored

        Returns:
            PhaseResult indicating waiting
        """
        return PhaseResult(
            success=True,
            phase=LoopPhase.INTAKE,
            message="Waiting",
        )


def create_default_handlers(
    manager: PoolManager,
    config: Optional[HandlerConfig] = None,
) -> Dict[RouteAction, Callable[[Pool, Optional[List[str]]], PhaseResult]]:
    """Create default handlers for all route actions.

    Provides a complete set of handlers for the execution loop.

    Args:
        manager: Pool manager for persistence
        config: Handler configuration

    Returns:
        Dict mapping RouteAction to handler callable

    Usage:
        handlers = create_default_handlers(manager, config)
        for action, handler in handlers.items():
            loop.register_handler(action, handler)
    """
    cfg = config or HandlerConfig()

    return {
        RouteAction.BUILD_GRAPH: BuildGraphHandler(manager, cfg),
        RouteAction.LOAD_CONTEXT: LoadContextHandler(manager, cfg),
        RouteAction.DETECT_PATTERNS: DetectPatternsHandler(manager, cfg),
        RouteAction.CREATE_BEADS: CreateBeadsHandler(manager, cfg),
        RouteAction.SPAWN_ATTACKERS: SpawnAttackersHandler(manager, cfg),
        RouteAction.SPAWN_DEFENDERS: SpawnDefendersHandler(manager, cfg),
        RouteAction.SPAWN_VERIFIERS: SpawnVerifiersHandler(manager, cfg),
        RouteAction.RUN_DEBATE: RunDebateHandler(manager, cfg),
        RouteAction.COLLECT_VERDICTS: CollectVerdictsHandler(manager, cfg),
        RouteAction.GENERATE_REPORT: GenerateReportHandler(manager, cfg),
        RouteAction.FLAG_FOR_HUMAN: FlagForHumanHandler(manager, cfg),
        RouteAction.COMPLETE: CompleteHandler(manager, cfg),
        RouteAction.WAIT: WaitHandler(manager, cfg),
    }


# Type alias for handlers
PhaseHandler = Callable[[Pool, Optional[List[str]]], PhaseResult]


# Export for module
__all__ = [
    "HandlerConfig",
    "BaseHandler",
    "BuildGraphHandler",
    "LoadContextHandler",
    "DetectPatternsHandler",
    "CreateBeadsHandler",
    "SpawnAttackersHandler",
    "SpawnDefendersHandler",
    "SpawnVerifiersHandler",
    "RunDebateHandler",
    "CollectVerdictsHandler",
    "GenerateReportHandler",
    "FlagForHumanHandler",
    "CompleteHandler",
    "WaitHandler",
    "create_default_handlers",
    "PhaseHandler",
    # Merge pipeline v2 handlers (Phase 5.10-10)
    "MergeResultsHandler",
    "ResolveConflictsHandler",
    # Idempotency helpers (Phase 07.1.1-02)
    "make_idempotency_key",
    "hash_payload",
]
