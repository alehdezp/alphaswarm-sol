# Builder Change Protocol

**Purpose:** Define safe procedures for modifying `src/true_vkg/kg/builder.py` - the critical graph construction module.

**Last Updated:** 2026-01-07

---

## Why This Protocol Exists

`builder.py` is the foundation of VKG's vulnerability detection. It extracts 50+ security properties from Solidity code. Changes here can:

1. **Break existing patterns** - Properties that patterns depend on may change semantics
2. **Introduce false positives/negatives** - New detection logic may have unintended effects
3. **Cause non-determinism** - Graph structure changes break fingerprinting
4. **Impact performance** - New analysis passes can slow builds significantly

---

## Change Classification

### Level 1: Safe Changes (Low Risk)
- Bug fixes that don't change property semantics
- Performance optimizations (caching, early returns)
- Code cleanup (refactoring without logic changes)
- Adding new properties that don't affect existing ones

**Validation Required:** Unit tests pass, 3 DVDeFi graphs identical

### Level 2: Moderate Changes (Medium Risk)
- Adding new properties used by patterns
- Modifying property extraction logic
- Changes to edge creation

**Validation Required:** All tests pass, full DVDeFi benchmark, no regressions

### Level 3: Structural Changes (High Risk)
- Changing property semantics
- Removing or renaming properties
- Modifying node/edge types
- Changes to graph structure

**Validation Required:** Full validation suite, property migration plan, deprecation period

---

## Pre-Change Checklist

Before modifying builder.py:

```bash
# 1. Baseline current state
uv run alphaswarm build-kg examples/damm-vuln-defi/src/unstoppable/ --out /tmp/baseline.kg.json

# 2. Run full test suite
uv run pytest tests/ -v --tb=short 2>&1 | tail -20

# 3. Record current detection rate
cat benchmarks/detection_baseline.json | jq '.summary.dvd_detection_rate'

# 4. Create git stash point
git stash push -m "pre-builder-change-$(date +%Y%m%d-%H%M%S)"
```

---

## Change Procedure

### Step 1: Document the Change

Before writing code, document:
- What property/behavior is being added/modified?
- Why is this change needed?
- What patterns will use this property?
- What are the expected effects on detection?

### Step 2: Write Tests First

For new properties:
```python
# tests/test_builder_properties.py

def test_new_property_true_positive():
    """Property X should be True for vulnerable pattern."""
    graph = load_graph("VulnerableContract")
    func = find_function(graph, "vulnerableFunction")
    assert func["properties"]["new_property"] == True

def test_new_property_true_negative():
    """Property X should be False for safe pattern."""
    graph = load_graph("SafeContract")
    func = find_function(graph, "safeFunction")
    assert func["properties"]["new_property"] == False
```

### Step 3: Implement Change

- Make minimal, focused changes
- Add inline comments explaining security-relevant logic
- Update property documentation in docstrings

### Step 4: Validate

```bash
# 1. Run tests
uv run pytest tests/ -v

# 2. Build DVDeFi graphs
for challenge in unstoppable truster naive-receiver side-entrance; do
    uv run alphaswarm build-kg examples/damm-vuln-defi/src/$challenge/ --out /tmp/$challenge.kg.json
done

# 3. Compare with baseline (must be identical for non-property changes)
diff <(jq -S . /tmp/baseline.kg.json/graph.json) <(jq -S . /tmp/unstoppable.kg.json/graph.json)

# 4. Check detection rate
uv run alphaswarm query --graph /tmp/unstoppable.kg.json/graph.json "pattern:*" | jq '.findings | length'
```

### Step 5: Document

Update relevant documentation:
- `docs/reference/properties.md` - If adding new properties
- `CHANGELOG.md` - For any user-visible changes
- Pattern YAML files - If patterns need updating

---

## Property Naming Convention

```
# Format: <category>_<behavior>_<modifier>

# Good examples:
has_access_gate              # Boolean: presence check
uses_ecrecover               # Boolean: usage detection
state_write_after_call       # Boolean: ordering detection
external_call_count          # Integer: count
access_gate_sources          # List: collection

# Bad examples:
isSecure                     # Too vague
check1                       # Not descriptive
vulnerable                   # Subjective judgment
```

---

## Property Categories

| Category | Prefix | Examples |
|----------|--------|----------|
| Access Control | `has_access_`, `uses_`, `access_` | `has_access_gate`, `uses_tx_origin` |
| State | `reads_state`, `writes_state`, `state_` | `state_write_after_call` |
| External Calls | `has_external_`, `external_`, `call_` | `has_external_calls`, `call_target_validated` |
| Loops | `has_loop`, `loop_`, `unbounded_` | `has_unbounded_loop`, `loop_bound_sources` |
| Tokens | `uses_erc20_`, `token_`, `uses_safe_` | `uses_erc20_transfer`, `token_return_guarded` |
| Oracle | `reads_oracle_`, `has_staleness_` | `reads_oracle_price`, `has_staleness_check` |
| Crypto | `uses_ecrecover`, `checks_` | `uses_ecrecover`, `checks_sig_s` |

---

## Rollback Procedure

If a change causes issues:

```bash
# 1. Revert to last known good state
git checkout HEAD~1 -- src/true_vkg/kg/builder.py

# 2. Verify tests pass
uv run pytest tests/ -v

# 3. Document the issue
echo "Reverted builder.py change due to: <reason>" >> CHANGELOG.md

# 4. Create issue for proper fix
# gh issue create --title "Builder change caused regression" --body "..."
```

---

## Property Deprecation

When removing or changing property semantics:

1. **Add deprecation warning** (minimum 1 release)
2. **Update patterns** to use new property
3. **Add migration notes** to CHANGELOG
4. **Test with all known patterns**

```python
# Deprecation example in builder.py
import warnings

def _extract_old_property(self, func):
    warnings.warn(
        "Property 'old_property' is deprecated, use 'new_property' instead",
        DeprecationWarning
    )
    return self._extract_new_property(func)
```

---

## Emergency Fixes

For critical bugs that need immediate fix:

1. **Minimal change only** - Fix the specific issue
2. **Add regression test** - Prevent recurrence
3. **Document in CHANGELOG** with `[HOTFIX]` tag
4. **Full validation** within 24 hours

---

## Approval Requirements

| Change Level | Reviewer | Tests Required |
|--------------|----------|----------------|
| Level 1 | Self-review | Unit tests |
| Level 2 | Code review | Full suite + DVDeFi |
| Level 3 | Team discussion | Full suite + migration plan |

---

## References

- `src/true_vkg/kg/builder.py` - Main builder module
- `docs/reference/properties.md` - Property documentation
- `patterns/` - Pattern definitions using properties
- `tests/test_builder.py` - Builder unit tests
