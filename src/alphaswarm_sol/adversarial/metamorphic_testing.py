"""
Metamorphic Testing for Vulnerability Patterns

Tests that patterns are robust to semantically-equivalent transformations.
Key property: Renaming identifiers should NOT affect detection results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re
import random
import string
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetamorphicTestResult:
    """Result of metamorphic testing."""
    pattern_id: str
    base_detected: bool       # Pattern detected in original
    transformations_tested: int
    consistent_results: int   # Same result as base
    inconsistent_results: int # Different result than base (BUG!)

    # Score: 1.0 = perfectly robust, < 1.0 = has semantic bugs
    robustness_score: float

    # Details of inconsistencies
    inconsistencies: List[Dict] = field(default_factory=list)

    def is_robust(self) -> bool:
        """Pattern is robust if all results are consistent."""
        return self.inconsistent_results == 0

    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "base_detected": self.base_detected,
            "transformations_tested": self.transformations_tested,
            "consistent_results": self.consistent_results,
            "inconsistent_results": self.inconsistent_results,
            "robustness_score": self.robustness_score,
            "is_robust": self.is_robust(),
        }


class IdentifierRenamer:
    """Renames identifiers while preserving semantics."""

    # Solidity reserved keywords (don't rename these)
    RESERVED_KEYWORDS = {
        # Types
        'address', 'bool', 'string', 'bytes', 'int', 'uint',
        'int8', 'int16', 'int32', 'int64', 'int128', 'int256',
        'uint8', 'uint16', 'uint32', 'uint64', 'uint128', 'uint256',
        'bytes1', 'bytes2', 'bytes4', 'bytes8', 'bytes16', 'bytes32',
        'fixed', 'ufixed',
        # Keywords
        'contract', 'interface', 'library', 'struct', 'enum', 'event',
        'function', 'modifier', 'constructor', 'fallback', 'receive',
        'public', 'private', 'internal', 'external', 'view', 'pure',
        'payable', 'virtual', 'override', 'abstract', 'immutable',
        'constant', 'memory', 'storage', 'calldata',
        'if', 'else', 'for', 'while', 'do', 'break', 'continue', 'return',
        'try', 'catch', 'revert', 'require', 'assert',
        'new', 'delete', 'this', 'super', 'selfdestruct',
        'true', 'false', 'wei', 'gwei', 'ether', 'seconds', 'minutes',
        'hours', 'days', 'weeks', 'years',
        'msg', 'block', 'tx', 'abi', 'type',
        'mapping', 'using', 'is', 'as', 'import', 'pragma',
        'emit', 'indexed', 'anonymous', 'unchecked', 'assembly',
    }

    # Common identifiers that shouldn't be renamed (external interfaces)
    PRESERVE_IDENTIFIERS = {
        'sender', 'value', 'data', 'sig', 'origin',
        'timestamp', 'number', 'difficulty', 'gaslimit',
        'gasprice', 'coinbase', 'prevrandao',
        'transfer', 'send', 'call', 'delegatecall', 'staticcall',
        'balance', 'code', 'codehash',
        'encode', 'encodePacked', 'encodeWithSelector', 'encodeWithSignature',
        'decode', 'selector',
        'name', 'symbol', 'decimals', 'totalSupply', 'balanceOf',
        'approve', 'allowance', 'transferFrom',
        'IERC20', 'IERC721', 'IERC1155',
        'onERC721Received', 'onERC1155Received',
        'owner', 'renounceOwnership', 'transferOwnership',
        'Ownable', 'ReentrancyGuard', 'Pausable',
    }

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.rename_map: Dict[str, str] = {}

    def generate_new_name(self, original: str) -> str:
        """Generate a semantically different but valid name."""
        # Try different naming strategies
        strategies = [
            lambda: f"renamed_{original}",
            lambda: f"var_{self._random_suffix()}",
            lambda: f"x{self._random_suffix()}",
            lambda: self._camel_to_snake(original) if '_' not in original else self._snake_to_camel(original),
            lambda: f"_{original}" if not original.startswith('_') else original[1:],
        ]

        new_name = random.choice(strategies)()

        # Ensure unique
        while new_name in self.rename_map.values():
            new_name = f"var_{self._random_suffix()}"

        return new_name

    def _random_suffix(self, length: int = 4) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _camel_to_snake(self, name: str) -> str:
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _snake_to_camel(self, name: str) -> str:
        components = name.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    def extract_identifiers(self, code: str) -> Set[str]:
        """Extract all user-defined identifiers from code."""
        # Find all potential identifiers
        identifier_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
        all_identifiers = set(identifier_pattern.findall(code))

        # Filter out reserved and preserved
        user_identifiers = {
            ident for ident in all_identifiers
            if ident not in self.RESERVED_KEYWORDS
            and ident not in self.PRESERVE_IDENTIFIERS
            and not ident.startswith('__')  # Internal names
        }

        return user_identifiers

    def rename_all(self, code: str) -> Tuple[str, Dict[str, str]]:
        """
        Rename all user-defined identifiers.

        Returns:
            Tuple of (renamed_code, rename_map)
        """
        identifiers = self.extract_identifiers(code)
        self.rename_map = {}

        # Generate new names
        for ident in identifiers:
            if len(ident) > 1:  # Don't rename single-char like 'i'
                self.rename_map[ident] = self.generate_new_name(ident)

        # Apply renames (longest first to avoid partial replacements)
        renamed_code = code
        for old_name in sorted(self.rename_map.keys(), key=len, reverse=True):
            new_name = self.rename_map[old_name]
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(old_name)}\b'
            renamed_code = re.sub(pattern, new_name, renamed_code)

        return renamed_code, self.rename_map

    def partial_rename(self, code: str, fraction: float = 0.5) -> Tuple[str, Dict[str, str]]:
        """Rename only a fraction of identifiers."""
        identifiers = list(self.extract_identifiers(code))
        random.shuffle(identifiers)

        num_to_rename = int(len(identifiers) * fraction)
        to_rename = identifiers[:num_to_rename]

        self.rename_map = {}
        for ident in to_rename:
            if len(ident) > 1:
                self.rename_map[ident] = self.generate_new_name(ident)

        renamed_code = code
        for old_name in sorted(self.rename_map.keys(), key=len, reverse=True):
            new_name = self.rename_map[old_name]
            pattern = rf'\b{re.escape(old_name)}\b'
            renamed_code = re.sub(pattern, new_name, renamed_code)

        return renamed_code, self.rename_map


class MetamorphicTester:
    """
    Tests pattern robustness using metamorphic relations.

    Key insight: If pattern detects vulnerability in code C,
    it MUST also detect in any semantically-equivalent C'.
    """

    def __init__(
        self,
        num_transformations: int = 5,
        seed: Optional[int] = None,
    ):
        self.num_transformations = num_transformations
        self.seed = seed

    def test_pattern(
        self,
        pattern_id: str,
        code: str,
        pattern_checker: callable,
    ) -> MetamorphicTestResult:
        """
        Test pattern robustness to identifier renaming.

        Args:
            pattern_id: ID of pattern being tested
            code: Original code
            pattern_checker: Function that returns True if pattern matches

        Returns:
            MetamorphicTestResult with robustness score
        """
        # Get base result
        base_detected = pattern_checker(code)

        consistent = 0
        inconsistent = 0
        inconsistencies = []

        for i in range(self.num_transformations):
            # Generate transformed version
            seed = (self.seed + i) if self.seed else None
            renamer = IdentifierRenamer(seed=seed)
            transformed_code, rename_map = renamer.rename_all(code)

            # Check transformed version
            transformed_detected = pattern_checker(transformed_code)

            if transformed_detected == base_detected:
                consistent += 1
            else:
                inconsistent += 1
                inconsistencies.append({
                    "transformation": i + 1,
                    "base_detected": base_detected,
                    "transformed_detected": transformed_detected,
                    "renames": list(rename_map.items())[:5],  # First 5 renames
                    "bug_type": "false_negative" if base_detected else "false_positive",
                })

        total = self.num_transformations
        robustness = consistent / total if total > 0 else 1.0

        return MetamorphicTestResult(
            pattern_id=pattern_id,
            base_detected=base_detected,
            transformations_tested=total,
            consistent_results=consistent,
            inconsistent_results=inconsistent,
            robustness_score=robustness,
            inconsistencies=inconsistencies,
        )

    def test_patterns_batch(
        self,
        pattern_ids: List[str],
        code: str,
        pattern_checkers: Dict[str, callable],
    ) -> Dict[str, MetamorphicTestResult]:
        """Test multiple patterns on same code."""
        results = {}

        for pattern_id in pattern_ids:
            if pattern_id in pattern_checkers:
                results[pattern_id] = self.test_pattern(
                    pattern_id,
                    code,
                    pattern_checkers[pattern_id],
                )

        return results

    def find_breaking_transformation(
        self,
        pattern_id: str,
        code: str,
        pattern_checker: callable,
        max_attempts: int = 100,
    ) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Try to find a transformation that breaks the pattern.

        Useful for debugging patterns with robustness issues.

        Returns:
            Tuple of (breaking_code, rename_map) or None if pattern is robust
        """
        base_detected = pattern_checker(code)

        for i in range(max_attempts):
            renamer = IdentifierRenamer(seed=i if self.seed is None else self.seed + i)
            transformed_code, rename_map = renamer.rename_all(code)

            transformed_detected = pattern_checker(transformed_code)

            if transformed_detected != base_detected:
                logger.info(f"Found breaking transformation at attempt {i + 1}")
                return transformed_code, rename_map

        return None


class SemanticTransformer:
    """Additional semantic-preserving transformations."""

    @staticmethod
    def add_whitespace(code: str) -> str:
        """Add extra whitespace (shouldn't affect anything)."""
        # Add spaces around operators
        code = re.sub(r'([=<>!+\-*/])', r' \1 ', code)
        # Add blank lines
        lines = code.split('\n')
        result = []
        for line in lines:
            result.append(line)
            if random.random() < 0.2:
                result.append('')
        return '\n'.join(result)

    @staticmethod
    def reorder_modifiers(code: str) -> str:
        """Reorder function modifiers (order shouldn't matter for detection)."""
        # Find function declarations with modifiers
        pattern = r'(function\s+\w+\s*\([^)]*\))\s+(public|external|internal|private)?\s*(view|pure)?\s*(returns\s*\([^)]*\))?'

        def reorder(match):
            parts = [p for p in match.groups() if p]
            random.shuffle(parts[1:])  # Keep function signature first
            return ' '.join(parts)

        return re.sub(pattern, reorder, code)

    @staticmethod
    def expand_shorthand(code: str) -> str:
        """Expand shorthand operators."""
        # a += b -> a = a + b
        code = re.sub(r'(\w+)\s*\+=\s*(\w+)', r'\1 = \1 + \2', code)
        code = re.sub(r'(\w+)\s*-=\s*(\w+)', r'\1 = \1 - \2', code)
        return code
