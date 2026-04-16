# API Contract: Scenario DSL Extensions

**Location:** `src/alphaswarm_sol/testing/scenarios/config_schema.py` (extends `ScenarioConfig`)
**3.1b Plan:** 3.1b-05
**3.1c Consumers:** 3.1c-06 (Evaluation Contracts), 3.1c-07 (Reasoning Evaluator), 3.1c-08 (Evaluation Runner), 3.1c-09 (Skill Tests), 3.1c-10 (Agent Tests), 3.1c-11 (Orchestrator Tests)

## Parse/Execute Boundary

- **3.1b parses:** Loads scenario YAML, validates schema (including `evaluation`, `evaluation_guidance`, `post_run_hooks`, `graders`), stores as Pydantic models. Scenario DSL fields are parsed and preserved.
- **3.1c executes:** Reads `evaluation` block to decide which evaluation components to run. Reads `evaluation_guidance` to configure reasoning evaluator. Executes `post_run_hooks`. Runs graders.

---

## evaluation: Block

Added to `ScenarioConfig` as an optional field. 3.1b parses it; 3.1c-08 executes it.

```python
from pydantic import BaseModel, Field
from typing import Literal

class EvaluationConfig(BaseModel):
    """Configuration for 3.1c evaluation pipeline.

    Stored in scenario YAML under the `evaluation:` key.
    Parsed by 3.1b's scenario loader; executed by 3.1c's evaluation runner.

    Attributes:
        contract: Evaluation contract identifier from 3.1c-06. Maps to a YAML
            file in `src/alphaswarm_sol/evaluation/contracts/{contract}.yaml`.
            Example: "vrs-attacker", "vrs-health-check".
        run_gvs: Whether to run Graph Value Scoring for this scenario.
        run_reasoning: Whether to run LLM reasoning evaluation.
    """

    contract: str = Field(
        description="Evaluation contract ID (maps to 3.1c-06 YAML file)"
    )
    run_gvs: bool = Field(default=True, description="Run Graph Value Scoring")
    run_reasoning: bool = Field(default=True, description="Run LLM reasoning evaluation")
```

**Backward compatibility:** `evaluation` is optional on `ScenarioConfig`. Existing YAML
files without an `evaluation:` block load normally — `ScenarioConfig.evaluation` is `None`.

**Failure modes:**
- `contract` references a nonexistent evaluation contract ID: 3.1c-08 raises a clear error at evaluation time (not at parse time — 3.1b doesn't validate contract existence).
- All flags default to `True`. A minimal `evaluation:` block needs only `contract:`.

---

## evaluation_guidance: Block

```python
class EvaluationGuidanceConfig(BaseModel):
    """Per-scenario evaluation guidance for the 3.1c reasoning evaluator.

    Stored in scenario YAML under the `evaluation_guidance:` key.
    Parsed by 3.1b; read by 3.1c-07 (reasoning evaluator) to focus its assessment.

    Attributes:
        reasoning_questions: Scenario-specific questions for the evaluator.
            Example: ["Did the agent check for reentrancy before concluding safe?"]
        hooks_if_failed: Hook scripts to enable on re-run if evaluation fails.
            Paths relative to workspace root. 3.1c-12 uses these for improvement.
    """

    reasoning_questions: list[str] = Field(
        default_factory=list,
        description="Questions for the LLM reasoning evaluator"
    )
    hooks_if_failed: list[str] = Field(
        default_factory=list,
        description="Hook scripts to enable on evaluation failure re-run"
    )
```

**Relationship to EvaluationGuidance dataclass:** The `EvaluationGuidanceConfig` Pydantic
model is the YAML-parsed form. The `EvaluationGuidance` dataclass (from observation-models.md)
is the runtime form used by 3.1c. 3.1b-05 provides a conversion method or the evaluation
runner performs the conversion.

---

## post_run_hooks: Field

```python
class ScenarioConfig(BaseModel):
    # ... existing fields ...

    post_run_hooks: list[str] = Field(
        default_factory=list,
        description=(
            "Script paths to execute after scenario run completes. "
            "Paths are relative to workspace root. "
            "3.1c hook scripts (e.g., hooks/evaluate_reasoning.py) "
            "are listed here. 3.1b parses and preserves this list; "
            "the harness runner invokes them in order after the run."
        )
    )
```

**Execution semantics (3.1b responsibility):**
- After a scenario run completes, the harness runner calls each script in `post_run_hooks` in order.
- Scripts receive the workspace path and run artifacts as arguments or environment variables.
- A non-zero exit code from any post_run_hook is logged but does NOT fail the scenario (hooks are advisory).

**Failure modes:**
- Empty list (default): no post-run hooks execute. This is normal for scenarios without evaluation.
- Script not found: logged as warning, execution continues with next hook.
- Script timeout: uses the default hook timeout (30s). Hooks that need longer should be noted.

---

## modes: Field (Already Implemented)

```python
class ScenarioConfig(BaseModel):
    # ... existing fields ...

    modes: list[Literal["single", "team"]] = Field(
        default_factory=lambda: ["single"],
        description=(
            "Execution modes. 'single' = one agent, 'team' = multi-agent team. "
            "Specifying both runs the scenario twice for comparison."
        )
    )
```

**Already implemented** in `config_schema.py`. No changes needed. Contract confirms:
- Default is `["single"]` for backward compatibility.
- `["single", "team"]` runs the scenario twice: once single-agent, once team.
- `["team"]` runs only the team configuration.

---

## team_config: Block (Already Implemented)

```python
class TeamConfig(BaseModel):
    """Configuration for multi-agent team execution mode.

    Already implemented in config_schema.py.

    Attributes:
        roles: Agent roles to spawn. Default: ["attacker", "defender", "verifier"].
        model: Model for team agents. Default: "sonnet".
        team_ground_truth: Team-specific expectations. Keys:
            - "evidence_passing" (bool): Should agents share evidence via SendMessage?
            - "debate_depth" (int): Expected number of debate turns.
            - "role_compliance" (bool): Should each agent stay within its role?
    """

    roles: list[str] = Field(
        default_factory=lambda: ["attacker", "defender", "verifier"]
    )
    model: str = Field(default="sonnet")
    team_ground_truth: dict[str, Any] = Field(default_factory=dict)
```

---

## Grader Types

```python
class CodeGrader(BaseModel):
    """Deterministic grader using code-based checks.

    Attributes:
        type: Always "code".
        method: Check method — "string_match", "regex", "schema", "contains_all",
            "contains_any".
        expected: The expected value, pattern, or schema to match against.
        target: What to check — "response", "structured_output", "tool_sequence".
    """

    type: Literal["code"] = "code"
    method: str = Field(description="Check method")
    expected: str | list[str] | dict = Field(description="Expected value or pattern")
    target: str = Field(default="response", description="What to check")

class ModelGrader(BaseModel):
    """LLM-powered grader for nuanced evaluation.

    Attributes:
        type: Always "model".
        prompt_template: Template for the grader prompt. Receives the scenario
            output as context. Must produce a structured assessment.
        model: Model to use for grading. Default: "sonnet".
        score_range: Expected score range. Default: [0, 100].
    """

    type: Literal["model"] = "model"
    prompt_template: str = Field(description="Grader prompt template")
    model: str = Field(default="sonnet")
    score_range: list[int] = Field(default_factory=lambda: [0, 100])
```

**3.1c consumer expectations:**
- 3.1c-06 evaluation contracts reference code graders for deterministic checks.
- 3.1c-07 reasoning evaluator IS the model grader (the evaluation contract's grader type selects which approach).
- Code graders are implemented in 3.1b; model graders are implemented in 3.1c.

---

## Full ScenarioConfig Extension (Summary)

```python
class ScenarioConfig(BaseModel):
    """Complete test scenario configuration.

    Existing fields (MUST NOT CHANGE):
    - name, category, description, contracts, prompt_template
    - allowed_tools, json_schema, timeout_seconds, model
    - isolation, chaos, tags, difficulty
    - modes, team_config

    New optional fields (3.1b-05 adds):
    """

    # ... existing fields unchanged ...

    evaluation: EvaluationConfig | None = Field(
        default=None,
        description="3.1c evaluation configuration. None = no evaluation."
    )

    evaluation_guidance: EvaluationGuidanceConfig | None = Field(
        default=None,
        description="Per-scenario reasoning evaluation guidance. None = use defaults."
    )

    post_run_hooks: list[str] = Field(
        default_factory=list,
        description="Post-run hook script paths (relative to workspace root)."
    )

    graders: list[CodeGrader | ModelGrader] = Field(
        default_factory=list,
        description="Grader configurations for scoring run output."
    )

    trials: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of times to run this scenario (for pass@k computation)."
    )
```

**Backward compatibility:** All new fields are optional with defaults. Existing YAML
files parse without modification. `evaluation: None` means no evaluation pipeline.

---

## Example YAML

```yaml
name: health-check-basic
description: Verify /vrs-health-check produces valid output
timeout_seconds: 120
model: sonnet
modes: [single]
contracts:
  - path: examples/testing/simple/SimpleToken.sol
    has_vulnerability: false
prompt_template: "Run /vrs-health-check"
graders:
  - type: code
    method: contains_all
    expected: ["alphaswarm", "build-kg"]
    target: response
trials: 3

# 3.1c evaluation (optional — 3.1b parses, 3.1c executes)
evaluation:
  contract: vrs-health-check
  run_gvs: false
  run_reasoning: false

evaluation_guidance:
  reasoning_questions:
    - "Did the health check cover all required components?"
  hooks_if_failed:
    - hooks/debug_health_check.py

post_run_hooks:
  - hooks/log_completion.py
```

---

## 3.1c Loading Path Guidance

Two loading paths exist for scenario YAML files:

| Path | Class | Evaluation Fields | Typed? |
|------|-------|-------------------|--------|
| `ScenarioConfig.from_yaml()` | Pydantic model | `EvaluationGuidanceConfig` object | Yes |
| `ScenarioLoader.load_scenario()` | `TestScenario` dataclass | `evaluation_guidance: dict` | No (raw dict) |

**Recommendation for 3.1c:** Use `ScenarioConfig.from_yaml()` directly for typed evaluation config access. `ScenarioLoader.load_scenario()` returns `TestScenario` with `evaluation_guidance: dict[str, Any]`, suitable for dict-based workflows but less type-safe for evaluation pipeline consumption.

## ModelGrader Scope Note

`ModelGrader` (in `tests/workflow_harness/graders/model_grader.py`) is designed for **simple pass/fail grading only**. It feeds `OutputCollector.summary()` — a ~10-line text summary — to the Claude CLI.

For 3.1c-07 (Reasoning Evaluator), this is insufficient. The reasoning evaluator needs:
- Full tool call sequences with timing
- All BSKG queries with citation status
- Inter-agent messages (for team scenarios)
- Raw transcript segments

**3.1c-07 should build `ReasoningEvaluator` as a new class** that uses `CollectedOutput` directly, not through `ModelGrader`. `ModelGrader` remains available for simple code/model grading in evaluation contracts (3.1c-06).
