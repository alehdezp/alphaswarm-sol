# Guide Pattern Discovery

**Purpose:** Define when and how to trigger novel pattern discovery from anomalies.

## Trigger Conditions (Required)

Discovery must trigger when any of the following occur:

1. **Evidence Contradiction**
A finding’s graph evidence does not match any existing pattern signature.

2. **False-Positive Wipeout**
All candidate findings are suppressed as false positives for a scenario.

3. **Novel Sequencing**
Cross-function paths reveal operation ordering not covered by existing patterns.

## Discovery Log

Use `.planning/testing/templates/PATTERN-DISCOVERY-LOG.md` to capture candidate patterns with evidence and routing.

## Routing Decision

- Route to `/pattern-forge` for new patterns.
- Route to `/vrs-refine` for improvements to existing patterns.

## Evidence Requirements

- Candidate must include graph node IDs and transcript reference.
- Trigger condition must be recorded explicitly.

## Related Docs

- `.planning/testing/templates/PATTERN-DISCOVERY-LOG.md`
- `docs/guides/patterns-basics.md`
