# Contingency Paths

**Purpose:** Define recovery procedures when builder.py changes cause issues.

**Last Updated:** 2026-01-07

---

## Scenario 1: Builder Change Breaks Tests

**Symptom:** Tests that were passing before now fail after builder.py modification.

**Immediate Actions:**
```bash
# 1. Don't panic - identify which tests failed
uv run pytest tests/ -v --tb=short 2>&1 | grep FAILED

# 2. Check if it's a property change
git diff src/true_vkg/kg/builder.py | head -100

# 3. Revert if unsure
git checkout HEAD -- src/true_vkg/kg/builder.py
```

**Decision Tree:**
```
Tests failed after builder change?
├── Are they property-related tests?
│   ├── YES: Property semantics changed
│   │   ├── Was change intentional?
│   │   │   ├── YES: Update tests to match new semantics
│   │   │   └── NO: Revert change, investigate
│   │   └── Are patterns using this property?
│   │       ├── YES: Update patterns OR revert
│   │       └── NO: Safe to update test expectations
│   └── NO: Structural issue
│       └── Revert and investigate
├── Are they pattern matching tests?
│   └── Property extraction changed unexpectedly
│       └── Revert, add regression test first
└── Are they unrelated tests?
    └── Investigate - may be pre-existing flaky test
```

---

## Scenario 2: Detection Rate Decreased

**Symptom:** DVDeFi detection rate dropped after builder.py change.

**Immediate Actions:**
```bash
# 1. Check current detection rate
cat benchmarks/detection_baseline.json | jq '.summary.dvd_detection_rate'

# 2. Identify which challenges regressed
for challenge in unstoppable truster naive-receiver side-entrance the-rewarder selfie puppet puppet-v2 puppet-v3 free-rider backdoor climber; do
    echo "=== $challenge ==="
    uv run alphaswarm build-kg examples/damm-vuln-defi/src/$challenge/ --out /tmp/$challenge.kg.json 2>/dev/null
    uv run alphaswarm query --graph /tmp/$challenge.kg.json/graph.json "pattern:*" 2>/dev/null | jq '.findings | length'
done

# 3. Revert if significant regression
git checkout HEAD -- src/true_vkg/kg/builder.py
```

**Decision Tree:**
```
Detection rate decreased?
├── By how much?
│   ├── > 5%: CRITICAL - Revert immediately
│   ├── 1-5%: CONCERNING - Investigate before proceeding
│   └── < 1%: May be acceptable - document trade-off
├── Which patterns affected?
│   ├── Core patterns (reentrancy, access control)?
│   │   └── CRITICAL - Do not proceed
│   └── Edge case patterns?
│       └── May be acceptable - document
└── Is new detection value worth trade-off?
    ├── YES: Document explicitly, update baseline
    └── NO: Revert change
```

---

## Scenario 3: False Positive Rate Increased

**Symptom:** More false positives reported after builder.py change.

**Immediate Actions:**
```bash
# 1. Run on known-safe contracts
uv run alphaswarm build-kg tests/contracts/safe/ --out /tmp/safe.kg.json
uv run alphaswarm query --graph /tmp/safe.kg.json/graph.json "pattern:*" | jq '.findings | length'

# 2. If findings on safe contracts, investigate
uv run alphaswarm lens-report --graph /tmp/safe.kg.json/graph.json --explain

# 3. Check if patterns need updating
ls patterns/core/*.yaml | head -20
```

**Decision Tree:**
```
False positives increased?
├── On which contracts?
│   ├── Known-safe test contracts: Property too broad
│   ├── Real-world safe code: Pattern too aggressive
│   └── Edge cases: May need none conditions
├── Which patterns affected?
│   └── Add more specific none conditions
└── Is property extraction correct?
    ├── YES: Pattern needs tuning
    └── NO: Builder logic needs fixing
```

---

## Scenario 4: Graph Structure Changed

**Symptom:** Graph fingerprints no longer match, CI fails.

**Immediate Actions:**
```bash
# 1. Check what changed in graph structure
diff <(jq -S . /tmp/before.kg.json/graph.json) <(jq -S . /tmp/after.kg.json/graph.json) | head -50

# 2. If node/edge types changed
git diff src/true_vkg/kg/schema.py

# 3. If structure fundamentally different
git checkout HEAD -- src/true_vkg/kg/builder.py
```

**Decision Tree:**
```
Graph structure changed?
├── Was this intentional?
│   ├── YES: Update golden snapshots
│   └── NO: Revert and investigate
├── Are node/edge counts different?
│   ├── More nodes: New extraction logic
│   ├── Fewer nodes: Lost extraction
│   └── Same count, different content: Property change
└── Do patterns still match?
    ├── YES: Update fingerprints
    └── NO: Fix builder before updating fingerprints
```

---

## Scenario 5: Performance Degraded

**Symptom:** Build times significantly increased after builder.py change.

**Immediate Actions:**
```bash
# 1. Profile build time
time uv run alphaswarm build-kg examples/damm-vuln-defi/src/unstoppable/

# 2. Check if new analysis passes added
git diff src/true_vkg/kg/builder.py | grep -E "for|while|\.analyze"

# 3. If > 2x slowdown, consider reverting
```

**Decision Tree:**
```
Performance degraded?
├── By how much?
│   ├── > 3x: CRITICAL - Needs optimization
│   ├── 2-3x: CONCERNING - Consider trade-offs
│   └── < 2x: May be acceptable
├── Is degradation per-function or per-contract?
│   ├── Per-function: Analysis complexity increased
│   └── Per-contract: External tool issue
└── Can optimization be added?
    ├── YES: Add caching, early returns
    └── NO: Consider feature toggle
```

---

## Scenario 6: Property Removed/Renamed

**Symptom:** Patterns fail to match because property no longer exists.

**Immediate Actions:**
```bash
# 1. Find patterns using the property
grep -r "property_name" patterns/

# 2. Check if property was renamed
git diff src/true_vkg/kg/builder.py | grep -E "^\+.*property_name|^\-.*property_name"

# 3. Update patterns or revert
```

**Decision Tree:**
```
Property removed/renamed?
├── Was there a deprecation warning?
│   ├── YES: Follow migration guide
│   └── NO: Should not have been removed
├── Are patterns updated?
│   ├── YES: Verify patterns still work
│   └── NO: Update patterns first
└── Is rollback needed?
    ├── YES: Revert builder, add deprecation
    └── NO: Proceed with updates
```

---

## Emergency Rollback Procedure

For any critical issue:

```bash
# 1. Stash current changes
git stash push -m "emergency-rollback-$(date +%Y%m%d-%H%M%S)"

# 2. Revert to last known good state
git checkout HEAD~1 -- src/true_vkg/kg/builder.py

# 3. Verify tests pass
uv run pytest tests/ -v --tb=short

# 4. Verify detection rate
cat benchmarks/detection_baseline.json | jq '.summary.dvd_detection_rate'

# 5. Document the issue
echo "ROLLBACK: $(date) - Reason: [describe issue]" >> task/4.0/INCIDENTS.md

# 6. Create issue for proper fix
# gh issue create --title "Builder rollback needed" --body "..."
```

---

## Prevention Checklist

Before any builder.py change:

- [ ] Read BUILDER-PROTOCOL.md
- [ ] Create baseline measurements
- [ ] Write tests first
- [ ] Make minimal changes
- [ ] Run full validation
- [ ] Document in CHANGELOG

---

## Contact Points

For escalation:
- Builder issues: Check BUILDER-PROTOCOL.md
- Pattern issues: Check pattern YAML documentation
- Test failures: Check tests/README.md
- Performance: Check profiling docs
