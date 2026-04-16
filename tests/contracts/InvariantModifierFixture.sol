// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract InvariantModifierFixture {
    /// invariant: totalSupply + pendingSupply == cap
    uint256 public totalSupply;
    uint256 public pendingSupply;
    uint256 public cap;

    modifier checkInvariant() {
        assert(totalSupply + pendingSupply <= cap);
        _;
    }

    function mint(uint256 amount) external checkInvariant {
        totalSupply += amount;
        pendingSupply += amount;
    }

    function unsafeMint(uint256 amount) external {
        totalSupply += amount;
    }

    function assertCheck(uint256 amount) external {
        totalSupply += amount;
        assert(totalSupply <= cap);
    }

    function internalChecked(uint256 amount) external {
        _internal(amount);
    }

    function _internal(uint256 amount) internal {
        totalSupply += amount;
        _assertInvariant();
    }

    function _assertInvariant() internal view {
        assert(totalSupply + pendingSupply <= cap);
    }
}
