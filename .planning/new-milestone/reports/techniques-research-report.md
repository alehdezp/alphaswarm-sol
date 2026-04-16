# T7: 2026 Techniques Research Report

## Executive Summary

**Research conducted:** Feb 8, 2026 | **Searches performed:** 18+ | **Confidence:** High (based on official docs + production reports)

### Key Findings

1. **Claude Code Agent Teams** (launched Feb 6, 2026 with Opus 4.6) is the single most impactful new capability for AlphaSwarm. It enables native multi-agent coordination without external frameworks.
2. **Hooks system** is mature and powerful enough to enforce graph-first reasoning, block agent drift, and gate quality at every lifecycle point.
3. **Subagent persistent memory** is a new capability that enables compound learning across sessions.
4. **Agent-based hooks** (spawning subagents for verification) can replace our manual quality gate enforcement.
5. **The Compaction API** enables longer-running audit sessions without context loss.
6. **External multi-agent frameworks (LangGraph, CrewAI, AutoGen) are not needed** -- Claude Code's native capabilities now cover our orchestration needs.
7. **LLM-SmartAudit** validates our multi-agent security approach but shows our graph-first approach is a genuine differentiator vs. pure LLM conversation.

### Critical Recommendation

**AlphaSwarm 6.0 should migrate from subagent-only orchestration to Agent Teams for the attacker/defender/verifier debate, while using hooks extensively for behavioral enforcement.** This is the highest-leverage architectural change available.

---

## 1. Claude Code Agent Teams

### Current Capabilities (as of Feb 6, 2026)

Agent Teams shipped with Opus 4.6 as an experimental research preview. Key facts:

- **Enable:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json or env
- **Architecture:** One team lead + N teammates, each with own context window
- **Coordination:** Shared task list (DAG-based with blocking/blocked-by), direct inter-agent messaging
- **Display modes:** In-process (Shift+Up/Down to navigate) or split-pane (claude-code-agent-teams/iTerm2)
- **Task system:** Tasks support DAGs -- Task 3 (Run Tests) can block on Task 1 (Build API) and Task 2 (Configure Auth)
- **File locking:** Task claiming uses file locking to prevent race conditions
- **Cross-session state:** `CLAUDE_CODE_TASK_LIST_ID` env var enables shared task lists across sessions

### Best Practices (from Addy Osmani, Anthropic docs, community)

1. **Teams work best for independent, parallel work** -- not sequential tasks
2. **Max 3-4 specialized agents** -- more decreases productivity
3. **Each teammate should own different files** -- avoids edit conflicts
4. **Use delegate mode** (Shift+Tab) to keep lead as coordinator-only
5. **Size tasks as self-contained units** with clear deliverables -- 5-6 tasks per teammate
6. **Start with research/review** before parallel implementation
7. **Give teammates enough context** in spawn prompt (they don't inherit lead's conversation)
8. **Use plan approval** for risky tasks: `Require plan approval before they make any changes`

### How Teams Compare to Subagents

| Aspect | Subagents | Agent Teams |
|--------|-----------|-------------|
| Context | Own window, results return to caller | Own window, fully independent |
| Communication | Report back to main agent only | Teammates message each other directly |
| Coordination | Main agent manages all work | Shared task list with self-coordination |
| Token cost | Lower (summarized back) | Higher (each is separate Claude instance) |
| Best for | Focused tasks where only result matters | Complex work requiring discussion |
| Nested | Cannot spawn subagents | Cannot spawn sub-teams |

### Limitations and Workarounds

| Limitation | Workaround |
|-----------|------------|
| No session resumption for in-process teammates | Spawn new teammates after resume |
| Task status can lag (teammates forget to mark complete) | Use `TaskCompleted` hooks to validate |
| One team per session | Clean up before starting new team |
| No nested teams | Use subagents within teammates for focused sub-tasks |
| Lead is fixed for lifetime | Design lead role carefully upfront |
| All teammates start with lead's permissions | Change individual modes after spawn |
| Split panes require claude-code-agent-teams/iTerm2 | Use in-process mode as fallback |

### Relevance to AlphaSwarm

**HIGH.** The attacker/defender/verifier debate maps directly to Agent Teams:
- Lead = Orchestrator (creates investigation beads, manages lifecycle)
- Attacker teammate = Construct exploit paths (has BSKG query access)
- Defender teammate = Find guards/mitigations (independent exploration)
- Verifier teammate = Cross-check evidence, arbitrate verdicts

The debate protocol naturally benefits from agents messaging each other directly rather than round-tripping through the orchestrator.

---

## 2. Hooks System

### Available Hook Events (Complete List)

| Event | When | Can Block? |
|-------|------|------------|
| `SessionStart` | Session begins/resumes/compacts | No |
| `UserPromptSubmit` | User submits prompt | No (can inject context) |
| `PreToolUse` | Before tool executes | **Yes** (exit 2) |
| `PermissionRequest` | Permission dialog appears | No |
| `PostToolUse` | After tool succeeds | No (can inject feedback) |
| `PostToolUseFailure` | After tool fails | No |
| `Notification` | Alert sent | No |
| `SubagentStart` | Subagent spawned | No |
| `SubagentStop` | Subagent finishes | No |
| `Stop` | Agent finishes responding | **Yes** (can force continuation) |
| `TeammateIdle` | Teammate about to idle | **Yes** (exit 2 = keep working) |
| `TaskCompleted` | Task being marked complete | **Yes** (exit 2 = prevent completion) |
| `PreCompact` | Before compaction | No |
| `SessionEnd` | Session terminates | No |

### Hook Types (3 tiers)

1. **Command hooks** (`type: "command"`) -- Run shell scripts. Deterministic, fast.
2. **Prompt hooks** (`type: "prompt"`) -- Single LLM call (Haiku by default). For judgment-based decisions.
3. **Agent hooks** (`type: "agent"`) -- Spawn subagent with tool access. For verification requiring code inspection.

### Critical: Tool Input Modification (v2.0.10+)

PreToolUse hooks can **modify tool inputs** before execution:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { "command": "modified-command-here" }
  }
}
```

This enables:
- Transparent sandboxing (e.g., force `--dry-run` flags)
- Automatic security enforcement (secret redaction)
- Team convention adherence (formatting, linting)
- **Graph-first enforcement** (inject BSKG query before manual code reading)

### Enforcement Patterns for AlphaSwarm

#### Pattern 1: Graph-First Enforcement
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read|Grep|Glob",
      "hooks": [{
        "type": "prompt",
        "prompt": "Check if BSKG queries have been run before this code read. If not, return {\"ok\": false, \"reason\": \"Run BSKG queries before reading code directly\"}"
      }]
    }]
  }
}
```

#### Pattern 2: Evidence-First Stop Gate
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "agent",
        "prompt": "Verify all findings have evidence packets with graph node IDs, code locations, and operation sequences. If any finding lacks evidence, return {\"ok\": false, \"reason\": \"...\"}"
      }]
    }]
  }
}
```

#### Pattern 3: Anti-Drift Re-Injection After Compaction
```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "compact",
      "hooks": [{
        "type": "command",
        "command": "cat .claude/context/audit-state.json"
      }]
    }]
  }
}
```

#### Pattern 4: Task Completion Quality Gate
```json
{
  "hooks": {
    "TaskCompleted": [{
      "hooks": [{
        "type": "agent",
        "prompt": "Verify this task's deliverables meet acceptance criteria. Check for evidence completeness.",
        "timeout": 60
      }]
    }]
  }
}
```

#### Pattern 5: Teammate Quality Enforcement
```json
{
  "hooks": {
    "TeammateIdle": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "Check if the teammate completed their assigned work with evidence. If they stopped prematurely, return {\"ok\": false, \"reason\": \"Complete your investigation before going idle\"}"
      }]
    }]
  }
}
```

### How to Prevent Agent Drift

Based on research (Agent Drift paper, arxiv 2601.04170):

Three types of drift in multi-agent systems:
1. **Semantic drift** -- Progressive deviation from original intent
2. **Coordination drift** -- Breakdown in multi-agent consensus
3. **Behavioral drift** -- Emergence of unintended strategies

**Prevention strategies using hooks:**
- `SessionStart(compact)` hooks to re-inject critical context after compaction
- `Stop` hooks to verify task completion matches original intent
- `TaskCompleted` agent hooks to independently verify deliverables
- `TeammateIdle` hooks to prevent premature stopping
- Persistent memory (MEMORY.md) to accumulate and recall conventions

---

## 3. Skills and Subagents

### Latest Design Patterns (Feb 2026)

#### Subagent Configuration

Full frontmatter options now available:
```yaml
---
name: my-agent
description: When to delegate to this agent
tools: Read, Grep, Glob, Bash  # or omit to inherit all
disallowedTools: Write, Edit   # deny specific tools
model: sonnet                   # sonnet, opus, haiku, inherit
permissionMode: default         # default, acceptEdits, delegate, dontAsk, bypassPermissions, plan
maxTurns: 50                   # max agentic turns
skills:                        # preload skills into context
  - api-conventions
  - error-handling
memory: user                   # persistent memory: user, project, local
hooks:                         # lifecycle hooks scoped to this agent
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
---
```

#### Persistent Memory (NEW)

Subagents can now maintain persistent memory across sessions:
- `user` scope: `~/.claude/agent-memory/<agent>/` (all projects)
- `project` scope: `.claude/agent-memory/<agent>/` (version-controlled)
- `local` scope: `.claude/agent-memory-local/<agent>/` (gitignored)

Auto-maintains MEMORY.md with first 200 lines loaded at startup. This enables compound learning.

#### Skills Preloading

Use `skills` field to inject skill content at startup:
```yaml
skills:
  - graph-first-template
  - evidence-packet-format
```

This gives subagents domain knowledge without runtime discovery overhead.

### Anti-Drift Techniques

1. **Explicit tool restrictions** -- Only give agents tools they need
2. **PreToolUse hooks** -- Validate every action against rules
3. **Stop hooks** -- Force completion verification before stopping
4. **Persistent memory** -- Accumulate conventions and patterns across sessions
5. **Skills injection** -- Pre-load domain knowledge to prevent re-invention
6. **Plan mode requirement** -- Force agents to plan before implementing (`permissionMode: plan`)

### Evidence Enforcement

Two approaches:

**A. Hook-based (deterministic):**
```json
{
  "hooks": {
    "TaskCompleted": [{
      "hooks": [{
        "type": "command",
        "command": "python3 validate_evidence.py"
      }]
    }]
  }
}
```

**B. Agent-based (LLM-verified):**
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "agent",
        "prompt": "Verify all findings contain: graph node IDs, code locations, operation sequences. Return {\"ok\": false} if any are missing.",
        "timeout": 120
      }]
    }]
  }
}
```

### Skill Auto-Invocation Reality Check

Community reports (Scott Spence, others) reveal that skills don't reliably auto-activate. Workaround:
- Use `UserPromptSubmit` hooks to detect trigger words and explicitly inject skill instructions
- Write crystal-clear descriptions with specific trigger terms
- Use `disable-model-invocation: true` for side-effect skills
- Consider hooks as the reliable trigger mechanism, not LLM discretion

---

## 4. Multi-Agent Orchestration

### Framework Comparison (2026 State)

| Framework | Philosophy | Strengths | Weaknesses | AlphaSwarm Fit |
|-----------|-----------|-----------|------------|----------------|
| **Claude Code Teams** | Native coordination | Zero setup, shared tasks, direct messaging | Experimental, limited nesting | **Best fit** -- already in ecosystem |
| **LangGraph** | Graph-based workflows | Fine-grained control, conditional logic, auditability | Complex setup, Python-centric | Good for custom workflow logic |
| **CrewAI** | Role-based teams | Fast prototyping, role clarity | Less control, rigid roles | Moderate -- role model maps well |
| **AutoGen** | Conversational agents | Natural dialogue, human-in-loop | Less structured, harder to audit | Low -- too loose for security |
| **Claude Agent SDK** | Programmatic agents | Full API control, CI/CD integration | More code to write | Good for headless/automated mode |

### Recommendation

**Use Claude Code Agent Teams as primary orchestrator.** Reasons:
1. Zero external dependency -- runs inside Claude Code natively
2. Task DAG system handles dependencies automatically
3. Direct inter-agent messaging enables debate protocol
4. Hooks provide behavioral enforcement not available in external frameworks
5. Already used by our user personas (they run Claude Code)

**Consider Claude Agent SDK** for:
- Headless/CI mode audits
- Integration with external systems
- Cases where Agent Teams' experimental status is a concern

### Best Patterns for Security Analysis

Based on LLM-SmartAudit (IEEE TSE 2025) and community research:

1. **Role specialization** -- Each agent focuses on specific audit aspects
2. **Buffer-of-thought** -- Maintain dynamic record of insights throughout audit
3. **Dual strategy** -- Targeted Analysis (specific vulns) + Broad Analysis (comprehensive scan)
4. **Multi-round debate** -- Adversarial cross-agent critique reduces false positives significantly
5. **Separate verification** -- AI proposes vulnerabilities, verification engine proves them

### Debate Protocols

Research findings (MDPI Applied Sciences, arXiv 2511.07784, D3 Framework):

**DebateCV Pattern:**
1. Two Debaters take opposing stances with evidence-grounded arguments
2. Moderator synthesizes debates into verdicts
3. Strict turn-taking: Debater A → Debater B → Judge
4. Multiple complete rounds
5. Judge can direct questions to either debater

**D3 Framework (Debate, Deliberate, Decide):**
- Role-specialized agents: advocates, judge, optional jury
- Structured debate produces reliable, interpretable evaluations
- Cost-aware -- balances thoroughness with efficiency

**Key finding:** "Debate-driven approaches significantly surpass prior methods, with superiority arising from adversarial cross-agent critique that rigorously evaluates evidence and mitigates misleading information."

**Practical consideration:** 2-3 debate rounds is optimal. More rounds show diminishing returns and increased cost.

---

## 5. Self-Testing and Self-Improving Patterns

### Agent Self-Validation

**Agent-as-Judge framework** (2026 survey, arXiv 2601.05111):
- Uses agentic systems to evaluate agentic systems
- Agents employ planning, tool-augmented verification, multi-agent collaboration
- Dramatically outperforms LLM-as-a-Judge and matches human evaluation

**Practical implementation for AlphaSwarm:**
1. Verifier agent runs BSKG queries to independently check attacker/defender claims
2. Tool-augmented verification (actually reads code, not just reasons about it)
3. Evidence collection through intermediate artifacts, not just text-based reasoning

### Quality Measurement

**Four-channel memory** (Addy Osmani):
1. Git history -- Objective change tracking
2. Progress logs -- Timestamped task attempts and outcomes
3. Task state files -- JSON tracking completion and validation
4. Knowledge base -- MEMORY.md accumulating semantic context

**Monitoring loop:**
- Production behavior feeds back into QA
- Failures convert into new tests automatically
- Performance issues trigger targeted regression suites
- Successful patterns saved to improve future runs

### Continuous Improvement Loops

**The "Ralph Wiggum" Loop** (Addy Osmani):
1. Task selection from prioritized queue
2. Implementation by AI agent
3. Automated validation (tests, linting, type checks)
4. Conditional commit on success
5. Context reset for next task

**Critical design principle:** "Resetting memory each iteration avoids accumulating confusion while maintaining context through files."

**AgentSpec (ICSE 2026):**
- Lightweight DSL for runtime constraints on LLM agents
- Triggers, predicates, enforcement mechanisms
- Prevents unsafe executions in >90% of cases
- Overheads in milliseconds
- Rules can be auto-generated by LLMs (95.56% precision)

---

## 6. Claude Code Latest Features (Feb 2026)

### Opus 4.6 (Released Feb 5, 2026)

| Feature | Details | AlphaSwarm Impact |
|---------|---------|-------------------|
| **Agent Teams** | Multi-agent coordination (research preview) | **Critical** -- enables native debate protocol |
| **Adaptive Thinking** | Dynamic thinking depth based on complexity | Reduces costs for simple steps |
| **128K Output Tokens** | Doubled from 64K | Longer audit reports without truncation |
| **1M Context Window** (beta) | Up from 200K | Entire protocol analysis in single context |
| **Compaction API** | `compact_20260112` strategy in Messages API | Longer-running audit sessions |
| **500+ Security Flaws Found** | Opus 4.6 found real CVEs in open-source | Validates LLM security analysis capability |
| **Better Code Review** | Improved debugging and code review skills | Better agent reasoning quality |

### Task System

- Tasks replace Todos as first-class citizen
- DAG support (blocking/blocked-by dependencies)
- Cross-session sharing via `CLAUDE_CODE_TASK_LIST_ID`
- File locking prevents race conditions

### Hooks Improvements

- Agent-based hooks (`type: "agent"`) for multi-turn verification
- `TeammateIdle` and `TaskCompleted` events for team coordination
- `PreCompact` event for context preservation
- Tool input modification in PreToolUse (since v2.0.10)

### Subagent Improvements

- Persistent memory across sessions
- Skills preloading in frontmatter
- CLI-defined subagents via `--agents` flag (JSON)
- Per-subagent hooks in frontmatter
- Plugin distribution for subagents

---

## 7. Metaprompt and Anti-Drift Techniques

### Metaprompt Patterns

Meta-prompting focuses on structural templates rather than content-specific examples:
- Provide *how to think* rather than *what to think*
- Chain reasoning: analysis loop → planning loop → execution loop
- Output from one agent becomes input for next

### Anti-Drift Research (arXiv 2601.04170)

Three drift manifestations:
1. **Semantic drift** -- Deviation from original intent over time
2. **Coordination drift** -- Breakdown in multi-agent consensus
3. **Behavioral drift** -- Emergence of unintended strategies

### Practical Anti-Drift Measures

1. **Context re-injection** -- `SessionStart(compact)` hooks restore critical context
2. **Periodic checkpoints** -- Stop hooks verify alignment with original task
3. **Persistent memory** -- MEMORY.md survives context resets
4. **AgentSpec-style runtime enforcement** -- Declarative rules externalized from LLM
5. **Regression evals** -- Graduated capability evals as regression suite
6. **Task atomization** -- Small, self-contained units with clear acceptance criteria
7. **External ground truth** -- Verify against BSKG graph, not agent's own memory

### Instruction Compliance

Research (arXiv 2601.03359) shows:
- LLMs generate relevant content but fail on formal constraints
- Multi-agentic workflow decoupling task descriptions from constraints works best
- Externalized rules (not embedded in prompts) ensure consistent behavior
- Runtime enforcement prevents drift without prompt engineering brittleness

---

## 8. Security-Specific Agent Patterns

### State of the Art (2026)

**LLM-SmartAudit (IEEE TSE 2025):**
- Multi-agent architecture: Project Manager, Counselor, Auditor, Solidity Expert
- Buffer-of-thought mechanism for dynamic insight recording
- 98% accuracy on common vulnerabilities
- 74% recall vs. Mythril/Securify's significantly lower rates
- ~$1 per contract operational cost

**Agent4Vul (Springer, Science China):**
- Multimodal LLM agents for smart contract vuln detection
- Combines code analysis with visual representations

**iAudit (ICSE 2025):**
- Combines fine-tuning with LLM-based agents
- Trained on audit-specific data

### Key Design Patterns

1. **AI proposes, verification engine proves** -- Eliminates LLM false positives
2. **Role specialization** -- Each agent handles one audit aspect
3. **Price dependency tracing** -- AI excels at cross-protocol chain analysis
4. **Flash loan modeling** -- Economic impact modeling LLMs can do in minutes vs. human days
5. **Adversarial cross-agent critique** -- Multiple rounds of challenge/response

### AlphaSwarm Differentiators

vs. LLM-SmartAudit:
- We have BSKG graph (they rely on pure LLM conversation)
- We have semantic operations (TRANSFERS_VALUE_OUT, etc.)
- We have VulnDocs pattern library (680+ patterns)
- We have external tool integration (Slither, Mythril, Aderyn)

vs. Traditional tools:
- We have LLM reasoning + graph structure
- We have multi-agent debate + verification
- We have economic/protocol context

---

## Recommendations for AlphaSwarm 6.0

### Must Adopt (Critical)

1. **Migrate to Agent Teams for debate protocol**
   - Attacker, Defender, Verifier as teammates
   - Lead as orchestrator with delegate mode
   - Direct inter-agent messaging for debate rounds
   - Shared task list for investigation beads
   - **Why:** Eliminates round-trip through orchestrator, enables true debate

2. **Implement hook-based behavioral enforcement**
   - Graph-first enforcement via PreToolUse prompt hooks
   - Evidence completeness via TaskCompleted agent hooks
   - Anti-drift via SessionStart(compact) context re-injection
   - Quality gates via Stop hooks
   - **Why:** Deterministic enforcement replaces "hoping agents follow instructions"

3. **Adopt Compaction API + context preservation**
   - Enable `compact_20260112` strategy
   - SessionStart(compact) hook to re-inject audit state
   - PreCompact hook to save critical context before compaction
   - **Why:** Enables longer-running audits without losing investigation context

4. **Use persistent memory for agents**
   - Attacker: accumulate exploit patterns across audits
   - Defender: accumulate guard patterns across audits
   - Verifier: accumulate evaluation heuristics
   - **Why:** Compound learning -- each audit improves future audits

### Should Adopt (Valuable)

5. **Task DAG system for investigation beads**
   - Model bead lifecycle as task dependencies
   - Attacker findings → Defender review → Verifier verdict
   - TaskCompleted hooks as quality gates
   - Cross-session state for long audits

6. **Agent-based hooks for quality verification**
   - Replace prompt-only checks with agent hooks that can read files and run tools
   - Particularly valuable for evidence completeness verification
   - 60-120 second timeout for thorough checking

7. **Delegate mode for orchestrator**
   - Prevent lead from doing investigation work itself
   - Force all work through specialized teammates
   - Enable with Shift+Tab or programmatically

8. **Skills preloading for domain knowledge**
   - Preload graph-first-template, evidence-packet-format into agent context
   - Eliminates need for agents to discover skills at runtime
   - More reliable than auto-invocation

9. **AgentSpec-inspired runtime rules**
   - Declarative rules for agent behavior constraints
   - Externalized from prompts (survives context changes)
   - Auto-generated rules as starting point, human-refined

### Nice to Have (Future Consideration)

10. **Opus 4.6 1M context window** (beta)
    - When stable, enables entire protocol analysis in single context
    - Currently beta -- monitor stability

11. **Claude Agent SDK for headless mode**
    - CI/CD integration for automated audits
    - Programmatic control for testing infrastructure
    - Important for commercial deployment

12. **Adaptive thinking optimization**
    - Use lower effort levels for mechanical steps (parsing, formatting)
    - Reserve high effort for complex reasoning (vulnerability analysis)
    - Can reduce costs significantly

13. **Cross-session task sharing**
    - `CLAUDE_CODE_TASK_LIST_ID` for audit continuity
    - Multiple audit sessions sharing investigation state
    - Important for large protocol audits spanning sessions

14. **Self-improving feedback loops**
    - After each audit, save successful investigation patterns to agent memory
    - Convert production failures into new test cases
    - Gradually improve agent effectiveness over time

---

## Sources

### Official Documentation
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code Custom Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Introducing Claude Opus 4.6](https://www.anthropic.com/news/claude-opus-4-6)
- [What's New in Claude 4.6](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6)
- [Compaction API](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Agent SDK Hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

### Community & Analysis
- [Addy Osmani: Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/)
- [Addy Osmani: Self-Improving Coding Agents](https://addyosmani.com/blog/self-improving-agents/)
- [Addy Osmani: The 80% Problem](https://addyo.substack.com/p/the-80-problem-in-agentic-coding)
- [Addy Osmani: How to Write a Good Spec for AI Agents](https://addyosmani.com/blog/good-spec/)
- [Kieran Klaassen: Swarm Orchestration Skill](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [VentureBeat: Claude Code Tasks](https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across)
- [TechCrunch: Anthropic Releases Opus 4.6](https://techcrunch.com/2026/02/05/anthropic-releases-opus-4-6-with-new-agent-teams/)
- [Scott Spence: Skills Don't Auto-Activate](https://scottspence.com/posts/claude-code-skills-dont-auto-activate)
- [eesel: Claude Code Multiple Agent Systems Guide](https://www.eesel.ai/blog/claude-code-multiple-agent-systems-complete-2026-guide)
- [Agent Design Patterns (Lance Martin)](https://rlancemartin.github.io/2026/01/09/agent_design/)
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery)

### Academic Research
- [LLM-SmartAudit (IEEE TSE 2025)](https://arxiv.org/abs/2410.09381) -- Multi-agent smart contract vulnerability detection
- [Agent Drift (arXiv 2601.04170)](https://arxiv.org/html/2601.04170v1) -- Behavioral degradation in multi-agent LLM systems
- [AgentSpec (ICSE 2026)](https://arxiv.org/abs/2503.18666) -- Customizable runtime enforcement for LLM agents
- [Agent-as-a-Judge Survey (arXiv 2601.05111)](https://arxiv.org/abs/2601.05111) -- Agent-based evaluation taxonomy
- [D3 Framework (arXiv 2410.04663)](https://arxiv.org/html/2410.04663v3) -- Cost-aware adversarial LLM evaluation
- [Tool-MAD (arXiv 2601.04742)](https://www.arxiv.org/pdf/2601.04742) -- Multi-agent debate for fact verification
- [DebateCV (MDPI 2025)](https://www.mdpi.com/2076-3417/15/7/3676) -- Adversarial debate and voting mechanisms
- [Enhancing LLM Instruction Following (arXiv 2601.03359)](https://arxiv.org/html/2601.03359) -- Multi-agentic prompt optimization

### Framework Comparisons
- [LangGraph vs CrewAI vs AutoGen (DEV)](https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63)
- [DataCamp: Framework Comparison](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [How to Build Multi-Agent Systems (Differ)](https://differ.blog/p/how-to-build-multi-agent-systems-complete-2026-guide-f50e02)
- [Top Agentic AI Frameworks 2026](https://research.aimultiple.com/agentic-frameworks/)
