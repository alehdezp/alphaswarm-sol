# Phase 20.D: End-to-End Vulnerability Validation

**Goal:** Validate that BSKG can detect and explain real vulnerabilities end-to-end with minimal context.

---

## D.0 Blind Ground-Truth Protocol (Required)

This phase must separate **ground-truth assembly** from **analysis execution**
to prevent leakage and bias.

1. Run a **Researcher pass** (LLM allowed, network allowed) to collect public
   reports for each repo in the corpus and build a vulnerability roster.
2. Map each finding to a pinned snapshot, contract, function, and category.
3. Store the full roster in `task/4.0/phases/phase-20/artifacts/GROUND_TRUTH.md`
   and mark it **sealed**.
4. Produce a **Redacted Scope Brief** for analysis agents:
   - repo + snapshot
   - allowed contract paths
   - optional category hints only (auth/logic/oracle/etc.)
   - **no** vuln names, function names, or report quotes
5. Analysis agents must not access ground truth or reports. If prior knowledge
   exists, it must be ignored and never cited.

---

## D.1 Two-Pass Test Workflow (Blind -> Scoped)

1. Receive redacted scope brief and confirm blinding.
2. Build KG for the protocol and record node/edge counts.
3. **Blind pass (open-world)**:
   - Enumerate candidates across the full graph.
   - Run Tier A patterns across candidates (all categories).
   - Capture initial findings + evidence packets.
4. **Scoped pass (optional)**:
   - Use category-level hints only (if provided).
   - Run targeted patterns and PPR-style subgraph retrieval on candidates.
   - Run Tier B verification only on ambiguous candidates.
5. Compare results to ground truth (evaluator only).
6. Validate explanation and remediation guidance.
7. Record bead lifecycle and task updates.

---

## D.2 Subgraph-First Execution Rules (Efficiency)

- Candidate enumeration must precede any pattern sweep.
- Candidate set cap: `min(200, 10% of functions)` per repo.
- PPR expansion cap: `min(120, 5% of functions)` if evidence is weak.
- Tier A patterns run on all candidates; Tier B only on hinted categories or
  ambiguous candidates.
- Do not run full-graph Tier B sweeps. If recall is low, expand candidates
  once and log the reason.

---

## D.3 Per-Vulnerability Protocol (Evaluator Only)

For each ground truth item:
- Track whether it was found in the blind pass, scoped pass, or both.
- Run query for the specific vuln pattern or subcategory.
- Confirm detection signals align with ground truth.
- Verify minimal context (<= 3,000 tokens).
- Validate remediation steps are correct and safe.
- Record false positives on safe samples.

**Behavior-first requirement:** Evidence must include semantic operations and behavioral signatures from PHILOSOPHY.md.
**Context requirement:** Evidence should be delivered via minimal-context packaging (PPR/TOON when available).

---

## D.4 Required Negative Controls

- Safe samples per protocol (at least 10)
- Contracts with similar patterns but safe logic
- False-positive trap cases (same tokens, safe ordering)

---

## D.5 Evidence Packet Requirements

Each finding must include:

- Behavioral signature
- Semantic operations list
- Graph signals and evidence locations
- Bead ID and verdict
- Retrieval slice notes (PPR expansion used or not)

Missing evidence packets automatically fail the test case.

Record bead lifecycle in `task/4.0/phases/phase-20/artifacts/BEAD_LOG.md`.

---

## D.6 Required Output

Store in `task/4.0/phases/phase-20/artifacts/END_TO_END_RESULTS.md`:

```
- id: GT-001
  run_mode: blind|scoped
  scope_hint_level: none|category|module
  detected: true|false
  false_positive: true|false
  notes: <why>
  evidence: <key signals>
  evidence_packet: <id>
  bead_id: <id>
  context_tokens: <int>
  remediation_quality: high|medium|low
  candidate_count: <int>
  patterns_run: <int>
  subgraph_nodes: <int>
  time_minutes: <int>
  leak_check: pass|fail
```

---

## D.7 Acceptance Criteria

- Precision >= 90%
- Recall >= 85%
- Context tokens <= 3,000 in 90% of cases
- Remediation quality >= medium for 90% of cases
- Blind-pass recall >= 70%
- Scoped-pass recall >= 85%
- Leakage incidents = 0

---

## D.8 PHILOSOPHY Alignment Checks

- **Two-tier patterns:** validate Tier A vs Tier B behavior separately.
- **Evidence packets:** each finding must link to evidence (code + signals).
- **Beads:** each candidate finding is tracked as a bead with a verdict.
- **PPR-style retrieval:** log any subgraph expansion decisions.

---

## D.9 Tier A vs Tier B Validation Matrix

For each category:

- **Tier A**: strict pattern signals must match without LLM reasoning.
- **Tier B**: exploratory patterns must include LLM verification and evidence packets.

Record tier attribution in `END_TO_END_RESULTS.md`.
