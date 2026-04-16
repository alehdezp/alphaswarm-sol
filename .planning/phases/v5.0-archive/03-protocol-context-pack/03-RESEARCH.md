# Phase 3: Protocol Context Pack - Research

**Researched:** 2026-01-20
**Domain:** Protocol context extraction, LLM-driven doc parsing, YAML schema design
**Confidence:** HIGH

## Summary

This phase implements Pillar 8 from PHILOSOPHY.md: economic context and off-chain reasoning capability. The goal is to create a Protocol Context Pack - a structured YAML document that captures protocol-level information (roles, incentives, assumptions, off-chain dependencies) that enables LLM agents to reason about business logic vulnerabilities.

Key constraints from 03-CONTEXT.md decisions:
- **LLM-generated, not human-authored** - Agents generate from BSKG analysis, protocol docs, web research
- **YAML format** for human readability
- **Confidence levels** on each field: 'certain', 'inferred', 'unknown'
- **Fully LLM-driven doc parsing** - most flexible for varied doc formats
- **Bidirectional linking** - context pack updates sync to BSKG and vice versa
- **Evidence packet integration** - extends existing schema with `protocol_context`, `assumptions`, `offchain_inputs` fields

The codebase already has robust patterns for:
- YAML-based schemas (patterns/, vulndocs/)
- LLM client abstraction (llm/client.py with multi-provider support)
- Dataclass-based schemas with to_dict/from_dict serialization
- File-based storage patterns (beads/storage.py)
- CLI command structure using Typer

**Primary recommendation:** Build context pack as a new module (`src/true_vkg/context/`) following existing vulndocs schema patterns, with LLM-driven generation through the existing llm/ infrastructure.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.x | YAML parsing/serialization | Established Python YAML library, already in project |
| pydantic | 2.x | Schema validation (optional) | Type-safe validation, already used in codebase |
| dataclasses | stdlib | Schema definitions | Consistent with beads/types.py, vulndocs/schema.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.x | Structured logging | Already used throughout codebase |
| httpx | 0.x | Web fetching for docs | Already dependency, used in llm/research.py |
| Typer | 0.x | CLI commands | Already used in cli/main.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML | ruamel.yaml | Better comment preservation, but heavier dependency |
| dataclasses | pydantic models | More validation, but inconsistent with existing schemas |
| httpx | aiohttp | Async-native, but httpx already in deps |

**Installation:**
```bash
# No new dependencies required - all needed libraries already in project
```

## Architecture Patterns

### Recommended Project Structure
```
src/true_vkg/context/
    __init__.py           # Exports: ContextPack, ContextPackBuilder, ContextPackStorage
    schema.py             # Dataclass definitions for context pack schema
    builder.py            # LLM-driven context pack generation
    storage.py            # File-based storage (like beads/storage.py)
    parser/
        __init__.py
        doc_parser.py     # LLM-driven document parsing
        code_analyzer.py  # Extract context from BSKG analysis
        web_fetcher.py    # Fetch external docs (README, whitepaper)
    integrations/
        __init__.py
        evidence.py       # Evidence packet extension
        vkg.py            # BSKG bidirectional sync
        bead.py           # Bead context inheritance
```

### Pattern 1: Dataclass Schema with Confidence Levels
**What:** Use dataclasses with explicit confidence enum per field
**When to use:** All context pack fields that may be inferred or uncertain
**Example:**
```python
# Source: Existing patterns in beads/types.py, vulndocs/schema.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

class Confidence(Enum):
    """Confidence level for context pack fields."""
    CERTAIN = "certain"      # Verified from official docs or code
    INFERRED = "inferred"    # Derived by LLM reasoning
    UNKNOWN = "unknown"      # Could not determine

@dataclass
class ConfidenceField:
    """A field with confidence metadata."""
    value: Any
    confidence: Confidence = Confidence.UNKNOWN
    source: str = ""         # Where this came from (doc, code, inference)
    source_tier: int = 3     # 1=official, 2=audit, 3=community

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "source_tier": self.source_tier,
        }

@dataclass
class Role:
    """A protocol role with capabilities and trust assumptions."""
    name: str
    capabilities: List[str]          # What this role CAN DO: mint, pause, upgrade
    trust_assumptions: List[str]     # Assumptions about role behavior
    confidence: Confidence = Confidence.INFERRED

@dataclass
class ProtocolContextPack:
    """Complete protocol context pack."""
    version: str = "1.0"
    protocol_name: str = ""
    protocol_type: str = ""          # lending, dex, nft, etc.

    # Roles and capabilities
    roles: List[Role] = field(default_factory=list)

    # Economic model
    value_flows: List[Dict[str, Any]] = field(default_factory=list)
    incentives: List[str] = field(default_factory=list)

    # Assumptions
    assumptions: List[Dict[str, Any]] = field(default_factory=list)
    accepted_risks: List[str] = field(default_factory=list)

    # Off-chain inputs
    offchain_inputs: List[Dict[str, Any]] = field(default_factory=list)

    # Invariants
    invariants: List[Dict[str, Any]] = field(default_factory=list)

    # Security model
    security_model: Dict[str, Any] = field(default_factory=dict)

    # Critical functions
    critical_functions: List[str] = field(default_factory=list)

    # Metadata
    sources: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""
    auto_generated: bool = True
    reviewed: bool = False
```

### Pattern 2: LLM-Driven Generation Pipeline
**What:** Use existing LLM client for structured extraction
**When to use:** All doc parsing and context inference
**Example:**
```python
# Source: Pattern from llm/client.py, llm/annotations.py
from true_vkg.llm.client import LLMClient
from true_vkg.llm.config import Provider
import json

class ContextPackBuilder:
    """LLM-driven context pack generation."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    async def generate_from_docs(
        self,
        doc_content: str,
        code_analysis: Dict[str, Any],
        source_tier: int = 1,
    ) -> ProtocolContextPack:
        """Generate context pack from documentation."""

        # Step 1: Extract roles and capabilities
        roles_prompt = self._build_roles_prompt(doc_content, code_analysis)
        roles_json = await self.llm.analyze_json(roles_prompt, system=EXTRACTION_SYSTEM)

        # Step 2: Extract assumptions
        assumptions_prompt = self._build_assumptions_prompt(doc_content)
        assumptions_json = await self.llm.analyze_json(assumptions_prompt)

        # Step 3: Cross-validate with code
        validated = await self._cross_validate(roles_json, assumptions_json, code_analysis)

        return self._build_pack(validated, source_tier)
```

### Pattern 3: Evidence Packet Extension
**What:** Add optional context fields to existing evidence packet schema
**When to use:** When findings need protocol context
**Example:**
```python
# Source: PHILOSOPHY.md Evidence Packet Contract
# Evidence packet already has optional fields:
#   protocol_context: [string]
#   assumptions: [string]
#   offchain_inputs: [string]

@dataclass
class EvidencePacketContextExtension:
    """Context fields for evidence packets."""

    # Relevant protocol context sections
    protocol_context: List[str] = field(default_factory=list)

    # Assumptions that support/contradict finding
    relevant_assumptions: List[str] = field(default_factory=list)
    violated_assumptions: List[str] = field(default_factory=list)

    # Off-chain dependencies affecting this finding
    offchain_dependencies: List[str] = field(default_factory=list)

    # Business impact derived from context
    business_impact: str = ""

    # Whether this is an accepted risk
    is_accepted_risk: bool = False
```

### Pattern 4: CLI Integration (Typer Subcommand)
**What:** Add context commands to existing CLI structure
**When to use:** CLI commands for generate-context, update-context
**Example:**
```python
# Source: Pattern from cli/main.py, cli/beads.py
import typer
from pathlib import Path

context_app = typer.Typer(help="Protocol context pack management")

@context_app.command("generate")
def generate_context(
    path: str = typer.Argument(..., help="Path to Solidity project"),
    docs: str = typer.Option(None, "--docs", help="Path to docs directory"),
    output: str = typer.Option(None, "--output", "-o", help="Output path for context pack"),
    sources: List[str] = typer.Option(None, "--source", help="Additional doc sources"),
) -> None:
    """Generate protocol context pack from code and documentation."""
    # Implementation follows existing CLI patterns
```

### Anti-Patterns to Avoid
- **Manual context authoring required:** Users decided LLM-generated, not human-authored
- **Single-source extraction:** Must combine BSKG analysis + docs + web research
- **Static context:** Must support incremental updates when code changes
- **Monolithic retrieval:** Must enable section-level retrieval for token efficiency

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM calls | Custom HTTP client | `llm/client.py` LLMClient | Has caching, fallback, cost tracking |
| YAML parsing | Custom parser | PyYAML with dataclass mapping | Consistent with patterns/ |
| File storage | Custom file handling | Pattern from `beads/storage.py` | Proven, tested pattern |
| CLI commands | argparse | Typer (existing) | Consistent with main.py |
| Document fetching | requests | httpx (existing) | Already in deps, async-capable |
| Structured prompts | String concatenation | `llm/prompts.py` PromptBuilder | Handles formatting, modes |

**Key insight:** The codebase has mature abstractions for LLM interaction, file storage, and CLI. Use them rather than building parallel implementations.

## Common Pitfalls

### Pitfall 1: Context Window Bloat
**What goes wrong:** Context pack grows too large, fills LLM context window
**Why it happens:** Including full documents instead of relevant excerpts
**How to avoid:**
- Design for section-level retrieval from the start
- Use `token_estimate` fields (like vulndocs/schema.py)
- Embed excerpts, not full docs
- Support targeted retrieval by section
**Warning signs:** Single context pack > 5000 tokens

### Pitfall 2: Stale Context
**What goes wrong:** Context pack doesn't reflect code changes
**Why it happens:** No incremental update mechanism
**How to avoid:**
- Track source hashes for change detection
- Implement `update_context()` that diffs and regenerates
- Store timestamps and version info
**Warning signs:** Context pack has no versioning or changelog

### Pitfall 3: Unvalidated Inferences
**What goes wrong:** LLM inferences treated as facts
**Why it happens:** No cross-validation with code
**How to avoid:**
- Always cross-validate doc claims against code analysis
- Mark inferences with `confidence: inferred`
- Flag conflicts explicitly
**Warning signs:** All fields marked `certain` when LLM-generated

### Pitfall 4: Orphaned Context
**What goes wrong:** Context pack not connected to beads/findings
**Why it happens:** Building context pack in isolation
**How to avoid:**
- Design evidence packet extension from the start
- Implement bead inheritance (each bead gets relevant context)
- Build BSKG sync for bidirectional linking
**Warning signs:** Context pack exists but not used in analysis

### Pitfall 5: Missing Source Attribution
**What goes wrong:** Can't trace where context came from
**Why it happens:** Not tracking sources during extraction
**How to avoid:**
- Section-level attribution (per 03-CONTEXT.md decision)
- Source reliability tiers: Tier 1 (official), Tier 2 (audits), Tier 3 (community)
- Store source URLs and document versions
**Warning signs:** Context pack has no `sources` section

## Code Examples

Verified patterns from codebase:

### Storage Pattern (from beads/storage.py)
```python
# Source: /Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/beads/storage.py
class ContextPackStorage:
    """File-based storage for context packs."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, pack: ProtocolContextPack, name: str = "context") -> Path:
        """Save context pack as YAML."""
        pack_path = self.path / f"{name}.yaml"
        with open(pack_path, "w", encoding="utf-8") as f:
            yaml.dump(pack.to_dict(), f, default_flow_style=False)
        return pack_path

    def load(self, name: str = "context") -> Optional[ProtocolContextPack]:
        """Load context pack from YAML."""
        pack_path = self.path / f"{name}.yaml"
        if not pack_path.exists():
            return None
        with open(pack_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ProtocolContextPack.from_dict(data)
```

### LLM JSON Extraction (from llm/client.py)
```python
# Source: /Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/llm/client.py
async def extract_roles(self, doc_content: str) -> Dict[str, Any]:
    """Extract roles from documentation using LLM."""
    prompt = f"""Analyze this protocol documentation and extract all roles:

{doc_content}

Return JSON with format:
{{
    "roles": [
        {{
            "name": "role name",
            "capabilities": ["capability1", "capability2"],
            "trust_assumptions": ["assumption about this role"],
            "confidence": "certain|inferred|unknown"
        }}
    ]
}}"""

    return await self.llm.analyze_json(prompt, system=EXTRACTION_SYSTEM)
```

### Schema with Serialization (from vulndocs/schema.py)
```python
# Source: /Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/vulndocs/schema.py
@dataclass
class Assumption:
    """A protocol assumption with metadata."""
    description: str
    category: str = ""           # price, time, trust, economic
    affects_functions: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.INFERRED
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "category": self.category,
            "affects_functions": self.affects_functions,
            "confidence": self.confidence.value,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Assumption":
        return cls(
            description=data.get("description", ""),
            category=data.get("category", ""),
            affects_functions=data.get("affects_functions", []),
            confidence=Confidence(data.get("confidence", "unknown")),
            source=data.get("source", ""),
        )
```

### CLI Command Pattern (from cli/main.py)
```python
# Source: /Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/cli/main.py
@app.command("generate-context")
def generate_context(
    path: str = typer.Argument(..., help="Path to Solidity project"),
    docs: str = typer.Option(None, "--docs", "-d", help="Path to documentation"),
    output: str = typer.Option(None, "--output", "-o", help="Output path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
) -> None:
    """Generate protocol context pack from code and documentation.

    Examples:
        # Auto-discover docs
        uv run alphaswarm generate-context ./src

        # Specify docs directory
        uv run alphaswarm generate-context ./src --docs ./docs

        # Custom output path
        uv run alphaswarm generate-context ./src -o ./context.yaml
    """
    try:
        # Implementation follows existing CLI patterns
        pass
    except Exception as exc:
        _handle_error(exc)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual context docs | LLM-generated context | 2025+ | Scales to any protocol |
| Single source truth | Multi-source with reliability tiers | 2025+ | Better accuracy |
| Binary classifications | Confidence levels + nuance | 2025+ | Supports "maybe vulnerable" |
| Code-only analysis | Code + docs + external sources | 2025+ | Catches business logic bugs |

**Deprecated/outdated:**
- Manual protocol summaries: Too slow, doesn't scale
- Hardcoded role assumptions: Can't adapt to protocol variations

## Open Questions

Things that couldn't be fully resolved:

1. **Off-chain input structure**
   - What we know: Need to track oracles, relayers, admins, UIs
   - What's unclear: Best structure (input registry, role embedding, or dependency graph)
   - Recommendation: Let implementation decide based on what emerges during development (per 03-CONTEXT.md: Claude's discretion)

2. **Assumption categorization**
   - What we know: Need categories for filtering (price, time, trust, economic)
   - What's unclear: Fixed categories vs. freeform tags
   - Recommendation: Start with freeform tags, consolidate to categories if patterns emerge

3. **Context pack composability**
   - What we know: May need inheritance for multi-contract protocols
   - What's unclear: Whether to support composition now or later
   - Recommendation: Design schema to allow future composition but don't implement now

4. **Multimodal doc parsing**
   - What we know: Decision to use vision for diagrams and flowcharts
   - What's unclear: Which LLM providers support vision well enough
   - Recommendation: Implement text-first, add vision as enhancement

## Sources

### Primary (HIGH confidence)
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/docs/PHILOSOPHY.md` - Pillar 8, Evidence Packet Contract
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/.planning/phases/03-protocol-context-pack/03-CONTEXT.md` - User decisions
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/beads/schema.py` - Bead schema patterns
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/vulndocs/schema.py` - VulnDocs schema patterns
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/llm/client.py` - LLM client abstraction
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/kg/schema.py` - Knowledge graph schema

### Secondary (MEDIUM confidence)
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/tests/test_beads_schema.py` - Testing patterns
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/tests/test_llm_integration.py` - LLM testing patterns
- `/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm/src/true_vkg/cli/main.py` - CLI patterns

### Tertiary (LOW confidence)
- General YAML schema best practices from training data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project
- Architecture: HIGH - Following established patterns from beads/, vulndocs/
- Pitfalls: HIGH - Based on CONTEXT.md decisions and codebase review
- Schema design: MEDIUM - Some aspects left to implementation discretion

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable domain, established patterns)
