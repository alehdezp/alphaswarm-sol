# Phase 5: Semantic Labeling - Research

**Researched:** 2026-01-20
**Domain:** LLM-driven semantic labeling for smart contract security analysis
**Confidence:** HIGH

## Summary

Semantic labeling enables detection of complex logic bugs that pure pattern matching misses by assigning intent and constraint labels to functions. The BSKG codebase already has strong foundations: an LLM provider abstraction (`llm/`), graph slicing infrastructure (`kg/slicer.py`), and an annotation system (`llm/annotations.py`) that can be extended.

The research confirms three key implementation strategies:
1. **Tool calling with structured outputs** - Anthropic's structured outputs (Nov 2025) guarantee schema compliance via constrained decoding, eliminating JSON parsing failures
2. **Hierarchical label taxonomy** - Coarse categories with fine sub-labels (e.g., `access_control.owner_only`) enables context filtering
3. **Sliced subgraph context** - Existing `GraphSlicer` can reduce context by ~75%, staying within 6k token budget

**Primary recommendation:** Implement the labeler as a microagent using tool calling with Anthropic's structured outputs, passing category-sliced subgraphs, and storing labels as overlay properties on function nodes.

## Standard Stack

The labeling system builds on existing BSKG infrastructure rather than introducing new dependencies.

### Core (Existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | 0.39+ | Primary LLM provider | Structured outputs beta, tool calling |
| `pydantic` | 2.x | Schema validation | Already used for LLMResponse |
| `networkx` | 3.x | Graph operations | Already used in kg/ |

### Supporting (Existing)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tiktoken` | 0.5+ | Token counting | Budget enforcement |
| `yaml` | - | Label taxonomy storage | Human-readable configs |

### New (Minimal)
| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| None | - | - | Full implementation uses existing infrastructure |

**Installation:** No new dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
src/true_vkg/
├── labels/
│   ├── __init__.py
│   ├── taxonomy.py        # LabelCategory, LabelDefinition, CORE_TAXONOMY
│   ├── schema.py          # FunctionLabel, LabelConfidence, LabelSet
│   ├── labeler.py         # LLMLabeler microagent
│   ├── validator.py       # Label validation and scoring
│   ├── overlay.py         # Label overlay lifecycle
│   └── tools.py           # Tool definitions for structured output
├── patterns/
│   ├── tier_c.py          # Tier C label-aware pattern matcher (new)
│   └── label_patterns/    # Policy mismatch, invariant patterns
└── queries/
    └── label_functions.py # VQL label query functions
```

### Pattern 1: Tool Calling for Labeling

**What:** Use Claude's tool calling with structured outputs to guarantee valid label responses
**When to use:** All labeler LLM calls
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs

APPLY_LABEL_TOOL = {
    "name": "apply_label",
    "description": "Apply a semantic label to a function",
    "input_schema": {
        "type": "object",
        "properties": {
            "function_id": {"type": "string"},
            "label": {
                "type": "string",
                "enum": ["access_control.owner_only", "access_control.role_based", ...]
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"]
            },
            "reasoning": {
                "type": "string",
                "description": "Required only if confidence is low"
            }
        },
        "required": ["function_id", "label", "confidence"]
    }
}

# With structured outputs header (anthropic-beta: structured-outputs-2025-11-13)
# the label field is guaranteed to be one of the enum values
```

### Pattern 2: Overlay Label Storage

**What:** Store labels as a separate overlay layer on function nodes, not modifying core properties
**When to use:** Label persistence and retrieval
**Example:**
```python
@dataclass
class FunctionLabel:
    """Semantic label attached to a function."""
    label_id: str                    # e.g., "access_control.owner_only"
    category: str                    # e.g., "access_control"
    subcategory: str                 # e.g., "owner_only"
    confidence: LabelConfidence      # HIGH, MEDIUM, LOW
    source: LabelSource              # LLM, USER_OVERRIDE, PATTERN_INFERRED
    reasoning: Optional[str] = None  # Required if uncertain
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class LabelOverlay:
    """Overlay layer storing labels for a graph."""
    labels: Dict[str, List[FunctionLabel]]  # function_id -> labels
    version: str = "1.0"

    def get_labels(self, function_id: str, category: Optional[str] = None) -> List[FunctionLabel]:
        """Get labels for a function, optionally filtered by category."""
        labels = self.labels.get(function_id, [])
        if category:
            labels = [l for l in labels if l.category == category]
        return labels
```

### Pattern 3: Context-Filtered Label Retrieval

**What:** Filter labels based on current analysis context to prevent context pollution
**When to use:** When returning labels to LLM for pattern matching or verification
**Example:**
```python
def get_filtered_labels(
    function_id: str,
    analysis_context: str,  # e.g., "reentrancy", "access_control"
) -> List[FunctionLabel]:
    """Return only labels relevant to current analysis."""
    # Map analysis context to relevant label categories
    CONTEXT_TO_CATEGORIES = {
        "reentrancy": ["state_mutation", "external_calls", "guards"],
        "access_control": ["access_control", "authorization", "roles"],
        "oracle": ["external_data", "price_feeds", "validation"],
    }

    relevant_categories = CONTEXT_TO_CATEGORIES.get(analysis_context, [])
    all_labels = overlay.get_labels(function_id)
    return [l for l in all_labels if l.category in relevant_categories]
```

### Pattern 4: Sliced Subgraph for Token Efficiency

**What:** Use existing GraphSlicer to extract category-relevant subgraph for labeling
**When to use:** Preparing context for labeler LLM call
**Example:**
```python
# Source: existing src/true_vkg/kg/slicer.py

from true_vkg.kg.slicer import GraphSlicer, slice_graph_for_category

def prepare_labeling_context(
    graph: KnowledgeGraph,
    function_id: str,
    max_tokens: int = 4000,  # Leave 2k for system prompt + output
) -> SlicedGraph:
    """Prepare minimal context for labeling."""
    # Extract 2-hop neighborhood
    subgraph = extract_neighborhood(graph, function_id, depth=2)

    # Slice to general properties (for labeling, we want broader view)
    sliced = GraphSlicer(include_core=True).slice_for_category(
        subgraph, "general"
    )

    # Compress if still over budget
    if estimate_tokens(sliced) > max_tokens:
        sliced = compress_to_essential(sliced, max_tokens)

    return sliced
```

### Anti-Patterns to Avoid

- **Full graph context:** Never pass the entire graph to the labeler - use sliced subgraphs
- **Storing labels in core properties:** Keep labels in overlay to avoid polluting deterministic properties
- **Ignoring label confidence:** Always filter by confidence threshold for pattern matching
- **Unbatched labeling:** Batch related functions together to reduce LLM calls
- **Hardcoded labels in patterns:** Use label references, not hardcoded strings

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom JSON parser | Anthropic structured outputs | Constrained decoding guarantees schema compliance |
| Token counting | Naive character estimation | tiktoken | Accurate counts prevent budget overruns |
| Graph slicing | Custom subgraph extraction | GraphSlicer from kg/slicer.py | Already handles category-aware property filtering |
| Label storage | Custom file format | LLMAnnotation extension | annotations.py already has the schema pattern |
| Context compression | Manual truncation | TOON encoder from subagents.py | 30-50% token reduction with existing code |

**Key insight:** The BSKG codebase already has ~80% of the infrastructure needed. The labeling system should integrate with existing patterns, not reinvent them.

## Common Pitfalls

### Pitfall 1: Token Budget Overruns
**What goes wrong:** LLM calls exceed 6k token budget, causing truncation or errors
**Why it happens:** Full function source + call graph + properties exceeds budget
**How to avoid:**
- Use GraphSlicer with strict_mode=True for minimal properties
- Compress function source to signature + key statements
- Limit call graph to 1-hop for large functions
**Warning signs:** Token estimate > 5k before adding system prompt

### Pitfall 2: Label Taxonomy Explosion
**What goes wrong:** Too many fine-grained labels make matching unreliable
**Why it happens:** Over-engineering the taxonomy before validation
**How to avoid:**
- Start with ~20 core labels across 5-6 categories
- Add sub-labels only when precision data justifies it
- Prefer hierarchical labels (coarse.fine) over flat enumeration
**Warning signs:** More than 50 total labels in initial taxonomy

### Pitfall 3: Context Pollution
**What goes wrong:** Irrelevant labels confuse LLM during pattern matching
**Why it happens:** Returning all labels regardless of current analysis focus
**How to avoid:**
- Implement context-filtered label retrieval from day one
- Map analysis types to relevant label categories
- Test with adversarial contexts (reentrancy labels during auth analysis)
**Warning signs:** False positives increase when labels are added

### Pitfall 4: Confidence Threshold Mismatch
**What goes wrong:** Low-confidence labels treated same as high-confidence
**Why it happens:** Ignoring confidence in pattern matching
**How to avoid:**
- Patterns should specify minimum confidence requirements
- Default to HIGH confidence for Tier C patterns
- Uncertain labels (< 0.5) should not trigger patterns without verification
**Warning signs:** High false positive rate on label-based patterns

### Pitfall 5: Stale Labels After Code Changes
**What goes wrong:** Labels persist after code is modified, leading to mismatches
**Why it happens:** Labels not invalidated on code change
**How to avoid:**
- Hash function source for change detection (context_hash pattern from beads)
- Mark labels as needing re-evaluation when source changes
- Support incremental re-labeling for modified functions only
**Warning signs:** Labels reference non-existent code patterns

## Code Examples

Verified patterns from official sources and existing codebase:

### Tool Definition for Label Application
```python
# Based on: https://platform.claude.com/docs/en/build-with-claude/structured-outputs

from typing import Literal

LABEL_TOOLS = [
    {
        "name": "apply_labels",
        "description": "Apply semantic labels to functions in batch",
        "input_schema": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "function_id": {"type": "string"},
                            "label": {"type": "string"},
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"]
                            }
                        },
                        "required": ["function_id", "label", "confidence"]
                    }
                }
            },
            "required": ["labels"]
        }
    }
]

# Request with structured outputs
response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=2048,
    tools=LABEL_TOOLS,
    tool_choice={"type": "tool", "name": "apply_labels"},
    extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
    messages=[{"role": "user", "content": labeling_prompt}]
)
```

### Core Label Taxonomy Structure
```python
# Source: CONTEXT.md decisions + existing property_sets.py pattern

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class LabelCategory(str, Enum):
    """Top-level label categories."""
    ACCESS_CONTROL = "access_control"
    STATE_MUTATION = "state_mutation"
    EXTERNAL_INTERACTION = "external_interaction"
    VALUE_HANDLING = "value_handling"
    INVARIANTS = "invariants"
    TEMPORAL = "temporal"

@dataclass
class LabelDefinition:
    """Definition of a semantic label."""
    id: str                          # "access_control.owner_only"
    category: LabelCategory
    subcategory: str                 # "owner_only"
    description: str
    examples: List[str]              # Code patterns that match
    anti_examples: List[str]         # Patterns that look similar but differ
    negation_id: Optional[str]       # "no_access_control" if applicable

# Core taxonomy (~20 labels to start)
CORE_TAXONOMY = [
    LabelDefinition(
        id="access_control.owner_only",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="owner_only",
        description="Function restricted to contract owner",
        examples=["require(msg.sender == owner)", "onlyOwner modifier"],
        anti_examples=["role-based access", "multi-sig"],
        negation_id="access_control.no_restriction",
    ),
    LabelDefinition(
        id="access_control.role_based",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="role_based",
        description="Function restricted by role assignment",
        examples=["hasRole(ADMIN_ROLE, msg.sender)", "AccessControl"],
        anti_examples=["simple owner check"],
        negation_id="access_control.no_restriction",
    ),
    # ... additional labels
]
```

### Tier C Pattern Matcher
```python
# Extension of existing patterns.py PatternEngine

@dataclass
class TierCCondition:
    """Tier C label-based condition."""
    type: str  # "has_label", "has_any_label", "missing_label"
    labels: List[str]
    min_confidence: str = "medium"
    category_filter: Optional[str] = None

class TierCMatcher:
    """Match patterns requiring semantic labels."""

    def __init__(self, label_overlay: LabelOverlay):
        self.overlay = label_overlay

    def matches(
        self,
        node: Node,
        conditions: List[TierCCondition],
        analysis_context: Optional[str] = None,
    ) -> bool:
        """Check if node satisfies Tier C conditions."""
        labels = self.overlay.get_labels(node.id)

        if analysis_context:
            # Context filtering
            labels = filter_by_context(labels, analysis_context)

        for cond in conditions:
            if not self._check_condition(labels, cond):
                return False
        return True

    def _check_condition(
        self,
        labels: List[FunctionLabel],
        cond: TierCCondition,
    ) -> bool:
        """Check single condition."""
        # Filter by confidence
        confident_labels = [
            l for l in labels
            if confidence_value(l.confidence) >= confidence_value(cond.min_confidence)
        ]
        label_ids = {l.label_id for l in confident_labels}

        if cond.type == "has_label":
            return all(lid in label_ids for lid in cond.labels)
        elif cond.type == "has_any_label":
            return any(lid in label_ids for lid in cond.labels)
        elif cond.type == "missing_label":
            return all(lid not in label_ids for lid in cond.labels)

        return False
```

### VQL Label Query Functions
```python
# Extension to queries/executor.py

def has_label(node: Node, label_id: str, overlay: LabelOverlay) -> bool:
    """VQL function: has_label('access_control.owner_only')"""
    labels = overlay.get_labels(node.id)
    return any(l.label_id == label_id for l in labels)

def label_confidence(node: Node, label_id: str, overlay: LabelOverlay) -> str:
    """VQL function: label_confidence('access_control.owner_only')"""
    labels = overlay.get_labels(node.id)
    for l in labels:
        if l.label_id == label_id:
            return l.confidence.value
    return "none"

def labels_in_category(node: Node, category: str, overlay: LabelOverlay) -> List[str]:
    """VQL function: labels_in_category('access_control')"""
    labels = overlay.get_labels(node.id, category=category)
    return [l.label_id for l in labels]

# VQL query example:
# FIND functions WHERE has_label('access_control.owner_only') AND writes_privileged_state
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode prompting | Structured outputs with constrained decoding | Nov 2025 | Guaranteed schema compliance |
| Manual prompt parsing | Tool calling with schemas | 2024 | Reliable structured extraction |
| Full context dumps | RAG + sliced subgraphs | 2024 | 70%+ context reduction |
| Flat label lists | Hierarchical taxonomies | Ongoing | Better precision and recall |

**Deprecated/outdated:**
- JSON mode without schema enforcement: Use structured outputs instead
- Single-label per function: Multi-label with confidence is standard now

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal taxonomy granularity**
   - What we know: Hierarchical structure (category.subcategory) is decided
   - What's unclear: Exact number of initial labels (research suggests 15-25)
   - Recommendation: Start with ~20, expand based on precision metrics

2. **Batch size for related functions**
   - What we know: Batching reduces cost, context should include call relationships
   - What's unclear: Optimal batch size before context overflow
   - Recommendation: Experiment with 3-5 functions per batch, measure token usage

3. **Label inheritance for overridden functions**
   - What we know: Parent function labels may not apply to overrides
   - What's unclear: When to inherit vs re-label
   - Recommendation: Re-label overrides, use parent labels as hints only

4. **Protocol-specific taxonomy extensions**
   - What we know: Lending, AMM, etc. may need domain labels
   - What's unclear: How to activate/manage protocol packs
   - Recommendation: Use protocol_context_pack flag to enable extensions

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Tool calling with constrained decoding
- [Anthropic Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) - Tool search, programmatic calling
- Existing BSKG codebase: `kg/slicer.py`, `llm/annotations.py`, `llm/subagents.py`

### Secondary (MEDIUM confidence)
- [Token-Budget-Aware LLM Reasoning](https://aclanthology.org/2025.findings-acl.1274/) - ACL 2025, dynamic token allocation
- [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/) - Constrained sampling reference
- [Guide to Structured Outputs](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms) - Comparison of methods

### Tertiary (LOW confidence)
- [SmartSecure Framework](https://onlinelibrary.wiley.com/doi/10.1002/cpe.70214) - Semantic vulnerability mining (2025)
- [LLM Smart Contract Detection](https://arxiv.org/abs/2501.02229) - ML + LLM hybrid approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing BSKG infrastructure
- Architecture: HIGH - Extends proven patterns (annotations, slicing)
- Pitfalls: MEDIUM - Based on general LLM engineering, not VKG-specific validation
- Label taxonomy: MEDIUM - Structure validated, specific labels need iteration

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable domain, structured outputs is production-ready)
