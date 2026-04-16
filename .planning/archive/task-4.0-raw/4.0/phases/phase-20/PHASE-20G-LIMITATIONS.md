# Phase 20.G: Limitations and Improvement Backlog

**Goal:** Produce the final real-world readiness dossier with explicit limitations and prioritized improvements.

---

## G.1 Limitations Log

Record every limitation in `task/4.0/phases/phase-20/artifacts/LIMITATIONS.md`:

```
- id: LIM-001
  category: <coverage|accuracy|usability|performance|agentic>
  severity: <blocker|critical|major|minor>
  description: <short>
  reproduction: <steps>
  root_cause: <analysis>
  evidence: <logs/outputs>
```

---

## G.2 Improvement Backlog

Record improvements in `task/4.0/phases/phase-20/artifacts/IMPROVEMENT_BACKLOG.md`:

```
- id: IMP-001
  priority: <p0|p1|p2|p3>
  related_limitation: LIM-001
  fix_summary: <short>
  effort: <low|medium|high>
  expected_impact: <summary>
```

---

## G.3 Final Dossier

The final dossier must answer:

- Can BSKG be used for real audits today?
- What classes of bugs are still unreliable?
- How much human intervention is still required?
- What is the exact improvement plan?

Include a link to `PILLAR_COVERAGE.md` and summarize any failed pillars.
