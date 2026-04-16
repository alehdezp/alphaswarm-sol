# Enforcement & Isolation Layer Review

**Phase:** 3.1c.2 — Agent Evaluation Harness Hardening
**Reviewer:** Security-focused testing framework reviewer
**Date:** 2026-03-02
**Scope:** delegate_guard.py enforcement, env-var gating, isolation completeness
**Files Analyzed:**
- `tests/workflow_harness/hooks/delegate_guard.py` (127 lines)
- `tests/workflow_harness/hooks/delegate_guard_config.yaml`
- `.planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-01-PLAN.md`
- `.planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md`
- `.planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-RESEARCH.md`
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
- `.planning/testing/CONTEXT-OVERVIEW.md`

---

## A. Gap Analysis

### Gap 1: Isolation Completeness — Can Agents Tell They Are Being Tested?

**What the vision requires:** "Agents don't know they're being tested" (TESTING-PHILOSOPHY.md, Principle 1). The agent should experience the evaluation session as indistinguishable from a real user interaction.

**What 3.1c.2 delivers:** Environment variable gating (`ALPHASWARM_EVAL_MODE=1`) that switches delegate_guard.py to a restrictive config. Prompt-based instructions telling agents what tools they can/cannot use.

**What is missing:**

1. **The env var itself is a leakage signal.** Any agent can run `Bash(env)` or `Bash(printenv)` or `Bash(echo $ALPHASWARM_EVAL_MODE)` and discover it is in eval mode. The env var name is literally `ALPHASWARM_EVAL_MODE`. An agent that encounters blocked tool calls and then queries the environment will find direct evidence that it is being evaluated. The blocked_patterns list does not include `env`, `printenv`, `ALPHASWARM`, or `EVAL_MODE` as patterns.

2. **Exit code 2 is a distinguishable signal.** When a tool call is blocked, the agent receives a specific error. In a real production session, tool calls do not return exit code 2 rejections from PreToolUse hooks (unless the production config also blocks things). The experience of having `Read` blocked but `Bash(uv run alphaswarm ...)` allowed is unusual enough to reveal evaluation context.

3. **The restrictive tool set itself is a fingerprint.** A real user session has access to Read, Write, Grep, Glob, Edit, WebFetch, etc. An evaluation session that blocks Read (except contracts/) and Write creates a distinctly constrained experience. An agent model that has been trained on Claude Code interaction patterns may recognize this as atypical.

**Severity:** MEDIUM. LLMs do not currently actively probe for evaluation markers, but the principle is about framework correctness, not about current model capabilities. As models improve, this becomes a real concern.

**Recommendation:** Rename `ALPHASWARM_EVAL_MODE` to something opaque like `_GUARD_PROFILE=strict`. Add `ALPHASWARM_EVAL` and `EVAL_MODE` to blocked_patterns. This does not fully solve the problem (the tool restriction fingerprint remains), but it closes the most trivially exploitable leakage path.

---

### Gap 2: Pattern Completeness — Bypass Vectors

**What the vision requires:** Agents MUST use CLI tools only, cannot import Python modules directly, cannot read project context. Plan 12 Batch 1 proved prompt-based restrictions fail.

**What 3.1c.2 delivers:** `blocked_patterns` in `delegate_guard_config_eval.yaml`:
```yaml
blocked_patterns:
  - "python "
  - "python3 "
  - "import "
  - "from alphaswarm"
  - "cat contracts/"
  - ".planning/"
  - "CLAUDE.md"
  - "docs/"
```

**What is missing — concrete bypass vectors:**

1. **Base64 / obfuscation bypass.** An agent can run:
   ```bash
   echo "aW1wb3J0IG9zOyBwcmludChvcy5saXN0ZGlyKCcuJykp" | base64 -d | sh
   ```
   This decodes to `import os; print(os.listdir('.'))`. Neither `"python "` nor `"import "` appear in the Bash command string. The delegate_guard does substring matching on the JSON-serialized tool_input, and the base64-encoded command does not contain any blocked pattern.

   **Severity:** HIGH. This is a direct, trivial bypass.

2. **`perl`, `ruby`, `node` interpreters.** The blocked patterns only cover `python` and `python3`. An agent can run:
   ```bash
   perl -e 'use File::Find; find(sub{print "$_\n"}, ".")'
   ruby -e 'Dir.glob("**/*").each{|f| puts f}'
   node -e 'const fs=require("fs"); console.log(fs.readdirSync("."))'
   ```
   None of these match any blocked pattern.

   **Severity:** MEDIUM. Most Claude agents default to Python, but there is no technical barrier to using other interpreters.

3. **`uv run python` bypass.** The pattern `"python "` (with trailing space) blocks `python -c ...` but does NOT block:
   ```bash
   uv run python -c "import os"
   ```
   Wait — this DOES contain `"python "` as a substring. However, it also contains `"alphaswarm"` if the allowed_reads check fires... No, actually `"uv run python"` does not contain `"alphaswarm"`. Let me re-check. The allowed_reads in the eval config is `["contracts/", "alphaswarm"]`. The string `"uv run python -c 'import os'"` contains `"python "` (blocked) and does NOT contain `"alphaswarm"` or `"contracts/"` (no exception). So this specific vector IS blocked. Good.

   But: `uv run python3.12 -c "import os"` — does `"python3 "` match inside `"python3.12 -c ..."? Yes, `"python3 "` is a substring of `"python3.12 -c"` — wait, actually no. `"python3 "` (with trailing space) vs `"python3.12"` — there is no space after `python3` in `python3.12`. The substring `"python3 "` does NOT match `"python3.12"`. This is a bypass.

   **Severity:** HIGH. `uv run python3.12 -c "import os"` bypasses the pattern.

4. **`exec` / `eval` via shell.** An agent can use:
   ```bash
   eval "$(printf 'imp''ort os')"
   ```
   Shell string concatenation can split the `import` keyword across a boundary so `"import "` never appears as a contiguous substring.

   **Severity:** MEDIUM. Requires deliberate obfuscation, but models are capable of this.

5. **`cat` variations.** `"cat contracts/"` is blocked, but `less contracts/`, `head contracts/`, `tail contracts/`, `bat contracts/`, `more contracts/` are not. Similarly, `cat ./contracts/`, `cat contracts`, or `cat "contracts/Reentrancy.sol"` vs `cat contracts/Reentrancy.sol` — the pattern matching is substring-based, so `"cat contracts/"` does block `cat contracts/Reentrancy.sol`, but NOT `cat ./contracts/Reentrancy.sol` (the path is `./contracts/` not `contracts/`).

   **Severity:** MEDIUM. Several file-reading commands bypass the `cat contracts/` pattern.

6. **Indirect execution via `xargs`, `find -exec`, `awk`, `sed`.** An agent can run:
   ```bash
   find . -name "*.py" -exec head -5 {} \;
   awk '{print}' .planning/STATE.md
   ```
   None of these match blocked patterns.

   **Severity:** MEDIUM. These let agents read any file on disk.

7. **`subprocess` via `uv run alphaswarm` trick.** If the alphaswarm CLI itself has a way to execute arbitrary code (e.g., a plugin system, an eval-like feature, or just a carefully crafted query that triggers code execution), then `"alphaswarm"` in allowed_reads creates an escape hatch. The allowed_reads check means ANY command containing `"alphaswarm"` bypasses ALL blocking. So: `Bash(python -c "import alphaswarm")` — this contains both `"python "` (blocked) AND `"alphaswarm"` (allowed) — and the allowed check fires first, returning exit 0. This is a direct bypass.

   **Severity:** CRITICAL. `Bash(python -c "import alphaswarm; ...")` passes through because `"alphaswarm"` is in the allowed_reads list and the allowed check overrides the block. The intent is to whitelist `uv run alphaswarm` CLI commands, but the substring match on `"alphaswarm"` is too broad.

**Recommendation:** The current substring-matching approach has fundamental limitations. For the highest-severity items:

- **Vector 7 (CRITICAL):** Change the allowed_reads logic for Bash tools. Instead of checking if `"alphaswarm"` appears anywhere in the input, check for the specific prefix `"uv run alphaswarm"`. Or better: restructure the matching so that `allowed_reads` only applies to Read/Grep/Glob tools, not to Bash pattern exceptions. Create a separate `allowed_bash_prefixes` list.
- **Vector 1 (HIGH):** Add patterns for `base64`, `eval`, `exec` in blocked_patterns.
- **Vector 3 (HIGH):** Change `"python3 "` to `"python3"` (without trailing space) or add patterns for `"python3."` to catch versioned interpreters.
- **Vectors 2, 5, 6:** Add `"perl "`, `"ruby "`, `"node "`, `"less "`, `"head "`, `"tail "`, `"more "`, `"awk "`, `"sed "`, `"find "` to blocked_patterns. This is a growing blocklist problem, but the alternative (an allowlist of permitted Bash commands) is more robust.

---

### Gap 3: Env-Var Propagation Reliability

**What the vision requires:** The delegate_guard eval config MUST be active for every hook invocation in every teammate subprocess.

**What 3.1c.2 delivers:** RESEARCH.md flags env-var propagation as MEDIUM confidence (Open Question 1). Plan 01's canary test verifies that `_load_config()` reads env vars correctly in-process, NOT that env vars propagate across subprocess boundaries to teammate sessions.

**What is missing:**

1. **The canary test is insufficient.** Plan 01 Task 3 tests `delegate_guard.main()` by calling it directly in Python with `monkeypatch`. This verifies the code path works when env vars are set in the same process. It does NOT verify that:
   - Claude Code propagates `ALPHASWARM_EVAL_MODE=1` from the orchestrator session to teammate sessions
   - Teammate sessions' hook subprocesses inherit the env var
   - The `DELEGATE_GUARD_CONFIG` absolute path resolves correctly from a worktree's working directory

2. **Worktree working directory changes.** When `isolation: "worktree"` is used, the teammate's working directory changes to `.claude/worktrees/{name}/`. If `DELEGATE_GUARD_CONFIG` is set to an absolute path, this works. But if it is set to a relative path, config loading fails. The plan specifies absolute paths, but there is no validation that the runner always uses absolute paths.

3. **No integration-level canary.** The canary test proves the code is correct. It does not prove the deployment is correct. The RESEARCH.md explicitly says: "This is the only empirically uncertain piece." Yet the plan does not include an integration test that spawns an actual teammate and verifies the hook fires.

**Severity:** HIGH. If env-var propagation silently fails, the entire enforcement layer is inactive, and evaluation sessions run with the default config (which allows everything except `.sol` reads). All results from Plan 06 would be invalid, repeating the Plan 12 Batch 1 failure.

**Recommendation:** Plan 06 (retry) should include a mandatory preflight: before running the real calibration, spawn a single test teammate that attempts `Bash(python -c "import os")` and verify it gets blocked. If it succeeds, halt immediately. This is an integration-level canary that covers the full propagation chain.

---

### Gap 4: Hook vs Prompt Enforcement — Uninterceptable Tools

**What the vision requires:** Hook-level enforcement (D-1: "hook-level blocking is the enforcement primitive").

**What 3.1c.2 delivers:** PreToolUse hook that intercepts Bash, Read, Write, and Grep.

**What is missing:**

1. **WebFetch and WebSearch (MCP tools) are not intercepted.** Claude Code agents have access to web search and web fetch tools. An agent could use `WebFetch` to fetch documentation about the project from a public URL (e.g., the GitHub repo if it is public), bypassing file-read restrictions entirely. The delegate_guard only checks `blocked_tools` and `blocked_patterns` — WebFetch is not in `blocked_tools` in the eval config, and its inputs (URL + prompt) would not match file-path-based blocked_patterns.

2. **Glob tool is not blocked.** `Glob` is not in `blocked_tools`. An agent can run `Glob(pattern="**/*.md")` to enumerate all markdown files in the project, revealing the directory structure, file names, and project organization. This is a significant context leakage vector — knowing that `.planning/phases/3.1c.2-agent-evaluation-harness-hardening/` exists tells the agent it is being evaluated.

3. **Edit tool is not blocked.** `Edit` is not in `blocked_tools`. While `Write` is blocked, `Edit` provides similar file modification capabilities. An agent could use `Edit` to modify files.

4. **NotebookEdit is not blocked.** Similar to Edit.

5. **Grep with output_mode: "content" leaks file contents.** `Grep` is handled in delegate_guard for path-based exceptions (lines 101-106), but the implementation only checks `tool_input.get("path", "")`. An agent can run `Grep(pattern="...", path=".", output_mode="content")` and read file contents without using `Read`. The delegate_guard's Grep handling only checks the path parameter, not whether the Grep is searching through project files. A Grep for `pattern="EVAL_MODE"` across the entire repo would reveal eval infrastructure.

   Wait — looking more carefully at the code: the blocked_tools check at line 94 blocks the tool entirely if it is in `blocked_tools`, then checks for allowed_reads exceptions. For Grep, the tool is not in `blocked_tools` in the eval config at all. It only appears in the code path for the dev config. So Grep is completely unblocked in the eval config.

**Severity:** HIGH for Glob and Grep (direct leakage vectors that are trivially exploitable). MEDIUM for WebFetch (requires public repo). LOW for Edit/NotebookEdit (agents typically do not use these for information gathering).

**Recommendation:**
- Add `Glob`, `Edit`, `NotebookEdit` to `blocked_tools` in the eval config.
- Add `Grep` to `blocked_tools` with `allowed_reads: ["contracts/"]` exception (same as Read).
- For WebFetch/WebSearch: add to `blocked_tools` or accept the risk if the repo is private.

---

### Gap 5: Worktree Isolation — Shared `.git/` Leakage

**What the vision requires:** Agents MUST have zero context about the project, testing framework, or expected results (MEMORY.md: "ALWAYS use `isolation: worktree`").

**What 3.1c.2 delivers:** `isolation: "worktree"` for teammate spawning.

**What is missing:**

1. **`.git/` is shared across worktrees.** Git worktrees share the same `.git/` directory (technically, the worktree has a `.git` file that points to the main repo's `.git/worktrees/` directory). An agent can run:
   ```bash
   git log --oneline -20
   ```
   This reveals commit messages like `docs(3.1c.2): implement improvements`, `docs(phase-3.1c.1): complete phase execution`, which directly expose that this is a testing framework project, that phase 3.1c.2 is about agent evaluation harness hardening, etc.

2. **`.git/config` contains remote URLs.** Running `git remote -v` or `cat .git/config` reveals the repository URL, which exposes the project name and purpose.

3. **`.git/hooks/` may contain testing hooks.** While the delegate_guard is registered via Claude Code's settings.json (not .git/hooks/), other hooks in `.git/hooks/` could reveal testing infrastructure.

4. **Branch names leak context.** `git branch` shows branch names that may contain testing-related keywords.

5. **Commit history contains full context.** `git show HEAD:CLAUDE.md` would bypass Read blocking entirely by reading file contents from git history.

**Severity:** HIGH. `git show HEAD:CLAUDE.md` is a complete bypass of the file-read restriction. The agent can read any file's content through git object storage. `git log` is a softer but significant leakage vector.

**Recommendation:**
- Add `"git "` to blocked_patterns (with a note that this prevents all git commands).
- Alternatively, add specific dangerous patterns: `"git log"`, `"git show"`, `"git diff"`, `"git remote"`, `"git config"`, `"git cat-file"`. This is a growing blocklist.
- The most robust approach: instead of worktrees, use a completely separate directory with only the contract files copied in. This is more complex but eliminates the `.git/` leakage entirely.

---

## B. Creative Improvements

### Improvement 1: Allowlist-Based Bash Enforcement (Invert the Model)

**What it does:** Instead of maintaining a growing blocklist of dangerous patterns, switch to an allowlist model for Bash commands in evaluation sessions. Only commands matching approved prefixes are allowed; everything else is blocked by default.

```yaml
# Proposed eval config structure
bash_mode: allowlist  # NEW: "blocklist" (current) or "allowlist"
allowed_bash_prefixes:
  - "uv run alphaswarm "
  - "ls "
  - "pwd"
  - "echo "
  - "mkdir -p .vrs/"
allowed_bash_patterns:
  - "alphaswarm build-kg"
  - "alphaswarm query"
```

In `delegate_guard.py`, when `bash_mode == "allowlist"`, the logic inverts: a Bash command is blocked unless it matches an allowed prefix/pattern.

**How it integrates:** Modifies Plan 01's `delegate_guard_config_eval.yaml` and adds ~15 lines to `delegate_guard.py`'s `main()` function. The existing blocklist mode remains for the dev config; only eval sessions use allowlist mode.

**Implementation complexity:** MODERATE. Requires refactoring the pattern matching logic in `main()` to support two modes. The main challenge is identifying the complete set of commands agents legitimately need.

**Which plan it modifies:** Plan 01 (config format + delegate_guard.py logic).

---

### Improvement 2: Git Isolation via Detached Workspace

**What it does:** Instead of using `isolation: "worktree"` (which shares `.git/`), create a completely isolated temporary directory containing ONLY the contract files and the alphaswarm CLI. No `.git/`, no project files, no CLAUDE.md.

Implementation: Before spawning teammates, the orchestrator:
1. Creates a temp directory: `/tmp/eval-{session_id}/`
2. Copies only the contract files: `cp contracts/Target.sol /tmp/eval-{session_id}/`
3. Ensures `uv run alphaswarm` is on the PATH (via env var or symlink)
4. Sets the teammate's working directory to `/tmp/eval-{session_id}/`

**How it integrates:** This replaces `isolation: "worktree"` with a custom isolation mechanism. The delegate_guard config path must be absolute. The evaluation_runner.py preflight (Stage 1) creates the workspace; cleanup happens in a finally block.

**Implementation complexity:** MODERATE. The main challenge is ensuring `uv run alphaswarm` works from an arbitrary directory (it needs the virtual environment on the path). May need to pass the full path to the alphaswarm binary.

**Which plan it modifies:** Plan 06 (retry) and potentially a new setup plan between 05 and 06.

---

### Improvement 3: Canary Trap for Leakage Detection

**What it does:** Plant a distinctive, unique marker in the evaluation environment that would only appear in agent output if the agent accessed restricted information. For example:

- Place a file `.planning/CANARY-{random_uuid}.txt` with a unique string like `CANARY-TOKEN-a8f3b2c1d4`
- After the evaluation session, search the agent's output/findings for this canary token
- If found, the agent accessed `.planning/` despite restrictions

This provides defense-in-depth: even if a bypass vector exists, the canary detects exploitation.

**How it integrates:** The orchestrator creates canary files before spawning teammates and checks for canary strings in the integrity validator (a new check 14). Works alongside the existing 13 checks.

**Implementation complexity:** TRIVIAL. A few lines in the evaluation_runner.py preflight and a string-search check in the validator.

**Which plan it modifies:** Plan 03 (ground truth generation, which already creates per-contract artifacts) or Plan 04 (integrity check pipeline, where the canary check would live).

---

### Improvement 4: Hook-Blocked Tool Call Logging

**What it does:** When delegate_guard.py blocks a tool call (exit code 2), log the blocked attempt to a JSONL file (e.g., `.vrs/observations/{session}/blocked_calls.jsonl`). This provides:
- A record of what agents tried to do that was blocked
- Evidence for post-session analysis of bypass attempts
- Input for the CLIAttemptState check (direct evidence of Python import attempts)

Currently, when a tool call is blocked, the only evidence is in the Claude Code session transcript (as a failed tool call). The delegate_guard itself leaves no trace.

**How it integrates:** Add 5-10 lines to `delegate_guard.py`'s blocking paths (before `sys.exit(2)`) that append a JSON record to a log file. The log file path comes from an env var (`DELEGATE_GUARD_LOG`). Plan 02's CLIAttemptState can read this log as a secondary signal.

**Implementation complexity:** TRIVIAL. A file append in the blocking code path.

**Which plan it modifies:** Plan 01 (delegate_guard.py modification).

---

### Improvement 5: Structural allowed_reads Separation

**What it does:** Split `allowed_reads` into two distinct mechanisms:
- `allowed_file_reads`: Applies to Read, Grep, Glob tools (path-based exceptions)
- `allowed_bash_commands`: Applies to Bash tool (command-prefix-based exceptions)

This fixes the CRITICAL bypass in Gap 2 Vector 7, where `"alphaswarm"` in `allowed_reads` means `Bash(python -c "import alphaswarm")` is allowed because the string `"alphaswarm"` appears in the input.

```yaml
# Proposed eval config
blocked_tools:
  - Read
  - Write
  - Glob
  - Edit
  - Grep

blocked_patterns:
  - "python "
  - "python3"
  - "import "
  - "git "

allowed_file_reads:
  - "contracts/"

allowed_bash_commands:
  - "uv run alphaswarm"
```

In `delegate_guard.py`, the Bash tool uses `allowed_bash_commands` for its exception check, while Read/Grep/Glob use `allowed_file_reads`. The two namespaces never cross.

**How it integrates:** Requires a config format change and a refactor of the pattern matching logic in `main()`. Backward compatible: if only `allowed_reads` is present, use the current behavior.

**Implementation complexity:** MODERATE. The config parsing and matching logic need updating, plus all tests need to cover the new format.

**Which plan it modifies:** Plan 01 (config format + delegate_guard.py logic). This should be considered a Plan 01 revision, not a new plan.

---

## C. Testing Framework Alignment Score

### Principle 1: "Agents don't know they're being tested"

**Score: 4/10**

**Justification:** The framework makes a genuine effort with worktree isolation and prompt-based restrictions, and the delegate_guard adds runtime enforcement. However:
- The `ALPHASWARM_EVAL_MODE` env var is discoverable (Gap 1.1)
- The tool restriction fingerprint is distinctive (Gap 1.3)
- Git history leaks full project context (Gap 5.1, 5.5)
- Glob is not blocked, allowing directory structure enumeration (Gap 4.2)
- The philosophy says agents should not be able to tell. Currently, an agent that probes even lightly can tell.

The Plan 01 canary test verifies that BLOCKING works, not that CONCEALMENT works. These are different goals. The framework is good at the former and weak at the latter.

### Principle 2: "Real execution only"

**Score: 8/10**

**Justification:** The framework strongly enforces real execution:
- Plan 06 is a live Agent Teams evaluation, not a simulation
- The delegate_guard operates at the actual tool-call level in real sessions
- JSONL transcript verification uses real session artifacts
- Ground truth is pre-built from real CLI runs

Deductions:
- The canary tests in Plan 01 are unit tests (monkeypatched), not integration tests against real Claude Code sessions. While appropriate for CI, they do not validate the real deployment path.
- The integration-level canary (spawning a real teammate) is not explicitly planned.

### Principle 3: "Safe sandboxing"

**Score: 6/10**

**Justification:** The sandboxing intent is clear and the delegate_guard provides a real enforcement primitive. However:
- The sandbox has bypass vectors (Gap 2: base64, alternative interpreters, git show)
- The blocklist model is inherently incomplete — every new bypass requires a new pattern
- Write is blocked but Edit is not (Gap 4.3)
- Glob is not blocked, undermining file-system isolation (Gap 4.2)
- The `allowed_reads: ["alphaswarm"]` escape hatch is too broad (Gap 2.7, CRITICAL)

The sandboxing is a meaningful step up from prompt-only restrictions, but it is not yet "safe" in the strong sense. An adversarially probing agent can escape it.

### Principle 4: "Smart observability"

**Score: 7/10**

**Justification:** The observability layer is well-designed:
- JSONL transcript parsing via TranscriptParser is mature
- SubagentStop hook provides reliable transcript paths
- CLIAttemptState enum provides structured post-session forensics
- agent_execution_validator has 13 checks covering the known failure modes
- The two-layer approach (prevention via delegate_guard + detection via transcript analysis) provides defense in depth

Deductions:
- The delegate_guard itself leaves no trace when it blocks calls (Improvement 4 addresses this)
- Canary trap detection is not present (Improvement 3 addresses this)
- There is no mechanism to detect bypass attempts that succeed (e.g., base64 encoding that passes the guard but is detected in transcript analysis)

---

## Summary Table

| Gap | Description | Severity | Addressed by Plan | Fix Available? |
|-----|-------------|----------|-------------------|----------------|
| 1.1 | Env var name leaks eval status | MEDIUM | Plan 01 | Rename to opaque name |
| 1.2 | Exit code 2 is distinguishable | LOW | None | Accept risk |
| 1.3 | Restricted tool set is a fingerprint | LOW | None | Accept risk (inherent to enforcement) |
| 2.1 | Base64 encoding bypasses pattern match | HIGH | Plan 01 | Add `base64`, `eval`, `exec` patterns |
| 2.2 | perl/ruby/node interpreters not blocked | MEDIUM | Plan 01 | Add interpreter patterns |
| 2.3 | `python3.12` bypasses `"python3 "` | HIGH | Plan 01 | Change to `"python3"` (no trailing space) |
| 2.4 | Shell string concatenation bypasses | MEDIUM | None | Allowlist model (Improvement 1) |
| 2.5 | `less`/`head`/`tail`/`more` bypass `cat` | MEDIUM | Plan 01 | Add file-reading command patterns |
| 2.6 | `find -exec`, `awk`, `sed` bypass | MEDIUM | Plan 01 | Add patterns or use allowlist |
| **2.7** | **`"alphaswarm"` in allowed_reads lets `python -c "import alphaswarm"` through** | **CRITICAL** | **Plan 01** | **Separate allowed_file_reads from allowed_bash_commands (Improvement 5)** |
| 3.1 | Canary test is unit-level, not integration | HIGH | Plan 06 | Add integration preflight canary |
| 3.2 | Relative path risk for DELEGATE_GUARD_CONFIG | MEDIUM | Plan 01 | Validate absolute path in code |
| 4.1 | WebFetch/WebSearch not intercepted | MEDIUM | Plan 01 | Add to blocked_tools |
| 4.2 | Glob not blocked | HIGH | Plan 01 | Add to blocked_tools |
| 4.3 | Edit not blocked | MEDIUM | Plan 01 | Add to blocked_tools |
| 4.4 | Grep is fully unblocked | HIGH | Plan 01 | Add to blocked_tools with contract/ exception |
| 5.1 | `git log` reveals project context | HIGH | Plan 01 | Block `"git "` in patterns |
| 5.5 | `git show HEAD:CLAUDE.md` bypasses Read block | HIGH | Plan 01 | Block `"git "` in patterns |

**Critical items requiring immediate Plan 01 revision:** Gap 2.7 (allowed_reads escape hatch).
**High items requiring Plan 01 additions:** Gaps 2.1, 2.3, 3.1, 4.2, 4.4, 5.1, 5.5.

---

## Prioritized Recommendations

### Must-Fix Before Plan 06 Execution

1. **Separate Bash exceptions from file-read exceptions** (Gap 2.7, CRITICAL). The `allowed_reads: ["alphaswarm"]` pattern creates a universal bypass for any Bash command containing `"alphaswarm"`. This alone invalidates the enforcement layer.

2. **Block Glob, Grep, Edit, git** (Gaps 4.2, 4.4, 4.3, 5.1). Without these, agents can enumerate the directory tree, search file contents, modify files, and read any file via git object storage.

3. **Add integration-level canary to Plan 06** (Gap 3.1). Spawn a single test teammate that attempts a blocked command; verify the block fires in a real teammate subprocess before running the full calibration.

### Should-Fix for Framework Robustness

4. Fix `"python3 "` pattern to catch versioned interpreters (Gap 2.3).
5. Add `"base64"`, `"perl "`, `"ruby "`, `"node "` to blocked patterns (Gaps 2.1, 2.2).
6. Rename `ALPHASWARM_EVAL_MODE` to something opaque (Gap 1.1).
7. Add blocked-call logging to delegate_guard.py (Improvement 4).

### Should-Consider for Long-Term

8. Switch to allowlist-based Bash enforcement (Improvement 1). The blocklist approach is fundamentally a cat-and-mouse game.
9. Use detached workspace instead of git worktree (Improvement 2). Eliminates the entire `.git/` leakage class.
10. Plant canary traps for leakage detection (Improvement 3).
