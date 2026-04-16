"""
Mutation Testing for Vulnerability Patterns

Applies mutations to safe contracts to create vulnerable variants,
then verifies that patterns detect the introduced vulnerabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class MutationType(Enum):
    """Types of mutations that introduce vulnerabilities."""
    REMOVE_REQUIRE = "remove_require"
    SWAP_STATEMENTS = "swap_statements"  # CEI violation
    CHANGE_VISIBILITY = "change_visibility"
    REMOVE_GUARD = "remove_guard"
    ADD_EXTERNAL_CALL = "add_external_call"
    REMOVE_ACCESS_CONTROL = "remove_access_control"
    ADD_STATE_WRITE = "add_state_write"


@dataclass
class MutationResult:
    """Result of a single mutation."""
    mutation_type: MutationType
    original_line: str
    mutated_line: str
    line_number: int
    introduced_vulnerability: str
    description: str


@dataclass
class MutationTestResult:
    """Result of mutation testing a pattern."""
    pattern_id: str
    total_mutants: int
    detected_mutants: int  # Pattern caught the vulnerability
    missed_mutants: int    # Pattern failed to detect
    mutation_score: float  # detected / total

    mutations_applied: List[MutationResult] = field(default_factory=list)
    detection_details: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "total_mutants": self.total_mutants,
            "detected_mutants": self.detected_mutants,
            "missed_mutants": self.missed_mutants,
            "mutation_score": self.mutation_score,
        }


class MutationOperator(ABC):
    """Base class for mutation operators."""

    name: str = "base"
    mutation_type: MutationType = MutationType.REMOVE_REQUIRE
    introduces_vulnerability: str = "unknown"

    @abstractmethod
    def can_apply(self, code: str) -> bool:
        """Check if this mutation can be applied."""
        pass

    @abstractmethod
    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        """
        Apply mutation to code.

        Returns:
            Tuple of (mutated_code, mutation_result or None if failed)
        """
        pass

    def apply_all(self, code: str) -> List[Tuple[str, MutationResult]]:
        """Apply mutation at all possible locations."""
        results = []
        lines = code.split('\n')

        for i, line in enumerate(lines):
            if self._can_apply_to_line(line):
                mutated_lines = lines.copy()
                mutated_line, result = self._mutate_line(line, i + 1)
                if result:
                    mutated_lines[i] = mutated_line
                    results.append(('\n'.join(mutated_lines), result))

        return results

    def _can_apply_to_line(self, line: str) -> bool:
        """Check if mutation can apply to specific line."""
        return False

    def _mutate_line(self, line: str, line_num: int) -> Tuple[str, Optional[MutationResult]]:
        """Mutate a single line."""
        return line, None


class RemoveRequireOperator(MutationOperator):
    """Remove require() statements to bypass input validation."""

    name = "remove_require"
    mutation_type = MutationType.REMOVE_REQUIRE
    introduces_vulnerability = "missing_input_validation"

    REQUIRE_PATTERN = re.compile(r'^\s*require\s*\([^;]+\);?\s*$')

    def can_apply(self, code: str) -> bool:
        return 'require(' in code

    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        lines = code.split('\n')

        for i, line in enumerate(lines):
            if self.REQUIRE_PATTERN.match(line):
                original = line
                mutated = f"// MUTATED: {line.strip()}"
                lines[i] = mutated

                return '\n'.join(lines), MutationResult(
                    mutation_type=self.mutation_type,
                    original_line=original,
                    mutated_line=mutated,
                    line_number=i + 1,
                    introduced_vulnerability=self.introduces_vulnerability,
                    description="Removed require() statement, bypassing input validation",
                )

        return code, None

    def _can_apply_to_line(self, line: str) -> bool:
        return bool(self.REQUIRE_PATTERN.match(line))

    def _mutate_line(self, line: str, line_num: int) -> Tuple[str, Optional[MutationResult]]:
        mutated = f"// MUTATED: {line.strip()}"
        return mutated, MutationResult(
            mutation_type=self.mutation_type,
            original_line=line,
            mutated_line=mutated,
            line_number=line_num,
            introduced_vulnerability=self.introduces_vulnerability,
            description="Removed require() statement",
        )


class SwapStatementsOperator(MutationOperator):
    """Swap external call and state write to create CEI violation (reentrancy)."""

    name = "swap_statements"
    mutation_type = MutationType.SWAP_STATEMENTS
    introduces_vulnerability = "reentrancy"

    EXTERNAL_CALL_PATTERNS = [
        r'\.call\s*\{',
        r'\.call\s*\(',
        r'\.transfer\s*\(',
        r'\.send\s*\(',
    ]

    STATE_WRITE_PATTERNS = [
        r'\w+\s*-=',
        r'\w+\s*\+=',
        r'\w+\s*=\s*[^=]',
        r'\w+\[[^\]]+\]\s*[+\-]?=',
    ]

    def can_apply(self, code: str) -> bool:
        has_external = any(re.search(p, code) for p in self.EXTERNAL_CALL_PATTERNS)
        has_write = any(re.search(p, code) for p in self.STATE_WRITE_PATTERNS)
        return has_external and has_write

    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        lines = code.split('\n')

        # Find external call line
        external_idx = None
        for i, line in enumerate(lines):
            if any(re.search(p, line) for p in self.EXTERNAL_CALL_PATTERNS):
                external_idx = i
                break

        if external_idx is None:
            return code, None

        # Find state write - either BEFORE (safe) or AFTER (vulnerable) external call
        state_write_idx = None

        # First look BEFORE external call (safe pattern - we can introduce vuln by swapping)
        for i in range(external_idx - 1, -1, -1):
            if any(re.search(p, lines[i]) for p in self.STATE_WRITE_PATTERNS):
                # Skip require statements
                if 'require' not in lines[i]:
                    state_write_idx = i
                    break

        # If not found before, look AFTER external call (vulnerable pattern)
        if state_write_idx is None:
            for i in range(external_idx + 1, len(lines)):
                if any(re.search(p, lines[i]) for p in self.STATE_WRITE_PATTERNS):
                    if 'require' not in lines[i]:
                        state_write_idx = i
                        break

        if state_write_idx is None:
            return code, None

        # Swap the lines
        original_external = lines[external_idx]
        original_write = lines[state_write_idx]

        lines[external_idx] = original_write
        lines[state_write_idx] = original_external

        return '\n'.join(lines), MutationResult(
            mutation_type=self.mutation_type,
            original_line=f"L{state_write_idx+1}: {original_write.strip()} | L{external_idx+1}: {original_external.strip()}",
            mutated_line=f"SWAPPED: statements at lines {state_write_idx+1} and {external_idx+1}",
            line_number=external_idx + 1,
            introduced_vulnerability=self.introduces_vulnerability,
            description="Swapped external call and state write, changing CEI pattern",
        )


class ChangeVisibilityOperator(MutationOperator):
    """Change function visibility from internal/private to public."""

    name = "change_visibility"
    mutation_type = MutationType.CHANGE_VISIBILITY
    introduces_vulnerability = "unauthorized_access"

    VISIBILITY_PATTERN = re.compile(r'\b(internal|private)\b')

    def can_apply(self, code: str) -> bool:
        return bool(self.VISIBILITY_PATTERN.search(code))

    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        match = self.VISIBILITY_PATTERN.search(code)
        if not match:
            return code, None

        original_visibility = match.group(1)
        mutated_code = code[:match.start()] + "public" + code[match.end():]

        # Find line number
        line_num = code[:match.start()].count('\n') + 1

        return mutated_code, MutationResult(
            mutation_type=self.mutation_type,
            original_line=f"visibility: {original_visibility}",
            mutated_line="visibility: public",
            line_number=line_num,
            introduced_vulnerability=self.introduces_vulnerability,
            description=f"Changed visibility from {original_visibility} to public",
        )


class RemoveGuardOperator(MutationOperator):
    """Remove reentrancy guards or access control modifiers."""

    name = "remove_guard"
    mutation_type = MutationType.REMOVE_GUARD
    introduces_vulnerability = "missing_protection"

    GUARD_PATTERNS = [
        (r'\bnonReentrant\b', "reentrancy_guard"),
        (r'\bonlyOwner\b', "access_control"),
        (r'\bonlyAdmin\b', "access_control"),
        (r'\bonlyRole\([^)]+\)', "role_based_access"),
        (r'\bwhenNotPaused\b', "pause_guard"),
    ]

    def can_apply(self, code: str) -> bool:
        return any(re.search(p, code) for p, _ in self.GUARD_PATTERNS)

    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        for pattern, guard_type in self.GUARD_PATTERNS:
            match = re.search(pattern, code)
            if match:
                original = match.group(0)
                mutated_code = code[:match.start()] + "/* REMOVED: " + original + " */" + code[match.end():]

                line_num = code[:match.start()].count('\n') + 1

                return mutated_code, MutationResult(
                    mutation_type=self.mutation_type,
                    original_line=original,
                    mutated_line=f"/* REMOVED: {original} */",
                    line_number=line_num,
                    introduced_vulnerability=f"missing_{guard_type}",
                    description=f"Removed {guard_type} modifier: {original}",
                )

        return code, None


class AddExternalCallOperator(MutationOperator):
    """Add external call before state write to create reentrancy."""

    name = "add_external_call"
    mutation_type = MutationType.ADD_EXTERNAL_CALL
    introduces_vulnerability = "reentrancy"

    STATE_WRITE_PATTERN = re.compile(r'(\s*)(\w+\s*-=\s*\w+;)')

    def can_apply(self, code: str) -> bool:
        # Can apply if there's a state write without preceding external call
        return bool(self.STATE_WRITE_PATTERN.search(code))

    def apply(self, code: str) -> Tuple[str, Optional[MutationResult]]:
        match = self.STATE_WRITE_PATTERN.search(code)
        if not match:
            return code, None

        indent = match.group(1)
        state_write = match.group(2)

        # Insert external call before state write
        malicious_call = f'{indent}(bool success,) = msg.sender.call{{value: amount}}("");  // MUTATED: added external call\n'

        mutated_code = code[:match.start()] + malicious_call + match.group(0) + code[match.end():]

        line_num = code[:match.start()].count('\n') + 1

        return mutated_code, MutationResult(
            mutation_type=self.mutation_type,
            original_line=state_write,
            mutated_line=f"Added external call before: {state_write}",
            line_number=line_num,
            introduced_vulnerability=self.introduces_vulnerability,
            description="Added external call before state write, creating reentrancy vulnerability",
        )


class ContractMutator:
    """
    Applies mutations to contracts and tracks results.

    Used to test if vulnerability patterns correctly detect
    introduced vulnerabilities (mutation testing).
    """

    DEFAULT_OPERATORS = [
        RemoveRequireOperator(),
        SwapStatementsOperator(),
        ChangeVisibilityOperator(),
        RemoveGuardOperator(),
        AddExternalCallOperator(),
    ]

    def __init__(self, operators: Optional[List[MutationOperator]] = None):
        self.operators = operators or self.DEFAULT_OPERATORS

    def generate_mutants(self, code: str) -> List[Tuple[str, MutationResult]]:
        """
        Generate all possible mutants from code.

        Returns:
            List of (mutated_code, mutation_result) tuples
        """
        mutants = []

        for operator in self.operators:
            if operator.can_apply(code):
                mutated_code, result = operator.apply(code)
                if result:
                    mutants.append((mutated_code, result))

        return mutants

    def generate_all_mutants(self, code: str) -> List[Tuple[str, MutationResult]]:
        """Generate mutants at all possible locations."""
        mutants = []

        for operator in self.operators:
            mutants.extend(operator.apply_all(code))

        return mutants

    def test_pattern(
        self,
        pattern_id: str,
        safe_code: str,
        pattern_checker: callable,
    ) -> MutationTestResult:
        """
        Test a pattern's ability to detect mutations.

        Args:
            pattern_id: ID of pattern being tested
            safe_code: Safe contract code to mutate
            pattern_checker: Function that returns True if pattern matches

        Returns:
            MutationTestResult with mutation score
        """
        mutants = self.generate_mutants(safe_code)

        detected = 0
        missed = 0
        detection_details = {}

        for mutated_code, mutation in mutants:
            mutant_id = f"{mutation.mutation_type.value}_{mutation.line_number}"

            # Check if pattern detects the vulnerability
            is_detected = pattern_checker(mutated_code)

            if is_detected:
                detected += 1
            else:
                missed += 1

            detection_details[mutant_id] = is_detected

        total = len(mutants)
        score = detected / total if total > 0 else 0.0

        return MutationTestResult(
            pattern_id=pattern_id,
            total_mutants=total,
            detected_mutants=detected,
            missed_mutants=missed,
            mutation_score=score,
            mutations_applied=[m for _, m in mutants],
            detection_details=detection_details,
        )

    def get_operator_stats(self, code: str) -> Dict[str, int]:
        """Get count of applicable mutations by operator."""
        stats = {}

        for operator in self.operators:
            if operator.can_apply(code):
                mutants = operator.apply_all(code)
                stats[operator.name] = len(mutants)
            else:
                stats[operator.name] = 0

        return stats
