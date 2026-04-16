# Subagent Offline Security Assessment Template (VKG-Only)

**Purpose:** Execute a full security assessment using only BSKG artifacts
(graph, patterns, beads, labels). No external browsing or prior knowledge.

**Audience:** Subagents operating offline with strict context budgets.

---

## 0. Hard Constraints

- No network access, no external docs, no web search.
- Use only local BSKG artifacts and pattern packs.
- Every claim must point to BSKG evidence (nodes, edges, properties).
- Minimize tokens: prefer labels over prose, prefer structured output.
- Remove `.git` before analysis to avoid patch history leakage.
- Do not access ground truth or audit reports; if prior knowledge surfaces,
  flag it and ignore it in conclusions.

---

## 1. Run Metadata (Fill In)

```
run_id: <A-###>
agent_id: <agent-name>
date_utc: <YYYY-MM-DD>
project: <protocol/repo>
scope: <contracts/files/modules>
corpus_ref: <CORPUS_MANIFEST entry>
kg_build_commit: <git hash>
kg_builder_version: <version>
pattern_pack_version: <version>
label_overlay_status: <enabled|disabled>
context_budget_tokens: <limit>
offline_mode: <true|false>
git_history_removed: <true|false>
blind_mode: <true|false>
scope_hint_level: <none|category|module>
ground_truth_visible: <false>
```

---

## 2. Inputs (Required Artifacts)

- Graph: `graphs/<project>/graph.json` or build output
- Pattern packs: `patterns/` (core + semantic)
- Label overlay store: `.vrs/learning/overlay.jsonl` (if enabled)
- Beads log: `task/4.0/phases/phase-20/artifacts/BEAD_LOG.md`
- Redacted scope brief (if provided): local note with repo + scope only
- Ground truth (evaluator only): `task/4.0/phases/phase-20/artifacts/GROUND_TRUTH.md`

---

## 3. Allowed Tools (Local Only)

- `alphaswarm build-kg <path>`
- `alphaswarm query "pattern:<id>"`
- `alphaswarm learn overlay status|export`
- `alphaswarm learn events export` (if needed)

No external tooling or network calls.

---

## 3b. Orchestration Roles (Offline)

Run these roles in order. Each role produces a structured output
that the next role consumes.

1. **Graph Scout**
   - Build KG and extract top candidates
   - Output: `candidates` list with risk signals

2. **Pattern Runner**
   - Execute Tier A patterns on candidates
   - Output: `pattern_matches`

3. **Logic Analyst**
   - Construct behavioral signatures and hypotheses
   - Output: `behavioral_signatures`, `hypotheses`

4. **Verifier**
   - Challenge hypotheses, check false positives
   - Output: `findings` with evidence + confidence

If any role fails, stop and log a remediation task.

---

## 4. Token Budget and Context Guardrails

- Hard budget per context slice: < 6,000 tokens
- Prefer:
  - Labels + properties over raw code
  - Function-level slices over whole-contract dumps
- Exclude unrelated categories (reentrancy context for access-control tasks, etc.)
- If context overflows, truncate in this order:
  1) PPR-expanded neighbors
  2) Long code blocks
  3) Non-essential modifiers

---

## 5. Preflight Checklist

- [ ] Graph built successfully and cached
- [ ] Node count and edge count recorded
- [ ] Pattern packs loaded
- [ ] Label overlay enabled (if required)
- [ ] Evidence packet schema version recorded
- [ ] Scope confirmed and bounded
- [ ] Known safe set identified (for FP control)
- [ ] `.git` removed from target repo (offline snapshot)
- [ ] Blinding confirmed (no access to ground truth or reports)

**Preflight Output:**
```
preflight:
  graph_nodes: <int>
  graph_edges: <int>
  missing_sources: <count>
  overlay_labels: <count>
  patterns_loaded: <count>
```

---

## 6. Assessment Pipeline (Mandatory Order)

### Stage 1: Candidate Enumeration

Goal: Identify high-risk functions/variables for focused analysis.

Signals (examples):
- `has_external_calls` + `writes_state`
- `writes_privileged_state`
- `public_wrapper_without_access_gate`
- `reads_oracle_price` + `writes_state`

If `scope_hint_level` is set, restrict deep dives to hinted categories,
but still run a baseline Tier A sweep across all candidates.

Output:
```
candidates:
  - node_id: <function:...>
    risk_signals: [<signal1>, <signal2>]
    score: <int>
```

### Stage 2: Tier A Pattern Sweep

Run baseline patterns against candidate set.
Record matches, evidence, and any overlaps.

Output:
```
pattern_matches:
  - pattern_id: <id>
    nodes: [<node_id>]
    evidence: <graph props>
```

### Stage 3: Label-Aware Sweep (Tier B)

If label overlay enabled, run label-aware patterns and note deltas.

Output:
```
label_matches:
  - pattern_id: <id>
    labels_used: [<label>]
    nodes: [<node_id>]
```

### Stage 4: Behavioral Reasoning Pass

Construct behavioral signatures from graph signals.
Verify sequence constraints (e.g., read -> external call -> write).

Output:
```
behavioral_signatures:
  - node_id: <function:...>
    signature: <R:bal->X:out->W:bal>
    ops: [<op1>, <op2>]
```

### Stage 5: Outside-the-Box Hypotheses

Generate hypotheses not covered by patterns:
- Permission drift: roles can do more than intended
- Parameterized authority: attacker controls a target address
- Invariant breaks: total supply vs balances mismatch
- State-machine bypass: missing state guards
- Cross-contract assumptions: untrusted callbacks in trusted flow

Record hypotheses and disconfirming evidence.

Output:
```
hypotheses:
  - hypothesis_id: H-###
    description: <short>
    evidence_for: [<node_id>]
    evidence_against: [<node_id>]
    status: <confirmed|rejected|needs_data>
```

### Stage 6: Multi-Agent Role Debate

Use three roles for complex cases:
- Attacker: construct exploit path
- Defender: find mitigations or missing preconditions
- Verifier: arbitrate using evidence

Output:
```
role_debate:
  - finding_id: F-###
    attacker_claim: <one paragraph>
    defender_claim: <one paragraph>
    verifier_verdict: <confirm|reject|uncertain>
```

### Stage 7: Evidence Packaging

Every finding must cite:
- graph nodes
- properties or labels
- behavior signature

Output:
```
findings:
  - id: F-###
    title: <short>
    category: <access_control|reentrancy|oracle|dos|logic>
    severity: <critical|high|medium|low>
    node_id: <function:...>
    evidence_nodes: [<node_id>]
    evidence_props: [<prop>]
    labels: [<label>]
    behavioral_signature: <sig>
    exploit_path: <short>
    remediation: <short>
    confidence: <0.0-1.0>
    false_positive_checks: <what was ruled out>
```

### Stage 8: Task and Label Updates

If new structural knowledge is found, propose label updates.
If findings affect other tasks, propose task updates.

Output:
```
label_updates:
  - node_id: <...>
    label: <...>
    confidence: <...>
    evidence: <short>

task_updates:
  - action: <create|reprioritize|deprioritize>
    target: <task id/filter>
    reason: <short>
```

---

## 7. Out-of-the-Box Heuristic Checklist

Use these prompts during Stage 5:

- Does any public function mutate privileged state without access checks?
- Can any function accept a target address that later receives value or control?
- Are state transitions guarded consistently across all entry points?
- Are invariants encoded only in comments, not checks?
- Are external calls followed by state writes without explicit guards?
- Are token approvals or transfers done on user-controlled addresses?
- Are admin/owner functions callable indirectly via wrapper functions?
- Are upgrade hooks or delegatecalls reachable by untrusted callers?
- Are loops bounded by user-controlled inputs without caps?
- Do callback handlers assume the caller is trusted without verification?

---

## 8. Output Summary Template

```
summary:
  scope: <contracts reviewed>
  total_candidates: <int>
  pattern_matches: <int>
  findings_confirmed: <int>
  findings_rejected: <int>
  hypotheses_open: <int>
  token_usage_estimate: <int>
  leak_check: pass|fail
  major_risks: [<short list>]
  missing_data: [<short list>]
```

---

## 9. Quality Gates (Must Pass)

- [ ] Every finding has evidence nodes and properties
- [ ] No finding relies on unstated external knowledge
- [ ] Each severity is justified by impact path
- [ ] At least one negative check per finding
- [ ] Token budget respected

---

## 10. Retrospective and Metrics

```
retrospective:
  precision_estimate: <0.0-1.0>
  recall_estimate: <0.0-1.0>
  top_false_positive_cause: <short>
  top_false_negative_cause: <short>
  label_quality_issues: <short>
  next_actions: [<short list>]
```

---

## 11. Failure Modes (If Triggered)

- Missing graph nodes or broken edges
- Pattern pack mismatch with schema
- Label overlay noise or drift
- Excessive context consumption

If any failure mode occurs, stop and write a remediation task.
