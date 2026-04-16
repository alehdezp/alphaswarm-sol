"""
DeFi Primitive Definitions

Defines common DeFi building blocks like AMM, lending pools,
flash loans, and vaults with their security properties.
"""

from alphaswarm_sol.knowledge.domain_kg import (
    DeFiPrimitive,
    Invariant,
)


# Automated Market Maker (AMM)
AMM_SWAP = DeFiPrimitive(
    id="amm-swap",
    name="AMM Swap",
    description="Automated market maker token swap",
    entry_functions=["swap", "swapExact", "swapTokensForTokens"],
    callback_pattern=None,
    implements_specs=["erc-20"],
    trust_assumptions=[
        "Price oracle is manipulation-resistant",
        "Pool reserves are accurate",
        "No front-running protection at protocol level",
    ],
    attack_surface=[
        "Price manipulation via large trades",
        "MEV (sandwich attacks, frontrunning)",
        "Slippage exploitation",
        "Deadline bypass",
    ],
    known_attack_patterns=[
        "sandwich-attack",
        "frontrun-swap",
        "price-manipulation",
    ],
    primitive_invariants=[
        Invariant(
            id="amm-constant-product",
            description="Product of reserves must increase or stay constant (k)",
            scope="transaction",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="amm-slippage-protection",
            description="Must have minimum output amount parameter",
            scope="function",
            must_have=[],
            must_not_have=["risk_missing_slippage_parameter"]
        ),
        Invariant(
            id="amm-deadline-check",
            description="Must have transaction deadline to prevent stale swaps",
            scope="function",
            must_have=[],
            must_not_have=["risk_missing_deadline_check"]
        ),
    ]
)


# Lending Pool
LENDING_POOL = DeFiPrimitive(
    id="lending-pool",
    name="Lending Pool",
    description="DeFi lending and borrowing protocol",
    entry_functions=["borrow", "deposit", "withdraw", "repay", "liquidate"],
    callback_pattern=None,
    implements_specs=["erc-20", "erc-4626"],
    trust_assumptions=[
        "Collateral price oracle is accurate",
        "Interest rate model is fair",
        "Liquidation incentives are sufficient",
    ],
    attack_surface=[
        "Oracle manipulation for under-collateralized loans",
        "Flash loan attacks on price feeds",
        "Interest rate manipulation",
        "Liquidation frontrunning",
        "Reentrancy in borrow/repay",
    ],
    known_attack_patterns=[
        "oracle-manipulation",
        "flash-loan-attack",
        "liquidation-frontrun",
    ],
    primitive_invariants=[
        Invariant(
            id="lending-collateral-ratio",
            description="Total collateral value must exceed total borrows",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="lending-health-factor",
            description="User health factor must be >= 1.0 after borrow",
            scope="function",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="lending-oracle-freshness",
            description="Price oracle data must be fresh",
            scope="function",
            must_have=["has_staleness_check"],
            must_not_have=[]
        ),
    ]
)


# Flash Loan
FLASH_LOAN = DeFiPrimitive(
    id="flash-loan",
    name="Flash Loan",
    description="Uncollateralized loan repaid in same transaction",
    entry_functions=["flashLoan", "flashBorrow"],
    callback_pattern="executeOperation|onFlashLoan",
    implements_specs=["erc-20"],
    trust_assumptions=[
        "Borrower contract is not malicious",
        "Callback validates return value",
        "Fee calculation is correct",
    ],
    attack_surface=[
        "Reentrancy via callback",
        "Price manipulation during loan",
        "Fee bypass",
        "Callback validation bypass",
    ],
    known_attack_patterns=[
        "flash-loan-reentrancy",
        "flash-loan-price-manipulation",
    ],
    primitive_invariants=[
        Invariant(
            id="flashloan-repayment",
            description="Borrowed amount + fee must be repaid",
            scope="transaction",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="flashloan-callback-validation",
            description="Callback must validate return value",
            scope="function",
            must_have=["has_external_calls"],
            must_not_have=[]
        ),
        Invariant(
            id="flashloan-reentrancy-guard",
            description="Must protect against reentrancy",
            scope="function",
            must_have=["has_reentrancy_guard"],
            must_not_have=["state_write_after_external_call"]
        ),
    ]
)


# Vault (Yield Aggregator)
YIELD_VAULT = DeFiPrimitive(
    id="yield-vault",
    name="Yield Vault",
    description="Yield aggregation vault (extends ERC-4626)",
    entry_functions=["deposit", "withdraw", "harvest", "compound"],
    callback_pattern=None,
    implements_specs=["erc-4626", "erc-20"],
    trust_assumptions=[
        "Strategy contracts are secure",
        "Share price calculation is accurate",
        "Emergency withdrawal works",
    ],
    attack_surface=[
        "Share price manipulation (first depositor attack)",
        "Strategy contract exploit",
        "Donation attack via direct transfers",
        "Rounding errors in share calculation",
    ],
    known_attack_patterns=[
        "erc4626-inflation-attack",
        "donation-attack",
        "strategy-exploit",
    ],
    primitive_invariants=[
        Invariant(
            id="vault-share-price-monotonic",
            description="Share price should generally increase over time",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="vault-first-deposit-protection",
            description="Must protect against first depositor inflation attack",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="vault-withdrawal-queue",
            description="Withdrawals must be processable even if strategy fails",
            scope="function",
            must_have=[],
            must_not_have=[]
        ),
    ]
)


# Staking Contract
STAKING = DeFiPrimitive(
    id="staking",
    name="Staking",
    description="Token staking with rewards",
    entry_functions=["stake", "unstake", "claim", "claimRewards"],
    callback_pattern=None,
    implements_specs=["erc-20"],
    trust_assumptions=[
        "Reward distribution is fair",
        "Staking period enforced",
        "Reward rate is sustainable",
    ],
    attack_surface=[
        "Reward calculation manipulation",
        "Early unstake penalty bypass",
        "Sybil attacks on rewards",
        "Reentrancy in claim",
    ],
    known_attack_patterns=[
        "reward-manipulation",
        "compound-rounding-exploit",
    ],
    primitive_invariants=[
        Invariant(
            id="staking-reward-conservation",
            description="Total rewards distributed <= total rewards allocated",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="staking-lock-period",
            description="Must enforce minimum staking period if applicable",
            scope="function",
            must_have=[],
            must_not_have=[]
        ),
    ]
)


# Collection of all DeFi primitives
ALL_DEFI_PRIMITIVES = [
    AMM_SWAP,
    LENDING_POOL,
    FLASH_LOAN,
    YIELD_VAULT,
    STAKING,
]
