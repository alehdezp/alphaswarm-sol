# [P1-T3] Builder Integration

**Phase**: 1 - Intent Annotation
**Task ID**: P1-T3
**Status**: NOT_STARTED
**Priority**: HIGH
**Estimated Effort**: 2 days
**Actual Effort**: -

---

## Executive Summary

Integrate the Intent Annotator into VKGBuilder so that function nodes automatically receive business intent annotations during graph construction. This makes intent a first-class property of the VKG.

---

## Dependencies

### Required Before Starting
- [ ] [P1-T1] Intent Schema
- [ ] [P1-T2] LLM Intent Annotator

### Blocks These Tasks
- [P1-T4] Intent Validation
- All Phase 2+ tasks that use intent

---

## Objectives

1. Add optional intent annotation to VKGBuilder
2. Store intent as node property
3. Support both eager (during build) and lazy (on-demand) annotation
4. Maintain backward compatibility (intent optional)

---

## Technical Design

### Modified Builder

```python
class VKGBuilder:
    """Enhanced builder with intent annotation support."""

    def __init__(
        self,
        project_root: Path,
        *,
        exclude_dependencies: bool = True,
        intent_annotator: Optional[IntentAnnotator] = None,
        annotate_intent: bool = False,  # Default off for speed
    ):
        self.project_root = project_root
        self.exclude_dependencies = exclude_dependencies
        self.intent_annotator = intent_annotator
        self.annotate_intent = annotate_intent and intent_annotator is not None

    def build(self, target: Path) -> KnowledgeGraph:
        # ... existing build logic ...

        # NEW: Annotate intents if enabled
        if self.annotate_intent:
            self._annotate_all_intents(graph)

        return graph

    def _annotate_all_intents(self, graph: KnowledgeGraph) -> None:
        """Annotate all functions with intent."""
        functions = [n for n in graph.nodes.values() if n.type == "Function"]

        for fn_node in functions:
            code_context = self._get_function_code(fn_node)
            contract_context = self._get_contract_context(fn_node, graph)

            intent = self.intent_annotator.annotate_function(
                fn_node, code_context, contract_context
            )

            # Store as property
            fn_node.properties["intent"] = intent.to_dict()
            fn_node.properties["business_purpose"] = intent.business_purpose.value
            fn_node.properties["trust_level"] = intent.expected_trust_level.value
```

### Lazy Annotation Support

```python
class LazyIntentMixin:
    """Mixin for lazy intent annotation on node access."""

    def get_intent(self, fn_node: Node) -> Optional[FunctionIntent]:
        """Get or compute intent lazily."""
        if "intent" in fn_node.properties:
            return FunctionIntent.from_dict(fn_node.properties["intent"])

        if self.intent_annotator:
            intent = self.intent_annotator.annotate_function(fn_node, ...)
            fn_node.properties["intent"] = intent.to_dict()
            return intent

        return None
```

---

## Success Criteria

- [ ] Builder accepts optional IntentAnnotator
- [ ] Intent stored in node properties
- [ ] Lazy annotation works on-demand
- [ ] Backward compatible (works without annotator)
- [ ] Serialization preserves intent

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
