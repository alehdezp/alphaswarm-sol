// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title Erc1155Vulnerabilities
 * @dev Demonstrates ERC1155-specific vulnerabilities
 *
 * VULNERABILITIES:
 * - TotalSupply inconsistency (CVE-2021-43987)
 * - Batch operation reentrancy
 * - ID confusion between fungible/non-fungible
 * - Hook exploitation
 *
 * CWE-841: Improper Enforcement of Behavioral Workflow
 * CWE-1265: Unintended Reentrant Invocation
 *
 * REAL EXAMPLES:
 * - OpenZeppelin ERC1155Supply reentrancy (2021)
 * - reNFT token freezing vulnerability (2024)
 */

interface IERC1155 {
    function safeTransferFrom(
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes calldata data
    ) external;

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) external;

    function balanceOf(address account, uint256 id) external view returns (uint256);
    function balanceOfBatch(
        address[] calldata accounts,
        uint256[] calldata ids
    ) external view returns (uint256[] memory);
}

interface IERC1155Receiver {
    function onERC1155Received(
        address operator,
        address from,
        address to,
        uint256 id,
        uint256 value,
        bytes calldata data
    ) external returns (bytes4);

    function onERC1155BatchReceived(
        address operator,
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata values,
        bytes calldata data
    ) external returns (bytes4);
}

// VULNERABLE: TotalSupply inconsistency during minting
contract VulnerableErc1155Supply is IERC1155 {
    mapping(uint256 => uint256) private _totalSupply;
    mapping(uint256 => mapping(address => uint256)) private _balances;

    event TransferSingle(
        address indexed operator,
        address indexed from,
        address indexed to,
        uint256 id,
        uint256 value
    );

    function mint(address to, uint256 id, uint256 amount) public {
        _balances[id][to] += amount;

        // PROBLEM: Call hook BEFORE updating totalSupply
        // During the hook, totalSupply is inconsistent with actual supply
        if (isContract(to)) {
            require(
                IERC1155Receiver(to).onERC1155Received(
                    msg.sender, address(0), to, id, amount, ""
                ) == IERC1155Receiver.onERC1155Received.selector,
                "Receiver rejected"
            );
        }

        // TotalSupply updated AFTER hook - reentrancy window!
        _totalSupply[id] += amount;

        emit TransferSingle(msg.sender, address(0), to, id, amount);
    }

    function totalSupply(uint256 id) public view returns (uint256) {
        return _totalSupply[id];
    }

    function balanceOf(address account, uint256 id) public view override returns (uint256) {
        return _balances[id][account];
    }

    function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes calldata data) public override {
        _balances[id][from] -= amount;
        _balances[id][to] += amount;
        emit TransferSingle(msg.sender, from, to, id, amount);
    }

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) public override {
        for (uint i = 0; i < ids.length; i++) {
            _balances[ids[i]][from] -= amounts[i];
            _balances[ids[i]][to] += amounts[i];
        }
    }

    function balanceOfBatch(
        address[] calldata accounts,
        uint256[] calldata ids
    ) public view override returns (uint256[] memory) {
        uint256[] memory batchBalances = new uint256[](accounts.length);
        for (uint i = 0; i < accounts.length; i++) {
            batchBalances[i] = _balances[ids[i]][accounts[i]];
        }
        return batchBalances;
    }

    function isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }
}

// Exploit contract for totalSupply inconsistency
contract TotalSupplyExploit is IERC1155Receiver {
    VulnerableErc1155Supply public token;
    uint256 public exploitId;
    bool public attacking;

    constructor(address _token) {
        token = VulnerableErc1155Supply(_token);
    }

    function onERC1155Received(
        address,
        address,
        address,
        uint256 id,
        uint256,
        bytes calldata
    ) external override returns (bytes4) {
        if (!attacking) {
            attacking = true;
            exploitId = id;

            // During this callback, balance is updated but totalSupply is not!
            uint256 myBalance = token.balanceOf(address(this), id);
            uint256 supply = token.totalSupply(id);

            // Balance > totalSupply - inconsistent state!
            // Can exploit systems that rely on totalSupply for calculations
        }

        return IERC1155Receiver.onERC1155Received.selector;
    }

    function onERC1155BatchReceived(
        address,
        address,
        address,
        uint256[] calldata,
        uint256[] calldata,
        bytes calldata
    ) external pure override returns (bytes4) {
        return IERC1155Receiver.onERC1155BatchReceived.selector;
    }
}

// SAFE: TotalSupply update before hook
contract SafeErc1155Supply is IERC1155 {
    mapping(uint256 => uint256) private _totalSupply;
    mapping(uint256 => mapping(address => uint256)) private _balances;

    event TransferSingle(
        address indexed operator,
        address indexed from,
        address indexed to,
        uint256 id,
        uint256 value
    );

    function mint(address to, uint256 id, uint256 amount) public {
        // Update state BEFORE external call
        _balances[id][to] += amount;
        _totalSupply[id] += amount;

        emit TransferSingle(msg.sender, address(0), to, id, amount);

        // Hook called AFTER state is consistent
        if (isContract(to)) {
            require(
                IERC1155Receiver(to).onERC1155Received(
                    msg.sender, address(0), to, id, amount, ""
                ) == IERC1155Receiver.onERC1155Received.selector,
                "Receiver rejected"
            );
        }
    }

    function totalSupply(uint256 id) public view returns (uint256) {
        return _totalSupply[id];
    }

    function balanceOf(address account, uint256 id) public view override returns (uint256) {
        return _balances[id][account];
    }

    function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes calldata data) public override {
        _balances[id][from] -= amount;
        _balances[id][to] += amount;
        emit TransferSingle(msg.sender, from, to, id, amount);
    }

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) public override {
        for (uint i = 0; i < ids.length; i++) {
            _balances[ids[i]][from] -= amounts[i];
            _balances[ids[i]][to] += amounts[i];
        }
    }

    function balanceOfBatch(
        address[] calldata accounts,
        uint256[] calldata ids
    ) public view override returns (uint256[] memory) {
        uint256[] memory batchBalances = new uint256[](accounts.length);
        for (uint i = 0; i < accounts.length; i++) {
            batchBalances[i] = _balances[ids[i]][accounts[i]];
        }
        return batchBalances;
    }

    function isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }
}

// VULNERABLE: ID confusion - can't distinguish rented from owned tokens
contract VulnerableErc1155Rental {
    IERC1155 public token;
    mapping(address => mapping(uint256 => uint256)) public rentedAmounts;

    constructor(address _token) {
        token = IERC1155(_token);
    }

    function rentToken(uint256 id, uint256 amount) public {
        // Track rented amount
        rentedAmounts[msg.sender][id] += amount;

        // Transfer tokens to user
        token.safeTransferFrom(address(this), msg.sender, id, amount, "");
    }

    function returnToken(uint256 id, uint256 amount) public {
        require(rentedAmounts[msg.sender][id] >= amount, "Not rented");

        // PROBLEM: Can't distinguish rented tokens from user's own tokens!
        // User can transfer their own tokens instead of rented ones
        token.safeTransferFrom(msg.sender, address(this), id, amount, "");

        rentedAmounts[msg.sender][id] -= amount;
    }
}

// Exploit: User with existing tokens can keep rented tokens
contract Erc1155RentalExploit is IERC1155Receiver {
    VulnerableErc1155Rental public rental;
    IERC1155 public token;
    uint256 public exploitId;

    constructor(address _rental, address _token) {
        rental = VulnerableErc1155Rental(_rental);
        token = IERC1155(_token);
    }

    function exploit(uint256 id, uint256 amount) public {
        // Assume we already own some tokens of this ID
        // Rent additional tokens
        rental.rentToken(id, amount);

        // When returning, send our own tokens instead of rented ones
        // Keep the rented tokens!
    }

    function onERC1155Received(
        address,
        address,
        address,
        uint256,
        uint256,
        bytes calldata
    ) external pure override returns (bytes4) {
        return IERC1155Receiver.onERC1155Received.selector;
    }

    function onERC1155BatchReceived(
        address,
        address,
        address,
        uint256[] calldata,
        uint256[] calldata,
        bytes calldata
    ) external pure override returns (bytes4) {
        return IERC1155Receiver.onERC1155BatchReceived.selector;
    }
}

// SAFE: Use separate rental tokens (wrapped)
contract SafeErc1155Rental is IERC1155 {
    IERC1155 public underlyingToken;
    mapping(uint256 => mapping(address => uint256)) private _rentalBalances;
    mapping(uint256 => uint256) private _totalRental;

    constructor(address _token) {
        underlyingToken = IERC1155(_token);
    }

    function rentToken(uint256 id, uint256 amount) public {
        // Receive underlying tokens
        underlyingToken.safeTransferFrom(msg.sender, address(this), id, amount, "");

        // Issue rental tokens (different from underlying)
        _rentalBalances[id][msg.sender] += amount;
        _totalRental[id] += amount;
    }

    function returnToken(uint256 id, uint256 amount) public {
        require(_rentalBalances[id][msg.sender] >= amount, "Insufficient rental balance");

        // Burn rental tokens
        _rentalBalances[id][msg.sender] -= amount;
        _totalRental[id] -= amount;

        // Return underlying tokens
        underlyingToken.safeTransferFrom(address(this), msg.sender, id, amount, "");
    }

    function balanceOf(address account, uint256 id) public view override returns (uint256) {
        return _rentalBalances[id][account];
    }

    function safeTransferFrom(address, address, uint256, uint256, bytes calldata) public pure override {
        revert("Rental tokens not transferable");
    }

    function safeBatchTransferFrom(
        address,
        address,
        uint256[] calldata,
        uint256[] calldata,
        bytes calldata
    ) public pure override {
        revert("Rental tokens not transferable");
    }

    function balanceOfBatch(
        address[] calldata accounts,
        uint256[] calldata ids
    ) public view override returns (uint256[] memory) {
        uint256[] memory batchBalances = new uint256[](accounts.length);
        for (uint i = 0; i < accounts.length; i++) {
            batchBalances[i] = _rentalBalances[ids[i]][accounts[i]];
        }
        return batchBalances;
    }
}

// VULNERABLE: Batch transfer reentrancy
contract VulnerableBatchTransfer is IERC1155, IERC1155Receiver {
    mapping(uint256 => mapping(address => uint256)) private _balances;

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) public override {
        // PROBLEM: Updates balances in loop, then calls hook at end
        // Hook can observe partially-updated state
        for (uint i = 0; i < ids.length; i++) {
            _balances[ids[i]][from] -= amounts[i];
            _balances[ids[i]][to] += amounts[i];
        }

        // Hook called after all updates
        if (isContract(to)) {
            require(
                IERC1155Receiver(to).onERC1155BatchReceived(
                    msg.sender, from, to, ids, amounts, data
                ) == IERC1155Receiver.onERC1155BatchReceived.selector,
                "Receiver rejected"
            );
        }
    }

    function balanceOf(address account, uint256 id) public view override returns (uint256) {
        return _balances[id][account];
    }

    function safeTransferFrom(address, address, uint256, uint256, bytes calldata) public override {}
    function balanceOfBatch(address[] calldata, uint256[] calldata) public pure override returns (uint256[] memory) {
        return new uint256[](0);
    }

    function isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }

    function onERC1155Received(address, address, address, uint256, uint256, bytes calldata)
        external
        pure
        override
        returns (bytes4)
    {
        return IERC1155Receiver.onERC1155Received.selector;
    }

    function onERC1155BatchReceived(
        address,
        address,
        address,
        uint256[] calldata,
        uint256[] calldata,
        bytes calldata
    ) external pure override returns (bytes4) {
        return IERC1155Receiver.onERC1155BatchReceived.selector;
    }
}

// SAFE: Reentrancy guard for batch operations
contract SafeBatchTransfer is IERC1155 {
    mapping(uint256 => mapping(address => uint256)) private _balances;
    bool private locked;

    modifier noReentrant() {
        require(!locked, "Reentrant call");
        locked = true;
        _;
        locked = false;
    }

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) public override noReentrant {
        for (uint i = 0; i < ids.length; i++) {
            _balances[ids[i]][from] -= amounts[i];
            _balances[ids[i]][to] += amounts[i];
        }

        if (isContract(to)) {
            require(
                IERC1155Receiver(to).onERC1155BatchReceived(
                    msg.sender, from, to, ids, amounts, data
                ) == IERC1155Receiver.onERC1155BatchReceived.selector,
                "Receiver rejected"
            );
        }
    }

    function balanceOf(address account, uint256 id) public view override returns (uint256) {
        return _balances[id][account];
    }

    function safeTransferFrom(address, address, uint256, uint256, bytes calldata) public override {}
    function balanceOfBatch(address[] calldata, uint256[] calldata) public pure override returns (uint256[] memory) {
        return new uint256[](0);
    }

    function isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }
}
