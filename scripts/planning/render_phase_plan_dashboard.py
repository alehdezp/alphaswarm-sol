#!/usr/bin/env python3
"""
Render a plan-vs-reality dashboard from phase context files and debug artifacts.

The dashboard is intended to detect planning drift:
- Which plans are declared in context files
- Which required governance artifacts exist
- Which declared "Created" artifacts actually exist
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLAN_HEADING_RE = re.compile(r"^###\s+((?:\d+(?:\.\d+)?[a-z]?)-\d{2}):\s*(.+)$")
CREATED_LINE_RE = re.compile(r"^\s*-\s+\*\*Created:\*\*\s*(.+)$")
BACKTICK_RE = re.compile(r"`([^`]+)`")


@dataclass
class ArtifactCheck:
    name: str
    path: str
    exists: bool


@dataclass
class PlanStatus:
    plan_id: str
    title: str
    phase_key: str
    context_file: str
    gate_status: str | None
    required_artifacts: list[ArtifactCheck]
    declared_created_artifacts_total: int
    declared_created_artifacts_found: int
    overall_status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render phase plan dashboard.")
    parser.add_argument(
        "--phase",
        help="Optional phase filter (e.g., 3.1, 3.1b, 3.2).",
    )
    parser.add_argument(
        "--output-json",
        default=".vrs/debug/planning/plan-vs-reality.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--output-md",
        default=".vrs/debug/planning/plan-vs-reality.md",
        help="Output markdown path.",
    )
    return parser.parse_args()


def get_context_files() -> list[Path]:
    phase_root = Path(".planning/phases")
    out: list[Path] = []
    for path in sorted(phase_root.glob("*/context.md")):
        if "v5.0-archive" in path.parts:
            continue
        out.append(path)
    return out


def split_sections(lines: list[str]) -> list[tuple[int, int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        match = PLAN_HEADING_RE.match(line.strip())
        if match:
            plan_id = match.group(1)
            title = match.group(2).strip()
            headings.append((idx, plan_id, title))

    sections: list[tuple[int, int, str, str]] = []
    for i, (start, plan_id, title) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
        sections.append((start, end, plan_id, title))
    return sections


def parse_declared_created_artifacts(section_lines: list[str]) -> list[str]:
    artifacts: list[str] = []
    for line in section_lines:
        match = CREATED_LINE_RE.match(line)
        if not match:
            continue
        payload = match.group(1)
        for token in BACKTICK_RE.findall(payload):
            token = token.strip()
            if not token:
                continue
            if "<" in token or ">" in token:
                continue
            if " " in token:
                continue
            artifacts.append(token)
    return artifacts


def read_gate_status(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return "invalid_json"
    status = payload.get("status")
    if isinstance(status, str):
        return status.lower()
    return None


def required_artifacts_for_plan(plan_id: str) -> list[tuple[str, str]]:
    phase_key = plan_id.split("-", 1)[0]
    return [
        ("gate", f".vrs/debug/phase-{phase_key}/gates/{plan_id}.json"),
        ("hitl", f".vrs/debug/phase-{phase_key}/hitl/{plan_id}.md"),
        (
            "derived_checks",
            f".vrs/debug/phase-{phase_key}/plan-phase/derived-checks/{plan_id}.yaml",
        ),
        ("research", f".vrs/debug/phase-{phase_key}/plan-phase/research/{plan_id}.md"),
    ]


def compute_overall_status(
    gate_status: str | None,
    required: list[ArtifactCheck],
    created_found: int,
    created_total: int,
) -> str:
    required_found = sum(1 for item in required if item.exists)
    if gate_status in {"pass", "passed", "ok"} and required_found == len(required):
        return "implemented"
    if required_found > 0 or created_found > 0:
        return "in_progress"
    if created_total > 0:
        return "planned"
    return "untracked"


def collect_plan_statuses(phase_filter: str | None) -> list[PlanStatus]:
    statuses: list[PlanStatus] = []
    for context_file in get_context_files():
        lines = context_file.read_text().splitlines()
        for start, end, plan_id, title in split_sections(lines):
            phase_key = plan_id.split("-", 1)[0]
            if phase_filter and phase_key != phase_filter:
                continue

            section_lines = lines[start:end]
            created_artifacts = parse_declared_created_artifacts(section_lines)

            required_checks: list[ArtifactCheck] = []
            for name, path_str in required_artifacts_for_plan(plan_id):
                exists = Path(path_str).exists()
                required_checks.append(ArtifactCheck(name=name, path=path_str, exists=exists))

            gate_path = Path(required_checks[0].path)
            gate_status = read_gate_status(gate_path)

            created_found = sum(1 for path in created_artifacts if Path(path).exists())
            overall_status = compute_overall_status(
                gate_status=gate_status,
                required=required_checks,
                created_found=created_found,
                created_total=len(created_artifacts),
            )

            statuses.append(
                PlanStatus(
                    plan_id=plan_id,
                    title=title,
                    phase_key=phase_key,
                    context_file=str(context_file),
                    gate_status=gate_status,
                    required_artifacts=required_checks,
                    declared_created_artifacts_total=len(created_artifacts),
                    declared_created_artifacts_found=created_found,
                    overall_status=overall_status,
                )
            )
    return statuses


def build_summary(statuses: list[PlanStatus]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for item in statuses:
        by_status[item.overall_status] = by_status.get(item.overall_status, 0) + 1

    total_required = sum(len(item.required_artifacts) for item in statuses)
    found_required = sum(
        1 for item in statuses for artifact in item.required_artifacts if artifact.exists
    )

    total_created = sum(item.declared_created_artifacts_total for item in statuses)
    found_created = sum(item.declared_created_artifacts_found for item in statuses)

    return {
        "plans_total": len(statuses),
        "plans_by_status": by_status,
        "required_artifacts_found": found_required,
        "required_artifacts_total": total_required,
        "declared_created_artifacts_found": found_created,
        "declared_created_artifacts_total": total_created,
    }


def render_markdown(summary: dict[str, Any], statuses: list[PlanStatus]) -> str:
    lines: list[str] = []
    lines.append("# Plan-vs-Reality Dashboard")
    lines.append("")
    lines.append(f"- Generated: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- Plans: `{summary['plans_total']}`")
    lines.append(
        f"- Required artifacts: `{summary['required_artifacts_found']}/{summary['required_artifacts_total']}`"
    )
    lines.append(
        "- Declared created artifacts found: "
        f"`{summary['declared_created_artifacts_found']}/{summary['declared_created_artifacts_total']}`"
    )
    lines.append("")
    lines.append("| Plan | Status | Gate | HITL | Checks | Research | Created Artifacts | Context |")
    lines.append("|---|---|---|---|---|---|---|---|")

    def req(plan: PlanStatus, name: str) -> str:
        for item in plan.required_artifacts:
            if item.name == name:
                return "yes" if item.exists else "no"
        return "no"

    for item in statuses:
        gate_value = item.gate_status if item.gate_status else ("yes" if req(item, "gate") == "yes" else "no")
        lines.append(
            "| "
            f"`{item.plan_id}` | `{item.overall_status}` | `{gate_value}` | `{req(item, 'hitl')}` | "
            f"`{req(item, 'derived_checks')}` | `{req(item, 'research')}` | "
            f"`{item.declared_created_artifacts_found}/{item.declared_created_artifacts_total}` | "
            f"`{item.context_file}` |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    statuses = collect_plan_statuses(args.phase)
    summary = build_summary(statuses)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase_filter": args.phase,
        "summary": summary,
        "plans": [asdict(item) for item in statuses],
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(payload, indent=2))
    output_md.write_text(render_markdown(summary, statuses))

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

