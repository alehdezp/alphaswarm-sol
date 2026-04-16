# Phase 20.H: Human Shadow Audits

**Goal:** Compare BSKG outputs against human auditor reports for the same protocols.

---

## H.1 Scope

- 3 to 5 real-world protocols
- At least one protocol with known incident history
- At least one protocol with complex governance or business logic

---

## H.2 Shadow Audit Workflow

1. Collect human audit report and findings.
2. Run BSKG agent on the same codebase and scope.
3. Compare outputs against human findings.
4. Record deltas: missing, extra, or mismatched findings.

---

## H.3 Evaluation Dimensions

- Coverage: did BSKG find the same issues?
- Signal quality: did evidence match?
- Explanation quality: did remediation align?
- False positives: did BSKG report benign issues?

**Behavior-first requirement:** compare behavioral signatures and semantic ops, not names.

---

## H.4 Output Template

Store in `task/4.0/phases/phase-20/artifacts/HUMAN_SHADOW.md`:

```
- protocol: <name>
  auditor_report: <url>
  vkg_findings: <count>
  human_findings: <count>
  overlap: <count>
  missed: <count>
  extra: <count>
  signature_overlap: <high|medium|low>
  semantic_ops_overlap: <high|medium|low>
  notes: <summary>
```

---

## H.5 Acceptance Criteria

- >= 85% overlap with human findings for high/critical issues
- <= 10% false-positive rate on safe findings
