"""VQL 2.0 LLM Guidance System - MCP-style protocol for LLM interaction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alphaswarm_sol.queries.patterns import get_patterns
from alphaswarm_sol.vql2.lexer import KEYWORDS, Lexer, LexerError, TokenType
from alphaswarm_sol.vql2.parser import Parser, ParseError
from alphaswarm_sol.vql2.semantic import SemanticAnalyzer, VKGSchema


class LLMGuidanceSystem:
    """Provides MCP-style guidance for LLMs constructing VQL 2.0 queries."""

    OPERATORS = ["=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "REGEX", "LIKE", "CONTAINS", "CONTAINS_ANY", "CONTAINS_ALL"]

    QUERY_TYPES = ["DESCRIBE", "FIND", "MATCH", "FLOW", "PATTERN"]

    CLAUSES = ["WHERE", "RETURN", "WITH", "GROUP BY", "HAVING", "ORDER BY", "LIMIT", "OFFSET"]

    def __init__(self, schema: VKGSchema | None = None, pattern_dir: Path | None = None):
        self.schema = schema or VKGSchema.default()
        self.pattern_dir = pattern_dir

    # ========================================
    # Schema Discovery Protocol
    # ========================================

    def discover_schema(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        """Handle schema discovery request.

        Response format:
        {
            "capabilities": {...},
            "properties_by_type": {...},
            "operators": [...],
            "examples": [...]
        }
        """
        patterns = get_patterns(self.pattern_dir)
        lenses = sorted(set(lens for p in patterns for lens in p.lens))

        return {
            "capabilities": {
                "node_types": sorted(self.schema.node_types),
                "edge_types": sorted(self.schema.edge_types),
                "operators": self.OPERATORS,
                "query_types": self.QUERY_TYPES,
                "clauses": self.CLAUSES,
                "lenses": lenses,
            },
            "properties_by_type": {
                node_type: [
                    {"name": prop, "type": self._infer_property_type(prop)}
                    for prop in sorted(props)
                ]
                for node_type, props in self.schema.properties.items()
            },
            "patterns": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "severity": p.severity,
                    "lens": p.lens,
                }
                for p in patterns[:20]  # Limit to 20 for token efficiency
            ],
            "examples": self._get_example_queries(),
        }

    def _infer_property_type(self, prop_name: str) -> str:
        """Infer property type from name."""
        boolean_indicators = [
            "is_",
            "has_",
            "uses_",
            "writes_",
            "reads_",
            "touches_",
            "_ok",
            "payable",
        ]
        if any(prop_name.startswith(ind) or prop_name.endswith(ind) for ind in boolean_indicators):
            return "boolean"

        if "count" in prop_name or "depth" in prop_name or "complexity" in prop_name:
            return "integer"

        if prop_name in ("visibility", "mutability", "label", "name"):
            return "string"

        if "tags" in prop_name or "calls" in prop_name:
            return "array"

        return "any"

    def _get_example_queries(self) -> list[dict[str, str]]:
        """Get example queries for each query type."""
        return [
            {
                "type": "DESCRIBE",
                "query": "DESCRIBE TYPES",
                "description": "List all available node types",
            },
            {
                "type": "FIND",
                "query": "FIND functions WHERE visibility = 'public' AND writes_state LIMIT 10",
                "description": "Find public state-changing functions",
            },
            {
                "type": "MATCH",
                "query": "MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable) WHERE f.visibility = 'public' RETURN f.label, s.label",
                "description": "Find functions writing to state variables",
            },
            {
                "type": "FLOW",
                "query": "FLOW FROM (i:Input WHERE i.kind = 'parameter') TO (s:StateVariable) RETURN PATHS",
                "description": "Track dataflow from parameters to state",
            },
            {
                "type": "PATTERN",
                "query": "PATTERN weak-access-control LENS Authority SEVERITY high",
                "description": "Check for access control vulnerabilities",
            },
        ]

    # ========================================
    # Autocomplete Protocol
    # ========================================

    def autocomplete(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle autocomplete request.

        Request format:
        {
            "query": "FIND functions WHERE visi",
            "cursor_position": 27
        }

        Response format:
        {
            "suggestions": [
                {
                    "text": "visibility",
                    "type": "property",
                    "description": "...",
                    "values": [...],
                    "confidence": 0.95
                }
            ]
        }
        """
        query = request.get("query", "")
        cursor = request.get("cursor_position", len(query))

        # Get text up to cursor
        prefix = query[:cursor]

        # Determine context
        context = self._determine_context(prefix)

        # Generate suggestions based on context
        suggestions = []

        if context["type"] == "keyword":
            suggestions = self._suggest_keywords(context)
        elif context["type"] == "node_type":
            suggestions = self._suggest_node_types(context)
        elif context["type"] == "property":
            suggestions = self._suggest_properties(context)
        elif context["type"] == "operator":
            suggestions = self._suggest_operators(context)
        elif context["type"] == "value":
            suggestions = self._suggest_values(context)

        return {"suggestions": suggestions, "context": context}

    def _determine_context(self, prefix: str) -> dict[str, Any]:
        """Determine what the user is trying to type."""
        prefix_lower = prefix.lower().strip()

        # Empty or whitespace - suggest query keywords
        if not prefix_lower:
            return {"type": "keyword", "partial": ""}

        # After FIND/MATCH - suggest node types
        if prefix_lower.startswith(("find ", "match ")):
            words = prefix_lower.split()
            if len(words) == 1 or (len(words) == 2 and not prefix.endswith(" ")):
                return {"type": "node_type", "partial": words[-1] if len(words) == 2 else ""}

        # After WHERE - suggest properties or keywords
        if " where " in prefix_lower:
            after_where = prefix_lower.split(" where ")[-1]
            # Check if we're in the middle of a property name
            if not any(op in after_where for op in ("=", ">", "<", "in")):
                words = after_where.split()
                partial = words[-1] if words else ""
                return {"type": "property", "partial": partial, "node_type": self._extract_node_type(prefix)}

        # Default to keyword suggestion
        words = prefix_lower.split()
        return {"type": "keyword", "partial": words[-1] if words else ""}

    def _extract_node_type(self, query: str) -> str | None:
        """Extract node type from query for property suggestions."""
        query_lower = query.lower()
        if "find " in query_lower:
            after_find = query_lower.split("find ")[1].split()[0]
            # Singularize
            if after_find.endswith("s"):
                after_find = after_find[:-1]
            # Capitalize
            node_type = after_find.capitalize()
            if node_type in self.schema.node_types:
                return node_type
        return "Function"  # Default

    def _suggest_keywords(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest query keywords."""
        partial = context.get("partial", "").upper()
        suggestions = []

        for keyword in ["DESCRIBE", "FIND", "MATCH", "FLOW", "PATTERN", "WHERE", "RETURN", "LIMIT"]:
            if keyword.startswith(partial):
                suggestions.append(
                    {
                        "text": keyword,
                        "type": "keyword",
                        "description": f"{keyword} clause",
                        "confidence": 0.9,
                    }
                )

        return suggestions

    def _suggest_node_types(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest node types."""
        partial = context.get("partial", "").lower()
        suggestions = []

        for node_type in self.schema.node_types:
            if node_type.lower().startswith(partial):
                # Get property count
                prop_count = len(self.schema.get_properties(node_type))

                suggestions.append(
                    {
                        "text": node_type.lower() + "s",  # Pluralize
                        "type": "node_type",
                        "description": f"{node_type} nodes ({prop_count} properties)",
                        "confidence": 0.95 if node_type.lower() == partial else 0.8,
                    }
                )

        return suggestions

    def _suggest_properties(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest properties for the current node type."""
        partial = context.get("partial", "").lower()
        node_type = context.get("node_type", "Function")
        suggestions = []

        properties = self.schema.get_properties(node_type)

        for prop in properties:
            if prop.lower().startswith(partial) or partial in prop.lower():
                prop_type = self._infer_property_type(prop)

                # Get example values
                values = None
                if prop == "visibility":
                    values = ["public", "external", "internal", "private"]
                elif prop == "mutability":
                    values = ["view", "pure", "nonpayable", "payable"]
                elif prop_type == "boolean":
                    values = [True, False]

                confidence = 0.95 if prop.lower().startswith(partial) else 0.7

                suggestions.append(
                    {
                        "text": prop,
                        "type": "property",
                        "description": f"{prop} ({prop_type})",
                        "values": values,
                        "confidence": confidence,
                    }
                )

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:10]  # Limit to top 10

    def _suggest_operators(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest operators."""
        return [
            {
                "text": op,
                "type": "operator",
                "description": f"{op} operator",
                "confidence": 0.9,
            }
            for op in self.OPERATORS
        ]

    def _suggest_values(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Suggest values for a property."""
        # Would need more context to provide good suggestions
        return []

    # ========================================
    # Validation Protocol
    # ========================================

    def validate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle validation request.

        Request format:
        {
            "query": "FIND functions WHERE visability = public"
        }

        Response format:
        {
            "valid": false,
            "errors": [...],
            "warnings": [...],
            "suggestions": [...]
        }
        """
        query = request.get("query", "")

        try:
            # Tokenize
            lexer = Lexer(query)
            tokens = lexer.tokenize()

            # Parse
            parser = Parser(tokens)
            ast = parser.parse()

            # Semantic analysis
            analyzer = SemanticAnalyzer(self.schema)
            analyzer.analyze(ast)

            if analyzer.has_errors():
                return {
                    "valid": False,
                    "errors": [self._format_error(e) for e in analyzer.errors],
                    "warnings": [self._format_warning(w) for w in analyzer.warnings],
                }

            return {
                "valid": True,
                "warnings": [self._format_warning(w) for w in analyzer.warnings],
                "message": "Query is valid",
            }

        except LexerError as e:
            return {
                "valid": False,
                "errors": [
                    {
                        "type": "lexer",
                        "line": e.line,
                        "column": e.column,
                        "message": e.message,
                        "hint": e.hint,
                    }
                ],
            }
        except ParseError as e:
            return {
                "valid": False,
                "errors": [
                    {
                        "type": "syntax",
                        "line": e.line,
                        "column": e.column,
                        "message": e.message,
                        "hint": e.hint,
                        "suggestion": e.suggestion,
                    }
                ],
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [
                    {
                        "type": "unknown",
                        "message": str(e),
                    }
                ],
            }

    def _format_error(self, error) -> dict[str, Any]:
        """Format semantic error for response."""
        return {
            "type": "semantic",
            "line": error.line,
            "column": error.column,
            "message": error.message,
            "hint": error.hint,
            "suggestions": error.suggestions,
            "auto_fix": error.auto_fix,
            "confidence": error.confidence,
        }

    def _format_warning(self, warning) -> dict[str, Any]:
        """Format semantic warning for response."""
        return {
            "type": "warning",
            "message": warning.message,
            "hint": warning.hint,
        }

    # ========================================
    # Example Generation
    # ========================================

    def generate_examples(self, request: dict[str, Any]) -> dict[str, Any]:
        """Generate example queries for a specific use case.

        Request format:
        {
            "use_case": "find_vulnerable_functions",
            "node_type": "Function",
            "complexity": "simple"
        }

        Response format:
        {
            "examples": [
                {
                    "query": "...",
                    "description": "...",
                    "complexity": "simple|intermediate|advanced"
                }
            ]
        }
        """
        use_case = request.get("use_case", "")
        node_type = request.get("node_type", "Function")
        complexity = request.get("complexity", "simple")

        examples = []

        # Generate examples based on use case
        if use_case == "find_vulnerable_functions":
            examples.extend(
                [
                    {
                        "query": "FIND functions WHERE writes_state AND NOT has_access_gate LIMIT 20",
                        "description": "Find unprotected state-changing functions",
                        "complexity": "simple",
                    },
                    {
                        "query": "MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable) WHERE f.visibility = 'public' AND s.security_tags CONTAINS 'owner' RETURN f.label, s.label",
                        "description": "Functions writing to owner-like state",
                        "complexity": "intermediate",
                    },
                ]
            )
        elif use_case == "dataflow_analysis":
            examples.extend(
                [
                    {
                        "query": "FLOW FROM (i:Input) TO (s:StateVariable) RETURN PATHS",
                        "description": "Basic dataflow from inputs to state",
                        "complexity": "simple",
                    }
                ]
            )

        # Filter by complexity if specified
        if complexity != "all":
            examples = [e for e in examples if e["complexity"] == complexity]

        return {"examples": examples}

    # ========================================
    # Query Assistance
    # ========================================

    def assist(self, request: dict[str, Any]) -> dict[str, Any]:
        """Provide assistance for constructing a query.

        Request format:
        {
            "intent": "I want to find public functions that change state",
            "current_query": "FIND functions WHERE"
        }

        Response format:
        {
            "suggested_query": "...",
            "explanation": "...",
            "next_steps": [...]
        }
        """
        intent = request.get("intent", "")
        current = request.get("current_query", "")

        # Simple intent-to-query mapping (could be much more sophisticated)
        suggestions = {
            "find public functions": "FIND functions WHERE visibility = 'public'",
            "find state changing": "FIND functions WHERE writes_state",
            "find unprotected": "FIND functions WHERE NOT has_access_gate",
        }

        # Find best match
        intent_lower = intent.lower()
        for key, query in suggestions.items():
            if key in intent_lower:
                return {
                    "suggested_query": query,
                    "explanation": f"This query finds {key}",
                    "next_steps": [
                        "Add more conditions with AND/OR",
                        "Add LIMIT to restrict results",
                        "Add RETURN to select specific fields",
                    ],
                }

        return {
            "suggested_query": current,
            "explanation": "Continue building your query",
            "next_steps": [
                "Use WHERE to add conditions",
                "Use RETURN to select fields",
                "Use LIMIT to restrict results",
            ],
        }
