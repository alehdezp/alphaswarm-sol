# Guide Ground Truth

**Purpose:** Ensure validation uses external, provenance-backed sources.

## Accepted Sources

- Code4rena reports
- Sherlock contests
- Immunefi disclosures
- Trail of Bits audits
- SmartBugs curated corpus

## Required Provenance Fields

- Source name
- URL or contest ID
- Commit hash or file path when applicable
- Severity and location details
- Stable reference ID (for `ground_truth_ref` in scenario manifest)

## Prohibited Practices

- No self-generated ground truth.
- No hardcoded `is_true_positive` flags in code.
- No hidden mock results.

## Enforcement Checklist (Required)

- Any validation or E2E scenario **must** set `requires_ground_truth: true`.
- Scenario entries **must** include `ground_truth_ref` that points to a provenance entry.
- Evidence packs for validation runs **must** include `ground_truth.json` and the `ground_truth_ref`.
- If provenance is missing, the scenario is **blocked** and the run is invalid.
- Canonical provenance registry: ` .planning/testing/ground_truth/PROVENANCE-INDEX.md `.

## Isolation Requirement

- The **subject** Claude Code session must not access ground truth files.
- Only the evaluator or controller may use ground truth for comparison.
