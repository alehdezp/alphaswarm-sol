# Interface Reference

**Purpose:** API contracts and interface specifications for all major modules.
**Last Updated:** 2026-01-22

---

## Table of Contents

1. [Agent Runtime System](#agent-runtime-system)
2. [Knowledge Graph Builder](#knowledge-graph-builder)
3. [Orchestration Layer](#orchestration-layer)
4. [Semantic Labeling](#semantic-labeling)
5. [Protocol Context Pack](#protocol-context-pack)
6. [Tool Integration](#tool-integration)
7. [VulnDocs Framework](#vulndocs-framework)
8. [Model Ranking System](#model-ranking-system)

---

## Agent Runtime System

**Location:** `src/alphaswarm_sol/agents/runtime/`

### AgentRuntime ABC (base.py)

```python
class AgentRuntime(ABC):
    """Abstract base for all SDK runtimes."""

    @abstractmethod
    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent with given configuration and messages."""

    @abstractmethod
    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str
    ) -> AgentResponse:
        """Spawn new agent for a specific task."""

    @abstractmethod
    def get_model_for_role(self, role: AgentRole) -> str:
        """Get appropriate model for agent role."""

    @abstractmethod
    def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics (tokens, costs)."""
```

### AgentRole Enum (6 roles)

| Role | Anthropic Model | OpenAI Model | Purpose |
|------|-----------------|--------------|---------|
| ATTACKER | claude-opus-4-20250514 | o3 | Deep exploit reasoning |
| DEFENDER | claude-sonnet-4-20250514 | gpt-4.1 | Fast guard detection |
| VERIFIER | claude-opus-4-20250514 | o3 | Critical accuracy verification |
| TEST_BUILDER | claude-sonnet-4-20250514 | gpt-4.1 | Foundry test generation |
| SUPERVISOR | claude-sonnet-4-20250514 | gpt-4.1 | Orchestration coordination |
| INTEGRATOR | claude-sonnet-4-20250514 | gpt-4.1 | Verdict merging |

### AgentConfig Dataclass

```python
@dataclass
class AgentConfig:
    role: AgentRole
    system_prompt: str
    tools: List[Dict[str, Any]] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### AgentResponse Dataclass

```python
@dataclass
class AgentResponse:
    content: str
    role: AgentRole
    model: str
    usage: Dict[str, int]  # input_tokens, output_tokens
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
```

### RuntimeConfig Dataclass

```python
@dataclass
class RuntimeConfig:
    preferred_sdk: str = "anthropic"  # anthropic, openai, opencode
    enable_prompt_caching: bool = True
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_base_seconds: float = 2.0
```

### create_runtime Factory

```python
def create_runtime(
    config: Optional[RuntimeConfig] = None,
    runtime_type: Optional[str] = None,  # anthropic, openai, opencode, claude_code, codex
    **kwargs
) -> AgentRuntime:
    """Factory function to create appropriate runtime."""
```

---

## Knowledge Graph Builder

**Location:** `src/alphaswarm_sol/kg/builder/`

### VKGBuilder (core.py)

```python
class VKGBuilder:
    """Main builder orchestrating all processors."""

    def __init__(
        self,
        project_root: Path,
        config: Optional[BuildConfig] = None
    ):
        self.ctx = BuildContext(project_root, config)

    def build_graph(
        self,
        slither_output: SlitherOutput,
        include_labels: bool = False
    ) -> KnowledgeGraph:
        """Build complete knowledge graph from Slither output."""

    def get_completeness_report(self) -> CompletenessReport:
        """Get build quality metrics."""
```

### BuildContext (context.py)

```python
@dataclass
class BuildContext:
    """Dependency injection container for all processors."""
    project_root: Path
    config: BuildConfig

    # Shared state
    node_registry: Dict[str, Node] = field(default_factory=dict)
    edge_registry: Dict[str, Edge] = field(default_factory=dict)
    unresolved_targets: List[UnresolvedTarget] = field(default_factory=list)
    source_cache: Dict[Path, List[str]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def add_unresolved(self, target: UnresolvedTarget) -> None: ...
    def get_source_lines(self, path: Path) -> List[str]: ...
```

### FunctionProcessor (functions.py)

```python
class FunctionProcessor:
    """Process functions and compute security properties."""

    def __init__(self, ctx: BuildContext):
        self.ctx = ctx
        self._legacy = LegacyBuilder(ctx)  # Delegation pattern

    def process_all(
        self,
        contract: Contract,
        contract_node: Node
    ) -> List[Node]:
        """Process all functions in a contract."""

    def process(
        self,
        fn: Function,
        contract: Contract,
        contract_node: Node
    ) -> Node:
        """Process single function, returns function node."""

    def _compute_all_properties(
        self,
        fn: Function,
        contract: Contract
    ) -> FunctionProperties:
        """Compute all 225+ properties for a function."""
```

### FunctionProperties Dataclass (225 fields in 16 groups)

| Group | Fields | Purpose |
|-------|--------|---------|
| Basic Identity & Visibility | 8 | name, visibility, modifiers, etc. |
| Access Control | 18 | has_access_gate, checks_owner, etc. |
| State Operations | 14 | writes_state, reads_state, etc. |
| External Calls | 20 | calls_external, calls_untrusted, etc. |
| User Input & Parameters | 18 | has_user_input, parameter_types, etc. |
| Context Variables | 12 | uses_msg_sender, uses_msg_value, etc. |
| Token Operations | 24 | transfers_tokens, approves_tokens, etc. |
| Oracle & Price | 22 | reads_oracle, price_dependent, etc. |
| Deadline & Slippage | 12 | has_deadline, has_slippage, etc. |
| Loop Analysis | 12 | has_loop, loops_over_array, etc. |
| Arithmetic & Precision | 28 | performs_division, uses_mul, etc. |
| Reentrancy | 6 | has_reentrancy_guard, cei_pattern, etc. |
| Function Classification | 16 | is_initializer, is_upgrader, etc. |
| Flash Loan | 8 | is_flash_loan_callback, etc. |
| Semantic Operations | 4 | semantic_ops, behavioral_signature, etc. |
| Source Location | 3 | file_path, line_start, line_end |

### CallTracker (calls.py)

```python
class CallTracker:
    """Track external calls with confidence scoring."""

    def __init__(self, ctx: BuildContext):
        self.ctx = ctx

    def process(
        self,
        fn: Function,
        fn_node: Node
    ) -> List[Edge]:
        """Process all calls in a function, return call edges."""

    def _resolve_target(
        self,
        call: Call
    ) -> Tuple[Optional[Node], TargetResolution, CallConfidence]:
        """Resolve call target with confidence scoring."""

    def _detect_callbacks(
        self,
        fn: Function,
        call: Call
    ) -> List[Edge]:
        """Detect callback patterns, create bidirectional edges."""
```

### CallInfo Dataclass

```python
@dataclass
class CallInfo:
    source_function: str
    target_function: Optional[str]
    target_contract: Optional[str]
    call_type: CallType  # DIRECT, INTERFACE, DELEGATE, LOW_LEVEL
    resolution: TargetResolution  # DIRECT, INFERRED, INTERFACE, UNRESOLVED
    confidence: CallConfidence  # HIGH, MEDIUM, LOW
    gas_value: Optional[int] = None
    value_sent: bool = False
    is_callback: bool = False
```

### ProxyResolver (proxy.py)

```python
class ProxyResolver:
    """Resolve proxy patterns and implementation contracts."""

    SUPPORTED_PATTERNS = [
        "EIP-1967",      # Standard proxy storage slots
        "UUPS",          # Universal Upgradeable Proxy Standard
        "Diamond",       # EIP-2535 Diamond pattern
        "Beacon",        # Beacon proxy pattern
        "Transparent",   # OpenZeppelin Transparent proxy
    ]

    def resolve(
        self,
        contract: Contract
    ) -> Optional[ProxyInfo]:
        """Detect proxy pattern and resolve implementation."""

    def get_implementation_slots(
        self,
        proxy_type: str
    ) -> List[bytes32]:
        """Get storage slots for implementation address."""
```

---

## Orchestration Layer

**Location:** `src/alphaswarm_sol/orchestration/`

### ExecutionLoop (loop.py)

```python
class ExecutionLoop:
    """Fixed-sequence execution loop with handler injection."""

    PHASE_ORDER = [
        "intake",    # Initial pool setup
        "context",   # Load protocol context
        "beads",     # Create vulnerability beads
        "execute",   # Run agents (A->D->V)
        "verify",    # Run debates
        "integrate", # Merge verdicts
        "complete",  # Finalize pool
    ]

    def __init__(
        self,
        pool_manager: PoolManager,
        config: Optional[LoopConfig] = None
    ):
        self.handlers: Dict[RouteAction, Callable] = {}

    def register_handler(
        self,
        action: RouteAction,
        handler: Callable[[Pool, RouteDecision], PhaseResult]
    ) -> None:
        """Register domain handler for route action."""

    async def run(
        self,
        pool_id: str
    ) -> PhaseResult:
        """Run loop until checkpoint or completion."""

    async def run_single_phase(
        self,
        pool_id: str
    ) -> PhaseResult:
        """Execute single phase, return result."""

    async def resume(
        self,
        pool_id: str
    ) -> PhaseResult:
        """Resume from checkpoint."""
```

### RouteAction Enum (13 actions)

```python
class RouteAction(str, Enum):
    BUILD_GRAPH = "build_graph"
    DETECT_PATTERNS = "detect_patterns"
    LOAD_CONTEXT = "load_context"
    CREATE_BEADS = "create_beads"
    SPAWN_ATTACKERS = "spawn_attackers"
    SPAWN_DEFENDERS = "spawn_defenders"
    SPAWN_VERIFIERS = "spawn_verifiers"
    RUN_DEBATE = "run_debate"
    COLLECT_VERDICTS = "collect_verdicts"
    GENERATE_REPORT = "generate_report"
    FLAG_FOR_HUMAN = "flag_for_human"
    COMPLETE = "complete"
    WAIT = "wait"
```

### Router (router.py)

```python
class Router:
    """Thin routing layer - no domain logic."""

    PHASE_ROUTES: Dict[PoolStatus, RouteAction] = {
        PoolStatus.INTAKE: RouteAction.BUILD_GRAPH,
        PoolStatus.CONTEXT: RouteAction.LOAD_CONTEXT,
        PoolStatus.BEADS: RouteAction.CREATE_BEADS,
        PoolStatus.EXECUTE: RouteAction.SPAWN_ATTACKERS,  # First batch
        PoolStatus.VERIFY: RouteAction.RUN_DEBATE,
        PoolStatus.INTEGRATE: RouteAction.COLLECT_VERDICTS,
        PoolStatus.COMPLETE: RouteAction.COMPLETE,
    }

    def route(self, pool: Pool) -> RouteDecision:
        """Pure routing function - returns action, no side effects."""
```

### ConfidenceEnforcer (confidence.py)

```python
class ConfidenceEnforcer:
    """Enforce verdict confidence rules per ORCH-09/10."""

    def validate(
        self,
        verdict: Verdict
    ) -> ValidationResult:
        """Check verdict against rules without modification."""

    def enforce(
        self,
        verdict: Verdict
    ) -> Verdict:
        """Auto-correct verdict to pass validation."""

    def bucket_uncertain(
        self,
        finding_id: str,
        reason: str
    ) -> Verdict:
        """Create UNCERTAIN verdict for missing context."""

    def elevate_on_test(
        self,
        verdict: Verdict,
        test_passed: bool
    ) -> Verdict:
        """Elevate/downgrade based on test result."""
```

### BatchingPolicy Dataclass

```python
@dataclass
class BatchingPolicy:
    """Agent batching configuration."""
    first_batch: List[str] = field(default_factory=lambda: ["attacker"])
    second_batch: List[str] = field(default_factory=lambda: ["defender"])
    third_batch: List[str] = field(default_factory=lambda: ["verifier"])
    parallel_within_batch: bool = True
    max_parallel: int = 5
    timeout_seconds: int = 300
```

### Verdict Rules

| Rule | Description | Severity |
|------|-------------|----------|
| V-01 | human_flag must be True | ERROR |
| V-02 | CONFIRMED requires evidence | ERROR |
| V-03 | CONFIRMED should have debate | WARNING |
| V-04 | LIKELY requires evidence | ERROR |
| V-05 | Positive requires rationale | ERROR |
| V-06 | Dissent triggers human review | INFO |

### Pool Rules

| Rule | Description | Severity |
|------|-------------|----------|
| P-01 | Pool must have scope files | ERROR |
| P-02 | EXECUTE requires beads | ERROR |
| P-03 | COMPLETE should have all verdicts | WARNING |
| P-04 | FAILED should have reason | WARNING |
| P-05 | All verdicts must pass rules | Inherited |

---

## Semantic Labeling

**Location:** `src/alphaswarm_sol/labels/`

### LLMLabeler (labeler.py)

```python
class LLMLabeler:
    """Microagent for semantic function labeling via tool calling."""

    def __init__(
        self,
        client: Anthropic,
        overlay: LabelOverlay,
        config: Optional[LabelingConfig] = None
    ):
        self.config = config or LabelingConfig()

    async def label_function(
        self,
        graph: KnowledgeGraph,
        function_id: str,
        context: Optional[str] = None
    ) -> LabelingResult:
        """Label single function."""

    async def label_functions(
        self,
        graph: KnowledgeGraph,
        function_ids: List[str],
        context: Optional[str] = None
    ) -> BatchLabelingResult:
        """Batch label functions with automatic batching."""

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics (tokens, cost, counts)."""
```

### LabelingConfig Dataclass

```python
@dataclass
class LabelingConfig:
    max_tokens_per_call: int = 6000
    max_functions_per_batch: int = 5
    min_confidence_threshold: ConfidenceLevel = ConfidenceLevel.LOW
    include_negation_labels: bool = True
    temperature: float = 0.1
```

### LabelOverlay (overlay.py)

```python
class LabelOverlay:
    """Storage for labels separate from core graph."""

    def add_label(
        self,
        function_id: str,
        label: FunctionLabel
    ) -> None:
        """Add label to function."""

    def get_labels(
        self,
        function_id: str
    ) -> List[FunctionLabel]:
        """Get all labels for function."""

    def has_label(
        self,
        function_id: str,
        label_id: str
    ) -> bool:
        """Check if function has specific label."""

    def save(self, path: Path) -> None:
        """Persist overlay to YAML."""

    @classmethod
    def load(cls, path: Path) -> "LabelOverlay":
        """Load overlay from YAML."""
```

### Label Taxonomy (20 labels, 6 categories)

| Category | Labels |
|----------|--------|
| access_control | owner_only, admin_only, role_based, no_access_control |
| state_mutation | balance_update, allowance_update, ownership_transfer |
| external_interaction | external_call, delegate_call, callback_pattern |
| value_handling | eth_transfer, token_transfer, flash_loan |
| control_flow | loop_over_array, conditional_return, require_check |
| security_pattern | reentrancy_guard, check_effects_interactions, pausable |

### Tier C Pattern Matching (tier_c.py)

```python
def match_tier_c(
    function_id: str,
    conditions: List[TierCCondition],
    overlay: LabelOverlay,
    aggregation: AggregationMode = AggregationMode.TIER_A_REQUIRED
) -> MatchResult:
    """Match Tier C conditions against label overlay."""
```

### TierCCondition Types

| Type | Description | Example |
|------|-------------|---------|
| has_label | Function has specific label | `has_label: state_mutation.balance_update` |
| has_any | Function has any of labels | `has_any: [owner_only, admin_only]` |
| has_all | Function has all labels | `has_all: [external_call, eth_transfer]` |
| missing_label | Function lacks label | `missing_label: reentrancy_guard` |
| has_category | Function has label in category | `has_category: access_control` |
| confidence_above | Label confidence above threshold | `confidence_above: 0.8` |

---

## Protocol Context Pack

**Location:** `src/alphaswarm_sol/context/`

### ContextPackBuilder (builder.py)

```python
class ContextPackBuilder:
    """Build protocol context pack from multiple sources."""

    def __init__(
        self,
        project_root: Path,
        config: Optional[BuilderConfig] = None
    ):
        self.code_analyzer = CodeAnalyzer()
        self.doc_parser = DocParser()
        self.web_fetcher = WebFetcher()

    async def build(
        self,
        graph: KnowledgeGraph,
        doc_paths: Optional[List[Path]] = None,
        fetch_web: bool = True
    ) -> ProtocolContextPack:
        """Build complete context pack."""

    def merge(
        self,
        *packs: ProtocolContextPack
    ) -> ProtocolContextPack:
        """Merge multiple context packs with conflict resolution."""
```

### CodeAnalyzer (parser/code_analyzer.py)

```python
class CodeAnalyzer:
    """Extract context from BSKG semantic operations."""

    # 12 operation-to-assumption mappings
    OPERATION_ASSUMPTIONS: Dict[str, str] = {
        "READS_ORACLE": "Oracle data is honest and timely",
        "CALLS_UNTRUSTED": "External contract may be malicious",
        "USES_TIMESTAMP": "Block timestamp is approximately accurate",
        "LOOPS_OVER_ARRAY": "Array length is bounded",
        "PERFORMS_DIVISION": "Divisor is non-zero",
        # ... 7 more mappings
    }

    # 17 modifier-to-role mappings
    ROLE_CAPABILITIES: Dict[str, Tuple[str, str]] = {
        "onlyowner": ("owner", "Full administrative control"),
        "onlyadmin": ("admin", "Administrative operations"),
        "onlyminter": ("minter", "Token minting"),
        "onlypauser": ("pauser", "Emergency pause"),
        # ... 13 more mappings
    }

    def analyze(
        self,
        graph: KnowledgeGraph
    ) -> AnalysisResult:
        """Analyze graph for roles, assumptions, invariants."""
```

### AnalysisResult Dataclass

```python
@dataclass
class AnalysisResult:
    roles: List[Role]
    assumptions: List[Assumption]
    invariants: List[Invariant]
    value_flows: List[ValueFlow]
    offchain_inputs: List[OffchainInput]
    critical_functions: List[str]
```

---

## Tool Integration

**Location:** `src/alphaswarm_sol/tools/`

### ToolCoordinator (coordinator.py)

```python
class ToolCoordinator:
    """Coordinate multi-tool analysis with pattern skip logic."""

    SKIP_THRESHOLD = 0.80  # Skip patterns if tool precision >= 80%

    NEVER_SKIP_PATTERNS = [
        "business-logic-violation",
        "economic-manipulation",
        "governance-attack",
        "cross-function-reentrancy",
        "cross-contract-reentrancy",
        "oracle-manipulation",
        "price-manipulation",
        "slippage-manipulation",
        "sandwich-attack",
        "flash-loan-attack",
        "front-running",
        "privilege-escalation",
        "role-confusion",
    ]

    def create_strategy(
        self,
        project_path: Path,
        available_tools: Optional[List[str]] = None
    ) -> ExecutionStrategy:
        """Create execution strategy for project."""

    def explain_strategy(
        self,
        strategy: ExecutionStrategy
    ) -> str:
        """Human-readable strategy explanation."""

    def get_edge_case_patterns(self) -> List[str]:
        """Get patterns that tools can't detect."""
```

### SemanticDeduplicator (dedup.py)

```python
class SemanticDeduplicator:
    """Two-stage deduplication: location + semantic similarity."""

    def deduplicate(
        self,
        findings: List[Finding]
    ) -> Tuple[List[Finding], DeduplicationStats]:
        """Deduplicate findings, return unique + stats."""

    def _stage1_location_cluster(
        self,
        findings: List[Finding],
        line_tolerance: int = 5
    ) -> List[List[Finding]]:
        """Cluster by file + approximate line number."""

    def _stage2_semantic_similarity(
        self,
        cluster: List[Finding],
        threshold: float = 0.85
    ) -> List[Finding]:
        """Dedupe within cluster by embedding similarity."""
```

### Tool Confidence Boosting

| Tools Agreeing | Confidence Boost |
|----------------|------------------|
| 2 tools | +0.1 |
| 3+ tools | +0.2 |

---

## VulnDocs Framework

**Location:** `vulndocs/` + `src/alphaswarm_sol/vulndocs/`

### VulnDocSchema (schema.py)

```python
class VulnDocIndex(BaseModel):
    """Schema for index.yaml validation."""
    id: str
    category: str
    subcategory: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    vulndoc: VulnDocMeta

    # Phase 7 fields
    semantic_triggers: List[str] = []
    vql_queries: List[str] = []
    graph_patterns: List[Dict[str, Any]] = []
    reasoning_template: Optional[str] = None
```

### Validation Levels

| Level | Requirements |
|-------|--------------|
| MINIMAL | index.yaml with required fields |
| STANDARD | index.yaml + at least one .md file |
| COMPLETE | All recommended .md files present |
| EXCELLENT | Patterns with test coverage |

### CLI Commands

```bash
# Validate
uv run alphaswarm vulndocs validate vulndocs/

# Scaffold new entry
uv run alphaswarm vulndocs scaffold weak-randomness --name "Weak Randomness" --severity high

# Info
uv run alphaswarm vulndocs info vulndocs/reentrancy-classic/

# List
uv run alphaswarm vulndocs list --status validated
```

---

## Model Ranking System

**Location:** `src/alphaswarm_sol/agents/ranking/`

### ModelSelector (selector.py)

```python
class ModelSelector:
    """Select best model based on rankings and profile."""

    def select_model(
        self,
        profile: TaskProfile,
        rankings: Dict[str, ModelRanking]
    ) -> str:
        """Select best model for task profile."""

    def _filter_by_capability(
        self,
        models: List[str],
        profile: TaskProfile
    ) -> List[str]:
        """Filter models by context window capability."""

    def _filter_by_accuracy(
        self,
        models: List[str],
        rankings: Dict[str, ModelRanking],
        profile: TaskProfile
    ) -> List[str]:
        """Filter models meeting accuracy thresholds."""

    def _sort_by_priority(
        self,
        models: List[str],
        rankings: Dict[str, ModelRanking],
        profile: TaskProfile
    ) -> List[str]:
        """Sort by priority: latency, quality, or cost."""
```

### Selection Priority

| Profile Flag | Sort By | Example Use Case |
|--------------|---------|------------------|
| latency_sensitive | Latency (lowest first) | Interactive queries |
| accuracy_critical | Quality (after filtering) | Attacker/Verifier tasks |
| Default | Cost (lowest first) | Routine operations |

### FeedbackCollector (feedback.py)

```python
class FeedbackCollector:
    """Collect feedback and update rankings with EMA."""

    EMA_DECAY = 0.95  # Recent feedback contributes 5%

    def record(
        self,
        feedback: TaskFeedback
    ) -> None:
        """Record task feedback."""

    def update_ranking_from_feedback(
        self,
        model: str,
        feedback: TaskFeedback
    ) -> ModelRanking:
        """Update model ranking using EMA."""
```

### TaskProfile Dataclass

```python
@dataclass
class TaskProfile:
    task_type: TaskType
    context_size: int = 0
    latency_sensitive: bool = False
    accuracy_critical: bool = False
    max_cost_usd: Optional[float] = None
```

### ModelRanking Dataclass

```python
@dataclass
class ModelRanking:
    model_id: str
    success_rate: float = 0.0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost_usd: float = 0.0
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
```

---

## Cross-Reference to Summaries

For implementation details beyond these interfaces, see:

| Module | Summary Files |
|--------|---------------|
| Agent Runtime | 05.2-01-SUMMARY.md, 05.3-01-SUMMARY.md |
| Builder | 02-01 through 02-08-SUMMARY.md |
| Orchestration | 04-01 through 04-07-SUMMARY.md |
| Labeling | 05-01 through 05-09-SUMMARY.md |
| Context | 03-01 through 03-06-SUMMARY.md |
| Tools | 05.1-01 through 05.1-10-SUMMARY.md |
| VulnDocs | 05.4-01 through 05.4-10-SUMMARY.md |
| Ranking | 05.3-07-SUMMARY.md |

---

*Reference: interfaces.md*
*Last Updated: 2026-01-22*
