// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IRouterNoChecks {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract RouterSwapNoChecks {
    IRouterNoChecks public router;

    constructor(IRouterNoChecks router_) {
        router = router_;
    }

    function doSwap(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external {
        router.swapExactTokensForTokens(amountIn, amountOutMin, path, to, deadline);
    }
}
