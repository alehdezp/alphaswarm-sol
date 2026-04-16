# Research: Developer Blogging Tools and Content Publishing Pipelines

**Date:** 2026-02-20
**Goal:** Identify tools and automation pipelines that convert project work (docs, code, research notes) into published content across blog platforms, LinkedIn, and social media -- optimized for markdown-heavy, CLI-friendly developer workflows.

---

## 1. AI-Assisted Content Pipelines

Tools that take technical artifacts and generate publishable content drafts.

### Direct-Use Tools

| Tool | What It Does | CLI/Markdown Fit | Notes |
|------|-------------|-------------------|-------|
| **Claude / ChatGPT** (manual prompting) | Transform research docs, CLAUDE.md files, planning notes into blog drafts | Excellent -- input/output is text | Most flexible; requires custom prompts per content type |
| **Docs.dev** (docs.dev) | Generates documentation from codebase + existing content; AI-enabled markdown editor | Good -- GitHub-native, markdown-first | More docs-focused than blog-focused, but the "generate from codebase" concept applies |
| **Promptless** (gopromptless.ai) | Auto-detects when code changes need doc updates; generates docs from PRs | Good -- GitHub Actions integration | Watches PRs and auto-generates; could be adapted for changelogs/blog posts |
| **DocAider** (GitHub) | AI-powered documentation maintenance via GitHub Actions; generates docs from code changes | Good -- CI/CD native | Open-source, uses GitHub Actions workflows to trigger generation |
| **DeepDocs** (deepdocs.dev) | GitHub AI agent that keeps docs in sync with code repo on every PR | Good -- GitHub-native | Continuous documentation updates; could feed a blog pipeline |

### Custom Pipeline Approach (Recommended for Dev Workflows)

The most practical approach for a developer building in public:

1. **Write in markdown** (Obsidian, VS Code, or directly in repo)
2. **Use Claude/LLM** to transform artifacts into drafts:
   - Research doc -> blog post draft
   - Planning phase completion -> "build in public" update
   - Code change + context -> technical deep-dive
3. **Script the transformation** (CLI tool or shell script that passes markdown + system prompt to an API)
4. **Publish via platform APIs** (see sections below)

This is essentially what tools like BlogBurst and EchoWrite do, but a custom script gives full control over voice, format, and which artifacts feed into content.

---

## 2. LinkedIn Publishing Automation

### LinkedIn API Access

| Aspect | Detail |
|--------|--------|
| **API versions** | Marketing Developer Platform (company pages) or Community Management API (personal profiles) |
| **Auth** | OAuth 2.0 three-legged flow |
| **Post endpoint** | `POST /rest/posts` (UGC Posts API) |
| **Character limit** | 3,000 characters per post |
| **Rate limits** | 100 API calls per day per member for most endpoints; posting limits are stricter (varies by access tier) |
| **Media support** | Images, videos, documents (PDF/PPTX/DOCX displayed as carousels), articles |
| **Access requirement** | Must create a LinkedIn App, request appropriate product permissions (e.g., "Share on LinkedIn", "Sign In with LinkedIn using OpenID Connect") |
| **Key gotcha** | Personal profile posting requires Community Management API access, which has a restricted approval process. Company pages are easier to automate. |

### Scheduling and Automation Tools

| Tool | Type | Notes |
|------|------|-------|
| **PostFast** (postfa.st) | API-as-a-service | Unified API for scheduling across LinkedIn, Twitter, etc. Simple REST calls. Supports text, images, video, document carousels. |
| **Late.dev** (getlate.dev) | API-as-a-service | "Post everywhere. One API." Handles OAuth complexity for you. Developer-focused. |
| **Buffer / Hootsuite** | SaaS scheduling | GUI-based, not CLI-friendly, but reliable for scheduling |
| **AuthoredUp** | LinkedIn-specific | Formatting, preview, scheduling for LinkedIn posts. Not API/CLI. |
| **ConnectSafely.ai** | Markdown-to-LinkedIn converter | Converts markdown formatting to LinkedIn-compatible Unicode characters (bold, italic, etc.) |

### LinkedIn Content Best Practices for Technical Posts

- **Optimal length:** 1,200-1,500 characters for engagement; up to 3,000 allowed
- **Formatting:** LinkedIn does NOT support markdown. Use Unicode characters for bold/italic. Tools like ConnectSafely convert markdown to Unicode.
- **Structure:** Hook line (first 2 lines visible before "see more") -> body with line breaks -> CTA
- **Engagement patterns:** Document/carousel posts get highest engagement (6.60% average). Text-only posts with formatting get 2-3x more engagement than unformatted.
- **Posting frequency:** 2-4 times per week for optimal reach
- **Hashtags:** 3-5 relevant hashtags, placed at end

---

## 3. Blog Platforms with Developer Tooling

### Platform Comparison

| Platform | API | Markdown Support | CLI Workflow | Free Tier | Self-Host |
|----------|-----|-----------------|--------------|-----------|-----------|
| **Dev.to** | REST API (v1) | Native markdown with frontmatter | Excellent -- `POST /api/articles` with markdown body | Yes (fully free) | No |
| **Hashnode** | GraphQL API | Native markdown | Good -- GraphQL mutations for publishing | Yes (free for personal) | Headless mode available |
| **Ghost** | Admin API (REST) + Content API | Native markdown; supports Mobiledoc and Lexical formats | Good -- Admin API key auth, JSON payloads | Self-host only (free); Ghost(Pro) paid | Yes |
| **Hugo** | N/A (static site generator) | Native markdown with frontmatter | Excellent -- `hugo new post`, git push, CI/CD deploys | Yes (free, open source) | Yes (generates static files) |
| **Astro** | N/A (static/SSR framework) | Content Collections (markdown + MDX) | Excellent -- file-based content, git push, CI/CD deploys | Yes (free, open source) | Yes |
| **Medium** | Limited API (mostly deprecated for new apps) | Markdown via import | Poor -- API access restricted since 2023 | Freemium (paywall) | No |

### Dev.to API Details

- **Endpoint:** `https://dev.to/api/articles`
- **Auth:** API key in header (`api-key: YOUR_KEY`)
- **Publish:** `POST /api/articles` with JSON body containing `title`, `body_markdown`, `published`, `tags`, `canonical_url`
- **Update:** `PUT /api/articles/{id}`
- **Rate limits:** 30 requests per 30 seconds, 10 articles created per 30 seconds
- **Canonical URL:** Supports setting canonical URL for SEO (critical for cross-posting)

### Hashnode API Details

- **Endpoint:** `https://gql.hashnode.com`
- **Auth:** Personal Access Token
- **Publish:** GraphQL mutation `publishPost` with markdown content
- **Canonical URL:** Supported
- **Unique feature:** Headless CMS mode -- use your own domain and frontend, Hashnode as backend

### Ghost API Details

- **Admin API:** JWT-based authentication using Admin API key
- **Publish:** `POST /ghost/api/admin/posts/` with Mobiledoc or Lexical content
- **Markdown:** Ghost parses markdown into its internal format; tools like **MD2Ghost** (github.com/MirisWisdom/MD2Ghost) enable bulk markdown-to-Ghost publishing
- **Self-hosting:** Docker or Node.js deployment
- **Unique features:** Built-in membership/newsletter system, native SEO tools

### Static Site Generators (Hugo / Astro)

**Hugo:**
- Write markdown with YAML/TOML frontmatter -> `hugo build` -> deploy static files
- CI/CD: GitHub Actions workflow: checkout -> setup Hugo -> build -> deploy (Netlify, Cloudflare Pages, AWS S3, GitHub Pages)
- Typical workflow: `git push` triggers build + deploy in <60 seconds
- Themes: Hundreds available; Paper, PaperMod, and Stack are popular for dev blogs

**Astro:**
- Content Collections: type-safe markdown/MDX with schema validation
- Supports MDX (markdown + JSX components) for interactive content
- CI/CD: Same GitHub Actions pattern as Hugo
- Unique: Can embed React/Vue/Svelte components in markdown posts
- Custom integrations possible (e.g., auto-publish to Hashnode on build)

### Cross-Publishing Pipeline (Write Once, Publish Everywhere)

The most mature approach found in research:

1. **Write in markdown** in your primary blog repo (Hugo/Astro)
2. **GitHub Actions** on push to main:
   - Build and deploy primary site
   - Cross-post to Dev.to via API (set canonical URL to your site)
   - Cross-post to Hashnode via GraphQL API (set canonical URL)
   - Optionally push to Medium via import
3. **Tools for this:**
   - Custom GitHub Actions scripts (most common approach -- see references below)
   - `devto-publisher` GitHub Action for Hugo -> Dev.to
   - Astro integration for Hashnode (logarithmicspirals.com example)
   - Navin Varma's cross-publishing pipeline (Astro -> Dev.to + Hashnode + Medium)

**Key references:**
- Prachi Jamdade: "How to Automate Blog Publishing to Multiple Platforms" (dev.to, 2025)
- Isaac Dyor: "How to programmatically post to Dev.to, Hashnode, and Medium with GitHub Actions" (dev.to, 2024)
- Sergio Rodriguez: "GitHub Action to Publish Hugo Posts to Dev.to" (dev.to, 2026)
- Grizzly Coda: "Building a Write-Once Publishing Pipeline" (dev.to, 2026)

---

## 4. "Build in Public" Tooling

### Knowledge Base to Blog Pipelines

| Tool/Approach | Source | Output | CLI-Friendly |
|--------------|--------|--------|-------------|
| **Obsidian + Quartz** | Obsidian vault | Static site (digital garden) | Good -- `npx quartz build`, git-based |
| **Obsidian + GitHub Publisher** | Obsidian notes | GitHub repo -> static site | Moderate -- plugin-based, triggers git |
| **Obsidian + Dev.to plugin** (stroiman/obsidian-dev-publish) | Obsidian notes | Dev.to posts | Plugin-based |
| **Obsidian Blogger** | Obsidian vault | Blog via Cloudflare Pages | Good -- git push to deploy |
| **Notion to MD** (notion-to-md v4) | Notion pages | Markdown files | Good -- npm package, scriptable |
| **Obsidian-to-Notion** (EasyChris) | Obsidian notes | Notion pages | Plugin-based |
| **GitHub Issues -> Blog** | GitHub issue content | Pull request with blog post markdown | Excellent -- fully git/CLI native |

### Digital Garden / Working-in-Public Patterns

1. **Quartz v4** (quartz.jzhao.xyz): Most popular open-source tool for publishing Obsidian notes as a website. Supports backlinks, graph view, full-text search. Free hosting on GitHub Pages or Cloudflare Pages.

2. **GitHub Issues as CMS:** Write blog posts as GitHub issues, use a script/action to convert issue content into a markdown file in your blog repo, create PR, merge to publish. Fully CLI-native.

3. **Changelog-driven updates:** Use git commit history, planning docs, or CHANGELOG.md as source material for "build in public" updates. Script extracts recent changes and generates social posts.

4. **Project README/STATE.md as content source:** For projects with detailed planning docs (like this one), a script can diff STATE.md changes between dates and generate "what changed this week" summaries.

### Recommended "Build in Public" Stack for CLI Developers

```
Obsidian (writing) or VS Code (in-repo markdown)
    |
    v
Git repo (source of truth)
    |
    v
Hugo/Astro (primary blog) -- deployed via GitHub Actions
    |
    +---> Dev.to (cross-post via API)
    +---> Hashnode (cross-post via API)
    +---> LinkedIn (formatted post via PostFast or custom script)
    +---> Twitter/X (thread or summary)
```

---

## 5. Content Repurposing Tools

### Automated Repurposing Platforms

| Tool | Input | Output Formats | CLI/API | Price |
|------|-------|---------------|---------|-------|
| **BlogBurst** (blogburst.ai) | Blog posts, trending topics | Twitter, Bluesky, Discord, Telegram posts | API available | Free trial, then paid |
| **EchoWrite AI** (echowriteai.com) | Blog, podcast, YouTube | 14 social posts per input (Twitter + LinkedIn) | RSS/URL integration | Paid |
| **Distribution.ai** | Long-form content | Multi-platform social posts | API | Paid |
| **Repurpose.io** | Video/audio content | Multi-platform clips | Webhook/API | Paid |
| **Descript** | Video/audio | Clips, transcripts, social posts | Desktop app | Freemium |
| **Typefully** | Draft threads | Twitter threads, LinkedIn posts | API | Freemium |
| **Stormy AI** (stormy.ai) | Long-form video | 30-day cross-platform campaign | Web app | Paid |

### DIY Repurposing with LLMs (Most CLI-Friendly)

The most developer-friendly approach is scripting LLM calls with format-specific system prompts:

```bash
# Example: repurpose a research doc into multiple formats
cat research-doc.md | llm -s "Convert to a LinkedIn post (1200 chars, hook + body + CTA)" > linkedin-post.txt
cat research-doc.md | llm -s "Convert to a Twitter thread (5-7 tweets, each <280 chars)" > twitter-thread.txt
cat research-doc.md | llm -s "Convert to a dev.to blog post with frontmatter" > devto-post.md
cat research-doc.md | llm -s "Convert to a newsletter section (300 words, key insights)" > newsletter.md
```

Tools for this approach:
- **`llm` CLI** (simonwillison.net/llm) -- pipe text to LLMs from the terminal
- **Claude API** via `curl` or Python script
- **Custom shell functions** wrapping API calls with platform-specific system prompts

### Markdown-to-Platform Format Conversion

| Conversion | Tool/Method |
|------------|-------------|
| Markdown -> LinkedIn Unicode | ConnectSafely.ai converter, or custom script using Unicode bold/italic chars |
| Markdown -> Twitter thread | Split by headers/sections, truncate to 280 chars per tweet |
| Markdown -> Dev.to article | Direct (Dev.to accepts markdown natively with frontmatter) |
| Markdown -> Ghost post | MD2Ghost CLI tool, or Ghost Admin API with markdown body |
| Markdown -> Newsletter (HTML) | `pandoc` or `markdown-it` for HTML conversion, then embed in email template |

---

## 6. Recommended Architecture for This Project

Given a markdown-heavy, CLI-native workflow with research docs, planning phases, and technical content:

### Minimal Viable Pipeline

```
Phase 1: Write
  - Continue writing in markdown (planning docs, research, CLAUDE.md updates)
  - Tag publishable content with frontmatter or a marker

Phase 2: Transform (script)
  - Shell script or Python CLI that:
    1. Reads source markdown
    2. Calls Claude API with format-specific prompts
    3. Outputs: blog post, LinkedIn post, Twitter thread

Phase 3: Publish (script)
  - Blog: git push to Hugo/Astro repo -> GitHub Actions deploys
  - Dev.to: POST to /api/articles with canonical URL
  - LinkedIn: POST via PostFast API or direct LinkedIn API
  - Twitter: Manual or via Typefully API

Phase 4: Cross-post (GitHub Action)
  - On new blog post merge, automatically cross-post to Dev.to + Hashnode
```

### Tool Selection Summary

| Need | Recommended Tool | Why |
|------|-----------------|-----|
| Primary blog | **Hugo** or **Astro** | Markdown-native, fast, excellent CI/CD, free hosting |
| Cross-posting | **GitHub Actions + platform APIs** | Full control, no vendor lock-in |
| LinkedIn publishing | **PostFast API** or **direct LinkedIn API** | Developer-friendly, supports all content types |
| Content transformation | **Claude API + custom prompts** | Most flexible, maintains voice, handles technical content well |
| Markdown -> LinkedIn formatting | **ConnectSafely converter** or custom Unicode script | LinkedIn does not support markdown natively |
| Digital garden / notes | **Quartz v4** (if using Obsidian) | Best open-source option for publishing Obsidian notes |
| Content scheduling | **Typefully** (Twitter) + **PostFast** (LinkedIn) | Developer-friendly APIs |

### Key Decision Points

1. **Hugo vs Astro:** Hugo is simpler and faster for pure markdown blogs. Astro is more flexible if you want interactive components (React/Vue) or MDX. Both have excellent CI/CD stories.

2. **Self-host Ghost vs static site:** Ghost adds built-in newsletter/membership but requires server maintenance. Static sites (Hugo/Astro) are zero-maintenance once CI/CD is set up.

3. **Direct LinkedIn API vs intermediary (PostFast/Late.dev):** Direct API requires managing OAuth tokens and dealing with LinkedIn's restricted access tiers. Intermediary services handle this complexity for a fee.

4. **Automated vs semi-automated repurposing:** Fully automated risks losing voice/quality. Recommended: LLM generates drafts, human reviews before publishing.

---

## References

- Navin Varma, "Blog Syndication: Cross-Publishing Blog Posts to Dev.to, Hashnode, Medium" (2026) -- https://www.nvarma.com/blog/2026-02-10-cross-publishing-blog-posts-devto-hashnode-medium/
- Prachi Jamdade, "How to Automate Blog Publishing to Multiple Platforms" (2025) -- https://dev.to/prachijamdade/how-to-automate-blog-publishing-to-multiple-platforms-52po
- Isaac Dyor, "How to programmatically post to Dev.to, Hashnode, and Medium with GitHub Actions" (2024) -- https://dev.to/isaacdyor/how-to-programmatically-post-your-personal-blogs-to-devto-hashnode-and-medium-with-github-actions-pp2
- Sergio Rodriguez, "GitHub Action to Publish Hugo Posts to Dev.to" (2026) -- https://dev.to/w4ls3n/github-action-to-publish-hugo-posts-to-devto-2nmp
- Grizzly Coda, "Building a Write-Once Publishing Pipeline" (2026) -- https://dev.to/12ww1160/building-a-write-once-publishing-pipeline-4ila
- Late.dev, "How to Post to LinkedIn via API" (2025) -- https://getlate.dev/blog/post-to-linkedin-via-api
- Late.dev, "LinkedIn Posting API Guide" (2025) -- https://getlate.dev/blog/linkedin-posting-api
- PostFast, "Schedule LinkedIn Posts via API" -- https://postfa.st/api-guides/linkedin/posting
- ObsidianStats, "Best Plugins for Publishing Obsidian Notes Online" (2025) -- https://www.obsidianstats.com/posts/2025-04-16-publish-plugins
- ConnectSafely, "Convert Markdown to LinkedIn Post" (2025) -- https://connectsafely.ai/articles/markdown-to-linkedin-post-converter-guide-2026
- MirisWisdom/MD2Ghost, "Publish Markdown files to Ghost CMS in bulk" -- https://github.com/MirisWisdom/MD2Ghost
- logarithmicspirals, "Creating a Custom Astro Integration: Auto-Publishing to Hashnode" (2024) -- https://logarithmicspirals.com/blog/astro-hashnode-cross-posting-integration/
