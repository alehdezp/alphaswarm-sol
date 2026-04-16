"""Intent schema and parser for safe NL queries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from alphaswarm_sol.queries.aliases import EDGE_ALIASES, NODE_TYPE_ALIASES, PROPERTY_ALIASES
from alphaswarm_sol.queries.patterns import get_patterns
from alphaswarm_sol.queries.rule_map import resolve_rule_matches
from alphaswarm_sol.queries.vql_grammar import parse_vql_query
from alphaswarm_sol.queries.schema_hints import apply_schema_hints

from pydantic import BaseModel, Field, field_validator


class FlowSpec(BaseModel):
    """Dataflow constraints for complex queries."""

    from_kinds: list[str] = Field(default_factory=list, description="input kinds")
    exclude_sources: list[str] = Field(default_factory=list, description="input names to ignore")
    target_type: str = Field(default="StateVariable")
    edge_type: str = Field(default="INPUT_TAINTS_STATE")


class ConditionSpec(BaseModel):
    property: str
    op: str
    value: Any | None = None


class MatchSpec(BaseModel):
    all: list[ConditionSpec] = Field(default_factory=list)
    any: list[ConditionSpec] = Field(default_factory=list)
    none: list[ConditionSpec] = Field(default_factory=list)


class EdgeSpec(BaseModel):
    type: str
    direction: str = "out"
    target_type: str | None = None


class PathStepSpec(BaseModel):
    edge_type: str
    direction: str = "out"
    target_type: str | None = None


class PathSpec(BaseModel):
    steps: list[PathStepSpec] = Field(default_factory=list)
    edge_type: str | None = None
    direction: str = "out"
    max_depth: int = 3
    target_type: str | None = None


class Intent(BaseModel):
    """Structured query intent derived from natural language."""

    raw_text: str = Field(description="Original user query text.")
    query_kind: str = Field(default="nodes", description="nodes | edges | pattern | lens | fetch | flow | logic")
    node_types: list[str] = Field(default_factory=list)
    edge_types: list[str] = Field(default_factory=list)
    node_ids: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    flow: FlowSpec | None = None
    match: MatchSpec | None = None
    edges: list[EdgeSpec] = Field(default_factory=list)
    paths: list[PathSpec] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list, description="Pattern IDs to run")
    lens: list[str] = Field(default_factory=list, description="Lens tags to run")
    severity: list[str] = Field(default_factory=list, description="severity tags")
    limit: int = Field(default=50, ge=1, le=1000)
    compact_mode: bool = Field(default=False)
    evidence_mode: str = Field(default="full", description="full | none")
    explain_mode: bool = Field(default=False)
    include_evidence: bool = Field(default=True)
    warnings: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    disambiguation_prompt: str | None = None

    @field_validator("query_kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        allowed = {"nodes", "edges", "pattern", "lens", "fetch", "flow", "logic", "semgrep"}
        if value not in allowed:
            raise ValueError(f"query_kind must be one of {sorted(allowed)}")
        return value

    @field_validator("evidence_mode")
    @classmethod
    def _validate_evidence_mode(cls, value: str) -> str:
        allowed = {"full", "none"}
        if value not in allowed:
            raise ValueError(f"evidence_mode must be one of {sorted(allowed)}")
        return value


_NODE_HINTS = NODE_TYPE_ALIASES

_EDGE_HINTS = EDGE_ALIASES

_BOOL_HINTS = {
    "payable": ("payable", True),
    "constructor": ("is_constructor", True),
    "fallback": ("is_fallback", True),
    "receive": ("is_receive", True),
}

_VISIBILITY = {"public", "external", "internal", "private"}
_MUTABILITY = {"view", "pure", "nonpayable", "payable"}
_SEVERITY = {"critical", "high", "medium", "low", "info"}

_ATTACKER_TERMS = (
    "attacker-controlled",
    "attacker controlled",
    "user-controlled",
    "user controlled",
    "untrusted input",
    "tainted input",
    "tainted",
)
_STATE_TERMS = ("state", "storage")
_WRITE_TERMS = ("write", "writes", "update", "updates", "updated", "mutate", "mutates")
_EXCLUDE_MSG_SENDER = (
    "exclude msg.sender",
    "excluding msg.sender",
    "without msg.sender",
    "no msg.sender",
)
_EXCLUDE_CONSTRUCTOR = (
    "exclude constructor",
    "excluding constructor",
    "non-constructor",
    "non constructor",
    "not constructor",
)
_STATE_WRITE_PHRASES = (
    "state updated",
    "state update",
    "writes state",
    "write state",
    "state write",
    "storage write",
    "updates state",
    "mutates state",
)
_PRIVILEGED_STATE_PHRASES = (
    "privileged state",
    "admin state",
    "owner state",
    "upgrade state",
)
_PHRASE_PROPERTY_HINTS = {
    "block.timestamp": ("uses_block_timestamp", True),
    "timestamp": ("uses_block_timestamp", True),
    "block.number": ("uses_block_number", True),
    "blockhash": ("uses_block_hash", True),
    "prevrandao": ("uses_block_prevrandao", True),
    "chainid": ("uses_chainid", True),
    "tx.origin": ("uses_tx_origin", True),
    "delegatecall": ("uses_delegatecall", True),
    "ecrecover": ("uses_ecrecover", True),
}


def parse_intent(
    text: str,
    *,
    pattern_dir: Path | None = None,
    cli_mode: bool = False,
) -> Intent:
    """Parse a safe NL query into a structured intent.

    Args:
        text: Natural language query text.
        pattern_dir: Optional pattern directory override.
        cli_mode: When True, prevents silent degradation to "nodes" query kind.
            Instead of falling back to raw node search when no patterns match,
            keeps query_kind as "pattern" so the CLI can emit the structured
            header with matches=0. This eliminates the Plan 3.1c-12 Batch 1
            failure where agents got meaningless "nodes" results.
    """

    raw = text.strip()
    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
            payload.setdefault("raw_text", raw)
            if "query_kind" not in payload and any(key in payload for key in ("match", "edges", "paths")):
                payload["query_kind"] = "logic"
            return Intent.model_validate(payload)
        except json.JSONDecodeError:
            pass

    vql_intent = _parse_vql(raw, pattern_dir=pattern_dir)
    if vql_intent is not None:
        return vql_intent

    lowered = raw.lower()
    node_types = _extract_matches(lowered, _NODE_HINTS)
    edge_types = _extract_matches(lowered, _EDGE_HINTS)
    properties: dict[str, Any] = {}
    patterns = _extract_tokens(lowered, "pattern")
    lens = _extract_tokens(lowered, "lens")
    explain_mode = "explain" in lowered or "why" in lowered or "explain:true" in lowered
    severity = [s for s in _SEVERITY if re.search(rf"\b{s}\b", lowered)]

    for token, (key, value) in _BOOL_HINTS.items():
        if token in lowered:
            properties[key] = value

    for visibility in _VISIBILITY:
        if re.search(rf"\b{visibility}\b", lowered):
            properties["visibility"] = visibility
            break

    for mutability in _MUTABILITY:
        if re.search(rf"\b{mutability}\b", lowered):
            properties["mutability"] = mutability
            break

    _apply_phrase_overrides(lowered, properties)

    limit = _extract_limit(lowered) or 50
    compact_mode = "compact" in lowered or "summary" in lowered
    evidence_mode = "none" if "no evidence" in lowered else "full"
    node_ids = _extract_ids(lowered)

    rule_confidence = 0.0
    rule_candidates: list[dict[str, Any]] = []
    if not patterns:
        all_patterns = get_patterns(pattern_dir)
        patterns, rule_confidence, rule_candidates = resolve_rule_matches(lowered, all_patterns)
        if not patterns and rule_candidates:
            patterns = [entry["pattern_id"] for entry in rule_candidates[:3]]

    # Determine query_kind.
    # In cli_mode, we NEVER silently fall back to "nodes" when the user's
    # query doesn't match explicit edge/fetch/flow/semgrep signals.
    # Instead, default to "pattern" so the CLI outputs the structured
    # header with matches=0 — making it explicit that zero patterns matched.
    query_kind = "pattern" if cli_mode else "nodes"
    if edge_types:
        query_kind = "edges"
    if patterns:
        query_kind = "pattern"
    if lens:
        query_kind = "lens"
    if node_ids:
        query_kind = "fetch"
    flow = _extract_flow(lowered, properties)
    if flow:
        query_kind = "flow"
    elif "edges" in lowered or "relationships" in lowered:
        query_kind = "edges"
    if "semgrep" in lowered:
        query_kind = "semgrep"

    intent = Intent(
        raw_text=raw,
        query_kind=query_kind,
        node_types=sorted(node_types),
        edge_types=sorted(edge_types),
        node_ids=node_ids,
        properties=properties,
        flow=flow,
        patterns=patterns,
        lens=lens,
        severity=severity,
        limit=limit,
        compact_mode=compact_mode,
        evidence_mode=evidence_mode,
        explain_mode=explain_mode,
        include_evidence=evidence_mode == "full",
    )
    min_confidence = _extract_min_confidence(raw)
    if rule_confidence:
        intent.properties["rule_confidence"] = rule_confidence
    if rule_candidates:
        intent.properties["rule_candidates"] = rule_candidates
        if rule_confidence < min_confidence:
            intent.disambiguation_prompt = _build_disambiguation(rule_candidates)
    apply_schema_hints(intent, pattern_dir)
    return intent


def _parse_vql(text: str, *, pattern_dir: Path | None = None) -> Intent | None:
    result = parse_vql_query(text)
    if result is None:
        return None
    if result.error:
        intent = Intent(raw_text=text.strip(), query_kind="logic")
        intent.properties["vql_error"] = result.error.message
        if result.error.hint:
            intent.properties["vql_hint"] = result.error.hint
        apply_schema_hints(intent, pattern_dir)
        return intent

    node_types = _extract_matches(result.head.lower(), _NODE_HINTS)
    if not node_types:
        node_types = ["Function"]

    lowered = text.lower()
    patterns = _extract_tokens(lowered, "pattern")
    lens = _extract_tokens(lowered, "lens")
    severity = [s for s in _SEVERITY if re.search(rf"\b{s}\b", lowered)]
    limit = _extract_limit(lowered) or 50
    compact_mode = "compact" in lowered or "summary" in lowered
    explain_mode = "explain" in lowered or "why" in lowered
    evidence_mode = "none" if "no evidence" in lowered else "full"

    match = _parse_conditions(_strip_vql_options(result.where))

    intent = Intent(
        raw_text=text.strip(),
        query_kind="logic",
        node_types=sorted(node_types),
        match=match,
        patterns=patterns,
        lens=lens,
        severity=severity,
        limit=limit,
        compact_mode=compact_mode,
        evidence_mode=evidence_mode,
        explain_mode=explain_mode,
        include_evidence=evidence_mode == "full",
    )
    apply_schema_hints(intent, pattern_dir)
    return intent


def _parse_conditions(text: str) -> MatchSpec:
    normalized = text.replace(";", " ")
    or_parts = [part.strip() for part in re.split(r"\bor\b", normalized, flags=re.IGNORECASE) if part.strip()]
    if len(or_parts) > 1:
        any_conditions: list[ConditionSpec] = []
        for part in or_parts:
            for condition in _parse_and_conditions(part):
                any_conditions.append(condition)
        return MatchSpec(any=any_conditions)
    return MatchSpec(all=_parse_and_conditions(normalized))


def _strip_vql_options(text: str) -> str:
    stripped = re.sub(r"\blimit\s+\d+\b", " ", text, flags=re.IGNORECASE)
    stripped = re.sub(r"\btop\s+\d+\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bpattern\s*:\s*[a-z0-9,_-]+\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\blens\s*:\s*[a-z0-9,_-]+\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bseverity\s+(critical|high|medium|low|info)\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bcompact\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bsummary\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bexplain\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bno\s+evidence\b", " ", stripped, flags=re.IGNORECASE)
    return stripped


def _parse_and_conditions(text: str) -> list[ConditionSpec]:
    conditions: list[ConditionSpec] = []
    for part in re.split(r"\band\b", text, flags=re.IGNORECASE):
        chunk = part.strip()
        if not chunk:
            continue
        negated = False
        if chunk.lower().startswith("not "):
            negated = True
            chunk = chunk[4:].strip()
        condition = _parse_condition(chunk)
        if condition is None:
            continue
        if negated:
            condition.op = "eq"
            condition.value = False
        conditions.append(condition)
    return conditions


def _parse_condition(text: str) -> ConditionSpec | None:
    text = _apply_aliases(text)
    match = re.match(
        r"^(?P<field>[a-zA-Z0-9_.-]+)\s*(?P<op>!=|==|=|>=|<=|>|<|in|not\s+in|regex)?\s*(?P<value>.+)?$",
        text.strip(),
    )
    if not match:
        return None
    field = _normalize_property_name(match.group("field"))
    op = (match.group("op") or "eq").lower().replace("==", "=")
    value_raw = (match.group("value") or "").strip()

    if not value_raw and op == "eq":
        return ConditionSpec(property=field, op="eq", value=True)

    value = _parse_value(value_raw)
    op = _normalize_op(op)
    return ConditionSpec(property=field, op=op, value=value)


def _parse_value(raw: str) -> Any:
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if raw.startswith("(") and raw.endswith(")"):
        inner = raw[1:-1]
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw.strip("\"'")


def _normalize_op(op: str) -> str:
    op = op.strip()
    if op in {"=", "eq"}:
        return "eq"
    if op in {"!=", "ne"}:
        return "neq"
    if op in {">", "<", ">=", "<="}:
        return op
    if op.startswith("not"):
        return "not_in"
    if op == "in":
        return "in"
    if op == "regex":
        return "regex"
    return "eq"


def _normalize_property_name(field: str) -> str:
    lowered = field.lower().replace("_", " ").strip()
    if lowered in PROPERTY_ALIASES:
        return PROPERTY_ALIASES[lowered]
    return field


def _apply_aliases(text: str) -> str:
    lowered = text.lower()
    for alias, target in PROPERTY_ALIASES.items():
        if alias in lowered:
            lowered = lowered.replace(alias, target)
    return lowered


def _build_disambiguation(candidates: list[dict[str, float]]) -> str:
    top = [entry["pattern_id"] for entry in candidates[:3]]
    joined = ", ".join(top)
    return f"Did you mean one of: {joined}? Try pattern:<id>."


def _extract_matches(text: str, mapping: dict[str, str]) -> list[str]:
    matches: list[str] = []
    for key, value in mapping.items():
        if key in text:
            matches.append(value)
    return list(dict.fromkeys(matches))


def _extract_limit(text: str) -> int | None:
    match = re.search(r"\blimit\s+(\d+)\b", text)
    if not match:
        match = re.search(r"\btop\s+(\d+)\b", text)
        if not match:
            return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_min_confidence(text: str) -> float:
    match = re.search(r"\bmin-confidence\s+([0-9]+(?:\.[0-9]+)?)\b", text, flags=re.IGNORECASE)
    if not match:
        return 0.2
    try:
        value = float(match.group(1))
    except ValueError:
        return 0.2
    return max(0.0, min(1.0, value))


def _extract_tokens(text: str, prefix: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(rf"\b{prefix}\s*:\s*([a-z0-9,_-]+)", text):
        raw = match.group(1)
        tokens.extend([value for value in raw.split(",") if value])
    return list(dict.fromkeys(tokens))


def _extract_ids(text: str) -> list[str]:
    match = re.search(r"\bids?\s*:\s*([a-z0-9,._:-]+)", text)
    if not match:
        return []
    raw_ids = match.group(1)
    return [value.strip() for value in raw_ids.split(",") if value.strip()]


def _apply_phrase_overrides(text: str, properties: dict[str, Any]) -> None:
    if any(phrase in text for phrase in _STATE_WRITE_PHRASES):
        properties["writes_state"] = True
    if any(phrase in text for phrase in _EXCLUDE_MSG_SENDER):
        properties["uses_msg_sender"] = False
    if any(phrase in text for phrase in _EXCLUDE_CONSTRUCTOR):
        properties["is_constructor"] = False
    if any(phrase in text for phrase in _PRIVILEGED_STATE_PHRASES):
        properties["writes_privileged_state"] = True
    for phrase, (key, value) in _PHRASE_PROPERTY_HINTS.items():
        if phrase in text:
            properties[key] = value


def _extract_flow(text: str, properties: dict[str, Any]) -> FlowSpec | None:
    attacker_controlled = any(term in text for term in _ATTACKER_TERMS)
    state_write = any(term in text for term in _STATE_TERMS) and any(term in text for term in _WRITE_TERMS)
    if not (attacker_controlled and state_write):
        return None
    exclude_sources: list[str] = []
    if properties.get("uses_msg_sender") is False or any(phrase in text for phrase in _EXCLUDE_MSG_SENDER):
        exclude_sources.append("msg.sender")
    return FlowSpec(
        from_kinds=["parameter", "env"],
        exclude_sources=exclude_sources,
        target_type="StateVariable",
        edge_type="INPUT_TAINTS_STATE",
    )
