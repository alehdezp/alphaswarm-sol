# Expected Results: 3.1b-01 Companion Bridge + CLI Verification

---

## Fundamental Deliverable

**This plan delivers a Python bridge that enables programmatic multi-turn Claude Code session automation via Companion REST+WS, plus a one-shot CLI wrapper.** It provides the secondary automation infrastructure for scripted regression runs after interactive evaluation proves what "good" looks like.

This is Wave 4 (optional). Zero 3.1c plans are blocked by this.

---

## Alignment Criteria

### 1. Multi-Turn Session Capability

**The question:** Can Python code create a Claude Code session, send multiple messages with memory preserved between turns, and receive structured responses?

**Aligned if:** A `CompanionSession` (or equivalent) class provides create/send/close lifecycle with WebSocket-based communication, multi-turn memory, and structured response parsing.

**Misaligned if:** Only CLI one-shot wrapper exists (no multi-turn capability), or the bridge simulates multi-turn by chaining independent CLI calls (no memory between turns).

### 2. One-Shot CLI Wrapper

**The question:** Can Python code invoke `claude --print -p "prompt"` and get structured output back?

**Aligned if:** A wrapper class handles subprocess invocation, stdout parsing, error handling, and returns structured results.

**Misaligned if:** No CLI wrapper exists alongside the Companion bridge, or the wrapper returns raw stdout without parsing.

### 3. Graceful Degradation When Companion Unavailable

**The question:** Do tests skip cleanly when Companion isn't running, rather than failing the test suite?

**Aligned if:** Tests use `pytest.mark.skipif` or equivalent to detect Companion availability and skip gracefully. The bridge module itself is importable regardless of Companion status.

**Misaligned if:** Tests fail (not skip) when Companion is down, or the import itself requires a running Companion.

### 4. Verified API Shapes From Research

**The question:** Does the bridge use the actual Companion API shapes verified by research, not guessed from documentation?

**Aligned if:** Endpoint paths, message framing format, and payload types match what was empirically verified in Research Spike 01.

**Misaligned if:** The bridge uses documented-but-wrong shapes (the research identified known documentation inaccuracies).

---

## Drift Detection

### OK (preserves intent)
- Different class/method names than plan pseudocode
- Additional helper methods or extra fields on result types
- Different timeout defaults or retry strategies
- More tests than specified

### DRIFT (needs correction)
- Using known-incorrect API shapes that research explicitly flagged as wrong
- Using async client libraries when the plan selected synchronous for simplicity
- Mocking Companion in smoke tests instead of testing real connections
- Missing session cleanup (orphaned sessions after test runs)

### STOP (fundamental failure)
- No multi-turn support (only CLI one-shot)
- Bridge that sends one message then closes the session
- No WebSocket support (REST-only bridge)
- Tests that fail (not skip) when Companion is unavailable

---

## Cross-Plan Dependencies

| Plan | What's Exchanged | Impact If Missing |
|------|------------------|-------------------|
| 3.1b-04 | `CompanionSession` for multi-turn team testing | Team framework has no automation path |
| 3.1b-07 | Bridge for interactive smoke test | Smoke test can't automate multi-turn steps |
| 3.1c | Full bridge for regression automation | 3.1c can't script N-trial regressions |

**Note:** Since this is Wave 4 (optional), ALL downstream consumers have fallback paths using `claude --print -p`. The Companion bridge adds capability but nothing blocks on it.

---

## Reviewer Guidance

Focus your review on:
1. **Does the bridge actually talk to Companion?** Not mocked, not simulated — real HTTP/WS when available.
2. **Does multi-turn work?** Send message A, send message B that references A's response — does it work?
3. **Does the test suite remain clean?** No failures when Companion is down.
4. **Is the CLI wrapper functional?** Can it invoke `claude` and parse the output?

Do NOT focus on: exact field counts, specific variable names, number of test functions, or whether the implementation matches pseudocode line-by-line.
