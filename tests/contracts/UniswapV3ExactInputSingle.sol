// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IUniswapV3Router {
    function exactInputSingle(bytes calldata params) external payable returns (uint256 amountOut);
}

contract UniswapV3ExactInputSingle {
    IUniswapV3Router public router;

    constructor(IUniswapV3Router router_) {
        router = router_;
    }

    function swap(bytes calldata params) external payable {
        router.exactInputSingle(params);
    }
}
