"""
Prompt Templates

Level-specific templates for VKG 3.5 LLM analysis.
Progressive detail: Level 1 (quick) → Level 2 (focused) → Level 3 (deep)
"""

from typing import Dict

# Level-specific prompt templates
TEMPLATES: Dict[int, str] = {
    1: """QUICK SECURITY SCAN

Function: {compressed_context}

Question: Does this function have any obvious security issues?

Reply with:
- SAFE: No issues found
- SUSPICIOUS: [one-line reason] (escalate to Level 2)
- VULNERABLE: [one-line reason] (escalate to Level 3)

Answer:""",

    2: """FOCUSED SECURITY ANALYSIS

Function: {compressed_context}

Pattern Matches: {patterns}
Spec Requirements: {specs}

Analyze:
1. Are the pattern matches true positives?
2. Are spec requirements satisfied?
3. Is there a plausible attack vector?

Reply as JSON:
{{
  "verdict": "safe|suspicious|vulnerable",
  "patterns_confirmed": ["pattern_id", ...],
  "patterns_rejected": [{{"id": "...", "reason": "..."}}],
  "attack_vector": "description or null",
  "confidence": 0.0-1.0
}}

Analysis:""",

    3: """DEEP ADVERSARIAL SECURITY ANALYSIS

Function: {compressed_context}

Source Code:
```solidity
{source_code}
```

Related Functions:
{related_functions}

Cross-Graph Context:
- Specifications: {specs}
- Known Vulnerabilities: {known_vulns}
- Attack Patterns: {attack_patterns}

You are a security auditor. Analyze this function thoroughly.

Consider:
1. Reentrancy risks (CEI pattern?)
2. Access control (who can call this?)
3. Input validation (untrusted inputs?)
4. State consistency (invariants maintained?)
5. External interactions (can they be manipulated?)

Reply as JSON:
{{
  "verdict": "safe|vulnerable",
  "vulnerabilities": [
    {{
      "type": "reentrancy|access_control|...",
      "severity": "critical|high|medium|low",
      "description": "...",
      "evidence": ["line:code", ...],
      "attack_scenario": "...",
      "fix_recommendation": "..."
    }}
  ],
  "safe_patterns": ["description of safety measures"],
  "confidence": 0.0-1.0,
  "needs_human_review": true|false,
  "reasoning": "brief explanation"
}}

Analysis:"""
}

# System prompts per level
SYSTEM_PROMPTS: Dict[int, str] = {
    1: """You are a security expert performing quick triage on Solidity smart contracts.
Your goal: quickly identify obviously safe vs potentially vulnerable functions.
Be conservative: when in doubt, escalate to deeper analysis.""",

    2: """You are a security expert analyzing Solidity smart contracts.
Your goal: validate pattern matches and identify attack vectors.
Use the VKG semantic representations to assess vulnerabilities.
Focus on behavioral signatures and operation ordering.""",

    3: """You are an expert security auditor analyzing Solidity smart contracts.
Your goal: thorough adversarial analysis to find exploits.
Consider attack scenarios from pattern matches, specs, and known vulnerabilities.
Provide detailed evidence and actionable fix recommendations."""
}

# Intent annotation template (used for business context inference)
INTENT_TEMPLATE = """BUSINESS INTENT INFERENCE

Function: {compressed_context}

What is the business purpose of this function?

Choose from taxonomy:
- transfer: Move tokens/value between accounts
- mint: Create new tokens
- burn: Destroy tokens
- swap: Exchange tokens
- stake: Lock tokens for rewards
- deposit: Accept tokens into protocol
- withdraw: Release tokens from protocol
- claim: Collect earned rewards
- vote: Governance action
- delegate: Transfer voting power
- configure: Admin configuration
- upgrade: Contract upgrade
- emergency: Emergency action

Reply as JSON:
{{
  "intent": "primary_intent",
  "secondary_intents": ["..."],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Analysis:"""

# Attack construction template (adversarial agent)
ATTACK_TEMPLATE = """ATTACK VECTOR CONSTRUCTION

Function: {compressed_context}

Source Code:
```solidity
{source_code}
```

You are an attacker. Find exploits in this function.

Consider:
- Reentrancy (can you re-enter before state updates?)
- Access control (can you bypass guards?)
- Oracle manipulation (can you manipulate price feeds?)
- MEV extraction (can you frontrun/sandwich?)
- DoS (can you block legitimate users?)
- Input validation (can you provide malicious inputs?)

Reply as JSON:
{{
  "exploitable": true|false,
  "attack_vectors": [
    {{
      "type": "reentrancy|access_control|...",
      "severity": "critical|high|medium|low",
      "description": "step-by-step exploit",
      "preconditions": ["what must be true"],
      "impact": "what attacker gains",
      "proof_of_concept": "solidity code snippet"
    }}
  ],
  "confidence": 0.0-1.0
}}

Analysis:"""

# Defense argument template (adversarial agent)
DEFENSE_TEMPLATE = """DEFENSE ARGUMENT CONSTRUCTION

Function: {compressed_context}

Source Code:
```solidity
{source_code}
```

Proposed Attack: {attack_vector}

You are a defender. Find guards that prevent this exploit.

Look for:
- Modifiers (access control, reentrancy guards)
- Checks (require statements, validations)
- CEI pattern (checks-effects-interactions)
- Safe external calls (pull over push, etc.)

Reply as JSON:
{{
  "attack_prevented": true|false,
  "defenses": [
    {{
      "type": "modifier|check|pattern",
      "description": "how it prevents the attack",
      "evidence": ["line:code"],
      "effectiveness": "complete|partial|weak"
    }}
  ],
  "residual_risk": "description of remaining risk",
  "confidence": 0.0-1.0
}}

Analysis:"""

# Arbitration template (resolve agent disagreement)
ARBITRATION_TEMPLATE = """ARBITRATION

Function: {compressed_context}

Attacker Argument:
{attack_argument}

Defender Argument:
{defense_argument}

As an impartial judge, resolve this disagreement.

Reply as JSON:
{{
  "verdict": "vulnerable|safe|inconclusive",
  "winning_argument": "attacker|defender|neither",
  "reasoning": "detailed explanation",
  "final_severity": "critical|high|medium|low|none",
  "confidence": 0.0-1.0,
  "recommendation": "accept|reject|escalate_to_human"
}}

Analysis:"""


def get_template(level: int) -> str:
    """
    Get prompt template for analysis level.

    Args:
        level: Analysis level (1, 2, or 3)

    Returns:
        Template string
    """
    return TEMPLATES.get(level, TEMPLATES[2])


def get_system_prompt(level: int) -> str:
    """
    Get system prompt for analysis level.

    Args:
        level: Analysis level (1, 2, or 3)

    Returns:
        System prompt string
    """
    return SYSTEM_PROMPTS.get(level, SYSTEM_PROMPTS[2])


def format_pattern_list(patterns: list) -> str:
    """
    Format pattern matches for template insertion.

    Args:
        patterns: List of pattern match dicts

    Returns:
        Formatted string
    """
    if not patterns:
        return "none"

    strs = []
    for p in patterns[:5]:  # Limit to top 5
        pid = p.get("id", "unknown")
        severity = p.get("severity", "?")
        score = p.get("score", 0.0)
        strs.append(f"{pid} ({severity}, {score:.2f})")

    return ", ".join(strs)


def format_spec_list(specs: list) -> str:
    """
    Format spec requirements for template insertion.

    Args:
        specs: List of cross-graph link dicts

    Returns:
        Formatted string
    """
    if not specs:
        return "none"

    strs = []
    for s in specs[:3]:  # Limit to top 3
        spec = s.get("spec", "unknown")
        req = s.get("requirement", "?")
        strs.append(f"{spec}: {req}")

    return ", ".join(strs)
