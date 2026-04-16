# Graph Integrity Checks

**Purpose:** Define the integrity contract for BSKG graph artifacts used in audit workflows.

## Schema Checks (Required)

A graph build is only valid if it passes **all** schema checks:

- Graph file is valid JSON or TOON (no parse errors).
- Top-level keys exist: `nodes`, `edges`, `metadata`.
- `metadata` includes `schema_version`, `build_hash`, `timestamp`, and `scope`.
- Each node entry includes: `id`, `type`, and at least one location field (`file`, `line`, or `source_ref`).
- Each edge entry includes: `source`, `target`, `type`.

If any check fails, the graph integrity check **fails** and the workflow must halt.

## Node/Edge Count Ranges (Required)

Integrity checks MUST enforce explicit count ranges:

- **Baseline required:** record `node_count` and `edge_count` from the last known-good build for the same scope.
- **Allowed variance:** `node_count` must be within **±30%** of baseline; `edge_count` must be within **±40%** of baseline.
- **Absolute minimums:** `node_count >= 1`, `edge_count >= 0`.

If counts fall outside the allowed ranges, integrity check **fails**.

## Diff Policy (Required)

Define acceptable vs. unacceptable changes between graph builds.

**Allowed (no action):**
- `build_hash` and `timestamp` changes.
- Node/edge additions or removals **within range**.
- Metadata updates for tool versions.

**Investigate (manual review required):**
- New node types or edge types not present in the baseline.
- Node/edge count drift near the range limits.
- Large ID churn (>20% node IDs changed) without source changes.

**Fail (hard stop):**
- Schema violations or missing required fields.
- `schema_version` change without a migration note.
- `build_hash` mismatch vs. proof token `graph_hash`.
- Node/edge counts outside the required ranges.

## Evidence Requirement

Graph-using workflows MUST include a `stage.graph_integrity` proof token in the evidence pack.
