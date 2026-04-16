"""Pipeline Orchestrator for Multi-Model Knowledge Mining.

Task 18.2: Coordinates the full crawl-process-merge-link-validate pipeline.

Architecture:
    /vuln-build skill invokes PipelineOrchestrator
    → Phase 1: Crawl (Haiku workers)
    → Phase 2: Process (Haiku workers)
    → Phase 3: Merge (Opus orchestrators)
    → Phase 4: Link (Opus linker)
    → Phase 5: Validate (Opus validator)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from alphaswarm_sol.vulndocs.agents.base import (
    AgentConfig,
    AgentResult,
    AgentStatus,
    TaskProgress,
)
from alphaswarm_sol.vulndocs.agents.category_agent import (
    CategoryAgent,
    CategoryResult,
    CategorySource,
    get_all_categories,
)
from alphaswarm_sol.vulndocs.agents.merge_orchestrator import MergeOrchestrator
from alphaswarm_sol.vulndocs.knowledge_doc import MergeResult, VulnKnowledgeDoc

logger = logging.getLogger(__name__)


class PipelinePhase(Enum):
    """Phases in the knowledge mining pipeline."""

    CRAWL = "crawl"
    PROCESS = "process"
    MERGE = "merge"
    LINK = "link"
    VALIDATE = "validate"


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""

    # Phase 1: Crawl
    crawl_concurrent: int = 20
    crawl_rate_limit: float = 1.0

    # Phase 2: Process
    process_concurrent: int = 50
    process_batch_size: int = 10

    # Phase 3: Merge
    merge_concurrent: int = 15  # One per category

    # Phase 4: Link
    link_timeout: int = 300

    # Phase 5: Validate
    validate_completeness_threshold: float = 0.8

    # General
    dry_run: bool = False
    verbose: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "crawl_concurrent": self.crawl_concurrent,
            "crawl_rate_limit": self.crawl_rate_limit,
            "process_concurrent": self.process_concurrent,
            "process_batch_size": self.process_batch_size,
            "merge_concurrent": self.merge_concurrent,
            "link_timeout": self.link_timeout,
            "validate_completeness_threshold": self.validate_completeness_threshold,
            "dry_run": self.dry_run,
            "verbose": self.verbose,
        }


@dataclass
class PhaseResult:
    """Result of a pipeline phase."""

    phase: PipelinePhase
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    items_processed: int = 0
    items_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "phase": self.phase.value,
            "success": self.success,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
        }


@dataclass
class PipelineResult:
    """Result of the full pipeline run."""

    success: bool
    phases: List[PhaseResult] = field(default_factory=list)
    documents: List[VulnKnowledgeDoc] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    start_time: str = ""
    end_time: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        """Set timestamps if not provided."""
        if not self.start_time:
            self.start_time = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "phases": [p.to_dict() for p in self.phases],
            "document_count": len(self.documents),
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
        }

    def get_phase_result(self, phase: PipelinePhase) -> Optional[PhaseResult]:
        """Get result for a specific phase."""
        for p in self.phases:
            if p.phase == phase:
                return p
        return None


class PipelineOrchestrator:
    """Orchestrates the full knowledge mining pipeline.

    Coordinates Haiku workers and Opus orchestrators across all phases.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
    ):
        """Initialize the pipeline orchestrator.

        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self.progress_callbacks: List[Callable[[PipelinePhase, TaskProgress], None]] = []
        self._current_phase: Optional[PipelinePhase] = None

    def add_progress_callback(
        self, callback: Callable[[PipelinePhase, TaskProgress], None]
    ) -> None:
        """Add a progress callback.

        Args:
            callback: Function called with (phase, progress)
        """
        self.progress_callbacks.append(callback)

    def _notify_progress(self, progress: TaskProgress) -> None:
        """Notify callbacks of progress."""
        if self._current_phase:
            for callback in self.progress_callbacks:
                try:
                    callback(self._current_phase, progress)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

    async def run(
        self,
        sources: Optional[Dict[str, List[CategorySource]]] = None,
        categories: Optional[List[str]] = None,
    ) -> PipelineResult:
        """Run the full pipeline.

        Args:
            sources: Dictionary of category -> sources. If None, uses all sources.
            categories: Categories to process. If None, processes all.

        Returns:
            PipelineResult with all generated documents
        """
        result = PipelineResult(success=False)
        start_time = datetime.utcnow()

        try:
            # Determine categories to process
            if categories is None:
                categories = get_all_categories()

            logger.info(f"Starting pipeline for {len(categories)} categories")

            # Phase 1: Crawl (if sources not provided)
            if sources is None:
                self._current_phase = PipelinePhase.CRAWL
                crawl_result = await self._run_crawl_phase(categories)
                result.phases.append(crawl_result)
                if not crawl_result.success:
                    result.error = f"Crawl phase failed: {crawl_result.error}"
                    return result
                sources = crawl_result.data
            else:
                # Skip crawl, use provided sources
                result.phases.append(
                    PhaseResult(
                        phase=PipelinePhase.CRAWL,
                        success=True,
                        items_processed=sum(len(s) for s in sources.values()),
                    )
                )

            # Phase 2: Process
            self._current_phase = PipelinePhase.PROCESS
            process_result = await self._run_process_phase(sources)
            result.phases.append(process_result)
            if not process_result.success:
                result.error = f"Process phase failed: {process_result.error}"
                return result
            category_results: List[CategoryResult] = process_result.data

            # Phase 3: Merge
            self._current_phase = PipelinePhase.MERGE
            merge_result = await self._run_merge_phase(category_results)
            result.phases.append(merge_result)
            if not merge_result.success:
                result.error = f"Merge phase failed: {merge_result.error}"
                return result
            merge_results: List[MergeResult] = merge_result.data

            # Phase 4: Link
            self._current_phase = PipelinePhase.LINK
            link_result = await self._run_link_phase(merge_results)
            result.phases.append(link_result)
            if not link_result.success:
                result.error = f"Link phase failed: {link_result.error}"
                return result
            linked_docs: List[VulnKnowledgeDoc] = link_result.data

            # Phase 5: Validate
            self._current_phase = PipelinePhase.VALIDATE
            validate_result = await self._run_validate_phase(linked_docs)
            result.phases.append(validate_result)

            result.documents = linked_docs
            result.success = True

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            result.error = str(e)

        finally:
            end_time = datetime.utcnow()
            result.end_time = end_time.isoformat()
            result.total_duration_seconds = (end_time - start_time).total_seconds()
            self._current_phase = None

        return result

    async def _run_crawl_phase(
        self, categories: List[str]
    ) -> PhaseResult:
        """Run the crawl phase (placeholder - uses provided sources in real impl).

        Args:
            categories: Categories to crawl

        Returns:
            PhaseResult with crawled sources
        """
        start_time = datetime.utcnow()
        logger.info(f"Phase 1: Crawl - {len(categories)} categories")

        # In real implementation, this would use Crawl4AI
        # For now, return empty sources (caller should provide)
        sources: Dict[str, List[CategorySource]] = {cat: [] for cat in categories}

        return PhaseResult(
            phase=PipelinePhase.CRAWL,
            success=True,
            data=sources,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            items_processed=len(categories),
        )

    async def _run_process_phase(
        self, sources: Dict[str, List[CategorySource]]
    ) -> PhaseResult:
        """Run the process phase with CategoryAgents.

        Args:
            sources: Dictionary of category -> sources

        Returns:
            PhaseResult with CategoryResults
        """
        start_time = datetime.utcnow()
        logger.info(f"Phase 2: Process - {len(sources)} categories")

        results: List[CategoryResult] = []
        failed = 0

        # Create category agents and process in parallel
        tasks = []
        for category, category_sources in sources.items():
            if not category_sources:
                continue

            agent = CategoryAgent(category)
            agent.add_progress_callback(self._notify_progress)
            tasks.append(agent.process(category_sources))

        # Execute all category agents
        if tasks:
            agent_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in agent_results:
                if isinstance(result, Exception):
                    logger.error(f"Category agent failed: {result}")
                    failed += 1
                elif result.success and result.data:
                    results.append(result.data)
                else:
                    failed += 1

        return PhaseResult(
            phase=PipelinePhase.PROCESS,
            success=True,
            data=results,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            items_processed=len(results),
            items_failed=failed,
        )

    async def _run_merge_phase(
        self, category_results: List[CategoryResult]
    ) -> PhaseResult:
        """Run the merge phase with MergeOrchestrators.

        Args:
            category_results: Results from process phase

        Returns:
            PhaseResult with MergeResults
        """
        start_time = datetime.utcnow()
        logger.info(f"Phase 3: Merge - {len(category_results)} categories")

        merge_results: List[MergeResult] = []
        failed = 0

        # Create merge tasks for each subcategory
        tasks = []
        for cat_result in category_results:
            for sub_result in cat_result.subcategory_results:
                orchestrator = MergeOrchestrator()
                tasks.append(
                    orchestrator.process(
                        {
                            "category": cat_result.category,
                            "subcategory": sub_result.subcategory,
                            "summaries": sub_result.summaries,
                        }
                    )
                )

        # Execute merge orchestrators with limited concurrency
        semaphore = asyncio.Semaphore(self.config.merge_concurrent)

        async def merge_with_semaphore(task):
            async with semaphore:
                return await task

        if tasks:
            results = await asyncio.gather(
                *[merge_with_semaphore(t) for t in tasks],
                return_exceptions=True,
            )

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Merge orchestrator failed: {result}")
                    failed += 1
                elif result.success and result.data:
                    merge_results.append(result.data)
                else:
                    failed += 1

        return PhaseResult(
            phase=PipelinePhase.MERGE,
            success=True,
            data=merge_results,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            items_processed=len(merge_results),
            items_failed=failed,
        )

    async def _run_link_phase(
        self, merge_results: List[MergeResult]
    ) -> PhaseResult:
        """Run the link phase to connect documents to VKG patterns.

        Args:
            merge_results: Results from merge phase

        Returns:
            PhaseResult with linked VulnKnowledgeDocs
        """
        start_time = datetime.utcnow()
        logger.info(f"Phase 4: Link - {len(merge_results)} documents")

        # Extract documents and verify pattern linkage
        documents = []
        for merge_result in merge_results:
            doc = merge_result.document

            # Pattern linkage is already done in merge phase
            # This phase could be extended to verify patterns exist
            # and update coverage statistics

            documents.append(doc)

        return PhaseResult(
            phase=PipelinePhase.LINK,
            success=True,
            data=documents,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            items_processed=len(documents),
        )

    async def _run_validate_phase(
        self, documents: List[VulnKnowledgeDoc]
    ) -> PhaseResult:
        """Run the validation phase to ensure quality.

        Args:
            documents: Documents to validate

        Returns:
            PhaseResult with validation metrics
        """
        start_time = datetime.utcnow()
        logger.info(f"Phase 5: Validate - {len(documents)} documents")

        # Calculate quality metrics
        valid_count = 0
        invalid_docs = []

        for doc in documents:
            completeness = doc.metadata.completeness_score
            if completeness >= self.config.validate_completeness_threshold:
                valid_count += 1
            else:
                invalid_docs.append(doc.id)

        if invalid_docs:
            logger.warning(
                f"Low completeness documents: {', '.join(invalid_docs[:5])}"
            )

        return PhaseResult(
            phase=PipelinePhase.VALIDATE,
            success=True,
            data={
                "total": len(documents),
                "valid": valid_count,
                "invalid": len(invalid_docs),
                "invalid_ids": invalid_docs,
            },
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            items_processed=len(documents),
            items_failed=len(invalid_docs),
        )

    async def run_single_category(
        self,
        category: str,
        sources: List[CategorySource],
    ) -> List[VulnKnowledgeDoc]:
        """Process a single category.

        Convenience method for testing or incremental processing.

        Args:
            category: Category to process
            sources: Sources for the category

        Returns:
            List of generated VulnKnowledgeDocs
        """
        result = await self.run(
            sources={category: sources},
            categories=[category],
        )
        return result.documents


async def build_knowledge_base(
    sources: Dict[str, List[CategorySource]],
    config: Optional[PipelineConfig] = None,
    progress_callback: Optional[Callable[[PipelinePhase, TaskProgress], None]] = None,
) -> PipelineResult:
    """Build the complete knowledge base.

    High-level function for running the full pipeline.

    Args:
        sources: Dictionary of category -> sources
        config: Pipeline configuration
        progress_callback: Optional progress callback

    Returns:
        PipelineResult with all generated documents
    """
    orchestrator = PipelineOrchestrator(config)
    if progress_callback:
        orchestrator.add_progress_callback(progress_callback)
    return await orchestrator.run(sources)
