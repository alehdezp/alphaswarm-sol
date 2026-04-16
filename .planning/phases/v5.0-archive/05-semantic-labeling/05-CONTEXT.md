# Phase 5: Semantic Labeling - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable detection of complex logic bugs through LLM-driven semantic labeling. Labels describe code intent and constraints, enabling detection of policy mismatches, invariant violations, and state machine issues that pure pattern matching misses. Labels are context-filtered to prevent LLM context pollution.

</domain>

<decisions>
## Implementation Decisions

### Label Taxonomy

**Categories:**
- Both intent-focused AND constraint-focused labels
- Intent labels: describe what code is MEANT to do ('transfers_ownership', 'enforces_timelock')
- Constraint labels: describe what must be TRUE ('balance_never_negative', 'only_owner_can_call')

**Granularity:**
- Hierarchical structure: coarse categories with fine sub-labels
- Example: `access_control.owner_only`, `access_control.role_based`
- Labels are context-filtered when returned to LLM — only surface relevant labels for current task
- Prevents context pollution (no access control labels when testing for reentrancy)

**Attachment Level:**
- Function-level as primary attachment point
- Statement-level labels available for precision when needed

**Negations:**
- Explicit negation labels: 'no_reentrancy_guard', 'no_access_check'
- Useful for finding missing protections

**Relationships:**
- Labels can capture relationships between functions
- Examples: 'depends_on(functionA)', 'must_call_before(init)', 'mutually_exclusive_with(withdraw)'

**Versioning:**
- No versioning or timestamps — current labels only
- Simpler, no history tracking

**Protocol Influence:**
- Hybrid: universal core taxonomy + protocol-specific extensions when context pack available
- Protocol type (lending, AMM, etc.) can enable additional label categories

**Custom Labels:**
- Review-gated: custom labels allowed but flagged for review before use in patterns

**Temporal:**
- Sequence labels only — label functions as part of sequences
- Don't encode full temporal logic

**Confidence:**
- Confidence levels (high/medium/low) instead of source tracking
- Don't track whether label came from docs vs code vs comments

### Labeler Behavior

**Context:**
- Sliced subgraph: relevant slice of BSKG based on function's properties and relationships
- Not just function source, not entire graph

**Ambiguity Handling:**
- Best guess + flag: apply most likely label but mark as 'uncertain' for later review

**Scope:**
- Smart incremental: only label changed/new functions
- Re-label affected neighbors when dependencies change

**Protocol Context:**
- Always use protocol context pack — informs labeling decisions
- "This is a lending protocol, so..."

**Reasoning:**
- Include reasoning for uncertain labels only
- High-confidence labels don't need explanation

**Conflict Resolution:**
- Prioritize code over comments
- If code does X but comment says Y, label based on code behavior

**VulnDocs Integration:**
- Pattern-aware: labeler knows vulnerability patterns and applies relevant labels proactively

**Specialization:**
- Cascading labelers: general labeler first, then specialized labelers for specific categories

**Trigger:**
- Configurable: flag on build-kg (--with-labels or --skip-labels)
- Not automatic by default

**Batching:**
- Smart batching: batch related functions (same call subgraph) together

**Output Format:**
- Tool calling: LLM uses tool calls to apply labels with structured parameters

### Pattern Integration

**Tier System:**
- New Tier C for label-dependent patterns
- Label-aware matching across all tiers
- Maximum flexibility for complex reasoning

**Auto-findings:**
- Configurable severity: auto-generate findings for label mismatches
- Severity depends on label type (critical vs informational)

**Evidence:**
- Summarized: include label summary in evidence packets
- Full labels available on drill-down

**YAML Syntax:**
- Both: dedicated `labels:` block for complex label logic
- Inline for simple checks: `has_label: access_control.owner_only`

**New Pattern Types:**
- Policy mismatch patterns: 'docs say X but code does Y'
- Invariant violation patterns: 'balance should never be negative'
- State machine patterns: illegal state transitions

**Verification:**
- No multi-agent verification for label-based findings
- Labels already represent LLM reasoning — skip attacker/defender/verifier

**VQL:**
- Full VQL support for label queries
- `FIND functions WHERE has_label('access_control.owner_only')`

**Prerequisites:**
- Pattern authors can define required labels
- Pattern only runs if specified labels exist

### Validation Approach

**Validation Method:**
- Ground truth corpus: maintain labeled contracts with known-correct labels
- Used for regression testing

**Review Threshold:**
- Below 0.5: only very uncertain labels (< 50% confidence) need review
- Less overhead than higher threshold

**Manual Override:**
- Full override: users can manually set/change any label
- Takes precedence over LLM-assigned labels

**Decay:**
- No decay: labels persist until explicitly re-labeled or deleted
- No time-based or code-change invalidation

**Export:**
- JSON/YAML export: export all labels in structured format for other tools

**Diff:**
- No label diff: only care about current labels, no historical comparison

**Metrics:**
- No separate label quality metrics reporting
- Labels are internal enrichment, not user-facing feature

**Feedback:**
- Agents can detect and modify labels on the fly if incorrect
- Update references automatically
- No separate feedback loop required

### Claude's Discretion

- Exact label taxonomy design within hierarchical structure
- Specific specialized labeler prompt designs
- Smart batching algorithm details
- VQL function names for label queries
- Ground truth corpus contract selection

</decisions>

<specifics>
## Specific Ideas

- "Labels should be filtered when returned to the LLM so they are context dependent of what the LLM is trying to prove" — prevents hallucination from irrelevant context
- "No need for reentrancy fields if testing for auth bugs" — smart filtering principle applies to labels
- "Agent could detect and modify flag on the fly if incorrect and update references" — self-correcting label system
- Labels enable complex reasoning that pure pattern matching misses — the core value proposition

</specifics>

<deferred>
## Deferred Ideas

- Label versioning/timestamps — decided against, keep simple
- Time-based label decay — decided against
- Multi-agent verification for label findings — decided against (labels are already LLM reasoning)
- Label diff across versions — decided against
- Separate label quality metrics reports — decided against

</deferred>

---

*Phase: 05-semantic-labeling*
*Context gathered: 2026-01-20*
