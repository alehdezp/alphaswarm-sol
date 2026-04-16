"""Investigation Executor for LLM Investigation Patterns.

Task 13.11: Execute investigation patterns using graph, LSP, PPR, and LLM.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol

from alphaswarm_sol.investigation.schema import (
    InvestigationAction,
    InvestigationPattern,
    InvestigationResult,
    InvestigationStep,
    InvestigationVerdict,
    StepResult,
)

logger = logging.getLogger(__name__)


class GraphQueryProtocol(Protocol):
    """Protocol for graph query interface."""

    def query(self, query_str: str) -> Any: ...


class LSPClientProtocol(Protocol):
    """Protocol for LSP client interface."""

    async def find_references(self, symbol: str, file_path: str) -> Any: ...
    async def go_to_definition(self, symbol: str, file_path: str) -> Any: ...
    async def incoming_calls(self, symbol: str, file_path: str) -> Any: ...
    async def outgoing_calls(self, symbol: str, file_path: str) -> Any: ...


class PPREngineProtocol(Protocol):
    """Protocol for PPR engine interface."""

    def expand(self, seed_node: str, max_depth: int) -> Any: ...


class LLMProviderProtocol(Protocol):
    """Protocol for LLM provider interface."""

    async def analyze(self, context: str, prompt: str) -> Dict[str, Any]: ...


class KnowledgeManagerProtocol(Protocol):
    """Protocol for knowledge manager interface."""

    def get_for_pattern(self, pattern_id: str) -> Optional[Any]: ...


@dataclass
class InvestigationContext:
    """Context for investigation execution."""

    # Target information
    function_name: str = ""
    contract_name: str = ""
    file_path: str = ""

    # Graph node data
    node_properties: Dict[str, Any] = field(default_factory=dict)
    graph_data: Dict[str, Any] = field(default_factory=dict)

    # Source code
    function_code: str = ""
    contract_code: str = ""

    # Custom context variables
    variables: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get context value by key."""
        # Check direct attributes first
        if hasattr(self, key) and not key.startswith("_"):
            val = getattr(self, key)
            if val is not None:
                return val

        # Check node_properties
        if key in self.node_properties:
            return self.node_properties[key]

        # Check variables
        if key in self.variables:
            return self.variables[key]

        return default

    def set(self, key: str, value: Any) -> None:
        """Set context variable."""
        self.variables[key] = value

    def has_property(self, property_name: str, expected_value: Any = True) -> bool:
        """Check if node has a property with expected value."""
        actual = self.node_properties.get(property_name)
        if expected_value is True:
            return bool(actual)
        return actual == expected_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for substitution."""
        result = {
            "function_name": self.function_name,
            "contract_name": self.contract_name,
            "file_path": self.file_path,
            "function_code": self.function_code,
            "contract_code": self.contract_code,
        }
        result.update(self.node_properties)
        result.update(self.variables)
        return result


# Type alias for step action handlers
ActionHandler = Callable[[InvestigationStep, InvestigationContext, List[StepResult]], Any]


class InvestigationExecutor:
    """Execute LLM investigation patterns.

    The executor:
    1. Checks trigger conditions against node properties
    2. Executes each investigation step in sequence
    3. Gets LLM interpretation of step results
    4. Synthesizes final verdict from all evidence

    Example:
        executor = InvestigationExecutor(
            graph=knowledge_graph,
            lsp_client=lsp,
            ppr_engine=ppr,
            llm_provider=llm,
        )

        result = await executor.execute(
            pattern=investigation_pattern,
            context=InvestigationContext(
                function_name="withdraw",
                contract_name="Vault",
                node_properties={"writes_user_balance": True},
            ),
        )
    """

    def __init__(
        self,
        graph: Optional[GraphQueryProtocol] = None,
        lsp_client: Optional[LSPClientProtocol] = None,
        ppr_engine: Optional[PPREngineProtocol] = None,
        llm_provider: Optional[LLMProviderProtocol] = None,
        knowledge_manager: Optional[KnowledgeManagerProtocol] = None,
    ) -> None:
        """Initialize executor with optional dependencies.

        Args:
            graph: Graph query interface
            lsp_client: LSP client for code navigation
            ppr_engine: PPR engine for context expansion
            llm_provider: LLM provider for reasoning
            knowledge_manager: Knowledge manager for context
        """
        self.graph = graph
        self.lsp = lsp_client
        self.ppr = ppr_engine
        self.llm = llm_provider
        self.knowledge = knowledge_manager

        # Custom action handlers
        self._action_handlers: Dict[InvestigationAction, ActionHandler] = {}

    def register_action_handler(
        self,
        action: InvestigationAction,
        handler: ActionHandler,
    ) -> None:
        """Register a custom handler for an action type.

        Args:
            action: Action type to handle
            handler: Handler function
        """
        self._action_handlers[action] = handler

    async def execute(
        self,
        pattern: InvestigationPattern,
        context: InvestigationContext,
    ) -> InvestigationResult:
        """Execute an investigation pattern.

        Args:
            pattern: Investigation pattern to execute
            context: Context for execution

        Returns:
            InvestigationResult with verdict and evidence
        """
        start_time = time.time()
        result = InvestigationResult(
            pattern_id=pattern.id,
            pattern_name=pattern.name,
            started_at=datetime.utcnow().isoformat(),
        )

        # Check trigger conditions
        if not self._check_triggers(pattern, context):
            result.verdict = InvestigationVerdict.SKIPPED
            result.confidence = 100
            result.evidence = ["Trigger conditions not met"]
            result.completed_at = datetime.utcnow().isoformat()
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        # Execute investigation steps
        step_results: List[StepResult] = []
        accumulated_evidence: List[str] = []
        total_tokens = 0

        for step in pattern.investigation.steps:
            step_start = time.time()

            try:
                step_result = await self._execute_step(
                    step=step,
                    context=context,
                    previous_results=step_results,
                    pattern=pattern,
                )
                step_result.duration_ms = int((time.time() - step_start) * 1000)
                step_results.append(step_result)
                accumulated_evidence.extend(step_result.evidence)
                total_tokens += step_result.tokens_used

            except Exception as e:
                logger.error(f"Step {step.id} failed: {e}")
                if not step.optional:
                    step_results.append(StepResult(
                        step_id=step.id,
                        action=step.action,
                        success=False,
                        error=str(e),
                        duration_ms=int((time.time() - step_start) * 1000),
                    ))

        result.step_results = step_results

        # Synthesize verdict
        try:
            verdict_result = await self._synthesize_verdict(
                pattern=pattern,
                step_results=step_results,
                context=context,
            )
            result.verdict = verdict_result.get("verdict", InvestigationVerdict.UNCERTAIN)
            result.confidence = verdict_result.get("confidence", 0)
            result.attack_path = verdict_result.get("attack_path")
            result.evidence = accumulated_evidence + verdict_result.get("evidence", [])
            result.recommendation = verdict_result.get("recommendation", "")
            total_tokens += verdict_result.get("tokens_used", 0)
        except Exception as e:
            logger.error(f"Verdict synthesis failed: {e}")
            result.verdict = InvestigationVerdict.UNCERTAIN
            result.confidence = 0
            result.evidence = accumulated_evidence + [f"Verdict synthesis failed: {e}"]

        result.total_tokens = total_tokens
        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = int((time.time() - start_time) * 1000)
        result.context_used = context.to_dict()

        return result

    def _check_triggers(
        self,
        pattern: InvestigationPattern,
        context: InvestigationContext,
    ) -> bool:
        """Check if trigger conditions are met.

        Args:
            pattern: Investigation pattern
            context: Execution context

        Returns:
            True if triggers are satisfied
        """
        trigger = pattern.trigger
        if not trigger.graph_signals:
            # No signals = always trigger
            return True

        results = []
        for signal in trigger.graph_signals:
            property_name = signal.property
            expected_value = signal.value

            if property_name:
                has_property = context.has_property(property_name, expected_value)
                results.append(has_property)

        if not results:
            return True

        if trigger.require_all:
            return all(results)
        return any(results)

    async def _execute_step(
        self,
        step: InvestigationStep,
        context: InvestigationContext,
        previous_results: List[StepResult],
        pattern: InvestigationPattern,
    ) -> StepResult:
        """Execute a single investigation step.

        Args:
            step: Step to execute
            context: Execution context
            previous_results: Results from previous steps
            pattern: Parent pattern

        Returns:
            StepResult from execution
        """
        # Check for custom handler
        if step.action in self._action_handlers:
            handler = self._action_handlers[step.action]
            raw_output = await self._run_async(
                handler, step, context, previous_results
            )
        else:
            # Use built-in handlers
            raw_output = await self._execute_builtin_action(
                step, context, previous_results
            )

        # Get LLM interpretation of results
        interpretation = await self._interpret_results(
            step=step,
            raw_output=raw_output,
            context=context,
        )

        return StepResult(
            step_id=step.id,
            action=step.action,
            success=True,
            raw_output=raw_output,
            llm_interpretation=interpretation.get("interpretation", ""),
            evidence=interpretation.get("evidence", []),
            tokens_used=interpretation.get("tokens_used", 0),
        )

    async def _execute_builtin_action(
        self,
        step: InvestigationStep,
        context: InvestigationContext,
        previous_results: List[StepResult],
    ) -> Any:
        """Execute a built-in action.

        Args:
            step: Step to execute
            context: Execution context
            previous_results: Results from previous steps

        Returns:
            Raw output from action
        """
        action = step.action
        params = self._substitute_params(step.params, context, previous_results)

        if action == InvestigationAction.EXPLORE_GRAPH:
            return await self._action_explore_graph(params, context)
        elif action == InvestigationAction.LSP_REFERENCES:
            return await self._action_lsp_references(params, context)
        elif action == InvestigationAction.LSP_DEFINITION:
            return await self._action_lsp_definition(params, context)
        elif action == InvestigationAction.LSP_CALL_HIERARCHY:
            return await self._action_lsp_call_hierarchy(params, context)
        elif action == InvestigationAction.PPR_EXPAND:
            return await self._action_ppr_expand(params, context)
        elif action == InvestigationAction.READ_CODE:
            return await self._action_read_code(params, context)
        elif action == InvestigationAction.REASON:
            return await self._action_reason(step, context, previous_results)
        elif action == InvestigationAction.SYNTHESIZE:
            return await self._action_synthesize(step, context, previous_results)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _action_explore_graph(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Execute graph exploration action."""
        if not self.graph:
            return {"error": "Graph not available", "params": params}

        query = params.get("graph_query", "")
        query = self._substitute_variables(query, context)

        try:
            return self.graph.query(query)
        except Exception as e:
            return {"error": str(e), "query": query}

    async def _action_lsp_references(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Find references using LSP."""
        if not self.lsp:
            return {"error": "LSP not available", "params": params}

        target = params.get("target", "")
        target = self._substitute_variables(target, context)
        file_path = context.file_path

        try:
            return await self.lsp.find_references(target, file_path)
        except Exception as e:
            return {"error": str(e), "target": target}

    async def _action_lsp_definition(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Go to definition using LSP."""
        if not self.lsp:
            return {"error": "LSP not available", "params": params}

        target = params.get("target", "")
        target = self._substitute_variables(target, context)
        file_path = context.file_path

        try:
            return await self.lsp.go_to_definition(target, file_path)
        except Exception as e:
            return {"error": str(e), "target": target}

    async def _action_lsp_call_hierarchy(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Get call hierarchy using LSP."""
        if not self.lsp:
            return {"error": "LSP not available", "params": params}

        target = params.get("target", "")
        target = self._substitute_variables(target, context)
        file_path = context.file_path
        direction = params.get("direction", "incoming")

        try:
            if direction == "outgoing":
                return await self.lsp.outgoing_calls(target, file_path)
            return await self.lsp.incoming_calls(target, file_path)
        except Exception as e:
            return {"error": str(e), "target": target}

    async def _action_ppr_expand(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Expand context using PPR."""
        if not self.ppr:
            return {"error": "PPR not available", "params": params}

        seed = params.get("seed", "")
        seed = self._substitute_variables(seed, context)
        depth = params.get("depth", 2)

        try:
            return self.ppr.expand(seed_node=seed, max_depth=depth)
        except Exception as e:
            return {"error": str(e), "seed": seed}

    async def _action_read_code(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
    ) -> Any:
        """Read code from file."""
        target = params.get("target", params.get("file_path", ""))
        target = self._substitute_variables(target, context)

        # If we have the code in context, return it
        if target == context.function_name and context.function_code:
            return {
                "code": context.function_code,
                "path": context.file_path,
                "function": context.function_name,
            }
        if context.contract_code:
            return {
                "code": context.contract_code,
                "path": context.file_path,
                "contract": context.contract_name,
            }

        return {
            "code": f"// Code for {target} not available in context",
            "path": target,
        }

    async def _action_reason(
        self,
        step: InvestigationStep,
        context: InvestigationContext,
        previous_results: List[StepResult],
    ) -> Any:
        """Execute reasoning step with LLM."""
        if not self.llm:
            return {"reasoning": "LLM not available", "params": step.params}

        prompt = step.params.get("prompt", "")
        prompt = self._substitute_variables(prompt, context)

        # Substitute previous step results
        for prev in previous_results:
            placeholder = f"{{step_{prev.step_id}_results}}"
            prompt = prompt.replace(placeholder, prev.llm_interpretation)

        try:
            response = await self.llm.analyze(context="", prompt=prompt)
            return response
        except Exception as e:
            return {"error": str(e), "prompt": prompt[:100]}

    async def _action_synthesize(
        self,
        step: InvestigationStep,
        context: InvestigationContext,
        previous_results: List[StepResult],
    ) -> Any:
        """Synthesize multiple findings."""
        if not self.llm:
            return {"synthesis": "LLM not available"}

        # Build synthesis prompt from all previous results
        findings = "\n".join([
            f"Step {r.step_id} ({r.action.value}): {r.llm_interpretation}"
            for r in previous_results
        ])

        prompt = f"""
        Synthesize the following investigation findings:

        {findings}

        Provide a coherent summary of what was discovered.
        """

        try:
            response = await self.llm.analyze(context="", prompt=prompt)
            return response
        except Exception as e:
            return {"error": str(e)}

    async def _interpret_results(
        self,
        step: InvestigationStep,
        raw_output: Any,
        context: InvestigationContext,
    ) -> Dict[str, Any]:
        """Get LLM interpretation of step results.

        Args:
            step: Step that was executed
            raw_output: Raw output from action
            context: Execution context

        Returns:
            Dictionary with interpretation, evidence, tokens_used
        """
        if not self.llm:
            # Without LLM, provide basic interpretation
            return {
                "interpretation": str(raw_output)[:500],
                "evidence": self._extract_evidence_basic(raw_output),
                "tokens_used": 0,
            }

        interpretation_guide = step.interpretation or "Analyze the results."

        interpretation_prompt = f"""
        Step: {step.description}

        Raw Output:
        {self._format_output(raw_output)}

        Interpretation Guide:
        {interpretation_guide}

        Provide:
        1. A concise interpretation of what the output shows (2-3 sentences)
        2. Any evidence of vulnerability or safety (bullet points)
        3. Key findings relevant to the investigation

        Format as JSON:
        {{
            "interpretation": "...",
            "evidence": ["...", "..."],
            "key_findings": ["...", "..."]
        }}
        """

        try:
            response = await self.llm.analyze(context="", prompt=interpretation_prompt)
            content = response.get("content", "{}")

            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                return {
                    "interpretation": parsed.get("interpretation", content),
                    "evidence": parsed.get("evidence", []) + parsed.get("key_findings", []),
                    "tokens_used": response.get("tokens_used", 0),
                }
            except json.JSONDecodeError:
                return {
                    "interpretation": content,
                    "evidence": self._extract_evidence_basic(content),
                    "tokens_used": response.get("tokens_used", 0),
                }

        except Exception as e:
            logger.error(f"Interpretation failed: {e}")
            return {
                "interpretation": f"Failed to interpret: {e}",
                "evidence": [],
                "tokens_used": 0,
            }

    async def _synthesize_verdict(
        self,
        pattern: InvestigationPattern,
        step_results: List[StepResult],
        context: InvestigationContext,
    ) -> Dict[str, Any]:
        """Synthesize final verdict from all step results.

        Args:
            pattern: Investigation pattern
            step_results: Results from all steps
            context: Execution context

        Returns:
            Dictionary with verdict, confidence, attack_path, evidence, recommendation
        """
        if not self.llm:
            # Without LLM, provide basic verdict
            return self._basic_verdict(step_results)

        # Get relevant knowledge
        knowledge_block = ""
        if self.knowledge:
            kb = self.knowledge.get_for_pattern(pattern.id)
            if kb:
                knowledge_block = getattr(kb, "content", str(kb))

        # Build step results summary
        steps_summary = "\n".join([
            f"Step {r.step_id} ({r.action.value}):\n{r.llm_interpretation}"
            for r in step_results
            if r.success
        ])

        criteria = pattern.investigation.verdict_criteria

        # Build knowledge section if available
        knowledge_section = ""
        if knowledge_block:
            knowledge_section = f"## Relevant Knowledge:\n{knowledge_block}"

        synthesis_prompt = f"""
        ## Investigation: {pattern.name}
        ## Hypothesis: {pattern.investigation.hypothesis}

        ## Step Results:
        {steps_summary}

        ## Verdict Criteria:
        VULNERABLE if: {criteria.vulnerable}
        LIKELY_VULNERABLE if: {criteria.likely_vulnerable}
        UNCERTAIN if: {criteria.uncertain}
        LIKELY_SAFE if: {criteria.likely_safe}
        SAFE if: {criteria.safe}

        {knowledge_section}

        Based on all the above, provide your verdict as JSON:
        {{
            "verdict": "vulnerable" | "likely_vulnerable" | "uncertain" | "likely_safe" | "safe",
            "confidence": 0-100,
            "attack_path": "Description of attack sequence if vulnerable, null otherwise",
            "evidence": ["List of supporting evidence"],
            "recommendation": "Fix if vulnerable, otherwise why safe"
        }}
        """

        try:
            response = await self.llm.analyze(context="", prompt=synthesis_prompt)
            content = response.get("content", "{}")

            # Parse JSON response
            try:
                parsed = json.loads(content)
                verdict_str = parsed.get("verdict", "uncertain").lower()
                try:
                    verdict = InvestigationVerdict(verdict_str)
                except ValueError:
                    verdict = InvestigationVerdict.UNCERTAIN

                return {
                    "verdict": verdict,
                    "confidence": int(parsed.get("confidence", 0)),
                    "attack_path": parsed.get("attack_path"),
                    "evidence": parsed.get("evidence", []),
                    "recommendation": parsed.get("recommendation", ""),
                    "tokens_used": response.get("tokens_used", 0),
                }
            except json.JSONDecodeError:
                return {
                    "verdict": InvestigationVerdict.UNCERTAIN,
                    "confidence": 0,
                    "evidence": [f"Failed to parse verdict: {content[:100]}"],
                    "tokens_used": response.get("tokens_used", 0),
                }

        except Exception as e:
            logger.error(f"Verdict synthesis failed: {e}")
            return self._basic_verdict(step_results)

    def _basic_verdict(self, step_results: List[StepResult]) -> Dict[str, Any]:
        """Generate basic verdict without LLM."""
        # Check for any evidence of vulnerability
        all_evidence = []
        for r in step_results:
            all_evidence.extend(r.evidence)

        vuln_keywords = ["vulnerable", "vulnerability", "attack", "exploit", "risk"]
        safe_keywords = ["safe", "protected", "guarded", "checked"]

        vuln_score = sum(
            1 for e in all_evidence
            if any(k in e.lower() for k in vuln_keywords)
        )
        safe_score = sum(
            1 for e in all_evidence
            if any(k in e.lower() for k in safe_keywords)
        )

        if vuln_score > safe_score:
            verdict = InvestigationVerdict.LIKELY_VULNERABLE
            confidence = min(70, 30 + vuln_score * 10)
        elif safe_score > vuln_score:
            verdict = InvestigationVerdict.LIKELY_SAFE
            confidence = min(70, 30 + safe_score * 10)
        else:
            verdict = InvestigationVerdict.UNCERTAIN
            confidence = 30

        return {
            "verdict": verdict,
            "confidence": confidence,
            "evidence": all_evidence,
            "recommendation": "Manual review recommended - LLM not available",
            "tokens_used": 0,
        }

    def _substitute_variables(self, text: str, context: InvestigationContext) -> str:
        """Substitute ${variable} placeholders with context values."""
        context_dict = context.to_dict()

        # Find all ${var} patterns
        pattern = r"\$\{(\w+)\}"
        matches = re.findall(pattern, text)

        for var in matches:
            if var in context_dict:
                text = text.replace(f"${{{var}}}", str(context_dict[var]))

        return text

    def _substitute_params(
        self,
        params: Dict[str, Any],
        context: InvestigationContext,
        previous_results: List[StepResult],
    ) -> Dict[str, Any]:
        """Substitute variables in params dict."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                value = self._substitute_variables(value, context)
                # Substitute step results
                for prev in previous_results:
                    value = value.replace(
                        f"{{step_{prev.step_id}_results}}",
                        prev.llm_interpretation
                    )
            result[key] = value
        return result

    def _format_output(self, output: Any) -> str:
        """Format output for LLM consumption."""
        if isinstance(output, dict):
            return json.dumps(output, indent=2, default=str)[:2000]
        if isinstance(output, list):
            return json.dumps(output[:20], indent=2, default=str)[:2000]
        return str(output)[:2000]

    def _extract_evidence_basic(self, output: Any) -> List[str]:
        """Extract evidence from output without LLM."""
        evidence = []
        text = str(output)

        # Look for bullet points or numbered items
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "")) or (
                len(line) > 2 and line[0].isdigit() and line[1] in ".)"
            ):
                cleaned = line.lstrip("-*• 0123456789.)")
                if cleaned:
                    evidence.append(cleaned[:200])

        return evidence[:10]  # Limit to 10

    async def _run_async(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Run a function, handling both sync and async."""
        import asyncio
        import inspect

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
