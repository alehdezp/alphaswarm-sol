# Codebase Concerns

**Analysis Date:** 2026-02-04

## Tech Debt

**Legacy Graph Builder:**
- Issue: 6,139-line `builder_legacy.py` marked deprecated but still present in codebase
- Files: `src/alphaswarm_sol/kg/builder_legacy.py`, `src/alphaswarm_sol/kg/builder/functions.py` (imports legacy)
- Impact: Maintenance burden, confusion about which builder to use, import warnings on every build
- Fix approach: Complete migration validation, remove legacy module before GA release

**Large Monolithic Files:**
- Issue: Multiple files exceed 2,000 LOC, indicating potential god-object anti-patterns
- Files: `src/alphaswarm_sol/kg/builder.py` (6,138 LOC), `src/alphaswarm_sol/kg/slicer.py` (3,412 LOC), `src/alphaswarm_sol/orchestration/schemas.py` (2,366 LOC), `src/alphaswarm_sol/vulndocs/schema.py` (2,027 LOC)
- Impact: Difficult to test, high cognitive load, merge conflicts, slow IDE performance
- Fix approach: Extract cohesive sub-modules, apply Single Responsibility Principle

**TODO/FIXME Comments in Production Code:**
- Issue: 100+ TODO/FIXME/HACK markers scattered across production code
- Files: Template generators, beads creation, VulnDocs scaffolding, test helpers
- Impact: Incomplete implementations shipped to production, unclear what's placeholder vs. intentional
- Fix approach: Audit all markers, convert to tracked issues, remove or implement before GA

**Deprecated Aliases Still Active:**
- Issue: Taxonomy module maintains `DEPRECATED_ALIASES` dict with migration paths, but aliases still functional
- Files: `src/alphaswarm_sol/kg/taxonomy.py` (lines 653-681)
- Impact: Users rely on deprecated patterns, migration never completes
- Fix approach: Add deprecation warnings with version deadline, schedule removal in 5.1

**Empty Return Statements:**
- Issue: 402 instances of `pass`, empty returns, or stub implementations across 187 files
- Files: Widespread across adapters, orchestration, context, testing modules
- Impact: Silent failures, incomplete feature implementations, unclear completion state
- Fix approach: Replace stubs with explicit NotImplementedError or complete implementations

## Known Bugs

**Skill Recognition Gap:**
- Symptoms: Skills with non-v2 frontmatter format not recognized by validation system
- Files: `.claude/skills/vrs-agentic-testing.md`, `.claude/skills/vrs-claude-code-agent-teams-runner.md`, `.claude/skills/vrs-run-validation.md`, `.claude/skills/vrs-status.md`
- Trigger: Using `skill:` instead of `name:` in frontmatter
- Workaround: Manual skill invocation works, but validation/discovery fails
- Fix approach: Standardize frontmatter format across all skills, update parser to handle legacy format

**Missing Ground Truth Corpus:**
- Symptoms: E2E validation blocked due to no external ground truth data
- Files: `.vrs/corpus/ground-truth/` exists but incomplete (only 5 Code4rena, 0 SmartBugs indexed)
- Trigger: Any E2E validation attempt requiring external provenance
- Workaround: None - validation cannot proceed without external data
- Fix approach: Seed corpus with 10+ validated contracts from external sources (Phase 7.3.1.6 B1/IMP-B1)

**Zero claude-code-controller Evidence for Core Workflows:**
- Symptoms: No workflow has a complete claude-code-agent-teams transcript proving it works end-to-end
- Files: All workflows in `.planning/testing/workflows/` marked `no-proof` in `COVERAGE-MAP.md`
- Trigger: Attempting to validate any workflow behavior
- Workaround: None - workflows are theoretically correct but unproven
- Fix approach: Execute Phase 7.3.1.6 with mandatory claude-code-controller validation for every workflow

## Security Considerations

**API Key Handling:**
- Risk: No explicit documentation on secure API key storage for Anthropic/OpenAI integrations
- Files: `src/alphaswarm_sol/agents/runtime/anthropic.py`, `src/alphaswarm_sol/agents/runtime/openai_agents.py`
- Current mitigation: Environment variable usage implied but not enforced
- Recommendations: Add explicit key validation, refuse to run if keys in plaintext config, document secure storage patterns

**External Tool Execution:**
- Risk: Tools like Slither, Mythril, Aderyn executed via subprocess without strict sandboxing
- Files: `src/alphaswarm_sol/tools/executor.py`, `src/alphaswarm_sol/tools/runner.py`, adapter files
- Current mitigation: Timeout enforcement, basic error handling
- Recommendations: Add resource limits, validate tool outputs before processing, document trust model

**User-Supplied Contract Code:**
- Risk: Malicious contracts could exploit parser vulnerabilities or cause resource exhaustion
- Files: `src/alphaswarm_sol/kg/builder.py` (Slither integration)
- Current mitigation: Slither's own parsing safety
- Recommendations: Add max file size limits, timeout enforcement on graph builds, document supported Solidity versions

## Performance Bottlenecks

**Knowledge Graph Build Time:**
- Problem: Large contracts (>5k LOC) cause multi-minute graph builds
- Files: `src/alphaswarm_sol/kg/builder.py`, Slither compilation phase
- Cause: Sequential contract processing, no build caching, full re-analysis on changes
- Improvement path: Implement incremental builds, cache graph segments, parallelize contract analysis

**VQL Query Performance:**
- Problem: Complex graph queries on large codebases can timeout
- Files: `src/alphaswarm_sol/vql2/executor.py` (line 544: TODO comment on aggregations)
- Cause: No query optimization, no graph indexing beyond basic node lookups
- Improvement path: Add query planning, implement graph indexes, cache common query patterns

**Pattern Matching at Scale:**
- Problem: Running all 556+ patterns sequentially is slow
- Files: Pattern detection orchestration in audit flows
- Cause: No parallelization, no early exit on negative controls
- Improvement path: Tier A/B/C parallel execution, pattern ranking to prioritize high-value checks

**LLM Token Overhead:**
- Problem: Large evidence packets and verbose prompts drive up costs and latency
- Files: Agent runtime, context packing, debug mode outputs
- Cause: TOON format adoption incomplete, no token budget enforcement per-call
- Improvement path: Complete TOON migration, add token budgets to all LLM calls, implement prompt compression

## Fragile Areas

**Phase 7.3.1.5/7.3.1.6 Testing Framework:**
- Files: `.planning/phases/07.3.1.5-full-testing-orchestrator/`, `.planning/phases/07.3.1.6-full-testing-hardening/`
- Why fragile: 44 blocking gaps identified in IMPROVEMENT-ROADMAP.md, zero workflows proven with transcripts
- Safe modification: DO NOT modify testing orchestration until Definition Gate passes and Wave 0 artifacts created
- Test coverage: Framework exists but unvalidated - changes could break undetected

**Orchestration Marker System:**
- Files: Skills expecting TaskCreate/TaskUpdate markers, progress guidance
- Why fragile: Marker specifications incomplete (IMP-A1), no enforcement layer, skills don't emit markers yet
- Safe modification: Lock marker format in canonical docs before changing skill prompts
- Test coverage: No tests verify marker presence or format

**Multi-Agent Debate Flow:**
- Files: `src/alphaswarm_sol/agents/adversarial/`, attacker/defender/verifier agents
- Why fragile: Debate never proven in live claude-code-agent-teams session, no evidence packs demonstrating full cycle
- Safe modification: Changes to agent prompts require E2E transcript validation
- Test coverage: Unit tests exist but no integration/E2E validation

**Economic Context Generation:**
- Files: `src/alphaswarm_sol/context/builder.py` (1,324 LOC), EI/CTL undefined (IMP-A4)
- Why fragile: Context quality unpredictable, no validation of required fields, Tier C gating incomplete
- Safe modification: Define EI/CTL spec before relying on context for Tier C reasoning
- Test coverage: Context generation tested but quality/completeness unvalidated

## Scaling Limits

**Single-Machine Orchestration:**
- Current capacity: All orchestration assumes single machine, no distributed execution
- Limit: Large audits (100+ contracts) will hit memory/time constraints
- Scaling path: Add worktree-based parallelization, support remote agent execution, implement result streaming

**Knowledge Graph Memory Usage:**
- Current capacity: Full graph loaded in memory
- Limit: Large projects (500k+ LOC) will OOM on graph build
- Scaling path: Implement graph streaming, paginated queries, lazy node loading

**LLM Rate Limits:**
- Current capacity: No rate limit handling beyond basic retry
- Limit: High-volume usage will hit Anthropic/OpenAI quotas
- Scaling path: Add backoff/retry with jitter, queue management, fallback to alternative models

## Dependencies at Risk

**Slither Dependency:**
- Risk: Core graph building depends on Slither, which has breaking changes between versions
- Impact: Graph builds fail if Slither API changes
- Migration plan: Abstract Slither behind adapter, support multiple versions, add fallback to solc AST

**Claude Code Orchestration Model:**
- Risk: Framework assumes Claude Code Task tools (TaskCreate, TaskUpdate, Task) remain stable
- Impact: Breaking changes would invalidate entire orchestration layer
- Migration plan: Document required Task tool API, add version detection, maintain fallback to manual orchestration

**Python 3.11+ Requirement:**
- Risk: Specific Python version required for type hints, not documented in constraints
- Impact: Install failures on older Python versions
- Migration plan: Document minimum Python version, add runtime version check, consider 3.10 backport

## Missing Critical Features

**Orchestration Proof:**
- Problem: Core product claim (multi-agent orchestration) is unproven with real transcripts
- Blocks: Credible GA release, user trust, competitive positioning
- Priority: CRITICAL - tracked as I-01 in Phase 7.3.1.6

**Resume/Restart Semantics:**
- Problem: Audit resume behavior undefined and untested
- Blocks: Long-running audits, failure recovery, incremental validation
- Priority: HIGH - tracked in Phase 7.3.1.6 N5

**Economic Context Mock Bypass:**
- Problem: Tier C testing requires mock contexts, but bypass mechanism undefined
- Blocks: Tier C validation scenarios
- Priority: HIGH - tracked as Phase 7.3.1.6 T4

**Graph Integrity Validation:**
- Problem: No automated check that graph builds are complete and correct
- Blocks: Trusting graph-based reasoning outputs
- Priority: HIGH - tracked as Phase 7.3.1.6 B16

## Test Coverage Gaps

**Audit Entrypoint Orchestration:**
- What's not tested: Full `/vrs-audit` flow from invocation → graph → detection → debate → report
- Files: `.claude/skills/vrs-audit.md`, orchestration handlers
- Risk: Users invoke audit, nothing happens or behavior diverges from docs
- Priority: CRITICAL

**Multi-Agent Debate:**
- What's not tested: Attacker/defender/verifier debate cycle producing verdicts
- Files: `.claude/agents/vrs-attacker/`, `.claude/agents/vrs-defender/`, `.claude/agents/vrs-verifier/`
- Risk: Core product differentiator may not work as designed
- Priority: CRITICAL - tracked as I-02 in Phase 7.3.1.6

**Tier B/C Pattern Reasoning:**
- What's not tested: Complex vulnerabilities detected via graph + VQL, not pattern matching
- Files: Tier B/C patterns in `vulndocs/`
- Risk: Framework may fall back to pattern matching, undermining behavioral detection claims
- Priority: CRITICAL - existential validation in IMP-G1, IMP-I1

**Tool Integration End-to-End:**
- What's not tested: Full flow from tool execution → finding dedup → task creation → investigation
- Files: `src/alphaswarm_sol/tools/runner.py`, dedup orchestration
- Risk: Tools run but findings not properly integrated into workflow
- Priority: HIGH - tracked in Phase 7.3.1.6 B9

**Failure Modes:**
- What's not tested: Corrupt graph, missing files, timeout scenarios, concurrent run collisions
- Files: Error handling across all modules
- Risk: Silent failures, state corruption, poor error messages
- Priority: HIGH - tracked in Phase 7.3.1.6 B13, critique W2

**Context Pack Completeness:**
- What's not tested: Economic Intelligence (EI) outputs, Context Trust Level (CTL) validation
- Files: `src/alphaswarm_sol/context/builder.py`, Tier C gating logic
- Risk: Tier C patterns run without sufficient context, producing false positives
- Priority: HIGH - tracked as IMP-A4, IMP-A5, B10.A

**Progress and State Management:**
- What's not tested: `.vrs/state/current.yaml` updates, `/vrs-status` output, resume from snapshots
- Files: State management, status reporting
- Risk: Users cannot track progress or resume after failures
- Priority: MEDIUM - tracked in Phase 7.3.1.6 B7

**Documentation Alignment:**
- What's not tested: Workflow docs match actual behavior, skills reference correct commands
- Files: All workflow documentation in `docs/workflows/`, `.planning/testing/workflows/`
- Risk: Docs become stale, users follow outdated instructions
- Priority: MEDIUM - tracked as Phase 7.3.1.6 B12

## Phase 7.3.1.5 Status (Full-Testing Orchestrator)

**Delivered Artifacts (Verified 2026-01-30):**
- `/vrs-full-testing` super-orchestrator skill (324 LOC)
- `FullTestingOrchestrator` Python class (1,152 LOC)
- Evidence pack schema with transcript validation
- Debug mode specification and recorder
- 95 scenario matrix across 14 vulnerability categories
- 10 QA gates (G01-G10) with thresholds
- Retry/resume state machine (19 states)

**Gaps Identified in Critique:**
- W1: No explicit skill/agent coverage mapping (47 skills, 24 agents)
- W2: Insufficient edge case scenarios (failure injection, parser stress, negative controls)
- W3: claude-code-controller enforcement not guaranteed at runtime
- W4: Debug mode not enforced per skill/agent invocation
- W5: Golden transcript strategy incomplete (diff tolerance undefined)
- W6: Snapshot strategy incomplete (per-stage snapshots missing)
- W7: Ground truth sources not explicit in scenario matrix
- W8: Failure taxonomy and refinement triggers undefined

**Current State:** Infrastructure delivered but operationally untested - zero evidence packs from real runs exist in repo

## Phase 7.3.1.6 Status (Full-Testing Hardening)

**Documentation Complete:**
- Context document defines goals, constraints, non-negotiables
- IMPROVEMENT-ROADMAP.md lists 44 IMP items + 7 I-validations + 3 HENTI validations
- SUPER-REPORT.md provides 25 plan seeds (B1-B25, N1-N5)
- Plan index maps waves 0-6 to plan seeds

**Execution Status:** BLOCKED by Definition Gate
- Wave 0 artifacts COMPLETE: ORCHESTRATION-MARKERS.md, PROOF-TOKEN-MATRIX.md, economic-intelligence-spec.md, RULES-ESSENTIAL.md updates
- Wave 0.5 artifacts PARTIAL: Decision trees for IMP-G1, IMP-H1, IMP-I1 created
- Remaining: IMP-J2 execution sequences, Wave 1+ artifacts

**Critical Blockers (From SUPER-REPORT.md):**
1. **Installation never validated** (B1): No claude-code-agent-teams transcript of `uv tool install -e .` → `alphaswarm init` → `alphaswarm --help`
2. **Audit doesn't orchestrate** (B5): Skills describe workflow but don't emit TaskCreate/TaskUpdate markers
3. **Zero Tier B/C proofs** (B10): Complex vulnerability detection unproven with graph + VQL reasoning
4. **No workflow has evidence** (B11): All 13 workflows in COVERAGE-MAP.md marked `no-proof`
5. **Settings/state undefined** (B7): `.vrs/settings.yaml` schema incomplete, `.vrs/state/current.yaml` not updated
6. **Tier C gating incomplete** (B8): EI/CTL definitions missing (IMP-A4/A5), context quality unchecked
7. **Graph value unproven** (IMP-G1): No evidence that graph improves reasoning vs. pattern matching alone
8. **Multi-agent value unproven** (IMP-H1): No evidence that debate produces better results than single-agent

**Root Cause:** Plans are documentation-first, not execution-first. They describe what SHOULD happen but don't lock down definitions, create required artifacts, or prove behavior with transcripts.

**Non-Negotiable for GA:** Cannot ship without proving orchestration works (I-01), debate adds value (I-02), and Tier B/C reasoning uses graph (IMP-G1, IMP-I1)

## Existential Requirements

**Knowledge Graph Value (IMP-G1):**
- Question: Does the graph materially improve agent reasoning vs. pattern matching alone?
- Current state: Unvalidated assumption
- Validation: Graph ablation study comparing detection with/without graph queries
- Abort criteria: If graph provides <10% improvement in precision/recall, reconsider architecture
- Files: `.planning/testing/decision-trees/IMP-G1-graph-ablation.yaml`, execution sequence TBD

**Multi-Agent Value (IMP-H1):**
- Question: Does attacker/defender/verifier debate produce better results than single-agent analysis?
- Current state: Unvalidated assumption
- Validation: Compare single-agent vs. multi-agent on same contract set
- Abort criteria: If multi-agent shows no quality improvement or >3x cost increase, simplify to single-agent
- Files: `.planning/testing/decision-trees/IMP-H1-multi-agent.yaml`, execution sequence TBD

**Behavioral Detection (IMP-I1):**
- Question: Does semantic operation detection outperform name-based pattern matching?
- Current state: Partially validated (mutation testing showed rename resistance)
- Validation: Compare behavioral vs. name-based detection on adversarial corpus
- Abort criteria: If behavioral detection shows <15% improvement in recall, revert to hybrid approach
- Files: `.planning/testing/decision-trees/IMP-I1-behavioral.yaml`

**Project Justification:** If all three existential validations fail, the core architectural decisions are invalid and project must pivot or halt.

---

*Concerns audit: 2026-02-04*
*Focus: Testing framework gaps, unproven orchestration, existential validations*
*Blockers: Definition Gate, ground truth corpus, zero workflow evidence*
