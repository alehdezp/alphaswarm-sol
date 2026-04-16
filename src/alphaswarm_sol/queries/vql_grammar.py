"""Explicit VQL grammar with error hints."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VQLParseError:
    message: str
    hint: str | None = None


@dataclass(frozen=True)
class VQLParseResult:
    head: str
    where: str
    error: VQLParseError | None = None


def parse_vql_query(text: str) -> VQLParseResult | None:
    lowered = text.lower().strip()
    if not (lowered.startswith("find ") or lowered.startswith("select ") or lowered.startswith("show ")):
        return None

    match = re.match(r"^(find|select|show)\s+(.+)$", text.strip(), flags=re.IGNORECASE)
    if not match:
        return VQLParseResult(
            head=text.strip(),
            where="",
            error=VQLParseError(
                message="Unable to parse VQL head.",
                hint="Use 'find <type> where <conditions>'.",
            ),
        )

    remainder = match.group(2)
    if " where " not in remainder.lower():
        return VQLParseResult(
            head=remainder.strip(),
            where="",
            error=VQLParseError(
                message="Missing WHERE clause.",
                hint="Example: find functions where visibility in [public, external].",
            ),
        )

    head, where = re.split(r"\bwhere\b", remainder, maxsplit=1, flags=re.IGNORECASE)
    head = head.strip()
    where = where.strip()
    if not head:
        return VQLParseResult(
            head="",
            where=where,
            error=VQLParseError(
                message="Missing target type after find/select/show.",
                hint="Example: find functions where ...",
            ),
        )
    if not where:
        return VQLParseResult(
            head=head,
            where="",
            error=VQLParseError(
                message="Missing conditions after WHERE.",
                hint="Example: find functions where writes_state.",
            ),
        )
    return VQLParseResult(head=head, where=where)
