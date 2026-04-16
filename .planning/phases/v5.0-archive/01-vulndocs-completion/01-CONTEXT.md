# Phase 1: VulnDocs Completion - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the most condensed, LLM-optimized vulnerability knowledge database from 87 sources using parallel subagent extraction, semantic consolidation, and pattern-focused documentation. This phase completes the VulnDocs infrastructure with world knowledge aggregation.

**NOT in scope:** Pattern testing infrastructure, builder improvements, orchestration — those are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Crawling & Extraction

- Use crawl4ai Docker for all web extraction
- **Crawl depth:** Claude's discretion — follow Solidity-related links when source quality warrants
- **Duplicate sources:** Merge best details from all sources describing same vulnerability
- **Non-English sources:** Translate and extract using LLM
- **Version scope:** Skip vulnerabilities that only affect Solidity < 0.8
- **Audit sources:** Extract from both PDFs and curated databases
- **Code-only sources:** Infer patterns from test cases, assertions, and comments
- **Severity scope:** Include all severities (informational, gas) — some become high-sev in context
- **Emerging research:** Include theoretical/unproven vulns with 'theoretical' tag
- **Protocol-specific vulns:** Generalize to pattern IF similar libraries/protocols exist; keep protocol-specific only if truly unique
- **Contradictory advice:** Use latest consensus, resolve via Exa search if unclear
- **CTF sources:** Extract both vulnerability pattern AND solution approach
- **External conditions:** Document in dedicated assumptions section + inline notes

### Consolidation Rules

- **Taxonomy:** Full restructure from existing lenses — design new taxonomy based on semantic operations
- **Merge criteria:** Same semantic signature = merge, regardless of surface differences
- **Hierarchy depth:** Claude's discretion based on vulnerability complexity
- **Conflict resolution:** Claude evaluates technical accuracy; use Exa MCP for updated search when in doubt
- **Variant tracking:** Hybrid — minor variants in parent doc, major variants get own doc
- **Domain separation:** Unified taxonomy with tags (DeFi, NFT, Governance, etc.)
- **Cross-cutting vulns:** Claude determines if combo has unique detection pattern
- **Deprecated vulns:** Delete per skip-pre-0.8 decision
- **Emerging vulns:** Immediate entry with 'emerging' tag
- **Attribution:** Minimal — credit 1-2 primary sources per doc
- **Naming:** Descriptive names + simple IDs (e.g., `reen-001: classic-reentrancy`)
- **Technical depth:** LLM-optimized — enough context for LLM to understand without external lookups
- **Mitigations:** Conceptual + minimal working code with clear, simple language
- **PoC tests:** Include minimal Foundry/Hardhat test skeleton in each doc
- **Pattern linking:** Bidirectional links between VulnDocs and BSKG patterns
- **Library CVEs:** Only add CVEs that require semantic reasoning (skip those detectable by static analysis tools)

### Output Formatting

- **Doc structure:** Minimal — Pattern (with variants) + Detection + Fix. Scale slightly based on complexity but keep consistent
- **Code examples:** Minimal pseudo-code (abstract patterns, not full contracts)
- **File format:** YAML frontmatter for metadata + Markdown for content
- **Directory structure:** Nested by category > subcategory > deeper if needed. Enables focused agent runs per subcategory
- **Index files:** Hybrid — auto-generate base from structure, manually add priorities/notes
- **Semantic ops:** Plain language + BSKG operation name in parentheses (e.g., "transfers value out (TRANSFERS_VALUE_OUT)")
- **Detection logic:** Both plain description AND VQL query example
- **Versioning:** Git history only — no in-doc changelogs
- **Token tracking:** Claude's discretion on including token metadata
- **Linking format:** Claude determines most maintainable approach
- **YAML frontmatter fields:** Rich — id, name, category, tags, severity, patterns, assumptions, protocols, versions
- **Doc length:** Claude judges when length is justified (target ~100 lines)

### Quality Thresholds

- **Doc completeness:** All mandatory sections filled + pattern exists with tests
- **Pattern quality gate:** Draft OK for initial release (improve later)
- **FP tolerance:** Severity-based — critical vulns need low FP, low-sev more lenient
- **Iteration rule:** Keep iterating until doc is "really good" — no simple generic tests with high FP rates
- **Benchmark corpus:** DVDeFi challenges + real-world exploits + mixed into large codebases
- **LLM-reasoning vulns:** For docs requiring protocol context reasoning, test via subagent that uses BSKG + reasons about code (no hard pattern tests)
- **Coverage tracking:** Both source checklist (87/87) AND vulnerability class coverage matrix
- **Continuous improvement:** Hybrid — auto-discovery queues new vulns, human approves merge
- **Redundancy detection:** Semantic signature matching + LLM similarity check for edge cases
- **Tier processing:** Prioritized parallel — all tiers run simultaneously, Tier 1+2 conflicts win
- **Edge cases:** Claude adds limitations section when important for context
- **Tier B patterns:** Hybrid — create if semantic operations help, otherwise docs only
- **Subagent overlap:** Merge contributions from both subagents
- **Progress reporting:** Per-source updates
- **Error handling:** Retry 3x then skip, log for later retry

### Claude's Discretion

- Crawl depth per source
- Hierarchy depth per vulnerability
- Conflict resolution approach (with Exa search backup)
- Real-world exploit links (when detection-relevant)
- Severity in docs (when inherent to pattern)
- Token metadata inclusion
- Link format between docs
- Doc length exceptions
- Limitations sections
- When to create Tier B pattern vs docs-only

</decisions>

<specifics>
## Specific Ideas

- **Parallel processing:** Use multiple subagents to speed up the 87-source crawl significantly
- **Condensed docs:** Only actionable detection patterns, fixes, variations, and semantic reasoning — no bloated manual writeups
- **Agent-friendly structure:** Nested categories enable single-agent runs per subcategory in future orchestration
- **Protocol context:** Some vulnerabilities need LLM + protocol context to detect — test these with reasoning subagent, not hard pattern tests
- **Semantic-first:** Everything must be agnostic to variable names, function names — detection patterns should work across codebases

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-vulndocs-completion*
*Context gathered: 2026-01-20*
