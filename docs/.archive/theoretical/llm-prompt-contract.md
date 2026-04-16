# LLM Prompt Contract Specification

**Version:** 1.0.0
**Status:** DRAFT
**Source:** Critique lines 462-464 (noninteractive integration), 481-485 (safety)

This document defines the formal contract between BSKG and LLM providers for vulnerability analysis.

---

## 1. Purpose

VKG's Tier B analysis uses LLMs to:
1. Verify Tier A findings (reduce false positives)
2. Identify business logic vulnerabilities
3. Generate test scaffolds
4. Provide human-readable explanations

This contract ensures:
- **Reproducibility:** Same input → same analysis flow (though LLM output may vary)
- **Safety:** No prompt injection, no code execution
- **Provider Agnosticism:** Works with any LLM provider

---

## 2. Input Schema

Every LLM prompt MUST follow this structure:

```json
{
  "$schema": "https://vkg.dev/schemas/llm-prompt.schema.json",
  "schema_version": "1.0.0",
  "prompt_type": "finding_verification",
  "session_id": "uuid-here",

  "system_context": {
    "role": "security_auditor",
    "constraints": [
      "Only analyze provided code snippets",
      "Never execute or suggest execution of code",
      "Report uncertainties explicitly",
      "Output structured JSON only"
    ],
    "output_format": "structured_json"
  },

  "evidence": {
    "finding": {
      "id": "VKG-001",
      "pattern_id": "reentrancy-classic",
      "tier": "tier_a",
      "confidence": 0.85,
      "behavioral_signature": "R:bal->X:out->W:bal"
    },
    "code_snippets": [
      {
        "file": "Vault.sol",
        "lines": [45, 52],
        "content": "function withdraw(uint256 amount) public { ... }",
        "relevance": "vulnerable_function"
      }
    ],
    "graph_context": {
      "callers": ["userWithdraw", "batchWithdraw"],
      "callees": ["_transfer", "balanceOf"],
      "state_reads": ["balances[msg.sender]"],
      "state_writes": ["balances[msg.sender]"],
      "external_calls": ["payable(msg.sender).call{value: amount}"]
    }
  },

  "task": {
    "action": "verify_finding",
    "question": "Is this reentrancy vulnerability valid? Explain your reasoning.",
    "expected_output": {
      "verdict": "enum:confirmed|rejected|uncertain",
      "confidence": "float:0.0-1.0",
      "reasoning": "string",
      "evidence_refs": "array:string"
    }
  }
}
```

---

## 3. Output Schema

LLM responses MUST conform to this structure:

```json
{
  "$schema": "https://vkg.dev/schemas/llm-response.schema.json",
  "schema_version": "1.0.0",
  "prompt_id": "uuid-from-input",
  "model_id": "claude-3.5-sonnet",
  "response_type": "finding_verification",

  "result": {
    "verdict": "confirmed",
    "confidence": 0.92,
    "reasoning": "The withdraw() function calls external address before updating balance, enabling reentrancy.",
    "evidence_refs": ["EVD-001", "EVD-002"]
  },

  "metadata": {
    "tokens_used": 1234,
    "latency_ms": 450,
    "model_version": "2024-01-01"
  }
}
```

---

## 4. Prompt Types

### 4.1 Finding Verification (`finding_verification`)

**Purpose:** Confirm or reject a Tier A finding.

**Input:**
- Finding details (pattern, confidence, signature)
- Minimal code snippet (per data minimization policy)
- Graph context (callers, callees, state access)

**Expected Output:**
- Verdict: confirmed | rejected | uncertain
- Confidence: 0.0 - 1.0
- Reasoning: Human-readable explanation
- Evidence refs: Links to specific code

---

### 4.2 Business Logic Analysis (`business_logic`)

**Purpose:** Identify vulnerabilities that patterns can't catch.

**Input:**
- Function summary
- Intent annotation (if available)
- Related functions

**Expected Output:**
- Potential issues list
- Severity per issue
- Suggested verification steps

---

### 4.3 Test Scaffold Generation (`scaffold_generation`)

**Purpose:** Generate test code to verify finding.

**Input:**
- Finding with evidence
- Test framework (Foundry, Hardhat)
- Contract interface

**Expected Output:**
- Test code (string)
- Setup requirements
- Expected result

**SAFETY:**
- Generated code is for REVIEW only
- Execution requires explicit user approval
- See scaffold sandbox security (Phase 1.C.3)

---

### 4.4 Explanation Generation (`explanation`)

**Purpose:** Generate human-readable finding explanation.

**Input:**
- Finding details
- Code context
- Target audience (auditor | developer | executive)

**Expected Output:**
- Summary paragraph
- Technical details (for auditor/developer)
- Impact description
- Recommended fix

---

## 5. Safety Invariants

### 5.1 No Code Execution

```python
# FORBIDDEN in prompts
eval(llm_response)
exec(llm_response)
subprocess.run(llm_response)

# ALLOWED
display(llm_response)
validate_json(llm_response)
```

### 5.2 No Prompt Injection

**Protection Layers:**

1. **Input Sanitization:**
   ```python
   def sanitize_code_for_prompt(code: str) -> str:
       """Remove prompt-injection patterns from code."""
       # Remove obvious injection patterns
       patterns = [
           r"ignore previous instructions",
           r"you are now",
           r"system:",
           r"<\|.*?\|>",  # Control tokens
       ]
       for pattern in patterns:
           code = re.sub(pattern, "[REDACTED]", code, flags=re.I)
       return code
   ```

2. **Structured Prompts Only:**
   - Code is always in designated `code_snippets` field
   - Never interpolate user strings into system prompts
   - Use JSON structure, not string templates

3. **Output Validation:**
   ```python
   def validate_llm_response(response: dict) -> bool:
       """Validate LLM response structure."""
       if not jsonschema.validate(response, LLM_RESPONSE_SCHEMA):
           return False

       # Check for hallucinated file refs
       for ref in response.get("evidence_refs", []):
           if not ref.startswith("EVD-"):
               return False

       return True
   ```

### 5.3 Audit Trail

Every LLM interaction MUST be logged:

```python
@dataclass
class LLMInteractionLog:
    timestamp: datetime
    session_id: str
    prompt_type: str
    prompt_hash: str  # SHA256 of prompt JSON
    response_hash: str  # SHA256 of response JSON
    tokens_in: int
    tokens_out: int
    latency_ms: int
    model_id: str
    policy_applied: str  # strict | standard | relaxed
    bytes_sent: int
    bytes_filtered: int  # What was NOT sent due to policy
```

---

## 6. Provider Agnosticism

### 6.1 Supported Providers

| Provider | Model ID Pattern | Status |
|----------|-----------------|--------|
| Anthropic | claude-* | Supported |
| OpenAI | gpt-* | Supported |
| Google | gemini-* | Supported |
| Groq | llama-*, mixtral-* | Supported |
| DeepSeek | deepseek-* | Supported |
| OpenRouter | openrouter/* | Supported |

### 6.2 Provider Interface

```python
# src/true_vkg/llm/provider.py

class LLMProvider(Protocol):
    """Provider-agnostic LLM interface."""

    def chat(self, messages: List[Message], config: ChatConfig) -> Response:
        """Send chat completion request."""
        ...

    def validate_connection(self) -> bool:
        """Check provider is reachable."""
        ...

    @property
    def model_id(self) -> str:
        """Return canonical model identifier."""
        ...

    @property
    def capabilities(self) -> Set[str]:
        """Return supported capabilities."""
        # e.g., {"json_mode", "function_calling", "vision"}
        ...
```

### 6.3 SDK Compatibility

VKG prompts are compatible with:
- Anthropic Claude SDK
- OpenAI Chat Completions API
- Google Generative AI SDK
- Any OpenAI-compatible endpoint

---

## 7. Noninteractive / CI Usage

For Codex, batch jobs, and CI pipelines:

```python
# src/true_vkg/llm/noninteractive.py

class NoninteractiveRunner:
    """Run LLM analysis without user interaction."""

    def __init__(self, config: RunnerConfig):
        self.provider = create_provider(config.provider)
        self.timeout = config.timeout_seconds
        self.max_retries = config.max_retries

    def analyze_batch(self, findings: List[Finding]) -> List[Result]:
        """Analyze multiple findings in batch."""
        results = []

        for finding in findings:
            prompt = self.generate_prompt(finding)

            try:
                response = self.provider.chat(
                    [prompt],
                    ChatConfig(
                        temperature=0.0,  # Deterministic
                        max_tokens=1000,
                        timeout=self.timeout
                    )
                )
                results.append(self.parse_response(response))

            except TimeoutError:
                results.append(Result(
                    finding_id=finding.id,
                    status="timeout",
                    error="LLM response timed out"
                ))

            except RateLimitError:
                # Exponential backoff
                time.sleep(2 ** self.retry_count)
                self.retry_count += 1

        return results
```

**CI Integration:**
```yaml
# .github/workflows/tier-b-analysis.yml
jobs:
  tier-b:
    runs-on: ubuntu-latest
    env:
      VKG_LLM_PROVIDER: anthropic
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    steps:
      - name: Run Tier B Analysis
        run: |
          vkg analyze --tier b --noninteractive --timeout 30
```

---

## 8. Validation Requirements

### 8.1 Schema Validation

Every prompt and response MUST pass JSON Schema validation:

```bash
# Validate prompt
jsonschema validate prompt.json --schema schemas/llm-prompt.schema.json

# Validate response
jsonschema validate response.json --schema schemas/llm-response.schema.json
```

### 8.2 Round-Trip Testing

```python
def test_prompt_response_roundtrip():
    """Test that prompts generate valid responses."""
    prompt = generate_prompt(sample_finding)

    # Prompt is valid
    assert validate_prompt(prompt)

    # Send to mock provider
    response = mock_provider.chat([prompt])

    # Response is valid
    assert validate_response(response)

    # Response references valid evidence
    for ref in response["result"]["evidence_refs"]:
        assert ref in prompt["evidence"]["code_snippets"]
```

### 8.3 Determinism Testing

```python
def test_prompt_determinism():
    """Same finding generates same prompt (except session_id)."""
    p1 = generate_prompt(finding, session_id="a")
    p2 = generate_prompt(finding, session_id="b")

    # Everything except session_id should match
    p1["session_id"] = p2["session_id"] = "test"
    assert p1 == p2
```

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-07 | Initial specification |

---

*LLM Prompt Contract | Version 1.0.0 | 2026-01-07*
*Source: Critique integration requirements*
