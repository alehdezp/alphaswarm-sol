# GAP-02: EVMbench paper detection-only grading schema details

**Created by:** improve-phase
**Source:** P1-IMP-04
**Priority:** MEDIUM
**Status:** resolved
**depends_on:** []

## Question

What detection-only grading schema does EVMbench use? Specifically: (a) binary detect/miss encoding, (b) partial detection handling, (c) contract-level vs vulnerability-level counting methodology.

## Context

Plan 05 needs to produce schemas for 3.1c that capture empirical data formats. EVMbench is the closest prior art for detection-focused evaluation. Understanding their schema informs whether we adopt, adapt, or create our own format. Only detection fields are relevant — patch/exploit fields are deferred to Phase 5.

## Research Approach

- Search for "EVMbench" paper or documentation via Exa
- Look for their grading/scoring methodology
- Focus on detection-only fields, exclude patch/exploit metrics
- If paper not found, search for similar vulnerability detection benchmarks

## Findings

**Confidence: HIGH** — derived from EVMbench paper analysis (OpenAI + Paradigm, 2025).

**Source:** EVMbench paper (arxiv/project page), supplementary materials.

### EVMbench Detection Schema

1. **Binary detect/miss encoding:** Yes — each vulnerability instance is scored as detected (1) or missed (0). No partial credit at the detection level.

2. **Partial detection handling:** Uses an **LLM judge** (GPT-5 in their case) for semantic equivalence. When an agent's description doesn't exactly match the ground truth label but describes the same vulnerability, the LLM judge determines if it's a match. This handles naming differences (e.g., "reentrancy" vs "callback vulnerability").

3. **Counting methodology:** **Per-vulnerability**, not per-contract. Each contract may contain multiple vulnerabilities, each scored independently. A contract with 3 vulns where 2 are found scores 2/3 at the vulnerability level.

4. **Primary metric:** **Recall** (detection rate) — what fraction of known vulnerabilities were found. No precision penalty in the primary metric (they note FPs separately but don't penalize recall score).

5. **No severity weighting:** All vulnerabilities count equally in their primary metric. Severity is metadata, not a scoring multiplier.

### Comparison to VRS Needs

| Aspect | EVMbench | VRS Sprint Needs |
|--------|----------|-----------------|
| Detection encoding | Binary per-vuln | Binary per-vuln (adopt) |
| Partial match | LLM judge | LLM judge or manual (adapt) |
| Primary metric | Recall only | Recall + precision (extend) |
| Severity weight | None | Optional (defer) |
| Counting | Per-vulnerability | Per-vulnerability (adopt) |

## Recommendation

**Do X:** Adopt EVMbench's per-vulnerability binary detection encoding for Phase 3.1e experiments. Extend with precision tracking (EVMbench omits this, but VRS needs FP measurement).

**Minimal VRS detection schema:**
```yaml
detection_result:
  vulnerability_id: str        # ground truth ID
  detected: bool               # binary detect/miss
  match_method: enum           # exact | semantic_judge | partial
  agent_description: str       # what the agent reported
  false_positive: bool         # finding with no ground truth match
  confidence: float            # agent's stated confidence (0-1)
```

**CONTEXT.md changes:** Update Plan 05 to reference EVMbench schema as prior art. Note that VRS extends it with `false_positive` field and `confidence` (EVMbench lacks both).

**Affected plans:** Plan 05 (schema design), Plan 04 (if it produces detection data).
