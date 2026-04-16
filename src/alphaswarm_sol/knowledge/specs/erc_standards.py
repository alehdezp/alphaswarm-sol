"""
ERC Standard Specifications

Defines ERC-20, ERC-721, ERC-4626, and other token standards
with their invariants and expected behaviors.
"""

from alphaswarm_sol.knowledge.domain_kg import (
    Specification,
    Invariant,
    SpecType,
)


# ERC-20: Fungible Token Standard
ERC20 = Specification(
    id="erc-20",
    spec_type=SpecType.ERC_STANDARD,
    name="ERC-20",
    description="Fungible token standard",
    version="EIP-20",
    function_signatures=[
        "transfer(address,uint256)",
        "transferFrom(address,address,uint256)",
        "approve(address,uint256)",
        "balanceOf(address)",
        "allowance(address,address)",
        "totalSupply()",
    ],
    expected_operations=[
        "TRANSFERS_VALUE_OUT",
        "WRITES_USER_BALANCE",
        "READS_USER_BALANCE",
    ],
    invariants=[
        Invariant(
            id="erc20-balance-conservation",
            description="Sum of all balances must equal totalSupply",
            scope="transaction",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="erc20-transfer-cei",
            description="transfer must follow checks-effects-interactions",
            scope="function",
            violation_signature="R:bal→X:out→W:bal",
            must_have=["follows_cei_pattern"],
            must_not_have=["state_write_after_external_call"]
        ),
        Invariant(
            id="erc20-transfer-return",
            description="transfer must return bool indicating success",
            scope="function",
            must_have=["has_return_value"],
            must_not_have=[]
        ),
    ],
    preconditions=[
        "Sender has sufficient balance",
        "Recipient address is not zero",
    ],
    postconditions=[
        "Sender balance decreased by amount",
        "Recipient balance increased by amount",
        "Transfer event emitted",
    ],
    common_violations=[
        "Missing return value check",
        "Reentrancy in transfer",
        "Arithmetic overflow/underflow",
        "Missing zero address check",
    ],
    related_cwes=["CWE-682", "CWE-841"],
    semantic_tags=["token", "transfer", "balance", "fungible"],
    external_refs={
        "eip": "https://eips.ethereum.org/EIPS/eip-20",
        "openzeppelin": "https://docs.openzeppelin.com/contracts/erc20"
    }
)


# ERC-721: Non-Fungible Token Standard
ERC721 = Specification(
    id="erc-721",
    spec_type=SpecType.ERC_STANDARD,
    name="ERC-721",
    description="Non-fungible token (NFT) standard",
    version="EIP-721",
    function_signatures=[
        "transferFrom(address,address,uint256)",
        "safeTransferFrom(address,address,uint256)",
        "safeTransferFrom(address,address,uint256,bytes)",
        "approve(address,uint256)",
        "setApprovalForAll(address,bool)",
        "ownerOf(uint256)",
        "balanceOf(address)",
    ],
    expected_operations=[
        "TRANSFERS_VALUE_OUT",
        "WRITES_OWNER",
        "READS_OWNER",
    ],
    invariants=[
        Invariant(
            id="erc721-unique-ownership",
            description="Each tokenId must have exactly one owner",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="erc721-safe-transfer-callback",
            description="safeTransferFrom must check recipient is ERC721Receiver",
            scope="function",
            must_have=["has_external_calls"],
            must_not_have=[]
        ),
    ],
    preconditions=[
        "Token exists",
        "Caller is owner or approved",
        "Recipient address is not zero",
    ],
    postconditions=[
        "Token owner updated",
        "Previous owner approval cleared",
        "Transfer event emitted",
    ],
    common_violations=[
        "Missing receiver check in safeTransferFrom",
        "Reentrancy via onERC721Received callback",
        "Missing ownership validation",
    ],
    related_cwes=["CWE-682"],
    semantic_tags=["nft", "ownership", "transfer", "approval"],
    external_refs={
        "eip": "https://eips.ethereum.org/EIPS/eip-721",
    }
)


# ERC-4626: Tokenized Vault Standard
ERC4626 = Specification(
    id="erc-4626",
    spec_type=SpecType.ERC_STANDARD,
    name="ERC-4626",
    description="Tokenized vault standard",
    version="EIP-4626",
    function_signatures=[
        "deposit(uint256,address)",
        "mint(uint256,address)",
        "withdraw(uint256,address,address)",
        "redeem(uint256,address,address)",
        "totalAssets()",
        "convertToShares(uint256)",
        "convertToAssets(uint256)",
    ],
    expected_operations=[
        "TRANSFERS_VALUE_IN",
        "TRANSFERS_VALUE_OUT",
        "WRITES_USER_BALANCE",
        "READS_USER_BALANCE",
    ],
    invariants=[
        Invariant(
            id="erc4626-share-price-consistency",
            description="Share price must not be manipulatable within single transaction",
            scope="transaction",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="erc4626-deposit-mint-equivalence",
            description="deposit(a) should mint same shares as mint(convertToShares(a))",
            scope="contract",
            must_have=[],
            must_not_have=[]
        ),
        Invariant(
            id="erc4626-rounding-favor-vault",
            description="Rounding must favor the vault to prevent donation attacks",
            scope="function",
            must_have=[],
            must_not_have=[]
        ),
    ],
    preconditions=[
        "Vault has sufficient liquidity for withdrawals",
        "User has sufficient balance for deposits",
        "Slippage protection in place",
    ],
    postconditions=[
        "Shares minted/burned correctly",
        "Assets transferred",
        "Events emitted",
    ],
    common_violations=[
        "Share price manipulation via donation",
        "Rounding errors favoring attacker",
        "Missing slippage protection",
        "Reentrancy in deposit/withdraw",
        "First depositor attack",
    ],
    related_cwes=["CWE-682", "CWE-841"],
    semantic_tags=["vault", "deposit", "withdraw", "shares", "defi"],
    external_refs={
        "eip": "https://eips.ethereum.org/EIPS/eip-4626",
        "openzeppelin": "https://docs.openzeppelin.com/contracts/erc4626"
    }
)


# ERC-1155: Multi-Token Standard
ERC1155 = Specification(
    id="erc-1155",
    spec_type=SpecType.ERC_STANDARD,
    name="ERC-1155",
    description="Multi-token standard (fungible + non-fungible)",
    version="EIP-1155",
    function_signatures=[
        "safeTransferFrom(address,address,uint256,uint256,bytes)",
        "safeBatchTransferFrom(address,address,uint256[],uint256[],bytes)",
        "balanceOf(address,uint256)",
        "balanceOfBatch(address[],uint256[])",
        "setApprovalForAll(address,bool)",
    ],
    expected_operations=[
        "TRANSFERS_VALUE_OUT",
        "WRITES_USER_BALANCE",
        "READS_USER_BALANCE",
    ],
    invariants=[
        Invariant(
            id="erc1155-safe-transfer-callback",
            description="Must call onERC1155Received on recipient",
            scope="function",
            must_have=["has_external_calls"],
            must_not_have=[]
        ),
        Invariant(
            id="erc1155-balance-conservation",
            description="Total balance of tokenId must remain constant",
            scope="transaction",
            must_have=[],
            must_not_have=[]
        ),
    ],
    preconditions=[
        "Caller is owner or approved",
        "Sufficient balance for transfer",
    ],
    postconditions=[
        "Balances updated",
        "Receiver callback succeeded",
        "Events emitted",
    ],
    common_violations=[
        "Missing receiver check",
        "Reentrancy via callback",
        "Array length mismatch",
    ],
    related_cwes=["CWE-682"],
    semantic_tags=["multi-token", "batch", "transfer"],
    external_refs={
        "eip": "https://eips.ethereum.org/EIPS/eip-1155",
    }
)


# Collection of all ERC standards
ALL_ERC_STANDARDS = [
    ERC20,
    ERC721,
    ERC4626,
    ERC1155,
]
