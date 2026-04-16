# [Vulnerability Name] - Core Pattern

## Overview

[1-2 sentence description of the vulnerability]

## How It Works

[Concise explanation of the vulnerability mechanism]

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Why It Matters

[Security impact and severity explanation]

## Common Scenarios

- **Scenario 1:** [Description]
- **Scenario 2:** [Description]

## Key Characteristics

- [Characteristic 1]
- [Characteristic 2]
- [Characteristic 3]

## Detection Summary

**CRITICAL:** Use BSKG graph queries, NOT manual code reading.

Key operations to detect:
- `OPERATION_1`: [What it indicates]
- `OPERATION_2`: [What it indicates]

### Primary Detection Query
```vql
FIND functions WHERE
  operation1 AND
  operation2 AND
  NOT has_protection
```

### Vulnerable vs Safe Pattern

**Vulnerable:**
```
operation1 -> operation2 -> operation3
```

**Safe:**
```
operation1 -> protection -> operation2 -> operation3
```

## Verification Summary

1. **Check [Condition 1]:** Use graph query `[VQL]`
2. **Verify [Condition 2]:** Expected: [What to find]
3. **Confirm no protection:** `has_protection_mechanism = false`

## Related Patterns

- See `./patterns/` for detection patterns
- Related: [related-vulnerability-link]

---

*Keep this file as the core reference. Detailed detection in detection.md, verification in verification.md.*
