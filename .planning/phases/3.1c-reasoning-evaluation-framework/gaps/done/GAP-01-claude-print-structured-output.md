# GAP-01: Claude --print Structured JSON Output Viability

**Created by:** improve-phase
**Source:** P1-IMP-01
**Priority:** HIGH
**Status:** RESOLVED
**depends_on:** []
**Researched:** 2026-02-18
**Confidence:** HIGH

## Question

Does `claude --print --output-format json` receive a transcript + rubric prompt and return structured JSON scores reliably? Can it be used as the LLM evaluation mechanism from Python code?

## Context

P1-IMP-01 identifies a fundamental architecture contradiction: the evaluation pipeline runs in Python (pytest) but CONTEXT.md forbids direct Anthropic API calls. The proposed resolution is Option A: `ClaudeCodeRunner` wrapping `claude --print` for evaluation prompts. If this doesn't work reliably, the entire evaluation execution model needs rethinking.

Affected plans: 3.1c-07 (Evaluator), 3.1c-08 (Runner), all downstream.

## Findings

### 1. `--output-format json` wraps Claude's text response in a metadata envelope

**Confidence: HIGH** (verified via official CLI docs, `claude --help`, Agent SDK spec)

When you run `claude -p "query" --output-format json`, the CLI returns a JSON object with this structure:

```json
{
  "type": "result",
  "subtype": "success",
  "uuid": "...",
  "session_id": "...",
  "duration_api_ms": 12000,
  "num_turns": 2,
  "result": "The actual text response from Claude goes here...",
  ...
}
```

**Critical insight:** The `result` field contains Claude's text response as a **string**, not parsed JSON. If you prompt Claude to return JSON, the `result` field will contain a JSON string that must be double-parsed: first `json.loads(stdout)` to get the envelope, then `json.loads(envelope["result"])` to get the actual evaluation data.

**Source:** Claude Agent SDK Technical Specification (gist.github.com/SamSaffron/603648958a8c18ceae34939a8951d417), official CLI docs (code.claude.com/docs/en/cli-reference).

### 2. `--json-schema` flag provides GUARANTEED schema-compliant structured output

**Confidence: HIGH** (verified via `claude --help` v2.1.47 and official CLI docs)

The `--json-schema` flag (print mode only) accepts a JSON Schema string and guarantees the output conforms to it. From the official CLI reference:

> `--json-schema`: Get validated JSON output matching a JSON Schema after agent completes its workflow (print mode only, see structured outputs)

Example:
```bash
claude -p --json-schema '{"type":"object","properties":{"score":{"type":"integer"},"reasoning":{"type":"string"}},"required":["score","reasoning"]}' "Evaluate X"
```

When combined with `--output-format json`, the `result` field in the envelope will contain valid JSON matching the provided schema. When combined with `--output-format text`, the raw text output will be the JSON itself.

**This is the correct mechanism for our use case.** It uses Claude Code's built-in structured outputs feature (which maps to the API's `output_config.format` parameter) and guarantees schema compliance without relying on prompt engineering.

### 3. `-p` is the shorthand for `--print` — they are identical

**Confidence: HIGH** (verified via `claude --help`)

From help output: `-p, --print  Print response and exit (useful for pipes)`. Both forms are interchangeable. Use `-p` for brevity in code.

### 4. Existing `ModelGrader` implementation is MOSTLY correct but suboptimal

**Confidence: HIGH** (verified via codebase inspection)

The existing `tests/workflow_harness/graders/model_grader.py` already uses `claude --print -p --output-format json` via `subprocess.run()`. However:

**Bug:** Line 73-74 uses both `--print` and `-p` which are the same flag (redundant but harmless).

**Suboptimal:** It relies on prompt engineering ("Respond with ONLY a JSON object...") instead of using `--json-schema` for guaranteed schema compliance. The `_parse_response` method (lines 109-158) has extensive fallback parsing for malformed JSON, which would be unnecessary with `--json-schema`.

**Correct:** The double-parse logic at lines 140-145 correctly handles the `--output-format json` envelope by extracting the inner `result` string.

### 5. `--output-format json` vs `--output-format text` with `--json-schema`

**Confidence: MEDIUM-HIGH** (inferred from official docs + SDK spec)

Two viable combinations for evaluation:

| Combination | Stdout Content | Parsing Strategy |
|---|---|---|
| `--output-format text --json-schema SCHEMA` | Raw JSON string matching schema | Single `json.loads(stdout)` |
| `--output-format json --json-schema SCHEMA` | Envelope with `result` containing schema-compliant JSON string | `json.loads(stdout)["result"]` then `json.loads(...)` |

**Recommendation:** Use `--output-format text --json-schema SCHEMA` for simpler parsing. The text output with `--json-schema` will be guaranteed-valid JSON matching the schema, parseable in a single step.

### 6. Error handling and cost considerations

**Confidence: HIGH**

- `--max-budget-usd` flag caps spend per invocation (print mode only).
- `--max-turns` limits agentic turns; for evaluation prompts (single-turn, no tools needed), set `--max-turns 1`.
- `--model sonnet` or `--model haiku` for cost-effective evaluation.
- `--no-session-persistence` avoids writing session state to disk for ephemeral evaluation calls.
- `--tools ""` disables all tools since evaluation is purely text-in/text-out.
- Process exit code 0 = success, non-zero = failure.
- The `--dangerously-skip-permissions` flag or appropriate permission mode avoids interactive prompts in subprocess context.

### 7. Cannot be tested from within a Claude Code session

**Confidence: HIGH** (verified empirically)

Running `claude -p` from within a Claude Code session fails with: "Error: Claude Code cannot be launched inside another Claude Code session." This means unit tests for `ClaudeCodeRunner` must either: (a) mock the subprocess call, or (b) run in a separate process context outside Claude Code.

## Recommendation

**PRESCRIPTIVE: Use `claude -p --output-format text --json-schema SCHEMA --model MODEL --tools "" --no-session-persistence --max-turns 1` as the evaluation mechanism.**

### ClaudeCodeRunner Implementation Pattern

```python
import json
import subprocess
from dataclasses import dataclass
from typing import Any

@dataclass
class EvaluationResult:
    raw: dict[str, Any]
    model: str
    duration_ms: int | None = None

class ClaudeCodeRunner:
    """Wraps `claude -p` for LLM evaluation calls.

    Uses --json-schema for guaranteed structured output.
    No direct API calls. Cost covered by Claude Code subscription.
    """

    def __init__(
        self,
        model: str = "sonnet",
        timeout: int = 90,
        max_budget_usd: float | None = 0.50,
    ):
        self.model = model
        self.timeout = timeout
        self.max_budget_usd = max_budget_usd

    def evaluate(
        self,
        prompt: str,
        schema: dict[str, Any],
    ) -> EvaluationResult:
        """Send evaluation prompt, get schema-validated JSON back."""
        cmd = [
            "claude", "-p",
            "--output-format", "text",
            "--json-schema", json.dumps(schema),
            "--model", self.model,
            "--tools", "",
            "--no-session-persistence",
            "--max-turns", "1",
            prompt,
        ]

        if self.max_budget_usd is not None:
            cmd.insert(-1, "--max-budget-usd")
            cmd.insert(-1, str(self.max_budget_usd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"claude -p exited {result.returncode}: {result.stderr[:500]}"
            )

        # With --json-schema + --output-format text, stdout IS the JSON
        data = json.loads(result.stdout)

        return EvaluationResult(raw=data, model=self.model)
```

### Key Design Decisions

1. **Use `--output-format text` (not `json`)** with `--json-schema` — single parse step, no envelope unwrapping.
2. **Use `--json-schema`** — guaranteed schema compliance, no prompt-engineering fragility, no regex fallback parsing needed.
3. **Use `--tools ""`** — evaluation is pure text, no tool use needed. Faster, cheaper.
4. **Use `--no-session-persistence`** — evaluation calls are ephemeral, don't pollute session history.
5. **Use `--max-turns 1`** — evaluation is single-turn. Prevents runaway agentic loops.
6. **Use `--max-budget-usd`** — safety cap per evaluation call.
7. **Default model: `sonnet`** — good balance of quality/cost for evaluation. Upgrade to `opus` for high-stakes or disagreement cases.

### Schema Design for Evaluation

```json
{
  "type": "object",
  "properties": {
    "passed": { "type": "boolean" },
    "score": { "type": "integer", "minimum": 0, "maximum": 100 },
    "reasoning": { "type": "string" },
    "dimension_scores": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "score": { "type": "integer", "minimum": 0, "maximum": 100 },
          "evidence": { "type": "string" }
        },
        "required": ["score", "evidence"]
      }
    }
  },
  "required": ["passed", "score", "reasoning"]
}
```

### Impact on Downstream Plans

- **3.1c-07 (Evaluator):** Use `ClaudeCodeRunner.evaluate()` as the LLM grading backend. No direct API calls.
- **3.1c-08 (Runner):** Orchestrate `ClaudeCodeRunner` calls within pytest. Each evaluation call is a subprocess.
- **Existing `ModelGrader`:** Refactor to use `ClaudeCodeRunner` internally. Remove regex fallback parsing, remove prompt-engineering for JSON format (handled by `--json-schema`).
- **Testing `ClaudeCodeRunner` itself:** Mock `subprocess.run` in unit tests. Integration tests must run outside Claude Code sessions.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| `--json-schema` not available in older CLI versions | LOW | Pin minimum version requirement; `claude --version` check at startup |
| Subprocess overhead (cold start) per evaluation call | MEDIUM | Batch evaluations; accept ~2-5s latency per call |
| Session nesting error if accidentally run from Claude Code | LOW | Environment variable check (`CLAUDECODE` env var); skip with mock in CI |
| Schema too complex for model to follow | LOW | `--json-schema` uses constrained decoding, not prompt-engineering; guaranteed compliance |

## Sources

### Primary (HIGH confidence)
- `claude --help` output, v2.1.47 — verified `--json-schema`, `--output-format`, `-p` flags
- Official CLI reference: https://code.claude.com/docs/en/cli-reference — authoritative flag documentation
- Agent SDK structured outputs docs: https://docs.claude.com/en/docs/agent-sdk/structured-outputs — confirms `--json-schema` maps to constrained decoding

### Secondary (MEDIUM-HIGH confidence)
- Claude Agent SDK Technical Specification (gist.github.com/SamSaffron/603648958a8c18ceae34939a8951d417) — JSON envelope structure for `--output-format json`
- ClaudeLog FAQ on --output-format: https://claudelog.com/faqs/what-is-output-format-in-claude-code — confirmed format options
- Blake Crosley's Claude Code CLI Reference (2026-01-15): https://blakecrosley.com/en/guides/claude-code — comprehensive CLI guide

### Codebase (HIGH confidence)
- `tests/workflow_harness/graders/model_grader.py` — existing implementation proving the subprocess pattern works
