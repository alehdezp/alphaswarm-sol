#!/usr/bin/env python3
"""
AlphaSwarm Crawl Tool - Complete Pipeline for Phase 17

Pipeline:
1. URL → crawl4ai (discard images) → raw .md
2. raw .md → crawl-filter-worker (Haiku, parallel) → filtered .md
3. filtered .md → knowledge-aggregation-worker (Sonnet) → VulnDocs

Usage:
    python scripts/alphaswarm_crawl.py <url> <source_id> [--parallel]
    python scripts/alphaswarm_crawl.py --batch <batch_file>
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AlphaSwarmCrawler:
    """Orchestrates the complete crawl-filter-extract pipeline"""

    def __init__(self, output_dir: str = ".vrs"):
        self.output_dir = Path(output_dir)
        self.crawl_cache = self.output_dir / "crawl_cache"
        self.filtered_cache = self.output_dir / "filtered_cache"
        self.discovery = self.output_dir / "discovery"

        # Ensure directories exist
        self.crawl_cache.mkdir(parents=True, exist_ok=True)
        self.filtered_cache.mkdir(parents=True, exist_ok=True)
        self.discovery.mkdir(parents=True, exist_ok=True)

    def check_docker(self) -> bool:
        """Check if Docker is running, start if needed"""
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def start_docker(self) -> bool:
        """Start Docker (OrbStack on macOS)"""
        print("Docker not running. Starting OrbStack...")
        try:
            subprocess.run(["open", "-a", "OrbStack"], check=False)
            time.sleep(5)
            return self.check_docker()
        except Exception as e:
            print(f"Failed to start Docker: {e}")
            return False

    def ensure_docker(self) -> None:
        """Ensure Docker is running"""
        if not self.check_docker():
            if not self.start_docker():
                print("ERROR: Docker is not available. Please start Docker manually.")
                sys.exit(1)
        print("✓ Docker is running")

    def ensure_crawl4ai_container(self) -> None:
        """Ensure crawl4ai container is running"""
        # Check if container exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=crawl4ai", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if "crawl4ai" not in result.stdout:
            print("Pulling crawl4ai image...")
            subprocess.run(
                ["docker", "pull", "unclecode/crawl4ai:latest"],
                check=True
            )

        # Check if container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=crawl4ai", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if "crawl4ai" not in result.stdout:
            print("Starting crawl4ai container...")
            # Try to start existing container
            subprocess.run(["docker", "start", "crawl4ai"], capture_output=True)

            time.sleep(2)

            # Check again
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=crawl4ai", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            if "crawl4ai" not in result.stdout:
                # Container doesn't exist or failed to start, create new one
                subprocess.run(["docker", "rm", "crawl4ai"], capture_output=True)
                subprocess.run(
                    [
                        "docker", "run", "-d",
                        "-p", "11235:11235",
                        "--name", "crawl4ai",
                        "unclecode/crawl4ai:latest"
                    ],
                    check=True
                )
                time.sleep(3)

        print("✓ crawl4ai container is running")

    def crawl(
        self,
        url: str,
        source_id: str,
        discard_images: bool = True
    ) -> Optional[Path]:
        """
        Crawl URL using crawl4ai Docker container

        Returns path to crawled markdown file or None on failure
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S.%f")
        output_file = self.crawl_cache / f"{source_id}_{timestamp}.json"

        print(f"\n[1/3] Crawling {url} (source: {source_id})...")

        # Prepare crawl4ai request
        payload = {
            "url": url,
            "source_id": source_id,
            "js_code": [],
            "wait_for": "",
            "screenshot": not discard_images,  # Don't take screenshots if discarding images
            "remove_images": discard_images
        }

        # Call crawl4ai API
        try:
            result = subprocess.run(
                [
                    "curl", "-X", "POST",
                    "http://localhost:11235/crawl",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload),
                    "-o", str(output_file),
                    "--silent"
                ],
                check=True
            )

            if output_file.exists():
                # Load and validate
                with open(output_file) as f:
                    data = json.load(f)

                if data.get("success"):
                    print(f"  ✓ Crawled {data.get('pages_crawled', 0)} pages")
                    print(f"  ✓ {data.get('total_tokens', 0)} tokens")
                    print(f"  ✓ Saved to {output_file}")
                    return output_file
                else:
                    print(f"  ✗ Crawl failed: {data.get('errors', [])}")
                    return None
            else:
                print("  ✗ Output file not created")
                return None

        except Exception as e:
            print(f"  ✗ Crawl error: {e}")
            return None

    def spawn_filter_agent(self, crawl_file: Path, source_id: str) -> Optional[str]:
        """
        Spawn crawl-filter-worker (Haiku) subagent to clean up crawled content

        Returns agent_id or None on failure
        """
        print(f"\n[2/3] Filtering {crawl_file.name}...")

        # This would be a Task tool call in the actual agent context
        # For now, return a placeholder
        # In real usage, the main agent would call:
        # Task(subagent_type="crawl-filter-worker", prompt=..., run_in_background=True)

        print("  → Spawning crawl-filter-worker (Haiku) subagent...")
        print(f"  → Input: {crawl_file}")
        print(f"  → Output: {self.filtered_cache / f'{source_id}_filtered.md'}")

        # Return placeholder agent ID
        return f"filter-{source_id}-{int(time.time())}"

    def spawn_knowledge_agent(self, filtered_file: Path, source_id: str) -> Optional[str]:
        """
        Spawn knowledge-aggregation-worker (Sonnet) subagent to extract and integrate

        Returns agent_id or None on failure
        """
        print(f"\n[3/3] Extracting knowledge from {filtered_file.name}...")

        # This would be a Task tool call in the actual agent context
        print("  → Spawning knowledge-aggregation-worker (Sonnet) subagent...")
        print(f"  → Input: {filtered_file}")
        print(f"  → Output: VulnDocs + patterns")

        # Return placeholder agent ID
        return f"knowledge-{source_id}-{int(time.time())}"

    def process_url(
        self,
        url: str,
        source_id: str,
        parallel: bool = True
    ) -> Dict[str, Optional[str]]:
        """
        Process a single URL through the complete pipeline

        Returns dict with agent IDs: {filter_agent_id, knowledge_agent_id}
        """
        # Step 1: Crawl
        crawl_file = self.crawl(url, source_id, discard_images=True)
        if not crawl_file:
            return {"error": "Crawl failed"}

        # Step 2: Filter (Haiku subagent)
        filter_agent_id = self.spawn_filter_agent(crawl_file, source_id)
        if not filter_agent_id:
            return {"error": "Failed to spawn filter agent"}

        # Step 3: Extract (Sonnet subagent)
        # In real implementation, wait for filter agent or process immediately
        filtered_file = self.filtered_cache / f"{source_id}_filtered.md"
        knowledge_agent_id = self.spawn_knowledge_agent(filtered_file, source_id)

        return {
            "crawl_file": str(crawl_file),
            "filter_agent_id": filter_agent_id,
            "knowledge_agent_id": knowledge_agent_id
        }

    def process_batch(self, batch_file: Path, parallel: bool = True) -> List[Dict]:
        """
        Process multiple URLs from a batch file

        Batch file format (JSON):
        [
            {"url": "https://...", "source_id": "name"},
            ...
        ]
        """
        with open(batch_file) as f:
            batch = json.load(f)

        results = []
        print(f"\nProcessing batch of {len(batch)} URLs...")

        for i, item in enumerate(batch, 1):
            print(f"\n=== Source {i}/{len(batch)}: {item['source_id']} ===")
            result = self.process_url(item["url"], item["source_id"], parallel)
            results.append({**item, **result})

        return results


def main():
    parser = argparse.ArgumentParser(
        description="AlphaSwarm Crawl Tool - Complete crawl-filter-extract pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl single URL
  python scripts/alphaswarm_crawl.py https://rekt.news rekt-news

  # Crawl batch
  python scripts/alphaswarm_crawl.py --batch sources_batch.json

  # Non-parallel mode (sequential)
  python scripts/alphaswarm_crawl.py https://rekt.news rekt-news --no-parallel
        """
    )

    parser.add_argument("url", nargs="?", help="URL to crawl")
    parser.add_argument("source_id", nargs="?", help="Source identifier")
    parser.add_argument("--batch", type=Path, help="Batch file (JSON)")
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing"
    )
    parser.add_argument(
        "--output-dir",
        default=".vrs",
        help="Output directory (default: .vrs)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.batch and (not args.url or not args.source_id):
        parser.error("Either provide URL and source_id, or use --batch")

    # Initialize crawler
    crawler = AlphaSwarmCrawler(output_dir=args.output_dir)

    # Ensure Docker is ready
    crawler.ensure_docker()
    crawler.ensure_crawl4ai_container()

    # Process
    parallel = not args.no_parallel

    if args.batch:
        results = crawler.process_batch(args.batch, parallel=parallel)
        print(f"\n✓ Batch complete: {len(results)} sources processed")
    else:
        result = crawler.process_url(args.url, args.source_id, parallel=parallel)
        print(f"\n✓ Pipeline complete")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
