"""
Intent Annotator

LLM-powered annotator that analyzes Solidity functions and infers their
business purpose, trust assumptions, and expected invariants.

This is THE CORE COMPONENT that bridges code analysis to semantic understanding.
"""

import json
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from .schema import (
    BusinessPurpose,
    TrustLevel,
    TrustAssumption,
    InferredInvariant,
    FunctionIntent,
)


class IntentCache:
    """
    Cache for intent annotations to avoid redundant LLM calls.

    Cache key is hash of function signature + code + properties.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files. None for in-memory only.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.memory_cache: Dict[str, FunctionIntent] = {}

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, cache_key: str) -> Optional[FunctionIntent]:
        """
        Get cached intent.

        Args:
            cache_key: Cache key

        Returns:
            Cached intent or None
        """
        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # Check disk cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    intent = FunctionIntent.from_dict(data)
                    # Populate memory cache
                    self.memory_cache[cache_key] = intent
                    return intent
                except Exception:
                    # Invalid cache file, ignore
                    pass

        return None

    def set(self, cache_key: str, intent: FunctionIntent) -> None:
        """
        Cache intent.

        Args:
            cache_key: Cache key
            intent: Intent to cache
        """
        # Store in memory
        self.memory_cache[cache_key] = intent

        # Store on disk
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            try:
                with open(cache_file, "w") as f:
                    json.dump(intent.to_dict(), f, indent=2)
            except Exception:
                # Failed to write cache, not critical
                pass

    def clear(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()

        if self.cache_dir:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()


class IntentAnnotator:
    """
    LLM-powered intent annotator for Solidity functions.

    Infers business purpose, trust assumptions, and expected invariants
    by analyzing function code, VKG properties, and domain knowledge.
    """

    def __init__(
        self,
        llm_client,  # Type: LLMClient from P0-T0
        domain_kg,  # Type: DomainKnowledgeGraph from P0-T1
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize annotator.

        Args:
            llm_client: LLM client for inference
            domain_kg: Domain knowledge graph for context
            cache_dir: Optional cache directory
        """
        self.llm = llm_client
        self.domain_kg = domain_kg
        self.cache = IntentCache(cache_dir) if cache_dir else None

    def annotate_function(
        self,
        fn_node: Any,  # Type: Node from VKG
        code_context: str,
        contract_context: Optional[str] = None,
    ) -> FunctionIntent:
        """
        Annotate a single function with intent.

        Args:
            fn_node: Function node from VKG
            code_context: Solidity source code for function
            contract_context: Optional broader contract context

        Returns:
            FunctionIntent with inferred business purpose and security context
        """
        # Check cache
        cache_key = self._compute_cache_key(fn_node, code_context)
        if self.cache and (cached := self.cache.get(cache_key)):
            return cached

        # Build context from VKG properties and domain knowledge
        context = self._build_context(fn_node, code_context, contract_context)

        # Build optimized prompt
        prompt = self._build_prompt(fn_node, context)

        # Call LLM
        response = self.llm.analyze(
            prompt=prompt,
            response_format="json",
            temperature=0.3,  # Lower for more consistent outputs
        )

        # Parse response into FunctionIntent
        intent = self._parse_response(response, fn_node)

        # Cache result
        if self.cache:
            self.cache.set(cache_key, intent)

        return intent

    def annotate_batch(
        self,
        functions: List[Tuple[Any, str, Optional[str]]],
    ) -> List[FunctionIntent]:
        """
        Annotate multiple functions efficiently using batching.

        Args:
            functions: List of (fn_node, code_context, contract_context) tuples

        Returns:
            List of FunctionIntent objects
        """
        # For now, process sequentially
        # Future: batch prompts for token efficiency
        results = []
        for fn_node, code_context, contract_context in functions:
            intent = self.annotate_function(fn_node, code_context, contract_context)
            results.append(intent)
        return results

    def _compute_cache_key(self, fn_node: Any, code_context: str) -> str:
        """
        Compute stable cache key from function signature and code.

        Args:
            fn_node: Function node
            code_context: Source code

        Returns:
            Hash string
        """
        # Combine function name, visibility, modifiers, and code
        key_components = [
            fn_node.label,
            str(fn_node.properties.get("visibility", "")),
            str(sorted(fn_node.properties.get("modifiers", []))),
            code_context.strip(),
        ]

        key_string = "|".join(key_components)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def _build_context(
        self,
        fn_node: Any,
        code_context: str,
        contract_context: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build rich context for LLM analysis.

        Args:
            fn_node: Function node with VKG properties
            code_context: Source code
            contract_context: Optional contract context

        Returns:
            Context dict with code, specs, operations
        """
        context = {
            "code": code_context.strip(),
            "function_name": fn_node.label,
            "visibility": fn_node.properties.get("visibility", "unknown"),
            "modifiers": fn_node.properties.get("modifiers", []),
            "semantic_ops": fn_node.properties.get("semantic_ops", []),
            "behavioral_signature": fn_node.properties.get("behavioral_signature", ""),
        }

        # Add contract context if provided
        if contract_context:
            context["contract_context"] = contract_context.strip()

        # Add relevant specifications from Domain KG
        spec_hints = self._get_spec_hints(fn_node)
        if spec_hints:
            context["spec_hints"] = spec_hints

        return context

    def _get_spec_hints(self, fn_node: Any) -> str:
        """
        Get relevant specification hints from Domain KG.

        Args:
            fn_node: Function node

        Returns:
            Formatted specification hints
        """
        hints = []

        # Check semantic operations for spec matches
        semantic_ops = fn_node.properties.get("semantic_ops", [])

        # Token transfer operations → ERC-20/721
        if "TRANSFERS_VALUE_OUT" in semantic_ops or "CALLS_ERC20_TRANSFER" in semantic_ops:
            hints.append("- Possibly implements ERC-20 transfer or ERC-721 transfer")

        # Balance operations → ERC-4626 vault
        if "READS_USER_BALANCE" in semantic_ops and "WRITES_USER_BALANCE" in semantic_ops:
            hints.append("- Possibly implements ERC-4626 vault withdrawal/deposit")

        # Oracle operations
        if "READS_ORACLE" in semantic_ops:
            hints.append("- Uses oracle price feeds (check for staleness/freshness)")

        # Access control operations
        if "CHECKS_PERMISSION" in semantic_ops:
            hints.append("- Implements access control (check authorization logic)")

        # Reentrancy patterns
        sig = fn_node.properties.get("behavioral_signature", "")
        if "X:out" in sig and "W:bal" in sig:
            if sig.index("X:out") < sig.index("W:bal"):
                hints.append("- WARNING: External call before state write (reentrancy risk)")

        return "\n".join(hints) if hints else "No specific specifications identified"

    def _build_prompt(self, fn_node: Any, context: Dict[str, Any]) -> str:
        """
        Build optimized prompt for intent extraction.

        Args:
            fn_node: Function node
            context: Rich context dict

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this Solidity function to understand its BUSINESS PURPOSE and SECURITY CONTEXT.

## Function Information
- Name: {context['function_name']}
- Visibility: {context['visibility']}
- Modifiers: {context['modifiers']}
- Semantic Operations: {context['semantic_ops']}
- Behavioral Signature: {context['behavioral_signature']}

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
   Choose from: withdrawal, deposit, transfer, claim_rewards, mint, burn,
   swap, add_liquidity, remove_liquidity,
   vote, propose, execute_proposal, delegate,
   set_parameter, pause, unpause, upgrade, transfer_ownership, grant_role, revoke_role,
   borrow, repay, liquidate, accrue_interest,
   update_price, sync_reserves,
   stake, unstake,
   flash_loan, flash_loan_callback,
   view_only, callback, internal_helper, constructor, fallback,
   unknown, complex_multifunction

2. **Trust Level**: Who should be able to call this safely?
   Choose from: permissionless, depositor_only, role_restricted, owner_only,
   governance_only, internal_only, trusted_contracts

3. **Trust Assumptions**: What security assumptions does this code make?
   - What external state must be true?
   - What caller properties are assumed?
   - What timing constraints exist?
   Mark critical assumptions (ones that, if violated, lead to exploits).

4. **Inferred Invariants**: What should be true after this function executes?
   - What balance changes are expected?
   - What state transitions should occur?
   - What properties should be preserved?

5. **Risk Notes**: Any security concerns based on the code structure?
   - Reentrancy risks?
   - Access control issues?
   - Oracle freshness?
   - MEV vulnerabilities?

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
            "critical": <true|false>,
            "validation_check": "<optional code that validates this>"
        }}
    ],
    "inferred_invariants": [
        {{
            "id": "<unique_id>",
            "description": "<what should hold after execution>",
            "scope": "<function|transaction|global|temporal>",
            "formal": "<optional formal specification>",
            "related_spec": "<optional spec ID from Domain KG>"
        }}
    ],
    "likely_specs": ["<spec_id1>", "<spec_id2>"],
    "spec_confidence": {{"<spec_id1>": <0.0-1.0>, "<spec_id2>": <0.0-1.0>}},
    "risk_notes": ["<risk1>", "<risk2>"],
    "complexity_score": <0.0-1.0>
}}

IMPORTANT:
- Be precise and specific in your analysis
- Use the semantic operations and behavioral signature as strong signals
- Flag all potential security risks
- Confidence should reflect certainty (0.9+ only for obvious cases)
"""

    def _parse_response(self, response: str, fn_node: Any) -> FunctionIntent:
        """
        Parse LLM JSON response into FunctionIntent.

        Args:
            response: LLM response string
            fn_node: Function node for fallback

        Returns:
            FunctionIntent object
        """
        try:
            # Parse JSON response
            data = json.loads(response)

            # Add metadata
            data["inferred_at"] = datetime.now().isoformat()
            data["raw_llm_response"] = response

            # Create FunctionIntent from dict
            intent = FunctionIntent.from_dict(data)

            return intent

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback to unknown intent if parsing fails
            return FunctionIntent(
                business_purpose=BusinessPurpose.UNKNOWN,
                purpose_confidence=0.0,
                purpose_reasoning=f"Failed to parse LLM response: {str(e)}",
                expected_trust_level=TrustLevel.PERMISSIONLESS,
                raw_llm_response=response,
                inferred_at=datetime.now().isoformat(),
                complexity_score=0.5,
            )
