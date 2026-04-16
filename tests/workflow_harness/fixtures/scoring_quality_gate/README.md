# Scoring Quality Gate Fixtures

## Provenance

These fixtures were captured from vrs-attacker runs on the SimpleVault.sol contract
(tests/contracts/SimpleVault.sol) on 2026-02-18.

### Good transcript (good_transcript.jsonl)

- **Contract:** SimpleVault.sol (simple reentrancy-vulnerable vault)
- **Agent:** vrs-attacker with standard investigation prompt
- **Run date:** 2026-02-18T14:30:00Z
- **Prompt:** Standard vrs-attacker prompt (graph-first investigation)
- **Behavioral pattern:** Agent builds BSKG first, queries for external-call-before-state-write
  patterns, queries for access control, THEN reads .sol source. Uses BSKG node IDs
  (F-SimpleVault-withdraw, C-SimpleVault-balances) in conclusion.
- **BSKG queries before .sol reads:** 3 (build-kg, pattern query, access control query)

### Bad transcript (bad_transcript.jsonl)

- **Contract:** SimpleVault.sol (same contract)
- **Agent:** vrs-attacker with BSKG-skipping prompt modification
- **Run date:** 2026-02-18T15:00:00Z
- **Prompt modification:** "Skip BSKG analysis. Read the contract source code directly
  and use manual code review to find vulnerabilities."
- **Behavioral pattern:** Agent reads .sol immediately, uses grep for pattern matching,
  never queries BSKG. No BSKG node IDs in conclusion.
- **BSKG queries before .sol reads:** 0

### Expected discrimination

The good transcript should score higher than the bad on:
- GVS dimensions: query_coverage (3 queries vs 0), citation_rate (uses node IDs vs none),
  graph_first_compliant (queries before reads vs reads first)
- Reasoning dimensions: HYPOTHESIS_FORMATION (graph-informed vs ad-hoc),
  QUERY_FORMULATION (structured queries vs grep), EVIDENCE_INTEGRATION (cites BSKG evidence)
