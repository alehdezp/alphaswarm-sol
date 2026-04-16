"""
LLM Output Validation

Validates LLM responses against expected schemas:
1. Structured JSON parsing
2. Schema validation
3. Verdict validation
4. Evidence reference checking
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar
from enum import Enum


class Verdict(Enum):
    """Valid verdicts for vulnerability analysis."""
    VULNERABLE = "VULNERABLE"
    SAFE = "SAFE"
    UNCERTAIN = "UNCERTAIN"
    ERROR = "ERROR"


@dataclass
class ValidationError:
    """Details of a validation error."""
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of output validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    parsed_data: Optional[Dict[str, Any]] = None
    raw_response: str = ""

    def add_error(self, field: str, message: str, value: Any = None):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, value))
        self.valid = False


@dataclass
class LLMVerdict:
    """Validated LLM verdict response."""
    verdict: Verdict
    confidence: int  # 0-100
    reasoning: str
    evidence: List[str]
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
        }


# JSON Schema for LLM verdict response
VERDICT_SCHEMA = {
    "type": "object",
    "required": ["verdict", "confidence", "reasoning", "evidence"],
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["VULNERABLE", "SAFE", "UNCERTAIN"]
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        },
        "reasoning": {
            "type": "string",
            "minLength": 10
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}


class OutputValidator:
    """Validates LLM outputs against expected schemas."""

    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.

        Args:
            strict_mode: If True, fail on any schema violation
        """
        self.strict_mode = strict_mode

    def validate_verdict(self, response: str) -> ValidationResult:
        """
        Validate an LLM verdict response.

        Args:
            response: Raw LLM response string

        Returns:
            ValidationResult with parsed verdict if valid
        """
        result = ValidationResult(valid=True, raw_response=response)

        # Try to extract JSON from response
        json_data = self._extract_json(response)
        if json_data is None:
            result.add_error("response", "Could not parse JSON from response")
            return result

        result.parsed_data = json_data

        # Validate required fields
        required_fields = ["verdict", "confidence", "reasoning", "evidence"]
        for field in required_fields:
            if field not in json_data:
                result.add_error(field, f"Missing required field: {field}")

        if not result.valid:
            return result

        # Validate verdict value
        verdict_str = json_data.get("verdict", "").upper()
        valid_verdicts = {"VULNERABLE", "SAFE", "UNCERTAIN"}
        if verdict_str not in valid_verdicts:
            result.add_error("verdict", f"Invalid verdict: {verdict_str}", verdict_str)

        # Validate confidence range
        confidence = json_data.get("confidence")
        if not isinstance(confidence, (int, float)):
            result.add_error("confidence", "Confidence must be a number", confidence)
        elif not 0 <= confidence <= 100:
            result.add_error("confidence", "Confidence must be 0-100", confidence)

        # Validate reasoning length
        reasoning = json_data.get("reasoning", "")
        if not isinstance(reasoning, str):
            result.add_error("reasoning", "Reasoning must be a string", reasoning)
        elif len(reasoning) < 10:
            result.add_error("reasoning", "Reasoning must be at least 10 characters")

        # Validate evidence is a list
        evidence = json_data.get("evidence", [])
        if not isinstance(evidence, list):
            result.add_error("evidence", "Evidence must be a list", evidence)

        return result

    def parse_verdict(self, response: str) -> LLMVerdict:
        """
        Parse and validate an LLM verdict response.

        Args:
            response: Raw LLM response string

        Returns:
            LLMVerdict if valid, or ERROR verdict if invalid

        Raises:
            ValueError: If response is invalid and strict_mode is True
        """
        result = self.validate_verdict(response)

        if not result.valid:
            if self.strict_mode:
                errors = "; ".join(e.message for e in result.errors)
                raise ValueError(f"Invalid LLM response: {errors}")

            return LLMVerdict(
                verdict=Verdict.ERROR,
                confidence=0,
                reasoning=f"Validation failed: {result.errors[0].message}",
                evidence=[],
                raw_response=response,
            )

        data = result.parsed_data
        return LLMVerdict(
            verdict=Verdict[data["verdict"].upper()],
            confidence=int(data["confidence"]),
            reasoning=data["reasoning"],
            evidence=data.get("evidence", []),
            raw_response=response,
        )

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.

        LLMs sometimes include markdown code blocks or extra text.
        This method attempts to extract valid JSON.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dict or None
        """
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in code blocks
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # JSON code block
            r'```\s*([\s\S]*?)\s*```',       # Generic code block
            r'\{[\s\S]*\}',                   # Raw JSON object
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    if isinstance(match, str) and match.strip().startswith('{'):
                        return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        return None

    def validate_json_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate data against a JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema definition

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, parsed_data=data)

        # Check type
        expected_type = schema.get("type")
        if expected_type == "object" and not isinstance(data, dict):
            result.add_error("root", f"Expected object, got {type(data).__name__}")
            return result

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                result.add_error(field, f"Missing required field: {field}")

        # Check properties
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field not in data:
                continue

            value = data[field]
            field_type = field_schema.get("type")

            # Type validation
            if field_type == "string" and not isinstance(value, str):
                result.add_error(field, f"Expected string, got {type(value).__name__}")
            elif field_type == "integer" and not isinstance(value, int):
                result.add_error(field, f"Expected integer, got {type(value).__name__}")
            elif field_type == "array" and not isinstance(value, list):
                result.add_error(field, f"Expected array, got {type(value).__name__}")

            # Enum validation
            if "enum" in field_schema:
                if value not in field_schema["enum"]:
                    result.add_error(field, f"Value must be one of {field_schema['enum']}")

            # Range validation
            if "minimum" in field_schema and isinstance(value, (int, float)):
                if value < field_schema["minimum"]:
                    result.add_error(field, f"Value must be >= {field_schema['minimum']}")
            if "maximum" in field_schema and isinstance(value, (int, float)):
                if value > field_schema["maximum"]:
                    result.add_error(field, f"Value must be <= {field_schema['maximum']}")

            # String length validation
            if "minLength" in field_schema and isinstance(value, str):
                if len(value) < field_schema["minLength"]:
                    result.add_error(field, f"String must be at least {field_schema['minLength']} chars")

        return result


def validate_llm_output(response: str) -> LLMVerdict:
    """
    Convenience function to validate and parse LLM verdict output.

    Args:
        response: Raw LLM response string

    Returns:
        LLMVerdict (with ERROR verdict if validation fails)
    """
    validator = OutputValidator(strict_mode=False)
    return validator.parse_verdict(response)


def is_valid_verdict(response: str) -> bool:
    """
    Quick check if response contains a valid verdict.

    Args:
        response: Raw LLM response string

    Returns:
        True if valid, False otherwise
    """
    validator = OutputValidator(strict_mode=False)
    result = validator.validate_verdict(response)
    return result.valid


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from an LLM response.

    Args:
        response: Raw LLM response

    Returns:
        Parsed JSON dict or None
    """
    validator = OutputValidator()
    return validator._extract_json(response)
