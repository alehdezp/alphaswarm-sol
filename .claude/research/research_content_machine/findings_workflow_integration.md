# Content Generation Integrated into Development Workflows

Research findings on minimum-friction content capture during development work.

**Date:** 2026-02-20
**Confidence:** High (based on 12+ web searches, official docs, real-world tools)

---

## Executive Summary

The highest-ROI approach is a **three-layer system**: (1) automatic capture via Claude Code hooks at session boundaries, (2) conventional commits as content signals that feed a lightweight content backlog, and (3) a weekly batch-processing session that turns seeds into published content. Everything else is optional amplification.

The core insight: **content should be a byproduct of work you're already doing, not a separate activity.** The systems that survive are the ones where capture requires zero extra effort, and refinement is batched into a single focused session.

---

## 1. Git-Based Content Triggers

### Conventional Commits as Content Signals

Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`) are already structured metadata about what happened. They are the lowest-friction content signal because developers are already writing them.

**Key tools:**
- **release-please** (Google, github.com/googleapis/release-please, 6.4k stars): Parses git history using conventional commits, auto-generates CHANGELOGs and release PRs. The CHANGELOG it produces is already a content draft — a list of what changed and why, organized by version.
- **conventional-changelog** (github.com/conventional-changelog/conventional-changelog, 8.4k stars): The original ecosystem. Generates changelogs from commit messages. Supports Angular, Atom, ESLint presets.
- **Commitlint + Husky**: Enforce conventional commit format at the git hook level. Ensures every commit is a parseable content signal.

**The content extraction pattern:**
1. Use conventional commits (you should already be doing this)
2. Let release-please auto-generate a CHANGELOG on merge to main
3. At content-batch time, scan the CHANGELOG for items worth expanding
4. A `feat:` commit that solved a hard problem = blog seed. A `fix:` that took 3 days = debugging story seed.

**AI-enhanced changelog generation:**
Scott Hebert's approach (slaptijack.com): A post-commit git hook that sends the diff to OpenAI to generate an intelligent changelog entry — not just the commit message, but a human-readable summary of what actually changed. This is a richer content signal than the raw commit.

```bash
# post-commit hook concept (simplified)
DIFF=$(git diff HEAD~1 HEAD)
SUMMARY=$(echo "$DIFF" | llm "Summarize this code change in 2-3 sentences for a changelog")
echo "- $SUMMARY" >> .content/seeds.md
```

**Friction score: 1/10** — Conventional commits are already best practice. The tooling is mature.

---

## 2. Claude Code Hooks for Content Capture

### The 12+ Lifecycle Events

Claude Code hooks fire deterministically at specific points in the agent lifecycle. The key events for content capture:

| Hook Event | When It Fires | Can Block? | Content Use |
|---|---|---|---|
| **SessionStart** | Session begins/resumes | No | Load content backlog context |
| **SessionEnd** | Session terminates | No | **Primary capture point** — generate session content seed |
| **PreCompact** | Before context compaction | No | Save full transcript before it's compressed |
| **Stop** | Claude finishes a response | No | Capture per-task summaries |
| **SubagentStop** | Subagent completes | No | Capture agent findings as content seeds |
| **PostToolUse** | After any tool runs | No | Log interesting tool outputs |

### The SessionEnd Content Seed Hook

This is the highest-value integration point. When a session ends, a hook can automatically extract a content seed from what happened.

**Implementation pattern (UV single-file script):**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic"]
# ///
"""SessionEnd hook: extract content seed from session."""

import json
import sys
import os
from datetime import datetime

# Read hook input from stdin
hook_input = json.load(sys.stdin)
session_id = hook_input.get("session_id", "unknown")

# The transcript_summary is available in the hook context
# Write a minimal seed to the content backlog
seed = {
    "date": datetime.now().isoformat(),
    "session_id": session_id,
    "type": "auto-capture",
    "status": "raw",
    # The actual summary gets appended by the hook command
}

backlog_path = os.path.expanduser("~/.content/seeds.jsonl")
os.makedirs(os.path.dirname(backlog_path), exist_ok=True)
with open(backlog_path, "a") as f:
    f.write(json.dumps(seed) + "\n")
```

**Settings configuration:**

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --script ~/.claude/hooks/content-seed.py"
          }
        ]
      }
    ]
  }
}
```

**Alternative: Agent-based hook for richer seeds.**
Instead of a simple command hook, use an agent-based hook that reads the session transcript and extracts: decisions made, problems solved, things learned, tools discovered.

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Review this session. Extract: (1) the main problem solved, (2) any non-obvious decisions or tradeoffs, (3) anything that would be interesting to other developers. Write a 3-5 line content seed in markdown to ~/.content/seeds.md with a date header. Only write if something genuinely interesting happened — skip routine tasks."
          }
        ]
      }
    ]
  }
}
```

**Exit code semantics:** Exit 0 = success, exit 2 = blocking (stops Claude). For content capture, always exit 0 — content seeds should never block work.

**Friction score: 2/10** — One-time setup, then fully automatic. The agent-based variant costs tokens per session but produces higher-quality seeds.

### Related Tools

- **claude-mem** (github.com/thedotmack/claude-mem): Plugin that automatically captures everything Claude does, compresses with AI, and injects into future sessions. Uses SQLite + Chroma for hybrid search. Captures observations, generates semantic summaries. Could be adapted to also emit content seeds.
- **Ars Contexta** (github.com/agenticnotetaking/arscontexta, 706 stars): Claude Code plugin that generates a complete "second brain" knowledge system from conversation. Derives folder structure, context files, processing pipeline, hooks, navigation maps, and note templates. More elaborate than needed for content capture, but the derivation approach (not templating) is interesting.
- **session-retrospective** (SkillMD.ai): A Claude Code skill for "iterative reflection, research, and improvement." Triggers: "session retrospective", "what did we learn." Produces agent-ready context documents. Directly applicable pattern.

---

## 3. Session Summary to Content Seed Pattern

### What to Capture

The minimum viable content seed from a session:

```markdown
## 2026-02-20 — [one-line title]

**Problem:** What was I trying to do?
**Insight:** What non-obvious thing did I learn or decide?
**Content angle:** Why would someone else care? (if nothing, skip)

Tags: #tooling #debugging #architecture (etc.)
```

That is 4 lines. It takes 30 seconds to review and either keep or discard. This is the minimum that is useful later.

### The Anti-Pattern: Elaborate Capture

The moment you add required fields, mandatory categorization, or structured templates, you've created a system people won't maintain. The research consistently shows: **the capture system that works is the one with the lowest activation energy.**

### Manual vs Automatic

| Approach | Friction | Quality | Recommended? |
|---|---|---|---|
| Fully automatic (SessionEnd agent hook) | Zero | Medium — may miss nuance | Yes, as baseline |
| Manual one-liner at session end | Low (30 sec) | High — you know what matters | Yes, as supplement |
| Elaborate template | High (5+ min) | High but rarely done | No |
| Voice memo after session | Low (60 sec) | High — captures thinking | Yes, if voice tooling exists |

**Best practice: automatic capture + optional manual annotation.** The hook writes a seed. You glance at it once a week during batch time and add a one-liner if something was genuinely interesting.

---

## 4. Phase-Integrated Content Generation

### The Pattern: End-of-Phase Content Checkpoint

In a phase-based planning system (like MSD improve-phase / plan-phase / execute-phase), content generation fits naturally at phase boundaries:

```
plan-phase → execute-phase → [CONTENT CHECKPOINT] → next plan-phase
```

**What the checkpoint does:**
1. The phase completion summary (which you're already writing) is the content seed
2. A short prompt asks: "What 1-2 things from this phase would be interesting to others?"
3. If anything, add a line to the content backlog. If nothing, skip.

**This is NOT "write a blog post per phase."** That is the anti-pattern — it makes content feel like busywork. Instead:

- Phase completes a feature: content seed = "how we designed X"
- Phase fixes a hard bug: content seed = "the debugging story of Y"
- Phase is routine: no content seed. That is fine.

### Amazon's "Working Backwards" as Inspiration

Amazon's PR/FAQ method writes the press release BEFORE building the product. The key insight: **articulating value for an audience is a design tool, not a marketing afterthought.**

For dev content, the lightweight version:

> Before starting a phase: write one sentence about who would care about the outcome and why. If nobody would, that is fine — it is just a maintenance phase. If someone would, you have a content hook.

This "who cares?" test at phase start costs 10 seconds and occasionally produces gold.

**Practical implementation in MSD:**

```yaml
# In phase definition (e.g., PHASE.md or phase config)
content_checkpoint:
  enabled: true
  trigger: phase_complete
  prompt: |
    Review the phase outcomes. What 1-2 things from this phase
    would be interesting to someone building similar systems?
    Add to .content/backlog.md if anything qualifies.
    Skip if nothing is notable.
```

---

## 5. The Content Backlog Pattern

### Why Most Content Backlogs Die

The universal anti-pattern: a Notion database / Trello board / GitHub project full of content ideas that nobody ever revisits. It grows, feels overwhelming, and gets abandoned.

**What kills backlogs:**
1. Too many items (no decay/pruning)
2. Items lack enough context to act on later
3. No scheduled processing time
4. Separate tool from where work happens

### The Surviving Pattern: Single Markdown File

A single file, in the repo, with a hard limit:

```markdown
# Content Backlog

## Ready to Write (max 5)
- [ ] How we designed the BSKG behavioral labeling system — decisions, tradeoffs, what surprised us
- [ ] The debugging story of the 3-day reentrancy false positive
- [ ] Voice-to-text for PR descriptions — 3x faster than typing

## Seeds (max 20 — prune weekly)
- 2026-02-20: SessionEnd hooks as content capture — zero-friction pattern
- 2026-02-18: Why conventional commits are actually a content strategy
- 2026-02-15: The graph-first reasoning insight — names lie, behavior doesn't

## Archived (older than 30 days, no longer interesting)
(delete these entirely — do not hoard)
```

**Rules that keep it alive:**
1. **Max 5 "Ready to Write"** — forces prioritization
2. **Max 20 Seeds** — when you add one, remove the least interesting
3. **Weekly prune** — if a seed is 30+ days old and you still haven't felt compelled, delete it
4. **In the repo** — not a separate tool. You see it during development.
5. **JSONL alternative** — for automated capture, append to `.content/seeds.jsonl`. The markdown file is the curated view.

### Tools for the Backlog

| Tool | Fit | Notes |
|---|---|---|
| **Single markdown file in repo** | Best for solo devs | Zero overhead, version controlled, visible |
| **GitHub Issues with `content` label** | Good for teams | Searchable, assignable, but separate from code |
| **Backlog.md** (github.com) | Good for structured work | Markdown-native task management in-repo. 3k+ stars |
| **Notion database** | Overkill for seeds | Only if you already live in Notion |
| **Obsidian vault** | Good if PKM-native | Wiki-links, graph view, but separate tool |

---

## 6. Minimum-Friction Content Capture

### Voice-to-Text During Work

The DEV Community article on voice-to-text for developers (dev.to/auratech) reports a striking finding: writing prose (PR descriptions, docs) via voice is **3x faster** than typing — not because of words-per-minute, but because dictation reduces the editing loop. You speak like you'd explain to a colleague, which is exactly the right tone for technical content.

**Recommended tools:**
- **WisprFlow** (wisprflow.ai): System-wide voice-to-text that learns technical terms. Works in IDEs, terminals, browsers. Context-aware. Best for daily coding + content dictation.
- **macOS Dictation** (built-in): Free, decent quality. Hit Fn-Fn to activate anywhere. Good enough for quick seeds.
- **Whisper API** (OpenAI): For building custom voice capture. Highest accuracy, 99 languages.
- **Granola** (granola.so): Meeting notes without a bot. Captures standups, 1:1s. Good for extracting content from verbal discussions.

**The pattern:** After a session where something interesting happened, dictate a 60-second voice note. The transcript is your content seed. This works especially well because the "just finished" context is still fresh.

### Quick Annotation Patterns

**Code comment tags:**
```python
# CONTENT: This algorithm choice is counterintuitive — worth explaining
# CONTENT: The tradeoff between X and Y here is a common design question
```

A grep for `# CONTENT:` during batch time extracts all in-code content markers. Zero friction at capture time.

**Commit message annotations:**
```
feat(bskg): add behavioral labeling for value transfers

CONTENT: The insight that function names are unreliable is worth a post.
The behavioral pattern R:bal -> X:out -> W:bal catches renamed functions.
```

These survive in git history and can be extracted by scripts.

### Anti-Pattern: Elaborate Capture Systems

Any system that requires:
- Opening a separate app
- Filling in more than 3 fields
- Categorizing before capturing
- Switching context from development

...will be abandoned within 2 weeks. The research is consistent on this.

---

## 7. Content as a Project Deliverable

### The "Write the Press Release First" Pattern

Amazon's Working Backwards: write a 1-page press release for the product BEFORE building it. Forces clarity on: who is the customer, what problem does this solve, why is this better than alternatives.

**Adapted for dev phases:**

> At phase start, write one sentence: "Someone building [X] would want to know [Y] because [Z]."

If you can not complete that sentence, the phase is not content-worthy. That is fine. If you can, you have a content hook that guides what to capture during the phase.

### Stripe's Developer Content Model

Stripe embeds writing into engineering culture. Engineers write blog posts about their work as a natural phase output. The key enablers:
1. Writing is valued as engineering work, not marketing work
2. There is an editorial process (draft review) but not an elaborate one
3. The content serves the developer audience directly (not translated by marketing)

### Practical Integration

```yaml
# Phase deliverables checklist
deliverables:
  - code: "Feature implementation"
  - tests: "Test coverage for new code"
  - docs: "Internal docs updated"
  - content_seed: "Optional: 1-2 line content seed if phase produced something interesting"
```

The `content_seed` is optional. Making it required turns it into busywork. Making it visible (in the checklist) keeps it top of mind.

---

## 8. The Refinement Workflow: Seeds to Published Content

### The Batch Processing Pattern

**Collect all week. Write on one day.**

The highest-output, lowest-friction pattern from the research:

| Day | Activity | Time |
|---|---|---|
| Mon-Fri | Seeds accumulate automatically (hooks, commits, manual notes) | 0 min/day |
| Saturday or Sunday | Review seeds, pick 1-2, expand to drafts | 60-90 min |
| Same session | LLM-assisted expansion: seed -> outline -> draft | (included above) |
| Monday | Quick human edit, publish | 15-30 min |

**Why this works:** It separates capture (continuous, zero-effort) from creation (focused, scheduled). No context-switching during development.

### The Expansion Pipeline

```
Seed (3-5 lines)
  → Outline (LLM: "expand this seed into a blog post outline")
  → Draft (LLM: "write the first draft from this outline, technical audience")
  → Human edit (you: fix tone, add nuance, verify accuracy)
  → Publish
```

Each LLM step takes 2-3 minutes. The human edit is 15-30 minutes for a ~1000 word post. Total: under 1 hour from seed to published, if the seed is good.

### Publishing Tools

| Platform | API? | Integration Pattern |
|---|---|---|
| **Ghost** (ghost.org) | Yes — Admin API | Create posts via `POST /ghost/api/admin/posts/`. Supports markdown body, tags, scheduling. JWT auth. Well-documented. |
| **Dev.to** | Yes — `POST /api/articles` | Simple JSON body with `body_markdown`, `title`, `tags`, `published`. API key auth. Trivially scriptable. |
| **Hashnode** | Yes — GraphQL | `createPublicationStory` mutation. Markdown body. API key auth. |
| **LinkedIn** | No good API for posts | Manual posting. Or use MCP tools if available. Buffer/Typefully for scheduling. |
| **Medium** | Limited API (deprecated) | Manual posting recommended. Cross-post from canonical source. |
| **Substack** | No API | Manual only. Best as newsletter aggregator of content published elsewhere. |

**Recommended simple pipeline:**
1. Write in markdown (already your natural format)
2. Publish to Ghost or your own site as canonical URL
3. Cross-post to Dev.to via API (set `canonical_url`)
4. Share link on LinkedIn/Twitter manually or via Buffer

```bash
# Publish to Dev.to from markdown file
curl -X POST https://dev.to/api/articles \
  -H "Content-Type: application/json" \
  -H "api-key: $DEVTO_API_KEY" \
  -d "{
    \"article\": {
      \"title\": \"$TITLE\",
      \"published\": false,
      \"body_markdown\": $(cat draft.md | jq -Rs .),
      \"tags\": [\"solidity\", \"security\", \"ai\"]
    }
  }"
```

---

## 9. Anti-Patterns to Avoid

### 1. The Elaborate Capture System
**Symptom:** A Notion database with 12 columns, a Zapier integration, and a weekly review ritual.
**Reality:** Nobody fills it in after the first week.
**Fix:** Single markdown file. Max 20 items. Prune ruthlessly.

### 2. The Content Backlog That Rots
**Symptom:** 47 "content ideas" from 6 months ago, none written.
**Reality:** If an idea doesn't compel you to write within 30 days, it never will.
**Fix:** Hard expiration. Delete seeds older than 30 days. If it was truly great, it will come back.

### 3. Automation That Produces Generic Output
**Symptom:** Auto-generated blog posts from changelogs that read like release notes.
**Reality:** AI can draft, but it cannot inject your unique perspective, your "I tried X and was surprised by Y" stories.
**Fix:** AI generates the skeleton. YOU add the insight, the opinion, the "here's what I actually think about this."

### 4. Content Debt Accumulation
**Symptom:** "I'll write about that later" repeated 50 times with no later.
**Reality:** Content debt, like technical debt, compounds. The context fades. The motivation fades.
**Fix:** Weekly batch processing. If you skip 2 weeks, declare bankruptcy on old seeds and start fresh.

### 5. Workflows That Feel Like Extra Work
**Symptom:** "I need to spend 30 minutes on my content system before I can start coding."
**Reality:** If content capture has any pre-work, it will be skipped.
**Fix:** Capture must be fully automatic or take < 30 seconds. Refinement is the only scheduled activity.

### 6. Separate Content Sessions
**Symptom:** "Content Tuesday" where you try to remember what you did last week.
**Reality:** By Tuesday, the context is gone. You stare at a blank page.
**Fix:** Seeds are captured in real-time (hooks, commits). Tuesday is just expansion, not recall.

---

## 10. Recommended Implementation: The Minimum Viable Content Machine

### Phase 1: Foundation (30 minutes setup)

1. **Adopt conventional commits** if not already using them (commitlint + husky)
2. **Create `.content/backlog.md`** with the template from section 5
3. **Add a SessionEnd hook** that appends a content seed (agent-based, from section 2)

### Phase 2: Capture Enrichment (15 minutes)

4. **Add `# CONTENT:` comment convention** to CLAUDE.md/coding guidelines
5. **Add the "who cares?" prompt** to phase completion checklists (section 4)

### Phase 3: Publishing Pipeline (1 hour)

6. **Set up Dev.to API key** and a simple publish script
7. **Schedule "Content Sunday"** — 60-90 minutes to process seeds into one post
8. **Set a calendar reminder** for the first 4 weeks (habit formation)

### Phase 4: Optimization (ongoing)

9. Track which seeds became published content (add `published: URL` to backlog entries)
10. Notice which capture sources produce the best seeds (hooks? commits? manual?)
11. Drop what does not work. Double down on what does.

### Expected Output

With this system running:
- **Seeds captured per week:** 5-15 (mostly automatic)
- **Seeds worth expanding:** 1-3 per week
- **Published posts per month:** 2-4
- **Time spent on content per week:** 60-90 minutes (batch day only)
- **Time spent on capture per week:** ~0 minutes (automatic)

---

## 11. Tool Reference

| Tool | URL | Purpose |
|---|---|---|
| release-please | github.com/googleapis/release-please | Auto-changelog from conventional commits |
| conventional-changelog | github.com/conventional-changelog/conventional-changelog | Changelog generation ecosystem |
| commitlint | commitlint.js.org | Enforce commit message format |
| Husky | typicode.github.io/husky | Git hooks made easy |
| Claude Code Hooks | code.claude.com/docs/en/hooks-guide | Lifecycle event automation |
| claude-mem | github.com/thedotmack/claude-mem | Session memory persistence plugin |
| Ars Contexta | github.com/agenticnotetaking/arscontexta | Knowledge system from conversation |
| WisprFlow | wisprflow.ai | Voice-to-text for developers |
| Granola | granola.so | Meeting notes without a bot |
| Backlog.md | github.com/backlog-md/backlog-md | Markdown-native task management |
| Ghost Admin API | ghost.org/docs/admin-api/ | Headless CMS with full API |
| Dev.to API | developers.forem.com/api | Developer blogging platform API |
| Buffer | buffer.com | Social media scheduling |

---

## 12. Key Findings Summary

| Finding | Confidence | Friction Level |
|---|---|---|
| Conventional commits are the best zero-cost content signal | High | Zero (already best practice) |
| SessionEnd agent hook is the highest-ROI capture mechanism | High | Zero after setup |
| Single markdown file backlog outlives all elaborate systems | High | Near-zero |
| Weekly batch processing beats daily content creation | High | Low (scheduled) |
| Voice-to-text is 3x faster than typing for prose | Medium | Low (tool required) |
| "Who cares?" test at phase start catches content opportunities | Medium | Near-zero (10 seconds) |
| Auto-generated content without human insight is worthless | High | N/A (design principle) |
| Content backlogs need hard expiration (30 days) or they rot | High | Near-zero (weekly prune) |
| The capture system that works is the one with lowest activation energy | High | Design principle |
