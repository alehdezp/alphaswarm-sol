"""Bridge Transformer: Plan 02 hook payloads -> Plan 07 EvaluationInput.

Adapter class that converts raw hook observation payloads (from Plan 02
observation hooks) into EvaluationInput instances that the Plan 07 evaluator
can process.

3.1e deferred Item 3: This module bridges the observation layer (hooks)
with the evaluation layer (scoring pipeline).

Input schema (Plan 02 hook payload JSON, per ObservationRecord):
    - tool_use_id: str
    - timestamp: ISO8601 str
    - session_id: str
    - raw_observation: str (or nested in data dict)
    - hook_type: str (PreToolUse | PostToolUse | etc.)
    - event_type: str
    - hook_name: str
    - data: dict (event-specific payload)

Output schema (EvaluationInput):
    - scenario_name: str
    - run_id: str
    - tool_sequence: list[str]
    - bskg_queries: list[dict]
    - response_text: str
    - etc.

CONTRACT_VERSION: 05.1
CONSUMERS: [3.1c-07 (Evaluator)]
"""

from __future__ import annotations

import logging
from typing import Any

from alphaswarm_sol.testing.evaluation.models import EvaluationInput, RunMode

logger = logging.getLogger(__name__)


class BridgeTransformer:
    """Transforms Plan 02 hook payloads into Plan 07 EvaluationInput instances.

    Usage:
        transformer = BridgeTransformer()
        evaluation_input = transformer.transform(hook_payload)
        if evaluation_input is not None:
            # Feed to evaluator
            ...
    """

    def __init__(
        self,
        *,
        default_scenario_name: str = "hook_observation",
        run_mode: RunMode = RunMode.SIMULATED,
    ) -> None:
        self._default_scenario_name = default_scenario_name
        self._run_mode = run_mode

    def transform(self, hook_payload: dict[str, Any]) -> EvaluationInput | None:
        """Transform a Plan 02 hook observation payload into an EvaluationInput.

        Args:
            hook_payload: Raw hook payload dict. Must contain at minimum
                a ``tool_use_id`` field (from ObservationRecord.data or
                top-level). If missing, returns None with a warning.

        Returns:
            EvaluationInput suitable for Plan 07 evaluator, or None if
            the payload lacks required fields (callers filter None).
        """
        if not isinstance(hook_payload, dict):
            logger.warning(
                "BridgeTransformer: payload is not a dict, got %s",
                type(hook_payload).__name__,
            )
            return None

        # Extract tool_use_id — required field
        tool_use_id = (
            hook_payload.get("tool_use_id")
            or hook_payload.get("data", {}).get("tool_use_id")
        )
        if not tool_use_id:
            logger.warning(
                "BridgeTransformer: payload missing tool_use_id, skipping. "
                "Keys present: %s",
                list(hook_payload.keys()),
            )
            return None

        # Extract session_id
        session_id = hook_payload.get("session_id", "")

        # Extract event metadata
        event_type = hook_payload.get("event_type", "")
        hook_name = hook_payload.get("hook_name", "")
        hook_type = hook_payload.get("hook_type", "")
        timestamp = hook_payload.get("timestamp", "")

        # Extract data payload
        data = hook_payload.get("data", {})

        # Build tool sequence from event type and tool info
        tool_sequence = _extract_tool_sequence(data, event_type, hook_type)

        # Extract BSKG queries if present
        bskg_queries = _extract_bskg_queries(data)

        # Build response text from observation content
        response_text = _extract_response_text(data, hook_payload)

        # Build scenario name
        scenario_name = (
            data.get("scenario_name")
            or hook_payload.get("scenario_name")
            or self._default_scenario_name
        )

        # Build run_id from session + tool_use_id
        run_id = f"{session_id}:{tool_use_id}" if session_id else tool_use_id

        return EvaluationInput(
            scenario_name=scenario_name,
            run_id=run_id,
            tool_sequence=tool_sequence,
            bskg_queries=bskg_queries,
            duration_ms=float(data.get("duration_ms", 0.0)),
            response_text=response_text,
            structured_output=_build_structured_output(
                hook_payload, tool_use_id, timestamp, hook_type
            ),
            run_mode=self._run_mode,
        )

    def transform_batch(
        self, payloads: list[dict[str, Any]]
    ) -> list[EvaluationInput]:
        """Transform multiple payloads, filtering out None results.

        Args:
            payloads: List of hook payload dicts.

        Returns:
            List of successfully transformed EvaluationInput instances.
        """
        results = []
        for payload in payloads:
            result = self.transform(payload)
            if result is not None:
                results.append(result)
        return results


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------


def _extract_tool_sequence(
    data: dict[str, Any],
    event_type: str,
    hook_type: str,
) -> list[str]:
    """Extract tool sequence from observation data."""
    tools: list[str] = []

    # Direct tool_name in data
    tool_name = data.get("tool_name", "")
    if tool_name:
        tools.append(tool_name)

    # tool_sequence already present
    if "tool_sequence" in data and isinstance(data["tool_sequence"], list):
        tools.extend(data["tool_sequence"])

    # Infer from event type
    if not tools and event_type == "bskg_query":
        tools.append("Bash")  # BSKG queries run via CLI

    return tools


def _extract_bskg_queries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract BSKG query information from observation data."""
    queries: list[dict[str, Any]] = []

    # Direct bskg_queries list
    if "bskg_queries" in data and isinstance(data["bskg_queries"], list):
        for q in data["bskg_queries"]:
            if isinstance(q, dict):
                queries.append(q)

    # Single query in data
    if "query" in data:
        queries.append(
            {
                "query_text": data["query"],
                "query_type": data.get("query_type", "unknown"),
            }
        )

    return queries


def _extract_response_text(
    data: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """Extract response/observation text from data."""
    # Try various fields where observation text lives
    for key in ("raw_observation", "response_text", "output", "result"):
        value = data.get(key) or payload.get(key)
        if value and isinstance(value, str):
            return value[:4000]  # Truncate for sanity

    return ""


def _build_structured_output(
    payload: dict[str, Any],
    tool_use_id: str,
    timestamp: str,
    hook_type: str,
) -> dict[str, Any]:
    """Build structured output metadata for traceability."""
    return {
        "source": "bridge_transformer",
        "tool_use_id": tool_use_id,
        "timestamp": timestamp,
        "hook_type": hook_type,
        "event_type": payload.get("event_type", ""),
        "hook_name": payload.get("hook_name", ""),
    }
