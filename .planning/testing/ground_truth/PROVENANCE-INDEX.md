# Ground Truth Provenance Index

**Purpose:** Canonical registry of external ground truth sources used for validation.

## Requirements

- Every validation or E2E scenario must reference an entry here via `ground_truth_ref`.
- Entries must include enough data to reproduce the ground truth fetch.
- Do not store the ground truth data in the subject Claude session.

## Entry Template

```yaml
- id: pending
  source: "<Code4rena | Sherlock | Immunefi | Trail of Bits | SmartBugs>"
  url: "<external report or corpus URL>"
  contest_id: "<optional contest ID>"
  commit: "<commit hash or tag>"
  artifact: "<file path or dataset identifier>"
  checksum: "<sha256>"
  notes: "<scope, known vulnerabilities, expected findings>"
```

## Entries

- id: pending
  source: "TBD"
  url: "TBD"
  contest_id: "TBD"
  commit: "TBD"
  artifact: "TBD"
  checksum: "TBD"
  notes: "Placeholder entry. Replace with real provenance before any validation claim."
