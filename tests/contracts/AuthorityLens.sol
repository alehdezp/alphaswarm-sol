// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UnprotectedStateWriter {
    address public owner;

    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function setOwnerProtected(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}

contract TxOriginAuth {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function privileged() external {
        require(tx.origin == owner, "no");
    }
}

contract SignatureIssues {
    function verify(bytes32 hash, uint8 v, bytes32 r, bytes32 s) external pure returns (address) {
        return ecrecover(hash, v, r, s);
    }
}

contract CentralizedAdmin {
    address public owner;
    address public oracle;

    constructor() {
        owner = msg.sender;
    }

    function setOracle(address newOracle) external {
        oracle = newOracle;
    }
}

contract UnprotectedInitializer {
    address public owner;

    function initialize(address newOwner) external {
        owner = newOwner;
    }

    modifier initializer() {
        _;
    }

    function initializeProtected(address newOwner) external initializer {
        owner = newOwner;
    }
}

contract PrivilegeEscalation {
    mapping(address => bool) public roles;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function grantSelf() external {
        roles[msg.sender] = true;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function grantSelfProtected() external onlyOwner {
        roles[msg.sender] = true;
    }
}

contract BypassableAccess {
    address public critical;

    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external returns (bytes4) {
        critical = msg.sender;
        return 0x150b7a02;
    }
}

contract CrossContractAuthConfusion {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function delegateAsOwner(address target, bytes calldata data) external {
        require(msg.sender == owner, "no");
        target.delegatecall(data);
    }
}

contract UnprotectedValueTransfer {
    function sweep(address payable to) external {
        to.transfer(address(this).balance);
    }
}

contract UnprotectedAdminNames {
    uint256 public feeBps;

    function updateFee(uint256 newFee) external {
        feeBps = newFee;
    }
}

contract InconsistentAccessControl {
    address public owner;
    address public oracle;

    constructor() {
        owner = msg.sender;
    }

    function setOracle(address newOracle) external {
        oracle = newOracle;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}

contract RoleGrantOnly {
    mapping(address => bool) public roles;

    function grantRole(address account) external {
        roles[account] = true;
    }
}

contract DefaultAdminConfigured {
    bytes32 public DEFAULT_ADMIN_ROLE;

    function grantRole(address account) external {
        account;
    }
}

interface IERC20Auth {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract DangerousAdminFunction {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function emergencyWithdraw(address token, address to, uint256 amount) external onlyOwner {
        IERC20Auth(token).transfer(to, amount);
    }
}

contract WeakTimeAuth {
    uint256 public value;

    function timeGate(uint256 release) external {
        require(block.timestamp > release, "too early");
        value = 1;
    }
}

contract CallbackWithoutAuth {
    address public lastCaller;

    function onERC1155Received(
        address,
        address,
        uint256,
        uint256,
        bytes calldata
    ) external returns (bytes4) {
        lastCaller = msg.sender;
        return 0xf23a6e61;
    }
}

contract TimeLockedWithdraw {
    uint256 public unlockTime;

    constructor(uint256 _unlockTime) {
        unlockTime = _unlockTime;
    }

    function withdraw(address payable to) external {
        require(block.timestamp >= unlockTime, "locked");
        to.transfer(address(this).balance);
    }
}
