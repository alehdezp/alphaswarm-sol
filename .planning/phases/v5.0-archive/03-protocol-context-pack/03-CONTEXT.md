# Phase 3: Protocol Context Pack - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement Pillar 8 - economic context and off-chain reasoning capability. Deliver a schema and tooling for capturing protocol-level context (docs, roles, incentives, assumptions, off-chain inputs) that feeds into vulnerability detection. Context packs are LLM-generated from code analysis, documentation, and web research, with human review encouraged but not required.

</domain>

<decisions>
## Implementation Decisions

### Schema Design

**Format and Structure:**
- YAML format for human readability and manual editing
- Explicit versioning with changelog support for protocol upgrades
- Confidence levels on each field: 'certain', 'inferred', 'unknown'
- Support for both reference links AND embedded excerpts for external docs

**Roles and Capabilities:**
- Hybrid approach: capability-based roles (what they CAN DO) plus trust assumptions
- Roles defined by capabilities: mint, pause, upgrade, etc.
- Trust assumptions captured alongside capabilities
- Support nuanced reasoning about "maybe vulnerable" scenarios, not binary checks

**Economics and Assumptions:**
- Hybrid structure: explicit fields PLUS freeform 'notes' for nuance
- Off-chain inputs: Claude decides structure (input registry, role embedding, or dependency graph as appropriate)
- Assumptions: Claude decides categorization (typed categories vs flat with tags)
- Composability: Claude decides whether context packs support inheritance

**Invariants:**
- Both semi-formal AND natural language for each invariant
- Semi-formal: `{what: 'totalSupply', must: 'lte', value: 'maxSupply'}`
- Natural language: for LLM reasoning context

**Special Sections:**
- Explicit 'accepted_risks' section for known/accepted behaviors (auto-filtered from findings)
- Dedicated 'security_model' section summarizing overall trust model
- 'critical_functions' section: manual list + auto-detected for coverage
- Optional 'deployment' section for chain-specific context
- Threat model: Claude decides whether explicit or derived from assumptions

**Granularity:**
- Function-level context supported (assumptions attached to specific functions)
- Bidirectional linking: context pack updates sync to BSKG and vice versa
- Designed for minimal, targeted retrieval (sections independently addressable)

### Input Workflow

**Generation Approach:**
- LLM-generated, not human-authored
- Agents generate from: BSKG analysis, protocol docs, web research (GitHub issues, audits, forums, Twitter)
- Infer business impact: "what would be a disaster for the protocol"
- Review encouraged but not required; flagged as 'auto-generated' when not reviewed

**CLI Integration:**
- Both: auto-generate during `build-kg` AND standalone `alphaswarm generate-context` command
- Storage in BSKG cache with structured folder for granular retrieval
- Smart filtering built into VKG: agents request only relevant properties for current test

**Discovery:**
- Auto-discover docs (README, docs/, whitepaper links) + user can override/add sources
- Comprehensive external search: GitHub issues, past audits, governance forums
- Section-level attribution (not per-fact)

**Updates:**
- Incremental update workflow when code changes
- Template library exists as reference, but generation always starts from code analysis

### Doc Parsing Approach

**Extraction Method:**
- Fully LLM-driven (most flexible, handles varied doc formats)
- Cross-validate doc claims against code: verify documented behaviors exist
- Multimodal: use vision to extract from diagrams and flowcharts

**Conflict Handling:**
- Flag conflicts between docs and code explicitly
- Do NOT assume docs are outdated - docs/forums are often "the law"
- Check version information when available
- Treat doc-code conflicts as potential finding source

**Inference:**
- Active inference of unstated assumptions (e.g., 'uses oracle' → infers 'assumes oracle honest')
- Infer potential invariants, flag as 'inferred' for validation
- Extract security claims as hypotheses to test

**Content Extraction:**
- Source reliability tiers: Tier 1 (official docs), Tier 2 (audits), Tier 3 (community/forums)
- Translate non-English docs to English
- Extract roles AND expected user flows when documented
- Freeform tokenomics summary focused on security-relevant parameters
- Extract governance: voting thresholds, timelock durations, upgrade procedures
- Parse prior audit reports: extract findings, mitigations, unresolved issues
- Track document changelog when available
- Emergency procedures: Claude decides what's relevant

**Ambiguity Handling:**
- Pick most likely interpretation, note alternatives existed
- Generate questions about security-critical gaps for investigation

### Evidence Integration

**Attachment Style:**
- Hybrid: links for full context, embedded excerpts for key assumptions

**Finding Types:**
- 'Violated assumption' is a first-class finding type with full evidence support
- Business impact derived from context: "user funds at risk because X role can do Y"

**Confidence:**
- Weighted combination: final confidence = f(code_evidence, context_confidence)

**Context Updates:**
- Bidirectional: agents can add discoveries to context pack (new assumptions, inferred roles)
- Each bead inherits relevant context pack sections automatically

**Filtering:**
- Accepted risks auto-filtered from findings
- Context-driven pattern selection: protocol type influences relevant patterns

**Analysis:**
- Uniform analysis (no priority hints)
- Support 'what-if' scenario testing: run analysis with modified assumptions

**Traceability:**
- Show relevant assumptions that directly support findings (not full trace)
- Bidirectional gap linkage: findings link to gaps AND gaps marked as addressed

### Claude's Discretion

- Off-chain input structure (input registry, role embedding, or dependency graph)
- Assumption categorization approach
- Whether context packs support inheritance/composition
- Emergency procedure extraction scope
- Threat model representation (explicit section vs derived)

</decisions>

<specifics>
## Specific Ideas

- "The docs or webpage or forums are often the law" - treat doc-code conflicts as potential bugs, not outdated docs
- "Logic vulnerabilities are not true or false, but more like 'it could be', 'seems not intended', 'could be dangerous even if docs don't say'" - support nuanced reasoning
- Schema should enable minimal, targeted retrieval so LLMs don't fill context window unnecessarily
- "No need for BSKG to return reentrancy fields if testing for auth bugs" - smart filtering principle
- Generate questions about gaps in documentation for agents to investigate

</specifics>

<deferred>
## Deferred Ideas

- BSKG smart filtering across all properties (mentioned but touches Phase 2 builder work)
- Convoy batching with context pack routing (Phase 4 orchestration)

</deferred>

---

*Phase: 03-protocol-context-pack*
*Context gathered: 2026-01-20*
