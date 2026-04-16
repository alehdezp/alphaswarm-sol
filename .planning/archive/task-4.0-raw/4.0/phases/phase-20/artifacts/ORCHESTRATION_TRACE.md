# Phase 20 Orchestration Trace

Capture tool orchestration sequences for agent runs.

- run_id: A-001
  scenario: <single-vuln|multi-vuln|false-positive|missing-context|ambiguous|recovery>
  tool_sequence:
    - <tool> <params>
    - <tool> <params>
  outputs:
    - <path>
  errors: <none|summary>
  recovery_steps: <if any>
  evidence_packet_ids: [id1, id2]
  bead_ids: [B-001, B-002]
