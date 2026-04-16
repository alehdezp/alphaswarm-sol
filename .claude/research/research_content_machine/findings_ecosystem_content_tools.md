# Ecosystem Research: Content Creation Tools in the Claude Code Ecosystem

**Date:** 2026-02-20
**Sources:** 10 GitHub repositories crawled and analyzed
**Focus:** Content creation, blogging, publishing, writing, newsletters, social media, knowledge-to-content pipelines

---

## 1. Ready-to-Use Content Skills & Agents

### 1.1 Marketing Skills Collection (coreyhaines31/marketingskills)
- **URL:** https://github.com/coreyhaines31/marketingskills
- **Stars:** 8.5k | **Maturity:** v1.2.0 (3 releases)
- **What:** 29 marketing skills for Claude Code covering CRO, copywriting, SEO, analytics, and growth engineering. Installable via `npx skills add`.
- **Content-relevant skills:**
  - `copywriting` -- Marketing page copy (headlines, hero sections, CTAs)
  - `copy-editing` -- Edit and polish existing copy
  - `content-strategy` -- Plan content strategy, decide what to create, topic coverage
  - `social-content` -- Social media content for LinkedIn, Twitter/X, Instagram
  - `email-sequence` -- Automated email flows and drip campaigns
  - `cold-email` -- B2B cold outreach sequences
  - `ad-creative` -- Bulk ad creative generation (headlines, descriptions, primary text)
  - `ai-seo` -- Optimize content for AI search engines (AEO, GEO, LLMO)
  - `programmatic-seo` -- Scaled page generation from templates and data
  - `marketing-psychology` -- Apply behavioral science to marketing copy
  - `launch-strategy` -- Product launch announcements
- **Install:** `npx skills add coreyhaines31/marketingskills` or clone to `.claude/skills/`
- **Verdict:** HIGH VALUE. The most comprehensive content-adjacent skill set. `content-strategy`, `copywriting`, `social-content`, and `email-sequence` are directly usable for a content machine pipeline.

### 1.2 Book Factory Pipeline (robertguss/claude-code-toolkit)
- **URL:** https://github.com/robertguss/claude-code-toolkit
- **Stars:** 25 | Renamed from `claude-skills`
- **What:** A toolkit with three dedicated writing skills:
  - **`ebook-factory`** -- Focused ebook creation pipeline
  - **`non-fiction-book-factory`** -- Full pipeline from idea to chapter architecture
  - **`writing`** -- Voice capture and ghost writing
- Also includes a **`compound-writing` plugin** (in `plugins/compound-writing/`)
- Other useful skills: `brainstorm` (multi-session ideation), `handoff` (session continuity), `code-documenter`
- **Install:** Clone and reference in CLAUDE.md, or `python build.py <skill>` to package for Claude.ai
- **Verdict:** HIGH VALUE. The `writing` skill with voice capture is directly applicable to ghost-writing blog posts. The `non-fiction-book-factory` shows a full knowledge-to-content pipeline pattern (idea -> outline -> chapter architecture).

### 1.3 ClawFu Marketing MCP Server (guia-matthieu/clawfu-skills)
- **URL:** https://github.com/guia-matthieu/clawfu-skills
- **Stars:** 3 | **Skills:** 172 (159 documented)
- **What:** Expert-sourced marketing skills as an MCP server. Named methodologies from Dunford, Schwartz, Ogilvy, Cialdini, Hormozi, Voss.
- **Content-relevant categories:**
  - **Content (22 skills):** copywriting (Schwartz), storytelling (StoryBrand), persuasion (Cialdini)
  - **Social (4 skills):** community building, social listening, content calendar
  - **Email (2 skills):** email sequence, newsletter strategy
  - **SEO Tools (5 skills):** keyword research, content optimization, technical audit
  - **Branding (2 skills):** brand voice, visual identity
  - **Video (5 skills):** AI storyboard, video concept, editing
  - **Audio (16 skills):** podcast production, sonic branding
- **Install:** `npx @clawfu/mcp-skills` (MCP server)
- **Verdict:** MEDIUM-HIGH VALUE. The MCP server architecture is interesting -- skills are served as tools, not files. The 22 Content skills and newsletter strategy skill are directly relevant. The named-methodology approach (Schwartz copywriting, Cialdini persuasion) provides structured frameworks rather than generic prompts.

### 1.4 Wondelai Marketing & Growth Skills (wondelai/skills)
- **URL:** https://github.com/wondelai/skills
- **Stars:** Not recorded | **Skills:** 25
- **What:** Agent skills for UX design, marketing/CRO, sales, product strategy, growth, based on books by Norman, Cialdini, Ries, Hormozi.
- **Content-relevant skills:**
  - `scorecard-marketing` -- Quiz/assessment funnel lead generation (Daniel Priestley)
  - `one-page-marketing` -- 9-square grid marketing plan (Allan Dib)
  - StoryBrand messaging framework (Donald Miller)
  - Web typography principles for blog/content readability
- Includes **49 copy-pasteable prompt examples** in EXAMPLES.md organized by persona (founders, PMs, marketers, copywriters, solopreneurs)
- **Install:** `npx skills add wondelai/skills/<skill-name>` or `/plugin install`
- **Verdict:** MEDIUM VALUE. More strategy-focused than execution-focused. The StoryBrand messaging framework and scorecard marketing could feed a content strategy pipeline.

### 1.5 Content Marketer Subagent (VoltAgent/awesome-claude-code-subagents)
- **URL:** https://github.com/VoltAgent/awesome-claude-code-subagents/blob/main/categories/08-business-product/content-marketer.md
- **Parent repo stars:** 10.8k
- **What:** A specialized Claude Code subagent for content marketing tasks: generating blog posts, social media content, email campaigns, marketing copy, and content performance insights.
- **Verdict:** MEDIUM VALUE. It is a subagent definition (CLAUDE.md-style markdown), not a full pipeline. Good as a template for the "content writer" agent role in a multi-agent content system.

### 1.6 Technical Writer Subagent (VoltAgent/awesome-claude-code-subagents)
- **URL:** https://github.com/VoltAgent/awesome-claude-code-subagents/blob/main/categories/08-business-product/technical-writer.md
- **What:** Subagent for generating, editing, and improving technical documentation (user guides, API references, product manuals). Adapts writing style to audiences.
- **Verdict:** MEDIUM VALUE. Useful for the "technical content" arm of a content pipeline (documentation-as-content, developer blog posts).

### 1.7 Internal Comms Skill (ComposioHQ/awesome-claude-skills & anthropics/skills)
- **URL:** https://github.com/anthropics/skills/tree/main/skills/internal-comms
- **Also listed in:** ComposioHQ/awesome-claude-skills
- **What:** Creates internal communications: status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates.
- **Verdict:** LOW-MEDIUM VALUE. The newsletter generation aspect is relevant. The skill shows a structured template approach for recurring written communications.

### 1.8 LinkedIn Automation Skill (ComposioHQ/awesome-claude-skills)
- **URL:** Referenced at `ComposioHQ/awesome-claude-skills/linkedin-automation` (directory not found at master branch)
- **What:** Automate LinkedIn: posts, profiles, companies, images, and comments.
- **Verdict:** POTENTIALLY HIGH VALUE but could not verify current state. The ComposioHQ README explicitly lists it under "Social Media" with the description above. May require Composio's API integration.

---

## 2. Publishing Infrastructure (MCP Servers, APIs, Format Converters)

### 2.1 X Article Publisher Skill (wshuyi/x-article-publisher-skill)
- **URL:** https://github.com/wshuyi/x-article-publisher-skill
- **Stars:** 589 | **Version:** v1.2.0
- **What:** Publishes Markdown articles to X (Twitter) Articles using Playwright browser automation. Full pipeline: Markdown -> parse -> structured data -> browser automation -> X Articles draft.
- **Key features:**
  - Rich text paste preserving all formatting (H2, bold, quotes, links)
  - Block-index image positioning (precise, deterministic)
  - Cover image + content images support
  - Divider support, table-to-image, Mermaid diagram support
  - Cross-platform (macOS + Windows)
  - Safe by design: only saves as draft, never auto-publishes
- **Requirements:** X Premium Plus, Playwright MCP, Python 3.9+
- **Install:** Clone + copy to `~/.claude/skills/` or `/plugin marketplace add`
- **Verdict:** HIGH VALUE. This is the most complete publish-to-platform skill in the ecosystem. The Markdown->Platform pipeline pattern (parse, structure, automate browser) is directly reusable for other platforms.

### 2.2 Markdown to EPUB Converter (smerchek/claude-epub-skill)
- **URL:** https://github.com/smerchek/claude-epub-skill
- **Stars:** 73 | **Version:** v1.1.0
- **What:** Converts markdown documents, chat summaries, or research reports into EPUB3 ebook files for Kindle and other readers.
- **Key features:**
  - EPUB3 standard compliance
  - Auto chapter detection from H1, sections from H2-H6
  - YAML frontmatter metadata extraction
  - Enhanced code blocks and professional tables
  - Automatic table of contents with navigation
- **Verdict:** MEDIUM VALUE. Useful for the "long-form content packaging" step -- turning research/blog series into ebooks for lead magnets or distribution.

### 2.3 Web Assets Generator (alonw0/web-asset-generator)
- **URL:** https://github.com/alonw0/web-asset-generator
- **What:** Generates web assets including favicons, PWA app icons, and **social media meta images** (Open Graph) for Facebook, Twitter, WhatsApp, and LinkedIn. Handles image resizing, text-to-image, and provides HTML meta tags.
- **Verdict:** LOW-MEDIUM VALUE. Handles the OG image / social card generation step needed when publishing blog posts. A supporting tool rather than core content creation.

### 2.4 Webflow Automation (ComposioHQ/awesome-claude-skills)
- **URL:** Referenced in ComposioHQ/awesome-claude-skills under "Marketing & Email Marketing"
- **What:** Automate Webflow: CMS collections, items, sites, publishing, and assets.
- **Verdict:** MEDIUM VALUE. If the blog is on Webflow, this enables programmatic publishing of content to CMS.

### 2.5 Blogging Platform Commands (cloudartisan/cloudartisan.github.io)
- **URL:** https://github.com/cloudartisan/cloudartisan.github.io/tree/main/.claude/commands
- **What:** Claude Code commands for publishing and maintaining a Jekyll/GitHub Pages blog: creating posts, managing categories, handling media files.
- **Note:** Could not crawl the directory listing successfully, but referenced in hesreallyhim/awesome-claude-code with description: "well-structured set of commands for publishing and maintaining a blogging platform."
- **Verdict:** MEDIUM VALUE. A practical reference for building blog publishing commands in `.claude/commands/`.

### 2.6 Claude Code Transcripts Publisher (simonw/claude-code-transcripts)
- **URL:** https://github.com/simonw/claude-code-transcripts
- **Stars:** 733
- **What:** Tools for publishing transcripts from Claude Code sessions. By Simon Willison.
- **Verdict:** LOW-MEDIUM VALUE for content directly, but HIGH VALUE as a pattern: turning AI session transcripts into publishable content. "Work in public" pattern.

---

## 3. Patterns & Workflows Applicable to Content

### 3.1 Continuous Learning + Instinct Export (affaan-m/everything-claude-code)
- **URL:** https://github.com/affaan-m/everything-claude-code
- **Key patterns:**
  - **`/evolve`** -- Cluster related instincts (learned patterns) into skills. Could be adapted as: cluster research notes into content topics.
  - **`/instinct-export`** -- Export learned instincts for sharing. Pattern: export accumulated knowledge into publishable form.
  - **`/instinct-import`** -- Import instincts from others. Pattern: ingest voice/style from reference writers.
  - **`/instinct-status`** -- View learned instincts with confidence scoring. Pattern: track content ideas and their maturity.
  - **`doc-updater`** skill -- Documentation sync. Pattern: keep published content in sync with evolving knowledge base.
  - **`/skill-create --instincts`** -- Generate skills + instincts together. Pattern: create content + update voice model simultaneously.
- **Verdict:** HIGH VALUE as a pattern source. The instinct-based learning system (learn patterns -> cluster -> evolve into skills) maps directly to a knowledge-to-content pipeline (accumulate insights -> cluster into themes -> evolve into articles).

### 3.2 Compound Writing Plugin (robertguss/claude-code-toolkit)
- **URL:** https://github.com/robertguss/claude-code-toolkit/tree/main/plugins/compound-writing
- **What:** A plugin approach to writing that likely implements iterative refinement (write -> review -> rewrite). Located in `plugins/compound-writing/`.
- **Verdict:** MEDIUM VALUE. Worth investigating the plugin structure for multi-pass writing workflows.

### 3.3 Homunculus -- Pattern Learning Agent (humanplane/homunculus)
- **URL:** https://github.com/humanplane/homunculus
- **Referenced in:** jqueryscript/awesome-claude-code
- **What:** "A Claude Code plugin that watches how you work, learns your patterns, and evolves itself to help you better."
- **Verdict:** MEDIUM VALUE as a pattern. Could be adapted to learn writing style/voice patterns from existing content and evolve writing assistance.

### 3.4 NotebookLM Integration (PleasePrompto/notebooklm-skill)
- **URL:** https://github.com/PleasePrompto/notebooklm-skill
- **Stars:** 2.7k
- **What:** Lets Claude Code chat directly with NotebookLM for source-grounded answers based exclusively on uploaded documents.
- **Verdict:** MEDIUM VALUE. Enables research-backed content creation: upload source documents to NotebookLM, then have Claude Code query them for grounded content generation.

### 3.5 Daniel Rosehill's Claude Code Repos Index
- **URL:** https://github.com/danielrosehill/Claude-Code-Repos-Index
- **Referenced in:** hesreallyhim/awesome-claude-code
- **What:** 75+ Claude Code repositories by the author covering CMS, system design, deep research, IoT, agentic workflows, server management, personal health.
- **Verdict:** LOW-MEDIUM VALUE. The CMS repositories may contain content publishing patterns worth exploring.

---

## 4. Hooks and Automation Triggers

### 4.1 Stop Hook -- Session Summary (robertguss/claude-code-toolkit)
- **URL:** https://github.com/robertguss/claude-code-toolkit/tree/main/hooks/change-summary
- **What:** `Stop` event hook that generates a session change summary when Claude Code finishes. Could be adapted to: generate a "what I learned/built today" content draft at session end.
- **Pattern for content:** SessionEnd -> summarize work -> draft blog post/tweet thread

### 4.2 Compaction Hook -- Preservation Priorities (robertguss/claude-code-toolkit)
- **URL:** https://github.com/robertguss/claude-code-toolkit/tree/main/hooks/compaction
- **What:** `PreCompact` hook that injects preservation priorities for better context compaction.
- **Pattern for content:** Before context compaction, extract and save key insights to a "content ideas" file so they survive context window limits.

### 4.3 Hook Creation Command (omril321/automated-notebooklm)
- **URL:** https://github.com/omril321/automated-notebooklm/blob/main/.claude/commands/create-hook.md
- **What:** Slash command that intelligently prompts through hook creation with smart suggestions based on project setup.
- **Pattern for content:** Use this to create custom hooks for content triggers (e.g., "when research file changes, generate content outline").

### 4.4 Hooks Mastery Patterns (disler/claude-code-hooks-mastery)
- **URL:** https://github.com/disler/claude-code-hooks-mastery
- **What:** Reference patterns for all hook types. Key content-applicable hooks:
  - **`Stop` hook:** Trigger content generation when a research/analysis session ends
  - **`SubagentStop` hook:** When a research subagent completes, trigger content drafting
  - **`PreCompact` hook:** Extract publishable insights before context window compaction
  - **Research agent template:** A subagent pattern for deep web research that feeds content creation
- **Verdict:** MEDIUM VALUE. No content-specific hooks, but the patterns (especially Stop + SubagentStop) are the right triggers for a "research -> content" pipeline.

---

## 5. Summary: Highest-Value Items for a Content Machine

| Priority | Item | Type | Why |
|----------|------|------|-----|
| 1 | marketingskills (coreyhaines31) | Skill collection | 29 production skills including copywriting, content-strategy, social-content, email-sequence |
| 2 | Book Factory (robertguss) | Skill pipeline | Writing, voice capture, ghost writing, ebook creation -- full authoring pipeline |
| 3 | X Article Publisher (wshuyi) | Publishing skill | Complete Markdown-to-platform pipeline with browser automation -- reusable pattern |
| 4 | Instinct/Evolve pattern (affaan-m) | Workflow pattern | Knowledge accumulation -> clustering -> evolution into publishable form |
| 5 | ClawFu MCP (guia-matthieu) | MCP server | 22 content skills + newsletter strategy as MCP tools |
| 6 | Content Marketer subagent (VoltAgent) | Agent template | Ready-made subagent role for content marketing |
| 7 | EPUB converter (smerchek) | Format tool | Long-form content packaging for distribution |
| 8 | Stop/SubagentStop hooks (disler, robertguss) | Automation trigger | Session-end triggers for "research done -> draft content" pipeline |
| 9 | LinkedIn Automation (ComposioHQ) | Publishing skill | Direct social media posting (needs verification) |
| 10 | Blogging commands (cloudartisan) | Command set | Blog post creation, categories, media management |

---

## 6. Gaps Identified

1. **No end-to-end "research to published blog post" skill exists.** The pieces are all there (research -> write -> format -> publish) but nobody has assembled them into a single orchestrated pipeline.
2. **No newsletter-specific creation skill.** ClawFu has "newsletter strategy" but no "newsletter writer" skill that generates a weekly digest from accumulated inputs.
3. **No cross-platform publisher.** The X Article Publisher is X-only. No equivalent for Medium, Substack, Dev.to, LinkedIn Articles, or Ghost.
4. **No content calendar/scheduling skill.** ClawFu lists "content calendar" but it is strategy-level, not execution-level (no actual scheduling integration).
5. **No voice/tone learning from existing content.** The `writing` skill in robertguss mentions "voice capture" but the instinct-learning pattern from affaan-m is more sophisticated and not connected to content creation.
