# Research: Claude Code Skills & Plugins for Content Generation from Project Artifacts

**Date:** 2026-02-20
**Confidence:** High (based on official docs, community repos, and verified MCP servers)
**Status:** Complete

---

## 1. Existing Community Skills for Content Generation

### Changelog / Summary Generation Skills

Several community skills already mine git history and produce structured output. These are the closest analogues to what we need:

| Skill | Source | What It Does |
|-------|--------|-------------|
| `changelog-generator` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills/blob/master/changelog-generator/SKILL.md) | Parses git commits, categorizes changes (Added/Changed/Fixed), outputs Keep-a-Changelog format. 23.6k stars on repo. |
| `changelog-manager` | [interstellar-code/claud-skills](https://playbooks.com/skills/interstellar-code/claud-skills/changelog-manager) | Full release workflow: git log analysis, version bumping, GitHub Releases. Auto-activates on "prepare release" keywords. |
| `changelog-guide` | [mcpmarket.com](https://mcpmarket.com/tools/skills/changelog-guide-generator) | Generates user-centric descriptions from commits (not raw technical messages). Focuses on stakeholder communication. |

### Content Repurposing Skills (from 36-skill survey)

From the [AibleWMyMind community survey](https://aiblewmymind.substack.com/p/claude-skills-36-examples) (Jan 2026, 23 creators, 36 skills):

- **Content Extraction skill** (by Alex McFarland): Extracts ideas from long-form content and organizes into platform-specific tables with titles. Directly applicable to extracting LinkedIn posts from IMPROVEMENT/RESEARCH docs.
- **Newsletter Writing skills**: Multiple community members built skills that enforce brand voice, structure, and audience targeting. Pattern: define voice/tone in SKILL.md, provide templates, let Claude adapt content to format constraints.

### Key Pattern: No existing skill specifically mines `.planning/` artifacts into social media content. This is a gap we can fill.

### Skill Marketplaces to Watch

| Platform | URL | Notes |
|----------|-----|-------|
| SkillMD.ai | https://skillmd.ai | Hosts downloadable SKILL.md packages |
| Playbooks.com | https://playbooks.com/skills | `npx playbooks add skill` install flow |
| MCP Market | https://mcpmarket.com | Combined MCP + Skills directory |
| awesome-claude-skills | https://github.com/travisvn/awesome-claude-skills | 6.5k stars, curated list |
| ComposioHQ/awesome-claude-skills | https://github.com/ComposioHQ/awesome-claude-skills | 23.6k stars, skill source code |

---

## 2. Skill Patterns for Mining Project Artifacts into Content

### Pattern A: Git History + Planning Docs -> Narrative Summary

```
Input Sources:
  - git log --oneline --since="2 weeks ago"
  - .planning/STATE.md (current phase, decisions)
  - .planning/phases/*/IMPROVEMENT-*.md (learnings)
  - .planning/phases/*/RESEARCH.md (deep dives)
  - .planning/phases/*-CONTEXT.md (session context)

Processing Steps:
  1. Extract key decisions and "aha moments" from IMPROVEMENT docs
  2. Map git commits to planning phase milestones
  3. Identify audience-relevant insights (technical vs business)
  4. Generate platform-specific drafts

Output:
  - LinkedIn post (< 3000 chars, hook + insight + takeaway)
  - Blog article (1000-2000 words, structured with headers)
  - Thread format (5-7 connected points)
```

### Pattern B: Decision Log -> "Lessons Learned" Content

The project's IMPROVEMENT files contain structured entries like:
- Problem encountered
- Approach tried
- What worked / what didn't
- Pattern extracted

This maps directly to a "lessons learned" content format popular on LinkedIn for technical audiences.

### Pattern C: Adversarial Review -> "Counterintuitive Insight" Content

Gap analysis and adversarial review docs (common in `.planning/` phases) contain contrarian findings that make excellent social content. Pattern:
1. Find claims that were challenged or overturned
2. Frame as "We assumed X, but discovered Y"
3. Add the evidence/reasoning chain

### Recommended SKILL.md Structure

```yaml
---
name: content-from-artifacts
description: |
  Generate LinkedIn posts and blog articles from project planning artifacts.

  Invoke when user wants to:
  - Create content: "write a LinkedIn post about our latest phase"
  - Summarize progress: "what did we learn this sprint"
  - Draft blog: "turn the IMPROVEMENT docs into an article"
  - Content calendar: "what content can we extract from recent work"

slash_command: content-draft
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git log*)
  - Bash(git diff*)
  - Write
---

# Content from Project Artifacts

## Overview
Mine .planning/ artifacts, git history, and decision logs to produce
publishable content drafts for LinkedIn and blog platforms.

## Source Priority
1. IMPROVEMENT-*.md files (highest signal: lessons learned)
2. RESEARCH.md files (deep technical insights)
3. *-CONTEXT.md files (narrative of what happened)
4. STATE.md (milestone achievements)
5. git log (commit-level changes, less useful alone)

## Output Formats

### LinkedIn Post (default)
- Hook line (question or bold claim, < 150 chars)
- 2-3 paragraphs of insight (total < 2500 chars)
- Takeaway or call to action
- 3-5 relevant hashtags
- NO emojis unless user requests them

### Blog Article
- Title (< 70 chars, specific)
- TL;DR (2-3 sentences)
- Problem/Context section
- What We Did section
- What We Learned section (bulk of value)
- Implications / What's Next
- Target: 1000-2000 words

### Thread Format
- 5-7 connected points
- Each point standalone but building on previous
- Final point: synthesis or call to action

## Voice Guidelines
- Technical but accessible
- First person plural ("we discovered", "our approach")
- Concrete examples over abstractions
- Quantify where possible (%, counts, time saved)
- Honest about failures and pivots

## Process
1. Read STATE.md to understand current phase
2. Glob .planning/phases/*/IMPROVEMENT-*.md for recent learnings
3. Read the most recent 2-3 IMPROVEMENT files
4. Identify the strongest insight (novel, counterintuitive, or impactful)
5. Draft in requested format
6. Write draft to .content/drafts/{date}-{slug}.md
```

---

## 3. Claude Code Hooks for Content Generation Triggers

### Available Hook Events (14 total as of Feb 2026)

| Event | Can Block? | Content Generation Use |
|-------|-----------|----------------------|
| `SessionStart` | Yes | Load content calendar, show pending drafts |
| `UserPromptSubmit` | Yes | Detect content-related requests |
| `PreToolUse` | Yes | N/A |
| `PostToolUse` | No | After git commit: suggest content extraction |
| `PostToolUseFailure` | No | N/A |
| `PermissionRequest` | Yes | N/A |
| `SubagentStart` | No | Initialize content writer subagent |
| `SubagentStop` | No | Collect content drafts from subagent |
| `Stop` | Yes | **Best trigger**: check if phase completed, suggest content |
| `TeammateIdle` | Yes | Assign content generation to idle teammate |
| `TaskCompleted` | Yes | **Best trigger**: on phase/milestone task completion |
| `PreCompact` | No | Backup content-relevant decisions before compaction |
| `Notification` | No | N/A |
| `Setup` | No | One-time content pipeline setup |

### Recommended Hook Configurations

#### Hook 1: Post-Phase Content Suggestion (Stop hook)

When Claude finishes a significant piece of work, check if planning artifacts were updated and suggest content extraction:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-content-opportunity.py"
          }
        ]
      }
    ]
  }
}
```

The script `check-content-opportunity.py` would:
1. Check `git diff --name-only HEAD~5` for changes to `.planning/` files
2. If IMPROVEMENT or RESEARCH files changed, output a JSON suggestion
3. The suggestion appears in Claude's context for the next turn

#### Hook 2: Post-Commit Content Nudge (PostToolUse on Bash)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/post-commit-content-check.sh"
          }
        ]
      }
    ]
  }
}
```

The shell script checks if the last Bash command was a git commit touching planning files, and if so, outputs a reminder.

#### Hook 3: TaskCompleted Content Generation

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/task-content-trigger.py"
          }
        ]
      }
    ]
  }
}
```

This is the most targeted option. When a planning phase task is marked complete, automatically suggest (or spawn) content generation.

### Key Constraint

Hooks execute shell commands and receive JSON on stdin. They **cannot** directly invoke Claude or spawn subagents. They can only:
- Output text that gets injected into Claude's context
- Return exit codes (0 = continue, non-zero = block for blocking hooks)
- Return JSON for tool-specific decisions (PreToolUse, PermissionRequest)

For automated content generation, hooks serve as **triggers** that remind or prompt; the actual generation must happen within a Claude session (skill invocation or subagent).

---

## 4. Agent Teams Patterns for Content Generation

### Architecture: Content Writer as a Teammate

Agent Teams (released Feb 5, 2026 with Opus 4.6) enable multiple Claude Code sessions to coordinate via a shared task list. This is fundamentally different from subagents:

| Feature | Subagents | Agent Teams |
|---------|-----------|-------------|
| Communication | Report back to parent only | Shared task list, visible to all |
| Context | Forked from parent | Independent sessions |
| Coordination | Parent orchestrates | Self-coordinating |
| Parallelism | Spawned by parent | True parallel sessions |

### Pattern: Content Writer Teammate

Define a custom agent at `.claude/agents/content-writer.md`:

```yaml
---
name: content-writer
description: |
  Reads project planning artifacts and produces content drafts for
  LinkedIn and blog. Operates as a teammate that picks up content
  tasks from the shared task list.
model: sonnet
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git log*)
  - Write
disallowedTools:
  - Bash
  - Edit
---

# Content Writer Agent

You are a technical content writer who transforms engineering artifacts
into compelling professional content.

## Your Role
- Monitor the team task list for content generation tasks
- Read .planning/ artifacts referenced in the task
- Produce drafts in the specified format (LinkedIn post, blog article, thread)
- Write drafts to .content/drafts/
- Mark the task complete with a summary of what was produced

## Content Standards
- Technical but accessible to senior engineers and tech leaders
- Lead with the insight, not the process
- Use concrete numbers and specifics
- Honest about challenges (this builds credibility)
- No jargon without context

## Source Reading Order
1. The specific file(s) referenced in the task
2. .planning/STATE.md for context
3. Related IMPROVEMENT files in the same phase directory
4. git log for timeline context

## Output Format
Always write to: .content/drafts/{YYYY-MM-DD}-{slug}.md
Include YAML frontmatter:
  - title
  - format (linkedin-post | blog-article | thread)
  - source_files (list of artifacts used)
  - status: draft
  - date_generated
```

### Workflow with Agent Teams

```
Main developer session (working on phase 3.2)
  |
  |-- Completes IMPROVEMENT-P14.md
  |-- Creates task: "Generate LinkedIn post from IMPROVEMENT-P14 insights"
  |
Content Writer teammate (picks up task)
  |
  |-- Reads IMPROVEMENT-P14.md
  |-- Reads STATE.md for context
  |-- Writes .content/drafts/2026-02-20-reasoning-eval-insights.md
  |-- Marks task complete
  |
Main session continues working (no context cost)
```

### Pattern: Subagent (simpler, no Agent Teams needed)

For projects not yet using Agent Teams, a subagent approach works:

```
User: "Turn the phase 3.1c learnings into a LinkedIn post"

Claude (orchestrator):
  1. Reads STATE.md, identifies relevant artifacts
  2. Spawns subagent with content-writer agent definition
  3. Subagent reads artifacts, produces draft
  4. Subagent returns draft summary
  5. Orchestrator presents draft for review
```

This is simpler but blocks the main session while the subagent works.

---

## 5. MCP Servers for Publishing

### LinkedIn Publishing

| MCP Server | GitHub | Status | Features |
|-----------|--------|--------|----------|
| `linkedin-mcp-server` | [Dishant27/linkedin-mcp-server](https://github.com/Dishant27/linkedin-mcp-server) | Active (40 stars, updated Feb 2026) | Post creation, profile search, messaging, network stats |
| `linkedin-mcpserver` | [felipfr/linkedin-mcpserver](https://github.com/felipfr/linkedin-mcpserver) | Active | Profile search, job search, messaging, posting |
| LinkedIn MCP (Apify) | [apify.com/mcp/linkedin-mcp-server](https://apify.com/mcp/linkedin-mcp-server) | Active (managed service) | Profile scraping, data extraction. Read-only, no posting. |

**LinkedIn API requirements for posting:**
- LinkedIn Developer Account with app created at https://www.linkedin.com/developers/
- OAuth 2.0 scopes: `w_member_social` (for posting), `openid`, `profile`
- API endpoint: `POST https://api.linkedin.com/v2/ugcPosts`
- Token refresh needed (60-day expiry for 3-legged OAuth)
- Rate limits apply (daily post limits vary by app approval level)

**Recommended:** Use Dishant27/linkedin-mcp-server. It's TypeScript, MCP-compatible, and actively maintained. Configuration:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "node",
      "args": ["/path/to/linkedin-mcp-server/dist/index.js"],
      "env": {
        "LINKEDIN_ACCESS_TOKEN": "${LINKEDIN_ACCESS_TOKEN}",
        "LINKEDIN_PERSON_URN": "${LINKEDIN_PERSON_URN}"
      }
    }
  }
}
```

### Blog Platform Publishing

| MCP Server | Platform | GitHub/Source | Features |
|-----------|----------|---------------|----------|
| `ghost-mcp` | Ghost CMS | [fanyangmeng/ghost-mcp](https://fanyangmeng.blog/introducing-ghost-mcp-a-model-context-protocol-server-for-ghost-cms/) | Full CRUD: create/update/delete posts, manage tags, member management |
| Ghost Admin API MCP | Ghost CMS | [fastmcp.me](https://fastmcp.me/MCP/Details/743/ghost-admin-api) | Admin API integration for automated publishing workflows |
| Hashnode MCP | Hashnode | [sbmagar13/hashnode-mcp](https://sbmagar13.medium.com/introduction-619fe9b91744) | Create, update, publish articles; search posts; fetch metadata |
| BlogCaster MCP | Hashnode + Dev.to | [DEV Community post](https://dev.to/bamacharan/i-built-an-mcp-server-that-publishes-blogs-automatically-and-this-post-was-published-through-it-4gjh) | Multi-platform publishing from single command. Uses Cloudflare KV for tokens. |
| WordPress MCP | WordPress | [webkul.com guide](https://webkul.com/blog/create-mcp-server-wordpress/) | Content management via WordPress REST API |

### Multi-Platform Publishing Strategy

For maximum reach, the recommended stack is:

```
Content Writer Agent/Skill
        |
        v
  .content/drafts/{date}-{slug}.md  (local draft, human review)
        |
        v
  /content-publish skill (human-triggered)
        |
        +-- LinkedIn MCP --> linkedin-mcp-server --> LinkedIn API
        +-- Blog MCP -----> ghost-mcp or hashnode-mcp --> Blog platform
        +-- (optional) --> Dev.to API (simple REST, no MCP needed)
```

**Critical design decision:** Never auto-publish. Always produce drafts that require human review and explicit `/content-publish` invocation.

---

## 6. Recommended Implementation Plan

### Phase 1: Content Extraction Skill (1-2 hours)

Create `.claude/skills/content-from-artifacts/SKILL.md` that:
- Reads `.planning/` artifacts on demand
- Produces LinkedIn post and blog article drafts
- Writes to `.content/drafts/`

No hooks, no MCP, no agents. Just a skill you invoke manually.

### Phase 2: Content Writer Agent (1 hour)

Create `.claude/agents/content-writer.md` that:
- Can be spawned as a subagent for content tasks
- Has read-only access to project files
- Follows voice/format guidelines

### Phase 3: Hook-Based Triggers (30 minutes)

Add a `Stop` hook that:
- Checks if `.planning/` files were modified in the session
- Outputs a suggestion to run `/content-from-artifacts`

### Phase 4: Publishing MCP Integration (2-3 hours)

- Set up LinkedIn MCP server with OAuth tokens
- Set up Ghost/Hashnode MCP server
- Create `/content-publish` skill that reads from `.content/drafts/` and publishes

### Phase 5: Agent Teams Integration (when ready)

- Register content-writer as a teammate
- Main session creates content tasks automatically after phase completions
- Content writer picks up tasks asynchronously

---

## 7. Key Takeaways

1. **The skill pattern is proven.** Changelog generators, content extraction skills, and newsletter writing skills are well-established in the community. The gap is specifically in mining `.planning/` artifacts for social/blog content.

2. **Hooks are triggers, not generators.** They can nudge you to create content but cannot independently run Claude. Use them for reminders and context injection.

3. **Agent Teams is the ideal architecture** for background content generation, but subagents work fine as a simpler starting point.

4. **MCP servers exist for LinkedIn, Ghost, Hashnode, WordPress, and Dev.to.** The LinkedIn MCP ecosystem is newer but functional. Ghost MCP is the most mature for blog publishing.

5. **Never auto-publish.** The pipeline should be: artifact mining -> draft generation -> human review -> explicit publish command. The draft step is where most value is created.

6. **Start with the skill, not the plumbing.** The highest-value piece is the SKILL.md that knows how to read your specific `.planning/` structure and extract compelling content. The publishing infrastructure is secondary.
