# Research Report: Project-to-Publication Pipeline

**Date:** 2026-02-20
**Sources:** 3 parallel research agents + 4 enrichment fetches from user-provided links
**Confidence:** HIGH (patterns well-established, tools verified)

---

## Executive Summary

Turning project artifacts into published content requires three things: (1) a Claude Code skill that mines `.planning/` artifacts, (2) documentation structured with extractable "key insight" sections, and (3) a publishing pipeline from drafts to platforms. The ecosystem already has all the pieces — no existing skill mines planning artifacts into social content, making this a clear gap to fill.

**The 80/20 recommendation:** Build a `/content-draft` skill (2 hours) and add `## Key Insight` sections to docs (5 min/doc). Everything else is optional enhancement.

---

## Part 1: What to Build

### 1A. `/content-draft` Skill (Priority 1 — build first)

A Claude Code skill at `.claude/skills/content-draft/SKILL.md` that:

```
Input:  .planning/ artifacts (CONTEXT, IMPROVEMENT, RESEARCH, DIGEST, gaps)
Output: .content/drafts/{date}-{slug}.md with YAML frontmatter
```

**Source priority for mining:**
1. IMPROVEMENT-P*.md files (highest signal — adversarial reviews, reframed ideas, failures)
2. RESEARCH.md files (prior art landscape, technical deep dives)
3. *-CONTEXT.md `<decisions>` and `<deferred>` sections (each decision = one LinkedIn post)
4. IMPROVEMENT-DIGEST.md (convergence data, rejection log = "what we tried and discarded")
5. PHILOSOPHY.md + architecture docs (contrarian positions, system design)
6. STATE.md + git log (timeline, milestones)

**Output formats:**
| Format | Length | Best For |
|--------|--------|----------|
| LinkedIn post | 150-300 words (1200-1500 chars optimal) | Single decision, single finding, single metric |
| Blog article | 1000-2500 words | Full experiment, deep dive, landscape review |
| Thread | 5-15 points | Accumulated learnings, listicle from DIGEST |

**Voice:** Technical but accessible. First person plural. Concrete examples. Honest about failures. Quantify where possible.

**Key design decision:** The skill is READ-ONLY. It produces drafts to `.content/drafts/`. Never auto-publishes.

### 1B. Content Writer Agent (Priority 2 — when using Agent Teams)

A `.claude/agents/content-writer.md` (sonnet model, read-only tools) that:
- Picks up content tasks from shared task list
- Reads artifacts referenced in the task
- Produces drafts while main session continues working
- Based on pattern from hooks-mastery: 5-step process (context → discovery → extraction → synthesis → output)

### 1C. Hook Triggers (Priority 3 — optional automation)

| Hook Event | Trigger | Action |
|-----------|---------|--------|
| `Stop` | `.planning/` files modified in session | Suggest `/content-draft` |
| `SessionEnd` | Session closes after phase work | Write content seed to `.content/seeds/` |
| `PostToolUse` (Bash) | Git commit touching `.planning/` | Flag for content review |

**Critical constraint:** Hooks can inject context but cannot invoke Claude. They're triggers, not generators.

---

## Part 2: How to Structure Docs for Content Extraction

### 2A. The Inverted Pyramid Rule

Internal docs bury the interesting parts. Add a `## Key Insight` section at the TOP of every publishable doc (2-3 sentences stating the finding in plain language). This becomes the blog lede and LinkedIn hook.

```markdown
## Key Insight

AI testing's hardest problem isn't catching failures — it's catching
success that's actually fabricated. We found our evaluator scored 100%
because it was tested on synthetic data crafted to match its own output.

[Rest of existing doc structure unchanged]
```

### 2B. Content Frontmatter (Minimal Version)

```yaml
---
title: "..."
date: 2026-02-20
content:
  publishable: true
  one_liner: "The most dangerous test failure is one that passes."
  topics: [ai-testing, evaluation]
---
```

Full schema (when needed):
- `extractable_as`: list of content types with `readiness` scores (0-1)
- `headline_candidates`: pre-written headlines captured when inspiration strikes
- `key_insight`: one-sentence takeaway
- `target_audience`: who cares (shapes tone)
- `content_freshness`: current | aging | stale

### 2C. Doc Type → Content Type Mapping

| Doc Type | Content Template | LinkedIn? | Blog? |
|----------|-----------------|-----------|-------|
| CONTEXT.md decisions | "What we chose and why" | Each decision = 1 post | Group 3-5 decisions |
| IMPROVEMENT (adversarial) | "What we tried and failed" | Reframed items = "We assumed X, discovered Y" | Full improvement pass narrative |
| IMPROVEMENT (rejected) | "What we deliberately discarded" | Contrarian takes | "N approaches we rejected" |
| RESEARCH.md | "Landscape review" | "We analyzed N approaches" | Full prior art comparison |
| IMPROVEMENT-DIGEST | "Lessons learned" listicle | Top 3-5 insights | Full accumulated learnings |
| PHILOSOPHY.md | "Contrarian take" | "Names lie. Behavior does not." | Deep dive on design philosophy |
| detection-baseline.md | "Metric reveal" | "13.3% precision. Here's why." | Full methodology + results |
| calibration-results.md | "Benchmark post" | Score comparison | Calibration methodology |

### 2D. Headline Examples from Your Existing Artifacts

| Artifact | Potential Headline |
|----------|-------------------|
| PHILOSOPHY.md | "Why AI Security Tools Fail: They Read Names, Not Behavior" |
| IMPROVEMENT (adversarial) | "Our AI Evaluator Scored Itself 100%. That Was the Bug." |
| CONTEXT.md (3.1e) | "We Built 26,000 Lines of Testing Code Before Running a Single Test" |
| RESEARCH (prior art) | "We Analyzed Every AI Security Tool. Here's What's Missing." |
| detection-baseline.md | "13.3% Precision: The Honest Benchmark Nobody Wants to Publish" |
| TESTING-PHILOSOPHY.md | "The Most Dangerous Test Is One That Passes" |
| IMPROVEMENT (deferred) | "6 Ideas We Killed (And Why They Deserved It)" |
| 3.1e novelty map | "Building Genuinely Novel AI: What Happens When There's No Prior Art" |

---

## Part 3: Publishing Pipeline

### 3A. Platform Stack

| Platform | API | Auth | Best For |
|----------|-----|------|----------|
| **Hugo/Astro** (primary blog) | Git push → CI/CD | None (static) | Long-form, technical deep dives |
| **Dev.to** | REST (`POST /api/articles`) | API key | Cross-post with canonical URL |
| **Hashnode** | GraphQL (`publishPost`) | Personal token | Cross-post with canonical URL |
| **LinkedIn** | MCP server or PostFast API | OAuth 2.0 | Short posts, decisions, metrics |
| **Ghost** | Admin API (JWT) | Admin key | If self-hosting blog |

### 3B. MCP Servers Available

| MCP Server | Platform | Status |
|-----------|----------|--------|
| [Dishant27/linkedin-mcp-server](https://github.com/Dishant27/linkedin-mcp-server) | LinkedIn | Active, 40 stars |
| [fanyangmeng/ghost-mcp](https://fanyangmeng.blog/introducing-ghost-mcp) | Ghost CMS | Most mature |
| [sbmagar13/hashnode-mcp](https://sbmagar13.medium.com/introduction-619fe9b91744) | Hashnode | Active |
| BlogCaster MCP | Hashnode + Dev.to | Multi-platform |
| WordPress MCP | WordPress | Active |

### 3C. Cross-Publishing Flow

```
.content/drafts/{date}-{slug}.md
  ↓ (human review + edit)
.content/published/{date}-{slug}.md
  ↓ (/content-publish skill)
  ├── Git push → Hugo/Astro → Primary blog (canonical URL)
  ├── Dev.to API → Cross-post (canonical → primary blog)
  ├── Hashnode API → Cross-post (canonical → primary blog)
  └── LinkedIn MCP → Formatted post (Unicode bold/italic, no markdown)
```

**LinkedIn formatting gotcha:** LinkedIn does NOT support markdown. Use Unicode characters for bold/italic. Tools: ConnectSafely.ai converter or custom script.

### 3D. LinkedIn Best Practices

- 3,000 char limit, 1,200-1,500 optimal for engagement
- Document/carousel posts get 6.60% engagement (highest)
- First 2 lines visible before "see more" — make them count
- 3-5 hashtags at end
- 2-4 posts per week optimal
- Personal profile posting requires Community Management API (restricted approval) — consider PostFast as intermediary

---

## Part 4: Implementation Roadmap

| Phase | What | Effort | Dependencies |
|-------|------|--------|-------------|
| **1** | Build `/content-draft` SKILL.md | 2 hours | None |
| **2** | Add `## Key Insight` to existing docs | 5 min/doc | None |
| **3** | Create `.claude/agents/content-writer.md` | 1 hour | Phase 1 |
| **4** | Add `Stop` hook for content suggestions | 30 min | Phase 1 |
| **5** | Set up Hugo/Astro blog with CI/CD | 2-3 hours | None |
| **6** | Add MCP servers (LinkedIn, Ghost/Hashnode) | 2-3 hours | Phase 5 |
| **7** | Create `/content-publish` skill | 1 hour | Phase 6 |
| **8** | Add content frontmatter to docs | 2-3 min/doc | Phase 2 |

**Start with Phase 1.** The skill is the highest-value piece. Everything else is enhancement.

---

## Part 5: Key Insights from Ecosystem Research

1. **No existing skill mines `.planning/` artifacts into social content.** This is a clear gap. Changelog generators (ComposioHQ, 23.6k stars) are the closest analogue but they mine git history, not planning docs.

2. **The continuous-learning pattern from everything-claude-code is directly applicable.** Their `/evolve` clusters session patterns into reusable skills — same pattern as extracting insights from IMPROVEMENT passes.

3. **The Book Factory (robertguss/claude-skills) proves multi-phase content pipelines work as Claude Code skills.** Research → outline → write → edit is a proven skill chain.

4. **Hooks are triggers, not generators.** They inject context into Claude's conversation but cannot independently run Claude. Use them for nudges.

5. **Agent Teams (Feb 2026) is the ideal architecture** for background content generation. Content writer teammate picks up tasks while main session continues. The hooks-mastery research agent pattern (5-step: context → discovery → extraction → synthesis → output) is the template.

6. **Failure stories outperform success stories 3-5x on engagement.** Your IMPROVEMENT files (adversarial reviews finding flaws) and CONTEXT deferred sections (rejected ideas) are the highest-value raw material.

7. **Each locked decision in CONTEXT.md is one LinkedIn post.** The "Implementation Decisions" section is a pre-formatted content goldmine.

8. **The "Seam" pattern** — leaving open questions, provisional decisions, explicit unknowns — your docs already do this naturally. These translate directly to engagement hooks in published content.

---

## References

### Community Resources (from user-provided links)
- awesome-claude-code: https://github.com/hesreallyhim/awesome-claude-code
- everything-claude-code: https://github.com/affaan-m/everything-claude-code
- claude-code-hooks-mastery: https://github.com/disler/claude-code-hooks-mastery
- claude-code-ultimate-guide: https://github.com/FlorianBruniaux/claude-code-ultimate-guide
- Book Factory: https://github.com/robertguss/claude-skills
- Blog commands: https://github.com/cloudartisan/cloudartisan.github.io/.claude/commands

### Publishing Tools
- LinkedIn MCP: https://github.com/Dishant27/linkedin-mcp-server
- Ghost MCP: https://fanyangmeng.blog/introducing-ghost-mcp
- PostFast API: https://postfa.st
- Late.dev API: https://getlate.dev
- ConnectSafely (MD→LinkedIn): https://connectsafely.ai
- MD2Ghost: https://github.com/MirisWisdom/MD2Ghost

### Research Methods
- Dunleavy, "How to write a blogpost from your journal article" (LSE)
- Sussex, "How to turn your research paper into a blog"
- Radensky et al., "LLM-Supported Planning of Research-Paper Blog Posts" (arXiv:2406.10370)
- MADR templates: https://adr.github.io/adr-templates/
