// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title MessageVerifier - Validates cross-chain messages
/// @dev VULNERABILITY: Weak verification allows forged messages (B1 split vulnerability)
contract MessageVerifier {
    address public trustedSigner;
    uint256 public minConfirmations;

    constructor(address _signer) {
        trustedSigner = _signer;
        minConfirmations = 1;
    }

    /// @notice Validate a cross-chain proof
    /// @dev VULNERABILITY: No chain ID in signed message (cross-chain replay)
    function validateProof(
        bytes32 messageId,
        address recipient,
        uint256 amount,
        bytes calldata proof
    ) external view returns (bool) {
        // Reconstructed message missing chain ID
        bytes32 expectedHash = keccak256(
            abi.encodePacked(messageId, recipient, amount)
        );
        bytes32 ethHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", expectedHash)
        );

        address recovered = _recover(ethHash, proof);
        return recovered == trustedSigner;
    }

    /// @notice Update trusted signer
    /// @dev VULNERABILITY: No access control on signer rotation
    function rotateSigner(address newSigner) external {
        trustedSigner = newSigner;
    }

    function _recover(bytes32 hash, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "Bad sig");
        bytes32 r; bytes32 s; uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        return ecrecover(hash, v, r, s);
    }
}
