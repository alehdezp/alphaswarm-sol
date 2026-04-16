// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-VULN-005: Callback Reentrancy
// VULNERABLE: Flash loan callback before state finalization
interface IFlashLoanReceiver {
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32);
}

contract Vault_09 {
    mapping(address => uint256) public balances;
    uint256 public totalLiquidity;
    bytes32 private constant CALLBACK_SUCCESS = keccak256("FlashLoanReceiver.onFlashLoan");

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalLiquidity += msg.value;
    }

    // VULNERABLE: callback invoked before state is finalized
    function executeFlashLoan(
        address receiver,
        uint256 amount,
        bytes calldata data
    ) external {
        require(totalLiquidity >= amount, "insufficient liquidity");

        uint256 balanceBefore = address(this).balance;

        // Transfer funds to receiver
        (bool ok, ) = receiver.call{value: amount}("");
        require(ok, "transfer failed");

        // VULNERABLE: callback invoked while state is inconsistent
        // totalLiquidity not yet updated, receiver can exploit
        bytes32 result = IFlashLoanReceiver(receiver).onFlashLoan(
            msg.sender,
            address(0), // ETH
            amount,
            0, // no fee for simplicity
            data
        );
        require(result == CALLBACK_SUCCESS, "invalid callback return");

        // Check repayment
        require(address(this).balance >= balanceBefore, "flash loan not repaid");
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        totalLiquidity -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
    }

    receive() external payable {}
}
