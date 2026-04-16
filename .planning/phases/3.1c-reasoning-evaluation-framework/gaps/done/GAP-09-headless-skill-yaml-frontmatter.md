# GAP-09: Headless Skill Injection — YAML Front-Matter Semantics

**Created by:** improve-phase
**Source:** P3-IMP-15
**Priority:** HIGH
**Status:** resolved
**depends_on:** []

## Question

Does `claude -p --append-system-prompt-file skill.md` process the YAML front-matter (allowed-tools, context: fork, disable-model-invocation) or treat it as raw text appended to the system prompt? If front-matter is not processed, what are the exact behavioral differences between headless and production skill execution?

## Context

CONTEXT.md Tier 1 execution model: `claude -p --append-system-prompt-file skill.md` for ~35 single-agent skills. Skill files have YAML front-matter parsed by Claude Code's skill system. GAP-07 resolved that slash commands don't work in -p mode and recommended --append-system-prompt-file, but did not verify whether front-matter is semantically processed. If front-matter is ignored, headless evaluation runs with different tool permissions and execution context than production. This affects Plan C's headless testing validity.

## Research Approach

- Check Claude Code documentation for --append-system-prompt-file behavior
- Search GitHub issues/discussions about skill injection in headless mode
- Look at Claude Code source code references for how system prompt files are processed
- If documentation is insufficient: design a 15-minute empirical test with a skill that has `allowed-tools` restrictions
- Authoritative answer: either "front-matter IS processed" (with evidence) or "front-matter is raw text" (with implications for Plan C)

## Findings

**Confidence: HIGH** — Multiple authoritative sources converge on the same answer.

### Answer: Front-matter is NOT processed by `--append-system-prompt-file`

The `--append-system-prompt-file` flag treats the file as **raw text appended to the system prompt**. It does NOT parse YAML front-matter. The YAML `---` block and its contents will be injected verbatim as literal text into the system prompt.

### Evidence

**1. Official CLI Reference (code.claude.com/docs/en/cli-reference)**

The flag is documented as:
> `--append-system-prompt-file`: Load additional system prompt text from a file and append to the default prompt (print mode only)

No mention of YAML parsing, frontmatter processing, or skill-system integration. The example uses `./extra-rules.txt` — a plain text file, not a SKILL.md.

**2. Skill System is a Separate Mechanism**

The Skill tool is a distinct Claude Code subsystem with its own discovery, invocation, and execution pipeline (official docs: code.claude.com/docs/en/skills):

- At startup, Claude Code scans `.claude/skills/` directories and reads frontmatter `name` + `description` for lightweight discovery
- When the `Skill` tool is invoked (via `/skill-name` or Claude's autonomous decision), the system:
  - Parses the YAML frontmatter
  - Applies `allowed-tools` as permission grants
  - Honors `context: fork` to spawn a subagent
  - Respects `disable-model-invocation` to control auto-loading
  - Strips frontmatter and returns only the markdown body as tool response
- This processing is done by the Skill tool implementation, NOT by generic file-loading code

**3. SDK Documentation Confirms Frontmatter Scope Limitation**

The official Agent SDK docs (platform.claude.com/docs/en/agent-sdk/skills) explicitly state:
> "The `allowed-tools` frontmatter field in SKILL.md is only supported when using Claude Code CLI directly. It does not apply when using Skills through the SDK."

This confirms `allowed-tools` is processed by a specific code path (the Skill tool in CLI), not by generic prompt injection. The `--append-system-prompt-file` flag uses a different code path entirely.

**4. Community Reverse-Engineering (mikhail.io/2025/10/claude-code-skills/)**

Mikhail Shilkov's analysis of the Skill tool internals shows:
- Frontmatter fields populate `<available_skills>` XML in the tool definition
- When invoked, the tool response includes the skill's base path and body (without frontmatter)
- Skills are "injected instructions" — but only via the Skill tool mechanism
- The `--append-system-prompt-file` path is completely separate

**5. Known Bugs in Frontmatter Processing Even Within Skill System**

- GitHub issue #14956 (open, Dec 2025): `allowed-tools` in frontmatter doesn't properly grant Bash command permissions even when invoked through the Skill tool
- GitHub issue #17283 (closed as duplicate, Jan 2026): `context: fork` and `agent:` frontmatter fields were ignored by the Skill tool
- GitHub issue #18394 (Jan 2026): `context: fork` fails inconsistently

These bugs exist within the Skill tool pipeline itself. The `--append-system-prompt-file` path doesn't even attempt to process these fields.

### Exact Behavioral Differences: Headless vs Production

| Frontmatter Field | Production (Skill Tool) | Headless (`--append-system-prompt-file`) |
|---|---|---|
| `name` | Used for `/slash-command` routing | Injected as raw YAML text (ignored) |
| `description` | Loaded into `<available_skills>` for discovery | Injected as raw YAML text (ignored) |
| `allowed-tools` | Grants tool permissions without user approval (buggy for Bash) | Injected as raw YAML text (no permission effect) |
| `context: fork` | Should spawn subagent (inconsistent, see #18394) | Injected as raw YAML text (no forking) |
| `agent` | Selects subagent type when `context: fork` | Injected as raw YAML text (ignored) |
| `model` | Sets model for skill execution | Injected as raw YAML text (ignored) |
| `disable-model-invocation` | Prevents Claude from auto-loading | Injected as raw YAML text (ignored) |
| `hooks` | Scoped lifecycle hooks | Injected as raw YAML text (ignored) |

**Impact on Tier 1 skills (~35 single-agent):** For skills that ONLY have `name` + `description` frontmatter and contain task instructions in the markdown body, the behavioral difference is minimal — Claude still receives the instructions. The raw YAML block at the top is harmless noise. However, skills relying on `allowed-tools`, `context: fork`, or `model` will behave differently.

## Recommendation

### Prescriptive Guidance

**Use `--allowedTools` CLI flag to replicate `allowed-tools` frontmatter behavior in headless mode.**

For each skill that has `allowed-tools` in its frontmatter, the headless invocation must explicitly pass those permissions via the CLI:

```bash
# Production (Skill tool processes frontmatter):
# /safe-reader (allowed-tools: Read, Grep, Glob in frontmatter)

# Headless equivalent:
claude -p \
  --append-system-prompt-file .claude/skills/safe-reader/SKILL.md \
  --allowedTools "Read" "Grep" "Glob" \
  "Your task here"
```

For skills with `context: fork`, do NOT attempt to replicate forking — the Tier 1 execution model already excludes multi-agent skills. If a skill requires `context: fork` in production, it belongs in Tier 2 (multi-agent), not Tier 1 (single-agent headless).

### Specific Actions

1. **Strip frontmatter before injection (recommended).** Create a preprocessing step that removes the `---` YAML block from SKILL.md before passing it to `--append-system-prompt-file`. This avoids injecting confusing raw YAML into the system prompt. A simple `sed` or Python script suffices:
   ```bash
   # Strip YAML frontmatter, pass only markdown body
   sed '1{/^---$/!q;};1,/^---$/d' skill.md > /tmp/skill-body.md
   claude -p --append-system-prompt-file /tmp/skill-body.md "task"
   ```

2. **Mirror `allowed-tools` via `--allowedTools` flag.** For each skill, extract `allowed-tools` from frontmatter and pass as `--allowedTools` on the CLI. The evaluation harness should automate this extraction.

3. **Mirror `model` via `--model` flag.** If a skill specifies `model: haiku` in frontmatter, pass `--model haiku` on the CLI.

4. **Document the delta explicitly.** For Plan C's evaluation validity claims, document which frontmatter fields are replicated and which are intentionally omitted in headless mode. Accept that headless mode is "close enough" for single-agent skills but NOT identical.

5. **Use `--tools` for restrictive skills.** If a skill uses `allowed-tools` to RESTRICT (not just allow) tool access (e.g., read-only mode), use the `--tools` flag to limit available tools:
   ```bash
   claude -p \
     --append-system-prompt-file skill-body.md \
     --tools "Read,Grep,Glob" \
     "task"
   ```

### What to Change in CONTEXT.md

Add to the Tier 1 execution model specification:

> **Frontmatter handling:** `--append-system-prompt-file` does NOT process YAML frontmatter. The evaluation harness MUST:
> (a) Strip `---` frontmatter blocks before injection
> (b) Mirror `allowed-tools` via `--allowedTools` CLI flag
> (c) Mirror `model` via `--model` CLI flag
> (d) Exclude skills requiring `context: fork` from Tier 1 (route to Tier 2)

### Plans Affected

- **Plan C (Scale Workflow Tests):** The 5+ Core skills tested with `run_mode=headless` must use the frontmatter-stripping + CLI-flag-mirroring approach. The evaluation harness needs a `parse_frontmatter()` utility.
- **Evaluation harness infrastructure:** Needs a preprocessing step between "select skill" and "invoke claude -p" that handles frontmatter extraction and CLI flag construction.

## Sources

### Primary (HIGH confidence)
- Official CLI reference: https://code.claude.com/docs/en/cli-reference — flag descriptions, system prompt flags comparison table
- Official Skills docs: https://code.claude.com/docs/en/skills — frontmatter reference, all fields documented
- Official Agent SDK docs: https://platform.claude.com/docs/en/agent-sdk/skills — explicit statement that `allowed-tools` is CLI-only

### Secondary (MEDIUM-HIGH confidence)
- Mikhail Shilkov reverse engineering: https://mikhail.io/2025/10/claude-code-skills/ — Skill tool internals
- GitHub issue #14956: https://github.com/anthropics/claude-code/issues/14956 — `allowed-tools` bug with Bash
- GitHub issue #17283: https://github.com/anthropics/claude-code/issues/17283 — `context: fork` not honored
- Reddit reverse engineering: https://www.reddit.com/r/ClaudeAI/comments/1o66m77/ — system prompt placement analysis

### Tertiary (MEDIUM confidence)
- ClaudeLog analysis: https://claudelog.com/faqs/what-is-system-prompt-file-flag-in-claude-code — `--system-prompt-file` behavior
