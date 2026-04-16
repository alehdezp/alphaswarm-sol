// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ExternalService {
    function touch() external {}
}

contract InternalChain {
    ExternalService public service;
    uint256 public total;

    constructor(ExternalService _service) {
        service = _service;
    }

    function outer(uint256 amount) external {
        _inner(amount);
        total += amount;
    }

    function outerSafe(uint256 amount) external {
        total += amount;
        _inner(amount);
    }

    function _inner(uint256 amount) internal {
        service.touch();
        total += amount;
    }
}
