# AlphaSwarm.sol API Reference

Complete API reference for AlphaSwarm.sol modules.

---

## Core Modules

### Knowledge Graph (`alphaswarm_sol.kg`)

#### `builder.py` - Graph Construction

```python
from alphaswarm_sol.kg.builder import VKGBuilder

# Build graph from Solidity files
builder = VKGBuilder()
graph = builder.build_from_path("path/to/contracts/")
```

**Key Functions:**
- `build_from_path(path)` - Build graph from file or directory
- `build_from_slither(slither_instance)` - Build from existing Slither analysis

#### `schema.py` - Graph Types

```python
from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge, Evidence

# Graph structure
graph = KnowledgeGraph(
    nodes={"id1": Node(id="id1", label="func", type="Function", properties={})},
    edges={"e1": Edge(id="e1", source="id1", target="id2", type="CALLS")},
    metadata={"version": "2.0"}
)

# Access nodes
func_nodes = [n for n in graph.nodes.values() if n.type == "Function"]
```

#### `operations.py` - Semantic Operations

```python
from alphaswarm_sol.kg.operations import SemanticOperation, OperationDetector

# Detect operations in a function
detector = OperationDetector()
ops = detector.detect(function_node)
# Returns: [SemanticOperation.TRANSFERS_VALUE_OUT, SemanticOperation.WRITES_USER_BALANCE]
```

**20 Semantic Operations:**
- Value: `TRANSFERS_VALUE_OUT`, `READS_USER_BALANCE`, `WRITES_USER_BALANCE`, `RECEIVES_VALUE`
- Access: `CHECKS_PERMISSION`, `MODIFIES_OWNER`, `MODIFIES_ROLES`, `GRANTS_APPROVAL`
- External: `CALLS_EXTERNAL`, `CALLS_UNTRUSTED`, `READS_EXTERNAL_VALUE`, `DELEGATECALLS`
- State: `MODIFIES_CRITICAL_STATE`, `READS_ORACLE`, `READS_TIMESTAMP`
- Flow: `LOOPS_OVER_ARRAY`, `MINTS_TOKENS`, `BURNS_TOKENS`, `PAUSES_SYSTEM`, `EMITS_EVENT`

#### `sequencing.py` - Operation Sequencing

```python
from alphaswarm_sol.kg.sequencing import SequenceAnalyzer, BehavioralSignature

# Analyze operation ordering
analyzer = SequenceAnalyzer()
signature = analyzer.compute_signature(function_node)
# Returns: "R:bal→X:out→W:bal" (vulnerable) or "R:bal→W:bal→X:out" (safe CEI)
```

---

### Query Layer (`alphaswarm_sol.queries`)

#### `executor.py` - Query Execution

```python
from alphaswarm_sol.queries.executor import QueryExecutor

executor = QueryExecutor(graph)

# Natural language query
results = executor.execute("public functions that write state without access control")

# VQL query
results = executor.execute("FIND functions WHERE visibility = public AND writes_state AND NOT has_access_gate")

# Pattern query
results = executor.execute("pattern:reentrancy-classic")
```

#### `patterns.py` - Pattern Matching

```python
from alphaswarm_sol.queries.patterns import PatternMatcher, load_patterns

# Load patterns from directory
patterns = load_patterns("patterns/")

# Match patterns against graph
matcher = PatternMatcher(patterns)
findings = matcher.match_all(graph)

for finding in findings:
    print(f"{finding.pattern_id}: {finding.node_label} - {finding.severity}")
```

---

### Analysis (`alphaswarm_sol.analysis`)

#### `attack_synthesis.py` - Attack Path Generation

```python
from alphaswarm_sol.analysis.attack_synthesis import AttackPathSynthesizer

synthesizer = AttackPathSynthesizer(graph)

# Generate attack paths for a contract
paths = synthesizer.synthesize(
    contract_id="Contract_Vault",
    max_paths=10,
    max_depth=5
)

for path in paths:
    print(f"Path: {' -> '.join(s.description for s in path.steps)}")
    print(f"Impact: {path.impact_level}")
    print(f"Difficulty: {path.difficulty}")
```

**Attack Types Detected:**
- Reentrancy paths
- Flash loan sequences
- Oracle manipulation
- Access control bypass
- DoS vectors

---

### Performance (`alphaswarm_sol.performance`)

#### `profiler.py` - Build Profiling

```python
from alphaswarm_sol.performance.profiler import BuildProfiler, BuildPhase

profiler = BuildProfiler()

profiler.start_phase("slither", BuildPhase.PARSE, file_count=10)
# ... do work ...
profiler.end_phase("slither")

result = profiler.get_result()
print(f"Total time: {result.total_time_ms}ms")
print(f"Bottleneck: {result.bottleneck.name}")
```

#### `cache.py` - Graph Caching

```python
from alphaswarm_sol.performance.cache import GraphCache

cache = GraphCache(max_size_mb=100, default_ttl_seconds=3600)

# Cache a graph
contract_hash = cache.get_contract_hash(source_code)
cache.set_graph(contract_hash, graph.to_dict())

# Retrieve cached graph
cached = cache.get_graph(contract_hash)
```

#### `incremental.py` - Incremental Builds

```python
from alphaswarm_sol.performance.incremental import IncrementalBuilder

builder = IncrementalBuilder()

# Plan build based on changes
change_set, build_plan = builder.plan_build("path/to/contracts/")

print(f"Added: {len(change_set.added)} files")
print(f"Modified: {len(change_set.modified)} files")
print(f"Deleted: {len(change_set.deleted)} files")
```

#### `parallel.py` - Parallel Processing

```python
from alphaswarm_sol.performance.parallel import ParallelProcessor, BatchProcessor

# Parallel map
processor = ParallelProcessor(max_workers=4)
results = processor.map(analyze_function, functions)

# Batch processing
batch = BatchProcessor(batch_size=100)
results = batch.process(analyze_function, all_items)
```

---

### Enterprise (`alphaswarm_sol.enterprise`)

#### `profiles.py` - Configuration Profiles

```python
from alphaswarm_sol.enterprise.profiles import ProfileManager, ProfileLevel

manager = ProfileManager()

# Get profile
profile = manager.get_profile("standard")
print(f"Max depth: {profile.analysis.max_depth}")
print(f"Patterns enabled: {profile.patterns.enabled}")

# Available profiles: fast, standard, thorough
```

**Profile Levels:**
- `fast`: Quick scans, basic patterns, no cross-contract
- `standard`: Full patterns, moderate depth, standard output
- `thorough`: All patterns, deep analysis, full cross-contract

#### `multi_project.py` - Multi-Project Analysis

```python
from alphaswarm_sol.enterprise.multi_project import MultiProjectManager

manager = MultiProjectManager()

# Load projects
manager.load_graph("project-a", graph_a)
manager.load_graph("project-b", graph_b)

# Cross-project queries
results = manager.query.find_similar_functions("withdraw")
vulns = manager.query.find_vulnerable_patterns("reentrancy")
```

#### `reports.py` - Report Generation

```python
from alphaswarm_sol.enterprise.reports import ReportGenerator, ReportFormat

generator = ReportGenerator(graph)
report = generator.generate("MyProject", include_info=False)

# Export formats
markdown = generator.to_markdown(report)
html = generator.to_html(report)

print(f"Critical: {report.stats['critical']}")
print(f"High: {report.stats['high']}")
```

---

### Validation (`alphaswarm_sol.validation`)

#### `benchmarks.py` - Exploit Benchmarks

```python
from alphaswarm_sol.validation.benchmarks import BenchmarkSuite, KNOWN_EXPLOITS

suite = BenchmarkSuite()
results = suite.run(graph)

summary = suite.get_summary(results)
print(f"Detection rate: {summary['detection_rate']:.1%}")
print(f"Precision: {summary['precision']:.1%}")
print(f"Recall: {summary['recall']:.1%}")
```

**Known Exploits:**
- DAO 2016 (reentrancy)
- Parity 2017 (access control)
- Cream 2021 (flash loan)
- Beanstalk 2022 (governance)

#### `metrics.py` - Detection Metrics

```python
from alphaswarm_sol.validation.metrics import MetricsCalculator

calc = MetricsCalculator()

# Add detection results
calc.add_binary_result(predicted=True, actual=True, category="reentrancy")
calc.add_binary_result(predicted=True, actual=False, category="access")

metrics = calc.get_metrics()
print(f"Precision: {metrics.precision:.2%}")
print(f"Recall: {metrics.recall:.2%}")
print(f"F1 Score: {metrics.f1_score:.2%}")

# Check targets
targets = calc.meets_targets(precision_target=0.9, recall_target=0.8)
print(f"All targets met: {targets['all_met']}")
```

#### `comparison.py` - Tool Comparison

```python
from alphaswarm_sol.validation.comparison import ToolComparison, Tool

comp = ToolComparison([Tool.VKG, Tool.SLITHER, Tool.MYTHRIL])

comp.add_result("vuln1", {Tool.VKG: True, Tool.SLITHER: False}, ground_truth=True)
comp.add_result("vuln2", {Tool.VKG: True, Tool.SLITHER: True}, ground_truth=True)

summary = comp.get_summary()
print(summary.to_markdown_table())
```

---

### Semantic Scaffolding (`alphaswarm_sol.kg.scaffold`)

```python
from alphaswarm_sol.kg.scaffold import ScaffoldGenerator, ScaffoldFormat

generator = ScaffoldGenerator(graph)

# Generate compact scaffold
scaffold = generator.generate(
    focal_nodes=["func1", "func2"],
    format=ScaffoldFormat.COMPACT,
    max_tokens=4000
)

print(scaffold.content)
print(f"Token estimate: {scaffold.token_estimate}")
```

**Scaffold Formats:**
- `COMPACT`: Minimal tokens, essential info only
- `STRUCTURED`: JSON-like with properties
- `YAML_LIKE`: Human-readable YAML format

---

## CLI Commands

```bash
# Build knowledge graph
uv run alphaswarm build-kg <path> [--output <graph.json>]

# Query graph
uv run alphaswarm query "<query>" [--graph <path>] [--compact] [--explain]

# Show schema
uv run alphaswarm schema [--graph <path>]

# Run patterns
uv run alphaswarm query "pattern:<pattern-id>"
uv run alphaswarm query "lens:<lens-name>"
```

---

## Type Reference

### Node Types

| Type | Description |
|------|-------------|
| `Contract` | Solidity contract with proxy detection |
| `Function` | Function with 50+ security properties |
| `StateVariable` | State variable with security tags |
| `Input` | Function parameter with taint tracking |
| `Loop` | Loop construct with bound analysis |
| `ExternalCallSite` | Low-level call tracking |
| `ExecutionPath` | Multi-step attack sequence |
| `Invariant` | Formal property from NatSpec |

### Edge Types

| Type | Description |
|------|-------------|
| `CALLS` | Function calls function |
| `WRITES_STATE` | Function modifies state variable |
| `READS_STATE` | Function reads state variable |
| `INPUT_TAINTS_STATE` | Taint flow from input to state |
| `EXTERNAL_CALL` | External contract call |
| `INHERITS` | Contract inheritance |

---

*Version 2.0 | December 2025*
