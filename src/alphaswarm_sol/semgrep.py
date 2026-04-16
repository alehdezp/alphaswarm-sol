"""Semgrep integration for Solidity rule packs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
import hashlib

import yaml

from alphaswarm_sol.kg.schema import Evidence, KnowledgeGraph, Node


@dataclass(frozen=True)
class SemgrepRule:
    rule_id: str
    path: Path
    category: str | None = None
    severity: str | None = None


def load_semgrep_rules(rules_root: Path) -> list[SemgrepRule]:
    rules: list[SemgrepRule] = []
    for path in sorted(rules_root.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in data.get("rules", []) or []:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            meta = rule.get("metadata") or {}
            category = meta.get("category")
            if not category:
                if "security" in path.parts:
                    category = "security"
                elif "performance" in path.parts:
                    category = "performance"
            rules.append(
                SemgrepRule(
                    rule_id=str(rule_id),
                    path=path,
                    category=category,
                    severity=rule.get("severity"),
                )
            )
    return rules


def run_semgrep(
    target: Path,
    rules_root: Path,
    *,
    rule_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run semgrep and return normalized findings."""

    cmd = [
        "semgrep",
        "--config",
        str(rules_root),
        "--json",
        "--metrics=off",
        str(target),
    ]
    semgrep_bin = shutil.which("semgrep")
    if semgrep_bin:
        cmd[0] = semgrep_bin
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(f"semgrep failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout or "{}")
    findings: list[dict[str, Any]] = []
    rule_index = {rule.rule_id: rule for rule in load_semgrep_rules(rules_root)}
    for item in payload.get("results", []) or []:
        check_id = item.get("check_id")
        rule_id = _normalize_rule_id(check_id, rule_index)
        if rule_ids and rule_id not in rule_ids:
            continue
        extra = item.get("extra") or {}
        start = item.get("start") or {}
        end = item.get("end") or {}
        rule_meta = rule_index.get(rule_id)
        findings.append(
            {
                "engine": "semgrep",
                "rule_id": rule_id,
                "message": extra.get("message"),
                "severity": extra.get("severity"),
                "category": rule_meta.category if rule_meta else None,
                "path": item.get("path"),
                "line_start": start.get("line"),
                "line_end": end.get("line"),
            }
        )
    return findings


def _normalize_rule_id(check_id: str | None, rule_index: dict[str, SemgrepRule]) -> str | None:
    if not check_id:
        return None
    if check_id in rule_index:
        return check_id
    candidates = [rule_id for rule_id in rule_index if check_id.endswith(rule_id)]
    if candidates:
        return max(candidates, key=len)
    return check_id.split(".")[-1]


def build_semgrep_graph(
    target: Path,
    rules_root: Path,
    *,
    rule_ids: list[str] | None = None,
) -> KnowledgeGraph:
    """Build a minimal graph from Semgrep findings."""

    findings = run_semgrep(target, rules_root, rule_ids=rule_ids)
    graph = KnowledgeGraph(
        metadata={
            "builder": "semgrep",
            "target": str(target),
            "rules_root": str(rules_root),
            "finding_count": len(findings),
        }
    )
    for finding in findings:
        node_id = _semgrep_node_id(finding)
        file_path = _normalize_path(finding.get("path"))
        line_start = finding.get("line_start")
        line_end = finding.get("line_end")
        node = Node(
            id=node_id,
            type="SemgrepFinding",
            label=finding.get("rule_id") or "semgrep-finding",
            properties={
                "rule_id": finding.get("rule_id"),
                "category": finding.get("category"),
                "severity": finding.get("severity"),
                "message": finding.get("message"),
                "path": file_path,
                "line_start": line_start,
                "line_end": line_end,
            },
            evidence=[Evidence(file=file_path, line_start=line_start, line_end=line_end)]
            if file_path
            else [],
        )
        graph.add_node(node)
    return graph


def _semgrep_node_id(finding: dict[str, Any]) -> str:
    raw = (
        f"{finding.get('rule_id')}:{finding.get('path')}:"
        f"{finding.get('line_start')}:{finding.get('line_end')}"
    )
    return f"semgrep:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _normalize_path(path: Any) -> str | None:
    if not path:
        return None
    return str(path)
