#!/usr/bin/env python3
"""
Validate plan dependencies against PLAN-INDEX and check referenced paths.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

PLAN_DIR = pathlib.Path(".planning/phases/07.3.1.6-full-testing-hardening")
PLAN_INDEX = PLAN_DIR / "07.3.1.6-PLAN-INDEX.md"


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text().splitlines()
    if not text or text[0].strip() != "---":
        return {}
    end_idx = None
    for i in range(1, len(text)):
        if text[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    data = {}
    for line in text[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_dep_list(value: str) -> list[str]:
    value = value.strip()
    if not value or value == "[]":
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed]
    except Exception:
        pass
    # Fallback: split by comma
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_plan_index() -> dict[str, list[str]]:
    if not PLAN_INDEX.exists():
        raise FileNotFoundError(f"Missing {PLAN_INDEX}")
    deps = {}
    for line in PLAN_INDEX.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        plan_path = cells[0].strip("`")
        if not plan_path.endswith("-PLAN.md"):
            continue
        depends_cell = cells[3]
        if depends_cell in {"", "-", "—"}:
            depends = []
        else:
            depends = [d.strip() for d in depends_cell.split(",") if d.strip()]
        plan_name = pathlib.Path(plan_path).name
        deps[plan_name] = depends
    return deps


def extract_paths(plan_text: str) -> tuple[list[str], list[str]]:
    files_modified = []
    other_paths = []
    in_files_modified = False
    for line in plan_text.splitlines():
        if line.strip().startswith("files_modified:"):
            in_files_modified = True
            continue
        if in_files_modified:
            if not line.startswith("  - "):
                in_files_modified = False
            else:
                path = line.strip()[2:].strip()
                files_modified.append(path)
                continue
        # path: "..."
        stripped = line.strip()
        if stripped.startswith("path:"):
            value = stripped.split(":", 1)[1].strip().strip('"')
            other_paths.append(value)
    return files_modified, other_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail on any missing path outside files_modified")
    args = parser.parse_args()

    plan_index_deps = parse_plan_index()

    errors = []
    plan_files = sorted(PLAN_DIR.glob("07.3.1.6-*-PLAN.md"))
    for plan_file in plan_files:
        fm = parse_frontmatter(plan_file)
        depends = parse_dep_list(fm.get("depends_on", "[]"))
        index_depends = plan_index_deps.get(plan_file.name)
        if index_depends is None:
            errors.append(f"Plan missing from PLAN-INDEX: {plan_file.name}")
        else:
            if depends != index_depends:
                errors.append(
                    f"Dependency mismatch {plan_file.name}: frontmatter={depends} index={index_depends}"
                )

        text = plan_file.read_text()
        files_modified, other_paths = extract_paths(text)
        files_modified_set = {p for p in files_modified}
        for path in other_paths:
            if not path:
                continue
            if not re.match(r"^(\.|docs|scripts|src|tests|skills|schemas)/", path):
                continue
            if pathlib.Path(path).exists():
                continue
            if path in files_modified_set:
                continue
            if args.strict:
                errors.append(f"Missing referenced path in {plan_file.name}: {path}")

    if errors:
        print("PLAN consistency check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PLAN consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
