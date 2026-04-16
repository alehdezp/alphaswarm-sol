"""Output formatters for VulnDocs tool responses.

TOON (Token-Optimized Output Notation) format provides 30-50% token reduction
while preserving semantic content for LLM consumption.

Per PHILOSOPHY.md:
- TOON format by default for LLM consumption
- 30-50% token reduction without losing semantic content
- Full JSON available for tools/APIs that need it
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc


class OutputFormat(Enum):
    """Available output formats."""

    TOON = "toon"  # Token-Optimized Output Notation (default for LLM)
    JSON = "json"  # Full JSON (for APIs/tools)
    MARKDOWN = "markdown"  # Human-readable markdown
    COMPACT = "compact"  # Minimal context version


@dataclass
class FormatterConfig:
    """Configuration for output formatting."""

    max_tokens: int = 2000
    include_metadata: bool = False
    include_examples: bool = True
    include_sources: bool = False
    abbreviate_signals: bool = True  # Use short signal names in TOON


class OutputFormatter:
    """Base class for output formatters."""

    def __init__(self, config: Optional[FormatterConfig] = None):
        """Initialize formatter with config."""
        self.config = config or FormatterConfig()

    def format(self, data: Any) -> str:
        """Format data to string output."""
        raise NotImplementedError

    def format_document(self, doc: VulnKnowledgeDoc) -> str:
        """Format a single VulnKnowledgeDoc."""
        raise NotImplementedError

    def format_documents(self, docs: List[VulnKnowledgeDoc]) -> str:
        """Format multiple VulnKnowledgeDocs."""
        raise NotImplementedError

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ~= 4 chars)."""
        return len(text) // 4


class TOONFormatter(OutputFormatter):
    """Token-Optimized Output Notation formatter.

    TOON reduces token count by:
    1. Using short keys and abbreviations
    2. Removing redundant whitespace
    3. Using compact list formats
    4. Omitting optional fields when empty
    5. Using symbols instead of words where clear

    Example TOON output:
    ```
    ▸ REENTRANCY/classic | SEV:critical
    ╌ State update after external call enables callbacks
    ↳ detect: [state_write_after_ext, no_guard]
    ↳ seq: R:bal→X:out→W:bal (vuln) vs R:bal→W:bal→X:out (safe)
    ↳ fix: CEI pattern | alt: reentrancy guard
    ↳ refs: DAO-2016($60M), Fei-2022($80M)
    ```
    """

    # Abbreviation map for common terms
    ABBREVIATIONS = {
        "vulnerability": "vuln",
        "critical": "crit",
        "external": "ext",
        "function": "fn",
        "contract": "ctr",
        "internal": "int",
        "parameter": "param",
        "reentrancy": "reent",
        "access_control": "access",
        "state_variable": "state",
        "modification": "mod",
        "implementation": "impl",
        "authorization": "auth",
        "verification": "verify",
        "exploitation": "exploit",
        "mitigation": "mitig",
    }

    # Signal abbreviations
    SIGNAL_ABBREV = {
        "state_write_after_external_call": "state_write_after_ext",
        "has_reentrancy_guard": "has_guard",
        "no_reentrancy_guard": "no_guard",
        "missing_access_control": "missing_access",
        "uses_delegatecall": "delegatecall",
        "reads_oracle_price": "reads_oracle",
        "has_staleness_check": "has_stale_chk",
        "external_calls_in_loop": "ext_in_loop",
        "unbounded_loop": "unbounded_loop",
    }

    def format(self, data: Any) -> str:
        """Format any data to TOON."""
        if isinstance(data, VulnKnowledgeDoc):
            return self.format_document(data)
        elif isinstance(data, list) and data and isinstance(data[0], VulnKnowledgeDoc):
            return self.format_documents(data)
        elif isinstance(data, dict):
            return self._format_dict(data)
        else:
            return str(data)

    def format_document(self, doc: VulnKnowledgeDoc) -> str:
        """Format VulnKnowledgeDoc to TOON."""
        lines = []

        # Header with category and severity
        sev_symbol = self._severity_symbol(doc.severity.value)
        lines.append(
            f"▸ {doc.category.upper()}/{doc.subcategory} | {sev_symbol}"
        )

        # One-liner
        if doc.one_liner:
            lines.append(f"╌ {doc.one_liner}")

        # Detection signals (abbreviated)
        if doc.detection.graph_signals:
            signals = [
                self.SIGNAL_ABBREV.get(s, s) for s in doc.detection.graph_signals[:5]
            ]
            lines.append(f"↳ detect: [{', '.join(signals)}]")

        # Sequence if available
        if doc.detection.vulnerable_sequence:
            vuln_seq = doc.detection.vulnerable_sequence
            safe_seq = doc.detection.safe_sequence or "?"
            lines.append(f"↳ seq: {vuln_seq} (vuln) vs {safe_seq} (safe)")

        # Fix
        if doc.mitigation.primary_fix:
            fix_line = f"↳ fix: {doc.mitigation.primary_fix}"
            if doc.mitigation.alternative_fixes:
                fix_line += f" | alt: {', '.join(doc.mitigation.alternative_fixes[:2])}"
            lines.append(fix_line)

        # Real exploit references (if enabled and available)
        if self.config.include_examples and doc.examples.real_exploits:
            refs = []
            for exp in doc.examples.real_exploits[:2]:
                ref = exp.name
                if exp.loss:
                    ref += f"({exp.loss})"
                refs.append(ref)
            if refs:
                lines.append(f"↳ refs: {', '.join(refs)}")

        # Pattern linkage
        if doc.pattern_linkage.pattern_ids:
            lines.append(f"↳ patterns: {', '.join(doc.pattern_linkage.pattern_ids)}")

        return "\n".join(lines)

    def format_documents(self, docs: List[VulnKnowledgeDoc]) -> str:
        """Format multiple documents to TOON."""
        parts = []
        total_tokens = 0

        for doc in docs:
            formatted = self.format_document(doc)
            doc_tokens = self.estimate_tokens(formatted)

            if total_tokens + doc_tokens > self.config.max_tokens:
                parts.append(f"[+{len(docs) - len(parts)} more]")
                break

            parts.append(formatted)
            total_tokens += doc_tokens

        return "\n─────\n".join(parts)

    def _severity_symbol(self, severity: str) -> str:
        """Convert severity to compact symbol."""
        symbols = {
            "critical": "SEV:★★★",
            "high": "SEV:★★",
            "medium": "SEV:★",
            "low": "SEV:○",
            "info": "SEV:·",
        }
        return symbols.get(severity.lower(), f"SEV:{severity}")

    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary to TOON."""
        lines = []
        for key, value in data.items():
            if value is None or value == "" or value == []:
                continue
            abbrev_key = self.ABBREVIATIONS.get(key, key)
            if isinstance(value, list):
                if len(value) <= 3:
                    lines.append(f"↳ {abbrev_key}: [{', '.join(str(v) for v in value)}]")
                else:
                    lines.append(
                        f"↳ {abbrev_key}: [{', '.join(str(v) for v in value[:3])}...+{len(value)-3}]"
                    )
            elif isinstance(value, dict):
                lines.append(f"↳ {abbrev_key}: {{...}}")
            else:
                lines.append(f"↳ {abbrev_key}: {value}")
        return "\n".join(lines)


class JSONFormatter(OutputFormatter):
    """Full JSON formatter for API/tool consumption."""

    def format(self, data: Any) -> str:
        """Format to JSON."""
        if isinstance(data, VulnKnowledgeDoc):
            return json.dumps(data.to_dict(), indent=2, ensure_ascii=False)
        elif isinstance(data, list) and data and isinstance(data[0], VulnKnowledgeDoc):
            return json.dumps(
                [d.to_dict() for d in data], indent=2, ensure_ascii=False
            )
        elif isinstance(data, dict):
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)

    def format_document(self, doc: VulnKnowledgeDoc) -> str:
        """Format document to JSON."""
        return json.dumps(doc.to_dict(), indent=2, ensure_ascii=False)

    def format_documents(self, docs: List[VulnKnowledgeDoc]) -> str:
        """Format documents to JSON array."""
        return json.dumps([d.to_dict() for d in docs], indent=2, ensure_ascii=False)


class MarkdownFormatter(OutputFormatter):
    """Human-readable Markdown formatter."""

    def format(self, data: Any) -> str:
        """Format to Markdown."""
        if isinstance(data, VulnKnowledgeDoc):
            return self.format_document(data)
        elif isinstance(data, list) and data and isinstance(data[0], VulnKnowledgeDoc):
            return self.format_documents(data)
        elif isinstance(data, dict):
            return self._dict_to_markdown(data)
        else:
            return str(data)

    def format_document(self, doc: VulnKnowledgeDoc) -> str:
        """Format document to Markdown."""
        return doc.to_markdown(include_metadata=self.config.include_metadata)

    def format_documents(self, docs: List[VulnKnowledgeDoc]) -> str:
        """Format documents to Markdown."""
        parts = []
        for doc in docs:
            parts.append(self.format_document(doc))
        return "\n---\n\n".join(parts)

    def _dict_to_markdown(self, data: Dict[str, Any], level: int = 1) -> str:
        """Convert dictionary to Markdown."""
        lines = []
        for key, value in data.items():
            if value is None or value == "" or value == []:
                continue
            header = "#" * min(level + 1, 4)
            if isinstance(value, dict):
                lines.append(f"{header} {key}")
                lines.append(self._dict_to_markdown(value, level + 1))
            elif isinstance(value, list):
                lines.append(f"**{key}:**")
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{key}:** {value}")
        return "\n".join(lines)


class CompactFormatter(OutputFormatter):
    """Minimal context formatter for token-constrained situations."""

    def format(self, data: Any) -> str:
        """Format to compact output."""
        if isinstance(data, VulnKnowledgeDoc):
            return self.format_document(data)
        elif isinstance(data, list) and data and isinstance(data[0], VulnKnowledgeDoc):
            return self.format_documents(data)
        else:
            return str(data)[:200]

    def format_document(self, doc: VulnKnowledgeDoc) -> str:
        """Format document to compact form."""
        return doc.to_compact_context(max_tokens=self.config.max_tokens)

    def format_documents(self, docs: List[VulnKnowledgeDoc]) -> str:
        """Format documents to compact form."""
        parts = []
        tokens_per_doc = max(100, self.config.max_tokens // len(docs))

        for doc in docs:
            parts.append(doc.to_compact_context(max_tokens=tokens_per_doc))

        return "\n---\n".join(parts)


# =============================================================================
# Factory Functions
# =============================================================================

_FORMATTERS = {
    OutputFormat.TOON: TOONFormatter,
    OutputFormat.JSON: JSONFormatter,
    OutputFormat.MARKDOWN: MarkdownFormatter,
    OutputFormat.COMPACT: CompactFormatter,
}


def get_formatter(
    format: Union[OutputFormat, str],
    config: Optional[FormatterConfig] = None,
) -> OutputFormatter:
    """Get formatter instance for specified format.

    Args:
        format: Output format (OutputFormat enum or string)
        config: Optional formatter configuration

    Returns:
        Formatter instance
    """
    if isinstance(format, str):
        format = OutputFormat(format.lower())

    formatter_class = _FORMATTERS.get(format, TOONFormatter)
    return formatter_class(config)


def format_output(
    data: Any,
    format: Union[OutputFormat, str] = OutputFormat.TOON,
    config: Optional[FormatterConfig] = None,
) -> str:
    """Format data to specified output format.

    Args:
        data: Data to format (VulnKnowledgeDoc, list, dict, etc.)
        format: Output format
        config: Optional formatter configuration

    Returns:
        Formatted string
    """
    formatter = get_formatter(format, config)
    return formatter.format(data)


def format_for_llm(
    data: Any,
    max_tokens: int = 2000,
    include_examples: bool = True,
) -> str:
    """Format data optimized for LLM consumption.

    Uses TOON format by default for token efficiency.

    Args:
        data: Data to format
        max_tokens: Maximum tokens
        include_examples: Whether to include examples

    Returns:
        TOON-formatted string
    """
    config = FormatterConfig(
        max_tokens=max_tokens,
        include_examples=include_examples,
    )
    return format_output(data, OutputFormat.TOON, config)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Args:
        text: Text to estimate

    Returns:
        Approximate token count
    """
    return len(text) // 4
