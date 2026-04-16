// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract InvariantConfigFixture {
    uint256 public totalSupply;
    uint256 public totalSupplyHash;
    mapping(address => uint256) public balances;

    modifier ensureInvariant() {
        _checkInvariant();
        _;
    }

    modifier guardByName() {
        _;
    }

    function _checkInvariant() internal view {
        require(totalSupply >= balances[msg.sender], "invariant");
    }

    function deposit(uint256 amount) external ensureInvariant {
        balances[msg.sender] += amount;
        totalSupply += amount;
    }

    function guardedByName(uint256 amount) external guardByName {
        balances[msg.sender] += amount;
        totalSupply += amount;
    }

    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
        totalSupply -= amount;
        _checkInvariant();
    }

    function adjust(uint256 amount) external {
        _adjust(amount);
    }

    function _adjust(uint256 amount) internal {
        totalSupply += amount;
        _postAdjustCheck();
    }

    function _postAdjustCheck() internal view {
        _checkInvariant();
    }

    function skim(uint256 amount) external {
        totalSupply -= amount;
    }

    function updateHash(bytes32 newHash) external {
        totalSupplyHash = uint256(newHash);
    }
}
