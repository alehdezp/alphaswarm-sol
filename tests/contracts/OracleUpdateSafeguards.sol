// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract OracleUpdateSafeguards {
    address public owner;
    uint256 public lastPrice;
    uint256 public lastUpdate;
    uint256 public minUpdateDelay = 60;
    uint256 public updateEta;
    uint256 public maxDeviationBps = 1000;
    uint256 public expectedNonce;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "owner");
        _;
    }

    function setPrice(uint256 newPrice) external {
        lastPrice = newPrice;
        lastUpdate = block.timestamp;
    }

    function setPriceChecked(uint256 newPrice, bytes calldata sig, uint256 nonce) external onlyOwner {
        require(block.timestamp >= lastUpdate + minUpdateDelay, "rate");
        require(block.timestamp >= updateEta, "timelock");
        require(newPrice <= (lastPrice * (10_000 + maxDeviationBps)) / 10_000, "deviation");
        require(nonce == expectedNonce, "nonce");
        expectedNonce += 1;
        _validateSignature(sig, newPrice, nonce);
        lastPrice = newPrice;
        lastUpdate = block.timestamp;
    }

    function _validateSignature(bytes calldata sig, uint256 price, uint256 nonce) internal view {
        bytes32 digest = keccak256(abi.encodePacked(price, nonce));
        (uint8 v, bytes32 r, bytes32 s) = _split(sig);
        ecrecover(digest, v, r, s);
    }

    function _split(bytes calldata sig) internal pure returns (uint8, bytes32, bytes32) {
        require(sig.length == 65, "sig");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        return (v, r, s);
    }
}
