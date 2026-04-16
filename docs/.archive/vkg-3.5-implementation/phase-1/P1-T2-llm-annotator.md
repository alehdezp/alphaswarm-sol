# [P1-T2] LLM Intent Annotator

**Phase**: 1 - Intent Annotation
**Task ID**: P1-T2
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 4-5 days
**Actual Effort**: -

---

## Executive Summary

Implement the LLM-powered intent annotator that analyzes Solidity functions and infers their business purpose, trust assumptions, and expected invariants. This is the core component that bridges code analysis to semantic understanding.

---

## Dependencies

### Required Before Starting
- [ ] [P1-T1] Intent Schema - Defines output structures
- [ ] [P0-T1] Domain Knowledge Graph - Provides spec context

### Blocks These Tasks
- [P1-T3] Builder Integration - Uses annotator during build
- [P2-T2] Attacker Agent - Uses intent for attack planning
- [P2-T3] Defender Agent - Uses intent for defense arguments

---

## Objectives

1. Implement `IntentAnnotator` class with LLM integration
2. Create optimized prompts for intent extraction
3. Implement structured output parsing
4. Add caching to avoid re-annotating unchanged code
5. Support multiple LLM backends (Claude, GPT-4, local models)
6. Batch annotation for efficiency

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INTENT ANNOTATOR                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────┐     ┌──────────────────┐                 │
│   │  Function Node   │────►│  Context Builder │                 │
│   │  (from VKG)      │     │                  │                 │
│   └──────────────────┘     └────────┬─────────┘                 │
│                                     │                            │
│   ┌──────────────────┐              │                           │
│   │  Domain KG Specs │──────────────┤                           │
│   │  (for context)   │              │                           │
│   └──────────────────┘              ▼                            │
│                            ┌──────────────────┐                  │
│                            │  Prompt Builder  │                  │
│                            │                  │                  │
│                            │  • Code context  │                  │
│                            │  • Spec hints    │                  │
│                            │  • Semantic ops  │                  │
│                            │  • Output schema │                  │
│                            └────────┬─────────┘                  │
│                                     │                            │
│                                     ▼                            │
│                            ┌──────────────────┐                  │
│                            │    LLM Client    │                  │
│                            │                  │                  │
│                            │  Claude / GPT-4  │                  │
│                            │  / Local model   │                  │
│                            └────────┬─────────┘                  │
│                                     │                            │
│                                     ▼                            │
│                            ┌──────────────────┐                  │
│                            │  Response Parser │                  │
│                            │                  │                  │
│                            │  JSON → Intent   │                  │
│                            │  + validation    │                  │
│                            └────────┬─────────┘                  │
│                                     │                            │
│                                     ▼                            │
│                            ┌──────────────────┐                  │
│                            │ FunctionIntent   │                  │
│                            └──────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Implementation

```python
class IntentAnnotator:
    """
    LLM-powered intent annotator for Solidity functions.

    Infers business purpose, trust assumptions, and invariants.
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        domain_kg: "DomainKnowledgeGraph",
        cache_dir: Optional[Path] = None,
    ):
        self.llm = llm_client
        self.domain_kg = domain_kg
        self.cache = IntentCache(cache_dir) if cache_dir else None

    def annotate_function(
        self,
        fn_node: "Node",
        code_context: str,
        contract_context: Optional[str] = None,
    ) -> FunctionIntent:
        """Annotate a single function with intent."""

        # Check cache
        cache_key = self._compute_cache_key(fn_node, code_context)
        if self.cache and (cached := self.cache.get(cache_key)):
            return cached

        # Build context
        context = self._build_context(fn_node, code_context, contract_context)

        # Build prompt
        prompt = self._build_prompt(fn_node, context)

        # Call LLM
        response = self.llm.analyze(prompt, response_format="json")

        # Parse response
        intent = self._parse_response(response, fn_node)

        # Cache result
        if self.cache:
            self.cache.set(cache_key, intent)

        return intent

    def annotate_batch(
        self,
        functions: List[tuple["Node", str]],
    ) -> List[FunctionIntent]:
        """Annotate multiple functions efficiently."""
        # Batch for token efficiency
        pass

    def _build_prompt(self, fn_node: "Node", context: dict) -> str:
        """Build optimized prompt for intent extraction."""
        return f"""Analyze this Solidity function to understand its BUSINESS PURPOSE and SECURITY CONTEXT.

## Function Information
- Name: {fn_node.label}
- Visibility: {fn_node.properties.get('visibility', 'unknown')}
- Modifiers: {fn_node.properties.get('modifiers', [])}
- Semantic Operations: {fn_node.properties.get('semantic_ops', [])}
- Behavioral Signature: {fn_node.properties.get('behavioral_signature', '')}

## Code
```solidity
{context['code']}
```

## Contract Context
{context.get('contract_context', 'Not available')}

## Potentially Related Specifications
{context.get('spec_hints', 'None identified')}

## Analysis Task

Analyze this function and provide:

1. **Business Purpose**: What business operation does this implement?
   Choose from: withdrawal, deposit, transfer, claim_rewards, swap, add_liquidity,
   remove_liquidity, vote, propose, execute_proposal, set_parameter, pause,
   upgrade, transfer_ownership, borrow, repay, liquidate, view_only, callback,
   internal_helper, unknown

2. **Trust Level**: Who should be able to call this safely?
   Choose from: permissionless, depositor_only, role_restricted, owner_only, internal_only

3. **Trust Assumptions**: What security assumptions does this code make?
   - What external state must be true?
   - What caller properties are assumed?
   - What timing constraints exist?

4. **Inferred Invariants**: What should be true after this function executes?
   - What balance changes are expected?
   - What state transitions should occur?
   - What properties should be preserved?

5. **Risk Notes**: Any security concerns based on the code structure?

Respond in this exact JSON format:
{{
    "business_purpose": "<purpose>",
    "purpose_confidence": <0.0-1.0>,
    "purpose_reasoning": "<why you inferred this purpose>",
    "expected_trust_level": "<trust_level>",
    "authorized_callers": ["<caller1>", "<caller2>"],
    "trust_assumptions": [
        {{
            "id": "<unique_id>",
            "description": "<what must be true>",
            "category": "<oracle|external_contract|caller|timing|state>",
            "critical": <true|false>
        }}
    ],
    "inferred_invariants": [
        {{
            "id": "<unique_id>",
            "description": "<what should hold after execution>",
            "scope": "<function|transaction|global>"
        }}
    ],
    "likely_specs": ["<spec_id1>", "<spec_id2>"],
    "risk_notes": ["<risk1>", "<risk2>"],
    "complexity_score": <0.0-1.0>
}}
"""
```

---

## Success Criteria

- [ ] LLM integration working (Claude API)
- [ ] Intent extraction accuracy > 80% on test corpus
- [ ] Caching reduces redundant API calls by 90%+
- [ ] Batch annotation 5x faster than individual
- [ ] Graceful fallback when LLM unavailable
- [ ] Token usage optimized (< 2000 tokens per function)

---

## Validation Tests

```python
def test_annotate_withdrawal_function():
    """Test intent annotation for withdrawal."""
    annotator = IntentAnnotator(llm_client, domain_kg)

    fn_node = MockFunctionNode(
        name="withdraw",
        semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    )
    code = """
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
    """

    intent = annotator.annotate_function(fn_node, code)

    assert intent.business_purpose == BusinessPurpose.WITHDRAWAL
    assert intent.purpose_confidence >= 0.8
    assert intent.expected_trust_level == TrustLevel.DEPOSITOR_ONLY
    assert any("balance" in inv.description.lower() for inv in intent.inferred_invariants)

def test_annotate_caching():
    """Test that caching works."""
    annotator = IntentAnnotator(llm_client, domain_kg, cache_dir=tmp_path)

    # First call
    intent1 = annotator.annotate_function(fn_node, code)
    call_count1 = llm_client.call_count

    # Second call (should use cache)
    intent2 = annotator.annotate_function(fn_node, code)
    call_count2 = llm_client.call_count

    assert call_count2 == call_count1  # No new LLM call
    assert intent1.business_purpose == intent2.business_purpose
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination | HIGH | Validate against BSKG properties |
| API rate limits | MEDIUM | Caching, batching |
| Cost explosion | MEDIUM | Token budget, caching |
| Inconsistent outputs | MEDIUM | Structured output format |

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
