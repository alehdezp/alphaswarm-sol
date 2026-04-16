"""
State Validator

Validates .vkg directory integrity.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ValidationResult:
    """Result of validation check."""

    valid: bool
    path: str
    issue: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "path": self.path,
            "issue": self.issue,
        }


class StateValidator:
    """Validates VKG state integrity."""

    def __init__(self, vkg_dir: Path):
        self.vkg_dir = vkg_dir

    def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks."""
        results = []

        # Validate directory existence
        if not self.vkg_dir.exists():
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(self.vkg_dir),
                    issue="VKG directory does not exist",
                )
            )
            return results

        # Validate directory structure
        results.extend(self._validate_structure())

        # Validate JSON files
        results.extend(self._validate_json_files())

        # Validate version consistency
        results.extend(self._validate_versions())

        return results

    def _validate_structure(self) -> List[ValidationResult]:
        """Validate directory structure."""
        results = []

        # These directories should exist for a valid VKG state
        expected_dirs = ["graphs"]
        optional_dirs = ["versions", "cache", "findings"]

        for d in expected_dirs:
            path = self.vkg_dir / d
            if path.exists():
                results.append(ValidationResult(valid=True, path=str(path)))
            else:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(path),
                        issue=f"Missing required directory: {d}",
                    )
                )

        for d in optional_dirs:
            path = self.vkg_dir / d
            if path.exists():
                results.append(ValidationResult(valid=True, path=str(path)))

        return results

    def _validate_json_files(self) -> List[ValidationResult]:
        """Validate JSON file integrity."""
        results = []

        for json_file in self.vkg_dir.rglob("*.json"):
            try:
                content = json_file.read_text()
                if content.strip():  # Skip empty files
                    json.loads(content)
                results.append(ValidationResult(valid=True, path=str(json_file)))
            except json.JSONDecodeError as e:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(json_file),
                        issue=f"Invalid JSON: {e}",
                    )
                )
            except Exception as e:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(json_file),
                        issue=f"Read error: {e}",
                    )
                )

        return results

    def _validate_versions(self) -> List[ValidationResult]:
        """Validate version tracking consistency."""
        results = []

        current_version_file = self.vkg_dir / "current_version.json"
        if not current_version_file.exists():
            # No version tracking - this is ok for legacy projects
            return results

        try:
            data = json.loads(current_version_file.read_text())
            version_id = data.get("current")

            if not version_id:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(current_version_file),
                        issue="No current version ID specified",
                    )
                )
                return results

            # Check if the referenced version file exists
            version_file = self.vkg_dir / "versions" / f"{version_id}.json"
            if version_file.exists():
                results.append(
                    ValidationResult(valid=True, path=str(current_version_file))
                )
            else:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(current_version_file),
                        issue=f"References missing version: {version_id}",
                    )
                )

        except json.JSONDecodeError as e:
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(current_version_file),
                    issue=f"Invalid JSON: {e}",
                )
            )
        except Exception as e:
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(current_version_file),
                    issue=str(e),
                )
            )

        return results

    def validate_graph(self) -> List[ValidationResult]:
        """Validate graph files (identity-based or legacy flat)."""
        results = []
        graphs_dir = self.vkg_dir / "graphs"

        # Find any graph file: check identity subdirs first, then flat files
        graph_path = None
        if graphs_dir.exists():
            for entry in graphs_dir.iterdir():
                if entry.is_dir() and len(entry.name) == 12:
                    for ext in ("graph.toon", "graph.json"):
                        candidate = entry / ext
                        if candidate.exists():
                            graph_path = candidate
                            break
                if graph_path:
                    break
            if graph_path is None:
                for ext in ("graph.toon", "graph.json"):
                    candidate = graphs_dir / ext
                    if candidate.exists():
                        graph_path = candidate
                        break

        if graph_path is None:
            graph_path = graphs_dir / "graph.json"  # default for error message

        if not graph_path.exists():
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(graph_path),
                    issue="Graph file does not exist",
                )
            )
            return results

        try:
            data = json.loads(graph_path.read_text())

            # Check required fields
            if "nodes" not in data:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(graph_path),
                        issue="Missing 'nodes' field",
                    )
                )
            elif not isinstance(data["nodes"], list):
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(graph_path),
                        issue="'nodes' must be a list",
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        valid=True,
                        path=f"{graph_path}:nodes",
                    )
                )

            if "edges" not in data:
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(graph_path),
                        issue="Missing 'edges' field",
                    )
                )
            elif not isinstance(data["edges"], list):
                results.append(
                    ValidationResult(
                        valid=False,
                        path=str(graph_path),
                        issue="'edges' must be a list",
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        valid=True,
                        path=f"{graph_path}:edges",
                    )
                )

        except json.JSONDecodeError as e:
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(graph_path),
                    issue=f"Invalid JSON: {e}",
                )
            )
        except Exception as e:
            results.append(
                ValidationResult(
                    valid=False,
                    path=str(graph_path),
                    issue=str(e),
                )
            )

        return results

    def is_healthy(self) -> bool:
        """Quick health check."""
        results = self.validate_all()
        return all(r.valid for r in results)

    def get_invalid(self) -> List[ValidationResult]:
        """Get only invalid results."""
        return [r for r in self.validate_all() if not r.valid]

    def get_summary(self) -> dict:
        """Get validation summary."""
        results = self.validate_all()
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = sum(1 for r in results if not r.valid)

        return {
            "total_checks": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "healthy": invalid_count == 0,
            "issues": [r.to_dict() for r in results if not r.valid],
        }
