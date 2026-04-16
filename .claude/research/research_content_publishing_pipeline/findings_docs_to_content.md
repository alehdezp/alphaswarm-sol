# Documentation-to-Content Publishing Pipeline: Research Findings

**Date:** 2026-02-20
**Confidence:** High (patterns well-established across industry; specific implementation recommendations are medium confidence as they depend on your audience)

---

## Executive Summary

Project documentation can serve double duty as publishable content with three structural changes: (1) add content-aware frontmatter metadata, (2) adopt "inverted pyramid" section ordering within existing doc types, and (3) define explicit extraction templates that map doc sections to content formats. The research shows this is not about writing docs differently — it is about writing docs with a consistent structure that a human or LLM can reliably extract from.

---

## 1. Documentation Structures That Double as Content

### The Core Problem

Most internal docs bury the interesting parts. A CONTEXT.md that opens with "Phase Boundary" and "Hard Dependencies" contains genuine insights about architectural tradeoffs, but the reader must dig through governance scaffolding to find them. The publishable content is already there — it just needs surfacing.

### Pattern: ADR as Blog Post Skeleton

Architecture Decision Records (ADRs) are the closest existing doc format to a publishable article. The standard ADR structure maps directly:

| ADR Section | Blog Post Section |
|---|---|
| Title | Headline |
| Status | (omit or use as "update" hook) |
| Context | "The problem we faced" |
| Decision | "What we chose and why" |
| Consequences | "What happened / what we learned" |
| Alternatives Considered | "What we rejected" (readers love this) |

**Key insight from ADR research (m7y.me, Google Cloud Architecture Center, MADR templates):** The best ADRs already read like blog posts because they answer "why" rather than "what." The MADR (Markdown ADR) template explicitly includes "Considered Options" with pros/cons — this is the most engaging part for external readers.

**Recommendation:** Your existing `CONTEXT.md` files already contain decision sections. Add a `## The Interesting Part` or `## Key Insight` section at the top (2-3 sentences) that states the finding in plain language. This becomes the blog lede.

### Pattern: Experiment Result as Technical Post

Your IMPROVEMENT files (adversarial reviews with methodology/results/discussion) map directly to the most popular engineering blog format: "We tried X, here's what happened."

| Internal Doc Section | Blog Post Section |
|---|---|
| Hypothesis / Goal | "What we set out to prove" |
| Methodology | "How we tested it" (1-2 paragraphs, not the full protocol) |
| Results | "What we found" (lead with this) |
| Discussion / Analysis | "Why this matters" |
| Deferred / Next Steps | "What's next" (engagement hook) |

### Pattern: Research File as "Prior Art" Post

Your RESEARCH.md files (prior art analysis) map to "landscape review" posts, which perform well on LinkedIn because they save readers research time.

| Internal Doc Section | Blog Post Section |
|---|---|
| Sources surveyed | "We looked at N approaches" |
| Key findings per source | Comparison table or bullet list |
| Gaps identified | "What nobody is doing yet" |
| Our approach | "How we're different" (the hook) |

---

## 2. Research-to-Blog Conversion: The Inverted Pyramid

### The LSE/Dunleavy Method (11 Steps, Validated)

Patrick Dunleavy's widely-cited guide (LSE Impact of Social Sciences) provides the canonical academic-to-blog conversion. The core steps relevant to AI/security research:

1. **Cut 80% of length.** 8,000 words becomes 1,000. This is not summarization — it is extraction of the interesting kernel.
2. **Eliminate methodology and literature review.** Link to the full doc for details. Readers want findings, not process.
3. **Front-load findings.** Academic writing builds to conclusions. Blog writing starts with them. "We found that LLM evaluators agree with human raters only 60% of the time" — that is your opening line, not your conclusion.
4. **Craft a narrative headline.** Not "Phase 3.1c: Reasoning Evaluation Framework" but "Why Testing AI Reasoning Is Harder Than Testing Code (And What We Built Instead)."
5. **Write a trailer paragraph.** 3-4 lines explaining why the reader should care. This is the LinkedIn preview text.
6. **End decisively.** Restate the core insight. Do not trail off with "future work."

### The Sussex Method (Structural Inversion)

University of Sussex's research communication guide emphasizes a structural principle: **the blog is the inverse of the paper.** Papers build context then reveal findings. Blogs state findings then provide context for the curious.

Applied to your docs:

```
INTERNAL DOC:
  Phase Boundary → Dependencies → Decisions → Implementation → Results → Insights

PUBLISHABLE VERSION:
  Key Insight → Why It Matters → What We Found → How We Got There → [Link to full doc]
```

### The PAPAS Method

The Academic Entrepreneur framework uses: **Problem, Approach, Payoff, Audience, Story.**

- **Problem:** What pain does this solve? (For your work: "AI security tools find pattern matches but miss reasoning flaws")
- **Approach:** One-sentence method ("We built a multi-agent debate system where AI attackers and defenders argue about vulnerabilities")
- **Payoff:** The result ("Catches 3x more logic bugs than static analysis alone")
- **Audience:** Who cares? (Security auditors, AI engineers, protocol teams)
- **Story:** The narrative thread (the 3am incident, the false positive that cost money, the vulnerability that slipped through)

---

## 3. Building in Public: What Works

### Formats That Perform

Based on analysis of successful "build in public" practitioners (dev.to, LinkedIn, X/Twitter):

**High-performing content types for technical projects:**

1. **"What broke and how we fixed it"** — Failure stories outperform success stories 3-5x on engagement. Your IMPROVEMENT files (adversarial reviews finding flaws) are gold.

2. **Decision logs with tradeoffs** — "We chose X over Y because Z" posts. Your CONTEXT.md decision sections map directly. LinkedIn audiences engage heavily with "here's a hard tradeoff we navigated."

3. **Metric reveals** — "Our detection rate went from X to Y." Concrete numbers anchor abstract work. Your calibration-results.md and detection-baseline.md are ready-made posts.

4. **Contrarian takes backed by evidence** — "Everyone does X but we found Y works better." Your PHILOSOPHY.md files (e.g., "Names lie. Behavior does not.") contain strong contrarian positions.

5. **"N things I learned building X"** — Listicles from accumulated learnings. Your IMPROVEMENT-DIGEST.md is literally this format.

**Content that underperforms:**
- Pure announcements without substance ("We released v2!")
- Process descriptions without outcomes ("Our sprint process")
- Jargon-heavy posts without a "so what"

### Cadence and Platform Fit

| Platform | Best Format | Length | From Your Docs |
|---|---|---|---|
| LinkedIn | Insight + evidence + takeaway | 150-300 words | CONTEXT.md decisions, single IMPROVEMENT finding |
| Blog (Medium/personal) | Technical deep dive | 1,000-2,500 words | Full RESEARCH.md or IMPROVEMENT file |
| X/Twitter thread | Numbered learnings | 5-15 tweets | IMPROVEMENT-DIGEST bullet points |
| Dev.to | Tutorial + narrative | 1,500-3,000 words | CONTEXT.md + code examples |

### The "Seam" Pattern

The most effective build-in-public practitioners leave **seams** — deliberate hooks in documentation that invite engagement:

- **Open questions:** "We haven't solved X yet" (invites comments)
- **Provisional decisions:** "We chose X but are watching Y" (shows intellectual honesty)
- **Explicit unknowns:** "Our confidence in this is medium because..." (builds trust)

Your CONTEXT.md files already do this with "Deferred" items and uncertainty qualifiers. These translate directly to "What we're still figuring out" sections in posts.

---

## 4. Content Templates for Technical Projects

### Template 1: "What We Built and Why"

```markdown
---
content_type: build_narrative
source_docs: [CONTEXT.md, PHILOSOPHY.md]
target_platforms: [blog, linkedin]
---

# [Descriptive Title: Action + Outcome]

## The Problem (2-3 paragraphs)
[From CONTEXT.md: Phase Boundary, why this exists]
[Concrete example of the problem affecting real people]

## What We Built (3-5 paragraphs)
[From CONTEXT.md: Implementation Decisions]
[Architecture diagram or key visual]
[One code example or concrete illustration]

## Key Design Decisions (2-3 subsections)
[From CONTEXT.md: each major decision with its rationale]
[What we considered and rejected — readers love "the road not taken"]

## What We Learned (2-3 paragraphs)
[From IMPROVEMENT files: surprising findings]
[Metrics if available]

## What's Next
[From CONTEXT.md: Deferred items, open questions]
```

### Template 2: "What We Tried and Failed"

```markdown
---
content_type: failure_narrative
source_docs: [IMPROVEMENT-*.md]
target_platforms: [blog, linkedin, twitter_thread]
---

# [We Thought X Would Work. It Didn't. Here's Why.]

## The Hypothesis (1-2 paragraphs)
[From IMPROVEMENT: what we expected]

## What Actually Happened (2-3 paragraphs)
[From IMPROVEMENT: results that contradicted expectations]
[Specific data points or examples]

## Why It Failed (2-3 paragraphs)
[From IMPROVEMENT: root cause analysis]
[The non-obvious insight]

## What We Did Instead (2-3 paragraphs)
[The pivot, the alternative, the new approach]

## The Takeaway (1 paragraph)
[One transferable lesson the reader can apply]
```

### Template 3: "Lessons Learned" (Listicle)

```markdown
---
content_type: lessons_learned
source_docs: [IMPROVEMENT-DIGEST.md, multiple IMPROVEMENT files]
target_platforms: [blog, linkedin, twitter_thread]
---

# N Things We Learned Building [System] Over [Time Period]

## [Lesson 1: Contrarian or surprising insight]
[2-3 paragraphs with evidence]

## [Lesson 2: ...]
...

## The Meta-Lesson
[What ties these together — the overarching principle]
```

### Template 4: "Technical Deep Dive"

```markdown
---
content_type: deep_dive
source_docs: [architecture docs, RESEARCH.md, code]
target_platforms: [blog, dev_to]
---

# How [System] Works: A Deep Dive into [Specific Mechanism]

## Why This Matters (1 paragraph)
[The "so what" — why should a reader spend 10 minutes on this]

## The 30-Second Version (1 paragraph)
[Complete summary for skimmers]

## The Architecture (3-5 paragraphs + diagram)
[How the pieces fit together]

## The Interesting Part (3-5 paragraphs)
[The non-obvious design choice, the clever trick, the hard problem solved]
[Code snippets where they illuminate]

## Performance / Results (1-2 paragraphs)
[Concrete numbers]

## Tradeoffs We Made (2-3 paragraphs)
[What we sacrificed for what gain]
```

### Template 5: "Research Findings / Landscape Review"

```markdown
---
content_type: research_findings
source_docs: [RESEARCH.md]
target_platforms: [blog, linkedin]
---

# We Analyzed N Approaches to [Problem]. Here's What We Found.

## The Question (1 paragraph)
[What we needed to decide or understand]

## What's Out There (comparison table + 1 paragraph per approach)
[From RESEARCH.md: prior art, condensed]

## The Gaps (2-3 paragraphs)
[What nobody is doing — this is the hook]

## Our Approach (2-3 paragraphs)
[How we're addressing the gaps]

## Open Questions
[What we still don't know — engagement hook]
```

---

## 5. Structured Content Metadata (Frontmatter)

### Recommended Frontmatter Schema

Every documentation file that could produce content should include a `content` block in its frontmatter (or a parallel metadata section). This enables automated extraction.

```yaml
---
# Standard doc metadata
title: "Phase 3.1c: Reasoning Evaluation Framework"
date: 2026-02-20
status: active

# Content extraction metadata
content:
  # Is this doc publishable? Not every doc is.
  publishable: true

  # What content types can be extracted from this doc?
  # Maps to extraction templates above.
  extractable_as:
    - type: build_narrative
      readiness: 0.7        # 0-1, how close to publishable
      headline_candidates:
        - "Why Testing AI Reasoning Is Harder Than Testing Code"
        - "We Built an AI That Grades Other AIs. Here's What It Found."
      key_insight: >
        The most dangerous failure in AI testing is a workflow that
        'works' but reasons badly. We built a system that catches this.
      target_audience: [ai_engineers, security_researchers]
      target_platforms: [blog, linkedin]

    - type: failure_narrative
      readiness: 0.5
      headline_candidates:
        - "Our AI Evaluator Scored Itself 100%. That Was the Bug."
      key_insight: >
        Fabricated training data creates circular validation —
        the evaluator passes because it was trained on its own output.
      target_audience: [ai_engineers, ml_ops]

  # Tags for content categorization and SEO
  topics: [ai-testing, multi-agent-systems, security-evaluation]
  themes: [building-in-public, ai-reasoning, evaluation-methods]

  # Linking to source material
  depends_on: []
  cited_by: []

  # Content lifecycle
  last_content_review: 2026-02-20
  content_freshness: current  # current | aging | stale
---
```

### Minimal Viable Frontmatter

For docs where full metadata is overhead, use a minimal version:

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

### Key Fields Explained

| Field | Purpose | Why It Matters |
|---|---|---|
| `publishable` | Gate: should this doc ever become content? | Prevents extraction of internal-only docs |
| `extractable_as` | List of content types this doc can produce | One doc can yield multiple posts (LinkedIn + blog) |
| `readiness` | 0-1 score of how close to publishable | Enables "what can I publish this week?" queries |
| `headline_candidates` | Pre-written headline options | Headlines are the hardest part; capture them when inspiration strikes |
| `key_insight` | The one-sentence takeaway | This becomes the LinkedIn hook and blog lede |
| `target_audience` | Who would read the extracted content | Shapes tone and jargon level during extraction |
| `topics` / `themes` | Categorization | Enables content calendar and SEO planning |
| `content_freshness` | Is this still relevant? | Prevents publishing stale findings |

---

## 6. Implementation Recommendations for This Project

### Phase 1: Tag Existing Docs (Low Effort, High Signal)

Go through existing planning artifacts and add minimal frontmatter:
- CONTEXT.md files: Add `publishable`, `one_liner`, `topics`
- IMPROVEMENT files: Add `publishable`, `key_insight` (each improvement pass is a potential "what we learned" post)
- RESEARCH files: Add `publishable`, `one_liner`, `topics`

This takes 2-3 minutes per file and creates a queryable inventory of publishable content.

### Phase 2: Adopt the Inverted Pyramid in New Docs

When writing new CONTEXT.md, IMPROVEMENT, or RESEARCH files, add a `## Key Insight` section at the very top (after frontmatter) that states the finding in plain language. This costs nothing extra during writing and makes extraction trivial.

Example for an existing doc:

```markdown
---
title: "Phase 3.1c Context"
content:
  publishable: true
  key_insight: >
    We discovered that AI evaluation systems can achieve perfect scores
    by being tested on data they were designed to produce — a form of
    circular validation that mimics competence without demonstrating it.
  topics: [ai-evaluation, testing-philosophy]
---

## Key Insight

AI testing's hardest problem isn't catching failures — it's catching
success that's actually fabricated. We found our evaluator scored 100%
because it was tested on synthetic data crafted to match its own
output patterns. Real transcripts told a different story.

[Rest of existing doc structure unchanged]
```

### Phase 3: Extraction Pipeline

Build a script (or Claude Code skill) that:
1. Scans docs for `content.publishable: true`
2. Filters by `readiness >= 0.7`
3. For each extractable type, applies the corresponding template
4. Produces a draft in `drafts/` directory
5. Includes the `key_insight` as the lede and `headline_candidates` as options

This can be a Claude Code skill (`/vrs-content-extract`) that reads the frontmatter and applies the templates from Section 4.

### Phase 4: Content Calendar from Metadata

Query all docs for their `topics` and `themes` to build a content calendar:
- Group by topic to find series opportunities ("3-part series on AI evaluation")
- Filter by `content_freshness: current` to avoid stale posts
- Sort by `readiness` to find what's closest to publishable

---

## 7. Specific Mappings for This Project's Artifacts

### Your Existing Docs → Content

| Artifact | Content Type | Estimated Readiness | Potential Headline |
|---|---|---|---|
| PHILOSOPHY.md ("Names lie. Behavior does not.") | Contrarian take | 0.8 | "Why AI Security Tools Fail: They Read Names, Not Behavior" |
| CONTEXT.md (decision sections) | Decision narrative | 0.6 | "Building an AI Auditor: The 5 Hardest Design Decisions" |
| IMPROVEMENT-DIGEST.md | Lessons listicle | 0.7 | "N Things We Learned Building a Multi-Agent Security System" |
| IMPROVEMENT files (adversarial reviews) | Failure narrative | 0.7 | "Our AI Evaluator Scored Itself 100%. That Was the Bug." |
| RESEARCH.md (prior art) | Landscape review | 0.6 | "We Analyzed Every AI Security Tool. Here's What's Missing." |
| calibration-results.md | Metric reveal | 0.5 | "How Accurate Is an AI Evaluator? Our Calibration Results" |
| detection-baseline.md | Benchmark post | 0.5 | "Setting a Baseline: What Our Multi-Agent System Actually Detects" |
| TESTING-PHILOSOPHY.md | Deep dive | 0.7 | "The Most Dangerous Test Is One That Passes" |

### LinkedIn Post Extraction Pattern

For quick LinkedIn posts from any decision in CONTEXT.md:

```
[Hook: The counterintuitive finding, in one sentence]

[Context: 2-3 sentences on what we were building]

[The decision: What we chose and the key tradeoff]

[The evidence: One concrete data point or example]

[The takeaway: One transferable insight]

---
Building [project] in public. More at [link].
```

This maps directly to your CONTEXT.md "Implementation Decisions" sections. Each locked decision is one LinkedIn post.

---

## Sources

1. Dunleavy, P. "How to write a blogpost from your journal article in eleven easy steps." LSE Impact of Social Sciences, 2016. https://blogs.lse.ac.uk/impactofsocialsciences/2016/01/25/how-to-write-a-blogpost-from-your-journal-article/
2. University of Sussex. "How to turn your research paper into a blog." https://blogs.sussex.ac.uk/policy-engagement/resources-for-researchers/how-to-turn-your-research-paper-or-article-into-a-blog/
3. Radensky et al. "Let's Get to the Point: LLM-Supported Planning, Drafting, and Revising of Research-Paper Blog Posts." arXiv:2406.10370, 2024.
4. m7y.me. "Architecture Decision Records: Actually Using Them." 2025. https://m7y.me/post/2025-12-23-architecture-decision-records/
5. Google Cloud Architecture Center. "Architecture decision records overview." https://cloud.google.com/architecture/architecture-decision-records
6. MADR (Markdown Architectural Decision Records). https://adr.github.io/adr-templates/
7. SteakHouse Blog. "The Front-Matter Standard: Using YAML Metadata to Programmatically Control Crawler Behavior." 2026. https://blog.trysteakhouse.com/blog/front-matter-standard-using-yaml-metadata-programmatically-control-crawler-behavior
8. Hugo documentation. "Front Matter." https://gohugo.io/content-management/front-matter/
9. Front Matter CMS for VS Code. https://frontmatter.codes/docs
10. OSO Architecture Evolution blog post pattern. https://docs.opensource.observer/blog/oso-architecture-evolution
11. Stripe Engineering. "How we built it: Usage-based billing." 2025. https://stripe.com/blog/how-we-built-it-usage-based-billing
