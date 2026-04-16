# Phase 5.2 Refactor: Multi-Model Agent Execution with OpenCode SDK

**Date:** 2026-01-21 (Updated)
**Goal:** Replace expensive API-based SDKs with cost-optimized multi-model execution using OpenCode SDK + free-tier models

## Motivation

The current implementation uses:
- `anthropic.AsyncAnthropic` → **API billing ($15/M input, $75/M output)**
- `agents.Agent/Runner` → **API billing ($10/M input, $30/M output)**

The refactor will use:
- **OpenCode SDK** → Gateway to 400+ models including free tiers
- **Claude Code CLI** → Subscription-based orchestration (Pro/Max flat monthly)
- **Codex CLI** → ChatGPT Plus subscription for reviews/discussion
- **Free-tier models** → Big Pickle, MiniMax M2 for verification tasks
- **Cost-effective models** → GLM-4.7 Z.AI ($6/month), Grok Code Fast 1

This eliminates per-token costs for most operations while maintaining quality through intelligent model routing.

---

## Architecture Overview

### Current Architecture (API-Based)
```
AgentRuntime (ABC)
    ├── AnthropicRuntime (anthropic.py) → Anthropic API (expensive)
    └── OpenAIAgentsRuntime (openai_agents.py) → OpenAI API (expensive)
```

### New Architecture (Multi-Model with OpenCode SDK)
```
AgentRuntime (ABC)
    │
    ├── OpenCodeRuntime (opencode_runtime.py) → OpenCode SDK
    │   ├── Uses @opencode-ai/sdk for programmatic control
    │   ├── Routes to 400+ models via OpenRouter
    │   ├── Model selection based on task requirements
    │   └── Free-tier models for verification/double-checks
    │
    ├── ClaudeCodeRuntime (claude_code.py) → Claude Code CLI (orchestration)
    │   ├── Uses `claude` command with --print/--output-format json
    │   ├── Session management via --resume
    │   ├── Subagent spawning via Task tool
    │   └── Primary analysis (Attacker, Defender, Verifier)
    │
    └── CodexCLIRuntime (codex_cli.py) → Codex CLI (reviews)
        ├── Uses `codex exec` for scripted tasks
        ├── Different perspective for double-checks
        └── Best for: review, discussion

Model Routing:
┌─────────────────────────────────────────────────────────────────┐
│                    Task Requirements                             │
├─────────────────────────────────────────────────────────────────┤
│ Critical Analysis (Attacker, Verifier) → Claude Code CLI        │
│ Guard Detection (Defender)             → Claude Code CLI        │
│ Code Generation (Test Builder)         → Claude Code CLI        │
│ Quick Context Gathering               → Grok Code Fast 1        │
│ Verification Tasks                    → Big Pickle (FREE)       │
│ Double-checks                         → MiniMax M2 (FREE)       │
│ Summarization                         → MiniMax M2 (FREE)       │
│ Coding Tasks (non-critical)           → GLM-4.7 Z.AI ($6/mo)   │
│ Reviews/Discussion                    → Codex CLI               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Model Selection Strategy

### Primary Models (Subscription-Based)
| Model | Cost | Use Case | Context |
|-------|------|----------|---------|
| Claude Code CLI | $20-100/mo | Critical analysis, orchestration | Unlimited |
| Codex CLI | $20/mo | Reviews, alternative perspective | Unlimited |

### Cost-Effective Models (Via OpenCode SDK)
| Model | Cost | Use Case | Context | Speed |
|-------|------|----------|---------|-------|
| GLM-4.7 Z.AI | $6/mo (Coding Plan) | Agentic coding, tool use | 128K | Good |
| Grok Code Fast 1 | $0.20/M in, $1.50/M out | Quick context gathering, heavy text | 256K | 92 TPS |

### Free-Tier Models (Via OpenCode SDK/OpenRouter)
| Model | Cost | Use Case | Context | Output |
|-------|------|----------|---------|--------|
| Big Pickle | **FREE** | Verification, validation | 200K | 128K |
| MiniMax M2 | **FREE** | Double-checks, summarization | 204K | 8K |

### OpenCode SDK Model IDs
```javascript
// Free models via OpenRouter
"qwen/qwen-2.5-72b-instruct:free"     // Alternative free option
"meta-llama/llama-3.3-70b-instruct:free"  // Alternative free option
"google/gemma-3-27b-it:free"          // Alternative free option

// Cost-effective models
"zhipu/glm-4.7"                       // GLM-4.7 Z.AI
"x-ai/grok-code-fast-1"               // Grok Code Fast 1
"minimax/minimax-m2.1"                // MiniMax M2.1 (paid tier)
```

---

## OpenCode SDK Integration

### Installation
```bash
# npm (for SDK)
npm install @opencode-ai/sdk

# CLI (already available via npx)
npx opencode --help
```

### SDK Usage Pattern
```javascript
import { createOpencode } from "@opencode-ai/sdk"

// Initialize with default model
const { client } = await createOpencode({
  config: {
    model: "minimax/minimax-m2:free",  // Default to free model
  },
})

// Create session
const session = await client.session.create({ body: {} })

// Send prompt with specific model override
const result = await client.session.prompt({
  path: { id: session.id },
  body: {
    model: {
      providerID: "openrouter",
      modelID: "qwen/qwen-2.5-72b-instruct:free",
    },
    parts: [{ type: "text", text: "Verify this finding..." }],
  },
})
```

### CLI Usage Pattern
```bash
# Quick verification with free model
opencode -p "Verify this finding is valid" --model "minimax/minimax-m2:free" -f json -q

# Fast context gathering with Grok
opencode -p "Summarize these 50 functions" --model "x-ai/grok-code-fast-1" -f json -q

# Coding task with GLM
opencode -p "Write a test for this vulnerability" --model "zhipu/glm-4.7" -f json
```

### Configuration (opencode.config.json)
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mode": {
    "verify": {
      "model": "minimax/minimax-m2:free",
      "tools": { "write": false, "edit": false, "bash": false }
    },
    "summarize": {
      "model": "minimax/minimax-m2:free",
      "tools": { "write": false, "edit": false, "bash": false }
    },
    "context": {
      "model": "x-ai/grok-code-fast-1",
      "tools": { "write": false, "edit": false, "bash": true }
    },
    "code": {
      "model": "zhipu/glm-4.7",
      "tools": { "write": true, "edit": true, "bash": true }
    }
  }
}
```

---

## Model Ranking/Feedback System (Phase 7)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Model Ranking System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Task      │───▶│   Model     │───▶│  Execution  │        │
│  │   Router    │    │  Selector   │    │   Engine    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                 │                   │                 │
│         ▼                 ▼                   ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Task      │    │   Model     │    │  Result     │        │
│  │   Profiles  │    │  Rankings   │    │  Evaluator  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                           │                   │                 │
│                           └───────┬───────────┘                 │
│                                   ▼                             │
│                          ┌─────────────┐                        │
│                          │  Feedback   │                        │
│                          │   Store     │                        │
│                          └─────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Task Profiles
```python
@dataclass
class TaskProfile:
    """Profile defining task requirements for model selection."""
    task_type: str  # verify, summarize, code, analyze, review
    complexity: str  # simple, moderate, complex
    context_size: int  # Required context window
    output_size: int  # Expected output size
    requires_tools: bool  # Needs tool use capability
    latency_sensitive: bool  # Needs fast response
    accuracy_critical: bool  # Quality matters most
```

### Model Rankings Schema
```python
@dataclass
class ModelRanking:
    """Track model performance per task type."""
    model_id: str
    task_type: str
    success_rate: float  # 0.0-1.0
    average_latency_ms: int
    average_tokens: int
    quality_score: float  # 0.0-1.0 (from evaluator)
    cost_per_task: float  # USD
    sample_count: int
    last_updated: datetime
```

### Feedback Collection
```python
@dataclass
class TaskFeedback:
    """Feedback from task execution for ranking updates."""
    task_id: str
    model_id: str
    task_type: str
    success: bool
    latency_ms: int
    tokens_used: int
    quality_score: float  # From automated or human evaluation
    cost_usd: float
    timestamp: datetime
    error_message: Optional[str] = None
```

### Model Selection Algorithm
```python
def select_model(task: TaskProfile, rankings: Dict[str, ModelRanking]) -> str:
    """Select best model for task based on rankings and requirements.

    Priority order:
    1. Filter by capability (context size, tool use)
    2. Filter by accuracy threshold (if accuracy_critical)
    3. Sort by:
       - If latency_sensitive: latency first, then quality
       - If accuracy_critical: quality first, then cost
       - Otherwise: cost first, then quality
    4. Return top model

    Fallback chain:
    - Free models → Cost-effective models → Claude Code CLI
    """
    candidates = []

    for model_id, ranking in rankings.items():
        # Check capability requirements
        model_caps = MODEL_CAPABILITIES[model_id]
        if task.context_size > model_caps.max_context:
            continue
        if task.requires_tools and not model_caps.supports_tools:
            continue

        # Check accuracy threshold for critical tasks
        if task.accuracy_critical and ranking.quality_score < 0.85:
            continue

        candidates.append((model_id, ranking))

    if not candidates:
        return "claude_code"  # Fallback to subscription

    # Sort based on task priority
    if task.latency_sensitive:
        candidates.sort(key=lambda x: (x[1].average_latency_ms, -x[1].quality_score))
    elif task.accuracy_critical:
        candidates.sort(key=lambda x: (-x[1].quality_score, x[1].cost_per_task))
    else:
        candidates.sort(key=lambda x: (x[1].cost_per_task, -x[1].quality_score))

    return candidates[0][0]
```

### Ranking Update Algorithm
```python
def update_ranking(
    ranking: ModelRanking,
    feedback: TaskFeedback,
    decay_factor: float = 0.95,
) -> ModelRanking:
    """Update model ranking with exponential moving average.

    Uses decay factor to weight recent feedback more heavily.
    """
    n = ranking.sample_count

    # Exponential moving average
    alpha = 1 / (n + 1) if n < 100 else 0.01  # Cap learning rate

    new_success_rate = (
        ranking.success_rate * decay_factor +
        (1.0 if feedback.success else 0.0) * (1 - decay_factor)
    )

    new_latency = int(
        ranking.average_latency_ms * decay_factor +
        feedback.latency_ms * (1 - decay_factor)
    )

    new_quality = (
        ranking.quality_score * decay_factor +
        feedback.quality_score * (1 - decay_factor)
    )

    new_cost = (
        ranking.cost_per_task * decay_factor +
        feedback.cost_usd * (1 - decay_factor)
    )

    return ModelRanking(
        model_id=ranking.model_id,
        task_type=ranking.task_type,
        success_rate=new_success_rate,
        average_latency_ms=new_latency,
        average_tokens=int(ranking.average_tokens * decay_factor + feedback.tokens_used * (1 - decay_factor)),
        quality_score=new_quality,
        cost_per_task=new_cost,
        sample_count=n + 1,
        last_updated=feedback.timestamp,
    )
```

### Phase 7 Integration
The ranking system will be exercised in Phase 7 (Final Testing) to:
1. Run each model against a standard test suite
2. Collect feedback on success rate, latency, quality
3. Build initial rankings for production use
4. Identify which models to use/avoid per task type

---

## Implementation Plan

### Wave 1: OpenCode SDK Runtime

#### Plan R5.2-01: OpenCode SDK Runtime
**Files:**
- `src/true_vkg/agents/runtime/opencode_runtime.py` (new, ~500 LOC)

**Implementation:**
```python
"""OpenCode SDK Runtime Implementation.

Uses OpenCode SDK for multi-model execution with free-tier optimization.
Routes tasks to appropriate models based on requirements and rankings.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResponse, AgentRole, AgentRuntime

@dataclass
class OpenCodeConfig:
    """OpenCode runtime configuration."""
    default_model: str = "minimax/minimax-m2:free"
    verify_model: str = "minimax/minimax-m2:free"  # FREE
    summarize_model: str = "minimax/minimax-m2:free"  # FREE
    context_model: str = "x-ai/grok-code-fast-1"  # Fast, good for heavy text
    code_model: str = "zhipu/glm-4.7"  # Already paid
    fallback_model: str = "qwen/qwen-2.5-72b-instruct:free"  # FREE fallback


class OpenCodeRuntime(AgentRuntime):
    """OpenCode SDK implementation of AgentRuntime.

    Uses OpenCode CLI for multi-model execution:
    - Free models for verification and summarization
    - Cost-effective models for coding and context gathering
    - Model routing based on task requirements

    Benefits:
    - Access to 400+ models via OpenRouter
    - Free-tier models for non-critical tasks
    - Smart routing based on task requirements
    - Cost tracking and optimization
    """

    def __init__(
        self,
        config: OpenCodeConfig | None = None,
        working_dir: Optional[Path] = None,
        rankings_store: Optional[Path] = None,
    ):
        self.config = config or OpenCodeConfig()
        self.working_dir = working_dir or Path.cwd()
        self.rankings_store = rankings_store or Path(".vrs/model_rankings.json")
        self._rankings: Dict[str, Dict] = self._load_rankings()

    def _load_rankings(self) -> Dict[str, Dict]:
        """Load model rankings from disk."""
        if self.rankings_store.exists():
            return json.loads(self.rankings_store.read_text())
        return {}

    def _save_rankings(self) -> None:
        """Save model rankings to disk."""
        self.rankings_store.parent.mkdir(parents=True, exist_ok=True)
        self.rankings_store.write_text(json.dumps(self._rankings, indent=2))

    def _select_model(self, task_type: str, role: AgentRole) -> str:
        """Select model based on task type and role.

        Task types:
        - verify: Validation, double-check → Free model
        - summarize: Compression, context gathering → Free model
        - context: Heavy text processing → Grok (fast)
        - code: Code generation, tests → GLM-4.7
        - analyze: Deep analysis → Check rankings, fallback to free
        """
        # Check rankings first
        ranking_key = f"{task_type}:{role.value}"
        if ranking_key in self._rankings:
            best_model = self._rankings[ranking_key].get("best_model")
            if best_model:
                return best_model

        # Default model selection
        if task_type == "verify":
            return self.config.verify_model
        elif task_type == "summarize":
            return self.config.summarize_model
        elif task_type == "context":
            return self.config.context_model
        elif task_type == "code":
            return self.config.code_model
        else:
            return self.config.default_model

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
        task_type: str = "analyze",
    ) -> AgentResponse:
        """Execute via OpenCode CLI.

        Args:
            config: Agent configuration
            messages: Conversation messages
            task_type: Type of task for model selection

        Returns:
            AgentResponse with model output
        """
        # Select model based on task type
        model = self._select_model(task_type, config.role)

        # Build prompt
        prompt = self._build_prompt(config, messages)

        # Build command
        cmd = self._build_command(model, prompt)

        # Execute
        start_time = asyncio.get_event_loop().time()
        result = await self._run_subprocess(cmd, config.timeout_seconds)
        latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        # Parse and record feedback
        response = self._parse_response(result, model, latency_ms)

        # Record feedback for ranking updates
        await self._record_feedback(task_type, config.role, model, response)

        return response

    def _build_command(self, model: str, prompt: str) -> List[str]:
        """Build opencode CLI command."""
        return [
            "opencode",
            "-p", prompt,
            "--model", model,
            "-f", "json",  # JSON output
            "-q",  # Quiet (no spinner)
        ]

    async def _run_subprocess(
        self,
        cmd: List[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """Run opencode CLI as subprocess."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            if proc.returncode != 0:
                raise RuntimeError(f"OpenCode CLI error: {stderr.decode()}")

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"OpenCode CLI timed out after {timeout}s")

    def _parse_response(
        self,
        result: Dict[str, Any],
        model: str,
        latency_ms: int,
    ) -> AgentResponse:
        """Parse OpenCode CLI response."""
        usage = result.get("usage", {})

        # Calculate cost based on model
        cost = self._calculate_cost(
            model,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )

        return AgentResponse(
            content=result.get("content", result.get("result", "")),
            tool_calls=result.get("tool_calls", []),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=0,
            cache_write_tokens=0,
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost,
            metadata={"provider": "opencode"},
        )

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost based on model pricing."""
        # Free models
        if ":free" in model or model in [
            "minimax/minimax-m2:free",
            "qwen/qwen-2.5-72b-instruct:free",
        ]:
            return 0.0

        # Grok Code Fast 1
        if "grok-code-fast" in model:
            return (input_tokens * 0.20 + output_tokens * 1.50) / 1_000_000

        # GLM-4.7 (subscription-based, estimate)
        if "glm-4" in model:
            return 0.0  # Subscription-based

        # Default estimate
        return (input_tokens * 0.50 + output_tokens * 1.50) / 1_000_000

    async def _record_feedback(
        self,
        task_type: str,
        role: AgentRole,
        model: str,
        response: AgentResponse,
    ) -> None:
        """Record feedback for ranking updates."""
        ranking_key = f"{task_type}:{role.value}"

        if ranking_key not in self._rankings:
            self._rankings[ranking_key] = {
                "best_model": model,
                "samples": [],
            }

        # Add sample
        self._rankings[ranking_key]["samples"].append({
            "model": model,
            "latency_ms": response.latency_ms,
            "tokens": response.input_tokens + response.output_tokens,
            "cost": response.cost_usd,
            "success": bool(response.content),
        })

        # Keep last 100 samples
        self._rankings[ranking_key]["samples"] = \
            self._rankings[ranking_key]["samples"][-100:]

        # Update best model periodically
        if len(self._rankings[ranking_key]["samples"]) % 10 == 0:
            self._update_best_model(ranking_key)

        self._save_rankings()

    def _update_best_model(self, ranking_key: str) -> None:
        """Update best model based on collected samples."""
        samples = self._rankings[ranking_key]["samples"]

        # Group by model
        model_stats: Dict[str, Dict] = {}
        for sample in samples:
            model = sample["model"]
            if model not in model_stats:
                model_stats[model] = {"success": 0, "total": 0, "cost": 0}
            model_stats[model]["total"] += 1
            if sample["success"]:
                model_stats[model]["success"] += 1
            model_stats[model]["cost"] += sample["cost"]

        # Calculate scores (success rate / cost, prefer free)
        best_score = -1
        best_model = None

        for model, stats in model_stats.items():
            if stats["total"] < 3:  # Need minimum samples
                continue

            success_rate = stats["success"] / stats["total"]
            avg_cost = stats["cost"] / stats["total"]

            # Score: success rate * (1 / (cost + 0.001))
            # Higher is better, free models get huge boost
            score = success_rate / (avg_cost + 0.001)

            if score > best_score:
                best_score = score
                best_model = model

        if best_model:
            self._rankings[ranking_key]["best_model"] = best_model
```

### Wave 2: Claude Code CLI Runtime (Updated)

#### Plan R5.2-02: Claude Code CLI Runtime
**Files:**
- `src/true_vkg/agents/runtime/claude_code.py` (new, ~400 LOC)

Same as original plan - used for orchestration and critical analysis tasks.

### Wave 3: Codex CLI Runtime

#### Plan R5.2-03: Codex CLI Runtime
**Files:**
- `src/true_vkg/agents/runtime/codex_cli.py` (new, ~300 LOC)

Same as original plan - used for reviews and alternative perspectives.

### Wave 4: Runtime Factory with Multi-Model Support

#### Plan R5.2-04: Runtime Factory Refactor
**Files:**
- `src/true_vkg/agents/runtime/__init__.py`
- `src/true_vkg/agents/runtime/factory.py` (update)

**Changes:**
```python
def create_runtime(
    sdk: str = "auto",
    config: Any = None,
    **kwargs,
) -> AgentRuntime:
    """Create appropriate runtime based on configuration.

    Args:
        sdk: Runtime type - "opencode", "claude_code", "codex", "anthropic", "openai", "auto"
        config: Runtime configuration

    Returns:
        AgentRuntime instance

    SDK Selection:
        - "opencode": OpenCode SDK with multi-model support (recommended for cost optimization)
        - "claude_code": Claude Code CLI (subscription, for critical analysis)
        - "codex": Codex CLI (subscription, for reviews/discussion)
        - "anthropic": Anthropic API (expensive, legacy)
        - "openai": OpenAI API (expensive, legacy)
        - "auto": Smart routing based on task type
    """
    if sdk == "auto":
        # Default routing logic
        sdk = "opencode"  # Default to cost-optimized

    if sdk == "opencode":
        from .opencode_runtime import OpenCodeRuntime, OpenCodeConfig
        return OpenCodeRuntime(config or OpenCodeConfig(), **kwargs)
    elif sdk == "claude_code":
        from .claude_code import ClaudeCodeRuntime
        return ClaudeCodeRuntime(config, **kwargs)
    elif sdk == "codex":
        from .codex_cli import CodexCLIRuntime
        return CodexCLIRuntime(config, **kwargs)
    elif sdk == "anthropic":
        from .anthropic import AnthropicRuntime
        return AnthropicRuntime(config, **kwargs)
    elif sdk == "openai":
        from .openai_agents import OpenAIAgentsRuntime
        return OpenAIAgentsRuntime(config, **kwargs)
    else:
        raise ValueError(f"Unknown SDK: {sdk}")
```

### Wave 5: Smart Task Router

#### Plan R5.2-05: Multi-Model Task Router
**Files:**
- `src/true_vkg/agents/runtime/router.py` (update)

**Logic:**
```python
def route_to_runtime(
    role: AgentRole,
    task_type: str = "analyze",
    accuracy_critical: bool = False,
    latency_sensitive: bool = False,
) -> AgentRuntime:
    """Route task to appropriate runtime.

    Routing logic:
    - Critical analysis (Attacker, Verifier): Claude Code CLI
    - Verification/double-checks: OpenCode (free models)
    - Summarization/context: OpenCode (Grok for speed)
    - Code generation: OpenCode (GLM-4.7)
    - Reviews: Codex CLI (different perspective)

    Args:
        role: Agent role
        task_type: Type of task
        accuracy_critical: Whether accuracy is paramount
        latency_sensitive: Whether speed matters

    Returns:
        Appropriate runtime instance
    """
    # Critical analysis always uses Claude Code
    if accuracy_critical and role in (AgentRole.ATTACKER, AgentRole.VERIFIER):
        return create_runtime("claude_code")

    # Reviews use Codex for different perspective
    if task_type in ("review", "discussion"):
        return create_runtime("codex")

    # Verification and summarization use free models
    if task_type in ("verify", "summarize", "double_check"):
        return create_runtime("opencode")

    # Default to OpenCode for cost optimization
    return create_runtime("opencode")
```

### Wave 6: Subagent Definitions

#### Plan R5.2-06: Claude Code Subagent Skills
**Files:**
- `.claude/agents/vkg-attacker.md` (update)
- `.claude/agents/vkg-defender.md` (update)
- `.claude/agents/vkg-verifier.md` (update)
- `.claude/agents/vkg-test-builder.md` (new)
- `.claude/agents/vkg-supervisor.md` (new)
- `.claude/agents/vkg-integrator.md` (new)

These remain Claude Code agents for critical tasks.

### Wave 7: Model Ranking System

#### Plan R5.2-07: Model Ranking System
**Files:**
- `src/true_vkg/agents/ranking/` (new module)
  - `__init__.py`
  - `schemas.py` - TaskProfile, ModelRanking, TaskFeedback dataclasses
  - `selector.py` - Model selection algorithm
  - `feedback.py` - Feedback collection and ranking updates
  - `store.py` - Persistent storage for rankings

This module implements the ranking/feedback system architecture defined above.

### Wave 8: Integration Updates

#### Plan R5.2-08: Propulsion Engine Update
**Files:**
- `src/true_vkg/agents/propulsion/engine.py` (update)

**Changes:**
- Add task_type parameter to execution calls
- Use router for runtime selection
- Pass rankings store to runtimes

#### Plan R5.2-09: CLI Commands Update
**Files:**
- `src/true_vkg/cli/orchestrate.py` (update)

**Changes:**
- Add `--runtime` flag: `opencode` (default), `claude-code`, `codex`, `api`
- Add `--show-rankings` flag to display current model rankings
- Add `--reset-rankings` flag to clear rankings and start fresh
- Warn when using API-based runtimes (expensive)

### Wave 9: Tests

#### Plan R5.2-10: Runtime Tests
**Files:**
- `tests/test_opencode_runtime.py` (new)
- `tests/test_claude_code_runtime.py` (update)
- `tests/test_codex_cli_runtime.py` (update)
- `tests/test_model_ranking.py` (new)

**Test Coverage:**
- OpenCode CLI command building
- Model selection logic
- Free model routing
- Ranking updates
- Feedback collection

---

## Cost Comparison

| Runtime | Cost Model | Example (1M tokens/month) |
|---------|------------|---------------------------|
| Anthropic API | $15/M in, $75/M out | ~$90 |
| OpenAI API | $10/M in, $30/M out | ~$40 |
| Claude Pro | $20/month flat | $20 |
| Claude Max | $100/month flat | $100 |
| ChatGPT Plus | $20/month flat | $20 |
| GLM-4.7 Coding | $6/month flat | $6 |
| Big Pickle | FREE | $0 |
| MiniMax M2 | FREE | $0 |
| Grok Code Fast 1 | $0.20/M in, $1.50/M out | ~$1.70 |

**Estimated Monthly Cost with New Architecture:**
- Claude Code (orchestration, critical): $20-100
- GLM-4.7 (coding tasks): $6
- Grok (context gathering): ~$5-10
- Free models (verify, summarize): $0

**Total: ~$31-116/month vs ~$500+/month with API billing**

**Savings: 75-95%**

---

## Success Criteria

1. ✅ OpenCode SDK runtime works with all free-tier models
2. ✅ Model ranking system tracks performance per task type
3. ✅ Free models handle verification/summarization effectively
4. ✅ Claude Code CLI used only for critical analysis
5. ✅ Codex CLI works for reviews/discussions
6. ✅ Rankings persist and update automatically
7. ✅ Cost tracking shows 75%+ savings vs API billing
8. ✅ All existing tests pass with new runtimes
9. ✅ Phase 7 can iterate model rankings through testing

---

## Timeline

- **Wave 1:** OpenCode SDK runtime (R5.2-01)
- **Wave 2-3:** CLI runtimes (R5.2-02, R5.2-03)
- **Wave 4-5:** Factory and router (R5.2-04, R5.2-05)
- **Wave 6:** Subagent definitions (R5.2-06)
- **Wave 7:** Model ranking system (R5.2-07)
- **Wave 8:** Integration updates (R5.2-08, R5.2-09)
- **Wave 9:** Tests (R5.2-10)

Total: 10 plans across 9 waves
