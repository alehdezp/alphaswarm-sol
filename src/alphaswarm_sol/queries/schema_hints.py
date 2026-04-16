"""Schema-guided validation and correction hints for intents."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
import re
from typing import Iterable

from alphaswarm_sol.queries.patterns import PatternDefinition, get_patterns


_ALLOWED_OPS = {"eq", "neq", "in", "not_in", "contains_any", "contains_all", "gt", "gte", "lt", "lte", "regex"}
_META_KEYS = {
    "rule_confidence",
    "rule_candidates",
    "vql_error",
    "vql_hint",
}


@dataclass(frozen=True)
class Hint:
    field: str
    message: str
    suggestions: list[str]


def apply_schema_hints(intent, pattern_dir: Path | None = None) -> None:
    known = _collect_known_properties(pattern_dir)
    warnings: list[str] = []
    hints: list[str] = []

    for prop in intent.properties.keys():
        if prop in _META_KEYS:
            continue
        if prop not in known:
            suggestion = _suggest(prop, known)
            warnings.append(f"Unknown property '{prop}'.")
            if suggestion:
                hints.append(f"Did you mean: {', '.join(suggestion)}?")

    if intent.match:
        for condition in intent.match.all + intent.match.any + intent.match.none:
            if condition.property not in known:
                suggestion = _suggest(condition.property, known)
                warnings.append(f"Unknown property '{condition.property}'.")
                if suggestion:
                    hints.append(f"Did you mean: {', '.join(suggestion)}?")
            if condition.op not in _ALLOWED_OPS:
                warnings.append(f"Unsupported operator '{condition.op}'.")
                hints.append("Supported ops: eq, neq, in, not_in, contains_any, contains_all, gt, gte, lt, lte, regex.")

    intent.warnings = sorted(set(intent.warnings + warnings))
    intent.hints = sorted(set(intent.hints + hints))


def _collect_known_properties(pattern_dir: Path | None) -> set[str]:
    known: set[str] = set()
    for pattern in _load_patterns(pattern_dir):
        known.update(_pattern_properties(pattern))
    known.update(_builder_properties())
    return known


def _load_patterns(pattern_dir: Path | None) -> Iterable[PatternDefinition]:
    return get_patterns(pattern_dir)


def _pattern_properties(pattern: PatternDefinition) -> set[str]:
    props = {cond.property for cond in pattern.match_all + pattern.match_any + pattern.match_none}
    return {prop for prop in props if prop}


def _builder_properties() -> set[str]:
    builder_path = Path(__file__).resolve().parents[1] / "kg" / "builder.py"
    if not builder_path.exists():
        return set()
    text = builder_path.read_text(encoding="utf-8")
    matches = re.findall(r'"([a-zA-Z0-9_]+)"\s*:', text)
    return set(matches)


def _suggest(name: str, known: set[str]) -> list[str]:
    return get_close_matches(name, known, n=3, cutoff=0.78)
