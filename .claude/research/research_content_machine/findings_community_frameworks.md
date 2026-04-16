# Community Frameworks for Developer Content Creation

Research date: 2026-02-20
Searches performed: 14 (across Exa, Brave Search, Crawl4AI)

---

## Table of Contents

1. [Claude Code Blog/Content Skills](#1-claude-code-blogcontent-skills)
2. [Blog Automation Frameworks](#2-blog-automation-frameworks)
3. [Digital Garden Frameworks](#3-digital-garden-frameworks)
4. [TIL (Today I Learned) Repositories](#4-til-today-i-learned-repositories)
5. [Obsidian/Logseq Publish Pipelines](#5-obsidianlogseq-publish-pipelines)
6. [Newsletter Tools (Self-Hosted/Open Source)](#6-newsletter-tools-self-hostedopen-source)
7. [Social Media Scheduling & Distribution](#7-social-media-scheduling--distribution)
8. [ADR-to-Content Tooling](#8-adr-to-content-tooling)
9. [Build-in-Public Frameworks](#9-build-in-public-frameworks)
10. [Git-to-Content Automation](#10-git-to-content-automation)
11. [Skill/Agent Collections (Meta-Resources)](#11-skillagent-collections-meta-resources)

---

## 1. Claude Code Blog/Content Skills

### nickwinder/klaude-blog
- **URL:** https://github.com/nickwinder/klaude-blog
- **Stars:** ~50+ (new, growing)
- **What it does:** AI-powered blog automation template built with Claude Code agents. Provides end-to-end content creation: automated research, writing, SEO optimization, and social media generation. Uses CLAUDE.md to define brand voice, writing style, SEO guidelines, and a publishing checklist. Integrates Twitter and LinkedIn MCPs for automated social distribution.
- **Key insight:** The author (Nick Winder) wrote about building specialized AI agents with Claude Code Meta -- the CLAUDE.md file encodes the entire content strategy, brand voice, and workflow. Agents handle research, drafting, SEO, and publishing as a pipeline.
- **Adaptation potential:** HIGH. This is the closest existing project to a "content machine" skill for Claude Code. Could be forked and adapted to add research-log ingestion, ADR-to-blog conversion, and newsletter generation. The CLAUDE.md-as-config-for-voice pattern is directly reusable.

### Joe Karlsson's Claude Code Blog Skill
- **URL:** https://www.joekarlsson.com/2025/10/building-a-claude-code-blog-skill-what-i-learned-systematizing-content-creation/
- **Stars:** N/A (blog post, not a repo)
- **What it does:** A developer advocate at MongoDB built a Claude Code skill that systematizes content creation from the terminal. He describes encoding his content workflow as a skill -- turning the one-off "craft the perfect prompt" approach into a repeatable system. Key lesson: the skill captures institutional knowledge about content structure, not just drafting.
- **Adaptation potential:** HIGH. The blog post is a detailed case study of exactly the pattern we want: encoding developer content workflows as Claude Code skills. The conceptual framework (systematize your content creation into repeatable skills) is the foundation of a content machine.

### ComposioHQ/awesome-claude-skills -- content-research-writer
- **URL:** https://github.com/ComposioHQ/awesome-claude-skills/blob/master/content-research-writer/SKILL.md
- **Stars:** Part of awesome-claude-skills (1000+)
- **What it does:** A Claude Code skill that acts as a writing partner -- helps research, outline, draft, and refine content while maintaining the user's unique voice and style. Open from any directory and start writing.
- **Adaptation potential:** MEDIUM. Good baseline skill for content drafting. Lacks the pipeline automation (git hooks, scheduling, distribution) that a full content machine needs, but provides a solid "writer assistant" component.

### laurigates/claude-plugins -- claude-blog-sources
- **URL:** https://playbooks.com/skills/laurigates/claude-plugins/claude-blog-sources
- **Stars:** N/A (playbooks.com skill)
- **What it does:** Helps research Claude Code features and CLAUDE.md best practices by extracting guidance from official docs and blog insights. Uses WebFetch and WebSearch.
- **Adaptation potential:** LOW-MEDIUM. Niche use case, but demonstrates the pattern of a skill that fetches and synthesizes web content into usable research.

---

## 2. Blog Automation Frameworks

### ry-ops.dev -- n8n + Claude Blog Pipeline
- **URL:** https://ry-ops.dev/amp/2026-02-11-building-an-automated-blog-content-pipeline-with-n8n-imagemagick-and-claude
- **Stars:** N/A (blog post describing n8n workflow)
- **What it does:** A 12-node n8n workflow that takes a topic, searches 217+ existing posts for related content (Qdrant RAG), generates a draft with valid Astro frontmatter, creates an animated SVG hero image, converts it to an OG social sharing image, commits everything to GitHub, and verifies deployment on Cloudflare Pages. Fully automated from topic input to published post.
- **Key architecture:** Topic -> search_blog_posts (Qdrant RAG) -> suggest_schedule (posting cadence analysis) -> generate_draft -> create_image -> commit_to_github -> verify_deployment
- **Adaptation potential:** HIGH. This is a complete content pipeline. The n8n orchestration approach could be replaced by Claude Code skills, but the architecture (RAG over existing content, auto-image generation, auto-commit, auto-deploy) is exactly what a content machine needs.

### ContentOps as Code (SteakHouse Blog)
- **URL:** https://blog.trysteakhouse.com/blog/contentops-as-code-ci-cd-pipeline-geo
- **Stars:** N/A (methodology article)
- **What it does:** Treats marketing content exactly like software code -- stored in Git, written in Markdown, deployed via automated CI/CD pipelines. Automates schema validation, ensures instant indexing, and scales content for search engines and AI answer engines.
- **Adaptation potential:** MEDIUM. The methodology ("ContentOps as Code") is philosophically aligned with a developer content machine. The Git-native, CI/CD-driven approach maps directly to how developer-researchers already work.

---

## 3. Digital Garden Frameworks

### jackyzha0/quartz
- **URL:** https://github.com/jackyzha0/quartz
- **Estimated Stars:** ~7,000+ (one of the most popular digital garden tools)
- **What it does:** A fast, batteries-included static site generator that transforms Markdown content into fully functional websites. Features: full-text search, wikilink support, backlinks, local graph view, tags, link previews. Designed specifically for digital gardens. Built on top of Hugo.
- **Key features:** Transforms an Obsidian vault into a navigable website. Supports graph visualization, backlinks, search. Zero-config deployment to GitHub Pages, Cloudflare Pages, etc.
- **Adaptation potential:** HIGH. Quartz is the leading digital garden framework. For a developer-researcher, it provides the "publish" layer: notes, research logs, and TILs written in Markdown can be automatically published as an interconnected knowledge garden. Could serve as the public-facing output of a content machine.

### MaggieAppleton/digital-gardeners
- **URL:** https://github.com/MaggieAppleton/digital-gardeners
- **Estimated Stars:** ~3,800+
- **What it does:** A curated collection of resources, links, projects, and ideas for digital gardeners. Lists tools (Quartz, Foam, TiddlyWiki, etc.), essays on the philosophy, and example gardens. The definitive meta-resource for digital gardening.
- **Adaptation potential:** MEDIUM. Reference resource, not a tool. Useful for choosing the right garden framework and understanding the philosophy. The "epistemic status" and "growth stage" concepts (seedling -> budding -> evergreen) map well to content maturity stages.

### thedevdavid/digital-garden
- **URL:** https://github.com/thedevdavid/digital-garden
- **Stars:** ~500+
- **What it does:** An open source blog (digital garden) template for developers. Next.js based with MDX support, Tailwind CSS, dark mode, SEO optimization. Designed specifically as a developer-friendly blog template with digital garden features.
- **Adaptation potential:** MEDIUM. Good starting template if you want a custom Next.js-based garden rather than Quartz. More control but more setup.

### Foam (VS Code Extension)
- **URL:** https://foambubble.github.io/foam/
- **Stars:** ~15,000+ on GitHub (foambubble/foam)
- **What it does:** A personal knowledge management and sharing system inspired by Roam Research, built as a VS Code extension. Creates a graph of interconnected Markdown notes. Publishes via GitHub Pages using standard static site generators.
- **Adaptation potential:** MEDIUM. If the content machine operator uses VS Code, Foam provides the note-taking layer with graph visualization. Less relevant if using Obsidian or terminal-first workflows.

### Dendron
- **URL:** https://docs.dendron.so/
- **Stars:** ~6,500+ on GitHub
- **What it does:** An open-source, local-first, schema-aware, reference-rich knowledge base built on top of VS Code. Uses a hierarchical note structure. Has built-in publishing to static sites. Notes can be flagged public/private in frontmatter.
- **Adaptation potential:** LOW-MEDIUM. Powerful but complex. The schema-aware and hierarchical structure is interesting for organizing research, but Dendron development has slowed. Quartz is a simpler choice for most use cases.

---

## 4. TIL (Today I Learned) Repositories

### jbranchaud/til
- **URL:** https://github.com/jbranchaud/til
- **Stars:** 14,000+
- **What it does:** The original TIL repository pattern. 1,737 TILs and counting. Each TIL is a concise write-up on a small thing learned day-to-day. Organized by topic (language, technology). A flat collection of Markdown files with an auto-generated README index. Topics: learn-in-public, til, today-i-learned, writing.
- **Key insight:** The constraint is the magic -- TILs are explicitly "things that don't really warrant a full blog post." This low-friction format produces consistent output.
- **Adaptation potential:** HIGH. The TIL pattern is one of the most proven developer content formats. A content machine should include a `/til` command that captures a learning in the standard format (title, category, short explanation with code). Auto-generating the index (like jbranchaud does) is trivial to automate.

### simonw/til
- **URL:** https://github.com/simonw/til
- **Stars:** 1,387
- **Homepage:** https://til.simonwillison.net
- **What it does:** Simon Willison's TIL collection (575+ TILs). Key innovation: uses GitHub Actions to auto-generate an index README, AND deploys to a Datasette-backed search engine (til.simonwillison.net) where all TILs are searchable via SQL. Self-rewriting README powered by GitHub Actions.
- **Key insight:** Simon's approach adds a "publish layer" on top of the basic TIL pattern -- GitHub Actions auto-build, Datasette for full-text search, Atom feed for subscribers. This transforms a GitHub repo into a mini-publication.
- **Adaptation potential:** VERY HIGH. Simon's TIL system is the gold standard for developer learning-in-public automation. The GitHub Actions + Datasette pattern could be directly adopted. The auto-rewriting README pattern (commit a TIL -> Actions rebuild the index -> deploy) is exactly the kind of zero-friction pipeline a content machine needs.

---

## 5. Obsidian/Logseq Publish Pipelines

### jobindjohn/obsidian-publish-mkdocs
- **URL:** https://github.com/jobindjohn/obsidian-publish-mkdocs
- **Stars:** 639
- **What it does:** A template to publish Obsidian/Foam notes on GitHub Pages using MkDocs (Material theme). Provides a ready-to-use GitHub Actions workflow. Write in Obsidian, push to Git, auto-deploy to web.
- **Adaptation potential:** MEDIUM. Solid "notes to web" pipeline. MkDocs Material is a beautiful theme. However, less feature-rich than Quartz for digital garden features (no graph view, limited backlinks).

### Obsidian Digital Garden Plugin
- **URL:** https://github.com/oleeskild/obsidian-digital-garden
- **Stars:** ~4,500+
- **What it does:** An Obsidian plugin that lets you publish notes to a digital garden website directly from Obsidian. Notes are published to a Vercel/Netlify-hosted 11ty site. Supports Obsidian themes, dataview, excalidraw, and more. Zero-config publishing.
- **Adaptation potential:** MEDIUM. Great if using Obsidian as the primary editor. The "flag a note as published" workflow (add `dg-publish: true` to frontmatter) is elegant. However, ties you to the Obsidian ecosystem.

### Obsidian-to-Hugo Pipelines (Multiple Authors)
- **URLs:**
  - https://kinderforce.org/posts/blog/automating-my-obsidian-to-blog-workflow/ (Ben Kinder)
  - https://pedrotchang.dev/posts/automated-obsidian-to-hugo-publishing/ (Pedro Chang)
  - https://ironpark.github.io/en/blog/blog-auto-publishing-with-obsidian (IRONPARK)
- **What they do:** Various authors have built Obsidian-to-Hugo automated pipelines using git hooks, GitHub Actions, and custom scripts. Common pattern: write in Obsidian, tag with `#publish`, git commit triggers sync to Hugo content directory, GitHub Actions builds and deploys.
- **Adaptation potential:** MEDIUM-HIGH. The pattern of "write in knowledge base, auto-publish to blog via git hooks" is directly applicable. The specific Hugo+Obsidian integration is a solved problem with multiple reference implementations.

### therealfakemoot/obsidian-pipeline
- **URL:** https://github.com/therealfakemoot/obsidian-pipeline
- **Stars:** 8
- **What it does:** Headless management of an Obsidian vault. Written in Go. Validates frontmatter against protobuf schemas. Targeted at users who programmatically interact with their vaults for publishing via static site generators.
- **Adaptation potential:** LOW-MEDIUM. Small project, but the concept of "headless vault management with schema validation" is interesting for quality control in a content pipeline.

### Logseq Publishing
- **URL:** https://docs.logseq.com/#/page/publishing
- **What it does:** Logseq has built-in publishing that generates a static site from your graph. Works with GitHub Pages. All pages are public by default (can be excluded). Simpler than Obsidian's ecosystem but less customizable.
- **Adaptation potential:** LOW. Only relevant if using Logseq. The publish mechanism is basic compared to Quartz.

---

## 6. Newsletter Tools (Self-Hosted/Open Source)

### knadh/listmonk
- **URL:** https://github.com/knadh/listmonk
- **Homepage:** https://listmonk.app
- **Stars:** ~16,000+
- **What it does:** High-performance, self-hosted newsletter and mailing list manager. Single binary app (Go). Modern dashboard, campaign management, subscriber management, templating, click tracking, analytics. Connects to any SMTP (Mailgun, Sendgrid, SES, etc.). PostgreSQL backend.
- **Key features:** Transactional + campaign emails, subscriber segmentation, custom templates, API access, S3 media uploads, i18n.
- **Adaptation potential:** HIGH. Listmonk is the best self-hosted newsletter tool available. A content machine could use Listmonk's API to automatically distribute weekly digests, TIL roundups, or research summaries. The API-first design makes it easy to integrate with Claude Code skills.

### Ghost
- **URL:** https://ghost.org / https://github.com/TryGhost/Ghost
- **Stars:** ~48,000+
- **What it does:** Open source blog and newsletter platform. Combines a publishing CMS with built-in newsletter delivery and paid memberships. Used by major publications (Platformer, 404Media, etc.). Modern editor, themes marketplace, member management, Stripe integration.
- **Adaptation potential:** MEDIUM. Ghost is excellent but heavier than needed for a developer content machine. Best suited if you want a full publication with paid subscriptions. The Ghost Content API could be used to programmatically publish posts from a Claude Code pipeline.

### Buttondown
- **URL:** https://buttondown.com
- **Stars:** Partially open source (docs, API clients)
- **What it does:** Simple, powerful newsletter tool for independent creators. Markdown-first. API for programmatic sending. Supports automation, paid subscriptions, analytics. Developer-friendly.
- **Adaptation potential:** MEDIUM. Not self-hosted (SaaS), but the API is clean and Markdown-native. Good choice if you want managed newsletter delivery without running infrastructure. The API could be called from a Claude Code skill to send newsletters.

### marcelkooi/awesome-newsletter-tools
- **URL:** https://github.com/marcelkooi/awesome-newsletter-tools
- **What it does:** Curated list of email newsletter tools, platforms, media, and software. Covers: discoverability (podcasts, directories), platforms (transactional, open source, marketing, editorial, bundling, blog-first), advertisements, communities.
- **Adaptation potential:** Reference resource for choosing newsletter tooling.

---

## 7. Social Media Scheduling & Distribution

### gitroomhq/postiz-app
- **URL:** https://github.com/gitroomhq/postiz-app
- **Homepage:** https://postiz.com
- **Stars:** 26,568
- **What it does:** The ultimate open-source social media scheduling tool. Supports Twitter/X, LinkedIn, Facebook, Instagram, TikTok, YouTube, Reddit, Threads, Bluesky, Mastodon, and more. AI-powered content generation, scheduling, analytics. Has a CLI agent, n8n integration, public API, Node.js SDK.
- **Key features:** Multi-platform scheduling, AI content generation, analytics dashboard, team collaboration, 100% open source (AGPL-3.0). New: CLI agent for programmatic posting.
- **Adaptation potential:** VERY HIGH. Postiz solves the "distribution" problem in a content machine. A Claude Code skill could generate content, then use Postiz's API or CLI to schedule and distribute it across social platforms. The n8n integration means it can be part of larger automation workflows. At 26k+ stars, this is a battle-tested tool.

---

## 8. ADR-to-Content Tooling

### joelparkerhenderson/architecture-decision-record
- **URL:** https://github.com/joelparkerhenderson/architecture-decision-record
- **Stars:** 15,073
- **What it does:** The definitive collection of ADR templates, examples, and guidance. Multiple template formats (MADR, Nygard, Alexandrian, etc.). Includes guidance on how to start using ADRs with tools and git.
- **Adaptation potential:** MEDIUM. Not a content generation tool, but the templates provide the input format. A content machine skill could parse ADRs in these formats and generate blog posts explaining the decisions.

### zircote/structured-madr
- **URL:** https://github.com/zircote/structured-madr
- **What it does:** Extends MADR (Markdown Any Decision Records) with YAML frontmatter for machine-readable metadata, comprehensive option analysis with risk assessments, and required audit sections. Designed for AI-assisted development -- the YAML frontmatter makes ADRs parseable by LLMs.
- **Adaptation potential:** HIGH. Structured MADR is specifically designed to be machine-readable. A content machine could parse these structured ADRs and auto-generate blog posts, with the YAML frontmatter providing rich metadata for content categorization.

### lior-guesty/llm_adr_generator
- **URL:** https://github.com/lior-guesty/llm_adr_generator
- **Stars:** 1
- **What it does:** Tool to generate ADRs from textual inputs using LLMs (GPT-4 or Claude Sonnet via OpenWebUI). Reads a design discussion and generates a structured ADR. JavaScript + Python.
- **Adaptation potential:** LOW-MEDIUM. Small project, but demonstrates the reverse direction: discussion -> ADR. A content machine could go further: discussion -> ADR -> blog post.

### AI-Generated ADR (Dennis Adolfi blog post)
- **URL:** https://adolfi.dev/blog/ai-generated-adr/
- **What it does:** Uses an AI agent to scan a codebase and automatically generate ADRs from the code structure and patterns. No manual writing required.
- **Adaptation potential:** MEDIUM. The concept of "scan codebase, generate documentation/content" is directly applicable to a content machine that turns development work into publishable content.

---

## 9. Build-in-Public Frameworks

### build-in-public.live
- **URL:** https://www.build-in-public.live/
- **What it does:** An open-source platform for daily progress tracking, social sharing, and community building. Features: visual progress timeline, rich text editor, media attachments, mood tracking, auto-generated social posts, engagement analytics, community features.
- **Adaptation potential:** MEDIUM. The daily progress tracking and auto-generated social posts are relevant features. However, this is a full web platform rather than a developer tool that integrates into existing workflows.

### buildinginpublic/buildinpublic (GitHub)
- **URL:** https://github.com/buildinginpublic/buildinpublic
- **What it does:** A guide for how to build in public. Provides frameworks, templates, and examples for the #buildinpublic movement.
- **Adaptation potential:** LOW-MEDIUM. Reference material, not tooling.

### open-sauced/100-days-of-oss-template
- **URL:** https://github.com/open-sauced/100-days-of-oss-template
- **What it does:** A journal template for tracking #100DaysOfOSS work. Structured daily logging with prompts for what you worked on, what you learned, and what's next.
- **Adaptation potential:** MEDIUM. The daily structured journal template is a good low-friction content format. Could be adapted into a Claude Code skill that generates daily/weekly build logs.

---

## 10. Git-to-Content Automation

### ai-commit-report-generator (npm)
- **URL:** https://github.com/stormsidali2001 (referenced in dev.to article)
- **NPM:** ai-commit-report-generator-cli
- **What it does:** Reads git commit history and uses AI to generate two types of reports: (1) business report (bullet-point daily summary), (2) technical report (per-commit/PR summary). Designed to automate weekly progress reports.
- **Adaptation potential:** HIGH. This is directly relevant -- turning git history into readable content. A content machine could use a similar approach to generate weekly devlogs, changelog blog posts, or progress updates from commit history.

### Changeish
- **URL:** https://dev.to/itlackey/changeish-automate-your-changelog-with-ai-45kj
- **What it does:** A Bash script that automates changelog entries by using a local LLM (via Ollama). Reads git commits and generates formatted changelog entries.
- **Adaptation potential:** MEDIUM. The "local LLM + git log -> formatted content" pattern is applicable. Could be a component of a content machine's "work-to-content" pipeline.

### "Commit-History" Trust Signal (SteakHouse Blog)
- **URL:** https://blog.trysteakhouse.com/blog/commit-history-trust-signal-leveraging-git-transparency-eeat
- **What it does:** A methodology for exposing git version control logs to search engines and users to prove content freshness and authorship. Uses public commit metadata and structured data to demonstrate what changed, when, and by whom.
- **Adaptation potential:** MEDIUM. Interesting SEO angle: using git history as proof of authentic, continuously-updated content. Could be integrated into a content machine's publishing pipeline.

---

## 11. Skill/Agent Collections (Meta-Resources)

### BehiSecc/awesome-claude-skills
- **URL:** https://github.com/BehiSecc/awesome-claude-skills
- **Stars:** 5,818
- **What it does:** Curated list of Claude Skills organized by category. Categories include: Writing & Research, Media & Content, Development & Code Tools, Data & Analysis, and more. 40+ contributors.
- **Adaptation potential:** HIGH as a discovery resource. Check the Writing & Research and Media & Content sections for additional content creation skills.

### alirezarezvani/claude-code-skill-factory
- **URL:** https://github.com/alirezarezvani/claude-code-skill-factory
- **Stars:** 513
- **What it does:** A toolkit for building and deploying production-ready Claude Skills. Generate structured skill templates, automate workflow integration, accelerate AI agent development.
- **Adaptation potential:** MEDIUM. Useful for building the content machine's skills themselves, not for content creation directly.

### VoltAgent/awesome-agent-skills
- **URL:** https://github.com/VoltAgent/awesome-agent-skills
- **What it does:** Claude Code Skills and 300+ agent skills from official dev teams and the community. Compatible with Codex, Antigravity, Gemini CLI, Cursor, and others.
- **Adaptation potential:** MEDIUM. Another discovery resource for finding content-related skills.

---

## Synthesis: Key Patterns for a Developer-Researcher Content Machine

### Pattern 1: TIL-as-Micro-Content (jbranchaud + simonw)
The most proven, lowest-friction developer content format. Write a short Markdown file, commit, and auto-publish. Simon Willison's addition of GitHub Actions + Datasette makes it a full publication pipeline.
- **Implementation:** A `/til` Claude Code skill that captures a learning, writes the Markdown, updates the index, commits, and triggers deployment.

### Pattern 2: Digital Garden as Knowledge Base (Quartz)
Long-form research notes, interconnected via wikilinks and backlinks. Quartz handles the heavy lifting of turning Markdown into a navigable website with graph visualization.
- **Implementation:** Use Quartz as the publish layer. Research logs, architectural decisions, and deep-dive posts live as Markdown in a vault. Claude Code manages the writing; Quartz manages the rendering.

### Pattern 3: Git-Native Content Pipeline (ContentOps as Code)
Content lives in Git. CI/CD pipelines validate, build, and deploy. Every piece of content has a commit history showing its evolution.
- **Implementation:** GitHub Actions validate frontmatter, check links, build the site, and deploy. Content changes go through the same PR/review process as code.

### Pattern 4: AI-Powered Blog Automation (klaude-blog + n8n pipeline)
Claude Code skills handle research, drafting, SEO optimization, and social media generation. The CLAUDE.md file encodes brand voice and content strategy.
- **Implementation:** Fork klaude-blog's approach. Define voice/style in CLAUDE.md. Build skills for each content type (blog post, newsletter, social thread, TIL).

### Pattern 5: Automated Distribution (Postiz + Listmonk)
Content generated by the machine is distributed via Postiz (social media) and Listmonk (newsletter). APIs enable programmatic scheduling.
- **Implementation:** After content is generated and published, a distribution skill calls Postiz API for social and Listmonk API for newsletter.

### Pattern 6: Work-to-Content Bridge (ADRs + Git History + Research Logs)
The most unique opportunity: automatically transforming development artifacts (ADRs, commit history, research logs, planning documents) into publishable content. No separate "content creation" step -- content emerges from work.
- **Implementation:** Claude Code skills that read `.planning/` docs, ADRs, git logs, and research notes, then generate blog posts, threads, and newsletter issues.

---

## Top Recommendations (Ranked by Adaptation Potential)

| Rank | Tool/Framework | Category | Why |
|------|---------------|----------|-----|
| 1 | simonw/til pattern | TIL | Gold standard for low-friction developer content. GitHub Actions auto-publish. Proven at scale (575+ TILs). |
| 2 | Quartz | Digital Garden | Best-in-class Markdown-to-website. Graph view, backlinks, search. Drop-in publish layer. |
| 3 | nickwinder/klaude-blog | Blog Automation | Direct Claude Code integration. CLAUDE.md-as-voice-config. End-to-end pipeline. |
| 4 | Postiz | Distribution | 26k+ stars. API/CLI for programmatic social scheduling. Solves the "distribute" problem. |
| 5 | Listmonk | Newsletter | 16k+ stars. Self-hosted, API-first. Solves the "email newsletter" problem. |
| 6 | n8n Blog Pipeline (ry-ops) | Full Pipeline | Complete architecture: RAG over past content, auto-draft, auto-image, auto-deploy. |
| 7 | structured-madr | ADR-to-Content | Machine-readable ADRs designed for LLM consumption. Enables ADR-to-blog automation. |
| 8 | ai-commit-report-generator | Git-to-Content | Turns commit history into weekly reports. Directly applicable to devlog generation. |
| 9 | jbranchaud/til | TIL | The original (14k stars). Simpler than simonw's but defines the format. |
| 10 | Obsidian-to-Hugo pipelines | Publish Pipeline | Multiple reference implementations. Solved problem. |
