"""ScenarioLoader - Load test scenarios from YAML configuration.

Scenarios define:
- Contract(s) to analyze
- Expected findings (ground truth)
- Prompt template
- Allowed tools
- Output schema
- Timeout and model settings
- Isolation settings for blind testing

Example:
    >>> loader = ScenarioLoader(Path("src/alphaswarm_sol/testing/scenarios"))
    >>> scenarios = loader.load_all()
    >>> for name, scenario in scenarios.items():
    ...     print(f"{name}: {len(scenario.contracts)} contracts")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Optional jsonschema support for schema validation
try:
    import jsonschema

    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

# Path to the scenario JSON Schema (relative to this module)
_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / (
    "tests/workflow_harness/scenarios/schema.json"
)


@dataclass
class ContractCase:
    """A contract test case within a scenario.

    Attributes:
        path: Path to the contract file
        has_vulnerability: Whether the contract is expected to have vulnerabilities
        expected_pattern: Expected vulnerability pattern (optional)
        expected_severity: Expected severity level (optional)
        ground_truth: List of expected findings with pattern, severity, location

    Example:
        >>> case = ContractCase(
        ...     path="corpus/reentrancy/vuln-001.sol",
        ...     has_vulnerability=True,
        ...     expected_pattern="reentrancy-classic",
        ...     expected_severity="critical",
        ...     ground_truth=[{"pattern": "reentrancy-classic", "severity": "critical", "location": "withdraw"}]
        ... )
    """

    path: str
    has_vulnerability: bool
    expected_pattern: str | None = None
    expected_severity: str | None = None
    ground_truth: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "has_vulnerability": self.has_vulnerability,
            "expected_pattern": self.expected_pattern,
            "expected_severity": self.expected_severity,
            "ground_truth": self.ground_truth,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractCase":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            has_vulnerability=data.get("has_vulnerability", True),
            expected_pattern=data.get("expected_pattern"),
            expected_severity=data.get("expected_severity"),
            ground_truth=data.get("ground_truth", []),
        )


@dataclass
class TestScenario:
    """A complete test scenario configuration.

    Attributes:
        name: Scenario name (e.g., "Classic Reentrancy")
        category: Vulnerability category (e.g., "reentrancy")
        description: Human-readable description
        contracts: List of ContractCase to test
        prompt_template: Template with {contract_path} placeholder
        allowed_tools: Tools to pre-approve
        json_schema: Schema for structured output
        timeout_seconds: Timeout per contract (default: 120)
        model: Model to use (optional)
        exclude_vulndocs: Don't include vulndocs in context
        blind_prompt: Don't hint at vulnerability type

    Example:
        >>> scenario = TestScenario(
        ...     name="Classic Reentrancy",
        ...     category="reentrancy",
        ...     description="Test detection of classic reentrancy vulnerabilities",
        ...     contracts=[ContractCase(path="vuln.sol", has_vulnerability=True)],
        ...     prompt_template="Analyze {contract_path} for vulnerabilities",
        ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read"],
        ...     json_schema={"type": "object", ...}
        ... )
    """

    name: str
    category: str
    description: str
    contracts: list[ContractCase]
    prompt_template: str
    allowed_tools: list[str]
    json_schema: dict[str, Any]
    timeout_seconds: int = 120
    model: str | None = None

    # Isolation settings for blind testing
    exclude_vulndocs: bool = False  # Don't include vulndocs
    blind_prompt: bool = False  # Don't hint at vulnerability type

    # Execution modes: "single" (one agent) and/or "team" (3-agent debate).
    # Running both on the same scenario enables orchestration comparison.
    modes: list[str] = field(default_factory=lambda: ["single"])

    # Team configuration (used when "team" in modes)
    team_config: dict[str, Any] = field(default_factory=lambda: {
        "roles": ["attacker", "defender", "verifier"],
        "model": "sonnet",
        "team_ground_truth": {},
    })

    # 3.1c evaluation configuration (parsed by 3.1b, executed by 3.1c)
    evaluation: dict[str, Any] | None = None
    evaluation_guidance: dict[str, Any] | None = None
    graders: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    post_run_hooks: list[str] = field(default_factory=list)
    trials: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "contracts": [c.to_dict() for c in self.contracts],
            "prompt_template": self.prompt_template,
            "allowed_tools": self.allowed_tools,
            "json_schema": self.json_schema,
            "timeout_seconds": self.timeout_seconds,
            "model": self.model,
            "isolation": {
                "exclude_vulndocs": self.exclude_vulndocs,
                "blind_prompt": self.blind_prompt,
            },
            "modes": self.modes,
            "team_config": self.team_config,
        }
        # Include new fields only when set (keeps backward compat for serialization)
        if self.evaluation is not None:
            result["evaluation"] = self.evaluation
        if self.evaluation_guidance is not None:
            result["evaluation_guidance"] = self.evaluation_guidance
        if self.graders:
            result["graders"] = self.graders
        if self.steps:
            result["steps"] = self.steps
        if self.post_run_hooks:
            result["post_run_hooks"] = self.post_run_hooks
        if self.trials != 1:
            result["trials"] = self.trials
        return result

    def get_prompt(self, contract_path: str) -> str:
        """Get the prompt for a specific contract.

        Args:
            contract_path: Path to substitute into template

        Returns:
            Formatted prompt string
        """
        return self.prompt_template.format(contract_path=contract_path)

    def get_vulnerable_contracts(self) -> list[ContractCase]:
        """Get contracts expected to have vulnerabilities."""
        return [c for c in self.contracts if c.has_vulnerability]

    def get_safe_contracts(self) -> list[ContractCase]:
        """Get contracts expected to be safe."""
        return [c for c in self.contracts if not c.has_vulnerability]

    def get_team_evaluation_questions(self) -> list[str]:
        """Return auto-injected evaluation questions for team mode.

        When a scenario runs in team mode, these questions guide the
        evaluator to assess orchestration quality -- the DIFFERENCE
        between single and team output IS the orchestration test.

        Returns:
            List of evaluation questions. Empty if "team" not in modes.
        """
        if "team" not in self.modes:
            return []
        return [
            "Did the team find more than a single agent would?",
            "Did evidence pass between agents via SendMessage?",
            "Did debate improve finding confidence vs solo assessment?",
        ]


# Default JSON schema for vulnerability findings
DEFAULT_FINDINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "has_vulnerability": {"type": "boolean"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "severity": {"type": "string"},
                    "location": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["pattern", "severity", "location", "confidence"],
            },
        },
        "reasoning": {"type": "string"},
    },
    "required": ["has_vulnerability", "findings", "reasoning"],
}


class ScenarioLoader:
    """Load test scenarios from YAML files.

    Scenarios are organized by category in subdirectories:
    ```
    scenarios/
    ├── reentrancy/
    │   └── config.yaml
    ├── access_control/
    │   └── config.yaml
    └── oracle/
        └── config.yaml
    ```

    Example:
        >>> loader = ScenarioLoader(Path("src/alphaswarm_sol/testing/scenarios"))
        >>> scenarios = loader.load_all()
        >>> for name, scenario in scenarios.items():
        ...     for contract in scenario.contracts:
        ...         # Run analysis and compare to ground truth
        ...         ...
    """

    def __init__(self, scenarios_dir: Path, *, validate_schema: bool = True):
        """Initialize ScenarioLoader.

        Args:
            scenarios_dir: Directory containing scenario configs
            validate_schema: If True and jsonschema is available, validate
                YAML against the scenario JSON Schema. Validation failures
                produce warnings, never hard errors.
        """
        self.scenarios_dir = Path(scenarios_dir)
        self._schema: dict[str, Any] | None = None
        if validate_schema and _HAS_JSONSCHEMA and _SCHEMA_PATH.exists():
            try:
                with open(_SCHEMA_PATH) as f:
                    self._schema = json.load(f)
            except Exception as exc:
                logger.warning("Failed to load scenario schema: %s", exc)

    def load_all(self) -> dict[str, TestScenario]:
        """Load all scenarios from directory.

        Returns:
            Dict mapping scenario name to TestScenario
        """
        scenarios: dict[str, TestScenario] = {}

        if not self.scenarios_dir.exists():
            logger.warning(f"Scenarios directory not found: {self.scenarios_dir}")
            return scenarios

        for config_file in self.scenarios_dir.rglob("config.yaml"):
            try:
                scenario = self.load_scenario(config_file)
                scenarios[scenario.name] = scenario
                logger.debug(f"Loaded scenario: {scenario.name}")
            except Exception as e:
                logger.error(f"Failed to load {config_file}: {e}")

        logger.info(f"Loaded {len(scenarios)} scenarios from {self.scenarios_dir}")
        return scenarios

    def load_scenario(self, config_path: Path) -> TestScenario:
        """Load a single scenario from YAML config.

        Args:
            config_path: Path to config.yaml file

        Returns:
            TestScenario instance

        Raises:
            KeyError: If required fields are missing
            yaml.YAMLError: If YAML parsing fails
        """
        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Optional schema validation (warns, never blocks)
        if self._schema is not None:
            self._validate_schema(data, config_path)

        # Parse contracts
        contracts = [
            ContractCase(
                path=c["path"],
                has_vulnerability=c.get("has_vulnerability", True),
                expected_pattern=c.get("expected_pattern"),
                expected_severity=c.get("expected_severity"),
                ground_truth=c.get("ground_truth", []),
            )
            for c in data.get("contracts", [])
        ]

        # Get isolation settings
        isolation = data.get("isolation", {})

        # Parse execution modes (default: single-agent only)
        raw_modes = data.get("modes", ["single"])
        valid_modes = {"single", "team"}
        modes = [m for m in raw_modes if m in valid_modes] or ["single"]

        # Parse team configuration
        default_team = {"roles": ["attacker", "defender", "verifier"], "model": "sonnet", "team_ground_truth": {}}
        team_config = data.get("team_config", default_team)

        # Parse new 3.1b-05 fields (all optional, backward compatible)
        evaluation = data.get("evaluation")
        evaluation_guidance = data.get("evaluation_guidance")
        graders = data.get("graders", [])
        steps = data.get("steps", [])
        post_run_hooks = data.get("post_run_hooks", [])
        trials = data.get("trials", 1)

        return TestScenario(
            name=data["name"],
            category=data.get("category", "unknown"),
            description=data.get("description", ""),
            contracts=contracts,
            prompt_template=data["prompt_template"],
            allowed_tools=data.get("allowed_tools", ["Read", "Glob"]),
            json_schema=data.get("json_schema", DEFAULT_FINDINGS_SCHEMA),
            timeout_seconds=data.get("timeout_seconds", 120),
            model=data.get("model"),
            exclude_vulndocs=isolation.get("exclude_vulndocs", False),
            blind_prompt=isolation.get("blind_prompt", False),
            modes=modes,
            team_config=team_config,
            evaluation=evaluation,
            evaluation_guidance=evaluation_guidance,
            graders=graders,
            steps=steps,
            post_run_hooks=post_run_hooks,
            trials=trials,
        )

    def _validate_schema(self, data: dict[str, Any], config_path: Path) -> None:
        """Validate YAML data against scenario JSON Schema.

        Produces warnings on failure, never raises exceptions.
        Schema drift should not block scenario loading.
        """
        try:
            jsonschema.validate(instance=data, schema=self._schema)
        except jsonschema.ValidationError as exc:
            logger.warning(
                "Schema validation warning for %s: %s (path: %s)",
                config_path,
                exc.message,
                list(exc.absolute_path),
            )
        except Exception as exc:
            logger.warning("Schema validation error for %s: %s", config_path, exc)

    def load_by_category(self, category: str) -> list[TestScenario]:
        """Load all scenarios for a specific category.

        Args:
            category: Category name (e.g., "reentrancy")

        Returns:
            List of TestScenario for that category
        """
        all_scenarios = self.load_all()
        return [s for s in all_scenarios.values() if s.category == category]

    def list_categories(self) -> list[str]:
        """List all available scenario categories.

        Returns:
            List of category names
        """
        all_scenarios = self.load_all()
        categories = set(s.category for s in all_scenarios.values())
        return sorted(categories)

    def get_total_contracts(self) -> int:
        """Get total number of contracts across all scenarios.

        Returns:
            Total contract count
        """
        all_scenarios = self.load_all()
        return sum(len(s.contracts) for s in all_scenarios.values())

    def validate_paths(self, base_path: Path | None = None) -> list[str]:
        """Validate that all contract paths exist.

        Args:
            base_path: Base path to resolve contract paths against

        Returns:
            List of missing contract paths
        """
        missing: list[str] = []
        base = base_path or Path(".")

        for scenario in self.load_all().values():
            for contract in scenario.contracts:
                contract_path = base / contract.path
                if not contract_path.exists():
                    missing.append(contract.path)

        return missing

    def create_scenario(
        self,
        name: str,
        category: str,
        description: str,
        prompt_template: str,
        allowed_tools: list[str] | None = None,
    ) -> Path:
        """Create a new scenario directory with config template.

        Args:
            name: Scenario name
            category: Vulnerability category
            description: Scenario description
            prompt_template: Prompt template
            allowed_tools: Tools to pre-approve

        Returns:
            Path to created config.yaml
        """
        # Create category directory
        category_dir = self.scenarios_dir / category.replace("-", "_")
        category_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "name": name,
            "category": category,
            "description": description,
            "contracts": [
                {
                    "path": f"corpus/{category}/example.sol",
                    "has_vulnerability": True,
                    "expected_pattern": f"{category}-classic",
                    "expected_severity": "high",
                    "ground_truth": [
                        {
                            "pattern": f"{category}-classic",
                            "severity": "high",
                            "location": "exampleFunction",
                        }
                    ],
                }
            ],
            "prompt_template": prompt_template,
            "allowed_tools": allowed_tools or ["Bash(uv run alphaswarm*)", "Read", "Glob"],
            "json_schema": DEFAULT_FINDINGS_SCHEMA,
            "timeout_seconds": 120,
            "isolation": {
                "exclude_vulndocs": False,
                "blind_prompt": False,
            },
        }

        config_path = category_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Created scenario config: {config_path}")
        return config_path
