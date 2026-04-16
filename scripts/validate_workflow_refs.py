#!/usr/bin/env python3
"""
Validate that skills and agents registries include workflow_refs,
that referenced workflow docs exist, and that workflow docs
list the expected skills/subagents for alignment.
"""

from pathlib import Path
import sys
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [
    ROOT / "src/alphaswarm_sol/skills/registry.yaml",
    ROOT / "src/alphaswarm_sol/agents/catalog.yaml",
]

DOCS_WORKFLOWS_ROOT = ROOT / "docs" / "workflows"


def normalize_item(item: str) -> str:
    item = item.strip().strip("`")
    item = item.rstrip(",")
    if not item:
        return ""
    return item.split()[0]


def parse_workflow_doc(path: Path) -> dict:
    skills = set()
    subagents = set()
    has_skills_section = False
    has_subagents_section = False
    current = None

    for line in path.read_text().splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            if heading == "skills":
                current = "skills"
                has_skills_section = True
            elif heading == "subagents":
                current = "subagents"
                has_subagents_section = True
            else:
                current = None
            continue

        if current and line.lstrip().startswith("- "):
            item = normalize_item(line.strip()[2:])
            if not item:
                continue
            if current == "skills":
                skills.add(item)
            elif current == "subagents":
                subagents.add(item)

    return {
        "skills": skills,
        "subagents": subagents,
        "has_skills_section": has_skills_section,
        "has_subagents_section": has_subagents_section,
    }


def parse_workflow_refs(path: Path) -> dict:
    entries = {}
    current_id = None
    in_refs = False
    refs_indent = None

    for line in path.read_text().splitlines():
        if line.strip().startswith("#"):
            continue

        m = re.match(r"^\s*-\s+id:\s*(\S+)", line)
        if m:
            current_id = m.group(1)
            entries.setdefault(current_id, [])
            in_refs = False
            refs_indent = None
            continue

        if current_id and re.match(r"^\s*workflow_refs:\s*$", line):
            in_refs = True
            refs_indent = len(line) - len(line.lstrip())
            continue

        if in_refs:
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= refs_indent and not line.lstrip().startswith("- "):
                in_refs = False
                refs_indent = None
                continue
            if line.lstrip().startswith("- "):
                ref = line.strip().lstrip("- ").strip()
                if ref:
                    entries[current_id].append(ref)

    return entries


def validate_refs(label: str, path: Path, workflow_index: dict, strict: bool) -> tuple[int, int]:
    errors = 0
    warnings = 0
    entries = parse_workflow_refs(path)
    if not entries:
        print(f"[error] {label}: no entries found in {path}")
        return 1, 0

    for entry_id, refs in entries.items():
        if not refs:
            print(f"[error] {label}: {entry_id} missing workflow_refs")
            errors += 1
            continue
        for ref in refs:
            ref_path = (ROOT / ref).resolve()
            if not ref_path.exists():
                print(f"[error] {label}: {entry_id} references missing file {ref}")
                errors += 1
                continue
            if DOCS_WORKFLOWS_ROOT in ref_path.parents:
                doc_info = workflow_index.get(ref_path)
                if not doc_info:
                    doc_info = parse_workflow_doc(ref_path)
                    workflow_index[ref_path] = doc_info
                if label == "registry.yaml":
                    expected = entry_id if entry_id.startswith("vrs-") else f"vrs-{entry_id}"
                    if not doc_info["has_skills_section"]:
                        print(f"[warn] workflow {ref} missing Skills section")
                        warnings += 1
                    elif expected not in doc_info["skills"]:
                        print(f"[warn] workflow {ref} missing skill {expected}")
                        warnings += 1
                elif label == "catalog.yaml":
                    expected = entry_id
                    if not doc_info["has_subagents_section"]:
                        print(f"[warn] workflow {ref} missing Subagents section")
                        warnings += 1
                    elif expected not in doc_info["subagents"]:
                        print(f"[warn] workflow {ref} missing subagent {expected}")
                        warnings += 1

    if errors == 0:
        print(f"[ok] {label}: {len(entries)} entries validated in {path}")
    if warnings and strict:
        errors += warnings
    return errors, warnings


def main() -> int:
    strict = False
    args = []
    for arg in sys.argv[1:]:
        if arg == "--strict":
            strict = True
            continue
        args.append(arg)
    files = [Path(p) for p in args] if args else DEFAULT_FILES
    total_errors = 0
    total_warnings = 0
    workflow_index = {}
    for path in files:
        label = path.name
        if not path.exists():
            print(f"[error] missing file: {path}")
            total_errors += 1
            continue
        errors, warnings = validate_refs(label, path, workflow_index, strict)
        total_errors += errors
        total_warnings += warnings
    if total_warnings and not strict:
        print(f"[warn] {total_warnings} alignment warnings (run with --strict to fail)")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
