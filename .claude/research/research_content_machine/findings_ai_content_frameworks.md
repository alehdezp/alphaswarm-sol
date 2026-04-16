# AI-Assisted Content Creation: Tools, Frameworks, and Voice Preservation

**Research date:** 2026-02-20
**Confidence level:** High (based on 12+ searches across Exa, Brave, and direct page crawls)

---

## 1. AI Writing Assistants for Technical Content

### Dedicated Tools

| Tool | Focus | Pricing | Notes |
|------|-------|---------|-------|
| **Lex.page** | AI-powered word processor | Free tier + paid | Google Docs-like editor with inline AI. Type `+++` to get AI continuation. Supports GPT-3/4 model selection and a "creativity" slider. Best for long-form writing with AI as a co-pilot, not a replacement. Founded by Nathan Baschez (True Ventures-backed). |
| **Typefully** | Social/thread writing | Free tier + paid ($12.50/mo+) | Focused on Twitter/LinkedIn threads. AI suggestions for hooks and rewrites. Good for short-form technical content distribution, not creation. |
| **Jasper** | Marketing content | $49/mo+ | Enterprise-oriented. Brand voice features, templates. Overkill for solo technical writers. Heavy marketing-speak bias. |
| **Copy.ai** | Marketing copy | Free tier + $49/mo | Similar to Jasper. Workflow automation focus. Not designed for deep technical writing. |
| **Grammarly** | Language/grammar | Free + $12/mo | Not a generation tool but excellent for editing. AI rewrite suggestions. Good complement to any workflow. |

### Assessment for Solo Developer-Researcher

Lex.page is the only tool here genuinely designed for thoughtful long-form writing. The others optimize for marketing copy volume. For a technical writer, the better approach is **Claude/GPT directly with structured prompts** rather than any of these tools --- the intermediary layer adds cost without adding value for someone comfortable with LLMs.

The most interesting pattern emerging (late 2025/early 2026): **Claude Code itself as the writing environment**, using skills and slash commands to create a local-first, version-controlled writing workflow.

---

## 2. Claude Code Skills for Content Creation

### The Book Factory Pattern (Robert Guss)

- **URL:** https://robertguss.github.io/claude-skills/
- **Listed in:** awesome-claude-code (hesreallyhim/awesome-claude-code)
- **What it is:** A comprehensive pipeline of Claude Code skills that replicates traditional publishing infrastructure for nonfiction book creation. Specialized skills handle different phases: outlining, drafting chapters, editing, fact-checking, formatting.
- **Key insight:** Treats book-writing as a multi-agent pipeline, similar to how software is built. Each skill handles one concern. This is the most ambitious content-creation skill set found.

### Cloud Artisan Blog Commands (David Taylor)

- **URL:** https://cloudartisan.com/posts/2025-04-14-claude-code-tips-slash-commands/
- **What it is:** Project-scoped slash commands for managing a Hugo blog:
  - `/project:posts:new` --- Create new post with proper front matter
  - `/project:posts:check_language` --- UK English spelling/grammar check
  - `/project:posts:check_links` --- Verify all links
  - `/project:posts:publish` --- Publish draft and push to GitHub
  - `/project:posts:find_drafts` --- List all draft posts
  - `/project:posts:check_images` --- Verify image references
- **Key insight:** Version-controlled commands in `.claude/commands/`. Simple markdown files. The friction-reduction philosophy: every repetitive blog task becomes a one-liner. This is the most practical, immediately-useful pattern for a solo technical blogger.

### Jo Vinkenroye's `/blog` Skill

- **Source:** LinkedIn post (Jan 2026), part of his Claude Code Mastery series
- **What it does:** Single command `/blog ~/Sites/my-project` that:
  - Explores the project directory
  - Finds screenshots
  - Creates MDX file with frontmatter
  - Writes in the author's voice (trained from examples)
  - Commits everything
  - Opens dev server preview
- **Key insight:** "This post was written using it." End-to-end from project to published blog post in one command.

### automationcreators/claude-code-skills

- **URL:** https://github.com/automationcreators/claude-code-skills
- **What it is:** Collection of Claude Code skills for content creation, document manipulation, development tools. Includes creative applications (art, music, design) and enterprise workflows (communications, branding).
- **Languages:** Python (89%), JavaScript (6.5%)

### OneWave-AI/claude-skills

- **URL:** https://github.com/onewave-ai/claude-skills
- **What it is:** "100 Production-Ready Claude Code Skills" covering sales, business automation, content creation, and development.

### alirezarezvani/claude-skills

- **URL:** https://github.com/alirezarezvani/claude-skills
- **Content-creator skill:** Includes blog post writing, brand voice analysis from sample articles, LinkedIn content calendar generation.

### ProductTalk SEO/Headlines Commands

- **URL:** https://www.producttalk.org/how-to-use-claude-code-features/
- **What it does:** `/headlines` command for brainstorming with personal preference context. `/seo` command that analyzes posts, identifies keywords, generates semantic variants, looks up keyword volumes via API, produces optimization analysis.
- **Key insight:** Demonstrates how a content skill can call external APIs (keyword volume lookup) to produce data-informed content decisions.

### Rohit Chavane's WordPress Post Publisher

- **URL:** https://notes.rohitchavane.com/p/claude-code-for-marketing-wordpress
- **What it is:** Non-developer marketer built a docx-to-WordPress-draft pipeline using Claude Code. Demonstrates the accessibility of this approach.

### Sabrina Ramonov's AI Marketing Officer

- **URL:** https://www.sabrina.dev/p/claude-code-full-course-for-beginners
- **What it is:** Full course building a "personalized AI Marketing Officer" with Claude Code that adapts content for Twitter, LinkedIn, Instagram, and Facebook.

### Andreas Stockl's Headless CMS Skill

- **URL:** https://medium.com/@andreasstckl/claude-skills-for-web-publishing-79d795aa7885
- **What it is:** Claude skills as a front-end for a headless CMS. Combines Claude's content generation with CMS storage and organization.

---

## 3. Voice Preservation Techniques

### Academic Research: "Who Owns the Text?" (Zhang, Bu, Dhillon --- arXiv 2601.10236, Jan 2026)

This is the most rigorous study found on preserving authorship in AI-assisted writing. Key findings:

1. **Psychological ownership decreases** whenever AI assists, even when the output is helpful
2. **The ownership-efficiency paradox:** The more efficiently AI helps, the less the writer feels the text is "theirs"
3. **Persona framing** (telling AI to act as a writing coach) stabilizes the writer's *stance* but not their *voice*
4. **Style personalization** (conditioning suggestions on the writer's prior samples) partially restores ownership --- this is the strongest intervention tested
5. **Design patterns identified:**
   - "Suggest, don't insert" --- AI proposes, human decides
   - "Show provenance" --- mark which text is AI-generated vs. human
   - "Edits-only mode" --- AI can only modify existing text, not generate new blocks

### Practical Voice-Matching Techniques

From Louis Bouchard / Towards AI (louisbouchard.ai/ai-editing/):

**The core insight:** "AI slop" is not just word choice --- it's *structural*. Even if you remove "delve" and "landscape," the skeleton (bullet-heavy, symmetric sections, generic conclusions) still feels synthetic.

**Concrete techniques:**

1. **You own the structure; the model fills it.** Write your own outline with asymmetric sections. Let AI draft within your structure, not create its own.

2. **Provide your own writing samples** as context. 3-5 previous posts as few-shot examples is more effective than any style description.

3. **Negative constraints are powerful:** "Do NOT use: delve, landscape, realm, underscore, meticulous, commendable, em-dashes, 'In conclusion,' 'It's worth noting that.'" Ban specific words and patterns.

4. **Control paragraph shape:** Specify that paragraphs should vary in length. Some 1-sentence. Some 5-sentence. No uniform blocks.

5. **Read-aloud test:** If you wouldn't say it to a friend, it's AI slop. This is the fastest filter.

### The Stormy AI "Anti-Slop" Framework

From stormy.ai/blog/scaling-brand-content-claude-constraints:

1. **Architected Brief > Vague Request:** Include action verb + specific quantity + defined target audience in every prompt
2. **Persona tuning per funnel stage:** Expert (technical depth), Brief (social media conciseness), Simplifier (explain-like-I'm-five)
3. **Negative constraints to kill cliches:** "Do not use the word 'cyber' or 'neon'" forces creative alternatives
4. **Scaffolding:** Provide the structure, let AI fill sections
5. **Divide and conquer for long-form:** Break into sections, generate separately, unify voice in editing pass

### The Reddit Consensus (r/PromptEngineering)

Common AI-slop markers to explicitly ban:
- Em dashes used excessively
- "It's not X, but Y" pattern
- Snappy one-line sentences as transitions
- Excessive emoji
- "Delve," "realm," "landscape," "underscore," "meticulous"
- "In this article, we will explore..."
- Generic zoom-out conclusions ("As AI continues to evolve...")

Most effective counter-techniques:
- **Few-shot with your own writing** (highest signal)
- **Explicit word/pattern banlists**
- **"Write as if explaining to a smart friend over coffee"** framing
- **Specify sentence length variance:** "Mix short punchy sentences with longer complex ones"
- **Inject specific details:** "Reference the exact Solidity opcode, not 'low-level operations'"

---

## 4. The "Draft then Refine" Workflow

### ArthurJ's "Writing as Search" Philosophy (dev.to)

The most intellectually honest framing found:

> "One useful way to think about writing is as a search problem. AI is useful when it helps you explore the search space (multiple framings, objections, structures) *before* you commit."

**His workflow:**
1. Start with bullet points in a markdown file (the idea)
2. Use AI to **expand the search space**: "Give me 5 different angles on this idea"
3. Use AI to **stress-test**: "What's the strongest objection to this argument?"
4. Use AI to **explore structure**: "Show me 3 different ways to organize these points"
5. **Human commits** to one angle, one structure, one argument
6. Use AI to **draft within that committed frame**
7. Human edits for voice

**Key insight:** "AI as research assistant, not ghostwriter." The ideas, opinions, and structure decisions are human. The AI accelerates exploration of possibilities.

### The "Chain of Draft" Technique (sgryt.com)

From Sergii Grytsaienko's analysis of iterative LLM drafting:

1. **Draft 1 (Skeleton):** AI generates a bare structural outline with key claims
2. **Draft 2 (Flesh):** AI expands each section with evidence, examples, transitions
3. **Draft 3 (Polish):** AI refines language, fixes flow, tightens prose
4. **Human pass:** Inject personality, cut fluff, add specific anecdotes

This mirrors the "facts then narrative then polish" pattern but adds explicit iteration.

### The Towards AI Editorial Workflow

From 2 years of editing thousands of AI-assisted submissions:

1. **Human writes the outline and key claims** (non-negotiable)
2. **AI drafts sections** within that structure
3. **Human identifies "tells"** --- structural uniformity, generic examples, zoom-out conclusions
4. **AI rewrites flagged sections** with specific constraints
5. **Human does final voice pass** --- adding personal anecdotes, specific details, opinions

**The prompt template they use (paraphrased):**
```
You are helping me draft a section of a technical article.

My writing style: [3 example paragraphs from previous work]

Section topic: [specific claim or point]
Target audience: [specific reader persona]
Length: [word count range]

Constraints:
- No bullet lists unless showing code examples
- Vary paragraph length (1-5 sentences)
- Use specific, concrete examples, not generic ones
- Do not start any paragraph with "It's worth noting" or "In conclusion"
- Write as if explaining to a colleague, not lecturing a student
```

### WorkWithAI.expert Framework

Key principles for professional documents:
- **Workflow matters more than prompts**
- **AI is a drafting and editing assistant, not a document owner**
- **Editing with AI is safer than full generation**
- **Structure before text** --- define the skeleton yourself
- **Human judgment defines quality, tone, and responsibility**

---

## 5. MCP Servers for Content/Publishing

### WordPress MCP

| Server | URL | Maturity |
|--------|-----|----------|
| **Automattic/wordpress-mcp** (official, now deprecated in favor of mcp-adapter) | https://github.com/Automattic/wordpress-mcp | High --- official Automattic project. Being transitioned to WordPress/mcp-adapter |
| **WordPress/mcp-adapter** (successor) | https://github.com/WordPress/mcp-adapter | Active development. Released Feb 2026. Lets AI models interact with WordPress sites: add banners, publish posts, format using existing theme elements |

**Capabilities:** Post creation/editing, media upload, theme manipulation, content formatting. Multiple users report publishing full blog posts from Word docs without opening WordPress.

### Ghost CMS MCP

| Server | URL | Maturity |
|--------|-----|----------|
| **mtane0412/ghost-mcp-server** | https://glama.ai/mcp/servers/@mtane0412/ghost-mcp-server | Moderate. TypeScript. Remote deployment supported. |
| **datawithjavi Ghost MCP** | https://www.datawithjavi.com/building-a-ghost-cms-mcp-server/ | Documented build-your-own approach. Covers post management, member management, newsletter management. |
| **Ghost Forum official thread** | https://forum.ghost.org/t/i-built-a-ghost-mcp-server-so-that-you-can-control-ghost-from-claude/55236 | Community-built. |

**Capabilities:** Full Ghost Admin API access --- post CRUD, page management, member management, newsletter management. Can manage entire blog through Claude conversation.

### Hashnode MCP

| Server | URL | Maturity |
|--------|-----|----------|
| **sbmagar13/hashnode-mcp-server** | https://github.com/sbmagar13/hashnode-mcp-server | Early. Community-built. |

**Capabilities:** Publish posts, manage content via Hashnode's GraphQL API.

### Dev.to / Multi-Platform MCP

| Server | URL | Maturity |
|--------|-----|----------|
| **BlogCaster MCP** | https://dev.to/bamacharan (Cloudflare Worker) | Early but functional. Published a real Dev.to post through it. |

**Capabilities:** Multi-platform publishing (Hashnode + Dev.to) from a single MCP tool call:
```
publishPost(
  title: "...",
  contentMarkdown: "...",
  platforms: ["hashnode", "devto"]
)
```

### LinkedIn MCP

| Server | URL | Maturity |
|--------|-----|----------|
| **mcpflow/mcp-server-linkedin** | https://github.com/mcpflow/mcp-server-linkedin | Early. |
| **dhrishp LinkedIn Post MCP** | https://www.pulsemcp.com/servers/dhrishp-post-linkedin | Early. Requires Node.js. |
| **alinaqi LinkedIn MCP** | https://www.pulsemcp.com/servers/alinaqi-linkedin | Early. Text, media, link sharing. |

**Capabilities:** Direct publishing of text content, media attachments, link sharing. All are early-stage and require developer setup.

### Medium

No dedicated MCP server found. Medium's API is notoriously limited (no official write API for new posts since ~2023). Most workflows use manual copy-paste or browser automation.

### Assessment

**WordPress** is the most mature, now with official Automattic backing. **Ghost** has multiple community implementations and is well-suited for developer blogs. **Hashnode** and **Dev.to** have working MCP servers but are early. **LinkedIn** MCP servers exist but are rudimentary. The multi-platform BlogCaster pattern (write once, publish to multiple platforms) is the most interesting emerging approach.

---

## 6. Prompting Patterns for Non-Generic Output

### Pattern 1: Contrarian Framing

```
Instead of writing "why X is good," write "why most people are wrong about X."
Force the AI to take a position, not summarize consensus.
```

This produces output with inherent tension and argument, which reads as more authentic because generic AI output avoids controversy.

### Pattern 2: "Explain to a Friend" Tone

```
Write as if you're explaining this to a smart friend over drinks.
Use "you" and "I". Include one self-deprecating aside.
No formal transitions. Jump between ideas the way conversation does.
```

### Pattern 3: Hook-First Structure

```
Start with the most surprising or counterintuitive claim.
No throat-clearing introduction. No "In today's rapidly evolving landscape."
First sentence should make someone stop scrolling.
```

### Pattern 4: The "3 Passes" Approach

1. **Pass 1 (Facts):** "List the 7 key technical facts about [topic]. No narrative. Just claims with evidence."
2. **Pass 2 (Narrative):** "Now weave these facts into a story. Start with the problem someone faces. End with what they should do differently."
3. **Pass 3 (Voice):** "Rewrite this in my voice. Here are 3 examples of my writing: [samples]. Make it sound like me, not like a textbook."

### Pattern 5: Negative Constraint Stacking

```
Rules:
- No sentences starting with "It is" or "There are"
- No em-dashes
- No bullet lists (use flowing paragraphs)
- No sentences over 25 words
- No abstract nouns without concrete examples
- Never use: delve, realm, landscape, crucial, leverage, robust, seamless
- Do not conclude with a "bigger picture" paragraph
```

### Pattern 6: Persona Adoption (Advanced)

From AI Fire's analysis of lab-internal techniques:

```
You are not an AI assistant. You are a burned-out senior engineer
who has seen three startups fail and finally found something that works.
You're skeptical of hype but genuinely excited about this specific thing.
Your humor is dry. You use concrete numbers, not adjectives.
```

This works because it constrains the LLM's "personality distribution" to a narrow, specific region rather than the broad "helpful assistant" default.

### Pattern 7: Structured Imperfection

```
Include one tangent that you then catch yourself on:
"But that's a different rant."
Leave one question genuinely unanswered.
Use "I think" or "I'm not sure" at least once.
```

This deliberately introduces the kind of rough edges that signal human authorship.

---

## 7. Anti-AI-Detection and Authenticity

### Why This Matters (Not for Deception)

The goal is not to deceive readers into thinking AI wasn't involved. The goal is to ensure the output **actually represents your thinking** rather than generic LLM consensus. If your content could have been written by anyone with ChatGPT access, it adds no value.

### The Bouchard Framework (Towards AI, 2 Years of Data)

**Structural tells are harder to fix than word tells:**

1. **Word-level:** Easy to fix. Ban "delve," "landscape," etc. Use negative constraints.
2. **Sentence-level:** Medium. Vary length. Mix simple and complex. Add fragments.
3. **Paragraph-level:** Hard. Vary paragraph length. Avoid uniform 3-sentence blocks.
4. **Section-level:** Hardest. Avoid symmetric sections. Let some be 3x longer than others. Don't mirror headings.

**The "delve" problem is a proxy for a deeper issue:** RLHF training biases models toward formal, hedged, comprehensive prose. The output sounds like a textbook because it was trained to be maximally "helpful" in a way that rewards thoroughness over personality.

### Concrete Authenticity Techniques

1. **Inject specific details only you would know:**
   - Bad: "In my experience with smart contracts..."
   - Good: "When I audited the Compound v3 Comet migration, the `absorb()` function had a subtle re-entrancy window that Slither completely missed because..."

2. **Personal anecdote placeholders:**
   - Write `[ANECDOTE: that time I spent 3 hours debugging a gas estimation issue]` in the draft
   - Force yourself to fill these with real stories in the editing pass

3. **Opinion markers:**
   - "I think X is overrated"
   - "Most articles get this wrong"
   - "Here's what nobody tells you about Y"
   - These signal a point of view, which is the defining characteristic of non-generic content

4. **Conversational asides:**
   - "(Yes, I know this contradicts what I said in my last post. I changed my mind.)"
   - "If this sounds obvious, great --- skip to section 3."

5. **Sentence variety injection:**
   - One-word sentences. "Really."
   - Questions to the reader. "Have you ever actually read the EIP-4337 spec? Neither had I."
   - Deliberately incomplete thoughts. "But that's for another post."

6. **Anti-patterns to avoid:**
   - Never let AI write your introduction (it will throat-clear)
   - Never let AI write your conclusion (it will zoom out to platitudes)
   - Never accept the first draft's structure (it will be symmetric)

### The "Ownership-Efficiency Paradox" (Zhang et al., 2026)

The research finding that more AI help = less authorial ownership has practical implications:

- **Use AI for research expansion, not prose generation** (preserves ownership)
- **Use AI for editing/tightening, not drafting** (safer for voice)
- **Use "suggest, don't insert" mode** when possible
- **Style personalization** (providing your writing samples) is the strongest tested intervention for preserving the feeling that the text is "yours"

---

## 8. Recommended Architecture for a Solo Developer-Researcher

Based on all findings, the highest-leverage setup:

### Core Stack

1. **Writing environment:** Claude Code with custom skills (not a separate tool)
2. **Content storage:** Git-managed markdown files (local-first, version-controlled)
3. **Publishing:** Ghost CMS MCP or static site generator (Hugo/Astro) with deploy scripts
4. **Distribution:** LinkedIn MCP + manual for other platforms (or BlogCaster for multi-platform)

### Custom Skills to Build

```
.claude/skills/
  content-draft/SKILL.md      # Drafts from outline + voice samples
  content-edit/SKILL.md       # Edit pass with anti-slop constraints
  content-publish/SKILL.md    # Publish to target platform
  content-research/SKILL.md   # Research expansion from bullet points
  content-hooks/SKILL.md      # Generate hooks/titles from draft
```

### The Workflow

```
1. Human writes bullet points (ideas, claims, opinions)
2. /content-research --- AI expands search space, finds counter-arguments
3. Human commits to angle and structure
4. /content-draft --- AI drafts within human structure, using voice samples
5. Human edits: injects anecdotes, cuts fluff, adds opinions
6. /content-edit --- AI tightens prose with anti-slop constraints
7. Human final pass: read aloud, fix anything that "sounds like AI"
8. /content-publish --- Push to Ghost/Hugo/whatever
```

### Key Principles

- **Never let AI choose the structure.** That's where your thinking happens.
- **Always provide 3-5 writing samples** as few-shot context for voice matching.
- **Maintain a banlist** of AI-slop words/patterns in your skill's system prompt.
- **The introduction and conclusion are yours.** AI can draft the middle.
- **Version control everything.** Your drafts, your prompts, your banlist. Iterate.

### What NOT to Use

- Jasper/Copy.ai/generic marketing tools (wrong audience, wrong output style)
- "AI humanizer" tools (post-hoc fixing of a fundamentally generic draft is worse than prompting correctly from the start)
- Full automation pipelines without human editing (the Reddit post about Claude "running my entire content strategy" is a recipe for brand-damaging slop)

---

## Sources

1. Cloud Artisan blog commands: https://cloudartisan.com/posts/2025-04-14-claude-code-tips-slash-commands/
2. Bouchard/Towards AI anti-slop guide: https://www.louisbouchard.ai/ai-editing/
3. Stormy AI anti-slop framework: https://stormy.ai/blog/scaling-brand-content-claude-constraints
4. ArthurJ "Writing as Search": https://dev.to/arthurbiensur/ai-assisted-writing-as-search-not-draft-generation-4io8
5. Zhang et al. "Who Owns the Text?": https://arxiv.org/abs/2601.10236
6. Book Factory (Robert Guss): https://robertguss.github.io/claude-skills/ (via awesome-claude-code)
7. WordPress MCP (official): https://github.com/Automattic/wordpress-mcp
8. Ghost MCP: https://glama.ai/mcp/servers/@mtane0412/ghost-mcp-server
9. BlogCaster MCP: https://dev.to/bamacharan/i-built-an-mcp-server-that-publishes-blogs-automatically-and-this-post-was-published-through-it-4gjh
10. Hashnode MCP: https://github.com/sbmagar13/hashnode-mcp-server
11. LinkedIn MCP: https://github.com/mcpflow/mcp-server-linkedin
12. awesome-claude-code: https://github.com/hesreallyhim/awesome-claude-code
13. awesome-claude-skills: https://github.com/ComposioHQ/awesome-claude-skills
14. OneWave-AI skills: https://github.com/onewave-ai/claude-skills
15. automationcreators skills: https://github.com/automationcreators/claude-code-skills
16. Chain of Draft technique: https://sgryt.com/posts/enhancing-llm-outputs-chain-of-draft/
17. WorkWithAI.expert: https://workwithai.expert/read/using-ai-for-professional-documents
18. Jo Vinkenroye Claude Code Mastery: https://www.jovweb.dev/blog/claude-code-mastery-08-production-workflows
19. Anthropic skills guide PDF: https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
20. Sabrina Ramonov full course: https://www.sabrina.dev/p/claude-code-full-course-for-beginners
21. ProductTalk Claude Code features: https://www.producttalk.org/how-to-use-claude-code-features/
22. r/PromptEngineering anti-slop discussion: https://www.reddit.com/r/PromptEngineering/comments/1m84tqc/
