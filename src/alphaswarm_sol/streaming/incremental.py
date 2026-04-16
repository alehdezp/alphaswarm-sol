"""
Incremental Analysis

Provides diff-based analysis for contract upgrades.
Only re-analyzes changed functions, significantly faster than full re-audit.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import difflib
import re
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes between contract versions."""
    ADDED = "added"           # New function/variable
    REMOVED = "removed"       # Function/variable removed
    MODIFIED = "modified"     # Code changed
    RENAMED = "renamed"       # Name changed but same logic
    SIGNATURE_CHANGED = "signature_changed"  # Parameters changed
    VISIBILITY_CHANGED = "visibility_changed"  # public→private, etc.
    MODIFIER_CHANGED = "modifier_changed"  # Modifiers added/removed


@dataclass
class FunctionChange:
    """
    A change to a specific function.
    """
    function_name: str
    change_type: ChangeType
    old_code: Optional[str] = None
    new_code: Optional[str] = None

    # Security impact
    security_relevant: bool = False
    security_reason: str = ""
    requires_reaudit: bool = False

    # Detailed changes
    lines_added: int = 0
    lines_removed: int = 0
    modifiers_added: List[str] = field(default_factory=list)
    modifiers_removed: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._analyze_security_impact()

    def _analyze_security_impact(self):
        """Analyze if change has security implications."""
        # Check for security-critical changes
        critical_patterns = [
            (r'\.call\{', "External call added/modified"),
            (r'\.transfer\(', "Value transfer added/modified"),
            (r'selfdestruct', "Self-destruct added"),
            (r'delegatecall', "Delegatecall added"),
            (r'assembly\s*\{', "Inline assembly added"),
            (r'tx\.origin', "tx.origin usage added"),
            (r'balances?\[.*\]\s*[-+]?=', "Balance modification added"),
        ]

        new_code = self.new_code or ""
        old_code = self.old_code or ""

        for pattern, reason in critical_patterns:
            # Check if pattern is new (in new but not in old)
            in_new = bool(re.search(pattern, new_code))
            in_old = bool(re.search(pattern, old_code))

            if in_new and not in_old:
                self.security_relevant = True
                self.security_reason = reason
                self.requires_reaudit = True
                return

        # Check for removed security measures
        security_modifiers = ["onlyOwner", "nonReentrant", "whenNotPaused"]
        for mod in security_modifiers:
            if mod in old_code and mod not in new_code:
                self.security_relevant = True
                self.security_reason = f"Security modifier '{mod}' removed"
                self.requires_reaudit = True
                self.modifiers_removed.append(mod)
                return

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "function_name": self.function_name,
            "change_type": self.change_type.value,
            "security_relevant": self.security_relevant,
            "security_reason": self.security_reason,
            "requires_reaudit": self.requires_reaudit,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }


@dataclass
class DiffResult:
    """
    Result of comparing two contract versions.
    """
    old_version: str                    # Version identifier
    new_version: str
    total_changes: int
    security_relevant_changes: int

    function_changes: List[FunctionChange] = field(default_factory=list)
    state_variable_changes: List[Dict] = field(default_factory=list)
    inheritance_changes: List[Dict] = field(default_factory=list)

    # Summary
    functions_added: int = 0
    functions_removed: int = 0
    functions_modified: int = 0

    # Analysis timing
    analysis_duration_ms: float = 0.0

    def get_security_relevant(self) -> List[FunctionChange]:
        """Get changes with security implications."""
        return [c for c in self.function_changes if c.security_relevant]

    def get_reaudit_required(self) -> List[FunctionChange]:
        """Get changes requiring re-audit."""
        return [c for c in self.function_changes if c.requires_reaudit]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "total_changes": self.total_changes,
            "security_relevant_changes": self.security_relevant_changes,
            "functions_added": self.functions_added,
            "functions_removed": self.functions_removed,
            "functions_modified": self.functions_modified,
            "function_changes": [c.to_dict() for c in self.function_changes],
            "analysis_duration_ms": self.analysis_duration_ms,
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Contract Diff: {self.old_version} → {self.new_version}",
            f"{'=' * 50}",
            f"Total Changes: {self.total_changes}",
            f"  - Functions Added: {self.functions_added}",
            f"  - Functions Removed: {self.functions_removed}",
            f"  - Functions Modified: {self.functions_modified}",
            f"",
            f"Security-Relevant Changes: {self.security_relevant_changes}",
        ]

        if self.security_relevant_changes > 0:
            lines.append("")
            for change in self.get_security_relevant():
                lines.append(f"  ⚠️  {change.function_name}: {change.security_reason}")

        return "\n".join(lines)


class IncrementalAnalyzer:
    """
    Performs incremental analysis of contract changes.

    Compares two versions and identifies what needs re-auditing.
    """

    # Function extraction pattern
    FUNCTION_PATTERN = re.compile(
        r'function\s+(\w+)\s*\([^)]*\)\s*'
        r'(public|private|internal|external)?\s*'
        r'(view|pure)?\s*'
        r'(payable)?\s*'
        r'((?:\w+\s*)*)?'  # modifiers
        r'(?:returns\s*\([^)]*\))?\s*'
        r'\{',
        re.MULTILINE
    )

    # State variable pattern
    STATE_VAR_PATTERN = re.compile(
        r'^\s*(mapping|address|uint\d*|int\d*|bool|bytes\d*|string)\s*'
        r'(public|private|internal)?\s*'
        r'(\w+)\s*[;=]',
        re.MULTILINE
    )

    def __init__(self):
        pass

    def diff_contracts(
        self,
        old_code: str,
        new_code: str,
        old_version: str = "v1",
        new_version: str = "v2"
    ) -> DiffResult:
        """
        Compare two contract versions.

        Args:
            old_code: Original contract source
            new_code: Updated contract source
            old_version: Version identifier for old
            new_version: Version identifier for new

        Returns:
            DiffResult with all changes
        """
        import time
        start_time = time.time()

        # Extract functions from both versions
        old_functions = self._extract_functions(old_code)
        new_functions = self._extract_functions(new_code)

        # Compare functions
        function_changes = self._compare_functions(old_functions, new_functions)

        # Compare state variables
        old_vars = self._extract_state_variables(old_code)
        new_vars = self._extract_state_variables(new_code)
        state_changes = self._compare_state_variables(old_vars, new_vars)

        # Calculate summary
        added = len([c for c in function_changes if c.change_type == ChangeType.ADDED])
        removed = len([c for c in function_changes if c.change_type == ChangeType.REMOVED])
        modified = len([c for c in function_changes if c.change_type == ChangeType.MODIFIED])

        security_relevant = len([c for c in function_changes if c.security_relevant])

        duration = (time.time() - start_time) * 1000

        return DiffResult(
            old_version=old_version,
            new_version=new_version,
            total_changes=len(function_changes) + len(state_changes),
            security_relevant_changes=security_relevant,
            function_changes=function_changes,
            state_variable_changes=state_changes,
            functions_added=added,
            functions_removed=removed,
            functions_modified=modified,
            analysis_duration_ms=duration,
        )

    def _extract_functions(self, code: str) -> Dict[str, str]:
        """Extract all functions from code."""
        functions = {}

        # Split code into lines for processing
        lines = code.split('\n')
        current_function = None
        function_code = []
        brace_count = 0
        in_function = False

        for line in lines:
            # Check for function start
            match = self.FUNCTION_PATTERN.search(line)
            if match and not in_function:
                current_function = match.group(1)
                function_code = [line]
                brace_count = line.count('{') - line.count('}')
                in_function = True
                continue

            if in_function:
                function_code.append(line)
                brace_count += line.count('{') - line.count('}')

                if brace_count <= 0:
                    # Function complete
                    functions[current_function] = '\n'.join(function_code)
                    in_function = False
                    current_function = None
                    function_code = []

        return functions

    def _extract_state_variables(self, code: str) -> Dict[str, Dict]:
        """Extract state variables from code."""
        variables = {}

        for match in self.STATE_VAR_PATTERN.finditer(code):
            var_type = match.group(1)
            visibility = match.group(2) or "internal"
            var_name = match.group(3)

            variables[var_name] = {
                "type": var_type,
                "visibility": visibility,
                "raw": match.group(0),
            }

        return variables

    def _compare_functions(
        self,
        old_functions: Dict[str, str],
        new_functions: Dict[str, str]
    ) -> List[FunctionChange]:
        """Compare functions between versions."""
        changes = []

        old_names = set(old_functions.keys())
        new_names = set(new_functions.keys())

        # Added functions
        for name in new_names - old_names:
            changes.append(FunctionChange(
                function_name=name,
                change_type=ChangeType.ADDED,
                new_code=new_functions[name],
                lines_added=len(new_functions[name].split('\n')),
            ))

        # Removed functions
        for name in old_names - new_names:
            changes.append(FunctionChange(
                function_name=name,
                change_type=ChangeType.REMOVED,
                old_code=old_functions[name],
                lines_removed=len(old_functions[name].split('\n')),
            ))

        # Modified functions
        for name in old_names & new_names:
            old_code = old_functions[name]
            new_code = new_functions[name]

            if old_code != new_code:
                # Calculate line differences
                old_lines = old_code.split('\n')
                new_lines = new_code.split('\n')

                diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
                lines_added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
                lines_removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))

                change = FunctionChange(
                    function_name=name,
                    change_type=ChangeType.MODIFIED,
                    old_code=old_code,
                    new_code=new_code,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                )

                # Check for specific change types
                if self._is_visibility_change(old_code, new_code):
                    change.change_type = ChangeType.VISIBILITY_CHANGED
                elif self._is_modifier_change(old_code, new_code):
                    change.change_type = ChangeType.MODIFIER_CHANGED

                changes.append(change)

        return changes

    def _compare_state_variables(
        self,
        old_vars: Dict[str, Dict],
        new_vars: Dict[str, Dict]
    ) -> List[Dict]:
        """Compare state variables between versions."""
        changes = []

        old_names = set(old_vars.keys())
        new_names = set(new_vars.keys())

        # Added variables
        for name in new_names - old_names:
            changes.append({
                "name": name,
                "change_type": "added",
                "new": new_vars[name],
            })

        # Removed variables
        for name in old_names - new_names:
            changes.append({
                "name": name,
                "change_type": "removed",
                "old": old_vars[name],
            })

        # Modified variables
        for name in old_names & new_names:
            if old_vars[name] != new_vars[name]:
                changes.append({
                    "name": name,
                    "change_type": "modified",
                    "old": old_vars[name],
                    "new": new_vars[name],
                })

        return changes

    def _is_visibility_change(self, old_code: str, new_code: str) -> bool:
        """Check if change is only visibility."""
        visibilities = ["public", "private", "internal", "external"]

        for vis in visibilities:
            old_has = vis in old_code
            new_has = vis in new_code

            if old_has != new_has:
                # Check if other code is same
                old_cleaned = old_code
                new_cleaned = new_code
                for v in visibilities:
                    old_cleaned = old_cleaned.replace(v, "")
                    new_cleaned = new_cleaned.replace(v, "")

                if old_cleaned.split() == new_cleaned.split():
                    return True

        return False

    def _is_modifier_change(self, old_code: str, new_code: str) -> bool:
        """Check if change is only in modifiers."""
        common_modifiers = ["onlyOwner", "nonReentrant", "whenNotPaused", "whenPaused"]

        for mod in common_modifiers:
            if (mod in old_code) != (mod in new_code):
                return True

        return False

    def get_reaudit_scope(self, diff_result: DiffResult) -> Dict[str, Any]:
        """
        Determine what needs re-auditing based on diff.

        Returns scope of re-audit with estimated effort reduction.
        """
        reaudit_functions = diff_result.get_reaudit_required()
        all_changes = diff_result.function_changes

        # Calculate effort reduction
        # Assumption: re-auditing only changed functions is faster
        if len(all_changes) == 0:
            effort_reduction = 100.0
        else:
            effort_reduction = (1 - len(reaudit_functions) / len(all_changes)) * 100

        return {
            "full_reaudit_required": len(reaudit_functions) == len(all_changes),
            "functions_to_reaudit": [f.function_name for f in reaudit_functions],
            "functions_safe": [
                f.function_name for f in all_changes
                if not f.requires_reaudit
            ],
            "total_changes": len(all_changes),
            "reaudit_count": len(reaudit_functions),
            "estimated_effort_reduction_percent": round(effort_reduction, 1),
        }
