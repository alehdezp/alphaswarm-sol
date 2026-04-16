# Phase 18 Lite: VulnDocs Knowledge Mining & Retrieval System

**Status:** COMPLETE (core) - optional task pending
**Priority:** CRITICAL - Foundation for world-class vulnerability detection
**Last Updated:** 2026-01-08

### Recent Progress (Carried Over)
- ✅ Core schemas + orchestrators implemented
- ✅ KnowledgeStore + IndexBuilder implemented
- ✅ KnowledgeRetriever API implemented
- ✅ LLM tool interface implemented

---

## Executive Summary (Lite)

Phase 18 Lite targets the same end goal (the most complete and updated Solidity vulnerability knowledge system) but removes unnecessary complexity. The system uses **one crawler (Crawl4AI)** to **download sources locally first**, then runs a **non-blind review gate** powered by Claude Code subagents (**claude-haiku-4-5** + skills) spawned in parallel per subcategory. Each subagent processes **one document at a time** for its subcategory, extracts only relevant sections, and integrates **novel, valuable, and actionable** knowledge. Retrieval focuses on **minimal context** needed to test vulnerabilities one by one.

---

## 1. OBJECTIVES (Lite)

### 1.1 Primary Objective

Build the **most comprehensive, granular, and intelligently-organized vulnerability knowledge database** in the smart contract security space, capable of:

1. **High-Value Coverage First**: Crawl authoritative sources before long-tail
2. **Granular Organization**: Split into fine-grained, retrievable units
3. **Minimal-Context Retrieval**: Fetch only what is needed to test one vuln at a time
4. **Continuous Growth**: New sources integrated on a schedule
5. **Non-Blind Integration**: Subagents validate content value and only emit subcategory/specific-vuln outputs

### 1.2 Non-Blind Extraction Requirement (Critical)

This is **not** a blind scrape. Every chunk must pass a subagent gate:
- **Novelty**: Adds new facts or nuance
- **Value**: Improves detection/testing/business context
- **Relevance**: Solidity vulnerability focus
- **Actionability**: Helps an LLM test for a vuln
- **Scope**: Subagents only build subcategories and specific vulnerabilities
- **Agnosticism**: Ignore variable names; focus on behavior and conditions

---

## 2. ARCHITECTURE OVERVIEW (Lite)

### 2.1 System Architecture

```
Source URL
    │
    ▼
[Crawl4AI Universal Crawler]
    │
    ▼
[Local Docs Snapshot (per-source markdown)]
    │
    ▼
[Parser + Chunker]
    │
    ▼
[Subagent Review Gate (Haiku 4.5 + skills, parallel per subcategory, per-doc)]
    │
    ├── ACCEPT → Dedup → Merge → Store → Index
    └── REJECT → Drop or log
    │
    ▼
[Knowledge Store + Retrieval API]
```

### 2.2 Design Constraints

- **One crawler stack**: Crawl4AI for websites + GitHub + feeds/APIs
- **No blind integration**: Claude Code subagents must approve any chunk
- **Subagent model pinned**: claude-haiku-4-5 for review/build tasks
- **Parallel subcategory pool**: spawn subagents per subcategory in parallel
- **Scope-limited outputs**: only subcategory and specific-vuln content
- **Per-doc pass**: subagents process one document/report at a time
- **Variable-name agnostic**: detect behaviors, not identifier names
- **Minimal retrieval**: 300-800 token chunks by section type
- **Optional semantic search**: Add only after corpus size demands it

---

## 3. KNOWLEDGE ORGANIZATION DESIGN (Lite)

### 3.1 Granularity Hierarchy

```
LEVEL 0: ROOT INDEX (~200 tokens)
├── Category list + navigation

LEVEL 1: CATEGORY (~1,200 tokens)
├── Overview + common attack vectors
├── Subcategory list

LEVEL 2: SUBCATEGORY (~400-700 tokens)
├── Variant summary + key distinguishing traits
├── Links to sections

LEVEL 3: SECTIONS (~300-800 tokens each)
├── detection.md   - How to identify
├── testing.md     - How to verify
├── business.md    - Impact and user trust
├── exploits.md    - Real incidents
├── patterns.md    - Vulnerable vs safe code
└── fixes.md       - Remediation and checks
```

### 3.2 Retrieval Goal

Given a single vulnerability hypothesis, return:
- **Detection** and **testing** sections first
- **Business** + **exploits** if the token budget allows
- Total context < 3,000 tokens by default

### 3.3 Specific Vulnerability Report (SVR) Fields

SVRs are **pattern-like but broader**. They must capture detection logic, testing guidance, and business impact in a way that is **variable-name agnostic**. Required fields:

- `id` (kebab-case), `name`, `category`, `subcategory`, `severity`, `confidence`
- `description` (behavioral summary, not identifier-based)
- `scope` (function/contract/system) and `prerequisites`
- `detection_signals` (graph properties, semantic ops, conditions)
- `false_positive_guards` (what should NOT trigger)
- `testing_guidance` (unit tests, fuzzing, invariants)
- `exploit_narrative` (attack steps + conditions)
- `business_impact` (monetary loss, user trust, governance risk)
- `remediation` (fix patterns + validation checks)
- `code_patterns` (bad vs safe examples)
- `variants` / `aliases`
- `references` (URLs) + `last_updated`

**Authorization and business-logic SVRs must include**: permission model, trust boundaries, invariants, and abuse-case checklist. These are open-ended and require explicit test guidance.

---

## 4. SOURCE MINING INFRASTRUCTURE (Lite)

### 4.1 Source Policy

- **Crawl4AI-only** ingestion
- Respect robots + rate limits
- Track source authority and update cadence
- All content must be traceable to a URL

### 4.2 Seed Source Registry (High-Value)

**Taxonomy / Standards / Field Guides**
- SWC Registry (swcregistry.io + GitHub)
- EthTrust Security Levels (entethalliance.org)
- Smart Contract Security Verification Standard (github.com/ComposableSecurity/SCSVS)
- Smart Contract Security Field Guide (scsfg.io)
- Ethereum Smart Contract Best Practices (consensys.github.io)
- DASP Top 10 (dasp.co)

**Audit Findings / Contests**
- Solodit (solodit.xyz)
- Code4rena reports (code4rena.com/reports)
- Sherlock reports (sherlock.xyz)

**Incident & Postmortem**
- Immunefi disclosures (immunefi.com)
- Rekt News (rekt.news)

**Vendor Advisories / Docs**
- OpenZeppelin advisories (blog.openzeppelin.com)
- Solidity docs (docs.soliditylang.org)

---

## 5. CONTENT PROCESSING PIPELINE (Lite)

### 5.1 Local Download + Snapshot

1. Crawl4AI fetches each source and stores a **local markdown snapshot** per URL.
2. Snapshots are immutable inputs for subagents (auditability + reproducibility).
3. Subagents iterate **all downloaded docs** for their subcategory, **one document at a time**, in full.

### 5.2 Subagent Review Gate (Haiku 4.5 + skills)

Each chunk is reviewed by a Claude Code subagent (model: **claude-haiku-4-5**) and routed to a **parallel subcategory worker pool**. Each subagent is scoped to **one subcategory** and produces **only subcategory/specific-vuln outputs**, processing documents **one by one**.
Subagent definition: `.claude/agents/vkg-vulndocs-subcategory-worker.md`.

**Inputs**
- Raw chunk text + source metadata
- Existing category/subcategory candidates
- Similar chunks (hash or simhash near-dup)

**Decision**
- `ACCEPT` if novel + valuable
- `MERGE` if overlapping but adds meaningful detail
- `REJECT` if redundant or low-value

**Output (required)**
```
status: ACCEPT | MERGE | REJECT
novelty: high | medium | low
value: high | medium | low
rationale: short text
subcategory: <name>
vulnerability: <specific vuln or variant>
section: detection | testing | business | exploits | patterns | fixes
missing_fields: [field1, field2]
tags: [category, subcategory, section]
```

### 5.3 SVR Field Sync Phase

Before merge, run a **field completeness sync** against the SVR schema (Section 3.3). Missing fields are queued for later enrichment or flagged for targeted re-crawl. This is critical for authorization and business-logic bugs.

### 5.4 Minimal Extract → Verify → Integrate Loop

1. Crawl → Local Snapshot
2. Parse → Chunk
3. Subagent gate (claude-haiku-4-5, parallel per subcategory, per-doc)
4. SVR field sync (schema completeness)
5. Dedup (hash + optional simhash)
6. Merge + store + index

---

## 6. RETRIEVAL SYSTEM DESIGN (Lite)

- Prefer **exact section retrieval** by category/subcategory
- Fallback to BM25/FTS if no direct match
- Return **minimal context** sufficient to test the vuln
- Keep a strict token budget (default 2,000-3,000)

---

## 7. INTELLIGENT MERGE SYSTEM (Lite)

- Hash-based dedup first
- Merge when new content adds:
  - new exploit example
  - new test technique
  - improved remediation guidance
- Preserve all source attributions

---

## 8. TASK BREAKDOWN (Lite)

### 8.1 Task Registry

| ID | Task | Est. | Priority | Depends | Status | Description |
|----|------|------|----------|---------|--------|-------------|
| 18.0 | Project Infrastructure | 4h | MUST | - | ✅ DONE | Directory structure, deps |
| 18.1 | Source Registry + Policies | 8h | MUST | 18.0 | ✅ DONE | 26 sources defined (registry.py) |
| 18.2 | Crawl4AI Docker Setup | 6h | MUST | 18.0 | ✅ DONE | Crawler supports Docker mode |
| 18.3 | Local Download + Snapshot | 12h | MUST | 18.2 | ✅ DONE | crawler.py with local snapshot |
| 18.4 | Parsing + Chunking | 8h | MUST | 18.3 | ✅ DONE | merger.py with section extraction |
| 18.5 | Subagent Per-Doc Review Gate | 10h | MUST | 18.4 | ✅ DONE | subcategory_worker.py with extraction |
| 18.6 | SVR Field Sync | 6h | MUST | 18.5 | ✅ DONE | completeness.py validator |
| 18.7 | Dedup + Merge | 10h | MUST | 18.6 | ✅ DONE | Hash + merge logic (merger.py) |
| 18.8 | Knowledge Store + Index | 8h | MUST | 18.7 | ✅ DONE | File storage + indexes |
| 18.9 | Retrieval API | 8h | MUST | 18.8 | ✅ DONE | Navigator API |
| 18.10 | Initial Population | 12h | NICE | 18.9 | OPTIONAL | Seed sources ingestion |
| 18.11 | Quality Validation | 6h | MUST | 18.10 | ✅ DONE | quality.py scorer |

**Total Estimated Hours: 98h**

---

## 9. TESTING STRATEGY (Lite)

| Category | Count | Coverage | Location |
|----------|-------|----------|----------|
| Unit Tests | 40+ | 80%+ | `tests/test_vulndocs_*.py` |
| Integration Tests | 12+ | - | `tests/integration/test_vulndocs_*.py` |
| Retrieval Tests | 10+ | - | `tests/test_vulndocs_retrieval.py` |

---

## 10. SUCCESS METRICS (Lite)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Sources Crawled | 12+ | Count in registry |
| Categories Covered | 6/11 | Populated categories |
| Subcategories | 20+ | Count across categories |
| Total Documents | 120+ | File count |
| Total Tokens | 60K+ | Token estimates |

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Retrieval Accuracy | 90%+ | Test suite |
| Dedup Effectiveness | 97%+ | No duplicates in review |
| Content Quality | 4.3/5 | Human evaluation |
| SVR Field Completeness | 90%+ | Schema check |
| Source Attribution | 100% | Traceable facts |

---

## 11. RISK MITIGATION (Lite)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Crawl4AI downtime | Low | High | Fallback to requests + BeautifulSoup |
| Low-quality sources | Medium | Medium | Authority scoring + subagent gate |
| Duplicate content | Medium | Low | Hash dedup + merge rules |
| Misclassification | Medium | Medium | Subagent review + manual spot checks |

---

## 12. EXIT CRITERIA (Lite)

- [ ] All 11 tasks completed
- [ ] 12+ sources successfully crawled
- [ ] 6 categories populated
- [ ] 20+ subcategories with content
- [ ] Navigator API operational
- [ ] Subagent review gate operational (parallel subcategory pool, claude-haiku-4-5)
- [ ] SVR field sync operational
- [ ] 60+ tests passing

---

## APPENDIX A: File Locations

| Component | Location |
|-----------|----------|
| Source Registry | `src/true_vkg/vulndocs/sources/registry.py` |
| Crawlers | `src/true_vkg/vulndocs/scraping/` |
| Processors | `src/true_vkg/vulndocs/processing/` |
| Navigator | `src/true_vkg/vulndocs/navigator.py` |
| Knowledge Store | `knowledge/vulndocs/` |
| Tests | `tests/test_vulndocs_*.py` |
| Docker | `docker/vulndocs/` |

## APPENDIX B: Dependencies (Lite)

```toml
[project.optional-dependencies]
vulndocs = [
    "crawl4ai>=0.3.0",
    "aiohttp>=3.8.0",
    "beautifulsoup4>=4.12.0",
    "sentence-transformers>=2.2.0",  # Optional semantic search
    "faiss-cpu>=1.7.0",              # Optional vector index
    "feedparser>=6.0.0",             # RSS feeds
]
```

*Phase 18 Lite Tracker | Version 1.0 | 2026-01-08*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P18.P.1 | Define mining to pattern candidate pipeline | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-18/TRACKER.md` | P17.P.1 | Pipeline spec | Phase 2/14 use candidates | No duplicate patterns | New mining source |
| P18.P.2 | Add provenance + quality scoring for mined knowledge | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-18/TRACKER.md` | P17.P.1 | Schema notes | Phase 14 uses quality weight | Evidence packet versioned | Conflicting source |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P18.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P18.R.2 | Task necessity review for P18.P.* | `task/4.0/phases/phase-18/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P18.P.1-P18.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with pattern packs | Redundant task discovered |
| P18.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P18.P.1-P18.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P18.R.4 | Ensure mining outputs do not duplicate existing patterns | `patterns/`, `task/4.0/phases/phase-18/TRACKER.md` | P18.P.1 | Duplicate check note | No duplicate pattern IDs | Pattern duplication | Duplicate detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** Conflicting sources found.
**Spawn:** Add debate or human review task.
**Example spawned task:** P18.P.3 Add human review for conflicting mined sources.
