# Phase 9 Brutal Critique

## Critical Issues Found

### 1. PPR Algorithm Research is Dangerously Vague
**Severity: BLOCKER**

R9.1 says "Study HippoRAG PPR Algorithm" with output "Adapted algorithm for VKG" but:
- HippoRAG PPR is for text retrieval, not security graph traversal
- No explanation of how to adapt edge weights for security relevance
- Risk score weighting formula in Task 9.1 is INVENTED without justification
- Alpha = 0.15 is copied from HippoRAG but may not be appropriate for VKG

**Reality Check:** The PPR implementation in Task 9.1 is pseudocode that won't converge properly because:
- It uses `in_edges` but should normalize by out-degree
- The weight function multiplies factors that can explode (1.5 * 1.5 * risk_score = blow up)
- Convergence detection is not defined

---

### 2. TOON Format Doesn't Exist
**Severity: HIGH**

Task 9.8 references "TOON Spec: toon-spec.io" but:
- That URL doesn't exist
- TOON is not a standard format
- The "TOON" in the example is just YAML

**Fix:** Either use YAML/TOML or define your own spec. Don't reference non-existent standards.

---

### 3. Query-to-Seed Mapping Assumes Query Types That Don't Exist
**Severity: HIGH**

Task 9.2 shows:
```python
if query.type == "finding":
if query.type == "pattern":
if query.type == "vql":
```

But the existing query system (`src/true_vkg/queries/`) doesn't have this `Query` type with a `.type` attribute. Need to:
- Define the Query abstraction
- Integrate with existing VQL2 executor
- Handle NL queries (which go through LLM)

---

### 4. Subgraph.py Already Exists
**Severity: MEDIUM**

Task 9.6 "Subgraph Extraction" says create `src/true_vkg/kg/subgraph.py` but that file ALREADY EXISTS (23KB). Need to:
- Clarify if this is extension or replacement
- Document what's already there
- Define how PPR integrates with existing code

---

### 5. Token Counting Dependency Not Installed
**Severity: MEDIUM**

Dependencies list `tiktoken >= 0.5` but:
- Not in pyproject.toml
- Assumes OpenAI tokenizer for all LLM providers
- Different providers have different token counts

---

### 6. Context Modes vs Context Policy - Confusion
**Severity: HIGH**

Task 9.4 defines "Context Modes" (full/balanced/minimal)
Task 9.7 defines "Context Policy" (strict/standard/relaxed)

These are DIFFERENT concepts with OVERLAPPING names:
- Modes = compression level
- Policy = security filtering

But CLI examples mix them:
- `--context balanced` (mode)
- `--context-policy strict` (policy)

User will be confused. Need unified approach or clearer naming.

---

### 7. 70% Token Reduction Target is Unrealistic
**Severity: MEDIUM**

Success metric says "Token Reduction: 70% target, 60% minimum" for balanced mode.

But the sample output format in Task 9.3 is VERBOSE:
```
ENTRY: withdraw(uint256)
PATH 1: withdraw -> CALLS_EXTERNAL -> target.call{value}
        -> WRITES_STATE -> balances[msg.sender]
RISK: state_write_after_external_call = true
GUARDS: none
RELATED: deposit() [READS balances]
```

This is NOT 70% smaller than JSON - it's about the same or larger.

---

### 8. No Integration with Existing LLM Module
**Severity: HIGH**

Phase 9 creates `src/true_vkg/llm/context.py` but `src/true_vkg/llm/` already has:
- compressor.py (does context compression already!)
- optimizer.py (does optimization already!)
- slicer.py (does slicing already!)

Where does PPR fit with these existing modules? No integration plan.

---

### 9. Accuracy Validation Protocol is Circular
**Severity: MEDIUM**

Task 9.5 says:
1. Run benchmark with full
2. Run benchmark with balanced
3. Compare detection rates

But "detection rate" requires knowing ground truth. Where does ground truth come from? This is the same problem as Phase 8.

---

### 10. Data Minimization (9.7) Should Be FIRST, Not Independent
**Severity: HIGH**

Task 9.7 is marked "Independent security task" but it defines the ContextPolicy that should be applied BEFORE any LLM context is sent. This should be a prerequisite for 9.4 Context Modes, not parallel.

---

## Recommendations

1. **Fix PPR Algorithm** with proper graph theory: out-degree normalization, bounded weights
2. **Replace TOON with YAML** or define actual spec
3. **Merge Context Modes + Policy** into single unified config
4. **Add Integration Task** showing how PPR fits with existing subgraph.py, compressor.py
5. **Define Query Abstraction** before Query-to-Seed mapping
6. **Move 9.7 to be 9.0** - security filtering comes first
7. **Add tiktoken to pyproject.toml** or use provider-agnostic counting
8. **Create realistic token reduction targets** (40-50% more achievable)
