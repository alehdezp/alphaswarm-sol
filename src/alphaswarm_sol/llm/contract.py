"""
LLM Prompt Contract Enforcement (Task 11.8)

Establishes formal input/output contract for LLM interactions:
1. Input schema validation
2. Output schema validation with retry
3. Safety invariants
4. Audit trail logging
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar
from enum import Enum

from .validate import (
    OutputValidator,
    ValidationResult,
    LLMVerdict,
    Verdict,
    VERDICT_SCHEMA,
)
from .sanitize import (
    CodeSanitizer,
    SanitizationResult,
    InjectionRisk,
)


logger = logging.getLogger(__name__)


class ContractViolation(Exception):
    """Raised when a prompt contract is violated."""
    pass


class PromptType(Enum):
    """Types of LLM prompts."""
    VULNERABILITY_ANALYSIS = "vulnerability_analysis"
    FALSE_POSITIVE_CHECK = "false_positive_check"
    SEVERITY_ASSESSMENT = "severity_assessment"
    CODE_EXPLANATION = "code_explanation"


@dataclass
class PromptInput:
    """Validated input for LLM prompt."""
    prompt_type: PromptType
    code_context: str
    finding_id: str
    pattern_id: str
    evidence: List[str] = field(default_factory=list)
    task_description: str = ""
    max_tokens: int = 4096
    temperature: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prompt_type": self.prompt_type.value,
            "code_context_length": len(self.code_context),
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "evidence_count": len(self.evidence),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


@dataclass
class ContractAuditEntry:
    """Audit entry for prompt contract enforcement."""
    timestamp: datetime
    prompt_type: PromptType
    finding_id: str
    input_sanitized: bool
    injection_risk: InjectionRisk
    output_valid: bool
    retry_count: int
    final_verdict: Optional[Verdict]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "prompt_type": self.prompt_type.value,
            "finding_id": self.finding_id,
            "input_sanitized": self.input_sanitized,
            "injection_risk": self.injection_risk.name,
            "output_valid": self.output_valid,
            "retry_count": self.retry_count,
            "final_verdict": self.final_verdict.value if self.final_verdict else None,
            "error": self.error,
        }


class PromptContract:
    """
    Enforces prompt contract for LLM interactions.

    Key responsibilities:
    1. Validate and sanitize inputs
    2. Validate outputs against schema
    3. Retry on invalid responses
    4. Maintain audit trail
    5. Enforce safety invariants
    """

    # Default schema for vulnerability analysis
    DEFAULT_SCHEMA = VERDICT_SCHEMA

    def __init__(
        self,
        max_retries: int = 3,
        strict_mode: bool = True,
        audit_log_path: Optional[Path] = None,
    ):
        """
        Initialize prompt contract.

        Args:
            max_retries: Maximum retry attempts for invalid responses
            strict_mode: If True, raise on contract violations
            audit_log_path: Path to write audit log (optional)
        """
        self.max_retries = max_retries
        self.strict_mode = strict_mode
        self.audit_log_path = audit_log_path
        self._sanitizer = CodeSanitizer()
        self._validator = OutputValidator(strict_mode=False)
        self._audit_log: List[ContractAuditEntry] = []

    def validate_input(self, prompt_input: PromptInput) -> SanitizationResult:
        """
        Validate and sanitize input before sending to LLM.

        Args:
            prompt_input: The prompt input to validate

        Returns:
            SanitizationResult with sanitized content

        Raises:
            ContractViolation: If input fails safety checks in strict mode
        """
        result = self._sanitizer.sanitize(
            prompt_input.code_context,
            context=prompt_input.task_description,
        )

        if self.strict_mode and result.injection_risk == InjectionRisk.HIGH:
            raise ContractViolation(
                f"High injection risk detected: {result.detected_patterns}"
            )

        return result

    def validate_output(self, response: str) -> ValidationResult:
        """
        Validate LLM response against schema.

        Args:
            response: Raw LLM response string

        Returns:
            ValidationResult with parsed data if valid
        """
        return self._validator.validate_verdict(response)

    async def execute_with_contract(
        self,
        prompt_input: PromptInput,
        llm_call: Callable[[str], Any],
        build_prompt: Callable[[PromptInput, str], str],
    ) -> LLMVerdict:
        """
        Execute LLM call with full contract enforcement.

        This method:
        1. Validates and sanitizes input
        2. Calls LLM
        3. Validates output
        4. Retries on invalid output
        5. Logs audit trail

        Args:
            prompt_input: The prompt input
            llm_call: Async function to call LLM
            build_prompt: Function to build prompt from input

        Returns:
            LLMVerdict with validated response

        Raises:
            ContractViolation: If contract cannot be satisfied after retries
        """
        # Step 1: Validate and sanitize input
        sanitized = self.validate_input(prompt_input)

        # Step 2: Build prompt with sanitized content
        prompt = build_prompt(prompt_input, sanitized.sanitized_content)

        # Step 3: Call LLM with retry on invalid output
        retry_count = 0
        last_error = None
        verdict = None

        while retry_count < self.max_retries:
            try:
                response = await llm_call(prompt)
                result = self.validate_output(response)

                if result.valid:
                    verdict = self._validator.parse_verdict(response)
                    break
                else:
                    last_error = "; ".join(e.message for e in result.errors)
                    retry_count += 1
                    logger.warning(
                        f"Invalid LLM response (attempt {retry_count}): {last_error}"
                    )
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.warning(f"LLM call failed (attempt {retry_count}): {e}")

        # Step 4: Log audit entry
        audit_entry = ContractAuditEntry(
            timestamp=datetime.now(),
            prompt_type=prompt_input.prompt_type,
            finding_id=prompt_input.finding_id,
            input_sanitized=True,
            injection_risk=sanitized.injection_risk,
            output_valid=verdict is not None,
            retry_count=retry_count,
            final_verdict=verdict.verdict if verdict else None,
            error=last_error if verdict is None else None,
        )
        self._audit_log.append(audit_entry)
        self._write_audit_log(audit_entry)

        # Step 5: Handle failure
        if verdict is None:
            if self.strict_mode:
                raise ContractViolation(
                    f"Failed to get valid response after {self.max_retries} attempts: {last_error}"
                )
            # Return ERROR verdict in non-strict mode
            verdict = LLMVerdict(
                verdict=Verdict.ERROR,
                confidence=0,
                reasoning=f"Contract violation: {last_error}",
                evidence=[],
            )

        return verdict

    def get_audit_log(self) -> List[ContractAuditEntry]:
        """Get the audit log."""
        return self._audit_log.copy()

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of audit log."""
        if not self._audit_log:
            return {"total_calls": 0}

        total = len(self._audit_log)
        valid = sum(1 for e in self._audit_log if e.output_valid)
        retried = sum(1 for e in self._audit_log if e.retry_count > 0)
        high_risk = sum(
            1 for e in self._audit_log
            if e.injection_risk == InjectionRisk.HIGH
        )

        verdict_counts = {}
        for entry in self._audit_log:
            if entry.final_verdict:
                v = entry.final_verdict.value
                verdict_counts[v] = verdict_counts.get(v, 0) + 1

        return {
            "total_calls": total,
            "valid_responses": valid,
            "valid_rate": valid / total if total > 0 else 0,
            "retried_calls": retried,
            "high_risk_inputs": high_risk,
            "verdict_distribution": verdict_counts,
        }

    def clear_audit_log(self):
        """Clear the audit log."""
        self._audit_log = []

    def _write_audit_log(self, entry: ContractAuditEntry):
        """Write audit entry to file if path configured."""
        if self.audit_log_path:
            try:
                self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.audit_log_path, "a") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            except Exception as e:
                logger.warning(f"Failed to write audit log: {e}")


# Standard prompt templates that conform to contract
PROMPT_TEMPLATES = {
    PromptType.VULNERABILITY_ANALYSIS: """
You are analyzing a potential vulnerability in Solidity code.

## Finding
Pattern: {pattern_id}
Finding ID: {finding_id}
Description: {task_description}

## Code Context
{code_context}

## Evidence
{evidence}

## Your Task
Analyze whether this is a real vulnerability or false positive.

## Response Format (REQUIRED)
Respond with ONLY a JSON object in this exact format:
{{
  "verdict": "VULNERABLE" | "SAFE" | "UNCERTAIN",
  "confidence": 0-100,
  "reasoning": "Your detailed analysis explaining why",
  "evidence": ["specific code reference", "another reference"]
}}
""",

    PromptType.FALSE_POSITIVE_CHECK: """
You are reviewing a flagged vulnerability to check for false positives.

## Finding
{task_description}

## Code Context
{code_context}

## Questions to Answer
1. Are there guards or checks that prevent exploitation?
2. Is the flagged pattern actually safe in this context?
3. What specific code behavior makes this safe or vulnerable?

## Response Format (REQUIRED)
Respond with ONLY a JSON object:
{{
  "verdict": "VULNERABLE" | "SAFE" | "UNCERTAIN",
  "confidence": 0-100,
  "reasoning": "Detailed explanation",
  "evidence": ["specific references"]
}}
""",

    PromptType.SEVERITY_ASSESSMENT: """
You are assessing the severity of a confirmed vulnerability.

## Vulnerability
{task_description}

## Code Context
{code_context}

## Assess
- Impact: What can an attacker do?
- Likelihood: How easy to exploit?
- Affected assets: What's at risk?

## Response Format (REQUIRED)
Respond with ONLY a JSON object:
{{
  "verdict": "VULNERABLE",
  "confidence": 0-100,
  "reasoning": "Severity assessment with impact analysis",
  "evidence": ["specific attack scenario"]
}}
""",
}


def get_prompt_template(prompt_type: PromptType) -> str:
    """Get standard prompt template for a prompt type."""
    return PROMPT_TEMPLATES.get(prompt_type, PROMPT_TEMPLATES[PromptType.VULNERABILITY_ANALYSIS])


def build_standard_prompt(prompt_input: PromptInput, sanitized_code: str) -> str:
    """
    Build a standard prompt from input.

    Args:
        prompt_input: The prompt input
        sanitized_code: Sanitized code context

    Returns:
        Formatted prompt string
    """
    template = get_prompt_template(prompt_input.prompt_type)
    evidence_str = "\n".join(f"- {e}" for e in prompt_input.evidence) if prompt_input.evidence else "No specific evidence provided."

    return template.format(
        pattern_id=prompt_input.pattern_id,
        finding_id=prompt_input.finding_id,
        task_description=prompt_input.task_description,
        code_context=sanitized_code,
        evidence=evidence_str,
    )


def create_contract(
    max_retries: int = 3,
    strict_mode: bool = True,
    audit_log_path: Optional[Path] = None,
) -> PromptContract:
    """
    Factory function to create a prompt contract.

    Args:
        max_retries: Maximum retry attempts
        strict_mode: Whether to raise on violations
        audit_log_path: Path for audit log

    Returns:
        Configured PromptContract
    """
    return PromptContract(
        max_retries=max_retries,
        strict_mode=strict_mode,
        audit_log_path=audit_log_path,
    )
