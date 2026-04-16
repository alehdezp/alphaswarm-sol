// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title MessageVerifier (SAFE VARIANT)
contract MessageVerifier_safe {
    address public trustedSigner;
    address public admin;

    modifier onlyAdmin() { require(msg.sender == admin, "Not admin"); _; }

    constructor(address _signer) { trustedSigner = _signer; admin = msg.sender; }

    function validateProof(bytes32 messageId, address recipient, uint256 amount, bytes calldata proof) external view returns (bool) {
        bytes32 expectedHash = keccak256(abi.encodePacked(messageId, recipient, amount, block.chainid)); // FIXED: chainId
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", expectedHash));
        address recovered = _recover(ethHash, proof);
        return recovered == trustedSigner;
    }

    function rotateSigner(address newSigner) external onlyAdmin { // FIXED
        require(newSigner != address(0));
        trustedSigner = newSigner;
    }

    function _recover(bytes32 hash, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "Bad sig");
        bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset) s := calldataload(add(sig.offset, 32)) v := byte(0, calldataload(add(sig.offset, 64))) }
        return ecrecover(hash, v, r, s);
    }
}
