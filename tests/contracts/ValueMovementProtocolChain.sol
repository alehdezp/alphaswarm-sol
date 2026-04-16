// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ExternalPool {
    function swap() external {}
}

contract Strategy {
    ExternalPool public pool;
    uint256 public total;

    constructor(ExternalPool _pool) {
        pool = _pool;
    }

    function invest(uint256 amount) external {
        pool.swap();
        total += amount;
    }

    function investSafe(uint256 amount) external {
        total += amount;
        pool.swap();
    }
}

contract Protocol {
    Strategy public strategy;
    uint256 public shares;

    constructor(Strategy _strategy) {
        strategy = _strategy;
    }

    function deposit(uint256 amount) external {
        strategy.invest(amount);
        shares += amount;
    }

    function depositSafe(uint256 amount) external {
        shares += amount;
        strategy.invest(amount);
    }
}
