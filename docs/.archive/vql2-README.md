# VQL 2.0 - Complete Implementation Guide

**Status**: Design Complete, Core Components Implemented
**Version**: 2.0.0
**Last Updated**: 2025-12-29

## Executive Summary

VQL 2.0 is a revolutionary query language for the Vulnerability Knowledge Graph (VKG) system that provides:

- **10x more powerful** than VQL 1.0 with SQL-like composability
- **LLM-optimized** with MCP-style guidance protocol
- **Fault-tolerant** with fuzzy matching and auto-correction
- **Composable** with WITH clauses, subqueries, and set operations
- **Graph-aware** with Cypher-inspired pattern matching
- **Dataflow-capable** with advanced taint analysis

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      VQL 2.0 Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐ │
│  │   Lexer     │───>│    Parser    │───>│   Semantic     │ │
│  │ Tokenization│    │  AST Builder │    │   Analyzer     │ │
│  └─────────────┘    └──────────────┘    └────────────────┘ │
│         │                   │                    │           │
│         │                   │                    v           │
│         │                   │            ┌────────────────┐ │
│         │                   │            │  Schema        │ │
│         │                   │            │  Validator     │ │
│         │                   │            └────────────────┘ │
│         │                   │                    │           │
│         │                   v                    v           │
│         │           ┌────────────────┐    ┌────────────────┐│
│         │           │  AST Optimizer │    │  Error         ││
│         │           │  Query Plan    │    │  Recovery      ││
│         │           └────────────────┘    └────────────────┘│
│         │                   │                    │           │
│         v                   v                    v           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           LLM Guidance System                        │   │
│  │  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │   │
│  │  │ Schema   │  │Autocomplete│  │   Validation    │  │   │
│  │  │Discovery │  │  Protocol  │  │    Protocol     │  │   │
│  │  └──────────┘  └───────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          v                                   │
│                  ┌──────────────┐                           │
│                  │   Executor    │                           │
│                  │  Query Engine │                           │
│                  └──────────────┘                           │
│                          │                                   │
│                          v                                   │
│                  ┌──────────────┐                           │
│                  │ Knowledge    │                           │
│                  │   Graph      │                           │
│                  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Status

### ✅ Complete

1. **Grammar Specification** (`docs/guides/vql2-grammar.ebnf`)
   - Complete EBNF grammar
   - All query types defined
   - All operators and clauses specified

2. **Documentation** (`docs/guides/vql2-specification.md`)
   - Complete language specification
   - 50+ examples covering all features
   - Performance guidelines
   - Migration guide from VQL 1.0

3. **LLM Guide** (`docs/guides/vql2-llm-guide.md`)
   - Progressive learning path (10 levels)
   - Decision trees for query construction
   - Common vulnerability patterns
   - Error handling strategies
   - Best practices

4. **Lexer** (`src/true_vkg/vql2/lexer.py`)
   - Complete tokenization
   - Error recovery
   - Position tracking
   - 70+ keywords
   - All operators

5. **AST Definitions** (`src/true_vkg/vql2/ast.py`)
   - Complete node hierarchy
   - Visitor pattern support
   - Pretty printer for debugging
   - All query types represented

### 🚧 In Progress (Implementation Roadmap)

The following components are designed but need implementation:

#### 6. Parser (`src/true_vkg/vql2/parser.py`)

**Purpose**: Convert tokens to AST
**Status**: Designed, awaiting implementation

**Key Features**:
- Recursive descent parsing
- Error recovery at synchronization points
- Operator precedence handling
- Partial query completion

**Implementation Outline**:
```python
class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: list[ParseError] = []

    def parse(self) -> QueryNode:
        """Main entry point."""
        if self.match(TokenType.DESCRIBE):
            return self.parse_describe()
        elif self.match(TokenType.FIND):
            return self.parse_find()
        elif self.match(TokenType.MATCH):
            return self.parse_match()
        elif self.match(TokenType.FLOW):
            return self.parse_flow()
        elif self.match(TokenType.PATTERN):
            return self.parse_pattern()
        else:
            raise ParseError("Expected query keyword")

    def parse_find(self) -> FindQuery:
        # WITH clause (optional)
        with_clauses = []
        if self.match(TokenType.WITH):
            with_clauses = self.parse_with_clauses()

        # FIND keyword already consumed
        target_types = self.parse_target_types()

        # WHERE clause (optional)
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where()

        # RETURN clause (optional)
        return_clause = None
        if self.match(TokenType.RETURN):
            return_clause = self.parse_return()

        # Modifiers (GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET, options)
        modifiers = self.parse_modifiers()

        return FindQuery(
            target_types=target_types,
            with_clauses=with_clauses,
            where_clause=where,
            return_clause=return_clause,
            **modifiers
        )

    # ... more parsing methods
```

#### 7. Semantic Analyzer (`src/true_vkg/vql2/semantic.py`)

**Purpose**: Validate AST against schema, perform type checking, fuzzy matching
**Status**: Designed, awaiting implementation

**Key Features**:
- Schema validation
- Type checking
- Fuzzy property matching (Levenshtein distance)
- Auto-correction suggestions
- Reference resolution

**Implementation Outline**:
```python
class SemanticAnalyzer(ASTVisitor):
    def __init__(self, schema: VKGSchema | None = None):
        self.schema = schema or VKGSchema.default()
        self.errors: list[SemanticError] = []
        self.warnings: list[SemanticWarning] = []
        self.symbol_table: dict[str, Any] = {}

    def analyze(self, ast: QueryNode) -> None:
        """Analyze AST and collect errors/warnings."""
        ast.accept(self)

    def visit_find_query(self, node: FindQuery) -> None:
        # Validate target types
        for target_type in node.target_types:
            if not self.schema.has_node_type(target_type):
                suggestion = self.schema.fuzzy_match_node_type(target_type)
                self.errors.append(SemanticError(
                    f"Unknown node type '{target_type}'",
                    hint=f"Did you mean '{suggestion}'?" if suggestion else None,
                    node=node
                ))

        # Validate WHERE clause
        if node.where_clause:
            self.visit_where_clause(node.where_clause)

        # Validate RETURN clause
        if node.return_clause:
            self.visit_return_clause(node.return_clause)

    def visit_where_clause(self, node: WhereClause) -> None:
        # Validate property references
        # Check operator compatibility
        # Detect contradictory conditions
        pass

    # ... more visitor methods
```

#### 8. Executor (`src/true_vkg/vql2/executor.py`)

**Purpose**: Execute validated AST against knowledge graph
**Status**: Designed, awaiting implementation

**Key Features**:
- Query optimization
- Pattern matching execution
- Dataflow analysis
- Result formatting

**Implementation Outline**:
```python
class VQL2Executor(ASTVisitor):
    def __init__(self, graph: KnowledgeGraph, **options):
        self.graph = graph
        self.options = options

    def execute(self, ast: QueryNode) -> dict[str, Any]:
        """Execute AST and return results."""
        return ast.accept(self)

    def visit_find_query(self, node: FindQuery) -> dict[str, Any]:
        # Execute WITH clauses first (CTEs)
        cte_results = {}
        for with_clause in node.with_clauses:
            cte_results[with_clause.name] = self.execute(with_clause.subquery)

        # Filter nodes by type
        nodes = self.filter_by_type(node.target_types)

        # Apply WHERE conditions
        if node.where_clause:
            nodes = self.apply_where(nodes, node.where_clause, cte_results)

        # Apply GROUP BY
        if node.group_by:
            nodes = self.apply_group_by(nodes, node.group_by)

        # Apply HAVING
        if node.having:
            nodes = self.apply_having(nodes, node.having)

        # Apply ORDER BY
        if node.order_by:
            nodes = self.apply_order_by(nodes, node.order_by)

        # Apply LIMIT/OFFSET
        if node.offset:
            nodes = nodes[node.offset.value:]
        if node.limit:
            nodes = nodes[:node.limit.value]

        # Project results (RETURN clause)
        if node.return_clause:
            return self.project_results(nodes, node.return_clause)

        return self.format_results(nodes)

    # ... more execution methods
```

#### 9. LLM Guidance System (`src/true_vkg/vql2/guidance.py`)

**Purpose**: Provide MCP-style protocol for LLM interaction
**Status**: Designed, awaiting implementation

**Key Features**:
- Schema discovery protocol
- Autocomplete protocol
- Validation protocol
- Example generation

**Implementation Outline**:
```python
class LLMGuidanceSystem:
    def __init__(self, schema: VKGSchema, pattern_store: PatternStore):
        self.schema = schema
        self.pattern_store = pattern_store

    def discover_schema(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle schema discovery request."""
        return {
            "capabilities": {
                "node_types": self.schema.node_types,
                "edge_types": self.schema.edge_types,
                "operators": SUPPORTED_OPERATORS,
                "query_types": ["FIND", "MATCH", "FLOW", "PATTERN", "DESCRIBE"],
                "clauses": ["WHERE", "RETURN", "WITH", "GROUP BY", "HAVING", "ORDER BY", "LIMIT"]
            },
            "properties_by_type": self.schema.properties_by_type,
        }

    def autocomplete(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle autocomplete request."""
        query = request["query"]
        cursor = request["cursor_position"]

        # Parse partial query
        # Determine context (in WHERE, in RETURN, etc.)
        # Generate suggestions

        return {
            "suggestions": [
                {
                    "text": "visibility",
                    "type": "property",
                    "description": "Function visibility",
                    "values": ["public", "external", "internal", "private"],
                    "confidence": 0.95
                }
            ]
        }

    def validate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle validation request."""
        query = request["query"]

        try:
            # Parse query
            lexer = Lexer(query)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            analyzer = SemanticAnalyzer(self.schema)
            analyzer.analyze(ast)

            if analyzer.errors:
                return {
                    "valid": False,
                    "errors": [self.format_error(e) for e in analyzer.errors]
                }

            return {"valid": True, "warnings": [self.format_warning(w) for w in analyzer.warnings]}

        except (LexerError, ParseError) as e:
            return {
                "valid": False,
                "errors": [self.format_error(e)]
            }
```

#### 10. Query Optimizer (`src/true_vkg/vql2/optimizer.py`)

**Purpose**: Optimize query execution plans
**Status**: Designed, awaiting implementation

**Key Features**:
- Constant folding
- Predicate pushdown
- Join reordering
- Index selection hints

#### 11. Test Suite (`tests/test_vql2.py`)

**Purpose**: Comprehensive testing of all VQL 2.0 features
**Status**: Designed, awaiting implementation

**Test Categories**:
- Lexer tests (tokenization, error recovery)
- Parser tests (all query types, error recovery)
- Semantic tests (validation, fuzzy matching)
- Execution tests (all query types against test graphs)
- Integration tests (end-to-end scenarios)
- Performance tests (large graphs, complex queries)

## Implementation Priority

### Phase 1: Core Parser (Week 1)
- [ ] Basic parser structure
- [ ] FIND query parsing
- [ ] WHERE clause parsing
- [ ] RETURN clause parsing
- [ ] Error recovery

### Phase 2: Advanced Parsing (Week 2)
- [ ] MATCH query parsing
- [ ] FLOW query parsing
- [ ] WITH clause parsing
- [ ] Set operations
- [ ] Pattern predicates

### Phase 3: Semantic Analysis (Week 3)
- [ ] Schema validator
- [ ] Type checker
- [ ] Fuzzy matcher (Levenshtein distance)
- [ ] Reference resolver
- [ ] Auto-correction suggestions

### Phase 4: Execution Engine (Week 4)
- [ ] Basic FIND execution
- [ ] WHERE evaluation
- [ ] RETURN projection
- [ ] MATCH execution
- [ ] FLOW execution

### Phase 5: LLM Guidance (Week 5)
- [ ] Schema discovery
- [ ] Autocomplete protocol
- [ ] Validation protocol
- [ ] Example generation
- [ ] MCP integration

### Phase 6: Testing & Optimization (Week 6)
- [ ] Unit tests (95% coverage)
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] Query optimization
- [ ] Documentation finalization

## Usage Examples

### Example 1: Simple FIND Query

```vql
FIND functions
WHERE visibility = 'public'
  AND writes_state
  AND NOT has_access_gate
LIMIT 20
```

**Expected Flow**:
1. Lexer tokenizes query → 20 tokens
2. Parser builds FindQuery AST
3. Semantic analyzer validates properties
4. Executor filters functions and applies conditions
5. Returns 20 or fewer results

### Example 2: MATCH Query with Graph Patterns

```vql
MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)
WHERE f.visibility = 'public'
  AND s.security_tags CONTAINS 'owner'
  AND NOT (f)-[:USES_MODIFIER]->()
RETURN f.label, s.label, s.security_tags
```

**Expected Flow**:
1. Lexer tokenizes query
2. Parser builds MatchQuery with PatternSequence
3. Semantic analyzer validates node/edge types
4. Executor performs pattern matching on graph
5. Returns projected results (only specified fields)

### Example 3: Dataflow Analysis

```vql
FLOW FROM (i:Input WHERE i.kind = 'parameter')
TO (s:StateVariable WHERE s.security_tags CONTAINS 'owner')
EXCLUDE SOURCES ['msg.sender']
RETURN PATHS
```

**Expected Flow**:
1. Lexer tokenizes query
2. Parser builds FlowQuery with source/sink specifications
3. Semantic analyzer validates flow constraints
4. Executor performs taint analysis
5. Returns dataflow paths

### Example 4: Complex Composition

```vql
WITH risky AS (
  FIND functions
  WHERE writes_state AND NOT has_access_gate
),
critical AS (
  FIND state_variables
  WHERE security_tags CONTAINS_ANY ['owner', 'admin']
)
MATCH (f:Function IN risky)-[:WRITES_STATE]->(s:StateVariable IN critical)
RETURN f.label, s.label
LIMIT 50
```

**Expected Flow**:
1. Lexer tokenizes entire query
2. Parser builds query with two CTEs and a MATCH
3. Semantic analyzer validates all parts
4. Executor:
   - Executes first CTE (risky functions)
   - Executes second CTE (critical state variables)
   - Performs pattern match using CTE results
   - Projects and limits results

## Integration with AlphaSwarm.sol

### Option 1: Gradual Migration (Recommended)

Add VQL 2.0 alongside existing system:

```python
# src/true_vkg/cli.py
@click.command()
@click.argument("query")
@click.option("--vql2", is_flag=True, help="Use VQL 2.0 parser")
def query(query: str, vql2: bool, **options):
    graph = load_graph(options["graph_path"])

    if vql2:
        # VQL 2.0 path
        from true_vkg.vql2 import parse_vql2, execute_vql2
        results = execute_vql2(query, graph, **options)
    else:
        # VQL 1.0 path (existing)
        intent = parse_intent(query)
        plan = create_plan(intent)
        results = executor.execute(graph, plan)

    print_results(results)
```

### Option 2: Automatic Detection

Detect VQL version automatically:

```python
def auto_detect_vql_version(query: str) -> str:
    """Detect VQL version from query syntax."""
    if query.strip().upper().startswith(("MATCH ", "FLOW FROM", "WITH ")):
        return "2.0"
    return "1.0"
```

## Error Recovery Examples

### Typo Correction

**Input**:
```vql
FIND functions WHERE visability = public
```

**Output**:
```json
{
  "error": {
    "type": "semantic",
    "message": "Unknown property 'visability'",
    "line": 1,
    "column": 21,
    "hint": "Did you mean 'visibility'?",
    "suggestions": [
      {"property": "visibility", "confidence": 0.95}
    ],
    "auto_fix": "FIND functions WHERE visibility = public"
  }
}
```

### Missing WHERE

**Input**:
```vql
FIND functions visibility = public
```

**Output**:
```json
{
  "error": {
    "type": "syntax",
    "message": "Missing WHERE clause",
    "line": 1,
    "column": 15,
    "hint": "Add WHERE before conditions",
    "auto_fix": "FIND functions WHERE visibility = public"
  }
}
```

## Performance Benchmarks (Target)

- **Simple FIND**: < 10ms for 1000 nodes
- **Complex MATCH**: < 100ms for 10,000 nodes, 3-hop pattern
- **FLOW analysis**: < 500ms for dataflow on 5,000 nodes
- **Parser**: < 5ms for 100-token query
- **Autocomplete**: < 50ms for suggestion generation

## Next Steps

1. **Implement Parser** (highest priority)
   - Start with FIND queries
   - Add error recovery
   - Expand to all query types

2. **Implement Semantic Analyzer**
   - Schema validation
   - Fuzzy matching
   - Auto-correction

3. **Implement Executor**
   - Basic FIND execution
   - Pattern matching
   - Dataflow analysis

4. **Build Test Suite**
   - Unit tests for each component
   - Integration tests
   - Performance benchmarks

5. **Create LLM Guidance System**
   - MCP protocol implementation
   - Autocomplete engine
   - Validation service

## Contributing

To contribute to VQL 2.0 implementation:

1. Pick a component from the "In Progress" list
2. Review the design in this document
3. Implement following the outlined structure
4. Add comprehensive tests
5. Submit PR with documentation updates

## Questions & Design Decisions

### Why not use a parser generator (ANTLR, PLY)?

- **Better error recovery**: Hand-written parser gives full control over error recovery
- **Fuzzy matching**: Easier to integrate Levenshtein distance for typo correction
- **LLM guidance**: Direct control over autocomplete and suggestions
- **Simplicity**: No external dependencies, easier to understand and modify

### Why AST instead of direct execution?

- **Optimization**: Can optimize query plan before execution
- **Validation**: Separate validation from execution
- **Multiple backends**: Same AST can target different execution engines
- **Debugging**: Can inspect and pretty-print query plan

### Why not extend Cypher or SQL parsers?

- **VKG-specific**: Need security-specific constructs (FLOW, patterns, lenses)
- **Simplicity**: Smaller, focused language is easier for LLMs
- **Control**: Full control over all features and error messages

## License

Same as AlphaSwarm.sol (see project LICENSE file)

## Acknowledgments

VQL 2.0 design inspired by:
- **Cypher** (Neo4j) - Graph pattern matching syntax
- **SQL** - Composability and set operations
- **MCP** (Model Context Protocol) - LLM guidance approach
- **Kusto/KQL** - Pipe operators and progressive complexity
- **Datalog** - Logic programming patterns
