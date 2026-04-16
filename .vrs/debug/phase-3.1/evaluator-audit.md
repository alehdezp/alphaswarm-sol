# Evaluator Infrastructure Audit for 3.1c Readiness

**Date:** 2026-02-11
**Plan:** 3.1-03
**Purpose:** Document evaluator APIs, identify gaps for 3.1c integration

---

## 1. WorkflowEvaluator

**Source:** `src/alphaswarm_sol/testing/workflow/workflow_evaluator.py` (554 LOC)

### Public Types

#### `EvalStatus(Enum)`
Values: `PASS`, `FAIL`, `ERROR`, `DRIFT`, `TIMEOUT`

#### `ErrorType(Enum)`
Values: `IMPORT_ERROR`, `TYPE_ERROR`, `ATTRIBUTE_ERROR`, `VALUE_ERROR`, `RUNTIME_ERROR`, `FILE_NOT_FOUND`, `PERMISSION_ERROR`, `ASSERTION_ERROR`, `MISSING_PATTERN`, `FORBIDDEN_PATTERN`, `MISSING_FILE`, `UNEXPECTED_OUTPUT`, `DRIFT_DETECTED`, `TIMEOUT`, `UNKNOWN` (15 total)

#### `EvalCriteria` (dataclass)
```python
@dataclass
class EvalCriteria:
    expected_patterns: list[str]          # Patterns that must be present in output
    forbidden_patterns: list[str]         # Patterns that must NOT be present
    expected_files: list[str]             # Files that should be created/modified
    max_errors: int = 0                   # Maximum allowed errors
    min_duration: Optional[float] = None  # Minimum duration (seconds)
    max_duration: Optional[float] = None  # Maximum duration (seconds)
    baseline_output: Optional[str] = None # Previous output for drift detection
    drift_threshold: float = 0.3          # Max allowed difference ratio
    custom_validators: dict[str, callable] = field(default_factory=dict)
```

#### `EvalError` (dataclass)
```python
@dataclass
class EvalError:
    error_type: ErrorType
    message: str
    location: Optional[str] = None       # File:line if available
    context: Optional[str] = None        # Surrounding context
    fixable_immediately: bool = False
    fix_suggestion: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict
```

#### `EvalResult` (dataclass)
```python
@dataclass
class EvalResult:
    status: EvalStatus
    passed_criteria: list[str]
    failed_criteria: list[str]
    errors: list[EvalError]
    drift_indicators: list[str]
    transcript: str = ""
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property is_pass -> bool
    @property has_fixable_errors -> bool
    @property fixable_errors -> list[EvalError]
    def to_dict(self) -> dict
```

### Public Methods

#### `WorkflowEvaluator.__init__(self, working_dir: Optional[str] = None)`
- Sets `self.working_dir` to a `Path` for file existence checks

#### `WorkflowEvaluator.evaluate(self, transcript: str, criteria: EvalCriteria, duration_seconds: float = 0.0, timed_out: bool = False) -> EvalResult`
- Main evaluation entry point
- Evaluation pipeline (in order):
  1. Timeout check
  2. `_extract_errors` - regex-based Python error extraction from transcript text
  3. `_check_expected_patterns` - substring matching for required patterns
  4. `_check_forbidden_patterns` - substring matching for forbidden patterns
  5. `_check_expected_files` - filesystem existence check
  6. `_check_duration` - duration range validation
  7. `_check_drift` - difflib SequenceMatcher similarity comparison
  8. `_run_custom_validators` - user-provided callable validation
  9. `_determine_status` - final status assignment based on error count and types

### Private Methods (internal)

- `_extract_errors(transcript, result)` — Regex-based extraction of 8 Python error types
- `_check_expected_patterns(transcript, criteria, result)` — Simple substring `in` check
- `_check_forbidden_patterns(transcript, criteria, result)` — Simple substring `in` check
- `_check_expected_files(criteria, result)` — `Path.exists()` check
- `_check_duration(duration, criteria, result)` — Range comparison, adds drift indicators
- `_check_drift(transcript, criteria, result)` — `difflib.SequenceMatcher` ratio comparison
- `_run_custom_validators(transcript, criteria, result)` — Calls `(transcript) -> (bool, str)` validators
- `_determine_status(criteria, result)` — Priority: DRIFT > ERROR > FAIL > PASS
- `_analyze_fixability(error_type, message, location)` — Heuristic fix suggestions for ImportError, FileNotFoundError, AttributeError, TypeError

### Extension Points

1. **`custom_validators`** in `EvalCriteria` — Dict of `name -> callable(transcript) -> (bool, msg)`. Extensible at call-site level.
2. **Subclassing** — All private methods follow `_method_name` convention and could be overridden, but the class is not designed for inheritance (no hooks or template methods).

### Identified Gaps for 3.1c

1. **No evaluation-contract-aware mode.** The evaluator operates on raw strings and pattern matching. There is no way to pass a capability contract JSON and have it automatically generate criteria. 3.1c-06 evaluation contracts will need an adapter layer to translate contract specs into `EvalCriteria`.

2. **Pattern matching is substring-only, not regex.** `expected_patterns` uses Python `in` operator, not `re.search`. For 3.1c capability checks like "calls build-kg with --with-labels flag", regex matching would be more precise.

3. **Drift detection is whole-transcript.** The `SequenceMatcher` compares entire transcripts, which is too coarse for detecting specific behavioral regressions. 3.1c-07 regression detection will need structured comparison (e.g., tool sequence diffs, finding count changes).

4. **No LLM-graded evaluation.** All checks are deterministic (substring, file existence, duration). There is no integration point for LLM-based reasoning assessment. 3.1c-04 (reasoning evaluator) will need to add this capability, likely as a custom_validator or new evaluator class.

5. **No graph value scoring.** The evaluator does not integrate with BSKG or graph queries. 3.1c-05 (graph value scoring) needs separate infrastructure.

6. **`to_dict()` output is flat.** The serialization does not include enough structure for automated regression comparison. Missing: tool sequence, capability check results, graph query evidence.

---

## 2. TrajectoryEvaluator

**Source:** `src/alphaswarm_sol/testing/trajectory/evaluator.py` (303 LOC)

### Public Types

#### `StepType(Enum)`
Values: `REASONING`, `TOOL_CALL`, `TOOL_RESULT`, `DECISION`, `ERROR`, `RECOVERY`, `CHECKPOINT` (7 types)

#### `TrajectoryStep` (dataclass)
```python
@dataclass
class TrajectoryStep:
    step_number: int
    step_type: StepType
    timestamp: datetime
    content: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    duration_ms: int = 0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### `Trajectory` (dataclass)
```python
@dataclass
class Trajectory:
    agent_id: str
    agent_type: str
    task_description: str
    start_time: datetime
    end_time: datetime | None = None
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_result: Any = None
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property total_duration_ms -> int
    @property tool_call_count -> int
    @property error_count -> int
    @property recovery_count -> int
```

#### `TrajectoryMetrics` (dataclass)
```python
@dataclass
class TrajectoryMetrics:
    step_efficiency: float        # Productive steps / total steps
    tool_efficiency: float        # Successful tool calls / total tool calls
    time_efficiency: float        # Expected vs actual duration
    tool_appropriateness: float   # Right tools for the task
    reasoning_coherence: float    # Logical flow score
    error_recovery_rate: float    # Recovery success rate
    dead_end_ratio: float         # Unproductive exploration (lower is better)
    redundancy_ratio: float       # Repeated actions (lower is better)
    overall_score: float          # Weighted combination

    def to_dict(self) -> dict[str, float]
```

### Public Methods

#### `TrajectoryEvaluator.__init__(self, expected_tools: list[str] | None = None, expected_duration_ms: int | None = None, optimal_step_count: int | None = None)`
- Configures expected baselines for comparison

#### `TrajectoryEvaluator.evaluate(self, trajectory: Trajectory) -> TrajectoryMetrics`
- Main evaluation entry point
- Computes all 8 quality dimensions and weighted overall score

### 8 Quality Dimensions (private methods)

| # | Dimension | Method | Logic |
|---|-----------|--------|-------|
| 1 | Step Efficiency | `_calculate_step_efficiency` | Productive types (TOOL_CALL, DECISION, CHECKPOINT, RECOVERY) with success=True / total |
| 2 | Tool Efficiency | `_calculate_tool_efficiency` | Successful tool calls / total tool calls |
| 3 | Time Efficiency | `_calculate_time_efficiency` | expected_duration / actual_duration, capped at 1.0 |
| 4 | Tool Appropriateness | `_calculate_tool_appropriateness` | Penalizes missing expected tools (-1 each) and extra tools (-0.5 each) |
| 5 | Reasoning Coherence | `_calculate_reasoning_coherence` | Counts logical connectors ("therefore", "because", etc.) between reasoning steps |
| 6 | Error Recovery Rate | `_calculate_error_recovery_rate` | recovery_count / error_count, capped at 1.0 |
| 7 | Dead End Ratio | `_calculate_dead_end_ratio` | Errors without subsequent recovery / total steps |
| 8 | Redundancy Ratio | `_calculate_redundancy_ratio` | Duplicate (tool_name, tool_args) pairs / total tool calls |

### Scoring Weights

```
step_efficiency:      0.15
tool_efficiency:      0.15
time_efficiency:      0.10
tool_appropriateness: 0.15
reasoning_coherence:  0.15
error_recovery_rate:  0.15
dead_end_ratio:       0.075 (inverted: 1 - ratio)
redundancy_ratio:     0.075 (inverted: 1 - ratio)
```

### Identified Gaps for 3.1c

1. **Reasoning coherence is keyword-based.** Checks for connectors like "therefore", "because" in consecutive reasoning steps. This is a very shallow proxy. 3.1c-04 should replace this with LLM-graded coherence evaluation (e.g., "does the agent's reasoning chain follow logically from evidence to conclusion?").

2. **No Trajectory construction from JSONL.** The `Trajectory` dataclass must be manually constructed. There is no parser that converts Claude Code JSONL transcripts into `Trajectory` objects. 3.1c (or 3.1b) needs a `TranscriptParser -> Trajectory` adapter.

3. **`optimal_step_count` is accepted but never used.** The constructor stores it but no metric references it. Dead parameter.

4. **No per-dimension thresholds.** All metrics are 0-1 floats but there is no way to define pass/fail thresholds per dimension. 3.1c evaluation contracts would benefit from per-dimension thresholds.

5. **Missing security-specific dimensions.** For VRS agents, important dimensions like "evidence citation rate", "graph-first compliance", and "finding specificity" are not captured. These are domain-specific and should be added in 3.1c.

6. **Overall score is for internal regression only.** The weighted overall_score should never be reported as a product quality metric (per STATE.md misconception correction). This needs documentation/enforcement.

---

## Summary

| Evaluator | LOC | Public Methods | Extension Points | Gaps for 3.1c |
|-----------|-----|----------------|-----------------|---------------|
| WorkflowEvaluator | 554 | 1 (evaluate) | custom_validators | 6 (no contract-aware mode, no regex, no structured drift, no LLM eval, no graph scoring, flat serialization) |
| TrajectoryEvaluator | 303 | 1 (evaluate) | constructor params | 6 (keyword coherence, no JSONL parser, dead param, no thresholds, no security dims, score misuse risk) |

**Overall Assessment:** Both evaluators provide useful foundations but are insufficient for 3.1c without adapter layers. The WorkflowEvaluator needs a contract-to-criteria translator. The TrajectoryEvaluator needs a JSONL-to-Trajectory parser. Both need LLM-graded evaluation integration (3.1c-04).
