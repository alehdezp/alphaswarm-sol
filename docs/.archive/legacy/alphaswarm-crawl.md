# AlphaSwarm Crawl Tool Documentation

**Location:** `scripts/alphaswarm_crawl.py`
**Purpose:** Complete crawl-filter-extract pipeline for Phase 17 vulnerability knowledge aggregation

---

## Overview

`alphaswarm_crawl.py` orchestrates the **complete 3-stage pipeline** for processing vulnerability knowledge sources:

```
URL → crawl4ai (discard images) → crawl-filter-worker (Haiku) → knowledge-aggregation-worker (Sonnet) → VulnDocs
```

### Pipeline Stages

| Stage | Tool | Model | Purpose |
|-------|------|-------|---------|
| 1. Crawl | crawl4ai Docker | N/A | Download web content, discard images |
| 2. Filter | crawl-filter-worker | Haiku 4.5 | Remove non-Solidity content, 50-80% token reduction |
| 3. Extract | knowledge-aggregation-worker | Sonnet 4.5 | Deep reasoning, extract vulnerabilities, integrate into VulnDocs |

---

## Installation

### Prerequisites

1. **Docker** (or OrbStack on macOS)
2. **Python 3.11+**
3. **AlphaSwarm.sol environment**

### Setup

```bash
# Make executable
chmod +x scripts/alphaswarm_crawl.py

# Verify Docker
docker ps

# If Docker not running (macOS):
open -a OrbStack
```

---

## Usage

### Single URL

```bash
# Basic usage
python scripts/alphaswarm_crawl.py <url> <source_id>

# Example
python scripts/alphaswarm_crawl.py https://rekt.news rekt-news
```

**Output:**
- Crawled JSON: `.vrs/crawl_cache/rekt-news_{timestamp}.json`
- Filtered markdown: `.vrs/filtered_cache/rekt-news_filtered.md`
- VulnDocs updates: `vulndocs/*/`

### Batch Processing

```bash
# Process multiple sources
python scripts/alphaswarm_crawl.py --batch sources_batch.json
```

**Batch File Format (`sources_batch.json`):**

```json
[
  {
    "url": "https://rekt.news",
    "source_id": "rekt-news"
  },
  {
    "url": "https://code4rena.com/reports",
    "source_id": "code4rena"
  },
  {
    "url": "https://solodit.xyz",
    "source_id": "solodit"
  }
]
```

### Options

```bash
# Non-parallel (sequential processing)
python scripts/alphaswarm_crawl.py https://rekt.news rekt-news --no-parallel

# Custom output directory
python scripts/alphaswarm_crawl.py https://rekt.news rekt-news --output-dir /custom/path

# Help
python scripts/alphaswarm_crawl.py --help
```

---

## Workflow Details

### Stage 1: Crawl (crawl4ai)

**What happens:**
1. Tool checks if Docker is running, starts if needed
2. Ensures `crawl4ai` container is running
3. Sends POST request to `http://localhost:11235/crawl`
4. Saves raw content to `.vrs/crawl_cache/{source_id}_{timestamp}.json`

**crawl4ai Options:**
- `discard_images: true` - Don't download images (Solidity focus)
- `screenshot: false` - No screenshots
- `remove_images: true` - Strip image tags from markdown

### Stage 2: Filter (crawl-filter-worker, Haiku)

**What happens:**
1. Tool spawns `crawl-filter-worker` subagent (Haiku 4.5)
2. Subagent reads crawled JSON
3. Removes non-Solidity content:
   - Non-security topics
   - Images and media
   - Irrelevant marketing content
   - Other programming languages
4. Outputs clean markdown to `.vrs/filtered_cache/{source_id}_filtered.md`

**Token Reduction:** 50-80% (conservative filtering)

**Runs in Parallel:** Multiple filter agents can run simultaneously

### Stage 3: Extract (knowledge-aggregation-worker, Sonnet)

**What happens:**
1. Tool spawns `knowledge-aggregation-worker` subagent (Sonnet 4.5)
2. Subagent reads filtered markdown
3. Extracts vulnerabilities using 7-component framework:
   - Identification signals
   - Remediation signals
   - Check patterns
   - Pattern signals
   - Code examples (semantic only)
   - Similar scenarios
   - Real-world exploits
4. Makes decisions: ACCEPT/MERGE/REJECT/CREATE_*
5. Integrates into VulnDocs structure
6. Generates BSKG patterns

**Output:**
- VulnDocs: `vulndocs/*/`
- Patterns: `patterns/*/`
- Discovery log: `.vrs/discovery/subagent_*_log.yaml`

---

## Parallel Processing

By default, the tool processes sources in parallel:

```
URL 1 → crawl4ai ─┐
URL 2 → crawl4ai ─┼─► [Filter Queue] ─► [Knowledge Queue] ─► VulnDocs
URL 3 → crawl4ai ─┘
```

**Parallelization Strategy:**
- **Crawl:** Sequential (limited by crawl4ai container)
- **Filter:** Up to 4 parallel Haiku subagents
- **Extract:** Up to 4 parallel Sonnet subagents

**Disable Parallel:**
```bash
python scripts/alphaswarm_crawl.py <url> <source_id> --no-parallel
```

---

## File Locations

| Type | Location | Purpose |
|------|----------|---------|
| Crawled JSON | `.vrs/crawl_cache/` | Raw crawl4ai output |
| Filtered MD | `.vrs/filtered_cache/` | Cleaned Solidity-focused content |
| VulnDocs | `vulndocs/` | Integrated vulnerability knowledge |
| Patterns | `patterns/` | Generated BSKG detection patterns |
| Discovery Logs | `.vrs/discovery/subagent_*_log.yaml` | Processing logs |

---

## Error Handling

### Docker Not Running

```
ERROR: Docker is not available. Please start Docker manually.
```

**Fix:** Start Docker Desktop or OrbStack

### crawl4ai Container Failed

```
ERROR: crawl4ai container failed to start
```

**Fix:**
```bash
docker rm crawl4ai
docker pull unclecode/crawl4ai:latest
```

### Crawl Failed

```
✗ Crawl failed: [errors]
```

**Common causes:**
- URL inaccessible
- Network issues
- crawl4ai API error

**Fix:** Retry or check URL manually

---

## Examples

### Example 1: Crawl Rekt News

```bash
$ python scripts/alphaswarm_crawl.py https://rekt.news rekt-news

✓ Docker is running
✓ crawl4ai container is running

[1/3] Crawling https://rekt.news (source: rekt-news)...
  ✓ Crawled 1 pages
  ✓ 2847 tokens
  ✓ Saved to .vrs/crawl_cache/rekt-news_2026-01-09T21-00-00.123456.json

[2/3] Filtering rekt-news_2026-01-09T21-00-00.123456.json...
  → Spawning crawl-filter-worker (Haiku) subagent...
  → Input: .vrs/crawl_cache/rekt-news_2026-01-09T21-00-00.123456.json
  → Output: .vrs/filtered_cache/rekt-news_filtered.md

[3/3] Extracting knowledge from rekt-news_filtered.md...
  → Spawning knowledge-aggregation-worker (Sonnet) subagent...
  → Input: .vrs/filtered_cache/rekt-news_filtered.md
  → Output: VulnDocs + patterns

✓ Pipeline complete
```

### Example 2: Batch Processing

```bash
$ cat sources_batch.json
[
  {"url": "https://rekt.news", "source_id": "rekt"},
  {"url": "https://solodit.xyz", "source_id": "solodit"},
  {"url": "https://code4rena.com", "source_id": "code4rena"}
]

$ python scripts/alphaswarm_crawl.py --batch sources_batch.json

Processing batch of 3 URLs...

=== Source 1/3: rekt ===
[Processing...]

=== Source 2/3: solodit ===
[Processing...]

=== Source 3/3: code4rena ===
[Processing...]

✓ Batch complete: 3 sources processed
```

---

## Integration with Phase 17

### Task 17.3a-j: World Knowledge Crawl

Use `alphaswarm_crawl.py` for all 87 sources:

```bash
# Create batch file with all 87 sources
python scripts/alphaswarm_crawl.py --batch .vrs/vulndocs_reference/sources_batch.json
```

### Monitoring Progress

```bash
# Check subagent status
bash scripts/monitor_subagents.sh

# Check discovery logs
ls -l .vrs/discovery/subagent_*_log.yaml

# Check VulnDocs updates
git status knowledge/vulndocs/
```

---

## Advanced Usage

### Custom Pipeline

The tool can be imported and used programmatically:

```python
from scripts.alphaswarm_crawl import AlphaSwarmCrawler

crawler = AlphaSwarmCrawler(output_dir=".vrs")
crawler.ensure_docker()
crawler.ensure_crawl4ai_container()

# Process single URL
result = crawler.process_url(
    url="https://rekt.news",
    source_id="rekt",
    parallel=True
)

# Process batch
results = crawler.process_batch(
    batch_file=Path("sources.json"),
    parallel=True
)
```

---

## Troubleshooting

### No Output Files

**Symptom:** Pipeline completes but no files created

**Check:**
1. Permissions on `.vrs/` directory
2. Disk space
3. Subagent logs for errors

### High Token Usage

**Symptom:** Filter stage doesn't reduce tokens much

**Cause:** Content is mostly Solidity-relevant

**Solution:** Expected behavior, filter targets 50-80% reduction

### Subagent Timeout

**Symptom:** Subagent stops responding

**Solution:** Check subagent output file, may need to restart

---

*AlphaSwarm Crawl Tool Documentation v1.0 | Phase 17 | 2026-01-09*
