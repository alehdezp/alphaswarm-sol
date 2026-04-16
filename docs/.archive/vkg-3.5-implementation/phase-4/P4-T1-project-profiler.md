# [P4-T1] Project Profiler

**Phase**: 4 - Cross-Project Transfer
**Task ID**: P4-T1
**Status**: NOT_STARTED
**Priority**: MEDIUM
**Estimated Effort**: 3 days
**Actual Effort**: -

---

## Executive Summary

Create project profiling system that characterizes Solidity projects by their architecture, DeFi primitives, and vulnerability patterns. Enables finding "similar projects" for cross-project learning.

---

## Dependencies

### Required Before Starting
- [ ] Phase 3 complete
- [ ] [P0-T2] Adversarial Knowledge Graph

### Blocks These Tasks
- [P4-T2] Transfer Engine

---

## Objectives

1. Profile project architecture (proxy, upgradeable, etc.)
2. Identify DeFi primitives used
3. Create project embedding for similarity search
4. Store profiles for known audited projects

---

## Technical Design

```python
@dataclass
class ProjectProfile:
    """Embedding of a project for similarity."""
    project_id: str
    name: str

    # Architecture
    is_upgradeable: bool
    proxy_pattern: Optional[str]
    uses_oracles: bool
    uses_governance: bool

    # DeFi classification
    protocol_type: str  # "dex", "lending", "vault", "nft"
    primitives_used: List[str]  # ["amm", "flash_loan", "staking"]

    # Aggregate stats
    num_contracts: int
    num_functions: int
    operation_histogram: Dict[str, int]  # Semantic ops distribution

    # Known vulnerabilities (for audited projects)
    known_vulns: List[str]

    # Vector embedding for similarity
    embedding: Optional[List[float]] = None


class ProjectProfiler:
    """Creates project profiles for similarity matching."""

    def profile(self, code_kg: "KnowledgeGraph") -> ProjectProfile:
        """Create profile from code KG."""

        # Count operations across all functions
        op_histogram = {}
        for node in code_kg.nodes.values():
            if node.type == "Function":
                for op in node.properties.get("semantic_ops", []):
                    op_histogram[op] = op_histogram.get(op, 0) + 1

        # Detect architecture
        contracts = [n for n in code_kg.nodes.values() if n.type == "Contract"]
        is_upgradeable = any(c.properties.get("is_upgradeable") for c in contracts)

        # Detect protocol type
        protocol_type = self._classify_protocol(op_histogram, contracts)

        return ProjectProfile(
            project_id=code_kg.metadata.get("target", "unknown"),
            name=Path(code_kg.metadata.get("target", "")).stem,
            is_upgradeable=is_upgradeable,
            proxy_pattern=self._detect_proxy_pattern(contracts),
            uses_oracles=op_histogram.get("READS_ORACLE", 0) > 0,
            uses_governance=op_histogram.get("MODIFIES_ROLES", 0) > 0,
            protocol_type=protocol_type,
            primitives_used=self._detect_primitives(op_histogram),
            num_contracts=len(contracts),
            num_functions=sum(1 for n in code_kg.nodes.values() if n.type == "Function"),
            operation_histogram=op_histogram,
            known_vulns=[],
        )

    def _classify_protocol(self, histogram: Dict, contracts) -> str:
        """Classify protocol type from operation distribution."""
        # Heuristics based on operation patterns
        if histogram.get("READS_ORACLE", 0) > 5:
            if histogram.get("TRANSFERS_VALUE_OUT", 0) > 10:
                return "lending"
            return "oracle_consumer"

        if histogram.get("WRITES_USER_BALANCE", 0) > 5:
            if any("swap" in c.label.lower() for c in contracts):
                return "dex"
            return "vault"

        return "utility"
```

---

## Success Criteria

- [ ] Profile creation working
- [ ] Protocol type classification accurate
- [ ] Primitive detection working
- [ ] Embedding generation for similarity

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
