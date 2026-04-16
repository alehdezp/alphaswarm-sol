# Phase 20 Agent Scorecards

- run_id: A-001
  scenario: <single-vuln|multi-vuln|false-positive|missing-context|ambiguous|recovery>
  tools_used: [build-kg, query]
  tool_sequence: [build-kg, query, report]
  roles_used: [attacker, defender, verifier]
  success: true|false
  notes: <what worked>
  failures: <what broke>
  recovery: <how it fixed it>
  missing_capabilities: <gaps>
  evidence_packets: <count>
  beads_created: <count>
