---
phase: 01-vulndocs-completion
plan: 07
subsystem: vulndocs-automation
tags: [automation, exa, solodit, discovery, github-actions]

dependency-graph:
  requires:
    - 01-05  # Consolidation complete
  provides:
    - solodit-fetcher
    - exa-scanner
    - review-queue-workflow
    - github-actions-automation
  affects:
    - ongoing-vulndocs-maintenance
    - knowledge-freshness

tech-stack:
  added:
    - httpx (async HTTP for Exa API)
  patterns:
    - queue-based-review
    - human-in-the-loop
    - scheduled-automation

key-files:
  created:
    - src/true_vkg/vulndocs/scrapers/__init__.py
    - src/true_vkg/vulndocs/scrapers/solodit_fetcher.py
    - src/true_vkg/vulndocs/automation/__init__.py
    - src/true_vkg/vulndocs/automation/exa_scanner.py
    - src/true_vkg/cli/vulndocs.py
    - .github/workflows/exa-scan.yaml
    - .true_vkg/automation/config.yaml
    - .true_vkg/vulndocs_reference/exa_queries.yaml (updated)
  modified:
    - src/true_vkg/cli/main.py

decisions:
  - id: no-auto-integrate
    date: 2026-01-20
    choice: "All discoveries require human review before VulnDocs integration"
    rationale: "Maintain quality and prevent knowledge base pollution"

  - id: queue-based-workflow
    date: 2026-01-20
    choice: "Use YAML queue files for pending/processed tracking"
    rationale: "Human-readable, versionable, simple tooling"

  - id: exa-queries-v2
    date: 2026-01-20
    choice: "Update exa_queries.yaml to schema v2.0 with 50+ queries"
    rationale: "Comprehensive coverage of emerging vulnerability categories"

  - id: github-actions-weekly
    date: 2026-01-20
    choice: "Weekly Exa scans via GitHub Actions (Mondays 9 AM UTC)"
    rationale: "Automated discovery without manual intervention"

metrics:
  duration: 25 minutes
  completed: 2026-01-20
---

# Phase 01 Plan 07: Continuous Knowledge Discovery Automation Summary

**One-liner:** Implemented Solodit fetcher, Exa scanner, and weekly GitHub Action for continuous vulnerability knowledge discovery with queue-based human review.

## What Was Done

### Task 1: Implement continuous Solodit fetcher

- Created `SoloditFetcher` class with crawl4ai integration
- Implemented finding extraction and BSKG operation suggestion
- Built queue-based review workflow (YAML storage)
- Added CLI commands for manual operation

**Key Features:**
- State tracking (last fetch, processed IDs)
- Severity normalization
- BSKG category and operation suggestions
- Duplicate prevention

**Commit:** `177f5b3` - feat(01-07): implement Solodit fetcher for continuous knowledge discovery

### Task 2: Implement Exa scanner for emerging vulnerabilities

- Created `ExaScanner` class with async httpx integration
- Loaded queries from exa_queries.yaml (50+ queries)
- Implemented relevance scoring and deduplication
- Added category filtering support

**Query Coverage:**
| Category | Queries |
|----------|---------|
| Account Abstraction | 4 |
| Restaking | 4 |
| ZK Rollup | 4 |
| Cross-Chain | 4 |
| Intent/MEV | 4 |
| Vault/Token | 4 |
| Reentrancy | 4 |
| Oracle | 4 |
| Governance | 2 |
| Protocol-Specific | 4 |
| Emerging | 4 |
| Source Discovery | 4 |
| Code Patterns | 6 |

**Commit:** `1955268` - feat(01-07): implement Exa scanner for emerging vulnerability discovery

### Task 3: Configure weekly automation and integration

- Created `.github/workflows/exa-scan.yaml` for weekly scans
- Supports manual trigger with customizable inputs
- Creates GitHub issue when discoveries found
- Added automation config at `.true_vkg/automation/config.yaml`

**GitHub Action Features:**
- Scheduled: Every Monday at 9 AM UTC
- Manual dispatch with days_back and category inputs
- Auto-creates issues for review notification
- Commits queue updates (when not gitignored)

**Commit:** `f9d451c` - feat(01-07): configure weekly Exa scan automation via GitHub Actions

## CLI Commands Added

| Command | Description |
|---------|-------------|
| `vulndocs fetch-solodit` | Fetch new findings from Solodit |
| `vulndocs scan-exa` | Scan Exa for emerging vulnerabilities |
| `vulndocs review-queue` | Review pending discoveries |
| `vulndocs queue-status` | Show discovery queue status |

**Usage Examples:**
```bash
# Fetch Solodit findings from last 2 weeks
uv run alphaswarm vulndocs fetch-solodit --since 2w

# Scan Exa with category filter
uv run alphaswarm vulndocs scan-exa --category reentrancy --verbose

# Interactive review
uv run alphaswarm vulndocs review-queue --interactive

# Check queue status
uv run alphaswarm vulndocs queue-status
```

## Queue Structure

**Solodit Queue (`solodit_queue.yaml`):**
```yaml
queue_type: "solodit"
schema_version: "1.0"
pending_review:
  - id: "solodit-abc123"
    title: "Reentrancy in withdraw"
    severity: "HIGH"
    suggested_category: "reentrancy/classic"
    suggested_operations: [CALLS_EXTERNAL, WRITES_USER_BALANCE]
processed:
  - id: "solodit-xyz789"
    action: ACCEPT
    target: "reentrancy/classic"
```

**Exa Queue (`exa_queue.yaml`):**
```yaml
queue_type: "exa"
pending_review:
  - url: "https://..."
    title: "Novel DeFi Attack"
    relevance_score: 0.92
    query_matched: "emerging-novel"
    suggested_category: "emerging"
```

## Review Workflow

```
Discovery Sources           Review Queue              VulnDocs
    │                           │                        │
    ├── Solodit ──────────────► pending_review          │
    │                           │                        │
    ├── Exa ──────────────────► pending_review          │
    │                           │                        │
    │                   Human Review                     │
    │                           │                        │
    │                     ┌─────┴─────┐                 │
    │                     │           │                 │
    │                 ACCEPT/MERGE  REJECT              │
    │                     │                             │
    │                     └─────────────────────────────► Integration
```

## Verification Results

| Check | Status |
|-------|--------|
| Solodit import | PASS |
| Exa import | PASS |
| CLI commands registered | PASS |
| queue-status works | PASS |
| fetch-solodit --help | PASS |
| scan-exa --help | PASS |
| GitHub workflow valid | PASS |

## Environment Setup Required

**For Exa scanning:**
```bash
export EXA_API_KEY="your-key-from-exa.ai"
```

**For Solodit fetching:**
```bash
pip install crawl4ai  # Optional, required for web scraping
```

**GitHub Secrets (for automation):**
- `EXA_API_KEY`: Exa API key for weekly scans

## Deviations from Plan

**None** - Plan executed exactly as written.

## Next Phase Readiness

**Phase 1 Complete:**
- Plans 01-07 all executed
- VulnDocs knowledge base established (87 sources)
- Continuous discovery automation in place
- All discoveries require human review

**Ready for:**
- Phase 2: Builder Foundation & Modularization
- Ongoing knowledge maintenance via automation
