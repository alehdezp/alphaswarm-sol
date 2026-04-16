// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleSimple {
    function latestAnswer() external view returns (int256);
}

contract OraclePositiveCheck {
    IOracleSimple public oracle;

    constructor(IOracleSimple oracle_) {
        oracle = oracle_;
    }

    function priceNoCheck() external view returns (int256) {
        return oracle.latestAnswer();
    }

    function priceChecked() external view returns (int256) {
        int256 answer = oracle.latestAnswer();
        require(answer > 0, "answer");
        return answer;
    }
}
