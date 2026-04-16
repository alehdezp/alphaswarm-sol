# Knowledge Extraction: Turning Project Work into Published Content

**Research date:** 2026-02-20
**Confidence level:** High (based on 12+ web searches, multiple primary sources, established practices)

---

## Executive Summary

The most effective content extraction systems share three properties: (1) they capture insights **during** work, not after; (2) they use structured metadata that makes documents machine-mineable; and (3) they map internal document types to external content formats with minimal transformation. The key insight for a solo developer is that **every decision, debugging session, and experiment is already 80% of a blog post** -- the missing 20% is narrative framing and audience context, which can be added cheaply if the raw material is well-structured.

---

## 1. ADRs as Content: Each Decision = One Post

### How ADRs Map to Blog Posts

Architecture Decision Records (ADR) -- particularly the MADR (Markdown Any Decision Records) format -- are structurally almost identical to a good technical blog post. The mapping is direct:

| ADR Section | Blog Post Section |
|---|---|
| **Context** | "The problem we faced" (hook) |
| **Decision Drivers** | "What mattered to us" (constraints) |
| **Considered Options** | "What we evaluated" (the meat) |
| **Decision Outcome** | "What we chose and why" (conclusion) |
| **Consequences** | "What happened next" / "What we learned" |

**The MADR template** (v4.0, from adr.github.io) adds `Pros and Cons of each Option`, which maps perfectly to the comparison-style blog post that performs well in search.

### Key Insight: The "Structured MADR" Extension

Robert Allen's Structured MADR (2026) adds YAML frontmatter to ADRs, making them machine-queryable. This is directly relevant to content extraction:

```yaml
---
status: accepted
date: 2026-01-15
decision-makers: [team-lead]
tags: [security, authentication, database]
# Content extraction metadata (my addition):
content_readiness: high
key_insight: "We chose Argon2id over bcrypt because..."
audience: [backend-developers, security-engineers]
---
```

With this metadata, you can programmatically query: "Show me all accepted decisions tagged 'security' with content_readiness >= medium" and get a list of blog post candidates.

### Practical Pattern for Solo Developer

1. Write ADRs as you make decisions (you should do this anyway)
2. Add a `## Key Takeaway` section at the bottom (one sentence a reader would remember)
3. Add `content_readiness: draft|ready|published` to frontmatter
4. When you need a blog post, run a query over your ADRs for `ready` items
5. Wrap the ADR in a narrative intro ("Last week we hit a problem...") and publish

**Source:** adr.github.io, ozimmer.ch MADR primer, zircote.com Structured MADR, m7y.me "ADRs: Actually Using Them"

---

## 2. Companies That Publish From Internal Research

### Trail of Bits: Research Practice to Blog Pipeline

Trail of Bits is the gold standard for turning internal security research into published content. Their pattern:

1. **Every audit produces internal research artifacts** -- tool improvements, novel findings, methodology refinements
2. **Research is categorized by practice area** (engineering-practice, research-practice, security-reviews)
3. **Blog posts are extracted from real work** -- e.g., "Making PyPI's test suite 81% faster" came directly from their PyPI collaboration work
4. **They follow a "don't just fix bugs, fix software" philosophy** that naturally produces systemic insights rather than one-off fixes

**What makes it work:** Their blog posts are always grounded in *specific, real work* with *measurable outcomes*. "We reduced test execution from 163s to 30s" is a blog post. "Testing is important" is not.

**Extraction pattern:** Real engagement -> internal writeup -> extract the "why and how" -> blog post with concrete numbers.

### Stripe: Writing Culture as Content Factory

Stripe's internal writing culture (documented extensively by Dave Nunez, their Documentation Manager, and by the Kool-Aid Factory essay) reveals a systematic approach:

1. **Leaders write with research-paper rigor** -- CEO Patrick Collison's emails literally had footnotes. This set the cultural standard.
2. **Narrative memos replace slide decks** -- "From leadership on down, we default to writing. We don't really have slide decks." This means every project kickoff already has a written narrative.
3. **Sample docs over templates** -- Rather than blank templates, Stripe creates exemplary documents (a detailed guide on "the life of a Stripe charge") that teams use as reference. This is more useful than Mad Libs-style fill-in.
4. **Standardize only high-leverage documents** -- Documents with broad audiences get editorial oversight; team-internal docs have autonomy.
5. **"Shipped emails"** -- Decision logs published into team Slack channels, even for small decisions. Multiple ex-Stripes report missing the "shipped email" culture at subsequent companies.

**The Kool-Aid Factory framework** distinguishes two types of internal writing:
- **Papertrails**: documented accounts produced *during* work (meeting notes, decision logs, status updates)
- **Curations**: editorialized summaries produced *for* the broader organization (like Amazon's 6-page narratives)

**Key takeaway for solo dev:** Both papertrails and curations are content sources, but curations are closer to publishable because they already have an audience in mind. If you write even brief "shipped" notes after completing significant work, you have curations to mine.

### Cloudflare: Incidents as Content

Cloudflare turns major incidents into detailed, public-facing post-mortems that serve as both accountability and content:
- November 2025 outage -> detailed technical blog post with architectural diagrams
- "Code Orange: Fail Small" resilience plan -> published as a blog post explaining their internal improvement program
- Each incident blog post follows: **Timeline -> Root Cause -> What We're Doing About It -> Architectural Changes**

This works because incidents have natural narrative tension. Something broke. Here's why. Here's what we learned.

### Rekt News: Incident Analysis as Engaging Narrative

Rekt News transforms DeFi security incidents into compelling investigative journalism. Their writing technique:

1. **Hook with dramatic irony** -- "Emergency functions make excellent getaway vehicles."
2. **Narrative voice with attitude** -- Unlike dry post-mortems, Rekt uses sardonic commentary: "When the person who stole your money starts fact-checking your security providers, what does that say about who's really watching the watchers?"
3. **Structure as investigation** -- They don't just report what happened; they follow the thread of accountability: who audited, what was in scope, who's pointing fingers.
4. **Credits section** -- Every piece credits all sources, building credibility and a network effect.
5. **Pattern recognition across incidents** -- They connect individual events to systemic issues (audit industry credibility, admin key management, etc.)

**Extraction insight:** Rekt proves that even highly technical incidents can be engaging content if you add: (a) a point of view, (b) narrative structure, and (c) the "so what" connecting it to a larger pattern.

**Sources:** blog.trailofbits.com, slab.com/blog/stripe-writing-culture, koolaidfactory.com, rekt.news

---

## 3. Experiment Reports as Content

### The Scientific Method Blog Post Format

The most underused content format in tech blogging is the experiment report. Structure:

```
## Hypothesis
"I believed X would improve Y because Z"

## Method
"Here's exactly what I did, step by step"

## Results
"Here's what actually happened" (with numbers)

## Discussion
"Here's why I think it happened, what surprised me, and what I'd do differently"
```

### Why Failed Experiments Make Better Content

The "negative results" movement in scientific publishing has a direct parallel in tech blogging:

1. **Failed experiments are more memorable** -- "Why we chose NOT to use microservices" outperforms "Why we chose microservices" because it defies expectations
2. **They build trust** -- Admitting failure signals honesty and expertise. You must understand something deeply to explain why it didn't work.
3. **They save others time** -- The highest-value content is "I tried X so you don't have to." This is the debugging equivalent of a negative result.
4. **They have natural narrative tension** -- "I expected A, got B instead" is inherently interesting.

### The "Negative Results" Blog Post Template

```markdown
# Why [Approach X] Didn't Work For [Our Use Case]

## What We Expected
[Clear hypothesis with reasoning]

## What We Tried
[Specific steps, tools, configuration -- enough to reproduce]

## What Actually Happened
[Honest results with data. Screenshots, benchmarks, logs.]

## Why It Failed
[Root cause analysis. Was our assumption wrong? Was the tool wrong?
Was our use case an edge case?]

## What We Did Instead
[The alternative that worked, or why we're still searching]

## The Takeaway
[One sentence: when SHOULD you use this approach, and when shouldn't you?]
```

**Key insight:** The most compelling failed-experiment posts include the emotional journey -- "I was confident this would work because..." followed by "...and then this happened." This is what Julia Evans excels at.

---

## 4. Content Extraction From Planning Artifacts

### What Makes Planning Docs Mineable

Not all planning documents are equal for content extraction. The key differentiator is **whether the document captures the "why" or just the "what."**

| Document Type | Content Potential | Why |
|---|---|---|
| Context files (CONTEXT.md) | **High** | Capture problem space, constraints, landscape analysis |
| Improvement passes | **High** | Each pass is a micro-experiment with hypothesis and results |
| Research notes | **Very High** | Raw insights, often with surprising findings |
| Gap analyses | **Medium** | Good for "state of X" overview posts |
| Task lists / backlogs | **Low** | Just "what" without "why" |
| Status updates | **Low** | Ephemeral, lacks depth |

### Frontmatter Schema for Content Readiness

A practical schema for tagging documents with content extraction metadata:

```yaml
---
title: "Reasoning Evaluation Framework Design"
type: context | research | improvement | decision | experiment
date: 2026-02-15
content:
  readiness: none | seed | draft | ready | published
  key_insight: "One-sentence takeaway a reader would remember"
  audience: [developers, security-researchers, ai-practitioners]
  format_hint: tutorial | deep-dive | comparison | narrative | how-to
  hook: "What if your tests pass but your AI agent reasons badly?"
  estimated_effort: low | medium | high  # effort to convert to publishable
tags: [testing, ai-evaluation, reasoning]
---
```

The critical fields are:
- **key_insight**: Forces you to crystallize the one thing worth sharing. If you can't write this, the document isn't content-ready.
- **format_hint**: Tells you what kind of post this naturally becomes.
- **hook**: The opening line. If a document has a good hook, it's 50% of the way to being published.
- **estimated_effort**: Triage for when you need a quick post vs. a deep investment.

### Mining Pattern: The Inverted Pyramid

For each planning artifact, apply the **"Key Insight" inverted pyramid**:

1. **Lead with the insight** -- What did you learn that someone else would find valuable?
2. **Support with evidence** -- What data, experiment, or experience supports this?
3. **Provide context** -- What was the situation? Why did this come up?
4. **Add detail** -- Technical specifics for those who want to go deeper.

This inverted structure means you can extract content at multiple depths: a tweet (layer 1), a short post (layers 1-2), a full article (all layers).

---

## 5. The "Content Seed" Pattern

### Capturing Publishable Moments DURING Work

The core problem with content creation is that insights are perishable. You have the clearest understanding of *why* something matters at the moment you discover it, not two weeks later when you sit down to write.

**swyx's "Learning in Public" philosophy** (the most influential articulation of this idea) puts it simply: "have a habit of creating learning exhaust." The key word is *exhaust* -- it's a byproduct of work, not a separate activity.

### Practical Techniques

**1. Inline Content Markers**

While working, drop markers into your documents, commit messages, or notes:

```markdown
<!-- CONTENT_SEED: This approach to graph scoring is novel because
     most systems treat graph compliance as binary, but we score on
     a spectrum from "checkbox compliance" to "genuine reasoning" -->
```

Or in commit messages:
```
fix(scoring): weight graph queries by reasoning depth

CONTENT: The insight here is that counting queries isn't enough --
you need to distinguish "asked a question" from "used the answer
to change your conclusion."
```

**2. The "Voice Note to Self" Pattern**

After a breakthrough or surprising discovery, record a 30-second voice note or write 2-3 sentences answering:
- What surprised me?
- Why does this matter?
- Who else would care about this?

These seeds can be expanded into posts later with minimal effort because they capture the emotional truth of the moment.

**3. The "Content Hook" Tagging System**

Maintain a simple file (`CONTENT_SEEDS.md`) where you drop one-liners as they occur:

```markdown
## Content Seeds

- [ ] 2026-02-15: Dual-Opus evaluator idea -- using two independent AI evaluators and flagging disagreement. Nobody does this for AI-graded assessments. (format: technique post)
- [ ] 2026-02-10: Graph compliance score discovered: systems that "use" a knowledge graph vs. systems that genuinely reason with it produce wildly different quality. (format: deep-dive)
- [ ] 2026-02-08: Spent 3 hours debugging why semantic operations weren't matching -- turned out the labeling was correct but the ordering was wrong. (format: debugging narrative)
- [x] 2026-02-01: Published -> "Why Behavioral Signatures Beat Name-Based Detection"
```

**4. The "Shipped Email" for Solo Developers**

Adapted from Stripe's practice: after completing significant work, write a brief "shipped" note (3-5 sentences) that explains what you did and why it matters. This is your internal curation. Keep these in a single rolling file.

```markdown
### 2026-02-15: Reasoning Evaluation Framework v1

Shipped the 7-move reasoning decomposition for evaluating AI agent transcripts.
The key insight is that "did the workflow complete?" is the wrong question --
you need to score HOW the agent reasoned at each step. Broke reasoning into
HYPOTHESIS_FORMATION through SELF_CRITIQUE. Each move scored independently.
Dual-evaluator pattern catches unreliable AI grading.

Content potential: HIGH (nobody is doing this for AI agent evaluation)
```

### Why This Works

The content seed pattern works because it respects two realities:
1. **Insights decay** -- Your understanding is sharpest at the moment of discovery
2. **Writing is hard** -- Starting from a blank page is the enemy; starting from a seed is easy

By capturing seeds during work, you never face the blank page problem. You face the much easier problem of *expanding* something you already understand.

**Sources:** swyxio/learn-in-public gist, koolaidfactory.com, deepseeking.dev/learning-in-public

---

## 6. Debugging Sessions as Content

### Julia Evans: The Master of This Format

Julia Evans (jvns.ca, Wizard Zines) has built an entire media empire on turning debugging experiences and learning moments into accessible content. Her approach:

1. **Start with genuine confusion** -- "I didn't understand X, so I decided to figure it out"
2. **Show the investigation process** -- Not just the answer, but how she got there
3. **Use simple language for complex topics** -- No jargon-signaling; explain as if to a smart friend
4. **Visual aids** -- Her zines use hand-drawn-style illustrations that make concepts memorable
5. **Short, focused scope** -- Each piece covers ONE thing well, not everything about a topic

Her "Debugging Manifesto" principles map directly to a content strategy:
- **"Inspect, don't squash"** -- Don't just fix the bug; understand it deeply enough to explain it
- **"Being stuck is temporary"** -- The emotional journey IS the content
- **"Trust nobody and nothing"** -- Surprising root causes make the best stories

### The Narrative Debugging Blog Post Template

```markdown
# [Descriptive Title: "The Bug That Wasn't a Bug" or "Why My Tests Were Lying"]

## The Symptom (30 seconds to hook the reader)
"Last Tuesday, our graph builder started producing empty results for contracts
that had worked fine the day before."

## What I Expected
"The obvious cause was X, because [reasoning]."

## The Investigation (this is the meat -- show your work)
"First I checked Y. That looked fine. Then I checked Z..."
[Include actual commands, log output, queries]

## The Surprise (the turn -- this is what makes it a story)
"It turned out the problem wasn't in the graph builder at all. It was..."

## The Fix
[Brief -- the fix is usually anticlimactic]

## What I Learned (the real value for the reader)
"This taught me that [general principle]. If you're debugging a similar
issue, check [specific thing] first."
```

### Why Debugging Posts Work

1. **Universal experience** -- Every developer debugs; they empathize immediately
2. **Built-in narrative arc** -- Problem -> investigation -> surprise -> resolution
3. **High practical value** -- Someone googling the same error finds your post
4. **SEO-friendly** -- Error messages and tool names are natural keywords
5. **Low effort to write** -- You already did the work; you just need to narrate it

**The key is to write notes DURING the debugging session**, not after. Even just "2pm: tried X, didn't work because Y" is enough to reconstruct the narrative later.

**Sources:** jvns.ca, wizardzines.com, blog.kdgregory.com "A Self-Made Bug"

---

## 7. Code Review Insights as Content

### Patterns From Reviews

Code reviews are an underexploited content source. Three content types emerge naturally:

**Type 1: "Patterns I Keep Seeing" Posts**

After reviewing enough code, you notice recurring issues. These become excellent posts:
- "5 Solidity Patterns That Look Safe But Aren't"
- "The Authorization Bug I Find in Every Third Audit"
- "Why Everyone Gets [Specific Pattern] Wrong"

**Type 2: "Here's How I Review X" Posts**

Matthias Endler (endler.dev) wrote "How To Review Code" after 20+ years of reviewing. The key insight: "I like to look at the lines that *weren't* changed. They often tell the true story." Documenting your review methodology is content.

**Type 3: "Things I Wish My Reviewees Knew" Posts**

From the Microsoft study on code review effectiveness (1.5M comments analyzed):
- Experienced reviewers with prior codebase knowledge provide the most valuable feedback
- Smaller changes get better feedback
- The gap between "rubber stamp" reviews and "human linter" reviews vs. strategic reviews is the content

### Practical Extraction

Keep a rolling note of interesting patterns noticed during reviews:

```markdown
## Review Insights Log

### 2026-02-18 - Contract X review
- Found: state write after external call (classic reentrancy)
- **Interesting because:** The developer had a `nonReentrant` guard on the wrong function
- Content potential: "The Guard That Guards Nothing" post

### 2026-02-15 - Pattern Y review
- Found: access control check uses msg.sender but should use tx.origin... wait, no, the other way
- **Interesting because:** The mental model confusion between msg.sender and tx.origin
- Content potential: Part of a "Common Solidity Mental Model Errors" collection
```

**Sources:** endler.dev, growthalgorithm.dev, pmatteo.com, Microsoft code review study

---

## 8. Lightweight Metadata for Content-Ready Documents

### The Minimal Viable Frontmatter

After reviewing multiple approaches (Hugo, Jekyll, Obsidian, Steakhouse's "Front-Matter Standard" for AI crawlers), here is the minimal metadata that makes documents content-mineable:

```yaml
---
# Required
title: "Document Title"
date: 2026-02-20
type: decision | experiment | research | debug-log | review-insight

# Content extraction
content:
  readiness: none | seed | draft | ready | published
  key_insight: "One sentence. If you can't write this, it's not ready."

# Optional but high-value
content_extended:
  audience: [target-audience-tags]
  format_hint: tutorial | deep-dive | comparison | narrative | til | list
  hook: "Opening line or question"
  effort_to_publish: low | medium | high
  related: [paths-to-related-documents]
tags: [topic-tags]
---
```

### The "Key Insight" Inverted Pyramid

The most important metadata field is `key_insight`. It serves three purposes:

1. **Content filter** -- Documents without a clear key insight aren't worth extracting
2. **Tweet/social seed** -- The key insight IS the social media post
3. **Blog post thesis** -- Every good post has one core idea; this is it

**Pattern:** Write the key insight as if answering: "If someone reads nothing else, what should they know?"

### Section Markers for Partial Extraction

Within longer documents, use standardized section markers to flag extractable content:

```markdown
<!-- KEY_INSIGHT: The most dangerous failure is a workflow that "works" but reasons badly. -->

<!-- QUOTABLE: "Names lie. Behavior does not." -->

<!-- EXAMPLE_START: reentrancy-detection -->
[Code or detailed example that could stand alone]
<!-- EXAMPLE_END -->

<!-- SURPRISING_FINDING: Graph compliance scores clustered bimodally --
     either near 30 (checkbox) or near 80 (genuine use), with almost
     nothing in between. -->
```

These markers make it possible to extract content at the paragraph level, not just the document level.

### Content Readiness Score Algorithm

A simple scoring system for automated triage:

```
Score = sum of:
  +3 if key_insight is present and non-empty
  +2 if hook is present
  +2 if the document has concrete examples or data
  +1 if format_hint is specified
  +1 if audience is specified
  +1 if document length > 500 words
  -2 if type is "status" or "task-list"
  -1 if date is > 90 days old (stale context)

Readiness:
  >= 7: ready (can be published with light editing)
  4-6: draft (needs narrative framing)
  1-3: seed (has potential but needs significant work)
  <= 0: not content-ready
```

---

## Synthesis: A Practical System for a Solo Developer

### The Content Extraction Stack

Based on this research, here is a complete, lightweight system:

**Layer 1: Capture (during work)**
- Use `CONTENT_SEEDS.md` for one-liner insights as they occur
- Write ADRs for significant decisions (each one = future post)
- Drop `<!-- CONTENT_SEED: ... -->` markers in working documents
- Write 3-sentence "shipped" notes after completing significant work
- Note debugging steps in real-time, even briefly

**Layer 2: Metadata (on documents)**
- Add minimal YAML frontmatter with `content.readiness` and `content.key_insight`
- Use `<!-- KEY_INSIGHT -->` and `<!-- SURPRISING_FINDING -->` markers in longer docs
- Tag documents with `type` (decision, experiment, research, debug-log, review-insight)

**Layer 3: Extraction (when you need content)**
- Query documents by `content.readiness >= draft` and `type`
- Each document type maps to a blog post template (see table below)
- Apply the inverted pyramid: lead with insight, support with evidence, add context, then detail

**Layer 4: Publishing (the last mile)**
- Wrap extracted content in narrative framing (the "I was working on X when..." opener)
- Add the "so what" -- why should the reader care?
- Include concrete examples, numbers, or code snippets from the original work

### Document Type to Blog Post Mapping

| Internal Document | Blog Post Format | Template | Effort |
|---|---|---|---|
| ADR (decision) | "Why We Chose X Over Y" comparison | ADR sections -> post sections directly | Low |
| Experiment/improvement pass | "What Happened When We Tried X" | Hypothesis -> method -> results -> discussion | Medium |
| Research notes | "Everything I Learned About X" deep-dive | Organize findings, add narrative | High |
| Context file | "The State of X in 2026" overview | Extract key findings, add opinion | Medium |
| Debug log | "The Bug That [Surprising Thing]" narrative | Symptom -> investigation -> surprise -> lesson | Low |
| Review insight | "N Things I Learned Reviewing X" listicle | Collect patterns, add examples | Low |
| Gap analysis | "What's Missing in X" opinion piece | Gaps -> why they matter -> what to do | Medium |
| Shipped note | "TIL" or micro-post | Expand the 3-sentence note to 3 paragraphs | Very Low |

### The 15-Minute Content Extraction Workflow

When you need a blog post:

1. **Scan** (2 min): Review `CONTENT_SEEDS.md` and recent documents with `readiness: draft+`
2. **Select** (1 min): Pick the item with the best combination of clear insight + low effort
3. **Frame** (3 min): Write the hook and the "so what" (why should a reader care?)
4. **Expand** (7 min): Fill in the template for that document type. Most of the content already exists.
5. **Polish** (2 min): Add a title, check the opening line, ensure there's one concrete example.

### What Makes This Different From "Just Write Blog Posts"

The critical difference is **the capture happens during work, not as a separate activity.** You're not "writing blog posts" -- you're documenting your work with enough structure that blog posts can be *extracted* from it later. The marginal cost of adding a `key_insight` field or a `CONTENT_SEED` comment is near zero. But the payoff is that when you need content, you have a library of seeds, drafts, and ready-to-publish material.

This is the same insight that makes Stripe's writing culture work at scale: writing is not a separate activity from work; it IS work. The blog post is just the last 20% of formatting and framing.

---

## Appendix: Sources and Further Reading

### Primary Sources Consulted
- adr.github.io -- ADR templates and MADR specification
- ozimmer.ch -- MADR template explained (Olaf Zimmermann)
- zircote.com -- Structured MADR for AI (Robert Allen, 2026)
- m7y.me -- "ADRs: Actually Using Them" (2025)
- blog.trailofbits.com -- Engineering practice and research practice categories
- slab.com/blog/stripe-writing-culture -- Dave Nunez interview on Stripe's writing culture
- koolaidfactory.com -- "Writing In Public, Inside Your Company" (Stripe alumni perspective)
- newsletter.pragmaticengineer.com -- Inside Stripe's Engineering Culture parts 1 & 2
- jvns.ca -- Julia Evans, debugging manifesto and zine methodology
- wizardzines.com -- Pocket Guide to Debugging
- rekt.news -- Incident analysis writing style (multiple articles)
- swyxio -- "Learn In Public" essay and gist
- endler.dev -- "How To Review Code" (Matthias Endler, 2025)
- blog.trysteakhouse.com -- YAML frontmatter as semantic control layer (2026)
- dev.to/12ww1160 -- Write-once publishing pipeline
- joekarlsson.com -- Building a Claude Code Blog Skill (2025)
- aaronheld.com -- Streamlining Blog Writing with Claude Code

### Recommended Reading Order (for implementation)
1. swyx "Learn In Public" -- The philosophy
2. Kool-Aid Factory "Writing In Public" -- The organizational framework
3. MADR template primer (ozimmer.ch) -- The decision record format
4. Julia Evans debugging manifesto -- The narrative technique
5. Trail of Bits engineering blog -- The exemplar of research-to-content
