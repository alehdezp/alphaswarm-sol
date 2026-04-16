#!/usr/bin/env python3
"""VQL Query Syntax Validator.

This script validates VQL queries against the BSKG schema.

Usage:
    python scripts/validate_vql_queries.py                    # Validate all queries
    python scripts/validate_vql_queries.py --dry-run FILE.sol # Dry-run on contract
    python scripts/validate_vql_queries.py --query VQL-MIN-04 # Validate specific query
    python scripts/validate_vql_queries.py --verbose          # Detailed output

Exit codes:
    0: All queries valid
    1: Validation errors found
    2: Schema or query file not found
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
VQL_QUERY_PATH = PROJECT_ROOT / "src" / "alphaswarm_sol" / "kg" / "queries" / "vql_minimum_set.yaml"
BSKG_SCHEMA_PATH = PROJECT_ROOT / ".vrs" / "schema" / "bskg-schema.yaml"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ValidationError:
    """A single validation error."""
    query_id: str
    error_code: str
    message: str
    field: str | None = None
    suggestion: str | None = None

    def __str__(self) -> str:
        loc = f" (field: {self.field})" if self.field else ""
        sug = f"\n  Suggestion: {self.suggestion}" if self.suggestion else ""
        return f"[{self.error_code}] {self.query_id}{loc}: {self.message}{sug}"


@dataclass
class ValidationResult:
    """Result of validating a single query."""
    query_id: str
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report."""
    total_queries: int
    valid_queries: int
    invalid_queries: int
    results: list[ValidationResult] = field(default_factory=list)
    schema_version: str = ""
    query_version: str = ""

    @property
    def success(self) -> bool:
        return self.invalid_queries == 0


# =============================================================================
# Schema Loader
# =============================================================================

class BSKGSchema:
    """Loaded BSKG schema for validation."""

    def __init__(self, schema_path: Path) -> None:
        with open(schema_path) as f:
            self.schema = yaml.safe_load(f)

        self.version = self.schema.get("metadata", {}).get("version", "unknown")
        self._load_types()

    def _load_types(self) -> None:
        """Extract type definitions from schema."""
        self.node_types = set(self.schema.get("node_types", {}).keys())
        self.edge_types = set(self.schema.get("edge_types", {}).keys())
        self.semantic_ops = set(self.schema.get("semantic_operations", {}).keys())

        # Build property map for each node type
        self.node_properties: dict[str, set[str]] = {}
        for node_type, defn in self.schema.get("node_types", {}).items():
            props = set()
            for prop in defn.get("required_properties", []):
                if isinstance(prop, dict):
                    props.update(prop.keys())
                else:
                    props.add(prop)
            for prop, _ in defn.get("optional_properties", {}).items():
                props.add(prop)
            self.node_properties[node_type] = props

        # Build property map for each edge type
        self.edge_properties: dict[str, set[str]] = {}
        for edge_type, defn in self.schema.get("edge_types", {}).items():
            props = set(defn.get("properties", {}).keys())
            # Add common edge properties
            props.update({"source", "target", "type", "id"})
            self.edge_properties[edge_type] = props

        # Short codes
        self.op_short_codes: dict[str, str] = {}
        for op, defn in self.schema.get("semantic_operations", {}).items():
            if isinstance(defn, dict) and "short_code" in defn:
                self.op_short_codes[defn["short_code"]] = op

    def is_valid_node_type(self, type_name: str) -> bool:
        return type_name in self.node_types

    def is_valid_edge_type(self, type_name: str) -> bool:
        return type_name in self.edge_types

    def is_valid_semantic_op(self, op_name: str) -> bool:
        return op_name in self.semantic_ops or op_name in self.op_short_codes

    def get_node_properties(self, node_type: str) -> set[str]:
        return self.node_properties.get(node_type, set())

    def get_edge_properties(self, edge_type: str) -> set[str]:
        return self.edge_properties.get(edge_type, set())


# =============================================================================
# Query Validator
# =============================================================================

class VQLValidator:
    """Validates VQL queries against BSKG schema."""

    def __init__(self, schema: BSKGSchema, verbose: bool = False) -> None:
        self.schema = schema
        self.verbose = verbose

    def validate_query(self, query_id: str, query_def: dict[str, Any]) -> ValidationResult:
        """Validate a single VQL query."""
        errors: list[ValidationError] = []
        warnings: list[str] = []

        # Get the inner query definition
        query = query_def.get("query", {})

        # Validate structure
        errors.extend(self._validate_structure(query_id, query))

        # Validate FROM clause
        errors.extend(self._validate_from_clause(query_id, query))

        # Validate SELECT clause
        errors.extend(self._validate_select_clause(query_id, query))

        # Validate WHERE clause
        errors.extend(self._validate_where_clause(query_id, query))

        # Validate path queries
        if "path" in query:
            errors.extend(self._validate_path_clause(query_id, query))

        # Check returns schema
        if "returns" in query_def:
            warnings.extend(self._check_returns_schema(query_id, query_def))

        return ValidationResult(
            query_id=query_id,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_structure(self, query_id: str, query: dict[str, Any]) -> list[ValidationError]:
        """Validate basic query structure."""
        errors: list[ValidationError] = []

        # Must have either select+from or path
        has_select_from = "select" in query and "from" in query
        has_path = "path" in query

        if not has_select_from and not has_path:
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-001",
                message="Query must have 'select' and 'from' clauses, or 'path' clause",
                suggestion="Add a 'select' and 'from' clause, or use 'path' for path queries",
            ))

        return errors

    def _validate_from_clause(self, query_id: str, query: dict[str, Any]) -> list[ValidationError]:
        """Validate FROM clause."""
        errors: list[ValidationError] = []
        from_clause = query.get("from", [])

        if not from_clause:
            return errors

        for source in from_clause:
            alias = source.get("alias")
            if not alias:
                errors.append(ValidationError(
                    query_id=query_id,
                    error_code="VQL-002",
                    message="FROM source missing required 'alias' field",
                    field="from",
                ))
                continue

            # Check node type
            node_type = source.get("type")
            edge_type = source.get("type_edge")

            if node_type and not self.schema.is_valid_node_type(node_type):
                errors.append(ValidationError(
                    query_id=query_id,
                    error_code="VQL-010",
                    message=f"Unknown node type: {node_type}",
                    field=f"from.{alias}.type",
                    suggestion=f"Valid types: {', '.join(sorted(self.schema.node_types))}",
                ))

            if edge_type and not self.schema.is_valid_edge_type(edge_type):
                errors.append(ValidationError(
                    query_id=query_id,
                    error_code="VQL-011",
                    message=f"Unknown edge type: {edge_type}",
                    field=f"from.{alias}.type_edge",
                    suggestion=f"Valid types: {', '.join(sorted(self.schema.edge_types))}",
                ))

        return errors

    def _validate_select_clause(self, query_id: str, query: dict[str, Any]) -> list[ValidationError]:
        """Validate SELECT clause."""
        errors: list[ValidationError] = []
        select_clause = query.get("select", [])

        if not select_clause:
            return errors

        # Build alias map from FROM clause
        aliases: dict[str, str] = {}  # alias -> type
        for source in query.get("from", []):
            alias = source.get("alias")
            node_type = source.get("type")
            edge_type = source.get("type_edge")
            if alias:
                aliases[alias] = node_type or edge_type or "unknown"

        # Check each select field
        for field_def in select_clause:
            if isinstance(field_def, dict):
                for field_name, field_expr in field_def.items():
                    errors.extend(self._validate_field_expression(
                        query_id, field_expr, aliases, f"select.{field_name}"
                    ))

        return errors

    def _validate_field_expression(
        self,
        query_id: str,
        expr: str,
        aliases: dict[str, str],
        context: str,
    ) -> list[ValidationError]:
        """Validate a field expression like 'fn.properties.visibility'."""
        errors: list[ValidationError] = []

        if not isinstance(expr, str):
            return errors

        # Skip complex expressions
        if " OR " in expr or " AND " in expr or ">" in expr or "<" in expr:
            return errors

        parts = expr.split(".")
        if not parts:
            return errors

        alias = parts[0]

        # Special handling for path queries
        if alias == "path":
            return errors

        if alias not in aliases:
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-003",
                message=f"Undefined alias '{alias}' in expression: {expr}",
                field=context,
                suggestion=f"Available aliases: {', '.join(sorted(aliases.keys()))}",
            ))

        return errors

    def _validate_where_clause(self, query_id: str, query: dict[str, Any]) -> list[ValidationError]:
        """Validate WHERE clause."""
        errors: list[ValidationError] = []
        where_clause = query.get("where", [])

        if not where_clause:
            return errors

        for idx, condition in enumerate(where_clause):
            cond_str = condition.get("condition", "") if isinstance(condition, dict) else str(condition)

            # Check for semantic operations in conditions
            if "CONTAINS" in cond_str and "semantic_ops" in cond_str:
                # Extract operation names
                for op in self.schema.semantic_ops:
                    if op in cond_str:
                        continue  # Valid operation

                # Check for invalid operations (rough check)
                import re
                matches = re.findall(r"'([A-Z_]+)'", cond_str)
                for match in matches:
                    if match not in self.schema.semantic_ops and match not in ["public", "external", "internal", "private"]:
                        # Could be a semantic op, warn if not found
                        if self.verbose:
                            errors.append(ValidationError(
                                query_id=query_id,
                                error_code="VQL-012",
                                message=f"Possible unknown semantic operation: {match}",
                                field=f"where[{idx}]",
                            ))

        return errors

    def _validate_path_clause(self, query_id: str, query: dict[str, Any]) -> list[ValidationError]:
        """Validate PATH clause for path queries."""
        errors: list[ValidationError] = []
        path_clause = query.get("path", {})

        if not path_clause:
            return errors

        # Validate start
        start = path_clause.get("start", {})
        start_type = start.get("type")
        if start_type and not self.schema.is_valid_node_type(start_type):
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-010",
                message=f"Unknown node type in path.start: {start_type}",
                field="path.start.type",
            ))

        # Validate end
        end = path_clause.get("end", {})
        end_type = end.get("type")
        if end_type and not self.schema.is_valid_node_type(end_type):
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-010",
                message=f"Unknown node type in path.end: {end_type}",
                field="path.end.type",
            ))

        # Validate edge type
        edges = path_clause.get("edges", {})
        edge_type = edges.get("type")
        if edge_type and not self.schema.is_valid_edge_type(edge_type):
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-011",
                message=f"Unknown edge type in path.edges: {edge_type}",
                field="path.edges.type",
            ))

        # Validate hop constraints
        min_hops = edges.get("min_hops", 1)
        max_hops = edges.get("max_hops", 5)
        if min_hops < 0:
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-020",
                message="min_hops cannot be negative",
                field="path.edges.min_hops",
            ))
        if max_hops < min_hops:
            errors.append(ValidationError(
                query_id=query_id,
                error_code="VQL-021",
                message="max_hops cannot be less than min_hops",
                field="path.edges.max_hops",
            ))

        return errors

    def _check_returns_schema(self, query_id: str, query_def: dict[str, Any]) -> list[str]:
        """Check returns schema for warnings (not errors)."""
        warnings: list[str] = []
        returns = query_def.get("returns", {})
        schema = returns.get("schema", {})

        # Check that all select fields have corresponding return schema
        select_clause = query_def.get("query", {}).get("select", [])
        select_fields = set()
        for field_def in select_clause:
            if isinstance(field_def, dict):
                select_fields.update(field_def.keys())

        schema_fields = set(schema.keys())
        missing = select_fields - schema_fields
        if missing:
            warnings.append(f"Fields in select but not in returns schema: {missing}")

        return warnings


# =============================================================================
# Dry-Run Executor
# =============================================================================

class DryRunExecutor:
    """Execute VQL queries on a real contract for validation."""

    def __init__(self, contract_path: Path) -> None:
        self.contract_path = contract_path
        self.graph = None

    def build_graph(self) -> bool:
        """Build the knowledge graph."""
        try:
            from alphaswarm_sol.kg.builder.core import build_graph
            self.graph = build_graph(self.contract_path)
            return True
        except Exception as e:
            print(f"Failed to build graph: {e}")
            return False

    def execute_query(self, query_id: str, query_def: dict[str, Any]) -> dict[str, Any]:
        """Execute a query and return results."""
        if self.graph is None:
            return {"error": "Graph not built"}

        query = query_def.get("query", {})
        results = []

        # Execute based on query type
        if "from" in query:
            results = self._execute_from_query(query)
        elif "path" in query:
            results = self._execute_path_query(query)

        return {
            "query_id": query_id,
            "result_count": len(results),
            "sample": results[:3] if results else [],
        }

    def _execute_from_query(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a FROM-based query."""
        results = []
        from_clause = query.get("from", [])

        # Simple implementation: iterate over nodes matching type
        for source in from_clause:
            node_type = source.get("type")
            if node_type:
                for node in self.graph.nodes.values():
                    if node.type == node_type:
                        results.append({
                            "id": node.id,
                            "label": node.label,
                            "type": node.type,
                        })

        return results

    def _execute_path_query(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a path query."""
        # Path queries require PathEnumerator
        try:
            from alphaswarm_sol.kg.paths import PathEnumerator
            enumerator = PathEnumerator(self.graph, max_depth=3, max_paths=10)
            paths = enumerator.enumerate_paths()
            return [{"path_id": p.id, "steps": len(p.steps)} for p in paths]
        except Exception as e:
            return [{"error": str(e)}]


# =============================================================================
# Main
# =============================================================================

def load_vql_queries(path: Path) -> dict[str, Any]:
    """Load VQL query file."""
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VQL queries against BSKG schema")
    parser.add_argument("--query", "-q", help="Validate specific query ID")
    parser.add_argument("--dry-run", "-d", type=Path, help="Dry-run on contract file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--vql-path", type=Path, default=VQL_QUERY_PATH, help="Path to VQL queries")
    parser.add_argument("--schema-path", type=Path, default=BSKG_SCHEMA_PATH, help="Path to BSKG schema")
    args = parser.parse_args()

    # Check files exist
    if not args.vql_path.exists():
        print(f"ERROR: VQL query file not found: {args.vql_path}")
        return 2
    if not args.schema_path.exists():
        print(f"ERROR: BSKG schema file not found: {args.schema_path}")
        return 2

    # Load schema and queries
    print(f"Loading BSKG schema from {args.schema_path}")
    schema = BSKGSchema(args.schema_path)
    print(f"  Schema version: {schema.version}")
    print(f"  Node types: {len(schema.node_types)}")
    print(f"  Edge types: {len(schema.edge_types)}")
    print(f"  Semantic operations: {len(schema.semantic_ops)}")

    print(f"\nLoading VQL queries from {args.vql_path}")
    vql_data = load_vql_queries(args.vql_path)
    queries = vql_data.get("queries", {})
    query_version = vql_data.get("metadata", {}).get("version", "unknown")
    print(f"  Query version: {query_version}")
    print(f"  Total queries: {len(queries)}")

    # Filter to specific query if requested
    if args.query:
        if args.query not in queries:
            print(f"ERROR: Query '{args.query}' not found")
            return 2
        queries = {args.query: queries[args.query]}

    # Validate queries
    validator = VQLValidator(schema, verbose=args.verbose)
    results: list[ValidationResult] = []

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    for query_id, query_def in sorted(queries.items()):
        result = validator.validate_query(query_id, query_def)
        results.append(result)

        status = "PASS" if result.valid else "FAIL"
        print(f"\n{query_id}: {status}")

        if result.errors:
            for error in result.errors:
                print(f"  ERROR: {error}")

        if result.warnings and args.verbose:
            for warning in result.warnings:
                print(f"  WARNING: {warning}")

        if args.verbose and result.valid:
            query = query_def.get("query", {})
            name = query_def.get("name", "unnamed")
            category = query_def.get("category", "unknown")
            print(f"  Name: {name}")
            print(f"  Category: {category}")

    # Summary
    valid_count = sum(1 for r in results if r.valid)
    invalid_count = len(results) - valid_count

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total queries:   {len(results)}")
    print(f"Valid queries:   {valid_count}")
    print(f"Invalid queries: {invalid_count}")

    # Dry-run if requested
    if args.dry_run:
        print("\n" + "=" * 60)
        print(f"DRY-RUN ON {args.dry_run}")
        print("=" * 60)

        if not args.dry_run.exists():
            print(f"ERROR: Contract file not found: {args.dry_run}")
            return 2

        executor = DryRunExecutor(args.dry_run)
        if executor.build_graph():
            print(f"Graph built: {len(executor.graph.nodes)} nodes, {len(executor.graph.edges)} edges")

            for query_id, query_def in sorted(queries.items()):
                result = executor.execute_query(query_id, query_def)
                print(f"\n{query_id}: {result['result_count']} results")
                if result.get("sample"):
                    for item in result["sample"]:
                        print(f"  - {item}")
        else:
            print("ERROR: Failed to build graph for dry-run")

    # Return exit code
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
