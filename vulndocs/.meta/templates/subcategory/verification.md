# Verification: {{subcategory_name}}

## Multi-Agent Verification Workflow

### Step 1: Graph Analysis (Automatic)

```yaml
verification_step: graph_analysis
agent: none (automatic)
actions:
  - Query BSKG for vulnerable patterns
  - Extract semantic operations
  - Identify state transitions
output: candidate_functions_list
```

### Step 2: Attacker Analysis

```yaml
verification_step: attack_construction
agent: vrs-attacker
model: claude-opus-4
actions:
  - Construct exploit sequence
  - Identify entry points
  - Calculate economic impact
output: attack_scenario
```

### Step 3: Defender Analysis

```yaml
verification_step: guard_search
agent: vrs-defender
model: claude-sonnet-4
actions:
  - Search for existing mitigations
  - Identify guards and checks
  - Evaluate protection coverage
output: mitigation_assessment
```

### Step 4: Cross-Verification

```yaml
verification_step: evidence_check
agent: vrs-verifier
model: claude-opus-4
actions:
  - Cross-reference attack and defense
  - Verify code locations
  - Calculate confidence score
output: verdict
```

## Verification Checklist

- [ ] Graph patterns match vulnerability signature
- [ ] Semantic operations confirm expected behavior
- [ ] No existing guards invalidate finding
- [ ] Attack scenario is economically viable
- [ ] Evidence links to specific code locations

## Confidence Scoring

| Score | Meaning | Required Evidence |
|-------|---------|-------------------|
| 0.9+ | Confirmed | Attack + no guards + exploit POC |
| 0.7-0.9 | Likely | Attack + minimal guards |
| 0.5-0.7 | Possible | Partial pattern match |
| <0.5 | Unlikely | Weak signals only |
