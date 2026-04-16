// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract OracleUpdateControls {
    uint256 public price;
    uint256 public lastUpdate;
    uint256 public nonce;
    uint256 public minUpdateDelay = 60;
    uint256 public maxDeviation = 1e17;

    // Vulnerable: update without rate limit, deviation, signature, or nonce checks.
    function updatePrice(uint256 newPrice) external {
        price = newPrice;
        lastUpdate = block.timestamp;
    }

    // Safe: update with rate limit, deviation, signature, and nonce checks.
    function updatePriceSafe(
        uint256 newPrice,
        uint256 newNonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp >= lastUpdate + minUpdateDelay, "cooldown");
        uint256 delta = price > newPrice ? price - newPrice : newPrice - price;
        require(delta <= maxDeviation, "deviation");
        require(newNonce == nonce + 1, "nonce");
        bytes32 digest = keccak256(abi.encodePacked(address(this), newPrice, newNonce));
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "signature");
        nonce = newNonce;
        price = newPrice;
        lastUpdate = block.timestamp;
    }
}
