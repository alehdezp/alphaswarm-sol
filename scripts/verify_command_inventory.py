#!/usr/bin/env python3
"""
Verify COMMAND-INVENTORY.md entries have required fields and transcripts.

Usage:
  python3 scripts/verify_command_inventory.py
  python3 scripts/verify_command_inventory.py --strict --min-lines 50
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

INVENTORY_PATH = pathlib.Path(".planning/testing/COMMAND-INVENTORY.md")

TRUTHY = {"yes", "y", "true", "1"}
FALSY = {"no", "n", "false", "0", ""}


def parse_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    header = []
    rows = []
    in_table = False
    for line in lines:
        if line.startswith("|") and "|" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                header = cells
                in_table = True
                continue
            if set(cells) == {"---"} or all(c == "---" for c in cells):
                continue
            if len(cells) == len(header):
                rows.append(cells)
        elif in_table:
            break
    return header, rows


def normalize_header(header: list[str]) -> dict[str, int]:
    mapping = {}
    for idx, name in enumerate(header):
        key = re.sub(r"[^a-z]+", "", name.lower())
        mapping[key] = idx
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="enforce transcript existence for verified entries")
    parser.add_argument("--min-lines", type=int, default=1, help="minimum transcript line count for verified entries")
    args = parser.parse_args()

    if not INVENTORY_PATH.exists():
        print(f"ERROR: {INVENTORY_PATH} not found")
        return 2

    lines = INVENTORY_PATH.read_text().splitlines()
    header, rows = parse_table(lines)
    if not header or not rows:
        print("ERROR: No table found in COMMAND-INVENTORY.md")
        return 2

    header_map = normalize_header(header)
    required_cols = ["commandpurpose", "command", "verified", "transcript"]
    missing_cols = [c for c in required_cols if c not in header_map]
    if missing_cols:
        print(f"ERROR: Missing required columns: {missing_cols}")
        return 2

    errors = []
    for row in rows:
        purpose = row[header_map["commandpurpose"]].strip()
        command = row[header_map["command"]].strip("`").strip()
        verified = row[header_map["verified"]].strip().lower()
        transcript = row[header_map["transcript"]].strip()

        if not purpose or not command:
            errors.append(f"Row missing purpose/command: {row}")
            continue

        if verified in TRUTHY:
            if not transcript:
                errors.append(f"Verified entry missing transcript: {purpose}")
                continue
            transcript_path = pathlib.Path(transcript)
            if not transcript_path.exists():
                errors.append(f"Transcript missing: {purpose} -> {transcript}")
                continue
            if args.min_lines > 1:
                try:
                    line_count = sum(1 for _ in transcript_path.read_text().splitlines())
                except UnicodeDecodeError:
                    line_count = sum(1 for _ in transcript_path.read_bytes().splitlines())
                if line_count < args.min_lines:
                    errors.append(
                        f"Transcript too short ({line_count} < {args.min_lines}): {purpose} -> {transcript}"
                    )
        elif verified in FALSY:
            if args.strict and transcript:
                transcript_path = pathlib.Path(transcript)
                if not transcript_path.exists():
                    errors.append(f"Transcript path set but missing: {purpose} -> {transcript}")
        else:
            errors.append(f"Invalid Verified value '{verified}' for: {purpose}")

    if errors:
        print("COMMAND-INVENTORY verification failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("COMMAND-INVENTORY verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
