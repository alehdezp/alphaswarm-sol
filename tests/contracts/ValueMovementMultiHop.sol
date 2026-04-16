// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract HopCallee {
    function ping() external {}
}

contract HopRouter {
    HopCallee public callee;

    constructor(HopCallee _callee) {
        callee = _callee;
    }

    function hop() external {
        callee.ping();
    }
}

contract HopStrategy {
    HopRouter public router;
    uint256 public total;

    constructor(HopRouter _router) {
        router = _router;
    }

    function rebalance(uint256 amount) external {
        router.hop();
        total += amount;
    }

    function rebalanceSafe(uint256 amount) external {
        total += amount;
        router.hop();
    }
}

contract HopProtocol {
    HopStrategy public strategy;
    uint256 public shares;
    bool private locked;

    constructor(HopStrategy _strategy) {
        strategy = _strategy;
    }

    modifier lock() {
        require(!locked, "locked");
        locked = true;
        _;
        locked = false;
    }

    function execute(uint256 amount) external {
        strategy.rebalance(amount);
        shares += amount;
    }

    function executeSafe(uint256 amount) external {
        shares += amount;
        strategy.rebalance(amount);
    }

    function executeGuarded(uint256 amount) external lock {
        strategy.rebalance(amount);
        shares += amount;
    }
}
