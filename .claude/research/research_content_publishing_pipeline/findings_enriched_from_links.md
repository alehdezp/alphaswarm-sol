# Enriched Findings from User-Provided Claude Code Ecosystem Links

## 1. Book Factory Pattern (robertguss/claude-skills)
- **ebook-factory** and **non-fiction-book-factory** skills exist as full pipelines
- Also includes a **writing** skill for "voice capture and ghost writing"
- Pattern: packaged multi-phase workflows that Claude follows when invoked
- Includes a `build.py` packager for converting skills into shareable formats
- **Key insight**: The pipeline pattern (research → outline → write → edit → publish) is directly applicable to project-artifact → content pipeline

## 2. Blogging Platform Commands (cloudartisan/cloudartisan.github.io)
- Real-world `.claude/commands/` for a blog: organized into `posts/`, `projects/`, `site/`
- Hierarchical skill system where domains have separate command modules
- Pattern: commands organized by function, documented through markdown
- **Key insight**: Proven that Claude Code can drive a full blog publishing workflow via skills

## 3. Hooks Mastery — 13 Lifecycle Events (disler/claude-code-hooks-mastery)
Most relevant hooks for content triggers:
- **Stop**: Can inject "content suggestion" context when planning artifacts are modified
- **SubagentStop**: Trigger content draft when a research/improvement agent completes
- **SessionEnd**: Summarize session work into potential content seed
- **PostToolUse**: Detect commits touching `.planning/` or `docs/research/`

Hook flow control:
- Exit 0 = success (stdout in transcript)
- Exit 2 = blocking error (fed back to Claude)
- UV single-file scripts pattern for isolation

**Agent patterns from hooks-mastery**:
- Team-Based: Builder (all tools) + Validator (read-only) — maps to Writer + Editor
- Meta-Agent: Creates other agents dynamically
- Research agent (`llm-ai-agents-and-eng-research.md`): 5-step process (temporal context → discovery → scope expansion → extraction → synthesis) with structured output format

## 4. Everything Claude Code (affaan-m/everything-claude-code)
- **doc-updater** skill: Auto-syncs docs with code changes
- **continuous-learning-v2**: Extracts patterns from sessions, `/evolve` clusters into reusable skills
- `/instinct-export` and `/instinct-import` for knowledge sharing — could be adapted for content export
- Hooks in `hooks.json` for PostToolUse and Stop event automation
- **Key insight**: The continuous-learning pattern (extract → cluster → evolve) is the same pattern needed for content mining (extract insights → cluster by topic → produce posts)

## 5. Ultimate Guide (FlorianBruniaux/claude-code-ultimate-guide)
- 14 production-ready skills with templates
- 31 hooks across bash and PowerShell
- 6 custom AI personas (agent definitions)
- Decision framework: agents vs skills vs commands
- Agent Teams (v2.1.32+): 5 validated workflows, multi-agent coordination
- **Key insight**: Phased adoption strategy — start basic, add hooks only after testing. Same principle for content pipeline: start with a `/publish-draft` skill, add hooks later

## 6. Awesome Claude Code — Specific Content-Adjacent Resources
- **Web Assets Generator**: Generates social media meta images — useful for blog post hero images
- **Fullstack Dev Skills (jeffallan/claude-skills)**: 65 skills including 9 project workflow commands for Jira/Confluence
- **Claude Code Templates (davila7)**: Usage dashboard, analytics — could be adapted for content tracking
- **No dedicated blogging MCP** found in awesome list, but LinkedIn MCP exists (Dishant27/linkedin-mcp-server)

## Synthesis: Key Patterns for Content Pipeline

### Pattern A: Skill-Driven Content Generation
```
/content-draft → reads .planning/ artifacts → produces .content/drafts/
/content-linkedin → reads draft → formats for LinkedIn (3000 char limit, Unicode bold)
/content-publish → reads draft → pushes via MCP to platform
```

### Pattern B: Hook-Triggered Content Seeds
```
SessionEnd hook → summarize session → write to .content/seeds/
Stop hook (after phase completion) → extract key findings → content seed
PostToolUse (git commit on .planning/) → flag for content review
```

### Pattern C: Agent Teams Content Writer
```
TeamCreate("content") → Writer agent (sonnet, read-only)
  → Reads .planning/ CONTEXT.md, IMPROVEMENT files, RESEARCH files
  → Mines adversarial reviews, decisions, deferred items
  → Produces structured drafts matching platform requirements
  → Human reviews → /content-publish
```

### Pattern D: Continuous Learning → Content Export
```
/evolve (from everything-claude-code) extracts session patterns
→ Cluster by publishable topic
→ Generate content from clusters
→ Similar to /instinct-export but for external publication
```
