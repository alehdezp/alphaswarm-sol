"""
Exploit Variant Generator

Generates diverse variants of vulnerability patterns for comprehensive testing.
Can use LLM for creative variant generation or rule-based templates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class VariantType(Enum):
    """Types of exploit variants."""
    CLASSIC = "classic"           # Standard pattern
    CROSS_FUNCTION = "cross_function"  # Vulnerability spans functions
    INDIRECT = "indirect"         # Through helper/internal calls
    EDGE_CASE = "edge_case"       # Unusual but valid pattern
    OBFUSCATED = "obfuscated"     # Intentionally hidden


@dataclass
class ExploitVariant:
    """A variant of a vulnerability exploit."""
    variant_id: str
    vuln_type: str
    variant_type: VariantType
    code: str
    description: str
    difficulty: str  # easy, medium, hard (for pattern to detect)

    # Expected detection
    should_detect: bool = True
    detection_hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "vuln_type": self.vuln_type,
            "variant_type": self.variant_type.value,
            "description": self.description,
            "difficulty": self.difficulty,
            "should_detect": self.should_detect,
        }


class VariantGenerator:
    """
    Generates diverse vulnerability variants for testing.

    Can use templates (fast, deterministic) or LLM (creative, varied).
    """

    # Template-based variants for common vulnerabilities
    REENTRANCY_VARIANTS = [
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "easy",
            "description": "Classic DAO-style reentrancy via fallback",
            "template": '''
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
    balances[msg.sender] -= amount;
}
''',
        },
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "easy",
            "description": "Reentrancy via receive()",
            "template": '''
function withdrawAll() external {
    uint256 bal = userBalances[msg.sender];
    require(bal > 0);
    payable(msg.sender).transfer(bal);
    userBalances[msg.sender] = 0;
}
''',
        },
        {
            "variant_type": VariantType.CROSS_FUNCTION,
            "difficulty": "medium",
            "description": "Cross-function reentrancy",
            "template": '''
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
    _updateBalance(msg.sender, amount);
}

function _updateBalance(address user, uint256 amount) internal {
    balances[user] -= amount;
}
''',
        },
        {
            "variant_type": VariantType.INDIRECT,
            "difficulty": "hard",
            "description": "Reentrancy through callback token",
            "template": '''
function deposit(IERC777 token, uint256 amount) external {
    token.transferFrom(msg.sender, address(this), amount);
    // ERC777 tokensReceived callback can reenter
    deposits[msg.sender] += amount;
}
''',
        },
        {
            "variant_type": VariantType.EDGE_CASE,
            "difficulty": "hard",
            "description": "Read-only reentrancy",
            "template": '''
function getPrice() public view returns (uint256) {
    return totalValue / totalShares;  // Can be manipulated mid-tx
}

function withdraw(uint256 shares) external {
    uint256 value = shares * getPrice();
    totalShares -= shares;
    (bool success,) = msg.sender.call{value: value}("");
    require(success);
    totalValue -= value;
}
''',
        },
    ]

    ACCESS_CONTROL_VARIANTS = [
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "easy",
            "description": "Missing access control on admin function",
            "template": '''
function setAdmin(address newAdmin) external {
    admin = newAdmin;  // No onlyOwner modifier!
}
''',
        },
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "easy",
            "description": "Missing access control on withdrawal",
            "template": '''
function emergencyWithdraw() external {
    // Should require onlyOwner
    payable(msg.sender).transfer(address(this).balance);
}
''',
        },
        {
            "variant_type": VariantType.INDIRECT,
            "difficulty": "medium",
            "description": "Bypassing access control via initializer",
            "template": '''
function initialize(address _owner) external {
    // Missing initializer guard - can be called multiple times
    owner = _owner;
}
''',
        },
        {
            "variant_type": VariantType.EDGE_CASE,
            "difficulty": "hard",
            "description": "tx.origin used for authentication",
            "template": '''
function transferOwnership(address newOwner) external {
    require(tx.origin == owner);  // Should use msg.sender
    owner = newOwner;
}
''',
        },
    ]

    ORACLE_VARIANTS = [
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "easy",
            "description": "Missing staleness check on oracle",
            "template": '''
function getPrice(address token) external view returns (uint256) {
    (, int256 answer, , , ) = priceFeed.latestRoundData();
    return uint256(answer);  // No staleness check!
}
''',
        },
        {
            "variant_type": VariantType.CLASSIC,
            "difficulty": "medium",
            "description": "Missing L2 sequencer uptime check",
            "template": '''
function getPriceL2(address token) external view returns (uint256) {
    // Should check sequencer uptime first
    (, int256 answer, , uint256 updatedAt, ) = priceFeed.latestRoundData();
    require(block.timestamp - updatedAt < 1 hours);
    return uint256(answer);
}
''',
        },
    ]

    # All variant templates by vulnerability type
    VARIANT_TEMPLATES = {
        "reentrancy": REENTRANCY_VARIANTS,
        "access_control": ACCESS_CONTROL_VARIANTS,
        "oracle": ORACLE_VARIANTS,
    }

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize generator.

        Args:
            llm_client: Optional LLM client for creative variant generation
        """
        self.llm = llm_client

    def generate_variants(
        self,
        vuln_type: str,
        num_variants: int = 5,
        use_llm: bool = False,
    ) -> List[ExploitVariant]:
        """
        Generate variants for a vulnerability type.

        Args:
            vuln_type: Type of vulnerability (reentrancy, access_control, etc.)
            num_variants: Number of variants to generate
            use_llm: Whether to use LLM for additional variants

        Returns:
            List of ExploitVariant objects
        """
        variants = []

        # Get template variants
        templates = self.VARIANT_TEMPLATES.get(vuln_type, [])

        for i, template in enumerate(templates[:num_variants]):
            variant = ExploitVariant(
                variant_id=f"{vuln_type}_{template['variant_type'].value}_{i+1}",
                vuln_type=vuln_type,
                variant_type=template["variant_type"],
                code=template["template"].strip(),
                description=template["description"],
                difficulty=template["difficulty"],
                should_detect=True,
            )
            variants.append(variant)

        # Generate additional variants with LLM if needed
        if use_llm and self.llm and len(variants) < num_variants:
            llm_variants = self._generate_llm_variants(
                vuln_type,
                num_variants - len(variants),
            )
            variants.extend(llm_variants)

        return variants[:num_variants]

    def _generate_llm_variants(
        self,
        vuln_type: str,
        num_variants: int,
    ) -> List[ExploitVariant]:
        """Generate variants using LLM."""
        if not self.llm:
            return []

        prompt = f"""Generate {num_variants} unique Solidity code snippets that demonstrate {vuln_type} vulnerabilities.

Requirements:
- Each variant should use DIFFERENT coding patterns
- Include edge cases and unusual implementations
- Vary function names, variable names, control flow
- All should be VULNERABLE to {vuln_type}
- Include brief description of why each is vulnerable

Format each as:
```solidity
// Variant N: [description]
[code]
```
"""

        try:
            response = self.llm.generate(prompt, temperature=0.9)
            return self._parse_llm_variants(response, vuln_type)
        except Exception as e:
            logger.warning(f"LLM variant generation failed: {e}")
            return []

    def _parse_llm_variants(self, response: str, vuln_type: str) -> List[ExploitVariant]:
        """Parse LLM response into variants."""
        variants = []

        # Extract code blocks
        pattern = r'```solidity\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)

        for i, code in enumerate(matches):
            # Extract description from comment
            desc_match = re.search(r'//\s*Variant\s*\d+:\s*(.+)', code)
            description = desc_match.group(1) if desc_match else f"LLM-generated variant {i+1}"

            variant = ExploitVariant(
                variant_id=f"{vuln_type}_llm_{i+1}",
                vuln_type=vuln_type,
                variant_type=VariantType.CLASSIC,
                code=code.strip(),
                description=description,
                difficulty="medium",
                should_detect=True,
            )
            variants.append(variant)

        return variants

    def generate_safe_variants(
        self,
        vuln_type: str,
        num_variants: int = 3,
    ) -> List[ExploitVariant]:
        """
        Generate SAFE variants (should NOT be detected).

        These are false-positive test cases.
        """
        safe_templates = {
            "reentrancy": [
                {
                    "description": "Safe: CEI pattern followed",
                    "code": '''
function withdraw(uint256 amount) external nonReentrant {
    require(balances[msg.sender] >= amount);
    balances[msg.sender] -= amount;  // State update FIRST
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
}
''',
                },
                {
                    "description": "Safe: Reentrancy guard present",
                    "code": '''
function withdraw(uint256 amount) external nonReentrant {
    require(balances[msg.sender] >= amount);
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
    balances[msg.sender] -= amount;
}
''',
                },
            ],
            "access_control": [
                {
                    "description": "Safe: onlyOwner modifier present",
                    "code": '''
function setAdmin(address newAdmin) external onlyOwner {
    admin = newAdmin;
}
''',
                },
                {
                    "description": "Safe: Role-based access control",
                    "code": '''
function emergencyWithdraw() external onlyRole(ADMIN_ROLE) {
    payable(msg.sender).transfer(address(this).balance);
}
''',
                },
            ],
            "oracle": [
                {
                    "description": "Safe: Staleness check present",
                    "code": '''
function getPrice(address token) external view returns (uint256) {
    (, int256 answer, , uint256 updatedAt, ) = priceFeed.latestRoundData();
    require(block.timestamp - updatedAt < 1 hours, "Stale price");
    return uint256(answer);
}
''',
                },
            ],
        }

        templates = safe_templates.get(vuln_type, [])
        variants = []

        for i, template in enumerate(templates[:num_variants]):
            variant = ExploitVariant(
                variant_id=f"{vuln_type}_safe_{i+1}",
                vuln_type=vuln_type,
                variant_type=VariantType.CLASSIC,
                code=template["code"].strip(),
                description=template["description"],
                difficulty="easy",
                should_detect=False,  # Should NOT be detected
            )
            variants.append(variant)

        return variants

    def get_available_vuln_types(self) -> List[str]:
        """Get list of vulnerability types with templates."""
        return list(self.VARIANT_TEMPLATES.keys())

    def get_variant_stats(self, vuln_type: str) -> Dict[str, int]:
        """Get statistics about available variants."""
        templates = self.VARIANT_TEMPLATES.get(vuln_type, [])

        stats = {
            "total": len(templates),
            "by_difficulty": {},
            "by_type": {},
        }

        for t in templates:
            diff = t["difficulty"]
            vtype = t["variant_type"].value

            stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1
            stats["by_type"][vtype] = stats["by_type"].get(vtype, 0) + 1

        return stats
