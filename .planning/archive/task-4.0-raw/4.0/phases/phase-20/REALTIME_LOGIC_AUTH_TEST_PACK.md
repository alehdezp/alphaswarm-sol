# Real-Time Logic/Auth Test Pack (Offline VKG-Only)

**Purpose:** Stress-test BSKG on less-obvious logic and authorization flaws
using an offline-only subagent with strict time budgets.

**Scope:** Improper access control, permission drift, business-logic mismatch,
state machine bypass, and multi-role invariants.

---

## 0. Offline-Only Rules

- No network access, no external docs.
- Use only BSKG artifacts (graph, patterns, labels, beads).
- Remove `.git` before analysis to avoid patch history.
- If a repo is already patched, pin a vulnerable commit and snapshot.

## 0.1 Ground-Truth and Blinding Split (Required)

To keep tests realistic and unbiased:

- Run a **Researcher pass** (LLM + network allowed) to gather public findings
  for each repo and map them to a pinned snapshot.
- Store full details in
  `task/4.0/phases/phase-20/artifacts/GROUND_TRUTH.md` and keep it sealed.
- Produce a **Redacted Scope Brief** for the offline agent:
  - repo + snapshot
  - optional category hints only (auth/logic)
  - **no** vuln names, function names, or report quotes
- The offline agent must never see ground truth or report text.

**Sanitize step (required):**
```
rm -rf <repo>/.git
```

---

## 1. Real-Time Budgets

### 1.1 Mode Selection

- **Rapid (R)**: 25 min cap, Tier A only, 1 hypothesis max
- **Standard (S)**: 43 min cap (default), Tier A + selective Tier B
- **Deep (D)**: 60 min cap, full Tier A + Tier B + debate

If not specified, use **Standard (S)**.

### 1.2 Stage Budgets (Standard)

| Phase | Target Time | Hard Limit | Notes |
|------|-------------|-----------|-------|
| Graph build | 8 min | 12 min | Must capture node/edge counts |
| Candidate scan | 5 min | 8 min | Top-N candidates only |
| Pattern sweep | 6 min | 10 min | Tier A only unless needed |
| Label sweep | 6 min | 10 min | Only if overlay enabled |
| Hypotheses + debate | 10 min | 15 min | Max 3 hypotheses |
| Report write-up | 8 min | 12 min | Structured only |

**Total target:** 43 min per repo
**Total hard cap:** 67 min per repo

---

### 1.3 Auto-Skip Rules (Time Optimization)

- Skip label sweep if Tier A already confirms a finding with strong evidence.
- Skip debate if evidence is unambiguous and matches a known ground-truth item.
- Stop after 3 failed hypotheses to preserve time budget.
- If graph build exceeds hard limit, terminate and log failure.

## 2. Test Case Definition Template

**Note:** `expected_failures` and `expected_signals` are evaluator-only and
must not be exposed to the offline agent.

```
- case_id: LA-###
  repo: <url>
  snapshot: <commit hash/tag>
  scope: <contract paths>
  vuln_type: <improper-auth|logic-mismatch|state-machine|permission-drift>
  severity: <medium|high|critical>
  scope_hint_level: <none|category|module>
  scope_brief: <redacted prompt for offline agent>
  expected_failures:
    - <one-liner from audit report>
  expected_signals:
    - graph_props: [<prop>]
    - labels: [<label>]
    - behavioral_signature: <sig>
  forbidden_shortcuts:
    - "Do not use git history"
    - "Do not use external docs"
  success_criteria:
    - detection: true
    - evidence_linked: true
    - remediation_quality: >= medium
```

---

## 3. Mandatory Run Sequence

0. **Researcher pass (outside offline)**
   - Build ground-truth roster from public reports
   - Seal in `GROUND_TRUTH.md`
   - Create redacted scope brief for offline agent

1. **Prepare snapshot**
   - Checkout vulnerable ref and delete `.git`
   - Record file list + line counts

2. **Build KG**
   - `alphaswarm build-kg <path>`
   - Record `nodes/edges` and build time

3. **Blind candidate scan**
   - No hints; enumerate candidates across the full graph
   - Focus on auth + logic signals:
     - `public_wrapper_without_access_gate`
     - `writes_privileged_state`
     - `CALLS_UNTRUSTED` + `WRITES_USER_BALANCE`
     - `REQUIRES_STATE:*` missing

4. **Tier A sweep**
   - Run baseline patterns against candidates

5. **Scoped sweep (optional)**
   - Use category hints only, if provided
   - Run targeted patterns and PPR-style subgraph retrieval

6. **Tier B sweep**
   - Run label-aware patterns (if overlay enabled)

7. **Outside-the-box reasoning**
   - Test 3 hypotheses max
   - Run attacker/defender/verifier roles if ambiguous

8. **Package evidence**
   - Provide behavioral signatures + semantic ops

9. **Score the run**
   - Precision estimate
   - Token budget estimate
   - Time budget compliance

---

## 4. Logic/Auth Heuristic Pack

Use these to generate hypotheses:

- Role confusion (same modifier used for multiple privilege levels)
- Indirect permission grant via state variable writes
- Upgrade gate bypass via unguarded initializer
- Emergency function callable via public wrapper
- Privileged action triggered by user-controlled parameter
- State transition without guard (paused/active mismatch)
- Multi-contract authority drift (A checks role, B doesn’t)
- Governance delay bypass (no timelock on critical paths)

---

## 5. Required Output Schema

```
run_summary:
  repo: <name>
  snapshot: <hash>
  total_findings: <int>
  confirmed: <int>
  rejected: <int>
  run_mode: <blind|scoped>
  scope_hint_level: <none|category|module>
  time_used_minutes: <int>
  budget_pass: true|false

findings:
  - id: F-###
    severity: <critical|high|medium>
    category: <auth|logic|state>
    node_id: <function:...>
    evidence_props: [<prop>]
    labels: [<label>]
    behavioral_signature: <sig>
    rationale: <short>
    remediation: <short>
    confidence: <0.0-1.0>

false_positive_controls:
  - node_id: <function:...>
    reason: <why ruled out>

time_breakdown:
  build: <min>
  scan: <min>
  patterns: <min>
  reasoning: <min>
  report: <min>
```

---

## 6. Scoring Rubric

| Metric | Target | Fail Trigger |
|--------|--------|--------------|
| Logic/auth precision | >= 0.80 | < 0.65 |
| High/critical recall | >= 0.60 | < 0.40 |
| Time budget adherence | 90% of runs | < 70% |
| Evidence completeness | 100% | Any missing evidence |

---

## 7. Recommended Repo Shortlist (Pin Vulnerable Snapshot)

Use the corpus manifest to pick a subset. Prioritize:

- `taiko-mono` (audit-backed logic/auth issues)
- `reserve-protocol` (audit-backed logic issues)
- `alchemix-v2-foundry` (contest findings on permissions/logic)
- DVDeFi latest challenges (logic-heavy scenarios)
- SmartBugs curated (logic + access control)

---

## 8. Seed Cases (Fill With Ground Truth)

Use these as initial real-world cases once you pin the vulnerable snapshot.
All examples below are from 2025 audit reports with explicit high-risk findings.

```
- case_id: LA-101
  repo: c4-2025-04-virtuals
  source: https://code4rena.com/reports/2025-04-virtuals-protocol
  vuln_type: improper-auth
  severity: high
  scope_hint_level: category
  scope_brief: "Review auth/logic paths without report details"
  expected_failures: <sealed in GROUND_TRUTH.md>

- case_id: LA-102
  repo: c4-2025-05-blackhole
  source: https://code4rena.com/reports/2025-05-blackhole
  vuln_type: improper-auth
  severity: high
  scope_hint_level: category
  scope_brief: "Review auth/logic paths without report details"
  expected_failures: <sealed in GROUND_TRUTH.md>

- case_id: LA-103
  repo: c4-2025-10-sequence
  source: https://code4rena.com/reports/2025-10-sequence
  vuln_type: improper-auth
  severity: high
  scope_hint_level: category
  scope_brief: "Review auth/logic paths without report details"
  expected_failures: <sealed in GROUND_TRUTH.md>

- case_id: LA-104
  repo: c4-2025-10-hybra
  source: https://code4rena.com/reports/2025-10-hybra-finance
  vuln_type: logic-mismatch
  severity: high
  scope_hint_level: category
  scope_brief: "Review auth/logic paths without report details"
  expected_failures: <sealed in GROUND_TRUTH.md>

- case_id: LA-105
  repo: c4-2025-06-panoptic
  source: https://code4rena.com/reports/2025-06-panoptic-hypovault
  vuln_type: logic-mismatch
  severity: high
  scope_hint_level: category
  scope_brief: "Review auth/logic paths without report details"
  expected_failures: <sealed in GROUND_TRUTH.md>
```

**Note:** These are seeds; copy into the corpus manifest with pinned commits.

Optional secondary seeds (if you need more):

- alchemix-v2-foundry + Past Audit Competitions
- pashov-audits + target protocol repo
- taiko-mono + in-repo audit report

---

## 9. Stop Conditions

Stop the run if any of the following occur:

- Time budget exceeds hard limit
- Evidence is missing for any finding
- Graph build fails or nodes missing critical functions
- Pattern pack mismatch with schema
- Any leak of ground-truth or report details into the offline run

Create a remediation task immediately if any stop condition triggers.
