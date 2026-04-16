# Research Spike 01: Companion Bridge — Findings

**Executed:** 2026-02-11
**Claude CLI:** 2.1.39
**Companion:** 0.20.3 (via bunx, bun 1.2.23)
**Environment:** macOS Darwin 25.1.0, arm64

---

## RQ-1: Companion Install & Startup

| Item | Result |
|------|--------|
| Bun version | 1.2.23 |
| Companion version | **0.20.3** (docs said 0.19.1 — version drift) |
| Startup time | ~3 seconds (includes npm resolve) |
| Port 3456 accessible | YES |
| Warnings | `fatal: HEAD does not point to a branch` (detached HEAD — cosmetic) |
| Memory footprint | ~58 MB (59,632 KB RSS) |
| Session persistence | `/var/folders/.../vibe-sessions/` — restored 1 old session on startup |

**Issue found:** When Companion is started as a background process, PATH inheritance can fail.
The first attempt got `ENOENT: no such file or directory, posix_spawn 'claude'` because the bun
subprocess didn't inherit `~/.local/bin` in PATH. Fixed by explicitly setting PATH before launch:
```bash
PATH="$HOME/.local/bin:$PATH" bunx the-vibe-companion@0.20.3
```

**Startup log reveals internal CLI invocation:**
```
claude --sdk-url ws://localhost:3456/ws/cli/{sessionId} --print --output-format stream-json
  --input-format stream-json --verbose --model sonnet --permission-mode bypassPermissions -p
```

This is the exact command Companion uses to spawn the CLI. `--sdk-url` is an undocumented flag
not in `claude --help`.

---

## RQ-2: REST API — Verified Endpoints

### Endpoint Map (VERIFIED)

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/sessions` | 200 | Returns `Session[]` |
| POST | `/api/sessions/create` | 200 | **NOT `/api/sessions` (POST)** — key difference from docs |
| GET | `/api/sessions/{id}` | 200 | Returns single session |
| DELETE | `/api/sessions/{id}` | 200 | Returns `{"ok": true}` — idempotent |
| POST | `/api/sessions/{id}/kill` | 200 | Kill process without removing session |
| POST | `/api/sessions/{id}/relaunch` | 200 | Relaunch dead session |
| PATCH | `/api/sessions/{id}/name` | 200 | Rename session |
| POST | `/api/sessions/{id}/archive` | 200 | Archive session |
| POST | `/api/sessions/{id}/unarchive` | 200 | Unarchive session |
| GET | `/api/backends` | 200 | Lists available backends (claude, codex) |
| GET | `/api/fs/list` | 200 | Directory listing |
| GET | `/api/fs/home` | 200 | Home directory info |
| GET | `/api/fs/tree` | 200 | Recursive tree |
| GET | `/api/fs/read` | 200 | Read file content |
| PUT | `/api/fs/write` | 200 | Write file content |
| GET | `/api/fs/diff` | 200 | Git diff for file |
| GET | `/api/envs` | 200 | List environments |
| GET | `/api/git/repo-info` | 200 | Repository info |
| GET | `/api/git/branches` | 200 | List branches |
| GET | `/api/usage-limits` | 200 | Usage limits |

### Session Create Payload (VERIFIED)

```json
POST /api/sessions/create
{
  "cwd": "/path/to/project",       // REQUIRED
  "model": "sonnet",               // optional, passed to CLI
  "permissionMode": "bypassPermissions", // optional
  "backend": "claude",             // optional, default "claude"
  "claudeBinary": "/path/to/claude", // optional, custom binary path
  "env": {"KEY": "value"},         // optional, env vars for CLI
  "envSlug": "my-env",             // optional, companion-managed env
  "allowedTools": ["Bash", "Read"], // optional, restrict tools
  "branch": "main",                // optional, git branch
  "useWorktree": false             // optional, git worktree mode
}
```

### Session Response Schema (VERIFIED)

```json
{
  "sessionId": "uuid-v4",
  "state": "starting" | "connected" | "exited",
  "model": "sonnet",
  "permissionMode": "bypassPermissions",
  "cwd": "/tmp",
  "createdAt": 1770847527375,
  "backendType": "claude",
  "pid": 3735
}
```

Session list includes additional fields: `name`, `gitBranch`, `gitAhead`, `gitBehind`,
`totalLinesAdded`, `totalLinesRemoved`, `exitCode`, `cliSessionId`.

---

## RQ-3: WebSocket Protocol — Verified

### Connection

- **Browser endpoint:** `ws://localhost:3456/ws/browser/{sessionId}`
- **CLI endpoint:** `ws://localhost:3456/ws/cli/{sessionId}` (internal, used by `--sdk-url`)
- **No authentication** required on WS

### Framing Model

| Direction | Format |
|-----------|--------|
| Browser → Bridge | **Single JSON per WS frame** (NOT NDJSON) |
| Bridge → Browser | **Single JSON per WS frame** (NOT NDJSON) |
| CLI → Bridge | **NDJSON** (newline-delimited JSON) |
| Bridge → CLI | **NDJSON** (newline-delimited JSON, sent with `\n` suffix) |

**Key correction:** The browser protocol is NOT NDJSON. Each WS message is exactly one JSON object. NDJSON is only used on the CLI↔Bridge link.

### Browser → Bridge Message Types (VERIFIED from source)

```typescript
type BrowserOutgoingMessage =
  | { type: "user_message"; content: string; images?: [...] }
  | { type: "permission_response"; request_id: string; behavior: "allow"|"deny"; ... }
  | { type: "interrupt" }
  | { type: "set_model"; model: string }
  | { type: "set_permission_mode"; mode: string }
```

### Bridge → Browser Message Types (VERIFIED from source + live test)

| Type | When | Content |
|------|------|---------|
| `session_init` | On WS connect + after CLI init | Full `SessionState` |
| `assistant` | Each assistant message | `message` with `content` blocks |
| `result` | Turn complete | Cost, tokens, result text |
| `permission_request` | Tool needs approval | Tool name, input, request_id |
| `permission_cancelled` | Permission revoked | request_id |
| `tool_progress` | Long tool execution | tool_name, elapsed seconds |
| `tool_use_summary` | Tool batch summary | summary text |
| `status_change` | State change | "compacting", "idle", "running" |
| `stream_event` | Streaming content | Raw event data |
| `cli_connected` | CLI process alive | (empty) |
| `cli_disconnected` | CLI process dead | (empty) |
| `message_history` | On reconnect | Array of past messages |
| `session_name_update` | Auto-naming | New session name |

### Full Round-Trip (VERIFIED)

1. `POST /api/sessions/create` → session created, CLI spawned
2. Wait for `state: "connected"` (CLI connected to bridge)
3. Connect WS to `/ws/browser/{sessionId}`
4. Receive `session_init` with default state
5. Send `{"type": "user_message", "content": "What is 2+2?"}`
6. Receive updated `session_init` (with model, tools, etc.)
7. Receive `assistant` with content blocks
8. Receive `result` with cost, tokens, result text
9. Receive `session_name_update` (auto-naming)

**Latency:** ~8 seconds from session create to `connected` state (CLI startup)
**Cost:** $0.235 for trivial Sonnet prompt (context caching overhead from CLAUDE.md)

---

## RQ-4: bypassPermissions — CONFIRMED

- Session created with `permissionMode: "bypassPermissions"` — accepted without error
- Sent prompt: "Run this command: echo 'hello from companion test'"
- Bash tool executed directly — **zero `permission_request` messages**
- Tool call visible in `assistant` message content blocks (`type: "tool_use"`)
- Result: "hello from companion test" — correct output
- Cost: $0.14 (Sonnet)

**bypassPermissions works exactly as expected. Tools auto-approved, no WS interaction needed.**

---

## RQ-5: Error Handling

| Scenario | Result | Notes |
|----------|--------|-------|
| WS to non-existent session | **404 handshake rejection** | Clean, WS never establishes |
| Malformed JSON via WS | **Silently ignored** | Connection survives, server logs warning |
| Empty string via WS | **Silently ignored** | Connection survives |
| Double-delete session | **Both return 200 `{"ok":true}`** | Idempotent, safe |
| Invalid model name | **Session created anyway** | CLI starts, model validation is CLI-side |
| Invalid backend type | **400 `{"error":"Invalid backend: ..."}`** | Proper validation |

**Error handling is permissive on the bridge side** — most errors are CLI-side. The bridge
doesn't validate model names, prompts, or message content. It just passes them through.

---

## RQ-6: CLI Subprocess — CRITICAL DISCOVERY

### Direct CLI Stream-JSON Mode

The CLI supports bidirectional NDJSON communication **without Companion**:

```bash
echo '{"type":"user","message":{"role":"user","content":"What is 2+2?"},"session_id":"","parent_tool_use_id":null}' | \
claude -p --output-format stream-json --input-format stream-json --verbose --model haiku
```

This produces the **exact same NDJSON stream** that Companion receives via its CLI WS:
1. `system/hook_started` — hook events
2. `system/hook_response` — hook results
3. `system/init` — full session state (tools, model, skills, agents, etc.)
4. `assistant` — response with content blocks
5. `result` — final result with cost/tokens

**This is the same protocol Companion uses internally.** Companion is essentially a web UI +
REST API + WS bridge around `claude -p --output-format stream-json --input-format stream-json`.

### Implications for Python Bridge

| Approach | Pros | Cons |
|----------|------|------|
| **Companion bridge** | REST session CRUD, WS multiplexing, session persistence, web UI | Extra dependency (bun, npm), PATH issues, version drift, 58MB memory |
| **Direct CLI subprocess** | Zero dependencies, same protocol, simpler, no port conflicts | No session persistence, no web UI, must manage process lifecycle |

### Recommendation

**For testing harness (3.1b):** Use **direct CLI subprocess** as the primary approach.
- Zero extra dependencies
- Same NDJSON protocol
- Simpler to manage in pytest fixtures
- `ClaudeCodeRunner` (489 LOC) already wraps subprocess — extend it with stream-json parsing

**Keep Companion as optional secondary tool:**
- Useful for interactive debugging (web UI)
- Useful for multi-session management
- Not required for automated testing

### CLI Flags Verified

| Flag | Works | Notes |
|------|-------|-------|
| `-p` / `--print` | YES | Non-interactive mode |
| `--output-format json` | YES | Single JSON result |
| `--output-format stream-json` | YES | NDJSON stream (requires `--verbose`) |
| `--input-format stream-json` | YES | Accepts NDJSON input on stdin |
| `--verbose` | YES | Required for stream-json output |
| `--model haiku/sonnet/opus` | YES | Alias or full model ID |
| `--permission-mode bypassPermissions` | YES | No approval prompts |
| `--sdk-url` | UNDOCUMENTED | Internal, used by Companion to connect CLI to WS |
| `--dangerously-skip-permissions` | YES | Alternative to bypassPermissions |
| `--allowedTools` | YES | Restrict available tools |
| `--max-budget-usd` | YES | Cost cap for -p mode |
| `--no-session-persistence` | YES | Don't save session to disk |
| `--session-id` | YES | Use specific UUID |

---

## What Works As Documented

- Companion installs and starts on port 3456
- REST API for session CRUD (with endpoint name correction)
- WebSocket for real-time streaming
- `bypassPermissions` mode
- Session lifecycle: create → connect → prompt → result → delete
- Session persistence across restarts

## What Differs From Documentation

| Documented | Actual |
|-----------|--------|
| Version 0.19.1 | **0.20.3** |
| `POST /api/sessions` for create | **`POST /api/sessions/create`** |
| NDJSON on browser WS | **Single JSON per frame** (NDJSON only on CLI link) |
| Complex REST API (git, env, files) | These exist but under `/api/git/`, `/api/fs/`, `/api/envs/` |
| `type: "user"` for browser messages | **`type: "user_message"` with `content: string`** |

## What's Missing From Documentation

1. **`--sdk-url` flag** — undocumented CLI flag used by Companion
2. **`--input-format stream-json`** — enables direct bidirectional NDJSON without Companion
3. **PATH inheritance issue** — Companion's bun subprocess may not inherit PATH
4. **Session auto-naming** — `session_name_update` message type
5. **`message_history` replay** — sent to browser on reconnect for conversation replay
6. **Codex backend support** — Companion can also manage OpenAI Codex sessions
7. **`claudeBinary` option** — session create accepts custom binary path
8. **`allowedTools` option** — restrict tools per session

## RQ-7: Multi-Turn Conversations (CRITICAL FOR WORKFLOW TESTING)

### Verified: Full Multi-Turn Memory

Companion sessions maintain **full conversation context** across multiple `user_message` sends:

| Turn | Prompt | Response | Memory? |
|------|--------|----------|---------|
| 1 | "What is 2+2?" | "4" | N/A |
| 2 | "Multiply that by 3" | "12" | YES — remembered "4" |
| 3 | "Read pyproject.toml, tell me the project name" | "alphaswarm-sol" | YES + used Read tool |
| 4 | "Count .py files in src/" | "609" | YES + used Bash + Glob |

**Cost for 4 turns (Haiku):** $0.0496 cumulative

### Verified: Skill Invocation

Sending `/vrs-health-check` as `user_message` content triggers skill execution:
- Skill loaded and executed correctly
- Bash tool auto-approved (bypassPermissions)
- Full result returned with cost/token metadata
- **Cost:** $0.036 (Haiku, 2 turns)

### Verified: Subagent Spawning

Requesting Task tool usage works — the session spawned an Explore subagent:
- `Task` tool call visible in assistant message content blocks (`type: "tool_use"`)
- Subagent executed Grep + Read tools (visible as subsequent tool_use blocks)
- Main agent synthesized subagent results into response
- **Cost:** $0.13 (Haiku, 2 turns including subagent)

### Multi-Turn Protocol (VERIFIED)

```
Session lifecycle:
1. POST /api/sessions/create → session_id
2. Wait for state=="connected"
3. Connect WS to /ws/browser/{session_id}
4. Send {"type": "user_message", "content": "..."} → wait for type=="result"
5. Send {"type": "user_message", "content": "..."} → wait for type=="result"
6. ... repeat as many turns as needed ...
7. DELETE /api/sessions/{session_id}
```

Each turn:
- Send: `{"type": "user_message", "content": "..."}`
- Receive: 0+ `assistant` messages, then 1 `result` message
- `result.data.num_turns` shows internal turn count (tool calls)
- `result.data.total_cost_usd` is cumulative for the session

### What This Enables for 3.1b

| Capability | Working? | Notes |
|------------|----------|-------|
| Multi-turn conversations | YES | Full memory across turns |
| Skill invocation | YES | Send skill name as message content |
| Tool use (Bash, Read, etc.) | YES | Auto-approved with bypassPermissions |
| Subagent spawning (Task tool) | YES | Explore, Bash, general-purpose agents |
| Team creation (TeamCreate) | UNTESTED | Should work — it's just another tool |
| Permission handling | YES | bypassPermissions skips all approvals |
| Cost tracking | YES | Cumulative per session |
| Session resume | YES | `--resume` flag on relaunch |
| Interrupt | YES | `{"type": "interrupt"}` message |
| Model switching | YES | `{"type": "set_model", "model": "opus"}` mid-session |

### Comparison: Companion vs `-p` for Workflow Testing

| Feature | Companion WS | `claude -p` |
|---------|-------------|-------------|
| Multi-turn | YES | NO (single prompt) |
| Memory | YES | NO |
| Skills | YES | YES |
| Subagents | YES | YES |
| Teams | YES | NO (no interaction) |
| Cost tracking | Per-session cumulative | Per-invocation |
| Session persistence | YES (survives restart) | NO |
| Permission control | Per-session | Per-invocation |
| Model switching mid-session | YES | NO |
| Interrupt mid-turn | YES | NO (kill process) |
| Extra dependencies | bun + npm | None |
| Setup time | ~8s (CLI startup) | ~2s |

**Verdict:** Companion is the **primary tool for workflow testing**, not secondary.
`claude -p` is useful for simple one-shot verification only.

> **Post-Gap Resolution Update (2026-02-12):**
> This verdict is technically correct but has been **deprioritized by GAP-03**. The 3.1c exit gate (context.md line 1621) explicitly marks Companion as NICE-TO-HAVE. Zero 3.1c plans have a hard dependency on `CompanionBridge` or `CompanionSession`. Companion is now Wave 4 in the execution order (after Agent Teams, DSL, and Corpus). The TeamManager (3.1b-04) uses native Agent Teams API, not Companion sessions -- the declared 3.1b-04 dependency on 3.1b-01 was confirmed FALSE. Companion remains valuable for interactive debugging and multi-session management, but is not on the critical path.

---

## Blockers Found

**None.** Companion provides everything needed for scripting complex interactions.

---

## Revised Implementation Spec for 3.1b-01

### Primary Approach: Companion Bridge (Multi-Turn, Skills, Subagents)

```python
class CompanionSession:
    """Scripted multi-turn Claude Code session via Companion REST+WS.

    Supports: multi-turn memory, skill invocation, subagent spawning,
    tool observation, cost tracking, model switching, interrupt.
    """

    def __init__(self, cwd: str, model: str = "sonnet",
                 permission_mode: str = "bypassPermissions",
                 base_url: str = "http://localhost:3456"):
        self.base_url = base_url
        self.session_id: str | None = None
        self.ws: websocket.WebSocketApp | None = None
        self.messages: list[dict] = []
        self._turn_done = threading.Event()
        ...

    def start(self) -> str:
        """Create session via REST, connect WS, wait for ready."""
        # POST /api/sessions/create
        # Wait for state=="connected" (poll every 1s, timeout 15s)
        # Connect WS to /ws/browser/{session_id}
        # Wait for session_init message
        return self.session_id

    def send(self, content: str, timeout: float = 60) -> TurnResult:
        """Send user message, block until result, return structured result.

        Returns TurnResult with:
          .text: str — result text
          .cost_usd: float — cumulative cost
          .num_turns: int — internal turn count
          .tool_calls: list[ToolCall] — tools used this turn
          .messages: list[dict] — all messages this turn
        """
        self._turn_done.clear()
        self._turn_messages = []
        self.ws.send(json.dumps({"type": "user_message", "content": content}))
        self._turn_done.wait(timeout=timeout)
        return self._parse_turn_result()

    def send_skill(self, skill_name: str, args: str = "", timeout: float = 120) -> TurnResult:
        """Invoke a skill (e.g., '/vrs-health-check')."""
        content = f"/{skill_name}" if not skill_name.startswith("/") else skill_name
        if args:
            content += f" {args}"
        return self.send(content, timeout=timeout)

    def interrupt(self):
        """Interrupt the current turn."""
        self.ws.send(json.dumps({"type": "interrupt"}))

    def set_model(self, model: str):
        """Switch model mid-session."""
        self.ws.send(json.dumps({"type": "set_model", "model": model}))

    def close(self):
        """Close WS + delete session."""
        self.ws.close()
        requests.delete(f"{self.base_url}/api/sessions/{self.session_id}")

    # Context manager support
    def __enter__(self): self.start(); return self
    def __exit__(self, *args): self.close()


@dataclass
class TurnResult:
    text: str
    cost_usd: float
    num_turns: int
    tool_calls: list[ToolCall]
    messages: list[dict]
    is_error: bool
    duration_ms: int


@dataclass
class ToolCall:
    name: str
    input: dict
    # tool_result available in messages if PostToolUse observed
```

**Usage in pytest:**
```python
def test_health_check_skill():
    with CompanionSession(cwd=PROJECT_DIR, model="haiku") as session:
        result = session.send_skill("vrs-health-check")
        assert not result.is_error
        assert "HEALTHY" in result.text or "alphaswarm" in result.text
        assert result.cost_usd > 0  # proves real API call
        assert "Bash" in [tc.name for tc in result.tool_calls]

def test_multi_turn_memory():
    with CompanionSession(cwd=PROJECT_DIR, model="haiku") as session:
        r1 = session.send("Remember the number 42.")
        r2 = session.send("What number did I just tell you?")
        assert "42" in r2.text

def test_subagent_spawning():
    with CompanionSession(cwd=PROJECT_DIR, model="haiku") as session:
        result = session.send("Use the Task tool to spawn an Explore agent to find the main entry point of the CLI.")
        assert "Task" in [tc.name for tc in result.tool_calls]
```

### Secondary Approach: Direct CLI Subprocess (Simple, One-Shot)

```python
class ClaudeOneShot:
    """Single-prompt Claude Code execution via subprocess.

    Use for: simple verification, one-off queries, no memory needed.
    """

    def run(self, prompt: str, model: str = "haiku",
            output_format: str = "json") -> dict:
        """Run claude -p and return parsed result."""
        cmd = ["claude", "-p", prompt, "--output-format", output_format,
               "--model", model, "--permission-mode", "bypassPermissions"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout)
```

### Verified Protocol Summary

```
Multi-turn (Companion — PRIMARY):
  Python Test → CompanionSession → REST create → WS connect
    → send("turn 1") → wait result → send("turn 2") → wait result → ...
    → close()

One-shot (CLI subprocess — SECONDARY):
  Python Test → ClaudeOneShot → claude -p "prompt" → JSON result
```

### Python Dependencies

- **Companion bridge:** `requests` + `websocket-client` (both already in deps)
- **CLI one-shot:** None (stdlib `subprocess` + `json`)
- **Companion server:** `bun` (must be installed), `the-vibe-companion` (via bunx)

### Estimated LOC

| Component | LOC |
|-----------|-----|
| `CompanionSession` (multi-turn) | ~250 |
| `CompanionManager` (lifecycle) | ~80 |
| `ClaudeOneShot` (one-shot) | ~50 |
| Message types / TurnResult | ~60 |
| Smoke tests | ~150 |
| **Total** | **~590** |

### Session Lifecycle (Companion — Multi-Turn)

```
1. POST /api/sessions/create → session_id
2. Poll GET /api/sessions/{id} until state=="connected" (~8s)
3. Connect WS to ws://localhost:3456/ws/browser/{session_id}
4. Receive session_init
5. For each turn:
   a. Send {"type": "user_message", "content": "..."}
   b. Collect messages until type=="result"
   c. Parse TurnResult (text, cost, tool_calls)
6. DELETE /api/sessions/{session_id}
```

### Error Handling Requirements

| Error | Handling |
|-------|----------|
| CLI not found | Check `which claude` before subprocess |
| Session startup timeout | Poll session state, timeout after 15s |
| WS handshake failure | Retry once, then raise |
| Malformed NDJSON line | Log warning, skip line |
| Tool permission denied | Should not happen with bypassPermissions |
| CLI process crash | Detect exit code, capture stderr |
| Cost budget exceeded | Use `--max-budget-usd`, detect `error_max_budget_usd` result subtype |
