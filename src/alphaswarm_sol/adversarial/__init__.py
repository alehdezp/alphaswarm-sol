"""
Novel Solution 3: Adversarial Test Case Generation

AI-powered exploit compiler that generates test cases to stress-test
vulnerability patterns through:
- Mutation testing (introduce vulnerabilities into safe code)
- Metamorphic testing (renaming shouldn't affect detection)
- Exploit variant generation (LLM-based diverse exploits)
"""

from alphaswarm_sol.adversarial.mutation_testing import (
    MutationTestResult,
    ContractMutator,
    MutationOperator,
    RemoveRequireOperator,
    SwapStatementsOperator,
    ChangeVisibilityOperator,
    RemoveGuardOperator,
    AddExternalCallOperator,
)

from alphaswarm_sol.adversarial.metamorphic_testing import (
    MetamorphicTestResult,
    MetamorphicTester,
    IdentifierRenamer,
)

from alphaswarm_sol.adversarial.variant_generator import (
    ExploitVariant,
    VariantGenerator,
)

__all__ = [
    # Mutation testing
    "MutationTestResult",
    "ContractMutator",
    "MutationOperator",
    "RemoveRequireOperator",
    "SwapStatementsOperator",
    "ChangeVisibilityOperator",
    "RemoveGuardOperator",
    "AddExternalCallOperator",
    # Metamorphic testing
    "MetamorphicTestResult",
    "MetamorphicTester",
    "IdentifierRenamer",
    # Variant generation
    "ExploitVariant",
    "VariantGenerator",
]
