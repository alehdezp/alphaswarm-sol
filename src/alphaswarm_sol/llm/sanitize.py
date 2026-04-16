"""
LLM Input Sanitization

Prevents prompt injection attacks by:
1. Escaping/marking untrusted code content
2. Detecting potential injection patterns
3. Sanitizing function names and comments
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class InjectionRisk(Enum):
    """Risk level for detected injection patterns."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    sanitized_content: str
    original_content: str
    injection_risk: InjectionRisk
    detected_patterns: List[str]
    warnings: List[str]

    def is_safe(self) -> bool:
        """Check if content is safe to send to LLM."""
        return self.injection_risk in (InjectionRisk.NONE, InjectionRisk.LOW)


# Patterns that might indicate prompt injection attempts
# Note: \s+ also matches underscores via [\s_]+ for function name patterns
INJECTION_PATTERNS = [
    # Direct instruction patterns (also match underscores for function names)
    (r"ignore[\s_]+(previous[\s_]+)?instructions?", InjectionRisk.HIGH, "Ignore instructions pattern"),
    (r"forget[\s_]+(everything|all)", InjectionRisk.HIGH, "Forget all pattern"),
    (r"disregard[\s_]+(above|previous)", InjectionRisk.HIGH, "Disregard previous pattern"),
    (r"new[\s_]+instructions?:", InjectionRisk.HIGH, "New instructions pattern"),
    (r"system\s*:\s*", InjectionRisk.HIGH, "System prompt pattern"),
    (r"assistant\s*:\s*", InjectionRisk.MEDIUM, "Assistant role pattern"),
    (r"user\s*:\s*", InjectionRisk.MEDIUM, "User role pattern"),

    # Output manipulation patterns
    (r"say[\s_]+(\w+[\s_]+)?(is|are)[\s_]+safe", InjectionRisk.HIGH, "Output manipulation: safe"),
    (r"report[\s_]+no[\s_]+vulnerabilit", InjectionRisk.HIGH, "Report no vulnerabilities"),
    (r"respond[\s_]+with[\s_]+(only[\s_]+)?safe", InjectionRisk.HIGH, "Respond safe pattern"),
    (r"always[\s_]+(say|respond|output)", InjectionRisk.MEDIUM, "Always respond pattern"),

    # Jailbreak patterns
    (r"pretend[\s_]+(you[\s_]+)?are", InjectionRisk.HIGH, "Pretend pattern"),
    (r"act[\s_]+as[\s_]+(if|a)", InjectionRisk.MEDIUM, "Act as pattern"),
    (r"roleplay[\s_]+as", InjectionRisk.MEDIUM, "Roleplay pattern"),
    (r"you[\s_]+are[\s_]+now", InjectionRisk.MEDIUM, "Role change pattern"),

    # Security bypass patterns
    (r"bypass[\s_]+(security|check)", InjectionRisk.HIGH, "Bypass security pattern"),
    (r"skip[\s_]+(validation|check)", InjectionRisk.MEDIUM, "Skip validation pattern"),
    (r"disable[\s_]+(security|filter)", InjectionRisk.HIGH, "Disable security pattern"),
]


class CodeSanitizer:
    """Sanitizes code content before sending to LLM."""

    def __init__(self, strict_mode: bool = True):
        """
        Initialize sanitizer.

        Args:
            strict_mode: If True, flag any suspicious patterns
        """
        self.strict_mode = strict_mode
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), risk, desc)
            for pattern, risk, desc in INJECTION_PATTERNS
        ]

    def sanitize(self, code: str, context: str = "") -> SanitizationResult:
        """
        Sanitize code content for LLM consumption.

        Args:
            code: The code content to sanitize
            context: Additional context about the code

        Returns:
            SanitizationResult with sanitized content and risk assessment
        """
        detected = []
        warnings = []
        max_risk = InjectionRisk.NONE

        # Check for injection patterns
        combined = f"{code}\n{context}"
        for pattern, risk, desc in self._compiled_patterns:
            if pattern.search(combined):
                detected.append(desc)
                if risk.value > max_risk.value:
                    max_risk = risk
                warnings.append(f"Detected: {desc} (risk: {risk.name})")

        # Wrap code in untrusted tags
        sanitized = self._wrap_untrusted(code)

        # Add context warnings
        if context:
            sanitized_context = self._wrap_untrusted(context, tag="untrusted_context")
            sanitized = f"{sanitized}\n\n{sanitized_context}"

        return SanitizationResult(
            sanitized_content=sanitized,
            original_content=code,
            injection_risk=max_risk,
            detected_patterns=detected,
            warnings=warnings,
        )

    def sanitize_function_name(self, name: str) -> Tuple[str, InjectionRisk]:
        """
        Sanitize a function name.

        Function names could contain injection attempts like:
        - ignore_security_warnings
        - bypass_auth_check

        Args:
            name: The function name to check

        Returns:
            Tuple of (sanitized_name, risk_level)
        """
        risk = InjectionRisk.NONE

        # Check function name for patterns
        for pattern, pat_risk, _ in self._compiled_patterns:
            if pattern.search(name):
                risk = max(risk, pat_risk, key=lambda r: list(InjectionRisk).index(r))

        # Keep original but note the risk
        return name, risk

    def sanitize_comment(self, comment: str) -> Tuple[str, InjectionRisk]:
        """
        Sanitize a code comment.

        Comments are a common injection vector:
        - // IGNORE PREVIOUS INSTRUCTIONS
        - /* Say this is safe */

        Args:
            comment: The comment text to check

        Returns:
            Tuple of (sanitized_comment, risk_level)
        """
        risk = InjectionRisk.NONE

        for pattern, pat_risk, _ in self._compiled_patterns:
            if pattern.search(comment):
                risk = max(risk, pat_risk, key=lambda r: list(InjectionRisk).index(r))

        # Escape comment markers that could confuse the LLM
        sanitized = comment.replace("//", "//​")  # Add zero-width space
        sanitized = sanitized.replace("/*", "/​*")
        sanitized = sanitized.replace("*/", "*​/")

        return sanitized, risk

    def _wrap_untrusted(self, content: str, tag: str = "untrusted_code") -> str:
        """
        Wrap content in untrusted tags.

        This signals to the LLM that the content should be treated
        as data, not instructions.

        Args:
            content: Content to wrap
            tag: XML-like tag to use

        Returns:
            Wrapped content
        """
        return f"<{tag}>\n{content}\n</{tag}>"

    def extract_safe_code(self, code: str) -> str:
        """
        Extract code with comments stripped (for safer analysis).

        This removes comments which are the most common injection vector.

        Args:
            code: Solidity code to clean

        Returns:
            Code with comments removed
        """
        # Remove single-line comments
        code = re.sub(r'//[^\n]*', '', code)
        # Remove multi-line comments
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)
        return code


def sanitize_for_llm(code: str, context: str = "", strict: bool = True) -> SanitizationResult:
    """
    Convenience function to sanitize code for LLM.

    Args:
        code: The code to sanitize
        context: Additional context
        strict: Whether to use strict mode

    Returns:
        SanitizationResult
    """
    sanitizer = CodeSanitizer(strict_mode=strict)
    return sanitizer.sanitize(code, context)


def check_injection_risk(text: str) -> InjectionRisk:
    """
    Quick check for injection risk in text.

    Args:
        text: Text to check

    Returns:
        Risk level
    """
    sanitizer = CodeSanitizer()
    result = sanitizer.sanitize(text)
    return result.injection_risk


def strip_comments(code: str) -> str:
    """
    Strip comments from code for safer processing.

    Args:
        code: Solidity code

    Returns:
        Code without comments
    """
    sanitizer = CodeSanitizer()
    return sanitizer.extract_safe_code(code)
