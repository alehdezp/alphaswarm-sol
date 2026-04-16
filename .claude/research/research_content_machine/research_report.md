# Research Report: The Content Machine

**Date:** 2026-02-20
**Sources:** 7 parallel research agents, 80+ web searches, 10 ecosystem repos crawled
**Confidence:** HIGH (patterns well-established, tools verified, multiple independent sources converge)

---

## Executive Summary

Building a "content machine" that turns daily project work into publishable content requires **not** a publishing pipeline — it requires a **capture system** embedded into the way you already work. The research across 7 agents converges on one finding:

> **The best developer-writers don't create content. They capture the byproducts of genuine work.**

The system has three layers: (1) zero-friction capture during work, (2) a lightweight backlog with hard limits, and (3) weekly batch refinement with AI assistance for drafting (not thinking). The human owns the ideas, structure, and voice. AI accelerates the middle — research expansion, draft generation, formatting. Content is NOT published automatically. It's drafted for human editing and personalization.

**The 80/20:** A SessionEnd hook + a single markdown backlog file + 90 minutes on Sunday = 2-4 published posts per month. Everything else is enhancement.

---

## Part 1: The Philosophy (What Makes Content Good)

### The Discovery Narrative Pattern

Across all domains (cybersecurity, Rust, web3, AI tooling), the most effective content format is the **discovery narrative** — writing that preserves the order of discovery, not the logical order of explanation.

| Creator | Domain | Technique |
|---------|--------|-----------|
| **samczsun** | Web3 security | Starts with the moment of discovery, walks through reasoning including wrong turns, shows concrete stakes ($350M at risk) |
| **fasterthanlime** | Rust/systems | "I was sick of articles glossing over particulars. I made it my trademark to go deep into little details." |
| **Trail of Bits** | Security | Every audit produces internal artifacts; blog posts extract the "why and how" with real numbers |
| **Julia Evans** | Debugging | Starts with genuine confusion, shows investigation process, uses simple language for complex topics |
| **Rekt News** | DeFi incidents | Adds sardonic editorial voice + connects individual incidents to systemic patterns |

### The Anti-Patterns That Kill Content

From Max Kreminski's research on "the dearth of the author" — AI-assisted content fails when it produces text "sparse in expressive intent." Concrete signals:

1. **No friction, no stakes** — Everything proceeds smoothly. Real work is messy.
2. **Conclusion-first** — AI states the answer, then supports it. Authentic content follows the journey.
3. **No temporal anchoring** — "It was just after lunch when I got a push notification" vs generic timelessness.
4. **Uniform hedging** — Real experts are confident about what they know, explicitly uncertain about what they don't.
5. **Missing "why I care"** — The strongest authenticity marker is personal investment.

### The Ownership-Efficiency Paradox

From Zhang et al. (arXiv 2601.10236, Jan 2026): **More AI help = less authorial ownership feeling.** The strongest intervention is providing your own writing samples as few-shot context. Style descriptions are less effective than actual examples of your writing.

**Design implication:** AI should expand your search space (angles, objections, structures) BEFORE you commit, then draft WITHIN your committed structure. Never let AI choose the structure — that's where your thinking happens.

---

## Part 2: The Capture System (Zero-Friction)

### Layer 1: Automatic Capture

| Mechanism | Friction | Quality | Setup |
|-----------|----------|---------|-------|
| **SessionEnd agent hook** | Zero (automatic) | Medium — may miss nuance | 10 min one-time |
| **Conventional commits** | Zero (already best practice) | Low — but cumulative | Already done |
| **`# CONTENT:` code comments** | Near-zero (30 sec) | High | Convention only |
| **"Shipped" notes** after significant work | Low (2 min) | High | Habit |

**The SessionEnd hook** is the highest-ROI capture point:

```json
{
  "hooks": {
    "SessionEnd": [{
      "hooks": [{
        "type": "agent",
        "prompt": "Review this session. Extract: (1) the main problem solved, (2) any non-obvious decisions, (3) anything interesting to other developers. Write a 3-5 line content seed to .content/backlog.md. Only write if genuinely interesting — skip routine tasks."
      }]
    }]
  }
}
```

### Layer 2: The Backlog (Single File, Hard Limits)

```markdown
# Content Backlog

## Ready to Write (max 5)
- [ ] How we designed behavioral labeling — decisions, tradeoffs, surprises
- [ ] The 3-day reentrancy false positive debugging story

## Seeds (max 20 — prune weekly, expire at 30 days)
- 2026-02-20: SessionEnd hooks as content capture — zero-friction pattern
- 2026-02-18: Why names lie and behavior doesn't — the core insight

## Published
- [x] 2026-02-01 → "Why Behavioral Signatures Beat Name-Based Detection"
```

**Rules:** Max 5 ready items. Max 20 seeds. 30-day expiration. In the repo (not a separate tool). Delete ruthlessly.

### Layer 3: Content Seeds from MSD Phase Work

At phase boundaries, add a lightweight checkpoint:

```
plan-phase → execute-phase → [CONTENT CHECKPOINT] → next phase
```

The checkpoint is one question: **"What 1-2 things from this phase would be interesting to others?"** If nothing, skip. This is NOT "write a blog post per phase." It's a 10-second "who cares?" test.

**MSD artifact → content mapping:**

| MSD Artifact | Content Potential | Format |
|-------------|-------------------|--------|
| CONTEXT.md decisions | **High** — each locked decision = one post | "What We Chose and Why" |
| IMPROVEMENT passes (adversarial) | **Very High** — "We assumed X, discovered Y" | Experiment report / failure story |
| IMPROVEMENT (rejected items) | **High** — "N Ideas We Killed (And Why)" | Contrarian listicle |
| RESEARCH.md | **High** — landscape analysis, prior art | Deep-dive comparison |
| IMPROVEMENT-DIGEST (convergence) | **Medium** — accumulated learnings | "Lessons Learned" listicle |
| Execution feedback | **Medium** — "what went wrong" | Debugging narrative |
| Gap analyses | **Medium** — "state of X" overview | Opinion piece |

---

## Part 3: The Refinement Workflow (Weekly Batch)

### The Pattern: Capture All Week, Write on Sunday

| Day | Activity | Time |
|-----|----------|------|
| Mon-Fri | Seeds accumulate automatically (hooks, commits, notes) | 0 min/day |
| Sunday | Review seeds, pick 1-2, expand to drafts | 60-90 min |
| Monday | Quick human edit, publish | 15-30 min |

### AI-Assisted Drafting (The "Writing as Search" Method)

From ArthurJ (dev.to): "Think of writing as a search problem. AI helps you explore the search space BEFORE you commit."

1. **Human writes bullet points** (the ideas, opinions, claims)
2. **AI expands search space:** "Give me 5 angles on this idea" / "What's the strongest objection?"
3. **Human commits** to one angle and one structure
4. **AI drafts** within the committed structure, using 3-5 writing samples as voice context
5. **Human edits:** injects anecdotes, cuts fluff, adds opinions, does read-aloud test
6. **AI tightens** with anti-slop constraints (banlist: delve, landscape, realm, "it's worth noting")
7. **Human final pass:** introduction and conclusion are always yours

### Voice Preservation Rules

- **Never let AI choose the structure** — that's where your thinking happens
- **Always provide 3-5 writing samples** as few-shot context
- **Maintain a banlist** of AI-slop patterns in your skill's system prompt
- **The intro and conclusion are yours** — AI can draft the middle
- **Read-aloud test:** If you wouldn't say it to a friend, it's AI slop

---

## Part 4: Content Formats by Domain

### Cybersecurity / Smart Contract Security

| Format | Platform | Template |
|--------|----------|----------|
| **Vulnerability narrative** | Blog (canonical) | The Hunt → The Clue → The Vulnerability → The Impact → The Fix → The Lesson |
| **"How would you exploit this?"** | LinkedIn + Twitter | Code snippet + question + "answer tomorrow" |
| **Metric reveal** | LinkedIn → Blog | "13% precision — here's why that's honest" + methodology + what it means |
| **Tool comparison** | Blog | "Slither vs Aderyn vs our approach — what each catches" |
| **CTF write-up** | Blog → Medium/InfoSec | Challenge → Recon → Exploit → Lessons |
| **Attack flow diagram** | LinkedIn (image) | ASCII art in blog, designed graphics for social |

### Rust / Solidity Learning

| Format | Platform | Template |
|--------|----------|----------|
| **TIL (Today I Learned)** | Dev.to + GitHub + LinkedIn | Context → Problem → Discovery → Why It Matters |
| **Weekly learning log** | Dev.to | What I Learned → What Surprised Me → What I'm Stuck On → Code Example |
| **"I finally understood X"** | Blog + LinkedIn | The confusion → wrong mental models → the "aha" → correct model |
| **Progressive series** | Blog | Part 1 (intro) → Part 2 (intermediate) → Part 3 (advanced) → Part 4 (meta/honest) |

### Claude Code / AI Tooling

| Format | Platform | Template |
|--------|----------|----------|
| **"How I automated X"** | Blog + LinkedIn | The repetitive task → the skill/hook → before/after |
| **Agent architecture post** | Blog | Problem → Design choices → What worked → What didn't |
| **"What the AI agents found"** | LinkedIn | This week's debate results between attacker/defender/verifier |
| **Discovery narrative** | Blog | "I was building X when the agent did something unexpected..." |

### LinkedIn Specifically

- **Carousels (PDF):** 6.60% engagement, highest format. 8-12 slides, first slide = hook
- **Long text:** 1,250-3,000 chars optimal. Hook-Story-Insight-CTA structure
- **Unicode formatting** required (no markdown). Bold: U+1D400 range. Tools: Taplio, YayText
- **3-5 hashtags** at end, not inline. Niche > broad
- **Post frequency:** 2-4/week optimal

---

## Part 5: Tools & Infrastructure

### The Minimum Viable Stack

| Layer | Tool | Why |
|-------|------|-----|
| **Capture** | SessionEnd hook + `.content/backlog.md` | Zero friction, automatic |
| **Writing** | Claude Code + custom `/content-draft` skill | Uses voice samples, anti-slop banlist |
| **Blog** | Ghost or Hugo/Astro (static) | Ghost for newsletter combo; static for simplicity |
| **Newsletter** | Listmonk (self-hosted, 16k stars) or Buttondown | API-first, markdown-native |
| **Social** | Postiz (26k stars, open-source) | API + CLI for programmatic scheduling |
| **TIL** | GitHub repo + GitHub Actions (simonw pattern) | Auto-index, auto-deploy |
| **Knowledge garden** | Quartz (~7k stars) | Markdown → navigable website with graph view |

### Ecosystem Skills Worth Adopting

| Skill/Tool | Source | What It Gives You |
|------------|--------|-------------------|
| **klaude-blog** | nickwinder/klaude-blog | End-to-end Claude Code blog automation template with CLAUDE.md-as-voice-config |
| **marketingskills** | coreyhaines31/marketingskills (8.5k stars) | 29 marketing skills including `content-strategy`, `social-content`, `copywriting` |
| **Book Factory** | robertguss/claude-code-toolkit | Writing skill with voice capture + ghost writing pipeline |
| **X Article Publisher** | wshuyi/x-article-publisher-skill (589 stars) | Complete Markdown-to-X pipeline via Playwright — reusable pattern |
| **content-research-writer** | ComposioHQ/awesome-claude-skills | Writing partner skill for research, outline, draft, refine |
| **ClawFu MCP** | guia-matthieu/clawfu-skills | 22 content skills + newsletter strategy as MCP tools (Schwartz, Cialdini frameworks) |

### MCP Servers for Publishing

| Platform | Server | Maturity |
|----------|--------|----------|
| **WordPress** | WordPress/mcp-adapter (official Automattic) | High — official backing |
| **Ghost** | mtane0412/ghost-mcp-server | Moderate — full Admin API |
| **Dev.to** | BlogCaster MCP | Early — multi-platform publishing |
| **LinkedIn** | mcpflow/mcp-server-linkedin | Early — basic posting |

---

## Part 6: MSD Integration (Simple, Not Verbose)

### The Principle

Content generation is NOT a separate MSD phase. It's a **lightweight checkpoint** at phase boundaries + an **end-of-milestone retrospective**.

### Integration Points

1. **SessionEnd hook** (automatic) — captures seeds during any MSD work
2. **Phase completion** — the "who cares?" 10-second test before moving on
3. **End of milestone** — the retrospective that mines all artifacts (P1-MAN-01 from earlier this session)
4. **`/content-draft` skill** (manual) — invoked when you decide to write, reads `.planning/` artifacts

### What NOT to Do

- Do NOT add a "content phase" to every milestone
- Do NOT require blog posts as phase deliverables
- Do NOT auto-publish anything — always draft for human review
- Do NOT add elaborate frontmatter to every planning doc — only to the ones you'll actually mine
- Do NOT create a separate content management system — use the backlog file

### The End-of-Milestone Retrospective (P1-MAN-01)

At phase end, a single skill mines all MSD artifacts:
- CONTEXT.md decisions → "What We Chose and Why" posts
- IMPROVEMENT passes → experiment reports, failure stories
- RESEARCH.md → landscape comparisons, deep-dives
- Adversarial lenses → contrarian takes
- Execution feedback → debugging narratives

Output: structured docs in `docs/research/` that double as blog draft source material.

---

## Part 7: Implementation Roadmap

| Phase | What | Effort | Dependencies |
|-------|------|--------|-------------|
| **1** | Add SessionEnd agent hook for content seeds | 15 min | None |
| **2** | Create `.content/backlog.md` with template | 5 min | None |
| **3** | Build `/content-draft` skill (reads backlog + .planning/) | 2 hrs | None |
| **4** | Add anti-slop banlist + 3-5 writing samples to skill | 30 min | Phase 3 |
| **5** | Set up blog (Ghost or Hugo/Astro + CI/CD) | 2-3 hrs | None |
| **6** | Create TIL repo with GitHub Actions (simonw pattern) | 1 hr | None |
| **7** | Set up Postiz for social scheduling | 1 hr | Phase 5 |
| **8** | Add MCP servers (Ghost + LinkedIn) | 2 hrs | Phase 5 |
| **9** | Build `/content-publish` skill | 1 hr | Phase 8 |
| **10** | Schedule first "Content Sunday" and do it | 90 min | Phase 3 |

**Start with Phases 1-3.** The hook + backlog + draft skill is the entire content machine. Everything else is distribution and polish.

---

## Part 8: Key Insights (Cross-Agent Synthesis)

### Convergent Findings (All 7 Agents Agree)

1. **Content is a byproduct of work, not a separate activity.** The best developer-writers don't "create content" — they capture what they learn while building. (Agents 1, 4, 5)

2. **Failure stories outperform success stories 3-5x on engagement.** Your IMPROVEMENT files (adversarial reviews finding flaws) and rejected ideas are the highest-value raw material. (Agents 1, 3, 4)

3. **The capture system that works is the one with lowest activation energy.** Any system requiring > 30 seconds of effort per capture will be abandoned within 2 weeks. (Agents 1, 4, 5)

4. **AI should expand your options, not make your choices.** Use AI for "give me 5 angles" and "what's the objection?" — not for "write me a blog post." (Agents 2, 4)

5. **Few-shot writing samples beat any style description.** Provide 3-5 examples of your actual writing. (Agent 2)

6. **No end-to-end research-to-blog-post skill exists in the ecosystem.** All building blocks exist (research agents, writing skills, publishers) but nobody has assembled the full pipeline. This is the gap. (Agents 6, 7)

7. **Weekly batch processing beats daily content creation.** Collect all week automatically, expand 1-2 seeds in a focused 90-minute Sunday session. (Agent 5)

### Unique Findings Per Agent

| Agent | Unique Finding |
|-------|---------------|
| 1 (Developer Machines) | **The "repurposing trap"** — automated content repurposing across platforms is "currency debasement." Pick one primary medium and invest deeply. |
| 2 (AI Frameworks) | **Structural AI tells are harder to fix than word tells.** Banning "delve" is easy; fixing symmetric sections and uniform paragraph blocks requires owning the outline yourself. |
| 3 (Content Formats) | **LinkedIn carousels at 6.60% engagement** are 3x higher than other formats. For technical content, the "How would you exploit this?" engagement post creates two posts from one topic. |
| 4 (Knowledge Extraction) | **Every decision is already 80% of a blog post.** ADR sections map 1:1 to blog post sections. The missing 20% is narrative framing. |
| 5 (Workflow Integration) | **The `# CONTENT:` code comment convention** + grep extraction is near-zero-friction in-code annotation. Also: voice-to-text is reportedly 3x faster for prose than typing. |
| 6 (Ecosystem Mining) | **coreyhaines31/marketingskills** (8.5k stars) has 29 production skills including content-strategy, social-content, and email-sequence — the richest content skill set in the ecosystem. |
| 7 (Community Frameworks) | **Postiz** (26k stars) with API + CLI agent solves the distribution problem. **simonw's TIL pattern** with GitHub Actions + Datasette is the gold standard for developer micro-content. |

---

## References

### People to Study
- **samczsun** (samczsun.com) — vulnerability storytelling
- **fasterthanlime** (fasterthanli.me) — exploratory long-form
- **Julia Evans** (jvns.ca) — debugging narratives, wizard zines
- **swyx** (swyx.io) — learning in public philosophy
- **Trail of Bits** (blog.trailofbits.com) — research-to-content pipeline
- **Rekt News** (rekt.news) — editorial voice on incidents
- **Simon Willison** (simonwillison.net) — TIL at scale

### Tools
- Postiz (postiz.com) — open-source social scheduling, 26k stars
- Listmonk (listmonk.app) — self-hosted newsletters, 16k stars
- Quartz (quartz.jzhao.xyz) — digital garden framework, ~7k stars
- Ghost (ghost.org) — blog + newsletter CMS, 48k stars
- klaude-blog (nickwinder/klaude-blog) — Claude Code blog automation
- marketingskills (coreyhaines31) — 29 content skills, 8.5k stars

### Research
- Zhang et al., "Who Owns the Text?" (arXiv 2601.10236) — ownership-efficiency paradox
- Kreminski, "The Dearth of the Author" — AI content sparse in expressive intent
- Bouchard/Towards AI — structural vs word-level AI tells
- Stripe Writing Culture (slab.com/blog) — papertrails vs curations
- swyx, "Learn In Public" (swyx.io) — learning exhaust philosophy
- MADR v4.0 (adr.github.io) — decision records as content source
