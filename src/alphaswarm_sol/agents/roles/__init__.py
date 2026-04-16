"""Agent Roles Package.

This package provides role-specific agents for multi-agent verification:
- TestBuilderAgent: Generates Foundry exploit tests from bead evidence (Plan 05.2-05)
- FoundryRunner: Executes Foundry CLI commands (Plan 05.2-05)

Also exports data types used by downstream modules:
- GeneratedTest: Result of test generation
- ForgeTestResult: Result of running forge test
- ForgeBuildResult: Result of running forge build
- TestGenerationConfig: Configuration for test generation

Usage:
    from alphaswarm_sol.agents.roles import (
        # Foundry runner
        FoundryRunner,
        ForgeTestResult,
        ForgeBuildResult,
        # Test builder
        TestBuilderAgent,
        TestGenerationConfig,
        GeneratedTest,
    )

    # Run Foundry commands
    runner = FoundryRunner(project_path)
    build_result = runner.build()

    # Generate test from bead
    agent = TestBuilderAgent(runtime, config)
    test = await agent.generate_test(bead)
"""

from .foundry import (
    ForgeTestResult,
    ForgeBuildResult,
    FoundryRunner,
)

from .test_builder import (
    TestGenerationConfig,
    GeneratedTest,
    TestBuilderAgent,
)


__all__ = [
    # Foundry
    "ForgeTestResult",
    "ForgeBuildResult",
    "FoundryRunner",
    # Test Builder
    "TestGenerationConfig",
    "GeneratedTest",
    "TestBuilderAgent",
]
