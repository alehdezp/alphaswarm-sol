"""Grimoire Execution Engine.

Task 13.1: Execute grimoire procedures step by step.

The executor:
- Runs grimoire steps in order
- Manages execution context
- Tracks evidence from each step
- Determines final verdict
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from alphaswarm_sol.grimoires.schema import (
    Grimoire,
    GrimoireResult,
    GrimoireStep,
    GrimoireStepAction,
    GrimoireVerdict,
    StepEvidence,
    VerdictConfidence,
    VerdictRule,
)

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result from executing a single step."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    skipped: bool = False
    skip_reason: str = ""

    @property
    def is_failure(self) -> bool:
        """Check if step failed (not skipped, not successful)."""
        return not self.success and not self.skipped


@dataclass
class ExecutionContext:
    """Context for grimoire execution.

    The context carries:
    - Finding information (what we're verifying)
    - Graph data (VKG nodes/edges)
    - Accumulated outputs from previous steps
    - Tool availability flags
    - Configuration overrides
    """

    # Finding being verified
    finding_id: str = ""
    function_name: str = ""
    contract_name: str = ""
    contract_path: str = ""

    # Source code context
    source_code: str = ""
    function_source: str = ""

    # Graph context
    graph_data: Dict[str, Any] = field(default_factory=dict)
    node_properties: Dict[str, Any] = field(default_factory=dict)

    # Bead context (from VulnerabilityBead if available)
    bead_data: Dict[str, Any] = field(default_factory=dict)

    # Step outputs (accumulated during execution)
    step_outputs: Dict[str, Any] = field(default_factory=dict)

    # Tool availability
    available_tools: Set[str] = field(default_factory=set)

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Working directory for test generation
    work_dir: str = ""

    # Fork configuration
    fork_rpc: str = ""
    fork_block: str = "latest"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context.

        Searches step_outputs, bead_data, node_properties, graph_data, config.

        Args:
            key: Key to look up
            default: Default value if not found

        Returns:
            Value if found, default otherwise
        """
        if key in self.step_outputs:
            return self.step_outputs[key]
        if key in self.bead_data:
            return self.bead_data[key]
        if key in self.node_properties:
            return self.node_properties[key]
        if key in self.graph_data:
            return self.graph_data[key]
        if key in self.config:
            return self.config[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """Set a value in step outputs.

        Args:
            key: Key to set
            value: Value to store
        """
        self.step_outputs[key] = value

    def has_tool(self, tool: str) -> bool:
        """Check if a tool is available.

        Args:
            tool: Tool name (e.g., "foundry", "medusa")

        Returns:
            True if tool is available
        """
        return tool in self.available_tools

    def has_all_tools(self, tools: List[str]) -> bool:
        """Check if all specified tools are available.

        Args:
            tools: List of tool names

        Returns:
            True if all tools are available
        """
        return all(self.has_tool(t) for t in tools)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "finding_id": self.finding_id,
            "function_name": self.function_name,
            "contract_name": self.contract_name,
            "contract_path": self.contract_path,
            "step_outputs": self.step_outputs,
            "available_tools": list(self.available_tools),
            "config": self.config,
        }


# Type for step handlers
StepHandler = Callable[[GrimoireStep, ExecutionContext], StepResult]


class GrimoireExecutor:
    """Executes grimoire procedures.

    The executor runs each step in order, collecting evidence
    and determining the final verdict based on the results.

    Example:
        executor = GrimoireExecutor()

        # Register custom handlers
        executor.register_handler(GrimoireStepAction.CHECK_GRAPH, my_graph_handler)

        # Execute grimoire
        context = ExecutionContext(
            finding_id="finding-123",
            function_name="withdraw",
            contract_name="Vault",
        )
        result = executor.execute(grimoire, context)

        print(f"Verdict: {result.verdict.value}")
    """

    def __init__(self) -> None:
        """Initialize executor with default handlers."""
        self._handlers: Dict[GrimoireStepAction, StepHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default step handlers."""
        # Default handlers that work without external tools
        self._handlers[GrimoireStepAction.CHECK_GRAPH] = self._handle_check_graph
        self._handlers[GrimoireStepAction.CHECK_PROPERTY] = self._handle_check_property
        self._handlers[GrimoireStepAction.CHECK_SEQUENCE] = self._handle_check_sequence
        self._handlers[GrimoireStepAction.ANALYZE_RESULTS] = self._handle_analyze_results
        self._handlers[GrimoireStepAction.DETERMINE_VERDICT] = self._handle_determine_verdict
        self._handlers[GrimoireStepAction.COMPARE_PATTERNS] = self._handle_compare_patterns

        # Handlers that require external tools (stubs - to be extended)
        self._handlers[GrimoireStepAction.GENERATE_TEST] = self._handle_generate_test
        self._handlers[GrimoireStepAction.GENERATE_INVARIANT] = self._handle_generate_invariant
        self._handlers[GrimoireStepAction.EXECUTE_TEST] = self._handle_execute_test
        self._handlers[GrimoireStepAction.EXECUTE_FUZZ] = self._handle_execute_fuzz
        self._handlers[GrimoireStepAction.EXECUTE_FORK] = self._handle_execute_fork

    def register_handler(self, action: GrimoireStepAction, handler: StepHandler) -> None:
        """Register a custom step handler.

        Args:
            action: Action type to handle
            handler: Handler function
        """
        self._handlers[action] = handler

    def execute(
        self,
        grimoire: Grimoire,
        context: ExecutionContext,
        stop_on_failure: bool = True,
    ) -> GrimoireResult:
        """Execute a grimoire procedure.

        Args:
            grimoire: Grimoire to execute
            context: Execution context
            stop_on_failure: If True, stop on first non-optional failure

        Returns:
            GrimoireResult with verdict and evidence
        """
        started_at = datetime.utcnow()
        start_time = time.time()

        result = GrimoireResult(
            grimoire_id=grimoire.id,
            finding_id=context.finding_id,
            started_at=started_at.isoformat(),
            steps_total=len(grimoire.procedure.steps),
        )

        logger.info(f"Executing grimoire: {grimoire.id} for finding {context.finding_id}")

        # Check tool requirements
        required_tools = grimoire.get_required_tools()
        missing_tools = [t for t in required_tools if not context.has_tool(t)]
        if missing_tools:
            logger.warning(f"Missing tools: {missing_tools}")
            # Continue anyway - some steps may be optional or have fallbacks

        # Execute steps
        for step in grimoire.procedure.steps:
            step_result = self._execute_step(step, context, grimoire)

            # Record evidence
            evidence = StepEvidence(
                step_number=step.step_number,
                step_name=step.name,
                action=step.action,
                success=step_result.success,
                output=step_result.output,
                error=step_result.error,
                duration_ms=step_result.duration_ms,
                metadata={"skipped": step_result.skipped, "skip_reason": step_result.skip_reason},
            )
            result.step_evidence.append(evidence)

            if step_result.success or step_result.skipped:
                result.steps_completed += 1
            else:
                result.steps_failed += 1

                if stop_on_failure and not step.optional:
                    logger.warning(f"Step {step.step_number} failed, stopping execution")
                    result.error = f"Step {step.step_number} ({step.name}) failed: {step_result.error}"
                    break

        # Determine verdict
        result.verdict, result.confidence, result.verdict_explanation = self._determine_verdict(
            grimoire.procedure.verdict_rules,
            grimoire.procedure.default_verdict,
            context,
            result.step_evidence,
        )

        # Finalize timing
        result.completed_at = datetime.utcnow().isoformat()
        result.total_duration_ms = int((time.time() - start_time) * 1000)

        # Extract generated artifacts
        result.generated_test = context.get("generated_test_path", "")
        result.test_output = context.get("test_output", "")
        result.fuzz_report = context.get("fuzz_report", "")

        logger.info(
            f"Grimoire {grimoire.id} completed: {result.verdict.value} "
            f"({result.confidence.value} confidence)"
        )

        return result

    def _execute_step(
        self,
        step: GrimoireStep,
        context: ExecutionContext,
        grimoire: Grimoire,
    ) -> StepResult:
        """Execute a single step.

        Args:
            step: Step to execute
            context: Execution context
            grimoire: Parent grimoire (for configuration)

        Returns:
            StepResult
        """
        # Check skip condition
        if step.skip_if and self._evaluate_condition(step.skip_if, context):
            logger.debug(f"Skipping step {step.step_number}: {step.skip_if}")
            return StepResult(
                success=True,
                skipped=True,
                skip_reason=step.skip_if,
            )

        # Check tool requirements
        if step.tools and not context.has_all_tools(step.tools):
            missing = [t for t in step.tools if not context.has_tool(t)]
            if step.optional:
                logger.debug(f"Skipping optional step {step.step_number}: missing tools {missing}")
                return StepResult(
                    success=True,
                    skipped=True,
                    skip_reason=f"Missing tools: {missing}",
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Missing required tools: {missing}",
                )

        # Get handler
        handler = self._handlers.get(step.action)
        if not handler:
            return StepResult(
                success=False,
                error=f"No handler for action: {step.action.value}",
            )

        # Execute with timing
        start_time = time.time()
        try:
            result = handler(step, context)
            result.duration_ms = int((time.time() - start_time) * 1000)

            # Store outputs in context
            if result.success and result.output and step.outputs:
                if isinstance(result.output, dict):
                    for key in step.outputs:
                        if key in result.output:
                            context.set(key, result.output[key])
                else:
                    # Single output
                    if len(step.outputs) == 1:
                        context.set(step.outputs[0], result.output)

            return result

        except Exception as e:
            logger.exception(f"Error in step {step.step_number}: {e}")
            return StepResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def _determine_verdict(
        self,
        rules: List[VerdictRule],
        default: GrimoireVerdict,
        context: ExecutionContext,
        evidence: List[StepEvidence],
    ) -> tuple[GrimoireVerdict, VerdictConfidence, str]:
        """Determine verdict from evidence using rules.

        Args:
            rules: Verdict rules to evaluate
            default: Default verdict if no rules match
            context: Execution context
            evidence: Evidence from step execution

        Returns:
            Tuple of (verdict, confidence, explanation)
        """
        # Build evidence summary for condition evaluation
        evidence_summary = {
            "all_steps_passed": all(e.success for e in evidence),
            "any_step_failed": any(not e.success and not e.metadata.get("skipped") for e in evidence),
            "test_passed": context.get("test_passed", False),
            "test_failed": context.get("test_failed", False),
            "exploit_successful": context.get("exploit_successful", False),
            "fuzz_found_issue": context.get("fuzz_found_issue", False),
            "graph_matches": context.get("graph_matches", False),
            "sequence_violated": context.get("sequence_violated", False),
            "has_guard": context.get("has_guard", False),
        }

        # Evaluate rules in order
        for rule in rules:
            if self._evaluate_condition(rule.condition, context, evidence_summary):
                return rule.verdict, rule.confidence, rule.explanation

        # No rule matched - use default
        return default, VerdictConfidence.UNKNOWN, "No verdict rule matched"

    def _evaluate_condition(
        self,
        condition: str,
        context: ExecutionContext,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Evaluate a condition expression.

        Supports simple conditions like:
        - "test_passes_exploit" (checks context.get("test_passes_exploit"))
        - "!has_guard" (negation)
        - "graph_matches && !has_guard" (and)
        - "test_failed || fuzz_found_issue" (or)

        Args:
            condition: Condition string
            context: Execution context
            extra: Additional variables for evaluation

        Returns:
            True if condition is satisfied
        """
        if not condition:
            return False

        # Build evaluation namespace
        namespace = {}
        namespace.update(context.step_outputs)
        if extra:
            namespace.update(extra)

        # Simple evaluation - not full expression parser
        condition = condition.strip()

        # Handle negation
        if condition.startswith("!"):
            return not self._evaluate_condition(condition[1:], context, extra)

        # Handle AND
        if "&&" in condition:
            parts = condition.split("&&")
            return all(self._evaluate_condition(p.strip(), context, extra) for p in parts)

        # Handle OR
        if "||" in condition:
            parts = condition.split("||")
            return any(self._evaluate_condition(p.strip(), context, extra) for p in parts)

        # Simple variable lookup
        value = namespace.get(condition, False)
        return bool(value)

    # Default step handlers

    def _handle_check_graph(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle CHECK_GRAPH action - query the VKG graph."""
        queries = step.queries
        if not queries:
            return StepResult(success=True, output={"matches": []})

        # Get graph data from context
        graph_data = context.graph_data
        if not graph_data:
            return StepResult(
                success=False,
                error="No graph data in context",
            )

        # Execute queries (simplified - real implementation would use query engine)
        matches = []
        for query in queries:
            # For now, just check if properties exist
            # Real implementation would use VKG query executor
            if "properties" in graph_data:
                matches.append({
                    "query": query,
                    "matched": True,
                })

        context.set("graph_matches", len(matches) > 0)
        return StepResult(
            success=True,
            output={"matches": matches, "graph_matches": len(matches) > 0},
        )

    def _handle_check_property(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle CHECK_PROPERTY action - check specific node properties."""
        properties = context.node_properties
        if not properties:
            return StepResult(success=True, output={"properties": {}})

        # Check relevant properties based on step inputs
        results = {}
        for prop_name in step.inputs:
            results[prop_name] = properties.get(prop_name)

        return StepResult(
            success=True,
            output={"properties": results},
        )

    def _handle_check_sequence(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle CHECK_SEQUENCE action - verify operation ordering."""
        # Check for sequence violations in context
        sequence_data = context.get("sequence_data", {})

        # Look for CEI violations (Checks-Effects-Interactions)
        has_violation = sequence_data.get("cei_violation", False)
        context.set("sequence_violated", has_violation)

        return StepResult(
            success=True,
            output={"sequence_violated": has_violation, "sequence_data": sequence_data},
        )

    def _handle_analyze_results(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle ANALYZE_RESULTS action - analyze test/fuzz results."""
        test_output = context.get("test_output", "")
        fuzz_report = context.get("fuzz_report", "")

        analysis = {
            "test_passed": "PASS" in test_output.upper() if test_output else None,
            "test_failed": "FAIL" in test_output.upper() if test_output else None,
            "fuzz_found_issue": "FAILED" in fuzz_report.upper() if fuzz_report else None,
        }

        # Update context with analysis results
        for key, value in analysis.items():
            if value is not None:
                context.set(key, value)

        return StepResult(
            success=True,
            output=analysis,
        )

    def _handle_determine_verdict(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle DETERMINE_VERDICT action - make final determination."""
        # This is handled by the executor's _determine_verdict method
        # This handler just ensures the step completes
        return StepResult(
            success=True,
            output={"verdict_determined": True},
        )

    def _handle_compare_patterns(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle COMPARE_PATTERNS action - compare with known patterns."""
        # Get pattern matches from context or bead
        known_patterns = context.get("matched_patterns", [])
        exploit_patterns = context.bead_data.get("exploit_patterns", [])

        similarity_score = 0.0
        if known_patterns and exploit_patterns:
            # Simple overlap calculation
            known_set = set(known_patterns)
            exploit_set = set(exploit_patterns)
            if exploit_set:
                similarity_score = len(known_set & exploit_set) / len(exploit_set)

        return StepResult(
            success=True,
            output={
                "pattern_similarity": similarity_score,
                "matched_patterns": known_patterns,
            },
        )

    def _handle_generate_test(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle GENERATE_TEST action - generate exploit test.

        This is a stub - real implementation would use LLM or templates.
        """
        template = step.template
        if not template:
            return StepResult(
                success=False,
                error="No template specified for test generation",
            )

        # Stub: return placeholder
        return StepResult(
            success=True,
            output={
                "generated": True,
                "template_used": template,
                "test_code": "// Test generation stub - implement with LLM",
            },
        )

    def _handle_generate_invariant(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle GENERATE_INVARIANT action - generate invariant check.

        This is a stub - real implementation would use LLM or templates.
        """
        return StepResult(
            success=True,
            output={
                "generated": True,
                "invariant_code": "// Invariant generation stub",
            },
        )

    def _handle_execute_test(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle EXECUTE_TEST action - run Foundry/Hardhat test.

        This is a stub - real implementation would execute tests.
        """
        if not context.has_tool("foundry") and not context.has_tool("hardhat"):
            return StepResult(
                success=False,
                error="No test framework available",
            )

        # Stub: return placeholder
        return StepResult(
            success=True,
            output={
                "executed": False,
                "reason": "Test execution stub - implement with subprocess",
            },
        )

    def _handle_execute_fuzz(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle EXECUTE_FUZZ action - run Medusa/Echidna fuzzer.

        This is a stub - real implementation would execute fuzzers.
        """
        if not context.has_tool("medusa") and not context.has_tool("echidna"):
            return StepResult(
                success=False,
                error="No fuzzer available",
            )

        # Stub: return placeholder
        return StepResult(
            success=True,
            output={
                "executed": False,
                "reason": "Fuzz execution stub - implement with subprocess",
            },
        )

    def _handle_execute_fork(self, step: GrimoireStep, context: ExecutionContext) -> StepResult:
        """Handle EXECUTE_FORK action - run on mainnet fork.

        This is a stub - real implementation would execute on fork.
        """
        if not context.fork_rpc:
            return StepResult(
                success=False,
                error="No fork RPC configured",
            )

        # Stub: return placeholder
        return StepResult(
            success=True,
            output={
                "executed": False,
                "reason": "Fork execution stub - implement with subprocess",
            },
        )
