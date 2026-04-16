"""Vuln Build Skill - Full Pipeline Orchestrator.

Task 18.2: Main skill for building the vulnerability knowledge base.

Usage:
    /vuln-build                    # Build all categories
    /vuln-build reentrancy         # Build single category
    /vuln-build --incremental      # Only new content
    /vuln-build --validate         # Build + validation
    /vuln-build --dry-run          # Preview without changes

This skill orchestrates:
1. /vuln-crawl (Haiku) - Fetch content from sources
2. /vuln-process (Haiku) - Extract and summarize
3. /vuln-merge (Opus) - Intelligently combine
4. /vuln-link (Opus) - Connect to patterns
5. Validation - Ensure quality
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from alphaswarm_sol.vulndocs.agents.category_agent import (
    CategorySource,
    get_all_categories,
)
from alphaswarm_sol.vulndocs.pipeline.orchestrator import (
    PipelineConfig,
    PipelineOrchestrator,
    PipelinePhase,
    PipelineResult,
)
from alphaswarm_sol.vulndocs.agents.base import TaskProgress

logger = logging.getLogger(__name__)


# Skill definition for Claude Code
SKILL_DEFINITION = {
    "name": "vuln-build",
    "description": "Build vulnerability knowledge base using multi-model pipeline",
    "model": "opus",  # Orchestrator uses Opus, workers use Haiku
    "commands": [
        "/vuln-build",
        "/vuln-build <category>",
        "/vuln-build --all",
        "/vuln-build --incremental",
        "/vuln-build --validate",
        "/vuln-build --dry-run",
    ],
    "examples": [
        {
            "command": "/vuln-build reentrancy",
            "description": "Build knowledge for reentrancy vulnerabilities",
        },
        {
            "command": "/vuln-build --all",
            "description": "Build complete knowledge base for all categories",
        },
        {
            "command": "/vuln-build --validate",
            "description": "Build and validate quality of all documents",
        },
    ],
}


@dataclass
class VulnBuildArgs:
    """Arguments for the vuln-build skill."""

    category: Optional[str] = None
    all_categories: bool = False
    incremental: bool = False
    validate: bool = False
    dry_run: bool = False
    verbose: bool = False
    output_dir: str = "vulndocs"

    @classmethod
    def from_args(cls, args: List[str]) -> "VulnBuildArgs":
        """Parse arguments from command line.

        Args:
            args: Command line arguments

        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            prog="/vuln-build",
            description="Build vulnerability knowledge base",
        )
        parser.add_argument(
            "category",
            nargs="?",
            help="Category to build (e.g., reentrancy, oracle)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_categories",
            help="Build all categories",
        )
        parser.add_argument(
            "--incremental",
            action="store_true",
            help="Only process new/updated content",
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Run validation after build",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without making changes",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Verbose output",
        )
        parser.add_argument(
            "--output",
            "-o",
            dest="output_dir",
            default="vulndocs",
            help="Output directory for knowledge base",
        )

        parsed = parser.parse_args(args)

        return cls(
            category=parsed.category,
            all_categories=parsed.all_categories,
            incremental=parsed.incremental,
            validate=parsed.validate,
            dry_run=parsed.dry_run,
            verbose=parsed.verbose,
            output_dir=parsed.output_dir,
        )


@dataclass
class VulnBuildResult:
    """Result of running the vuln-build skill."""

    success: bool
    message: str
    pipeline_result: Optional[PipelineResult] = None
    documents_generated: int = 0
    categories_processed: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_output(self) -> str:
        """Generate human-readable output.

        Returns:
            Formatted output string
        """
        lines = []

        if self.success:
            lines.append(f"Successfully built knowledge base")
        else:
            lines.append(f"Build failed: {self.message}")
            return "\n".join(lines)

        lines.append(f"")
        lines.append(f"Documents: {self.documents_generated}")
        lines.append(f"Categories: {', '.join(self.categories_processed)}")
        lines.append(f"Duration: {self.duration_seconds:.1f}s")

        if self.pipeline_result:
            lines.append(f"")
            lines.append(f"Phase Results:")
            for phase in self.pipeline_result.phases:
                status = "" if phase.success else ""
                lines.append(
                    f"  {status} {phase.phase.value}: "
                    f"{phase.items_processed} items, {phase.duration_seconds:.1f}s"
                )
                if phase.items_failed > 0:
                    lines.append(f"      {phase.items_failed} failed")

        return "\n".join(lines)


class VulnBuildSkill:
    """Skill for building the vulnerability knowledge base.

    Orchestrates the multi-model pipeline to crawl, process, merge,
    and link vulnerability knowledge.
    """

    def __init__(self):
        """Initialize the skill."""
        self.name = "vuln-build"
        self.orchestrator: Optional[PipelineOrchestrator] = None

    async def execute(
        self,
        args: VulnBuildArgs,
        sources: Optional[Dict[str, List[CategorySource]]] = None,
    ) -> VulnBuildResult:
        """Execute the skill.

        Args:
            args: Parsed arguments
            sources: Optional pre-crawled sources

        Returns:
            Build result
        """
        start_time = datetime.utcnow()

        # Determine categories to process
        if args.category:
            categories = [args.category]
        elif args.all_categories:
            categories = get_all_categories()
        else:
            # Default to all if no category specified
            categories = get_all_categories()

        logger.info(f"Building knowledge for categories: {categories}")

        if args.dry_run:
            return VulnBuildResult(
                success=True,
                message=f"Dry run: Would build {len(categories)} categories",
                categories_processed=categories,
            )

        # Configure pipeline
        config = PipelineConfig(
            verbose=args.verbose,
            dry_run=args.dry_run,
        )

        # Create orchestrator
        self.orchestrator = PipelineOrchestrator(config)

        # Add progress logging
        def log_progress(phase: PipelinePhase, progress: TaskProgress):
            if args.verbose:
                logger.info(
                    f"{phase.value}: {progress.completed}/{progress.total} "
                    f"({progress.progress_pct:.1f}%)"
                )

        self.orchestrator.add_progress_callback(log_progress)

        # Run pipeline
        try:
            pipeline_result = await self.orchestrator.run(
                sources=sources,
                categories=categories,
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            if pipeline_result.success:
                # Save documents if not dry run
                if not args.dry_run:
                    await self._save_documents(
                        pipeline_result.documents,
                        args.output_dir,
                    )

                return VulnBuildResult(
                    success=True,
                    message="Knowledge base built successfully",
                    pipeline_result=pipeline_result,
                    documents_generated=len(pipeline_result.documents),
                    categories_processed=categories,
                    duration_seconds=duration,
                )
            else:
                return VulnBuildResult(
                    success=False,
                    message=pipeline_result.error or "Unknown error",
                    pipeline_result=pipeline_result,
                    categories_processed=categories,
                    duration_seconds=duration,
                )

        except Exception as e:
            logger.exception(f"Build failed: {e}")
            return VulnBuildResult(
                success=False,
                message=str(e),
                categories_processed=categories,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def _save_documents(
        self,
        documents: List[Any],
        output_dir: str,
    ) -> None:
        """Save documents to the knowledge store.

        Args:
            documents: Documents to save
            output_dir: Output directory
        """
        import json
        import os

        os.makedirs(output_dir, exist_ok=True)

        for doc in documents:
            # Create category directory
            cat_dir = os.path.join(output_dir, "categories", doc.category)
            os.makedirs(cat_dir, exist_ok=True)

            # Save document as JSON
            doc_path = os.path.join(cat_dir, f"{doc.subcategory}.json")
            with open(doc_path, "w") as f:
                json.dump(doc.to_dict(), f, indent=2)

            # Save markdown version
            md_path = os.path.join(cat_dir, f"{doc.subcategory}.md")
            with open(md_path, "w") as f:
                f.write(doc.to_markdown())

        logger.info(f"Saved {len(documents)} documents to {output_dir}")


# Singleton instance
vuln_build_skill = VulnBuildSkill()


async def run_vuln_build(args: List[str]) -> str:
    """Entry point for running the skill from Claude Code.

    Args:
        args: Command line arguments

    Returns:
        Output string
    """
    parsed_args = VulnBuildArgs.from_args(args)
    result = await vuln_build_skill.execute(parsed_args)
    return result.to_output()


# For direct execution
if __name__ == "__main__":
    import sys

    result = asyncio.run(run_vuln_build(sys.argv[1:]))
    print(result)
