// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BaseState {
    function updateState(uint256 value) public virtual {}
}

contract LogicStateLens is BaseState {
    enum Status {
        None,
        Active,
        Closed
    }

    Status public state;
    // invariant balances accounting
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    uint256 public collateral;
    uint256 public pool;
    bool public paused;
    bool public flag;
    address public owner;

    event Updated(address indexed user, uint256 value);

    constructor() {
        uint256 size;
        assembly {
            size := extcodesize(address())
        }
        if (size == 0) {
            state = Status.None;
        }
    }

    function setStateNoCheck(Status next) external {
        state = next;
    }

    function finishState() external {
        state = Status.Closed;
    }

    function externalCallNoGuard(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
        state = Status.Active;
    }

    function updateBalance(address user, uint256 amount) external {
        balances[user] += amount;
    }

    function updateCollateral(uint256 amount) external {
        collateral += amount;
    }

    function updatePool(uint256 amount) external {
        pool += amount;
    }

    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
    }

    function transferToken(address token, address to, uint256 amount) external {
        (bool ok, ) = token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
        require(ok, "transfer failed");
    }

    function unsafeTransfer(address token, address to, uint256 amount) external {
        token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
    }

    function updateAmount(uint256 amount) external {
        totalSupply = amount;
    }

    function orderedExternalCall(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
        totalSupply += 1;
    }

    function conditionalGate() external {
        if (msg.sender != owner) {
            return;
        }
        paused = true;
    }

    function protocolCall(address target) external {
        (bool ok, ) = target.call("");
        require(ok, "call failed");
    }

    function doubleCount(address user, uint256 amount) external {
        balances[user] += amount;
        totalSupply += amount;
    }

    function transferEth(address payable to) external {
        to.transfer(1 ether);
    }

    function roundingLoop(uint256 amount, uint256 times) external pure returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < times; i++) {
            total += amount / 3;
        }
        return total;
    }

    function updateState(uint256 value) public override {
        totalSupply = value;
    }

    function kill(address payable recipient) external {
        selfdestruct(recipient);
    }

    function transferTo(address payable to) external {
        to.transfer(1);
    }

    function updateValue(address user, uint256 value) external {
        balances[user] = value;
    }

    function emitWrong(uint256 value) external {
        emit Updated(msg.sender, 0);
    }

    function shadowOwner(address owner) external {
        balances[owner] = 1;
    }
}

contract DiamondBaseA {
    function ping() external virtual {}
}

contract DiamondBaseB {
    function ping() external virtual {}
}

contract DiamondDerived is DiamondBaseA, DiamondBaseB {
    function ping() external override(DiamondBaseA, DiamondBaseB) {}
}
