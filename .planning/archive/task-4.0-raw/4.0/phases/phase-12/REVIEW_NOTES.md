# Phase 12: Brutal Review Notes

**Reviewed:** 2026-01-07
**Reviewer:** Claude Opus 4.5 (Technical Reviewer Mode)

---

## CRITICAL ISSUES FOUND

### 1. "Claude Agent SDK" Does Not Exist

**Problem:** The document repeatedly references "Claude Agent SDK" as if it's a library you can import. **This is not real.**

**Reality:**
- There is NO `claude-agent-sdk` npm package
- There is NO `from anthropic.agent_sdk import query` API
- The code examples like `ClaudeAgentOptions(...)` are FICTIONAL

**What Actually Exists:**
1. **Claude Code CLI** (`@anthropic-ai/claude-code`) - Command line tool
2. **Anthropic API** - Direct API for messages
3. **Subprocess spawning** - Calling Claude Code from Python

**Fix Required:** Task R12.1 must research ACTUAL integration patterns. See `tasks/R12.1-agent-sdk-research.md` for realistic approach.

---

### 2. Dependency on SHOULD Tasks

**Problem:** Task 12.8 depends on Phase 11.12 (Multi-Tier Model Support), which is a SHOULD priority task.

**Issue:** A task in Phase 12 should not be blocked on a non-critical task in Phase 11.

**Fix:**
- 12.8 should be implementable with or without 11.12
- Add fallback: "If 11.12 not complete, use single tier"

---

### 3. Task 12.8 is Too Large (80+ Lines of Code)

**Problem:** Original Task 12.8 contained:
- Task routing logic
- TOON encoding integration
- Batch dispatch with concurrency
- Cost tracking
- Provider initialization

This is at LEAST 3 separate tasks.

**Fix:** Split into:
- `12.8a-subagent-task-router.md` - Just routing
- `12.8b-toon-integration.md` - TOON encoding
- `12.8c-batch-dispatch.md` - Batch execution

See `tasks/` directory for split files.

---

### 4. Task 12.9 Has No Details

**Problem:** Task 12.9 (OpenCode SDK Integration) appears in registry but has NO task details section.

**Fix Required:** Add full task description or remove from scope.

---

### 5. Missing Context About Existing Infrastructure

**Problem:** No mention of:
- Existing `src/true_vkg/llm/` with LLMClient, providers
- Existing `src/true_vkg/agents/` with Attacker, Defender, Verifier
- How this phase integrates with existing code

**Fix:** Task files now include "Existing Infrastructure" sections.

---

### 6. Unrealistic Time Estimates

| Task | Original | Realistic |
|------|----------|-----------|
| 12.2 Verification Agent | 8h | 12h (SDK research needed) |
| 12.8 Subagent Manager | 8h | 10h (split into 3 tasks) |
| Total Phase | 44h | 52h+ |

---

### 7. Entry Gate is Too Broad

**Problem:** "Phase 11 complete" means 69 hours of work, 13 tasks.

**Reality:** Phase 12 only needs:
- 11.1 (Provider Abstraction) - for fallback
- 11.12 (Multi-Tier) - preferred but optional

**Fix:** Entry gate should be: "11.1 complete, 11.12 preferred"

---

## IMPROVEMENTS MADE

### New Task Files Created

| File | Purpose |
|------|---------|
| `tasks/R12.1-agent-sdk-research.md` | Realistic research protocol for CLI integration |
| `tasks/12.8a-subagent-task-router.md` | Task routing logic only |
| `tasks/12.8b-toon-integration.md` | TOON encoding integration |
| `tasks/12.8c-batch-dispatch.md` | Batch execution with concurrency |

### Key Clarifications Added

1. **No Agent SDK library exists** - Document the actual options (CLI, API)
2. **Existing infrastructure reference** - Point to actual code paths
3. **Fallback strategies** - Each task has "if X not available, do Y"
4. **Self-contained tasks** - Each task file has all context needed

---

## RECOMMENDATIONS

### Before Starting Phase 12:

1. **Complete R12.1 Research First** - Determine if CLI approach is viable
2. **Decide CLI vs API** - If CLI is not viable, use existing LLMClient
3. **Start with 12.8a** - Task routing provides value even without micro-agents

### If Research Shows CLI Not Viable:

1. Skip 12.1-12.4 (SDK detection, verification agent, test gen, swarm)
2. Keep 12.8a-c (task routing via existing providers)
3. Document as "future enhancement"
4. Focus on Phase 11 Tier B instead

### Phase Priority

Given that Phase 12 is marked OPTIONAL and LOW priority:
- Consider completing Phase 11 fully first
- Only proceed with 12 if Tier B (11) shows micro-agents would add value
- The comparison test (12.7) is the key validation

---

## FILES TO UPDATE IN TRACKER

If updating TRACKER.md, incorporate:

1. **Entry Gate:** "Phase 11.1 complete, 11.12 preferred"
2. **Add clarification section:** What "Agent SDK" actually means
3. **Split 12.8** into 12.8a, 12.8b, 12.8c
4. **Add Task File column** to registry
5. **Add existing infrastructure section**
6. **Revise estimates** to 52h

---

*Review Notes | Phase 12 | 2026-01-07*
