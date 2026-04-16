# Tool Integration Overview

**Architecture and supported tools for AlphaSwarm.sol.**

**For adapter details and detector mappings, see [Tool Adapters Reference](tools-adapters.md).**

---

## Tool Architecture

```
External Tools                    BSKG Integration
     |                                 |
     v                                 v
+---------------------------------------------------------+
|                    ToolRegistry                          |
|  - Tool discovery and health checks                      |
|  - Version detection and compatibility                   |
+---------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------+
|                   ToolCoordinator                        |
|  - Strategy creation per project                         |
|  - Pattern skip logic (TOOL-07)                          |
|  - Parallel execution orchestration                      |
+---------------------------------------------------------+
                         |
          +--------------+--------------+
          v              v              v
     +---------+   +---------+   +---------+
     | Adapter |   | Adapter |   | Adapter |   (7 adapters)
     | Slither |   | Aderyn  |   | Mythril |   ...
     +----+----+   +----+----+   +----+----+
          |              |              |
          +--------------+--------------+
                         v
+---------------------------------------------------------+
|                  SARIF Normalizer                        |
|  - Unified finding format                                |
|  - Severity mapping                                      |
+---------------------------------------------------------+
                         |
                         v
+---------------------------------------------------------+
|               SemanticDeduplicator                       |
|  - Stage 1: Location clustering                          |
|  - Stage 2: Embedding similarity                         |
+---------------------------------------------------------+
```

---

## Supported Tools

**Location:** `src/alphaswarm_sol/tools/adapters/`

| Tool | Type | Language | LOC |
|------|------|----------|-----|
| **Slither** | Static Analysis | Python | ~600 |
| **Aderyn** | Static Analysis | Rust | ~450 |
| **Mythril** | Symbolic Execution | Python | ~550 |
| **Echidna** | Fuzzing | Haskell | ~500 |
| **Foundry** | Testing Framework | Rust | ~400 |
| **Semgrep** | Pattern Matching | OCaml | ~450 |
| **Halmos** | Symbolic Testing | Python | ~400 |

### Capability Matrix

| Tool | Reentrancy | Access Control | Integer Issues | Oracle |
|------|------------|----------------|----------------|--------|
| Slither | High | High | Medium | No |
| Aderyn | Medium | Medium | Medium | No |
| Mythril | High | Medium | High | No |
| Echidna | High | Medium | High | Low |

---

## Tool Tiers

| Tier | Tools | Rationale |
|------|-------|-----------|
| **CORE** | Slither | Fast, comprehensive, Foundry-native |
| **RECOMMENDED** | Aderyn, Mythril | Good coverage, reasonable speed |
| **OPTIONAL** | Echidna, Foundry, Semgrep, Halmos | Specialized or require setup |

### Default Execution

```python
DEFAULT_TOOLS = ["slither", "aderyn"]
FULL_TOOLS = ["slither", "aderyn", "mythril", "semgrep"]
```

---

## Tool Commands (Subagent/Dev)

These commands are typically invoked by Claude Code workflows. Direct usage is for development, CI, and advanced debugging.

### Tool Status

```bash
uv run alphaswarm tools status
# Shows installed tools, versions, and tiers
```

### Run Tools

```bash
# Default tools (slither + aderyn)
uv run alphaswarm tools run path/to/contracts/

# Specific tools
uv run alphaswarm tools run path/to/contracts/ --tools slither,mythril

# All available
uv run alphaswarm tools run path/to/contracts/ --tools all
```

### Explain Strategy

```bash
uv run alphaswarm tools explain path/to/contracts/
# Shows tools to run, patterns to skip, rationale
```

---

## Tool Selection Decision Tree

```
Is project Foundry-based?
+-- YES -> Include Aderyn (Foundry-optimized)
+-- NO -> Slither only for static

Need deep symbolic analysis?
+-- YES -> Include Mythril
+-- NO -> Skip (too slow for quick scans)

Need fuzzing?
+-- YES -> Include Echidna
+-- NO -> Skip (requires property setup)
```

---

## VKG-Optimized Defaults

**File:** `.vrs/tools.yaml`

### Excluded Detectors (Noisy)

```yaml
slither:
  exclude:
    - naming-convention     # Not security
    - pragma               # Not runtime security
    - costly-loop          # Gas optimization
    - similar-names        # Too many false positives
```

### Tool Timeouts

```yaml
timeouts:
  slither: 300      # 5 minutes
  aderyn: 120       # 2 minutes
  mythril: 900      # 15 minutes
  echidna: 1800     # 30 minutes
```

---

## Related Documentation

- [Tool Adapters Reference](tools-adapters.md) - Detector mappings, deduplication, SARIF
- [Agent Reference](agents.md) - Agents that use tool output

---

*Last Updated: February 2026*
