---
phase: 3.1b-workflow-testing-harness
plan: 01
type: execute
wave: 4
depends_on: []
files_modified:
  - tests/workflow_harness/lib/companion_bridge.py
  - tests/workflow_harness/test_companion_smoke.py
autonomous: false

must_haves:
  truths:
    - "CompanionSession can create a session via REST and receive a valid sessionId"
    - "CompanionSession can connect via WebSocket and exchange messages in a multi-turn session"
    - "CompanionSession.send() returns a TurnResult with text, cost, and tool_calls extracted from WS stream"
    - "ClaudeOneShot can run a single prompt via CLI and return structured JSON output"
    - "bypassPermissions mode is verified working for unattended session creation"
    - "Python bridge is importable from pytest without errors"
  artifacts:
    - path: "tests/workflow_harness/lib/companion_bridge.py"
      provides: "CompanionSession and ClaudeOneShot classes"
      min_lines: 200
      contains: "class CompanionSession"
    - path: "tests/workflow_harness/test_companion_smoke.py"
      provides: "Smoke tests for Companion REST, WS, CLI"
      min_lines: 80
      contains: "def test_"
  key_links:
    - from: "tests/workflow_harness/lib/companion_bridge.py"
      to: "http://localhost:3456/api/sessions"
      via: "requests HTTP calls"
      pattern: "requests\\.(get|post|delete)"
    - from: "tests/workflow_harness/lib/companion_bridge.py"
      to: "ws://localhost:3456/ws/browser/"
      via: "websocket-client connection"
      pattern: "websocket.*WebSocketApp|ws://localhost:3456"
    - from: "tests/workflow_harness/test_companion_smoke.py"
      to: "tests/workflow_harness/lib/companion_bridge.py"
      via: "import CompanionSession, ClaudeOneShot"
      pattern: "from.*companion_bridge import"
---

<objective>
Build a Python bridge to the Companion REST+WS API for multi-turn Claude Code session
automation, and verify CLI subprocess mode works for one-shot prompts.

Purpose: This bridge enables secondary automation AFTER interactive evaluation proves
what "good" looks like. It provides two complementary paths: CompanionSession for
multi-turn sessions (skills, subagents, teams, model switching) and ClaudeOneShot
for simple single-prompt verification.

Output:
- `tests/workflow_harness/lib/companion_bridge.py` — CompanionSession (~250 LOC) + ClaudeOneShot (~50 LOC) + TurnResult/ToolCall dataclasses
- `tests/workflow_harness/test_companion_smoke.py` — Smoke tests verifying real connections (not mocks)
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/3.1b-workflow-testing-harness/context.md
@.planning/phases/3.1b-workflow-testing-harness/RESEARCH-SPIKE-01-companion-bridge.md

# Existing harness files (companion_bridge.py is NEW, these are for structural reference)
@tests/workflow_harness/lib/transcript_parser.py
@tests/workflow_harness/lib/workspace.py
@tests/workflow_harness/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build CompanionSession + ClaudeOneShot bridge</name>
  <files>tests/workflow_harness/lib/companion_bridge.py</files>
  <action>
Create `tests/workflow_harness/lib/companion_bridge.py` with the following components.

**CRITICAL: Use VERIFIED API shapes from Research Spike 01 — NOT documentation defaults.**

**Data classes:**

```python
@dataclass
class ToolCall:
    name: str
    input: dict

@dataclass
class TurnResult:
    text: str
    cost_usd: float
    num_turns: int
    tool_calls: list[ToolCall]
    messages: list[dict]  # raw WS messages for this turn
    is_error: bool
    duration_ms: int
```

**CompanionSession class (~250 LOC):**

```python
class CompanionSession:
    def __init__(self, cwd, model="sonnet", permission_mode="bypassPermissions",
                 base_url="http://localhost:3456"):
        ...

    def start(self) -> str:
        """Create session via REST, poll until connected, connect WS.

        VERIFIED endpoints:
        - POST /api/sessions/create (NOT /api/sessions)
        - Payload: {"cwd": ..., "model": ..., "permissionMode": ..., "backend": "claude"}
        - Response: {"sessionId": "uuid", "state": "starting", ...}
        - Poll GET /api/sessions/{id} until state=="connected" (~8s)
        - Connect WS to ws://localhost:3456/ws/browser/{sessionId}
        - Wait for session_init message on WS
        """

    def send(self, content: str, timeout: int = 60) -> TurnResult:
        """Send user message via WS, collect until result message.

        VERIFIED protocol:
        - Send: {"type": "user_message", "content": "..."} (single JSON per frame)
        - Collect messages until type=="result"
        - Parse assistant messages for text
        - Parse tool_use messages for ToolCall extraction
        - Extract cost from result message if available
        """

    def send_skill(self, skill_name: str, args: str = "", timeout: int = 120) -> TurnResult:
        """Convenience: send("/{skill_name} {args}")."""

    def close(self):
        """Close WS connection, DELETE session via REST.
        DELETE /api/sessions/{id} — returns 200 (idempotent, double-delete safe).
        """

    def __enter__(self): ...
    def __exit__(self, *args): ...
```

**VERIFIED error handling to implement:**
- WS to non-existent session: handle 404 handshake rejection → raise ConnectionError
- Malformed JSON via WS: silently ignored by server, connection survives
- Double-delete session: both return 200 (idempotent) — no error on close after close
- Invalid backend type: 400 error → raise ValueError

**VERIFIED session states:** "starting" → "connected" → "exited"
- Poll with 0.5s interval, max ~20s timeout for starting→connected transition
- Log warning if transition takes > 10s

**WS message types to handle (from bridge→browser):**
session_init, assistant, result, permission_request, status_change, stream_event,
cli_connected, cli_disconnected, message_history, session_name_update, tool_progress,
tool_use_summary, permission_cancelled.

Only session_init (connection ready), assistant (text), result (turn complete),
and tool_use/tool_use_summary need active parsing. Others: store in messages list.

**WS threading model for send():**
The WebSocket listener runs in a daemon thread using `websocket-client`'s `run_forever()`
method. Turn synchronization uses `threading.Event`:
- `send()` clears the event, sends the user_message frame, then calls `event.wait(timeout=N)`
- The WS `on_message` callback appends each parsed message to a `list` (thread-safe via GIL)
- When a message with `type=="result"` arrives, the callback sets the event
- If `event.wait()` times out, raise `TimeoutError` with elapsed duration
- `tool_use` blocks are extracted from `assistant` messages to populate `TurnResult.tool_calls`
- The daemon thread is started once during `start()` and torn down in `close()`

**ClaudeOneShot class (~50 LOC):**

```python
class ClaudeOneShot:
    def run(self, prompt: str, model: str = "haiku",
            output_format: str = "json", timeout: int = 30,
            permission_mode: str = "bypassPermissions") -> dict:
        """Run claude -p with subprocess.

        VERIFIED flags:
        - claude -p "prompt" --output-format json --model {model}
        - --permission-mode bypassPermissions (or --dangerously-skip-permissions)
        - --no-session-persistence
        - Returns parsed JSON dict from stdout
        """
```

**Dependencies:** `requests` and `websocket-client` — both already available. Do NOT use httpx or aiohttp.

**Import guard:** Add a module-level check:
```python
try:
    import requests
    import websocket
except ImportError as e:
    raise ImportError(
        f"companion_bridge requires 'requests' and 'websocket-client': {e}"
    ) from e
```

**Logging:** Use `logging.getLogger(__name__)` for debug-level protocol messages.
  </action>
  <verify>
```bash
cd .
python -c "from tests.workflow_harness.lib.companion_bridge import CompanionSession, ClaudeOneShot, TurnResult, ToolCall; print('Import OK')"
python -c "
from tests.workflow_harness.lib.companion_bridge import TurnResult, ToolCall
t = TurnResult(text='hi', cost_usd=0.01, num_turns=1, tool_calls=[ToolCall(name='Bash', input={'command': 'ls'})], messages=[], is_error=False, duration_ms=500)
assert t.text == 'hi'
assert t.tool_calls[0].name == 'Bash'
print('Dataclass OK')
"
```
  </verify>
  <done>
CompanionSession class exists with start/send/send_skill/close and context manager support.
ClaudeOneShot class exists with run method.
TurnResult and ToolCall dataclasses exist with all documented fields.
All classes importable from pytest.
Uses verified API shapes (POST /api/sessions/create, ws://localhost:3456/ws/browser/{id}, {"type": "user_message"}).
  </done>
</task>

<task type="auto">
  <name>Task 2: Build smoke tests for Companion bridge and CLI</name>
  <files>tests/workflow_harness/test_companion_smoke.py</files>
  <action>
Create `tests/workflow_harness/test_companion_smoke.py` with smoke tests that verify
REAL connections — no mocks, no hardcoded data.

**All tests require a running Companion instance.** Use `pytest.mark.companion` marker
and skip if Companion is not available (connection refused on localhost:3456).

**Test structure:**

```python
import pytest
import requests

COMPANION_URL = "http://localhost:3456"

def companion_available() -> bool:
    """Check if Companion is running on port 3456."""
    try:
        r = requests.get(f"{COMPANION_URL}/api/sessions", timeout=2)
        return r.status_code == 200
    except requests.ConnectionError:
        return False

companion = pytest.mark.skipif(
    not companion_available(),
    reason="Companion not running on localhost:3456"
)
```

**Tests to implement:**

1. `test_rest_list_sessions` — GET /api/sessions returns 200 + JSON array
   - Assert status_code == 200
   - Assert response is a list

2. `test_rest_create_and_delete_session` — Full session lifecycle via REST
   - POST /api/sessions/create with {"cwd": "/tmp", "permissionMode": "bypassPermissions", "backend": "claude"}
   - Assert response has "sessionId" key
   - Assert sessionId is a non-empty string
   - Poll GET /api/sessions/{id} — assert state transitions from "starting"
   - DELETE /api/sessions/{id} — assert 200
   - Cleanup: always delete in finally block

3. `test_rest_bypass_permissions` — Verify bypassPermissions is honored
   - Create session with permissionMode="bypassPermissions"
   - GET /api/sessions/{id} — assert permissionMode == "bypassPermissions"
   - Cleanup session

4. `test_ws_connect_and_receive_init` — WebSocket connection test
   - Create session via REST, wait for "connected" state
   - Connect WS to ws://localhost:3456/ws/browser/{sessionId}
   - Receive first message — assert type == "session_init"
   - Close WS + delete session
   - Timeout: 30s total

5. `test_ws_send_prompt_receive_result` — Full multi-turn via WS
   - Use CompanionSession context manager
   - session.send("What is 2+2?")
   - Assert TurnResult.text contains "4"
   - Assert TurnResult.is_error is False
   - Assert TurnResult.cost_usd > 0 (proves real API call)
   - Timeout: 60s

6. `test_cli_one_shot_json` — CLI subprocess verification
   - ClaudeOneShot().run("What is 2+2?", model="haiku", output_format="json")
   - Assert result is a dict
   - Assert "result" or text content contains "4"
   - Assert no error keys in response

7. `test_cli_bypass_permissions` — CLI with permission bypass
   - ClaudeOneShot().run("echo hello", model="haiku", permission_mode="bypassPermissions")
   - Assert successful execution (no permission prompts)

**Drift enforcement (from context.md):**
- test_rest_create_and_delete_session asserts HTTP status codes from real requests (not mocked)
- test_ws_send_prompt_receive_result makes a real API call (cost_usd > 0)
- test_cli_one_shot_json runs real subprocess with `claude -p`
- test_rest_bypass_permissions explicitly verifies permission mode setting

**Markers:**
- All tests decorated with `@companion` skip marker
- CLI tests additionally check `shutil.which("claude")` is not None

**Resource cleanup:** Every test that creates a session MUST delete it in a finally block
or use CompanionSession as context manager. No orphan sessions.

**Cost awareness:** Tests using real API calls (WS prompt, CLI) should use model="haiku"
to minimize cost. Expected total: ~$0.05-0.10 for full suite.
  </action>
  <verify>
```bash
cd .
# Verify file exists and has test functions
python -c "
import ast, sys
with open('tests/workflow_harness/test_companion_smoke.py') as f:
    tree = ast.parse(f.read())
tests = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
print(f'Found {len(tests)} tests: {tests}')
assert len(tests) >= 6, f'Expected >= 6 tests, got {len(tests)}'
print('Test count OK')
"

# Static API shape verification — ensures code follows research, not stale docs:
grep -q '/api/sessions/create' tests/workflow_harness/lib/companion_bridge.py && echo "OK: /api/sessions/create" || echo "FAIL: wrong session create endpoint"
grep -q 'user_message' tests/workflow_harness/lib/companion_bridge.py && echo "OK: user_message type" || echo "FAIL: wrong WS message type"
grep -q 'websocket' tests/workflow_harness/lib/companion_bridge.py && echo "OK: websocket-client" || echo "FAIL: missing websocket-client usage"
grep -q 'sessionId' tests/workflow_harness/lib/companion_bridge.py && echo "OK: sessionId key" || echo "FAIL: wrong session ID key"
! grep -q 'ndjson\|NDJSON\|split.*\\\\n' tests/workflow_harness/lib/companion_bridge.py && echo "OK: no NDJSON parsing" || echo "FAIL: NDJSON parsing found on browser WS path"

# If Companion is running, actually run the tests:
# pytest tests/workflow_harness/test_companion_smoke.py -v --timeout=120
```
  </verify>
  <done>
At least 7 smoke tests exist covering: REST list sessions, REST create/delete lifecycle,
REST bypassPermissions verification, WS connect + session_init, WS send prompt + receive result,
CLI one-shot JSON output, CLI bypass permissions.
All tests use real connections (skip if Companion unavailable).
All tests clean up sessions in finally blocks.
Cost-conscious: haiku model for API-calling tests.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify Companion bridge works end-to-end</name>
  <files>tests/workflow_harness/test_companion_smoke.py</files>
  <action>
Human verification checkpoint. All automated code is complete from Tasks 1-2.
This checkpoint verifies real execution against a running Companion instance.

**What was built:** Python bridge to Companion REST+WS API (CompanionSession + ClaudeOneShot) with 7 smoke tests.

**Prerequisites:**
1. Ensure Companion is running: `PATH="$HOME/.local/bin:$PATH" bunx the-vibe-companion@0.20.3`
   (Wait for "Listening on port 3456" message)
2. Ensure `claude` CLI is available: `which claude`

**Verification steps:**

Step 1 — Quick REST check:
```bash
curl -s http://localhost:3456/api/sessions | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Sessions: {len(data)}')"
```
Expected: "Sessions: N" (any number)

Step 2 — Run smoke tests:
```bash
cd .
uv run pytest tests/workflow_harness/test_companion_smoke.py -v --timeout=120
```
Expected: All tests pass (or skip with clear reason if Companion not running)

Step 3 — Verify import works:
```bash
cd .
python -c "from tests.workflow_harness.lib.companion_bridge import CompanionSession; print('OK')"
```
Expected: "OK"

Step 4 — Check cost sanity:
After running test_ws_send_prompt_receive_result, verify the reported cost_usd is
in the $0.01-0.10 range (proves real API call, not absurd).

**What to look for:**
- REST calls return real HTTP status codes (200)
- WS connection receives session_init type message
- Prompt "What is 2+2?" returns text containing "4"
- cost_usd > 0 in TurnResult
- No orphan sessions left after test suite completes
  </action>
  <verify>Human runs smoke tests with Companion running and confirms all pass</verify>
  <done>
All 7 smoke tests pass against real Companion instance.
REST returns session data, WS streams messages, CLI returns JSON output.
cost_usd > 0 proves real API calls. No orphan sessions after cleanup.
Type "approved" if all tests pass, or describe failures.
  </done>
</task>

</tasks>

<verification>
1. `python -c "from tests.workflow_harness.lib.companion_bridge import CompanionSession, ClaudeOneShot, TurnResult, ToolCall"` succeeds
2. `tests/workflow_harness/test_companion_smoke.py` contains >= 7 test functions
3. When Companion is running: all smoke tests pass with real connections
4. When Companion is NOT running: all tests skip gracefully (not fail)
5. CompanionSession uses verified endpoints: POST /api/sessions/create, ws://localhost:3456/ws/browser/{id}
6. CompanionSession sends {"type": "user_message", "content": "..."} (verified format)
7. ClaudeOneShot runs `claude -p` with `--output-format json` and `--permission-mode bypassPermissions`
8. No orphan sessions after test cleanup
</verification>

<success_criteria>
- CompanionSession creates sessions, exchanges messages over WS, and cleans up
- ClaudeOneShot runs CLI prompts and returns parsed JSON
- TurnResult captures text, cost, tool_calls from real execution
- bypassPermissions verified for both Companion and CLI paths
- All smoke tests pass against real Companion instance
- Bridge is importable from any pytest test in the harness
</success_criteria>

<output>
After completion, create `.planning/phases/3.1b-workflow-testing-harness/3.1b-01-SUMMARY.md`
</output>
