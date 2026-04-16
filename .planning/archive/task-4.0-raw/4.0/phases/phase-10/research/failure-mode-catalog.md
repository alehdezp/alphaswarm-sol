# Failure Mode Catalog

**Status:** Complete
**Created:** 2026-01-08
**Purpose:** Systematic catalog of all BSKG failure modes for graceful degradation design

---

## Component: Slither

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| SL-01 | Crash mid-analysis | Malformed Solidity, compiler bug | Non-zero exit code | No graph built | CRITICAL | Fail gracefully with clear error |
| SL-02 | Timeout | Large codebase (>100 contracts) | Timer exceeded | Partial graph | HIGH | Kill process, report progress |
| SL-03 | Out of Memory | Very large contracts, deep inheritance | MemoryError, OOM killer | Process killed | HIGH | Reduce scope, suggest splitting |
| SL-04 | Missing solc version | Version constraint in pragma | Subprocess error | Cannot compile | CRITICAL | Auto-install solc or suggest command |
| SL-05 | Invalid Solidity | Syntax errors | CompilationError | Cannot parse | MEDIUM | Report errors clearly |

## Component: LLM API

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| LLM-01 | Rate limit (429) | Too many requests | 429 status | Tier B blocked | HIGH | Exponential backoff (1s, 2s, 4s, 8s...) |
| LLM-02 | API key invalid | Misconfiguration | 401 status | Tier B unavailable | MEDIUM | Clear error, show env var name |
| LLM-03 | Network unreachable | No internet | Connection exception | Tier B blocked | HIGH | Offline mode, Tier A only |
| LLM-04 | Request timeout | Slow response, large context | Timer exceeded | Request lost | MEDIUM | Retry with smaller context |
| LLM-05 | Context too large | Token limit exceeded | 400/413 status | Cannot process | MEDIUM | Use PPR to reduce context |
| LLM-06 | Provider unavailable | Service outage | 5xx status | Tier B blocked | HIGH | Circuit breaker, fall back |

## Component: File System

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| FS-01 | Disk full | Low disk space | IOError/OSError | State corrupted | CRITICAL | Warn early, clear cache |
| FS-02 | Permission denied | Wrong permissions | PermissionError | Cannot write | CRITICAL | Clear error with chmod hint |
| FS-03 | Directory deleted | External interference | FileNotFoundError | Operation fails | HIGH | Recreate .vkg directory |
| FS-04 | Graph corrupted | Partial write, crash | JSON decode error | Cannot load | HIGH | Rebuild from source, use backup |
| FS-05 | Config missing | First run or deleted | FileNotFoundError | Use defaults | LOW | Create default config |
| FS-06 | Concurrent write | Multiple BSKG instances | Race condition | Corruption | MEDIUM | File locking |

## Component: External Tools (Aderyn, Medusa, Foundry)

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| EXT-01 | Not installed | Missing binary | FileNotFoundError | Tool unavailable | LOW | Skip tool, note in results |
| EXT-02 | Version mismatch | Old version | Version check | Possible bugs | LOW | Warn, suggest update |
| EXT-03 | Tool crash | Bug in tool | Non-zero exit | No tool results | MEDIUM | Skip tool, continue |
| EXT-04 | Tool timeout | Slow analysis | Timer exceeded | Partial results | MEDIUM | Kill, use available data |
| EXT-05 | Output parse error | Unexpected format | Parse exception | Cannot integrate | MEDIUM | Log error, skip tool |

## Component: Knowledge Graph

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| KG-01 | Invalid node reference | Bug, stale data | KeyError | Query fails | HIGH | Rebuild graph |
| KG-02 | Missing properties | Incomplete build | Missing key | Degraded detection | MEDIUM | Re-analyze function |
| KG-03 | Schema migration needed | Version upgrade | Schema check | Cannot load | HIGH | Migration script |
| KG-04 | Circular reference | Bad edge data | RecursionError | Query hangs | MEDIUM | Cycle detection |

## Component: Pattern Engine

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| PE-01 | Invalid pattern YAML | Syntax error | YAML parse error | Pattern skipped | MEDIUM | Clear error, continue others |
| PE-02 | Pattern timeout | Complex pattern, big graph | Timer exceeded | Pattern skipped | MEDIUM | Simplify or skip |
| PE-03 | Missing pattern file | File deleted/moved | FileNotFoundError | Pattern unavailable | LOW | Use bundled patterns |

## Component: Cache System

| ID | Failure Mode | Trigger | Detection | Impact | Priority | Recovery Strategy |
|----|-------------|---------|-----------|--------|----------|-------------------|
| CA-01 | Cache corrupted | Crash during write | Decode error | Cache miss | LOW | Clear cache, rebuild |
| CA-02 | Cache stale | Source changed | Fingerprint mismatch | Potential bug | MEDIUM | Auto-invalidate |
| CA-03 | Cache too large | Long usage | Disk check | Slow startup | LOW | Prune old entries |

---

## Priority Classification

### CRITICAL (VKG cannot continue - must handle)
- SL-01: Slither crash
- SL-04: Missing solc
- FS-01: Disk full
- FS-02: Permission denied

### HIGH (Major feature degraded - handle in Phase 10)
- SL-02: Slither timeout
- SL-03: Slither OOM
- LLM-01: Rate limit
- LLM-03: Network unreachable
- LLM-06: Provider unavailable
- FS-03: Directory deleted
- FS-04: Graph corrupted
- KG-01: Invalid node reference
- KG-03: Schema migration

### MEDIUM (Reduced capability - handle if time permits)
- SL-05: Invalid Solidity
- LLM-02: API key invalid
- LLM-04: Request timeout
- LLM-05: Context too large
- FS-06: Concurrent write
- EXT-03: Tool crash
- EXT-04: Tool timeout
- EXT-05: Output parse error
- KG-02: Missing properties
- KG-04: Circular reference
- PE-01: Invalid pattern YAML
- PE-02: Pattern timeout
- CA-02: Cache stale

### LOW (Edge case - log for future)
- FS-05: Config missing
- EXT-01: Not installed
- EXT-02: Version mismatch
- PE-03: Missing pattern file
- CA-01: Cache corrupted
- CA-03: Cache too large

---

## Recovery Strategy Matrix

| ID | Immediate Action | User Notification | Recovery Command | Prevention |
|----|-----------------|-------------------|------------------|------------|
| SL-01 | Log error, clean state | "Slither failed on {file}: {error}" | `vkg doctor --fix` | Validate Solidity first |
| SL-04 | Check available versions | "Solidity {version} required but not installed" | `solc-select install {v}` | Auto-install on build |
| FS-01 | Abort write | "Disk full. Free space needed: {size}" | `vkg cache clear` | Check space before ops |
| FS-04 | Load backup if exists | "Graph corrupted. Rebuilding..." | `vkg build-kg --force` | Atomic writes |
| LLM-01 | Wait with backoff | "Rate limited. Waiting {n}s..." | Auto-retry | Use circuit breaker |
| LLM-03 | Switch to Tier A | "Offline mode. Using pattern matching only." | Set VKG_OFFLINE=1 | Check network first |
| EXT-01 | Skip tool | "Tool '{name}' not found. Continuing without it." | Install command | Check on startup |

---

## Failure Mode Count Summary

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| Slither | 5 | 2 | 2 | 1 | 0 |
| LLM API | 6 | 0 | 3 | 3 | 0 |
| File System | 6 | 2 | 2 | 1 | 1 |
| External Tools | 5 | 0 | 0 | 3 | 2 |
| Knowledge Graph | 4 | 0 | 2 | 2 | 0 |
| Pattern Engine | 3 | 0 | 0 | 2 | 1 |
| Cache System | 3 | 0 | 0 | 1 | 2 |
| **Total** | **32** | **4** | **9** | **13** | **6** |

---

*Failure Mode Catalog | Version 1.0 | 2026-01-08*
