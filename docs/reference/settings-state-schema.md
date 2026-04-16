# Settings And State Schema

**Purpose:** Define the required schema for `.vrs/settings.yaml` and `.vrs/state/current.yaml`.

These files are the runtime contract between the user, the orchestrator, and testing.

---

## `.vrs/settings.yaml` (User Config)

**Required behavior:**
- Controls tool execution, tier gating, and context generation.
- Always read at audit start.
- Validation failures must stop the audit with explicit guidance.

**Minimum schema (required fields):**

```yaml
version: 1
tools:
  enabled: ["slither", "aderyn"]
tiers:
  enabled: ["A", "B", "C"]
context:
  protocol:
    enabled: true
  economic:
    enabled: false
audit:
  fail_fast: true
```

**Recommended fields:**
- `paths.contracts` (override default contracts path)
- `paths.docs` (override docs path)
- `output.format` (json, markdown)
- `gates.tier_c_requires_context` (boolean)

---

## `.vrs/state/current.yaml` (Auto‑Updated)

**Required behavior:**
- Written at each stage transition.
- Provides resume guidance for users and orchestrators.

**Minimum schema (required fields):**

```yaml
version: 1
stage:
  current: "graph_build"
  completed: ["health_check", "init"]
  next: "context_generation"
tasks:
  pending: ["task-001", "task-002"]
  completed: ["task-000"]
tools:
  available: ["slither", "aderyn"]
settings:
  hash: "sha256:..."
```

**Recommended fields:**
- `stage.started_at` and `stage.updated_at`
- `artifacts.transcripts[]`
- `artifacts.reports[]`
- `artifacts.evidence_packs[]`
- `resume.command`

**Status line mapping (optional):**
- Mirror `stage.current`, `stage.completed[]`, and `stage.next` into `.claude/data/sessions/{session_id}.json` extras.
- Use the same keys for UI consistency.

---

## Validation Rules

- Audit must halt if settings are missing or invalid.
- Tier C must not run if `context.economic.enabled` is false and Tier C requires context.
- State must always reflect the latest stage and next step.
