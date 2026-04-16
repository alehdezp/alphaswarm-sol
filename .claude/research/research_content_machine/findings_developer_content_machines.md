# Developer Content Machines: How Prolific Developer-Writers Turn Daily Work Into Published Content

Research conducted: 2026-02-20
Sources: 30+ web searches across Exa, Brave, and direct page crawls

---

## Executive Summary

The most effective developer-writers do not "create content" as a separate activity. They build systems that make content a natural byproduct of their daily work. The core pattern across all domains (security, Rust/systems, web3, AI tooling) is:

**Work --> Capture friction/insight --> Let it marinate --> Publish the narrative of discovery, not the conclusion.**

The authenticity gap between great developer content and generic/AI-assisted content comes down to one thing: **the presence of a real thinking process, with real uncertainty, real mistakes, and real stakes.**

---

## 1. The "Learning in Public" Framework (swyx)

### Core Concept

Shawn "swyx" Wang coined and popularized "Learn in Public" as the fastest way to learn. The core thesis:

> "You already know that you will never be done learning. But most people 'learn in private,' and lurk. They consume content without creating any themselves. What you do here is to have **a habit of creating learning exhaust.**"
> -- swyx, https://www.swyx.io/learn-in-public/

### The System

- Write blogs, tutorials, cheatsheets
- Speak at meetups and conferences
- Ask and answer things on StackOverflow and Reddit (**avoid** walled gardens like Slack/Discord -- they are not public)
- Make YouTube videos or Twitch streams
- Start a newsletter
- **"Make the thing you wish you had found"** when you were learning

### Key Insight: "Luck Surface Area"

Learning in public increases your "Luck Surface Area" -- the probability that opportunities find you. By creating reusable, referenceable content, you build compounding value. Each piece of content is a node in a network that others can discover.

### How swyx Practices This

- Moved his personal knowledge base to Obsidian as a **public** second brain: https://publish.obsidian.md/swyx/
- GitHub repo: sw-yx/brain
- 622+ pieces across essays, snippets, tutorials, podcasts, talks, and notes
- Publishes at different maturity levels: some content is polished essays, some is raw notes

### Application to Security/Web3/Rust

The "learning exhaust" model maps directly to:
- Writing up each vulnerability you investigate (even dead ends)
- Documenting each Rust lifetime/borrow checker battle
- Sharing the reasoning process behind audit findings, not just the findings

**Source:** https://www.swyx.io/learn-in-public/, https://www.swyx.io/obsidian-brain

---

## 2. Digital Gardens and Zettelkasten for Developers

### The Evergreen Notes Pattern (Joel Quenneville, thoughtbot)

Joel Quenneville (co-host of The Bikeshed podcast, prolific conference speaker and blog author) described his system in detail:

**Core principles:**
1. Notes are **atomic** -- each note contains a single idea (title + 1-2 paragraphs + optional code sample)
2. The title is a **thesis statement** -- e.g., "streams and lazy lists are conceptually the same thing" or "prefer buttons over links for destructive actions"
3. Notes are written in **prose**, not bullet points (forces you to actually think)
4. Notes are **densely hyperlinked** to each other

**Directory structure:**
```
my_vault/
  atomic_notes/      # Permanent, finished ideas
  literature_notes/  # Stream-of-consciousness notes on things consumed
  artifacts/         # Creative works produced (talks, blog posts)
```

**How ideas emerge:** When he needs a topic, he browses atomic notes. A single note rarely becomes a full post -- instead, a **cluster of connected notes** suggests a topic worth exploring. The hyperlinks between notes reveal which ideas are "load-bearing" (many connections = worth writing about).

**The pipeline:** Daily work insight --> atomic note --> links accumulate --> cluster forms --> blog post/talk/podcast topic

**Source:** https://thoughtbot.com/blog/my-note-taking-system-gives-me-constant-content-ideas

### Digital Gardens vs. Blogs

A blog is chronological -- publish and move on. A digital garden is topological -- ideas grow, interconnect, and mature over time. Key properties:

- **Not about perfection.** Notes exist at different maturity levels (seedling, budding, evergreen)
- **No artificial chronology.** Knowledge does not grow linearly
- **Conversations with yourself.** As one observer noted: "Digital gardens provide a fascinating view of the author's thinking process. Raw. Emergent. Frequently explicitly using questions, claims, evidence, and counter-points."
- **Obsidian** is the dominant tool in this space. Most practitioners use Obsidian with either Obsidian Publish, a custom static site generator, or GitHub Pages

### Tool Landscape

| Tool | Strengths | Used By |
|------|-----------|---------|
| Obsidian | Graph view, local-first, plugins, backlinks | swyx, most digital gardeners |
| Logseq | Outliner-first, open source | Privacy-focused devs |
| Notion | Collaborative, databases | Teams, less for individual gardens |
| Foam (VS Code) | Developer-native, Git-backed | Devs who live in VS Code |
| Custom (MDX/Astro/Hugo) | Full control | fasterthanlime, many Rust devs |

**Source:** https://wiobyrne.com/how-i-built-my-digital-garden/, https://obsidian.rocks/creating-a-digital-garden-in-obsidian/, https://bytes.zone/posts/digital-gardening-in-obsidian/

---

## 3. Second Brain --> Content Pipeline (Tiago Forte's CODE Framework)

### The Framework

C.O.D.E. = **Capture, Organize, Distill, Express**

Combined with P.A.R.A. = **Projects, Areas, Resources, Archives** (the filing system).

The key shift: from being an **archivist** (hoarding information) to a **curator** (actively refining toward creative output).

### How It Maps to Developer Content

| Stage | General | Developer-Writer Adaptation |
|-------|---------|----------------------------|
| **Capture** | Save interesting things | Log friction, bugs, surprising behaviors, "TIL" moments, interesting code patterns |
| **Organize** | File by project/area | Tag by domain (security, Rust, tooling), link to related notes |
| **Distill** | Progressive summarization | Extract the core insight, the "aha" moment, the one thing that would help someone else |
| **Express** | Create and share | Blog post, tweet thread, conference talk, video |

### Progressive Summarization

The key technique: each time you revisit a note, you highlight the most important parts. Over time, notes self-organize by importance. The ones you keep returning to and highlighting are the ones worth publishing.

### Critical Observation

Owen Robert McGregor (who used CODE extensively then stopped) noted a key limitation: CODE is optimized for **creative output** but can become misaligned if your goal is **deep understanding**. For developer-writers, the best content comes from genuine understanding, not from optimizing a publishing pipeline.

**The danger: systemizing content creation can kill the very thing that makes it good -- genuine curiosity and accidental discovery.**

**Source:** https://fortelabs.com/blog/basboverview/, https://medium.com/practice-in-public/a-no-nonsense-guide-to-the-code-framework-a10d3ee48976

---

## 4. Developer-Writers in Cybersecurity

### samczsun -- The Gold Standard of Vulnerability Storytelling

samczsun is perhaps the most celebrated security researcher in web3/DeFi. His blog posts (https://samczsun.com/) are case studies in turning security work into compelling content.

**His process (from ConsenSys Diligence interview, 2020):**

- **Target finding is organic:** "If someone mentions a project to me directly or in a group chat, I'll keep it in mind. Occasionally I browse the Ethereum subreddit. And if a project announces 'we just launched!' -- I'm like, 'cool, let's see if you're completely broken!'"
- **Exploration is graph-like:** He described finding the 0x bug by starting at a Wrapped Ether contract on Etherscan and branching outward: "It's kinda like a search algorithm -- like how you can visualize it branching out." He visited the same contracts 2-3 times before finding the bug. "I guess n-th time's the charm."
- **Mostly manual:** "A lot of my process is manual code review. I don't really tend to reach for automated vulnerability detectors since I'll have to go through it manually anyways."
- **Writing is the aftermath of real stakes:** His blog posts read like thriller narratives because they ARE -- he is literally racing to save millions of dollars. "Two Rights Might Make A Wrong" tells the story of finding a vulnerability that put over 109k ETH (~$350M) at risk while "offhandedly browsing through the LobsterDAO group on Telegram."

**Content pattern:**
1. Start with the **moment of discovery** ("It was just after lunch when I got a push notification...")
2. Walk through the **reasoning process** step by step, including wrong turns
3. Show the **stakes** in concrete terms ($350M at risk)
4. End with the **resolution** and what it teaches

**Why it works:** The reader experiences the discovery alongside the author. Uncertainty is preserved. The narrative has genuine tension because real money was at risk.

**Source:** https://samczsun.com/, https://consensys.net/diligence/blog/2020/01/interview-with-samczsun/, https://immunefi.com/blog/whitehat-spotlight/the-u-up-files-with-samczsun/

### Trail of Bits -- Turning Audits Into Educational Content

Trail of Bits (https://blog.trailofbits.com/) has one of the strongest security blogs in existence. Their pattern:

- **Audit work feeds the blog directly.** After completing audits, researchers write up the most interesting findings as educational content. Their 2025 output: 375+ merged PRs to 90+ open source projects, each a potential blog post.
- **Vulnerability disclosure as content:** Their post "5 reasons to strive for better disclosure processes" showcases five real-world vulnerabilities they disclosed, using each as a case study for the broader point.
- **Tool releases as content:** Releasing Slither-MCP, go-panikint, and other tools generates natural content (announcement + technical deep dive + usage guide).
- **The content IS the work.** They do not create content separately from their engineering -- the blog posts are the documentation of the engineering.

### OpenZeppelin -- Incident Storytelling

OpenZeppelin's blog (https://blog.openzeppelin.com/) excels at:
- **Incident retrospectives as educational content.** Their "ERC-2771 Crisis Management" post recounts a week where a critical vulnerability affected thousands of contracts. The post reads like a war room diary.
- **Annual "Security Auditor's Rewind"** -- curated summaries of the year's most notable incidents, distilled into actionable patterns for other auditors.
- **Community continuity:** The Rewind series was started by one researcher and explicitly handed off to another team, maintaining the tradition.

### Zellic -- Research-First Content

Zellic (https://www.zellic.io/blog/) publishes deep technical research posts that are clearly byproducts of their audit and research work. Topics range from FHE cryptography to Groq's hardware architecture -- driven by whatever the team is investigating, not by a content calendar.

**The Security Content Pattern:**
```
Audit/Research Work --> Interesting Finding --> Generalize to Teachable Concept --> Publish with Real Code
```

---

## 5. Developer-Writers in Rust/Systems Programming

### fasterthanlime (Amos Wenger) -- The Master of Exploratory Long-Form

Amos Wenger runs fasterthanli.me, arguably the most beloved technical blog in the Rust ecosystem. Key insights from a 2025 interview (writethatblog.substack.com):

**On why he started:**
> "I genuinely cannot remember why I started, because I've been blogging for about 15 years! That's just what the internet was like back then? It wasn't weird for people to have their own website."

**On his trademark deep-dives:**
> "In 2019 I started a Patreon to motivate me to take writing more seriously -- I'm reluctant to call it 'blogging' at this point because some of my longer articles are almost mini-books! Some can take a solid hour to go through. At the time, I was sick of so many articles glossing over particulars: I made it my trademark to go deep into little details, and not to be afraid to ask questions."

**On his proudest work (the "executable packer" series):**
> "I started out just trying to find out what was in ELF files, then how they're loaded, then went 'well, it can't be THAT hard to have code compressed on-disk and decompress it on launch,' but then I added a bunch of constraints... In the middle there, I had little confidence it was all going to work... That explains why the series is kinda long and there's a lot of 'fixing my earlier mistakes/assumptions' in it. Still, I taught myself something from scratch for it and a lot of people were along for the ride."

**On authenticity:**
> "When people tell you to write about things you're passionate about, it's not JUST wishful thinking... It's also that if you build something you really hate (but you think is going to be successful), and they DO come, then you're stuck maintaining that."

**On perfectionism:**
> "Blog articles are not like software projects. I'm not going to have to keep maintaining articles forever -- I spend a finite amount of time on them, do my best, and if I feel like revisiting the topic later, I can do that! Obsessing forever has an opportunity cost."

**His infrastructure:** He built his own CMS in Rust (now open-sourced) and has been writing about building the CMS since 2020. The meta-content (writing about the tools you build to write) is itself content.

**Revenue model:** ~282 sponsors on Patreon/GitHub Sponsors, plus a podcast "Self-Directed Research" with James Munns.

**Source:** https://writethatblog.substack.com/p/fasterthanlime-on-technical-blogging, https://fasterthanli.me/

### Without Boats (Rust Language Team)

Boats writes at https://without.boats/blog -- focused on Rust language design (Pin, async, generators). The writing is deeply technical and philosophical, aimed at the Rust community's "language design" audience. Content comes directly from his work on the Rust language itself -- each blog post is essentially a design note or RFC explanation written for a broader audience.

### Mara Bos (Rust Library Team Lead)

Author of "Rust Atomics and Locks" (O'Reilly, 2023). Her content pipeline is: **daily work leading the Rust library team --> deep understanding of concurrency primitives --> book that teaches what she learned.** Her blog (marabos.nl) hosts chapters of the book itself. The book was praised by Aria Beingessner (author of The Rustonomicon): "This book is incredible! It's exactly what I wanted The Rustonomicon to cover on concurrency, but far better than I dared dream."

**The pattern for systems writers:**
```
Deep daily work on a specific system --> Hit the limits of existing docs --> Write the docs you wish existed --> Book or blog series
```

---

## 6. Anti-Patterns: What Kills Authenticity

### The "Dearth of the Author" (Academic Research)

Max Kreminski (Santa Clara University) identified a condition he calls "the dearth of the author":

> "A condition that arises when AI-based creativity support tools for writing allow users to produce large amounts of text without making a commensurate number of creative decisions, resulting in output that is sparse in expressive intent."

**Key insight:** The problem is not that AI writes badly. The problem is that AI allows you to produce text without having actually thought about anything. The text is "sparse in expressive intent" -- it says words but no one meant them.

### Specific Anti-Pattern Signals

Based on research across multiple sources on AI-generated content detection:

1. **No friction, no stakes.** The writing describes no struggle, no uncertainty, no wrong turns. Everything proceeds smoothly from premise to conclusion. Real technical work is messy.

2. **Conclusion-first writing.** AI content tends to state the answer and then provide supporting evidence. Authentic developer content follows the *journey* -- including dead ends, surprises, and "wait, that can't be right" moments.

3. **Perfect grammar, zero personality.** Grammatically flawless prose with no distinctive voice, no humor, no tangents, no opinions. As one writer noted: "It reads like content written by a committee that's never experienced failure, triumph, or the messy reality of building something meaningful."

4. **Generic examples.** AI uses toy examples (Todo apps, counter apps). Real developer content uses the actual code from the actual project, warts and all.

5. **No temporal anchoring.** AI content exists outside time. Real developer content says things like "It was just after lunch when I got a push notification" or "I was offhandedly browsing through the LobsterDAO group on Telegram." Real events happen at real times.

6. **Uniform hedging.** AI content hedges everything equally. Real experts are confident about what they know and explicitly uncertain about what they do not.

7. **Missing the "why do I care" signal.** AI can explain what something is and how it works, but struggles to convey why the author personally cares about it. samczsun cares because real money is at stake. fasterthanlime cares because they find it genuinely fascinating. Without Boats cares because the design decision affects every Rust user. The "why I care" signal is the strongest authenticity marker.

### The Repurposing Trap

Automated content repurposing (one blog post --> 15 LinkedIn posts + 10 tweets + 3 threads) is now a cottage industry. Every AI tool promises to turn one piece into many. **This is the content equivalent of currency debasement.** The original insight gets diluted across formats until there is nothing left. The best developer-writers do not repurpose -- they create native content for each context, or they pick one primary format and invest deeply.

---

## 7. The Friction Log as Content Source

### The Pattern

Multiple developers independently converge on the same technique: **keep a running log of friction, confusion, and surprise.**

Mike Bifulco (Stripe, then Craftwork/YC) described Stripe's internal friction log system: "Every new Stripe is given training on how to give feedback on products, and the process for creating friction logs." The friction log captures:
- **Context:** Who you are and what you were trying to do
- **Steps:** What you actually did, in order
- **Emotional state:** Where you got confused, frustrated, delighted

Separately, a dev.to author recommended: "Throughout the week, capture tiny frustrations: messy abstractions, flaky pipelines, gaps in documentation, process failures, production incidents, decisions that didn't age well."

**The friction log --> content pipeline:**
```
Day 1-5: Log friction points as they happen (one sentence each)
Day 5-10: Review logs, notice patterns/clusters
Day 10-20: The cluster that keeps growing is your next blog post
Day 20-30: Write the post, using the friction log as your outline
```

This is fundamentally different from "decide to write a blog post, then figure out what to write about." The content finds you.

**Source:** https://mikebifulco.com/posts/how-stripe-uses-friction-logs, https://dev.to/humayunkabir/a-practical-blogging-strategy-for-software-engineers-who-want-to-be-seen-1pim

---

## 8. Emerging Patterns: The Meta-System

### Pattern 1: The Discovery Narrative

The most effective format across all domains is the **discovery narrative** -- writing that preserves the order of discovery, not the logical order of explanation.

| Author | Domain | Example |
|--------|--------|---------|
| samczsun | Web3 security | "Uncovering a Four Year Old Bug" -- starts with a push notification, branches outward |
| fasterthanlime | Rust/systems | "Making our own executable packer" -- starts with curiosity about ELF files, escalates |
| Trail of Bits | Security | "5 reasons for better disclosure" -- real bugs discovered, real frustrations encountered |
| OpenZeppelin | Web3 security | "ERC-2771 Crisis Management" -- recounts a week-long emergency response |

**Why this works:** The reader's brain mirrors the author's discovery process. They experience the same "wait, what?" moments. This creates genuine engagement that no amount of SEO optimization can replicate.

### Pattern 2: The Work IS the Content (Not Adjacent To It)

The best developer-writers do not have a "content creation" step. The content is:
- The audit report, rewritten for a general audience (Trail of Bits, OpenZeppelin)
- The language design note, expanded for non-experts (Without Boats)
- The investigation process, narrated in real-time (samczsun)
- The learning journey, documented as it happens (fasterthanlime)
- The daily friction, logged and clustered (Stripe friction logs, Zettelkasten)

There is no separate "content day." The work and the content are the same activity, viewed from different angles.

### Pattern 3: One Primary Medium, Deep Investment

| Writer | Primary Medium | Why |
|--------|---------------|-----|
| samczsun | Long-form blog | Stories need space to unfold |
| fasterthanlime | Long-form blog + video | Explorations need room to breathe |
| swyx | Essays + newsletter | Ideas need iteration |
| Without Boats | Blog posts | Design thinking needs precision |
| Mara Bos | Book | Concurrency needs systematic treatment |
| Trail of Bits | Blog | Research needs proper exposition |

None of them try to be everywhere. They pick a primary format that matches their thinking style and go deep. Cross-posting is incidental, not systematic.

### Pattern 4: Build Your Own Infrastructure

A surprising number of prolific developer-writers build their own publishing tools:
- fasterthanlime built a custom CMS in Rust (open-sourced 2025)
- swyx maintains a custom site with MDX
- samczsun has a custom blog
- Most digital garden practitioners use custom pipelines

**The act of building the tool teaches you about the medium,** which makes you better at using it. fasterthanlime has written at least 7 articles about building his own CMS -- the infrastructure IS content.

### Pattern 5: Sustainable Economics

| Model | Example | Viability |
|-------|---------|-----------|
| Sponsorship/Patreon | fasterthanlime (~282 sponsors) | Sustainable for prolific individuals |
| Employer-funded | Trail of Bits, OpenZeppelin, Zellic | Most common for security |
| Reputation-driven | samczsun (led to founding SEAL, role at Paradigm) | High upside, indirect |
| Book deal | Mara Bos (O'Reilly) | One-time, plus ongoing reputation |
| Course/workshop | swyx (various) | Scales but requires different skills |

The best content is almost never monetized directly. It is funded by the reputation it builds, which leads to better jobs, consulting, speaking fees, and advisory roles.

---

## 9. Synthesis: A Developer Content System That Actually Works

Based on all the research, here is the distilled system:

### Daily (5-10 minutes)
- **Capture friction:** One-sentence notes when you hit something confusing, surprising, or frustrating in your work
- **Capture insight:** When you figure something out, write down what you now know that you did not know this morning
- **Format:** Atomic notes with thesis-statement titles, stored in Obsidian or equivalent

### Weekly (30 minutes)
- **Review the week's notes.** Add links between related notes. Notice clusters forming.
- **Identify "load-bearing" notes** -- the ones that multiple other notes link to or reference.

### When a Cluster Reaches Critical Mass (irregular)
- **Write the discovery narrative.** Not "here is what I learned" but "here is how I learned it."
- **Preserve the journey.** Include wrong turns, surprises, moments of confusion.
- **Use your actual code, actual commands, actual error messages.** Not sanitized examples.
- **Anchor in time and place.** "Last Tuesday, while reviewing an audit for..." not "When reviewing audits, one might..."

### What NOT To Do
- Do NOT start with a content calendar and work backward to "what should I write about"
- Do NOT repurpose one post into 15 derivative posts across platforms
- Do NOT let AI write the first draft (use it for editing, fact-checking, or generating illustrations)
- Do NOT optimize for SEO at the expense of narrative
- Do NOT separate "content creation" from "real work"

---

## 10. Application to Security/Web3/Solidity Context

For someone building smart contract security tools (this project's domain):

**Natural content sources from daily work:**
1. Each vulnerability pattern investigated --> "How I found pattern X" (discovery narrative)
2. Each false positive analyzed --> "Why this looked like a bug but isn't" (defensive thinking)
3. Each tool integration battle --> "Making Slither and Claude Code talk to each other" (friction log)
4. Each agent debate result --> "When the attacker and defender disagree" (adversarial thinking)
5. Each graph-building insight --> "What the knowledge graph reveals that grep cannot" (methodology)

**Platforms that matter for this audience:**
- Personal blog (primary, long-form)
- Twitter/X (announcement + thread for key insights)
- GitHub (tools, open source, README as content)
- Ethereum security-focused communities (EthSecurity community, Secureum)

**Voice markers that signal authenticity in security writing:**
- Specific dollar amounts at risk
- Actual contract addresses or transaction hashes
- Exact tool versions and configuration
- Explicit statements of what you do NOT know
- Showing the graph/AST/IR that revealed the vulnerability
- "I was wrong about X, here is why"

---

## References

### Primary Sources Consulted
- swyx, "Learn In Public": https://www.swyx.io/learn-in-public/
- swyx, "Moving to Obsidian as a Public Second Brain": https://www.swyx.io/obsidian-brain
- Joel Quenneville, "My note-taking system gives me constant content ideas": https://thoughtbot.com/blog/my-note-taking-system-gives-me-constant-content-ideas
- Amos Wenger (fasterthanlime) interview: https://writethatblog.substack.com/p/fasterthanlime-on-technical-blogging
- fasterthanli.me blog: https://fasterthanli.me/
- samczsun blog: https://samczsun.com/
- samczsun interview (ConsenSys): https://consensys.net/diligence/blog/2020/01/interview-with-samczsun/
- samczsun interview (Immunefi): https://immunefi.com/blog/whitehat-spotlight/the-u-up-files-with-samczsun/
- Trail of Bits blog: https://blog.trailofbits.com/
- OpenZeppelin blog: https://blog.openzeppelin.com/
- Zellic blog: https://www.zellic.io/blog/
- Without Boats blog: https://without.boats/blog
- Mara Bos, "Rust Atomics and Locks": https://marabos.nl/atomics/
- Tiago Forte, "Building a Second Brain": https://fortelabs.com/blog/basboverview/
- Mike Bifulco, "How Stripe Uses Friction Logs": https://mikebifulco.com/posts/how-stripe-uses-friction-logs
- Max Kreminski, "The Dearth of the Author in AI-Supported Writing": https://mkremins.github.io/publications/Dearth_In2Writing2024.pdf
- Digital gardening in Obsidian: https://bytes.zone/posts/digital-gardening-in-obsidian/
- Ian O'Byrne, "Growing Ideas in Public": https://wiobyrne.com/how-i-built-my-digital-garden/
- Rizel Scarlett, "The Ultimate Guide to Writing Technical Blog Posts": https://blackgirlbytes.dev/the-ultimate-guide-to-writing-technical-blog-posts
- Joe Karlsson, "Building a Claude Code Blog Skill": https://www.joekarlsson.com/2025/10/building-a-claude-code-blog-skill-what-i-learned-systematizing-content-creation/
