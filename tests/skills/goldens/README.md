# Golden Output Fixtures

Golden outputs are deterministic test fixtures that validate skill output contracts and serve as reference implementations.

## Purpose

1. **Contract validation** - Ensure agent outputs conform to declared JSON schemas
2. **Regression prevention** - Detect when output structure changes unexpectedly
3. **Documentation** - Show concrete examples of correct output format
4. **Testing isolation** - Run tests without external tool calls or model invocations

## Structure

Each golden fixture is a valid JSON file that:
- Conforms to the skill's declared output schema
- Contains realistic but synthetic data
- Includes all required fields from the schema
- Demonstrates both success and edge cases

## Available Goldens

| File | Skill | Schema | Purpose |
|------|-------|--------|---------|
| `secure_reviewer.json` | vrs-secure-reviewer | `schemas/secure_reviewer_output.json` | Evidence-first security review |
| `attacker.json` | vrs-attacker | Embedded in skill frontmatter | Attack path construction |
| `defender.json` | vrs-defender | Embedded in skill frontmatter | Guard/mitigation discovery |
| `verifier.json` | vrs-verifier | Embedded in skill frontmatter | Evidence cross-checking |

## Updating Goldens

**Manual update:**
Edit JSON files directly, then validate:
```bash
# Validate against schema
python -c "import json, jsonschema
schema = json.load(open('schemas/secure_reviewer_output.json'))
golden = json.load(open('tests/skills/goldens/secure_reviewer.json'))
jsonschema.validate(golden, schema)
print('✓ Valid')"
```

**Automated update:**
Use the helper script to regenerate all goldens:
```bash
python scripts/update_skill_goldens.py
```

**After updates:**
Always run the test suite to verify:
```bash
uv run pytest tests/skills/test_skill_goldens.py -v
```

## Test Usage

Tests load goldens and validate them against schemas:

```python
import json
from pathlib import Path
from jsonschema import validate

# Load golden
golden = json.loads(Path('tests/skills/goldens/secure_reviewer.json').read_text())

# Load schema
schema = json.loads(Path('schemas/secure_reviewer_output.json').read_text())

# Validate
validate(instance=golden, schema=schema)
```

## Design Principles

1. **Deterministic** - No random data, timestamps, or UUIDs
2. **Realistic** - Data should match actual skill output patterns
3. **Complete** - Include all required fields
4. **Graph-anchored** - Evidence must reference valid graph nodes or code locations
5. **Mode-appropriate** - Creative mode has hypotheses, adversarial has refutations

## Schema Evolution

When schemas change:
1. Update the schema file first
2. Run `python scripts/update_skill_goldens.py --validate-only` to see what breaks
3. Update golden fixtures to match new schema
4. Run tests to confirm: `uv run pytest tests/skills/test_skill_goldens.py -v`
5. Document the change in the skill's changelog

## Anti-Patterns

❌ **Don't:**
- Include actual vulnerability data from real projects
- Use random or variable data (timestamps, UUIDs)
- Skip required fields
- Create goldens without schema validation

✅ **Do:**
- Use synthetic but realistic data
- Include edge cases (empty arrays, maximum confidence, etc.)
- Validate against schema before committing
- Document any special cases in comments

## Related Documentation

- `docs/reference/skill-schema-v2.md` - Skill schema specification
- `docs/reference/secure-reviewer.md` - Secure reviewer output contract
- `schemas/` - All JSON schemas
- `.planning/TOOLING.md` - Testing commands
