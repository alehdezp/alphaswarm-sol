# Phase 13: Brutal Review Notes

**Reviewed:** 2026-01-07
**Reviewer:** Claude Opus 4.5 (Technical Reviewer Mode)

---

## CRITICAL ISSUES FOUND

### 1. Wrong Entry Gate - Depends on OPTIONAL Phase

**Problem:** Entry gate says "Phase 12 complete (Agent SDK micro-agents work)"

**Issue:** Phase 12 is marked OPTIONAL and LOW priority. If Phase 12 can be skipped, Phase 13 cannot depend on it.

**Fix:** Change entry gate to:
- "Phase 11 complete (LLM integration works)" OR
- "Phase 12 complete with fallback (direct LLM calls work)"

Grimoires should work with direct LLM calls, not require Agent SDK.

---

### 2. No Base Infrastructure Task

**Problem:** Tasks 13.2-13.6 (individual grimoires) assume:
- Base Grimoire class exists
- GrimoireLoader exists
- Step execution (analysis, bash, code_generation) exists

**None of this infrastructure is defined.**

**Fix:** Created `tasks/13.0-grimoire-base.md` as new PREREQUISITE task.

---

### 3. Tasks 13.3-13.6 and 13.10 Have NO Details

**Problem:** These tasks appear in registry with only:
- ID and name
- "Grimoire works" as validation

**Missing:**
- Implementation steps
- YAML definition
- Test fixtures
- Verification procedure

**Fix:** Created detailed task files. See `tasks/13.3-access-control-grimoire.md` as example.

---

### 4. Grimoire Schema Assumes Non-Existent Code

**Problem:** Task 13.1 shows YAML schema but doesn't explain:
- How to parse it
- How steps execute
- Error handling
- Budget management

The Python implementation shows methods like:
```python
await self.analyze_step(...)
await self.generate_step(...)
await self.bash_step(...)
```

**These methods don't exist and aren't defined anywhere.**

**Fix:** Task 13.0 now defines base Grimoire class with all step execution logic.

---

### 5. Missing Integration with Existing Systems

**Problem:** No mention of how grimoires connect to:
- Knowledge Graph (context extraction)
- Pattern system (which patterns trigger which grimoires)
- Report system (how results flow)
- Existing agents (AttackerAgent, DefenderAgent)

**Fix:** Added integration notes to task files.

---

### 6. Skill Invocation Confusion

**Problem:** Task 13.7 references:
- `.claude/skills/*.yaml` - This is Claude Code's convention, not VKG's
- Loading skills from YAML - No schema defined
- `SkillRegistry` - No implementation

**Questions Not Answered:**
- Is BSKG creating its own skill system or using Claude Code's?
- How do skills relate to grimoires?
- Can skills be invoked from CLI?

**Fix:** Task 13.7 needs clearer scope definition.

---

### 7. Test Fixtures Not Defined

**Problem:** Test Matrix says:
- "Known vulnerable contracts for each grimoire"
- "Mock LLM responses for deterministic testing"

**Where are these?** No paths, no examples, no schemas.

**Fix:** Task files now include explicit fixture definitions with code.

---

### 8. Cost Estimates Optimistic

**Problem:** `max_budget_usd: 1.50` per grimoire

**Reality:** A grimoire with 4 steps might use:
- Step 1 (analysis): $0.10
- Step 2 (code gen): $0.30
- Step 3 (bash): $0.00
- Step 4 (interpret): $0.15
- Retry on failure: +$0.55
- **Total: $1.10 minimum, $2.20 with retries**

**Fix:** Budget should be $2.00-2.50 per grimoire with retry consideration.

---

## NEW TASKS CREATED

### 13.0: Grimoire Base Infrastructure (NEW)

**File:** `tasks/13.0-grimoire-base.md`

**Content:**
- Base Grimoire class with step execution
- StepType enum (analysis, code_generation, bash, decision)
- GrimoireContext and GrimoireResult dataclasses
- GrimoireLoader for YAML parsing
- Step execution for each type
- Budget and error handling

**This task MUST be completed before 13.1-13.10.**

---

### 13.3: Access Control Grimoire (Detailed)

**File:** `tasks/13.3-access-control-grimoire.md`

**Content:**
- Full verification procedure
- YAML definition with all prompts
- Test fixtures (vulnerable and safe contracts)
- Integration notes for graph context
- Validation criteria

---

## IMPROVEMENTS MADE

### Dependency Graph Fixed

```
Original:
13.1 (Schema) ── 13.2 (Reentrancy) ── ...

Fixed:
11.1 (LLM Provider) ── 13.0 (Base Infrastructure)
                            │
                            ├── 13.1 (Schema - optional refinement)
                            │
                            ├── 13.2 (Reentrancy Grimoire)
                            ├── 13.3 (Access Control Grimoire)
                            └── ...
```

### Entry Gate Options

**Option A: Full LLM Integration**
- Phase 11 complete
- Full Tier B support

**Option B: Minimal Path**
- Phase 11.1 (Provider Abstraction) complete
- Use direct LLM calls

**Option C: With Micro-Agents**
- Phase 12 complete
- Use Agent SDK for verification

Grimoires should support all options with graceful degradation.

---

## RECOMMENDATIONS

### Before Starting Phase 13:

1. **Complete Task 13.0 First** - All other tasks depend on it
2. **Decide skill integration** - BSKG skills vs Claude Code skills
3. **Create test fixtures** - Vulnerable and safe contracts for each grimoire type

### Task Order

```
13.0 (Base Infrastructure) - MUST
    │
    ├── 13.1 (Schema Refinement) - Can be parallel with grimoires
    │
    ├── 13.2 (Reentrancy) - First grimoire, validates base
    │
    ├── 13.7 (Skill Invocation) - After first grimoire works
    │
    └── 13.3-13.6 (Other Grimoires) - After 13.2 validates approach
```

### Quality Gate

Before creating more grimoires (13.10), validate:
- 13.2 works end-to-end
- Test compilation >= 60%
- Verdict accuracy >= 70%

If not achieved, iterate on base infrastructure before adding more grimoires.

---

## FILES TO UPDATE IN TRACKER

If updating TRACKER.md, incorporate:

1. **Entry Gate:** "Phase 11.1 complete OR Phase 12 with fallback"
2. **Add Task 13.0** to registry as MUST, blocking all others
3. **Add Task File column** to registry
4. **Expand tasks 13.3-13.6** with details or reference task files
5. **Revise estimates:**
   - Add 6h for 13.0
   - Total: 46h (up from 40h)

---

## INTEGRATION WITH PHASE 12

If Phase 12 is completed:
- Grimoires can use micro-agents for verification
- Swarm mode can run multiple grimoires in parallel

If Phase 12 is skipped:
- Grimoires use direct LLM calls (Phase 11 providers)
- Sequential execution only
- **This is the expected path** given Phase 12 is OPTIONAL

Grimoire infrastructure should NOT depend on Agent SDK.

---

*Review Notes | Phase 13 | 2026-01-07*
