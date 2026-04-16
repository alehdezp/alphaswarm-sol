"""Pydantic schema for test scenario YAML validation.

Ensures all scenario configurations are valid and complete.
Used by ScenarioLoader to parse and validate YAML files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class GroundTruth(BaseModel):
    """Expected finding for a contract."""

    pattern: str = Field(description="Pattern ID that should be detected")
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        description="Expected severity level"
    )
    location: str = Field(description="Code location (function:line or function name)")
    description: str | None = Field(
        default=None, description="Human description of the vulnerability"
    )
    confidence_min: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence for valid match"
    )


class ContractCase(BaseModel):
    """A contract test case within a scenario."""

    path: str = Field(description="Path to contract file relative to corpus root")
    has_vulnerability: bool = Field(
        default=True, description="Whether contract has the target vulnerability"
    )
    expected_pattern: str | None = Field(
        default=None, description="Primary pattern expected to match"
    )
    expected_severity: str | None = Field(
        default=None, description="Expected severity if vulnerable"
    )
    ground_truth: list[GroundTruth] = Field(
        default_factory=list, description="All expected findings"
    )
    notes: str | None = Field(
        default=None, description="Notes about this test case (e.g., why it's safe)"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for filtering (e.g., 'adversarial', 'edge-case')"
    )

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Ensure path uses forward slashes."""
        return v.replace("\\", "/")


class IsolationConfig(BaseModel):
    """Configuration for blind/isolated testing."""

    exclude_vulndocs: bool = Field(
        default=False, description="Don't include vulnerability documentation in context"
    )
    blind_prompt: bool = Field(
        default=False, description="Don't hint at expected vulnerability type"
    )
    corpus_segment: str | None = Field(
        default=None, description="Use specific corpus segment (e.g., 'post-june-2025')"
    )
    shuffle_corpus: bool = Field(
        default=False, description="Randomize contract order"
    )
    anonymize_contracts: bool = Field(
        default=False, description="Strip identifying comments and names"
    )


class ChaosConfig(BaseModel):
    """Configuration for chaos/fault injection testing."""

    enabled: bool = Field(default=False, description="Enable chaos injection")
    timeout_probability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Probability of tool timeout"
    )
    malformed_probability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Probability of malformed response"
    )
    failure_probability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Probability of tool failure"
    )


class JsonSchemaConfig(BaseModel):
    """JSON schema for structured output."""

    type: str = "object"
    properties: dict = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class TeamConfig(BaseModel):
    """Configuration for multi-agent team execution mode."""

    roles: list[str] = Field(
        default_factory=lambda: ["attacker", "defender", "verifier"],
        description="Agent roles to spawn",
    )
    model: str = Field(default="sonnet", description="Model for team agents")
    team_ground_truth: dict[str, Any] = Field(
        default_factory=dict,
        description="Team-specific expectations (evidence_passing, debate_depth, role_compliance)",
    )


class EvaluationConfig(BaseModel):
    """Configuration for 3.1c evaluation pipeline.

    Stored in scenario YAML under the ``evaluation:`` key.
    Parsed by 3.1b's scenario loader; executed by 3.1c's evaluation runner.

    Attributes:
        contract: Evaluation contract identifier from 3.1c-06. Maps to a YAML
            file in evaluation contracts directory. Any string is accepted;
            contract existence is NOT validated at parse time (3.1c does that).
        run_gvs: Whether to run Graph Value Scoring for this scenario.
        run_reasoning: Whether to run LLM reasoning evaluation.
    """

    contract: str | None = Field(
        default=None, description="Evaluation contract ID (maps to 3.1c-06 YAML file)"
    )
    run_gvs: bool = Field(default=True, description="Run Graph Value Scoring")
    run_reasoning: bool = Field(default=True, description="Run LLM reasoning evaluation")


class EvaluationGuidanceConfig(BaseModel):
    """Per-scenario evaluation guidance for the 3.1c reasoning evaluator.

    Stored in scenario YAML under the ``evaluation_guidance:`` key.
    Parsed by 3.1b; read by 3.1c-07 (reasoning evaluator) to focus its assessment.

    Attributes:
        reasoning_questions: Scenario-specific questions for the evaluator.
        hooks_if_failed: Hook scripts to enable on re-run if evaluation fails.
            Paths relative to workspace root.
    """

    reasoning_questions: list[str] = Field(
        default_factory=list, description="Questions for the LLM reasoning evaluator"
    )
    hooks_if_failed: list[str] = Field(
        default_factory=list, description="Hook scripts to enable on evaluation failure re-run"
    )


class GraderConfig(BaseModel):
    """Grader configuration for a scenario.

    Attributes:
        type: Grader type -- "code" for deterministic, "model" for AI judge.
        method: Check method for code graders (string_match, regex, schema,
            contains_all, contains_any, tool_usage).
        prompt: For model grader: evaluation prompt template.
        schema_path: For schema grader: path to JSON Schema file.
        pattern: For regex grader: regex pattern string.
        expected: Expected values for matching (strings, list, or dict).
        target: What to check -- "response", "structured_output", "tool_sequence".
        model: Model to use for model grader. Default: "sonnet".
        score_range: Expected score range for model grader. Default: [0, 100].
    """

    type: Literal["code", "model"] = "code"
    method: str | None = Field(
        default=None, description="Check method (string_match, regex, schema, etc.)"
    )
    prompt: str | None = Field(
        default=None, description="For model grader: evaluation prompt template"
    )
    schema_path: str | None = Field(
        default=None, description="For schema grader: JSON Schema path"
    )
    pattern: str | None = Field(
        default=None, description="For regex grader: regex pattern"
    )
    expected: str | list[str] | dict[str, Any] | None = Field(
        default=None, description="Expected value(s) for matching"
    )
    target: str | None = Field(
        default=None, description="What to check (response, structured_output, tool_sequence). None = use summary."
    )
    model: str = Field(default="sonnet", description="Model for model grader")
    score_range: list[int] = Field(
        default_factory=lambda: [0, 100], description="Score range for model grader"
    )


class StepExpect(BaseModel):
    """Expected outcomes for a scenario step."""

    response_contains: list[str] = Field(
        default_factory=list, description="Strings that must appear in the response"
    )
    tool_was_used: list[str] = Field(
        default_factory=list, description="Tools that must have been invoked"
    )
    response_not_contains: list[str] = Field(
        default_factory=list, description="Strings that must NOT appear in the response"
    )


class ScenarioStep(BaseModel):
    """A single step in a multi-turn scenario."""

    prompt: str = Field(description="The prompt to send for this step")
    expect: StepExpect | None = Field(
        default=None, description="Expected outcomes for this step"
    )


class ScenarioConfig(BaseModel):
    """Complete test scenario configuration.

    Loaded from YAML files in scenarios/ directory.
    """

    name: str = Field(description="Human-readable scenario name")
    category: str = Field(description="Vulnerability category (e.g., 'reentrancy')")
    description: str = Field(default="", description="Detailed description of scenario")

    # Test cases
    contracts: list[ContractCase] = Field(
        description="Contracts to test in this scenario"
    )

    # Execution config
    prompt_template: str = Field(
        description="Prompt template with {contract_path} placeholder"
    )
    allowed_tools: list[str] = Field(
        default_factory=list, description="Tools to pre-approve for autonomous execution"
    )
    json_schema: JsonSchemaConfig = Field(
        default_factory=JsonSchemaConfig, description="Schema for structured output"
    )
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    model: str | None = Field(default=None, description="Override default model")

    # Isolation for blind testing
    isolation: IsolationConfig = Field(default_factory=IsolationConfig)

    # Chaos injection
    chaos: ChaosConfig = Field(default_factory=ChaosConfig)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard", "expert"] = Field(default="medium")

    # Execution modes: run this scenario as single-agent, multi-agent team, or both.
    # Valid values: "single", "team". Default: ["single"] (backward compatible).
    modes: list[Literal["single", "team"]] = Field(
        default_factory=lambda: ["single"],
        description=(
            "Execution modes for this scenario. 'single' = one agent, "
            "'team' = 3-agent attacker/defender/verifier team. "
            "Specifying both runs the scenario twice for comparison."
        ),
    )

    # Team configuration (used when "team" in modes)
    team_config: TeamConfig = Field(
        default_factory=TeamConfig,
        description="Agent team configuration: roles, model, team-specific ground truth",
    )

    # 3.1c evaluation configuration (parsed by 3.1b, executed by 3.1c)
    evaluation: EvaluationConfig | None = Field(
        default=None,
        description="3.1c evaluation configuration. None = no evaluation.",
    )
    evaluation_guidance: EvaluationGuidanceConfig | None = Field(
        default=None,
        description="Per-scenario reasoning evaluation guidance. None = use defaults.",
    )
    graders: list[GraderConfig] = Field(
        default_factory=list,
        description="Grader configurations for scoring run output.",
    )
    steps: list[ScenarioStep] = Field(
        default_factory=list,
        description="Multi-turn scenario steps. Empty = single prompt_template.",
    )
    post_run_hooks: list[str] = Field(
        default_factory=list,
        description="Post-run hook script paths (relative to workspace root).",
    )
    trials: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of times to run this scenario (for pass@k computation).",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> "ScenarioConfig":
        """Load scenario from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Save scenario to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)

    @property
    def vulnerable_contracts(self) -> list[ContractCase]:
        """Get only contracts that should have vulnerabilities."""
        return [c for c in self.contracts if c.has_vulnerability]

    @property
    def safe_contracts(self) -> list[ContractCase]:
        """Get only contracts that should be safe (false positive tests)."""
        return [c for c in self.contracts if not c.has_vulnerability]

    @property
    def total_expected_findings(self) -> int:
        """Total number of expected findings across all contracts."""
        return sum(len(c.ground_truth) for c in self.contracts)
