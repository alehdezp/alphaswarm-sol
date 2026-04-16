"""Skill Invocation System.

Task 13.7: Skills are user-invocable actions that wrap grimoire execution.

Skills provide:
- CLI-friendly invocation (/test-reentrancy --finding <id>)
- Parameter parsing and validation
- Context preparation from findings/beads
- Result formatting for display
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from alphaswarm_sol.grimoires.executor import ExecutionContext, GrimoireExecutor
from alphaswarm_sol.grimoires.registry import get_grimoire, get_registry
from alphaswarm_sol.grimoires.schema import Grimoire, GrimoireResult, GrimoireVerdict

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """Status of skill execution."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded
    SKIPPED = "skipped"  # Prerequisites not met
    CANCELLED = "cancelled"


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""

    name: str
    description: str
    param_type: str = "string"  # string, int, bool, path, list
    required: bool = False
    default: Any = None
    choices: List[str] = field(default_factory=list)

    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a parameter value.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if self.required:
                return False, f"Parameter '{self.name}' is required"
            return True, ""

        if self.choices and str(value) not in self.choices:
            return False, f"Parameter '{self.name}' must be one of: {self.choices}"

        if self.param_type == "int":
            try:
                int(value)
            except (ValueError, TypeError):
                return False, f"Parameter '{self.name}' must be an integer"

        if self.param_type == "bool":
            if not isinstance(value, bool) and str(value).lower() not in ("true", "false", "1", "0"):
                return False, f"Parameter '{self.name}' must be a boolean"

        return True, ""


@dataclass
class SkillResult:
    """Result of skill execution."""

    skill_name: str
    status: SkillStatus
    grimoire_result: Optional[GrimoireResult] = None
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if skill succeeded."""
        return self.status == SkillStatus.SUCCESS

    @property
    def verdict(self) -> Optional[GrimoireVerdict]:
        """Get verdict from grimoire result."""
        if self.grimoire_result:
            return self.grimoire_result.verdict
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "grimoire_result": self.grimoire_result.to_dict() if self.grimoire_result else None,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Skill: {self.skill_name}",
            f"Status: {self.status.value}",
        ]

        if self.grimoire_result:
            lines.append(f"Verdict: {self.grimoire_result.verdict.value}")
            lines.append(f"Confidence: {self.grimoire_result.confidence.value}")

        if self.message:
            lines.append(f"Message: {self.message}")

        if self.error:
            lines.append(f"Error: {self.error}")

        return "\n".join(lines)


# Type for skill handlers (alternative to grimoire-based execution)
SkillHandler = Callable[[Dict[str, Any], ExecutionContext], SkillResult]


@dataclass
class Skill:
    """A user-invocable skill.

    Skills can be:
    1. Grimoire-backed: Execute a grimoire procedure
    2. Handler-backed: Execute a custom handler function
    3. Composite: Execute multiple skills in sequence

    Example:
        skill = Skill(
            name="/test-reentrancy",
            description="Test for reentrancy vulnerabilities",
            grimoire_id="grimoire-reentrancy",
        )
    """

    name: str  # e.g., "/test-reentrancy"
    description: str
    category: str = ""

    # Execution mode
    grimoire_id: str = ""  # Grimoire-backed
    handler: Optional[SkillHandler] = None  # Handler-backed
    sub_skills: List[str] = field(default_factory=list)  # Composite

    # Parameters
    parameters: List[SkillParameter] = field(default_factory=list)

    # Requirements
    required_tools: List[str] = field(default_factory=list)
    required_context: List[str] = field(default_factory=list)

    # Display
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False  # Hide from help listings
    tags: List[str] = field(default_factory=list)

    def get_parameter(self, name: str) -> Optional[SkillParameter]:
        """Get parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def validate_args(self, args: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate skill arguments.

        Args:
            args: Arguments to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        for param in self.parameters:
            value = args.get(param.name, param.default)
            is_valid, error = param.validate(value)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "grimoire_id": self.grimoire_id,
            "parameters": [
                {
                    "name": p.name,
                    "description": p.description,
                    "type": p.param_type,
                    "required": p.required,
                    "default": p.default,
                    "choices": p.choices,
                }
                for p in self.parameters
            ],
            "required_tools": self.required_tools,
            "aliases": self.aliases,
            "tags": self.tags,
        }


class SkillRegistry:
    """Registry for managing skills.

    Skills can be registered manually or auto-discovered from grimoires.

    Example:
        registry = SkillRegistry()
        registry.discover_from_grimoires()

        skill = registry.get("/test-reentrancy")
        result = registry.execute(skill.name, args, context)
    """

    def __init__(self, executor: Optional[GrimoireExecutor] = None) -> None:
        """Initialize skill registry.

        Args:
            executor: Optional executor for grimoire-backed skills
        """
        self._skills: Dict[str, Skill] = {}
        self._by_alias: Dict[str, str] = {}
        self._executor = executor or GrimoireExecutor()

    def register(self, skill: Skill) -> None:
        """Register a skill.

        Args:
            skill: Skill to register
        """
        if skill.name in self._skills:
            logger.warning(f"Replacing skill: {skill.name}")

        self._skills[skill.name] = skill

        # Index aliases
        for alias in skill.aliases:
            self._by_alias[alias] = skill.name

        logger.debug(f"Registered skill: {skill.name}")

    def unregister(self, skill_name: str) -> bool:
        """Unregister a skill.

        Args:
            skill_name: Name of skill to remove

        Returns:
            True if skill was removed
        """
        if skill_name not in self._skills:
            return False

        skill = self._skills.pop(skill_name)
        for alias in skill.aliases:
            if alias in self._by_alias:
                del self._by_alias[alias]

        return True

    def get(self, skill_name: str) -> Optional[Skill]:
        """Get skill by name or alias.

        Args:
            skill_name: Skill name or alias

        Returns:
            Skill if found
        """
        # Direct lookup
        if skill_name in self._skills:
            return self._skills[skill_name]

        # Alias lookup
        if skill_name in self._by_alias:
            return self._skills.get(self._by_alias[skill_name])

        return None

    def list_all(self, include_hidden: bool = False) -> List[Skill]:
        """List all registered skills.

        Args:
            include_hidden: Include hidden skills

        Returns:
            List of skills
        """
        if include_hidden:
            return list(self._skills.values())
        return [s for s in self._skills.values() if not s.hidden]

    def list_by_category(self, category: str) -> List[Skill]:
        """List skills by category.

        Args:
            category: Category to filter by

        Returns:
            List of matching skills
        """
        return [s for s in self._skills.values() if s.category == category]

    def discover_from_grimoires(self) -> int:
        """Auto-discover skills from registered grimoires.

        Creates a skill for each grimoire that has a skill name defined.

        Returns:
            Number of skills discovered
        """
        grimoire_registry = get_registry()
        count = 0

        for grimoire in grimoire_registry.list_all():
            if grimoire.skill:
                skill = self._create_skill_from_grimoire(grimoire)
                self.register(skill)
                count += 1

        logger.info(f"Discovered {count} skills from grimoires")
        return count

    def _create_skill_from_grimoire(self, grimoire: Grimoire) -> Skill:
        """Create a skill from a grimoire definition.

        Args:
            grimoire: Grimoire to create skill from

        Returns:
            Skill wrapping the grimoire
        """
        # Standard parameters for grimoire-backed skills
        parameters = [
            SkillParameter(
                name="finding",
                description="Finding ID to verify",
                param_type="string",
                required=False,
            ),
            SkillParameter(
                name="function",
                description="Function name to test",
                param_type="string",
                required=False,
            ),
            SkillParameter(
                name="contract",
                description="Contract name",
                param_type="string",
                required=False,
            ),
            SkillParameter(
                name="path",
                description="Path to contract file",
                param_type="path",
                required=False,
            ),
        ]

        # Add grimoire-specific required context as parameters
        for ctx_key in grimoire.required_context:
            if not any(p.name == ctx_key for p in parameters):
                parameters.append(
                    SkillParameter(
                        name=ctx_key,
                        description=f"Required: {ctx_key}",
                        required=True,
                    )
                )

        return Skill(
            name=grimoire.skill,
            description=grimoire.description or f"Execute {grimoire.name}",
            category=grimoire.category,
            grimoire_id=grimoire.id,
            parameters=parameters,
            required_tools=grimoire.get_required_tools(),
            aliases=grimoire.aliases,
            tags=grimoire.tags,
        )

    def execute(
        self,
        skill_name: str,
        args: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> SkillResult:
        """Execute a skill.

        Args:
            skill_name: Name of skill to execute
            args: Skill arguments
            context: Optional execution context (created if not provided)

        Returns:
            SkillResult
        """
        skill = self.get(skill_name)
        if not skill:
            return SkillResult(
                skill_name=skill_name,
                status=SkillStatus.FAILED,
                error=f"Unknown skill: {skill_name}",
            )

        # Validate arguments
        is_valid, errors = skill.validate_args(args)
        if not is_valid:
            return SkillResult(
                skill_name=skill_name,
                status=SkillStatus.FAILED,
                error=f"Invalid arguments: {'; '.join(errors)}",
            )

        # Create context if not provided
        if context is None:
            context = self._create_context_from_args(args)

        # Check tool requirements
        missing_tools = [t for t in skill.required_tools if not context.has_tool(t)]
        if missing_tools:
            logger.warning(f"Missing tools for skill {skill_name}: {missing_tools}")
            # Continue anyway - some steps may be optional

        # Execute based on skill type
        if skill.grimoire_id:
            return self._execute_grimoire_skill(skill, args, context)
        elif skill.handler:
            return self._execute_handler_skill(skill, args, context)
        elif skill.sub_skills:
            return self._execute_composite_skill(skill, args, context)
        else:
            return SkillResult(
                skill_name=skill_name,
                status=SkillStatus.FAILED,
                error="Skill has no execution method (grimoire, handler, or sub_skills)",
            )

    def _create_context_from_args(self, args: Dict[str, Any]) -> ExecutionContext:
        """Create execution context from skill arguments.

        Args:
            args: Skill arguments

        Returns:
            ExecutionContext
        """
        return ExecutionContext(
            finding_id=args.get("finding", ""),
            function_name=args.get("function", ""),
            contract_name=args.get("contract", ""),
            contract_path=args.get("path", ""),
            config=args,
        )

    def _execute_grimoire_skill(
        self,
        skill: Skill,
        args: Dict[str, Any],
        context: ExecutionContext,
    ) -> SkillResult:
        """Execute a grimoire-backed skill.

        Args:
            skill: Skill to execute
            args: Skill arguments
            context: Execution context

        Returns:
            SkillResult
        """
        grimoire = get_grimoire(skill.grimoire_id)
        if not grimoire:
            return SkillResult(
                skill_name=skill.name,
                status=SkillStatus.FAILED,
                error=f"Grimoire not found: {skill.grimoire_id}",
            )

        try:
            grimoire_result = self._executor.execute(grimoire, context)

            # Map grimoire verdict to skill status
            if grimoire_result.verdict in (GrimoireVerdict.VULNERABLE, GrimoireVerdict.LIKELY_VULNERABLE):
                status = SkillStatus.SUCCESS
                message = "Vulnerability confirmed"
            elif grimoire_result.verdict in (GrimoireVerdict.SAFE, GrimoireVerdict.LIKELY_SAFE):
                status = SkillStatus.SUCCESS
                message = "No vulnerability found"
            elif grimoire_result.verdict == GrimoireVerdict.UNCERTAIN:
                status = SkillStatus.PARTIAL
                message = "Unable to determine - manual review needed"
            else:
                status = SkillStatus.PARTIAL
                message = f"Verdict: {grimoire_result.verdict.value}"

            return SkillResult(
                skill_name=skill.name,
                status=status,
                grimoire_result=grimoire_result,
                message=message,
            )

        except Exception as e:
            logger.exception(f"Error executing skill {skill.name}: {e}")
            return SkillResult(
                skill_name=skill.name,
                status=SkillStatus.FAILED,
                error=str(e),
            )

    def _execute_handler_skill(
        self,
        skill: Skill,
        args: Dict[str, Any],
        context: ExecutionContext,
    ) -> SkillResult:
        """Execute a handler-backed skill.

        Args:
            skill: Skill to execute
            args: Skill arguments
            context: Execution context

        Returns:
            SkillResult
        """
        if not skill.handler:
            return SkillResult(
                skill_name=skill.name,
                status=SkillStatus.FAILED,
                error="Skill has no handler",
            )

        try:
            return skill.handler(args, context)
        except Exception as e:
            logger.exception(f"Error in skill handler {skill.name}: {e}")
            return SkillResult(
                skill_name=skill.name,
                status=SkillStatus.FAILED,
                error=str(e),
            )

    def _execute_composite_skill(
        self,
        skill: Skill,
        args: Dict[str, Any],
        context: ExecutionContext,
    ) -> SkillResult:
        """Execute a composite skill (multiple sub-skills).

        Args:
            skill: Composite skill to execute
            args: Skill arguments
            context: Execution context

        Returns:
            SkillResult with combined results
        """
        sub_results = []
        any_failed = False
        all_succeeded = True

        for sub_skill_name in skill.sub_skills:
            sub_result = self.execute(sub_skill_name, args, context)
            sub_results.append(sub_result)

            if sub_result.status == SkillStatus.FAILED:
                any_failed = True
                all_succeeded = False
            elif sub_result.status != SkillStatus.SUCCESS:
                all_succeeded = False

        # Determine overall status
        if all_succeeded:
            status = SkillStatus.SUCCESS
        elif any_failed:
            status = SkillStatus.PARTIAL
        else:
            status = SkillStatus.SUCCESS

        return SkillResult(
            skill_name=skill.name,
            status=status,
            message=f"Executed {len(sub_results)} sub-skills",
            metadata={"sub_results": [r.to_dict() for r in sub_results]},
        )

    def __len__(self) -> int:
        """Get number of registered skills."""
        return len(self._skills)

    def __contains__(self, skill_name: str) -> bool:
        """Check if skill is registered."""
        return skill_name in self._skills or skill_name in self._by_alias


# Global skill registry instance
_global_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry.

    Returns:
        Global SkillRegistry instance
    """
    global _global_skill_registry
    if _global_skill_registry is None:
        _global_skill_registry = SkillRegistry()
        _global_skill_registry.discover_from_grimoires()
    return _global_skill_registry


def invoke_skill(
    skill_name: str,
    args: Optional[Dict[str, Any]] = None,
    context: Optional[ExecutionContext] = None,
) -> SkillResult:
    """Invoke a skill by name.

    Convenience function for invoking skills from CLI or other code.

    Args:
        skill_name: Name of skill (e.g., "/test-reentrancy")
        args: Optional skill arguments
        context: Optional execution context

    Returns:
        SkillResult

    Example:
        result = invoke_skill("/test-reentrancy", {"finding": "finding-123"})
        print(result.to_summary())
    """
    registry = get_skill_registry()
    return registry.execute(skill_name, args or {}, context)


def list_skills(category: Optional[str] = None, include_hidden: bool = False) -> List[Skill]:
    """List available skills.

    Args:
        category: Optional category filter
        include_hidden: Include hidden skills

    Returns:
        List of skills
    """
    registry = get_skill_registry()
    if category:
        return registry.list_by_category(category)
    return registry.list_all(include_hidden)


def register_skill(skill: Skill) -> None:
    """Register a skill in the global registry.

    Args:
        skill: Skill to register
    """
    get_skill_registry().register(skill)


def reset_skill_registry() -> None:
    """Reset the global skill registry (mainly for testing)."""
    global _global_skill_registry
    _global_skill_registry = None
