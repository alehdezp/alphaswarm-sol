# Planning Rules Directory

**CRITICAL: These rules are MANDATORY and MUST be applied automatically.**

---

## Auto-Invoke Triggers

**When you see ANY of these patterns, IMMEDIATELY load the relevant rules:**

| Pattern Detected | Load This File | Enforcement |
|------------------|----------------|-------------|
| `skill`, `SKILL.md`, `/vrs-*`, `/gsd:*` | `RULES-ESSENTIAL.md` | BLOCKING |
| `/gsd-plan-phase`, `plan phase` | `.planning/testing/PLAN-PHASE-GOVERNANCE.md` | BLOCKING |
| `subagent`, `agent`, `.claude/agents/` | `RULES-ESSENTIAL.md` | BLOCKING |
| `orchestrat*`, `workflow`, `multi-agent` | `RULES-ESSENTIAL.md` | BLOCKING |
| `validation`, `e2e`, `ga-validation` | `VALIDATION-RULES.md` | BLOCKING |
| `agent teams`, `interactive`, `Claude Code` | `claude-code-controller-instructions.md` | BLOCKING |
| `test`, `testing`, `verify` | `TESTING-PHILOSOPHY.md` | WARNING |

---

## Quick Rule Summary

### claude-code-controller Testing (BLOCKING)

**ALL skills, subagents, and workflows MUST be tested via claude-code-controller:**

```bash
claude-code-controller launch "zsh"           # 1. Always launch shell first
claude-code-controller send "claude" --pane=X # 2. Start Claude Code
claude-code-controller send "/skill" --pane=X # 3. Execute skill
claude-code-controller wait_idle --pane=X     # 4. Wait for completion
claude-code-controller capture --pane=X       # 5. Capture transcript
```

**Mocks, simulations, and fabricated outputs are FORBIDDEN.**

### Validation Mode (BLOCKING)

- LIVE mode only (never mock/simulated)
- External ground truth only (Code4rena, SmartBugs)
- Real duration (not instant)
- Transcript authenticity (50+ lines minimum)

### Perfect Metrics = Fabrication

If you see 100% precision, 100% recall, or 0% error rate, the results are fabricated.

---

## Files in This Directory

| File | Purpose | Lines | When to Load |
|------|---------|-------|--------------|
| **RULES-ESSENTIAL.md** | Condensed actionable rules | ~220 | **AUTO: Any skill/agent/workflow work** |
| **VALIDATION-RULES.md** | Full rule reference (A1-G3) | ~1200 | Deep validation, audits |
| **TESTING-FRAMEWORK.md** | Agentic testing architecture | ~210 | Workflow testing setup |
| **TESTING-PHILOSOPHY.md** | Core reasoning principles | ~70 | Understanding "why" |
| **claude-code-controller-instructions.md** | Complete command reference | ~230 | Any Agent Teams operations |

---

## Enforcement Hierarchy

```
RULES-ESSENTIAL.md (always load for skill/agent/workflow)
    │
    ├── Quick reference + triggers
    ├── Must-follow patterns
    └── Links to detailed files when needed
            │
            ├── VALIDATION-RULES.md (full A1-G3 rules)
            ├── TESTING-FRAMEWORK.md (architecture)
            └── claude-code-controller-instructions.md (commands)
```

---

## Non-Negotiable Requirements

Before completing ANY work on skills, agents, or workflows:

1. **Test via claude-code-controller** - Not simulation, not mock, not fabricated
2. **Capture transcript** - Save to `.vrs/testing/runs/<run_id>/transcript.txt` (transcripts/ may be a symlink index)
3. **Verify authenticity** - Check line count, tool markers, duration
4. **Compare to ground truth** - External sources only
5. **Document limitations** - No perfect metrics claims
6. **For planning, derive checks from evidence** - No hardcoded outcomes in `/gsd-plan-phase`
