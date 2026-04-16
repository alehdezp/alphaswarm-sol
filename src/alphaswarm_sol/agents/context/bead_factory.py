"""ContextBeadFactory - creates beads from verified context-merge outputs.

Per 05.5-CONTEXT.md:
- Every bead creation goes through a skill
- Factory validates MergeResult before bead creation
- Beads stored in pool structure
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from alphaswarm_sol.agents.context.merger import MergeResult
from alphaswarm_sol.agents.context.verifier import VerificationResult

if TYPE_CHECKING:
    from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus


class ContextBeadFactory:
    """Factory for creating context-merge beads.

    The factory creates beads from verified merge results and manages
    storage in a pool-based directory structure.

    Attributes:
        beads_dir: Base directory for bead storage

    Usage:
        factory = ContextBeadFactory(beads_dir=Path(".vrs/beads"))
        bead = factory.create_from_verified_merge(
            merge_result=merge_result,
            verification_result=verification_result,
            pool_id="audit-2026-01",
        )
        factory.save_bead(bead)
    """

    def __init__(self, beads_dir: Path = Path(".vrs/beads")):
        """Initialize factory with bead storage directory.

        Args:
            beads_dir: Base directory for bead storage
        """
        self.beads_dir = beads_dir
        self.beads_dir.mkdir(parents=True, exist_ok=True)

    def create_from_verified_merge(
        self,
        merge_result: MergeResult,
        verification_result: VerificationResult,
        pool_id: Optional[str] = None,
        created_by: str = "context-merge-agent",
    ) -> ContextMergeBead:
        """Create bead from verified merge result.

        Args:
            merge_result: Successful MergeResult from ContextMerger
            verification_result: Passing VerificationResult from ContextVerifier
            pool_id: Optional pool to associate bead with
            created_by: Agent creating the bead

        Returns:
            Created ContextMergeBead

        Raises:
            ValueError: If merge or verification failed
        """
        # Import at runtime to avoid circular import
        from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus

        if not merge_result.success:
            raise ValueError(
                f"Cannot create bead from failed merge: {merge_result.errors}"
            )
        if not verification_result.valid:
            raise ValueError(
                f"Cannot create bead from failed verification: {verification_result.errors}"
            )

        bundle = merge_result.bundle
        if bundle is None:
            raise ValueError("Merge result has no bundle")

        timestamp = datetime.now()

        bead = ContextMergeBead(
            id=ContextMergeBead.generate_id(
                vuln_class=bundle.vulnerability_class,
                protocol_name=bundle.protocol_name,
                timestamp=timestamp,
            ),
            vulnerability_class=bundle.vulnerability_class,
            protocol_name=bundle.protocol_name,
            context_bundle=bundle,
            target_scope=bundle.target_scope,
            verification_score=verification_result.quality_score,
            verification_warnings=[w.message for w in verification_result.warnings],
            status=ContextBeadStatus.PENDING,
            created_at=timestamp,
            created_by=created_by,
            pool_id=pool_id,
        )

        return bead

    def save_bead(self, bead) -> Path:
        """Save bead to storage.

        Beads are organized by pool directory. If no pool is set,
        they go to the "unassigned" directory.

        Args:
            bead: Context bead to save

        Returns:
            Path to saved bead file
        """
        # Organize by pool if set
        if bead.pool_id:
            bead_dir = self.beads_dir / bead.pool_id
        else:
            bead_dir = self.beads_dir / "unassigned"

        bead_dir.mkdir(parents=True, exist_ok=True)
        bead_path = bead_dir / f"{bead.id}.yaml"
        bead_path.write_text(bead.to_yaml())
        return bead_path

    def load_bead(
        self, bead_id: str, pool_id: Optional[str] = None
    ):
        """Load bead from storage.

        Args:
            bead_id: Bead ID to load
            pool_id: Pool ID if known (searches all pools if not provided)

        Returns:
            Loaded ContextMergeBead

        Raises:
            FileNotFoundError: If bead not found
        """
        from alphaswarm_sol.beads.context_merge import ContextMergeBead

        if pool_id:
            bead_path = self.beads_dir / pool_id / f"{bead_id}.yaml"
        else:
            # Search unassigned and all pools
            bead_path = self.beads_dir / "unassigned" / f"{bead_id}.yaml"
            if not bead_path.exists():
                # Search pools
                for pool_dir in self.beads_dir.iterdir():
                    if pool_dir.is_dir():
                        candidate = pool_dir / f"{bead_id}.yaml"
                        if candidate.exists():
                            bead_path = candidate
                            break

        if not bead_path.exists():
            raise FileNotFoundError(f"Bead not found: {bead_id}")

        return ContextMergeBead.from_yaml(bead_path.read_text())

    def list_pending_beads(self, pool_id: Optional[str] = None) -> List:
        """List all pending context beads.

        Args:
            pool_id: Filter by pool ID (None = all pools)

        Returns:
            List of pending ContextMergeBeads
        """
        from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus

        beads = []
        if pool_id:
            search_dirs = [self.beads_dir / pool_id]
        else:
            # Search all pool directories
            search_dirs = [d for d in self.beads_dir.iterdir() if d.is_dir()]

        for bead_dir in search_dirs:
            if not bead_dir.exists():
                continue
            for bead_file in bead_dir.glob("CTX-*.yaml"):
                try:
                    bead = ContextMergeBead.from_yaml(bead_file.read_text())
                    if bead.status == ContextBeadStatus.PENDING:
                        beads.append(bead)
                except Exception:
                    # Skip malformed beads
                    continue

        return beads
