# BR.4: Table-Driven Detector Pipeline

**Status:** TODO
**Priority:** MUST
**Estimated Hours:** 8-12h
**Depends On:** BR.3 (detectors must exist)
**Unlocks:** BR.5

---

## Objective

Create an explicit, dependency-ordered execution pipeline for detectors. Currently, the order of property extraction is implicit in the code flow. This task makes ordering explicit and validated.

---

## Why This Matters

Some detectors depend on others:
- `mev.py` needs oracle signals (from `oracle.py`)
- `mev.py` needs token signals (from `token.py`)
- `reentrancy.py` needs call analysis first

Without explicit ordering:
1. Future changes may break dependencies
2. Parallel execution becomes impossible
3. Testing requires full integration

---

## Target State

Create `src/true_vkg/kg/pipeline.py`:

```python
"""Detector execution pipeline with dependency ordering.

This module defines the execution order for signal detectors. Dependencies
are validated at startup to prevent circular or missing dependencies.

WARNING: Changing detector order may affect property values if detectors
have implicit dependencies. Always run full test suite after modifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Set
import graphlib  # Python 3.9+ topological sort

from true_vkg.kg.contexts import ContractContext, FunctionContext
from true_vkg.kg.detectors.base import Detector, DetectorResult


@dataclass
class DetectorSpec:
    """Specification for a detector in the pipeline.

    Attributes:
        name: Unique identifier for the detector
        detector_class: The detector class to instantiate
        dependencies: List of detector names that must run before this one
        enabled: Whether to run this detector (for feature flags)
    """
    name: str
    detector_class: type
    dependencies: List[str]
    enabled: bool = True


# Import all detector classes
from true_vkg.kg.detectors.access_control import AccessControlDetector
from true_vkg.kg.detectors.reentrancy import ReentrancyDetector
from true_vkg.kg.detectors.oracle import OracleDetector
from true_vkg.kg.detectors.token import TokenDetector
from true_vkg.kg.detectors.loop import LoopDetector
from true_vkg.kg.detectors.mev import MevDetector
from true_vkg.kg.detectors.proxy import ProxyDetector
from true_vkg.kg.detectors.callback import CallbackDetector
from true_vkg.kg.detectors.crypto import CryptoDetector
from true_vkg.kg.detectors.external_call import ExternalCallDetector


# =============================================================================
# DETECTOR PIPELINE DEFINITION
# =============================================================================

DETECTOR_PIPELINE: List[DetectorSpec] = [
    # Tier 1: No dependencies (can run in parallel)
    DetectorSpec(
        name="access_control",
        detector_class=AccessControlDetector,
        dependencies=[],
    ),
    DetectorSpec(
        name="loop",
        detector_class=LoopDetector,
        dependencies=[],
    ),
    DetectorSpec(
        name="crypto",
        detector_class=CryptoDetector,
        dependencies=[],
    ),
    DetectorSpec(
        name="external_call",
        detector_class=ExternalCallDetector,
        dependencies=[],
    ),

    # Tier 2: Depends on Tier 1
    DetectorSpec(
        name="reentrancy",
        detector_class=ReentrancyDetector,
        dependencies=["external_call"],  # Needs call analysis
    ),
    DetectorSpec(
        name="oracle",
        detector_class=OracleDetector,
        dependencies=["external_call"],  # Needs external call detection
    ),
    DetectorSpec(
        name="token",
        detector_class=TokenDetector,
        dependencies=["external_call"],  # Needs call analysis
    ),
    DetectorSpec(
        name="proxy",
        detector_class=ProxyDetector,
        dependencies=["access_control"],  # May need access info
    ),
    DetectorSpec(
        name="callback",
        detector_class=CallbackDetector,
        dependencies=["external_call"],  # Needs callback detection
    ),

    # Tier 3: Depends on Tier 2
    DetectorSpec(
        name="mev",
        detector_class=MevDetector,
        dependencies=["oracle", "token"],  # Needs both oracle and token signals
    ),
]


# =============================================================================
# PIPELINE RUNNER
# =============================================================================

class DetectorPipeline:
    """Execute detectors in dependency order.

    Usage:
        pipeline = DetectorPipeline(DETECTOR_PIPELINE)
        results = pipeline.run(contract_ctx, function_ctx, slither_fn)
        # results is Dict[str, DetectorResult]
    """

    def __init__(self, specs: List[DetectorSpec]):
        """Initialize pipeline with detector specifications.

        Args:
            specs: List of DetectorSpec defining the pipeline

        Raises:
            graphlib.CycleError: If circular dependencies detected
            ValueError: If dependency references unknown detector
        """
        self._specs = {s.name: s for s in specs if s.enabled}
        self._order = self._compute_order()
        self._detectors: Dict[str, Detector] = {}

        # Instantiate detectors
        for name in self._order:
            spec = self._specs[name]
            self._detectors[name] = spec.detector_class()

    def _compute_order(self) -> List[str]:
        """Compute topological order of detectors.

        Returns:
            List of detector names in execution order

        Raises:
            graphlib.CycleError: If circular dependencies
            ValueError: If dependency references unknown detector
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}

        for name, spec in self._specs.items():
            # Validate dependencies exist
            for dep in spec.dependencies:
                if dep not in self._specs:
                    raise ValueError(
                        f"Detector '{name}' depends on unknown detector '{dep}'"
                    )
            graph[name] = set(spec.dependencies)

        # Topological sort
        sorter = graphlib.TopologicalSorter(graph)
        return list(sorter.static_order())

    def run(
        self,
        contract_ctx: ContractContext,
        function_ctx: FunctionContext,
        slither_fn: Any,
    ) -> Dict[str, DetectorResult]:
        """Run all detectors in order.

        Args:
            contract_ctx: Precomputed contract context
            function_ctx: Precomputed function context
            slither_fn: Raw Slither function object

        Returns:
            Dict mapping detector name to result
        """
        results: Dict[str, DetectorResult] = {}

        for name in self._order:
            detector = self._detectors[name]
            results[name] = detector.detect(
                contract_ctx,
                function_ctx,
                slither_fn,
            )

        return results

    def get_all_properties(
        self,
        results: Dict[str, DetectorResult]
    ) -> Dict[str, Any]:
        """Merge all detector results into single property dict.

        Args:
            results: Output from run()

        Returns:
            Dict of all properties from all detectors
        """
        merged: Dict[str, Any] = {}
        for result in results.values():
            merged.update(result.properties)
        return merged

    def get_all_evidence(
        self,
        results: Dict[str, DetectorResult]
    ) -> List[Dict[str, Any]]:
        """Collect all evidence from all detectors.

        Args:
            results: Output from run()

        Returns:
            List of all evidence items
        """
        evidence = []
        for result in results.values():
            evidence.extend(result.evidence)
        return evidence


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_pipeline(specs: List[DetectorSpec]) -> List[str]:
    """Validate pipeline configuration.

    Args:
        specs: Pipeline specification

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    names = {s.name for s in specs}

    for spec in specs:
        # Check for duplicate names
        if list(s.name for s in specs).count(spec.name) > 1:
            errors.append(f"Duplicate detector name: {spec.name}")

        # Check dependencies exist
        for dep in spec.dependencies:
            if dep not in names:
                errors.append(
                    f"Detector '{spec.name}' depends on unknown '{dep}'"
                )

    # Check for cycles
    try:
        graph = {s.name: set(s.dependencies) for s in specs}
        sorter = graphlib.TopologicalSorter(graph)
        list(sorter.static_order())
    except graphlib.CycleError as e:
        errors.append(f"Circular dependency detected: {e}")

    return errors


def print_pipeline_order(specs: List[DetectorSpec]) -> None:
    """Print pipeline execution order for debugging.

    Args:
        specs: Pipeline specification
    """
    graph = {s.name: set(s.dependencies) for s in specs if s.enabled}
    sorter = graphlib.TopologicalSorter(graph)
    order = list(sorter.static_order())

    print("Detector Pipeline Execution Order:")
    print("=" * 40)
    for i, name in enumerate(order, 1):
        spec = next(s for s in specs if s.name == name)
        deps = ", ".join(spec.dependencies) or "none"
        print(f"  {i}. {name} (deps: {deps})")
```

---

## Implementation Steps

### Step 1: Create pipeline.py (2h)

Create the file with the above structure.

### Step 2: Integrate with builder.py (4h)

Replace inline detection with pipeline execution:

```python
# In builder.py

from true_vkg.kg.pipeline import DetectorPipeline, DETECTOR_PIPELINE

class VKGBuilder:
    def __init__(self, ...):
        ...
        self._pipeline = DetectorPipeline(DETECTOR_PIPELINE)

    def _add_functions(self, graph, contract, contract_node):
        contract_ctx = build_contract_context(contract, contract_node)

        for fn in functions:
            function_ctx = build_function_context(fn, contract_ctx)

            # Run detector pipeline
            results = self._pipeline.run(contract_ctx, function_ctx, fn)
            properties = self._pipeline.get_all_properties(results)
            evidence = self._pipeline.get_all_evidence(results)

            # Create node with merged properties
            node = Node(
                id=...,
                kind="function",
                properties=properties,
                evidence=evidence,
            )
```

### Step 3: Add pipeline validation tests (2h)

```python
# tests/test_pipeline.py

def test_pipeline_no_cycles():
    """Pipeline has no circular dependencies."""
    errors = validate_pipeline(DETECTOR_PIPELINE)
    assert not errors, f"Pipeline errors: {errors}"

def test_pipeline_order_deterministic():
    """Pipeline order is deterministic across runs."""
    p1 = DetectorPipeline(DETECTOR_PIPELINE)
    p2 = DetectorPipeline(DETECTOR_PIPELINE)
    assert p1._order == p2._order

def test_pipeline_produces_same_properties():
    """Pipeline produces identical properties to inline."""
    # Compare with baseline
```

### Step 4: Validate graph fingerprint (2h)

```bash
# Build with pipeline
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/after-pipeline

# Compare fingerprints
diff <(jq -S . /tmp/golden-baseline/graph.json) <(jq -S . /tmp/after-pipeline/graph.json)
```

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/pipeline.py` | CREATE |
| `src/true_vkg/kg/__init__.py` | MODIFY - Export pipeline |
| `src/true_vkg/kg/builder.py` | MODIFY - Use pipeline |
| `tests/test_pipeline.py` | CREATE |

---

## Validation Commands

```bash
# Run pipeline tests
uv run pytest tests/test_pipeline.py -v

# Verify no cycles
uv run python -c "
from true_vkg.kg.pipeline import validate_pipeline, DETECTOR_PIPELINE
errors = validate_pipeline(DETECTOR_PIPELINE)
print('Errors:', errors or 'None')
"

# Print execution order
uv run python -c "
from true_vkg.kg.pipeline import print_pipeline_order, DETECTOR_PIPELINE
print_pipeline_order(DETECTOR_PIPELINE)
"

# Full validation
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py -v
```

---

## Acceptance Criteria

- [ ] `src/true_vkg/kg/pipeline.py` exists
- [ ] Pipeline validates no circular dependencies
- [ ] Pipeline order is deterministic
- [ ] Builder.py uses pipeline for property extraction
- [ ] Graph fingerprint identical to baseline
- [ ] All existing tests pass

---

## Rollback Procedure

```bash
# Remove pipeline
rm src/true_vkg/kg/pipeline.py

# Revert builder
git checkout HEAD -- src/true_vkg/kg/builder.py

# Verify
uv run pytest tests/ -v
```

---

*Task BR.4 | Version 1.0 | 2026-01-07*
