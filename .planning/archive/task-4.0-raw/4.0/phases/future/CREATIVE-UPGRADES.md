# Creative Upgrades (Post-4.0)

**Status:** Tracking Ideas for v4.1/v5.0
**Version:** 2.0 (Improved with brutal review)
**Last Updated:** 2026-01-07
**Source:** CRITIQUE-REMEDIATION.md WS4.3, Critique lines 372-390

---

## REVIEW NOTES

### Issues Fixed in This Version

1. **Pseudocode replaced with real implementation paths** - Actual file locations and functions
2. **Effort estimates revised** - More realistic based on actual complexity
3. **Dependencies fixed** - Correct references to BSKG phases and modules
4. **Acceptance criteria added** - How to know when it's done
5. **Test requirements added** - What tests are needed
6. **Version targeting added** - v4.1 vs v5.0 classification

---

## VERSION TARGETING

| Version | Scope | Timeline |
|---------|-------|----------|
| v4.1 | Quick wins, low complexity, high value | 2-4 weeks after 4.0 |
| v5.0 | Major features, high complexity, research | 6+ months after 4.0 |

---

## 1. Auditor Triage Mode [v4.1]

**Priority:** 1 (Highest)
**Effort:** 4-6 hours (LOW)
**Depends On:** Phase 3 (CLI) complete

### Problem Statement

Auditors face 50+ findings and need fast prioritization. Current output shows everything equally.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/cli/commands/triage.py` - New CLI command
2. `src/true_vkg/findings/ranker.py` - Ranking logic
3. `tests/test_triage.py` - Tests

**Code Location:**

```python
# src/true_vkg/cli/commands/triage.py
import click
from true_vkg.findings.ranker import rank_findings

@click.command()
@click.option('--top', default=5, help='Number of findings to show')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def triage(top: int, format: str):
    """Show top N highest-risk findings with evidence."""
    graph = load_graph()
    findings = get_all_findings(graph)
    ranked = rank_findings(findings, limit=top)
    output_triage_report(ranked, format)
```

```python
# src/true_vkg/findings/ranker.py
from dataclasses import dataclass
from typing import List

@dataclass
class RankedFinding:
    finding: Finding
    risk_score: float
    confidence: float
    evidence_summary: str

def rank_findings(findings: List[Finding], limit: int = 5) -> List[RankedFinding]:
    """Rank findings by risk score and return top N."""
    scored = []
    for f in findings:
        score = calculate_risk_score(f)  # Uses existing risk scoring
        evidence = generate_evidence_summary(f)  # Extract key evidence
        scored.append(RankedFinding(f, score, f.confidence, evidence))

    scored.sort(key=lambda x: x.risk_score, reverse=True)
    return scored[:limit]
```

### Acceptance Criteria

- [ ] `vkg triage` command works
- [ ] Shows top 5 by default, configurable with `--top`
- [ ] Each finding shows: severity, confidence, evidence summary
- [ ] Output is actionable (next steps clear)
- [ ] Tested with 50+ findings scenario

### Test Requirements

- `tests/test_triage.py::test_triage_default` - Top 5 shown
- `tests/test_triage.py::test_triage_custom_count` - Custom --top works
- `tests/test_triage.py::test_triage_empty` - Empty findings handled
- `tests/test_triage.py::test_triage_ranking` - Correct order

---

## 2. Evidence Packs [v4.1]

**Priority:** 2
**Effort:** 8-12 hours (MEDIUM)
**Depends On:** Phase 3 (CLI), Phase 6 (Beads)

### Problem Statement

LLM verification requires reading entire contracts. Evidence packs provide focused context.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/evidence/pack.py` - Evidence pack generation
2. `src/true_vkg/evidence/slicer.py` - Code path slicing
3. `src/true_vkg/evidence/templates.py` - LLM prompt templates
4. `tests/test_evidence_pack.py` - Tests

**Code Location:**

```python
# src/true_vkg/evidence/pack.py
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class EvidencePack:
    finding_id: str
    behavioral_signature: str
    path_slice: List[str]          # Minimal code slice (lines)
    control_flow_mermaid: str       # Mermaid diagram
    properties: Dict[str, Any]      # Relevant node properties
    verification_prompt: str        # Ready-to-use LLM prompt

def generate_evidence_pack(finding: Finding, graph: KnowledgeGraph) -> EvidencePack:
    """Generate focused evidence pack for LLM verification."""
    # Use existing path extraction from src/true_vkg/kg/paths.py
    from true_vkg.kg.paths import extract_minimal_path

    path = extract_minimal_path(graph, finding.function_id)
    slice_lines = extract_code_slice(path)

    # Generate CFG using existing subgraph extraction
    from true_vkg.kg.subgraph import extract_subgraph
    cfg = generate_mermaid_cfg(extract_subgraph(graph, finding.function_id))

    prompt = format_verification_prompt(finding, slice_lines, cfg)

    return EvidencePack(
        finding_id=finding.id,
        behavioral_signature=finding.behavioral_signature,
        path_slice=slice_lines,
        control_flow_mermaid=cfg,
        properties=get_relevant_properties(graph, finding),
        verification_prompt=prompt
    )
```

### Acceptance Criteria

- [ ] `vkg evidence VKG-001` generates pack
- [ ] Pack contains minimal code (< 50 lines typically)
- [ ] Mermaid CFG renders correctly
- [ ] LLM prompt is self-contained
- [ ] Pack size < 2000 tokens typically

### Test Requirements

- `tests/test_evidence_pack.py::test_pack_generation` - Pack created
- `tests/test_evidence_pack.py::test_minimal_slice` - Slice is minimal
- `tests/test_evidence_pack.py::test_mermaid_valid` - CFG syntax valid
- `tests/test_evidence_pack.py::test_prompt_template` - Prompt complete

---

## 3. Signature Diffing [v5.0]

**Priority:** 3
**Effort:** 12-20 hours (HIGH)
**Depends On:** Phase 5 (Validation), Similarity module

### Problem Statement

When exploits are patched, the behavioral signature change reveals the vulnerability pattern.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/diff/signature_diff.py` - Signature comparison
2. `src/true_vkg/diff/pattern_suggestion.py` - Pattern generation
3. `tests/test_signature_diff.py` - Tests

**Code Location:**

```python
# src/true_vkg/diff/signature_diff.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class SignatureDiff:
    function_name: str
    old_signature: str          # e.g., "R:bal->X:out->W:bal"
    new_signature: str          # e.g., "R:bal->W:bal->X:out"
    key_difference: str         # What changed
    pattern_suggestion: Optional['PatternSuggestion']

def diff_signatures(
    exploited_graph: KnowledgeGraph,
    patched_graph: KnowledgeGraph
) -> List[SignatureDiff]:
    """Diff behavioral signatures to suggest patterns."""
    diffs = []

    # Find functions that exist in both
    common_funcs = find_common_functions(exploited_graph, patched_graph)

    for func_id in common_funcs:
        old_sig = get_behavioral_signature(exploited_graph, func_id)
        new_sig = get_behavioral_signature(patched_graph, func_id)

        if old_sig != new_sig:
            diff = analyze_signature_change(old_sig, new_sig)
            pattern = suggest_pattern_from_diff(diff, func_id)
            diffs.append(SignatureDiff(
                function_name=get_function_name(exploited_graph, func_id),
                old_signature=old_sig,
                new_signature=new_sig,
                key_difference=diff.description,
                pattern_suggestion=pattern
            ))

    return diffs
```

### Acceptance Criteria

- [ ] `vkg diff exploited.sol patched.sol` works
- [ ] Identifies changed behavioral signatures
- [ ] Suggests pattern based on diff
- [ ] Works on DVDeFi pre/post exploit examples

### Test Requirements

- `tests/test_signature_diff.py::test_diff_detection` - Diffs found
- `tests/test_signature_diff.py::test_cei_pattern_diff` - CEI fix detected
- `tests/test_signature_diff.py::test_pattern_suggestion` - Pattern suggested
- `tests/test_signature_diff.py::test_no_change` - No false diffs

---

## 4. Behavior Mutation Testing [v5.0]

**Priority:** 4
**Effort:** 16-24 hours (HIGH)
**Depends On:** Phase 1 (Determinism), rename resistance tests

### Problem Statement

If BSKG claims "names lie, behavior doesn't", mutation testing validates this at scale.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/mutation/mutator.py` - Contract mutation
2. `src/true_vkg/mutation/validator.py` - Finding invariance check
3. `tests/test_mutation.py` - Tests

**Code Location:**

```python
# src/true_vkg/mutation/mutator.py
from typing import List
import re

def mutate_contract(source: str) -> List[str]:
    """Generate semantically equivalent variants."""
    variants = []

    # Mutation 1: Rename all functions (except entry points)
    variants.append(rename_internal_functions(source))

    # Mutation 2: Rename all local variables
    variants.append(rename_local_variables(source))

    # Mutation 3: Reorder independent statements (using CFG analysis)
    variants.append(reorder_independent_statements(source))

    # Mutation 4: Change formatting only
    variants.append(normalize_whitespace(source))

    # Mutation 5: Combine multiple mutations
    variants.append(rename_all(rename_local_variables(source)))

    return [v for v in variants if v != source]  # Filter unchanged

def rename_internal_functions(source: str) -> str:
    """Rename internal/private functions to random names."""
    # Parse with Slither to identify internal functions
    # Replace names while preserving call sites
    pass

def reorder_independent_statements(source: str) -> str:
    """Reorder statements that don't have data dependencies."""
    # Use CFG to identify independent statement sequences
    # Swap order preserving semantics
    pass
```

### Acceptance Criteria

- [ ] Generates 5+ variants per contract
- [ ] Variants compile successfully
- [ ] BSKG findings are identical across variants
- [ ] 100% invariance on DVDeFi contracts

### Test Requirements

- `tests/test_mutation.py::test_variants_compile` - All variants compile
- `tests/test_mutation.py::test_finding_invariance` - Same findings
- `tests/test_mutation.py::test_rename_mutation` - Rename works
- `tests/test_mutation.py::test_reorder_mutation` - Reorder works

---

## 5. Semantic Chunking for LLM [v4.1]

**Priority:** 5
**Effort:** 6-10 hours (MEDIUM)
**Depends On:** Phase 9 (Context Optimization)

### Problem Statement

Arbitrary byte-based chunking splits functions mid-line. Semantic chunking respects code structure.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/llm/chunker.py` - Semantic chunking
2. `tests/test_chunker.py` - Tests

**Code Location:**

```python
# src/true_vkg/llm/chunker.py
from dataclasses import dataclass
from typing import List

@dataclass
class SemanticChunk:
    content: str
    chunk_type: str          # "storage", "modifiers", "admin", "user"
    token_count: int
    functions: List[str]     # Function names in this chunk

def semantic_chunk(
    contract_source: str,
    graph: KnowledgeGraph,
    max_tokens: int = 4000
) -> List[SemanticChunk]:
    """Chunk contract by semantic boundaries."""
    chunks = []

    # Group 1: Storage variables
    storage = extract_storage_section(contract_source)
    if count_tokens(storage) <= max_tokens:
        chunks.append(SemanticChunk(storage, "storage", count_tokens(storage), []))

    # Group 2: Modifiers
    modifiers = extract_modifiers(contract_source)
    if count_tokens(modifiers) <= max_tokens:
        chunks.append(SemanticChunk(modifiers, "modifiers", count_tokens(modifiers), []))

    # Group 3: Admin functions (using graph role classification)
    admin_funcs = [f for f in graph.functions if f.role == "admin"]
    admin_code = extract_functions(contract_source, admin_funcs)
    chunks.extend(sub_chunk_if_needed(admin_code, "admin", max_tokens))

    # Group 4: User-facing functions
    user_funcs = [f for f in graph.functions if f.role == "user"]
    user_code = extract_functions(contract_source, user_funcs)
    chunks.extend(sub_chunk_if_needed(user_code, "user", max_tokens))

    return chunks
```

### Acceptance Criteria

- [ ] No function split mid-body
- [ ] Chunks respect logical groupings
- [ ] Each chunk < max_tokens
- [ ] Storage/modifiers kept together

### Test Requirements

- `tests/test_chunker.py::test_no_split_functions` - Functions whole
- `tests/test_chunker.py::test_under_token_limit` - All chunks valid
- `tests/test_chunker.py::test_grouping` - Groups correct

---

## 6. Cross-Audit Pattern Mining [v5.0]

**Priority:** 6 (Lowest for now)
**Effort:** 16-24 hours (HIGH)
**Depends On:** Phase 7 (Learning), Historical audit data

### Problem Statement

Patterns across multiple audits reveal common vulnerability signatures.

### Implementation

**Files to Create/Modify:**

1. `src/true_vkg/mining/pattern_miner.py` - Pattern mining
2. `src/true_vkg/mining/cluster.py` - Finding clustering
3. `tests/test_pattern_mining.py` - Tests

**NOTE:** This requires access to historical audit data. May be v5.0+ feature.

### Acceptance Criteria

- [ ] Mines patterns from 10+ audits
- [ ] Identifies patterns appearing 3+ times
- [ ] Generates pattern YAML suggestions
- [ ] Validates suggested patterns on holdout set

### Test Requirements

- `tests/test_pattern_mining.py::test_cluster_findings` - Clustering works
- `tests/test_pattern_mining.py::test_pattern_suggestion` - Patterns generated
- `tests/test_pattern_mining.py::test_minimum_frequency` - Threshold respected

---

## Prioritization Matrix (Updated)

| Upgrade | Value | Effort | Dependencies Ready | Priority | Version |
|---------|-------|--------|-------------------|----------|---------|
| Auditor Triage Mode | High | Low | Yes (Phase 3) | 1 | v4.1 |
| Evidence Packs | High | Medium | Yes (Phase 3,6) | 2 | v4.1 |
| Semantic Chunking | Medium | Medium | Yes (Phase 9) | 5 | v4.1 |
| Signature Diffing | Medium | High | Partial | 3 | v5.0 |
| Behavior Mutation | Medium | High | Yes (Phase 1) | 4 | v5.0 |
| Cross-Audit Mining | Low | High | No (needs data) | 6 | v5.0+ |

---

## Implementation Tracking

| Upgrade | Target Version | Status | Started | Completed | Notes |
|---------|---------------|--------|---------|-----------|-------|
| Auditor Triage Mode | v4.1 | NOT STARTED | - | - | Quick win |
| Evidence Packs | v4.1 | NOT STARTED | - | - | LLM value |
| Semantic Chunking | v4.1 | NOT STARTED | - | - | Context opt |
| Signature Diffing | v5.0 | NOT STARTED | - | - | Research |
| Behavior Mutation | v5.0 | NOT STARTED | - | - | Validation |
| Cross-Audit Mining | v5.0+ | NOT STARTED | - | - | Needs data |

---

## Getting Started (When Ready)

### For v4.1 features:

1. Complete Phase 16 (Release 4.0)
2. Create v4.1 milestone
3. Start with Auditor Triage (lowest effort, highest impact)
4. Validate on real auditor workflow
5. Add Evidence Packs
6. Add Semantic Chunking

### For v5.0 features:

1. Complete v4.1 and gather feedback
2. Assess which v5.0 features have demand
3. Start with Signature Diffing (builds on existing similarity)
4. Add Mutation Testing (validates philosophy)
5. Cross-Audit Mining only if historical data available

---

*Creative Upgrades Tracker | Version 2.0 | 2026-01-07*
*Improved with concrete implementation paths and realistic estimates*
