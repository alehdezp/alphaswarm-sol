# Economic Behavior Model Template

Use this template to capture concrete, evidence-backed economic reasoning. Replace placeholders with real values or formulas. If a value is unknown, provide the assumption and a range.

## Metadata
- model_id: ""
- protocol_type: ""  # lending | dex | staking | flash-loan | other
- contract: ""
- scenario_ref: ""
- context_pack_ref: ""  # optional
- version: ""
- author: ""
- created_at: ""

## Actors
List each participant with role and incentives.
- actor: ""
  role: ""
  incentives:
    - ""
  resources:
    - ""

## Incentives Summary
- incentive_summary: ""
- profit_threshold: ""  # minimum profit required for rational attacker
- non_financial_motivations: ""  # optional

## Value Flows
Describe concrete asset/value movement.
- flow:
  from: ""
  to: ""
  asset: ""
  trigger: ""
  notes: ""

## Assumptions
State what must hold for normal operation.
- assumption: ""
  validation: ""  # how to validate or data source

## Attack Economics
Describe how an attacker would profit, including costs and risks.
- exploit_path: ""
- profit_calculation:
  formula: ""  # e.g., profit = drained_balance - gas_costs - mev_tip
  variables:
    - name: ""
      value: ""
      source: ""
  estimated_profit: ""  # numeric value or range
- costs:
  gas_costs: ""
  setup_costs: ""
  opportunity_costs: ""
- risks:
  mev_competition: ""
  detection_risk: ""
  execution_risk: ""
- break_even: ""  # profit threshold or formula
- incentive_compatibility: ""  # yes/no with rationale
- sensitivity:
  key_variables:
    - ""
  impact_on_profit: ""

## Failure Conditions
Describe loss scenarios with concrete impact estimates.
- loss_scenario: ""
  impacted_parties: ""
  impact_estimate: ""  # value or range

## Evidence
Provide traceability to code and graph evidence.
- evidence_node_ids:
  - ""
- code_locations:
  - ""
- transcript_ref: ""  # claude-code-agent-teams transcript path
- supporting_artifacts:
  - ""

## Completion Checklist
- [ ] Actors, incentives, and flows are enumerated
- [ ] Profit calculation includes concrete numbers or formulas
- [ ] Costs and risks are included and quantified where possible
- [ ] Failure conditions include impact estimates
- [ ] Evidence links (graph node IDs, code locations) are provided
