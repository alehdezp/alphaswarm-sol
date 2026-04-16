# GAP-08: Multi-Agent Ground Truth Format Design

**Created by:** improve-phase
**Source:** P3-IMP-14
**Priority:** HIGH
**Status:** resolved
**depends_on:** []
**Resolved:** 2026-02-19

## Question

What does a multi-agent ground truth entry look like? What fields are needed to judge debate quality vs rubber-stamping? How should the existing single-agent `ground-truth.yaml` schema be extended to capture defender counter-arguments, verifier arbitration basis, and disagreement-to-resolution paths?

## Context

Plan C exit criteria include "At least 1 orchestrator flow tested with multi-agent lifecycle observation." The corpus (18 projects) has `ground-truth.yaml` files defining single-agent findings with `expected_reasoning_chain` (3-5 steps per finding). No fields exist for multi-agent debate quality. Without a ground truth format, orchestrator contracts are single-agent contracts with extra steps. Prestep P1 acknowledges "0 multi-agent ground truth templates." This format design blocks Prestep P-2 and Plan C orchestrator evaluation contracts.

## Research Approach

- Search for multi-agent debate evaluation frameworks in AI/ML literature (PRISM, DEBATE, MAD, iMAD protocols)
- Look at existing adversarial debate evaluation rubrics in LLM-as-judge research
- Examine how audit firms score multi-reviewer consensus processes
- Check smart contract audit contest formats (Code4rena, Sherlock) for how they evaluate finding quality with multiple reviewers
- An authoritative answer would be a concrete YAML schema with fields that distinguish genuine debate from rubber-stamping

## Findings

### 1. Academic Multi-Agent Debate Evaluation Frameworks

**Confidence: HIGH** (multiple peer-reviewed sources agree)

Three major frameworks inform ground truth design for adversarial debate evaluation:

**D3 (Debate, Deliberate, Decide)** (Harrasse et al., 2024, arXiv:2410.04663v4, NeurIPS-adjacent):
- Uses 6 scoring dimensions on 1-20 scale: relevance, accuracy, depth, clarity, reasoning strength, and *effectiveness in addressing opponent's points*
- Key rubber-stamping signal: "Evidence Citation Rate" -- 94% of rationales must explicitly reference debate transcripts. Low citation rate = rubber-stamping
- Diversity check: cross-persona agreement averaging 89.5% confirms verdicts are not unanimous rubber-stamps. Persona disagreements should trace to "identifiable reasoning axes"
- Budgeted stopping: forced continuation changes verdicts in only 6% of cases; early convergence without verdict change indicates genuine discrimination

**ColMAD (Collaborative Multi-Agent Debate)** (ICLR 2026 submission, OpenReview W6qSjvTQMW):
- Reframes debate as non-zero-sum game. Key insight: zero-sum framing leads to "debate hacking" -- debaters mislead the judge rather than seeking truth
- Detection signal: agents that misinterpret the task or present "overconfident claims" = debate hacking/rubber-stamping
- Ground truth: agents should "criticize each other in a supportive way" and "complement missing points"

**Safety Evaluation Multi-Agent Judge** (arXiv:2511.06396v1):
- Critic/Defender/Judge structure maps directly to Attacker/Defender/Verifier
- Scoring: binary (safe/unsafe), 5-level ordinal risk, 10-point continuous risk score
- Quality signal: Cohen's kappa agreement with human ground truth
- Key finding: 3 debate rounds optimal; more rounds = "error accumulation and noisy consensus" (consensus collapse, not genuine refinement)

**MAD Meta-Analysis** (Zhang et al., "Stop Overvaluing Multi-Agent Debate"):
- Critical finding: MAD often fails to outperform single-agent Chain-of-Thought and Self-Consistency
- Model heterogeneity is "a universal antidote" -- homogeneous agents produce fake consensus
- Implication: ground truth must capture WHETHER debate added value over single-agent analysis

### 2. Smart Contract Audit Contest Patterns

**Confidence: MEDIUM-HIGH** (official docs from Code4rena and Sherlock)

**Code4rena** (docs.code4rena.com/awarding):
- Multiple independent reviewers submit findings independently
- Deduplication: similar findings grouped into "duplicate sets" with severity calibration
- Quality scoring: "selected for report" bonus (30% slice bonus for best write-up in duplicate group)
- Key pattern: finding quality is judged NOT by consensus but by uniqueness, evidence depth, and PoC thoroughness
- Partial credit system for duplicates with insufficient proof

**Sherlock** (docs.sherlock.xyz):
- "Multi-Stage Judging" pipeline: duplicates cleared, severities corrected
- Lead Senior Watson does full review first, then crowd validates
- Key insight: the senior reviewer's assessment serves as ground truth baseline; crowd findings measured against it

**Relevance to AlphaSwarm:** The audit contest model suggests ground truth should include:
- Expected finding independence (did the attacker find it without being led?)
- Expected evidence quality tiers (PoC-level vs observation-level)
- Expected deduplication behavior (should attacker and defender independently identify same pattern?)

### 3. Existing AlphaSwarm Debate Infrastructure

**Confidence: HIGH** (direct codebase examination)

The existing codebase already has substantial debate infrastructure that the ground truth schema must align with:

**Debate Skill** (`src/alphaswarm_sol/shipping/skills/debate.md`):
- iMAD-inspired protocol: CLAIM -> REBUTTAL(S) -> SYNTHESIS -> HUMAN CHECKPOINT
- `DebateClaim` structure: role, claim, evidence (with locations + confidence), reasoning
- Synthesis produces: attacker_strength, defender_strength, delta, verdict (LIKELY/UNCERTAIN/REJECTED), dissent
- Early exit when no new arguments

**Orchestrator Debate Contract** (`.vrs/testing/contracts/samples/orchestrator-debate.json`):
- Already evaluates: spawns-required-agents, collects-verdicts, verifier-arbitrates, debate-produces-consensus
- Reasoning dimensions: evidence_quality, adversarial_rigor, consensus_formation
- Resolution statuses: confirmed/refuted/disputed

**Use Case Scenarios** (`.planning/testing/scenarios/use-cases/debate/`):
- UC-DEB-002: Tests convergence speed when both sides agree (rubber-stamping detection)
- UC-DEB-003: Tests escalation on non-convergence (honest uncertainty)
- UC-VER-003: Tests defender disagreement handling (balanced assessment)
- Key dimensions already defined: convergence_speed, agreement_recognition, evidence_quality, verdict_confidence

### 4. Rubber-Stamping Detection Signals

**Confidence: HIGH** (synthesized from multiple sources + codebase analysis)

From the literature and existing codebase, these signals reliably distinguish genuine debate from rubber-stamping:

| Signal | Genuine Debate | Rubber-Stamping |
|--------|----------------|-----------------|
| Evidence citation rate | Both sides cite specific code locations and graph nodes | Generic claims without location anchoring |
| Argument novelty per round | New arguments or evidence in rebuttals | Restating same claim with different words |
| Defender engagement | Defender identifies specific guards/mitigations OR honestly states none found | Defender agrees immediately or fabricates weak objections |
| Convergence pattern | Strength delta narrows then stabilizes | Immediate convergence or no delta change across rounds |
| Cross-reference | Agents reference each other's specific claims | Agents respond generically without addressing opponent |
| Verifier independence | Verifier runs own queries, cites evidence from both sides | Verifier echoes attacker without independent verification |

## Recommendation

### Prescriptive Schema Design

Extend `ground-truth.yaml` with a new top-level `debate_expectations` section that sits alongside the existing `findings` array. Do NOT modify the existing single-agent `findings` schema -- extend it.

**Concrete YAML Schema:**

```yaml
# Existing single-agent fields preserved as-is
findings:
  - pattern_id: balance-update-after-transfer
    contract: SimpleVault
    function: redeem
    line_range: 55-66
    severity: high
    expected_reasoning_chain:
      - "Identify external call..."
      - "Notice state update after..."
      - "Conclude: reentrancy..."

# NEW: Multi-agent debate ground truth extension
debate_expectations:
  # Which findings should trigger multi-agent debate
  debatable_findings:
    - finding_ref: balance-update-after-transfer  # references pattern_id above
      expected_outcome: confirmed                 # confirmed | refuted | disputed | escalated
      expected_rounds: 2                          # expected debate rounds before convergence
      difficulty: easy                            # easy | medium | hard | ambiguous

      # What the attacker SHOULD argue
      attacker_expected:
        claim_type: exploit_path                  # exploit_path | economic_impact | precondition_chain
        must_cite:                                # required evidence anchors
          - type: graph_node
            description: "CEI violation: external call before state update"
          - type: code_location
            description: "msg.sender.call{value: payout} at line 59"
        min_evidence_count: 2
        min_confidence: 0.8

      # What the defender SHOULD argue (or acknowledge)
      defender_expected:
        position: concede                         # concede | partial_mitigation | full_mitigation | challenge_preconditions
        # When position=concede: defender should honestly say "no guards found"
        # When position=full_mitigation: defender should cite specific guards
        must_cite: []                             # empty when no mitigations exist
        expected_mitigations: []                  # empty for genuinely vulnerable contracts
        # For guarded contracts:
        # expected_mitigations:
        #   - "nonReentrant modifier on redeem"
        #   - "ReentrancyGuard imported and applied"

      # What the verifier SHOULD do
      verifier_expected:
        must_check_both_sides: true               # ALWAYS true
        independent_queries:                      # queries verifier should run independently
          - "Check for reentrancy guards on redeem"
          - "Verify CEI ordering in redeem"
        arbitration_basis: evidence_weight         # evidence_weight | precondition_analysis | external_context
        expected_verdict_confidence: high          # high | medium | low

      # Rubber-stamping detection criteria
      quality_signals:
        min_unique_evidence_items: 3              # across all agents combined
        defender_must_engage: true                # false only for trivially obvious vulns
        verifier_must_run_own_queries: true        # ALWAYS true
        max_rounds_without_new_argument: 1        # if >1, debate is stalling
        # These become evaluation contract checks:
        anti_rubber_stamp_checks:
          - "Defender cites at least one specific code location (even if conceding)"
          - "Verifier references both attacker AND defender positions"
          - "Each rebuttal round introduces at least one new piece of evidence or argument"

  # Contested finding example (defender disagrees)
    - finding_ref: oracle-stale-price
      expected_outcome: confirmed
      expected_rounds: 3
      difficulty: medium

      attacker_expected:
        claim_type: exploit_path
        must_cite:
          - type: code_location
            description: "oracle.getLatestValue() return value with unchecked timestamp"
        min_evidence_count: 2
        min_confidence: 0.7

      defender_expected:
        position: challenge_preconditions
        must_cite:
          - type: code_location
            description: "oracle update frequency or external monitoring"
        expected_mitigations:
          - "Oracle is Chainlink with heartbeat (external context needed)"
        # Defender argues the oracle may be reliable enough

      verifier_expected:
        must_check_both_sides: true
        independent_queries:
          - "Check oracle interface for freshness guarantees"
          - "Verify if staleness threshold exists anywhere in codebase"
        arbitration_basis: precondition_analysis
        expected_verdict_confidence: medium    # medium because external context needed

      quality_signals:
        min_unique_evidence_items: 4
        defender_must_engage: true
        verifier_must_run_own_queries: true
        max_rounds_without_new_argument: 1
        anti_rubber_stamp_checks:
          - "Defender provides specific counter-evidence, not just 'oracle might be fine'"
          - "Verifier independently checks oracle interface, not just echoing attacker"
          - "If verdict is 'confirmed', verifier explains why defender's mitigation is insufficient"

  # Escalation example (genuinely ambiguous)
    - finding_ref: read-only-reentrancy
      expected_outcome: escalated
      expected_rounds: 3                          # max rounds before escalation
      difficulty: ambiguous

      attacker_expected:
        claim_type: exploit_path
        must_cite:
          - type: graph_node
            description: "Read-only reentrancy pattern identified"
        min_evidence_count: 2
        min_confidence: 0.6

      defender_expected:
        position: challenge_preconditions
        must_cite:
          - type: reasoning
            description: "Exploitability depends on external view function consumers"
        expected_mitigations:
          - "Impact requires external contract to read stale state during callback"

      verifier_expected:
        must_check_both_sides: true
        independent_queries:
          - "Check for external consumers of view functions"
          - "Verify if stale state during callback is actionable"
        arbitration_basis: external_context
        expected_verdict_confidence: low

      quality_signals:
        min_unique_evidence_items: 4
        defender_must_engage: true
        verifier_must_run_own_queries: true
        max_rounds_without_new_argument: 1
        anti_rubber_stamp_checks:
          - "Escalation summary includes both attacker and defender positions"
          - "Escalation identifies the specific unresolvable question"
          - "Escalation suggests what additional information would resolve it"

  # Global debate quality settings
  global_quality_requirements:
    evidence_citation_rate: 0.9                   # 90%+ of claims must cite evidence
    cross_reference_rate: 0.7                     # 70%+ of rebuttals must address opponent's specific points
    convergence_budget: 3                         # max rounds before requiring escalation or verdict
    model_heterogeneity_required: false           # future: use different models for different agents
```

### Key Design Decisions

1. **Additive extension, not replacement.** The `debate_expectations` section sits alongside `findings`. Single-agent ground truth remains untouched. Multi-agent evaluation adds a layer on top.

2. **Four expected outcomes** map to the existing debate skill's outputs: `confirmed` (attacker wins), `refuted` (defender wins), `disputed` (uncertainty, low-confidence verdict), `escalated` (non-convergence, human needed).

3. **Defender position taxonomy** with four levels: `concede` (no mitigation exists), `partial_mitigation` (some guards but incomplete), `full_mitigation` (finding should be refuted), `challenge_preconditions` (attack requires unrealistic conditions). This taxonomy is the core rubber-stamping detector -- if the ground truth says `concede` but the defender fabricates a `full_mitigation`, that is detectable.

4. **Anti-rubber-stamp checks** are explicit, evaluatable strings that become capability checks in the orchestrator evaluation contract. They translate directly to the existing `capability_checks` array in `evaluation_contract.schema.json`.

5. **Quality signals** are measurable: evidence counts, citation rates, query independence. These feed into the existing `reasoning_dimensions` in evaluation contracts.

### What to Change in CONTEXT.md

Add to **Decisions**:
- Multi-agent ground truth uses additive `debate_expectations` section alongside existing `findings` schema
- Four outcome types: confirmed, refuted, disputed, escalated
- Defender position taxonomy: concede, partial_mitigation, full_mitigation, challenge_preconditions
- Anti-rubber-stamp checks are explicit strings that map to evaluation contract capability checks

### Plans Affected

1. **Prestep P-2** (Multi-Agent Ground Truth Format Design): This gap resolution IS Prestep P-2. The schema above is the deliverable. Implementation task: add `debate_expectations` to 2-3 corpus projects as proof-of-concept.

2. **Plan C** (Scale Workflow Tests): The orchestrator debate evaluation contract (`orchestrator-debate.json`) should be extended with capability checks derived from the `anti_rubber_stamp_checks` in the ground truth. Specifically:
   - Add `defender-engages-substantively` check (grader_type: model)
   - Add `verifier-runs-independent-queries` check (grader_type: code)
   - Add `rebuttal-introduces-novelty` check (grader_type: model)

3. **Evaluation contract schema** (`.vrs/testing/schemas/evaluation_contract.schema.json`): No schema change needed -- the existing schema supports the capability checks and reasoning dimensions required. The new checks are instances of the existing schema, not extensions.

## Sources

### Primary (HIGH confidence)
- D3 framework: arXiv:2410.04663v4 (Harrasse et al., 2024) -- scoring dimensions, rubber-stamping detection
- Safety Evaluation MAJ: arXiv:2511.06396v1 -- critic/defender/judge structure, round optimization
- ColMAD: ICLR 2026 submission (OpenReview W6qSjvTQMW) -- debate hacking detection, collaborative framing
- Existing codebase: `debate.md`, `orchestrator-debate.json`, `UC-DEB-*` scenarios

### Secondary (MEDIUM-HIGH confidence)
- Code4rena docs: docs.code4rena.com/awarding -- multi-reviewer finding quality scoring
- Sherlock docs: docs.sherlock.xyz -- multi-stage judging pipeline
- MAD meta-analysis: Zhang et al., arXiv:2502.08788 -- model heterogeneity as consensus quality signal

### Tertiary (MEDIUM confidence)
- Du et al., ICML 2024 (arXiv:2305.14325) -- multiagent debate for factuality, convergence patterns
- M-MAD (ACL 2025): multidimensional debate for evaluation -- dimension decomposition pattern
