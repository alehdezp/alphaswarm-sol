"""
Skill schema validation for frontmatter v2.

Validates skill markdown files against schemas/skill_schema_v2.json.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
import yaml


class SkillSchemaError(Exception):
    """Raised when skill frontmatter fails schema validation."""
    pass


class SkillSchemaValidator:
    """Validates skill frontmatter against schema v2."""

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize validator with schema.

        Args:
            schema_path: Path to skill_schema_v2.json (auto-detected if None)
        """
        if schema_path is None:
            # Auto-detect schema path relative to project root
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent.parent
            schema_path = project_root / "schemas" / "skill_schema_v2.json"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        self.schema_path = schema_path
        self.schema = json.loads(schema_path.read_text())
        self.validator = jsonschema.Draft7Validator(self.schema)

    def extract_frontmatter(self, skill_file: Path) -> Optional[Dict[str, Any]]:
        """
        Extract YAML frontmatter from skill markdown file.

        Args:
            skill_file: Path to skill .md file

        Returns:
            Parsed YAML frontmatter dict, or None if no frontmatter

        Raises:
            ValueError: If frontmatter is malformed
        """
        content = skill_file.read_text()

        # Match YAML frontmatter block (---\n...\n---)
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return None

        frontmatter_text = match.group(1)

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            return frontmatter
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {skill_file}: {e}")

    def validate(self, frontmatter: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate frontmatter against schema v2.

        Args:
            frontmatter: Parsed frontmatter dict

        Returns:
            (is_valid, errors) tuple where errors is list of validation messages
        """
        errors = []

        # Run JSON schema validation
        for error in self.validator.iter_errors(frontmatter):
            # Build readable error path
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"{path}: {error.message}")

        # Additional semantic validations
        if frontmatter.get("deprecated") and not frontmatter.get("sunset_date"):
            errors.append("deprecated skills should have sunset_date")

        if frontmatter.get("replaces") and not frontmatter.get("deprecated"):
            errors.append("skills with 'replaces' should be marked deprecated")

        # Check evidence_requirements consistency
        evidence_req = frontmatter.get("evidence_requirements", {})
        if evidence_req.get("require_behavioral_signature") and not evidence_req.get("cite_graph_nodes"):
            errors.append("require_behavioral_signature requires cite_graph_nodes=true")

        # Check output_contract has schema
        output_contract = frontmatter.get("output_contract", {})
        if output_contract and "schema" not in output_contract:
            errors.append("output_contract must include 'schema' field")

        return (len(errors) == 0, errors)

    def validate_file(self, skill_file: Path, strict: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate a skill file against schema v2.

        Args:
            skill_file: Path to skill .md file
            strict: If True, missing frontmatter is an error

        Returns:
            (is_valid, errors) tuple
        """
        if not skill_file.exists():
            return (False, [f"File not found: {skill_file}"])

        if not skill_file.suffix == ".md":
            return (False, [f"Not a markdown file: {skill_file}"])

        try:
            frontmatter = self.extract_frontmatter(skill_file)
        except ValueError as e:
            return (False, [str(e)])

        if frontmatter is None:
            if strict:
                return (False, [f"No frontmatter found in {skill_file}"])
            else:
                return (True, [f"WARNING: No frontmatter in {skill_file}"])

        is_valid, errors = self.validate(frontmatter)

        # Prepend file path to all errors
        errors = [f"{skill_file}: {err}" for err in errors]

        return (is_valid, errors)

    def validate_directory(self, directory: Path, strict: bool = True) -> Tuple[int, int, List[str]]:
        """
        Validate all skill .md files in directory recursively.

        Args:
            directory: Directory to scan for .md files
            strict: If True, missing frontmatter is an error

        Returns:
            (valid_count, invalid_count, all_errors) tuple
        """
        if not directory.is_dir():
            return (0, 0, [f"Not a directory: {directory}"])

        valid_count = 0
        invalid_count = 0
        all_errors = []

        # Find all .md files recursively
        md_files = list(directory.rglob("*.md"))

        if not md_files:
            return (0, 0, [f"No .md files found in {directory}"])

        for md_file in md_files:
            # Skip files that are clearly not skills (README, docs, references)
            if md_file.name in ["README.md", "CHANGELOG.md"]:
                continue
            if "references" in md_file.parts or "docs" in md_file.parts:
                continue

            is_valid, errors = self.validate_file(md_file, strict=strict)

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.extend(errors)

        return (valid_count, invalid_count, all_errors)


def validate_skill_schema(
    path: Path,
    strict: bool = True,
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Validate skill file or directory against schema v2.

    Args:
        path: Path to skill file or directory
        strict: If True, missing frontmatter is an error
        schema_path: Path to schema (auto-detected if None)

    Returns:
        (is_valid, errors) tuple
    """
    validator = SkillSchemaValidator(schema_path=schema_path)

    if path.is_file():
        is_valid, errors = validator.validate_file(path, strict=strict)
        return (is_valid, errors)

    elif path.is_dir():
        valid_count, invalid_count, errors = validator.validate_directory(path, strict=strict)
        is_valid = invalid_count == 0

        if is_valid:
            summary = [f"✓ All {valid_count} skills valid"]
        else:
            summary = [f"✗ {invalid_count} skills invalid, {valid_count} valid"]

        return (is_valid, summary + errors)

    else:
        return (False, [f"Path does not exist: {path}"])
