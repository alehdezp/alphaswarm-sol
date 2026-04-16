"""ClaudeCodeRunner - Programmatic Claude Code invocation.

This module wraps the Claude Code CLI for automated testing.
Uses `claude -p` (headless mode) with JSON output for parsing.

Key Features:
- Pre-approve tools via --allowedTools (no human confirmation needed)
- Structured output via --output-format json
- Schema validation via --json-schema
- Session continuation via --resume
- Model selection via --model

Limitations:
- Skills (/vrs-*) don't work in headless mode
- Use prompt descriptions instead of skill invocations
- Interactive prompts not supported (use --allowedTools)

Example:
    >>> runner = ClaudeCodeRunner(project_root=Path("."))
    >>> result = runner.run_analysis(
    ...     prompt="Analyze contracts/ for reentrancy",
    ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read", "Glob"],
    ...     json_schema={"type": "object", "properties": {...}}
    ... )
    >>> print(result.structured_output)
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCodeResult:
    """Result from Claude Code execution.

    Attributes:
        raw_output: The raw stdout from the subprocess
        parsed_json: Parsed JSON from stdout, or None if parsing failed
        result_text: The 'result' field from JSON output
        session_id: The session ID for continuation
        structured_output: The structured output (if json_schema was provided)
        return_code: Process return code (0 = success)
        stderr: Any stderr output
        cost_usd: Estimated API cost (if available in output)
        duration_ms: Execution duration in milliseconds

    Example:
        >>> result = runner.run_analysis("Test prompt")
        >>> if result.return_code == 0:
        ...     print(result.result_text)
        ...     if result.structured_output:
        ...         findings = result.structured_output.get("findings", [])
    """

    raw_output: str
    parsed_json: dict[str, Any] | None
    result_text: str
    session_id: str | None
    structured_output: dict[str, Any] | None
    return_code: int
    stderr: str
    cost_usd: float = 0.0
    duration_ms: int = 0
    failure_notes: str = ""  # Evaluator fills this in. Free-text classification of why a scenario failed.

    @property
    def failed(self) -> bool:
        """Check if the evaluator has recorded a failure."""
        return bool(self.failure_notes)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.return_code == 0

    @property
    def has_structured_output(self) -> bool:
        """Check if structured output is available."""
        return self.structured_output is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "raw_output": self.raw_output,
            "parsed_json": self.parsed_json,
            "result_text": self.result_text,
            "session_id": self.session_id,
            "structured_output": self.structured_output,
            "return_code": self.return_code,
            "stderr": self.stderr,
            "cost_usd": self.cost_usd,
            "duration_ms": self.duration_ms,
            "failure_notes": self.failure_notes,
        }


# Default tools for VKG analysis
DEFAULT_VKG_TOOLS = [
    "Bash(uv run alphaswarm*)",
    "Bash(uv run aswarm*)",
    "Read",
    "Glob",
    "Grep",
]

# Standard JSON schema for vulnerability findings
FINDINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "has_vulnerability": {"type": "boolean"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "info"],
                    },
                    "location": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string"},
                },
                "required": ["pattern", "severity", "location", "confidence"],
            },
        },
        "reasoning": {"type": "string"},
    },
    "required": ["has_vulnerability", "findings", "reasoning"],
}


class ClaudeCodeRunner:
    """Programmatic Claude Code invocation for autonomous testing.

    This class wraps the Claude Code CLI to enable fully automated testing
    without human intervention. It handles:
    - Command building with all supported options
    - JSON output parsing
    - Error handling and timeouts
    - Session continuation

    Example:
        >>> runner = ClaudeCodeRunner(project_root=Path("."))
        >>> result = runner.run_analysis(
        ...     prompt="Analyze contracts/ for reentrancy",
        ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read", "Glob"],
        ...     json_schema=FINDINGS_SCHEMA
        ... )
        >>> print(result.structured_output)

    Attributes:
        project_root: Working directory for Claude Code execution
        default_timeout: Default timeout in seconds (default: 300)
        default_model: Default model to use (default: None, uses Claude default)
        claude_command: CLI command name (default: "claude")
    """

    def __init__(
        self,
        project_root: Path,
        default_timeout: int = 300,
        default_model: str | None = None,
        claude_command: str = "claude",
    ):
        """Initialize ClaudeCodeRunner.

        Args:
            project_root: Working directory for execution
            default_timeout: Default timeout in seconds
            default_model: Default model (e.g., "claude-sonnet-4")
            claude_command: CLI command name
        """
        self.project_root = Path(project_root)
        self.default_timeout = default_timeout
        self.default_model = default_model
        self.claude_command = claude_command

    def run_analysis(
        self,
        prompt: str,
        allowed_tools: list[str] | None = None,
        system_prompt: str | None = None,
        append_system_prompt: str | None = None,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        resume_session: str | None = None,
        model: str | None = None,
        max_turns: int | None = None,
    ) -> ClaudeCodeResult:
        """Run Claude Code in headless mode.

        Args:
            prompt: The analysis prompt
            allowed_tools: Tools to pre-approve (no human confirmation needed)
                           Supports wildcards: "Bash(git*)", "Bash(uv run*)"
            system_prompt: Replace system prompt entirely
            append_system_prompt: Append to default system prompt
            json_schema: Schema for structured output validation
            timeout_seconds: Override default timeout
            resume_session: Session ID to continue from
            model: Model to use (default: claude-sonnet-4)
            max_turns: Maximum conversation turns

        Returns:
            ClaudeCodeResult with parsed JSON, structured output, etc.

        Raises:
            RuntimeError: If Claude Code fails with non-zero exit
            TimeoutError: If execution exceeds timeout
        """
        import time

        start_time = time.monotonic()

        cmd = self._build_command(
            prompt=prompt,
            allowed_tools=allowed_tools,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            json_schema=json_schema,
            resume_session=resume_session,
            model=model or self.default_model,
            max_turns=max_turns,
        )

        timeout = timeout_seconds or self.default_timeout

        logger.info(f"Running Claude Code: {' '.join(cmd[:5])}...")
        logger.debug(f"Full command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(f"Claude Code timed out after {timeout}s")
            raise TimeoutError(
                f"Claude Code timed out after {timeout}s: "
                f"{e.stderr if e.stderr else 'No stderr'}"
            ) from e

        duration_ms = int((time.monotonic() - start_time) * 1000)
        parsed_result = self._parse_result(result)
        parsed_result.duration_ms = duration_ms

        if result.returncode != 0:
            logger.warning(
                f"Claude Code returned non-zero exit code: {result.returncode}"
            )
            logger.debug(f"stderr: {result.stderr}")

        return parsed_result

    def _build_command(
        self,
        prompt: str,
        allowed_tools: list[str] | None,
        system_prompt: str | None,
        append_system_prompt: str | None,
        json_schema: dict[str, Any] | None,
        resume_session: str | None,
        model: str | None,
        max_turns: int | None,
    ) -> list[str]:
        """Build the claude CLI command.

        Args:
            prompt: The prompt to send
            allowed_tools: Pre-approved tools
            system_prompt: Custom system prompt
            append_system_prompt: Append to system prompt
            json_schema: Output schema
            resume_session: Session to continue
            model: Model to use
            max_turns: Max conversation turns

        Returns:
            List of command arguments
        """
        cmd = [self.claude_command, "-p", prompt, "--output-format", "json"]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if append_system_prompt:
            cmd.extend(["--append-system-prompt", append_system_prompt])

        if json_schema:
            cmd.extend(["--json-schema", json.dumps(json_schema)])

        if resume_session:
            cmd.extend(["--resume", resume_session])

        if model:
            cmd.extend(["--model", model])

        if max_turns:
            cmd.extend(["--max-turns", str(max_turns)])

        return cmd

    def _parse_result(self, result: subprocess.CompletedProcess[str]) -> ClaudeCodeResult:
        """Parse subprocess result into ClaudeCodeResult.

        Args:
            result: Completed subprocess result

        Returns:
            ClaudeCodeResult with parsed fields
        """
        parsed_json: dict[str, Any] | None = None
        result_text = ""
        session_id: str | None = None
        structured_output: dict[str, Any] | None = None
        cost_usd = 0.0

        if result.stdout:
            try:
                data: dict[str, Any] = json.loads(result.stdout)
                parsed_json = data
                result_text = data.get("result", "")
                session_id = data.get("session_id")
                structured_output = data.get("structured_output")

                # Extract cost if available
                if "cost_usd" in data:
                    cost_usd = float(data.get("cost_usd", 0))
                elif "usage" in data:
                    # Some outputs include usage metrics
                    usage = data.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    # Rough estimate: $3/1M input, $15/1M output for Sonnet
                    cost_usd = (input_tokens * 3 + output_tokens * 15) / 1_000_000

            except json.JSONDecodeError:
                # Non-JSON output, use as raw text
                result_text = result.stdout
                logger.debug("Failed to parse JSON output, using raw text")

        return ClaudeCodeResult(
            raw_output=result.stdout,
            parsed_json=parsed_json,
            result_text=result_text,
            session_id=session_id,
            structured_output=structured_output,
            return_code=result.returncode,
            stderr=result.stderr,
            cost_usd=cost_usd,
        )

    def run_vkg_analysis(
        self,
        contract_path: str,
        vuln_class: str | None = None,
        include_labels: bool = False,
        timeout_seconds: int | None = None,
    ) -> ClaudeCodeResult:
        """Run VKG analysis on a contract.

        This is a convenience method that constructs the appropriate
        prompt and tools for VKG-based vulnerability analysis.

        Args:
            contract_path: Path to contract file or directory
            vuln_class: Specific vulnerability class to focus on (optional)
            include_labels: Whether to use --with-labels for Tier C patterns
            timeout_seconds: Override default timeout

        Returns:
            ClaudeCodeResult with vulnerability findings

        Example:
            >>> result = runner.run_vkg_analysis(
            ...     "contracts/Vault.sol",
            ...     vuln_class="reentrancy",
            ...     include_labels=True
            ... )
            >>> if result.structured_output:
            ...     for finding in result.structured_output.get("findings", []):
            ...         print(f"{finding['pattern']}: {finding['severity']}")
        """
        vuln_focus = f"Focus on: {vuln_class}" if vuln_class else "Check all vulnerability classes."

        prompt = f"""Analyze {contract_path} for security vulnerabilities using the VKG.

Steps:
1. Build the knowledge graph: uv run alphaswarm build-kg {contract_path}{' --with-labels' if include_labels else ''}
2. Query for suspicious patterns using VQL
3. Verify findings with semantic operations

{vuln_focus}

Return structured findings with:
- has_vulnerability: boolean
- findings: array of {{pattern, severity, location, confidence, reasoning}}
- reasoning: explanation of analysis approach
"""

        # Build command pattern for allowed tools
        build_cmd = "uv run alphaswarm build-kg*"
        if include_labels:
            build_cmd = "uv run alphaswarm build-kg* --with-labels*"

        return self.run_analysis(
            prompt=prompt,
            allowed_tools=[
                f"Bash({build_cmd})",
                "Bash(uv run alphaswarm query*)",
                "Bash(uv run aswarm*)",
                "Read",
                "Glob",
                "Grep",
            ],
            json_schema=FINDINGS_SCHEMA,
            timeout_seconds=timeout_seconds,
        )

    def continue_session(
        self,
        session_id: str,
        prompt: str,
        allowed_tools: list[str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ClaudeCodeResult:
        """Continue an existing session.

        Args:
            session_id: Session ID from previous result
            prompt: Follow-up prompt
            allowed_tools: Tools to pre-approve
            timeout_seconds: Override default timeout

        Returns:
            ClaudeCodeResult from continued session
        """
        return self.run_analysis(
            prompt=prompt,
            allowed_tools=allowed_tools,
            resume_session=session_id,
            timeout_seconds=timeout_seconds,
        )

    def check_available(self) -> bool:
        """Check if Claude Code CLI is available.

        Returns:
            True if claude command is available, False otherwise
        """
        try:
            result = subprocess.run(
                [self.claude_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_version(self) -> str | None:
        """Get Claude Code CLI version.

        Returns:
            Version string, or None if not available
        """
        try:
            result = subprocess.run(
                [self.claude_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
