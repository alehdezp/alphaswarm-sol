# Phase 20.J: VulnDocs Field Completeness Audit

**Goal:** Validate that VulnDocs coverage is sufficient for real-world detection, especially for access control and business-logic bugs.

---

## J.1 Scope

- Sample 10 docs per category (minimum)
- Mandatory focus on:
  - access-control
  - logic (business-logic flaws)
  - governance
  - oracle

---

## J.2 Audit Method

For each sampled doc:
- Check all SVR fields are present
- Verify detection guidance is behavior-based (variable-name agnostic)
- Validate that testing guidance is actionable
- Confirm references and source traceability

**PHILOSOPHY alignment:** verify semantic operations and behavioral signatures are present.

Additionally:
- Ensure evidence packets can be constructed from the doc
- Confirm bead-ready content (clear checklist + remediation)

---

## J.3 Output Template

Store in `task/4.0/phases/phase-20/artifacts/VULNDOCS_AUDIT.md`:

```
- doc_id: <category/subcategory>
  missing_fields: [field1, field2]
  detection_quality: high|medium|low
  testing_quality: high|medium|low
  business_context: high|medium|low
  notes: <summary>
```

---

## J.4 Acceptance Criteria

- >= 90% of docs pass SVR field completeness
- Access-control and logic categories must exceed 95% completeness
- No doc should lack detection checklist and testing guidance
