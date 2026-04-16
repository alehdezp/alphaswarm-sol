# GAP-01: delegate_guard.py blocked_patterns does not catch Bash Python import calls

**Created by:** improve-phase
**Source:** P1-IMP-02
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

Does `Bash(python -c "import os")` get blocked (exit code 2) when delegate_guard.py is active with current blocked_patterns config `[".sol"]`? The current config blocks `.sol` as a string pattern in tool_input. Need to confirm whether this pattern catches Python import calls or only catches file path patterns containing ".sol".

## Context

Decision D-1 must be rewritten from "prompt-enforced tool restrictions" to "hook-enforced restrictions via delegate_guard.py," but only after confirming that `blocked_patterns` in delegate_guard.py actually intercepts Bash-level Python import calls. Rewriting D-1 without confirmation would encode a third false enforcement model. The Plan 12 Batch 1 failure showed agents used `Bash(python -c "import alphaswarm_sol...")` to bypass restrictions.

## Research Approach

1. Read delegate_guard.py source to trace exact pattern matching logic
2. Simulate the hook's behavior with test inputs to determine whether `blocked_patterns: [".sol"]` matches against `Bash(python -c "import os")` or `Bash(python -c "from alphaswarm_sol.kg import KnowledgeGraph")`
3. Determine what patterns WOULD be needed to block Python imports via Bash

## Findings

**Confidence:** HIGH (source code analysis + deterministic simulation)

### 1. Pattern Matching Mechanism

`delegate_guard.py` (lines 111-119) implements `blocked_patterns` as a simple **substring search** against the entire serialized `tool_input` JSON:

```python
input_str = json.dumps(tool_input)
for pattern in blocked_patterns:
    if pattern in input_str:
        # ... check allowed exceptions ...
        sys.exit(2)  # Blocked by pattern
```

For a Bash tool call, `tool_input` is `{"command": "<the bash command>"}`. The pattern match checks if the blocked string appears **anywhere** in the JSON-serialized tool_input.

### 2. Canary Test Results (Simulated)

| Bash Command | tool_input JSON | `".sol"` matches? | Blocked? |
|---|---|---|---|
| `python -c "import os"` | `{"command": "python -c \"import os\""}` | **NO** | **NOT BLOCKED** |
| `python -c "from alphaswarm_sol.kg import KnowledgeGraph"` | `{"command": "python -c \"from alphaswarm_sol.kg import KnowledgeGraph\""}` | **NO** | **NOT BLOCKED** |
| `python3 -c "import sys; print(sys.path)"` | `{"command": "python3 -c \"import sys; print(sys.path)\""}` | **NO** | **NOT BLOCKED** |
| `cat contracts/Vulnerable.sol` | `{"command": "cat contracts/Vulnerable.sol"}` | YES | Blocked |

### 3. Why `.sol` Fails for Python Imports

The pattern `".sol"` (dot + sol) catches Solidity file paths (e.g., `Vulnerable.sol`) but NOT Python module paths:
- `alphaswarm_sol` contains `_sol` (underscore), not `.sol` (dot)
- `alphaswarm_sol.kg` produces substring `sol.` (sol + dot), not `.sol` (dot + sol)
- Generic Python calls like `python -c "import os"` contain zero `.sol` substrings

### 4. Patterns Required for Python Import Blocking

Simulation shows these patterns would be effective:

| Pattern | Blocks `python -c "import os"` | Blocks `from alphaswarm_sol...` | Blocks `python3 ...` |
|---|---|---|---|
| `"python"` | YES | YES | YES |
| `"python3"` | NO | NO | YES |
| `"import "` | YES | YES | YES |
| `"from alphaswarm"` | NO | YES | NO |

The minimum effective set for the evaluation config is: `["python", "import "]`. Adding `"python3"` and `"from alphaswarm"` provides defense-in-depth.

### 5. Important Edge Case: allowed_reads Bypass

The `blocked_patterns` check has an `allowed_reads` exception (lines 115-118):
```python
for allowed in allowed_reads:
    if allowed in input_str:
        sys.exit(0)
```

Current `allowed_reads: [".vrs/", ".planning/"]` would NOT interfere with Python blocking since Python commands don't typically contain those path strings. However, a Bash command like `python -c "import os" > .vrs/output.txt` WOULD be allowed through because `.vrs/` appears in the command string. This is a secondary bypass vector that the evaluation config must account for.

## Recommendation

**Do:** The current `blocked_patterns: [".sol"]` provides **zero protection** against Python import bypass via Bash. D-1 CANNOT be rewritten to claim hook enforcement until the evaluation-specific config adds Python-blocking patterns.

**Specific actions:**

1. Create `delegate_guard_config_eval.yaml` with `blocked_patterns` that include at minimum: `["python", "python3", "import ", "from alphaswarm", ".sol"]`.
2. The evaluation config's `allowed_reads` must be scoped to `["contracts/"]` only (not `.vrs/` or `.planning/`) to prevent the allowed_reads bypass vector.
3. Add a canary test (`test_bash_python_import_blocked`) that feeds simulated Bash tool_input to `delegate_guard.py` and asserts exit code 2. This test should cover: (a) `python -c "import os"`, (b) `from alphaswarm_sol.kg import KnowledgeGraph`, (c) `python3 -c "..."`.
4. D-1 rewrite should state: "Enforcement uses delegate_guard.py PreToolUse hook with `blocked_tools` (tool-level) AND `blocked_patterns` (Bash command-level, requiring patterns for `python`, `python3`, `import` to block Python invocations, plus `.sol` for Solidity file access)."

**Impacts:** Plan 01 scope (must produce eval-specific YAML with Python-blocking patterns), Plan 06 (retry depends on correct enforcement).
