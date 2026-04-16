// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title Erc777Reentrancy
 * @dev Demonstrates ERC777 reentrancy vulnerability via hooks
 *
 * ERC777 tokens have tokensReceived hook that's called on every
 * transfer. This creates reentrancy opportunities similar to ETH transfers.
 *
 * REAL-WORLD: Uniswap imBTC pool hack (2020) - $300k stolen via ERC777 reentrancy
 * Also affected: Lendf.me ($25M), dForce
 *
 * CWE-841: Improper Enforcement of Behavioral Workflow
 */

interface IERC777Recipient {
    function tokensReceived(
        address operator,
        address from,
        address to,
        uint256 amount,
        bytes calldata userData,
        bytes calldata operatorData
    ) external;
}

// Simplified ERC777 token
contract SimpleERC777 {
    mapping(address => uint256) public balanceOf;
    mapping(address => bool) public isERC777Recipient;

    function transfer(address to, uint256 amount) public returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;

        // ERC777 hook - calls recipient contract!
        if (isERC777Recipient[to]) {
            IERC777Recipient(to).tokensReceived(
                msg.sender,
                msg.sender,
                to,
                amount,
                "",
                ""
            );
        }
        return true;
    }

    function registerRecipient(address recipient) public {
        isERC777Recipient[recipient] = true;
    }

    function mint(address to, uint256 amount) public {
        balanceOf[to] += amount;
    }
}

// VULNERABLE: Vault without reentrancy protection
contract VulnerableERC777Vault is IERC777Recipient {
    mapping(address => uint256) public deposits;
    address public token;

    constructor(address _token) {
        token = _token;
        SimpleERC777(_token).registerRecipient(address(this));
    }

    function deposit(uint256 amount) public {
        SimpleERC777(token).transfer(address(this), amount);
        // PROBLEM: tokensReceived hook is called BEFORE this line!
        // Attacker can reenter and manipulate state
        deposits[msg.sender] += amount;
    }

    function withdraw(uint256 amount) public {
        require(deposits[msg.sender] >= amount, "Insufficient balance");
        // PROBLEM: State updated after transfer - classic reentrancy!
        SimpleERC777(token).transfer(msg.sender, amount);
        deposits[msg.sender] -= amount;
    }

    // ERC777 recipient hook
    function tokensReceived(
        address,
        address from,
        address,
        uint256,
        bytes calldata,
        bytes calldata
    ) external override {
        // Hook is called during transfer
        // Attacker can reenter here!
    }
}

// Attacker contract exploiting ERC777 reentrancy
contract ERC777Attacker is IERC777Recipient {
    VulnerableERC777Vault public vault;
    SimpleERC777 public token;
    uint256 public attackCount;
    uint256 constant MAX_ATTACKS = 5;

    constructor(address _vault, address _token) {
        vault = VulnerableERC777Vault(_vault);
        token = SimpleERC777(_token);
        SimpleERC777(_token).registerRecipient(address(this));
    }

    function attack() public {
        // Initial deposit
        token.transfer(address(vault), 100);
        // This will trigger reentrancy in tokensReceived
    }

    function tokensReceived(
        address,
        address,
        address,
        uint256,
        bytes calldata,
        bytes calldata
    ) external override {
        // REENTRANCY: Called during vault.deposit() or vault.withdraw()
        if (attackCount < MAX_ATTACKS) {
            attackCount++;
            // Reenter and withdraw before state is updated!
            if (vault.deposits(address(this)) > 0) {
                vault.withdraw(100);
            }
        }
    }
}

// SAFE: Vault with reentrancy guard
contract SafeERC777Vault is IERC777Recipient {
    mapping(address => uint256) public deposits;
    address public token;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "Reentrancy detected");
        locked = true;
        _;
        locked = false;
    }

    constructor(address _token) {
        token = _token;
        SimpleERC777(_token).registerRecipient(address(this));
    }

    function deposit(uint256 amount) public nonReentrant {
        SimpleERC777(token).transfer(address(this), amount);
        deposits[msg.sender] += amount;
    }

    function withdraw(uint256 amount) public nonReentrant {
        require(deposits[msg.sender] >= amount, "Insufficient balance");
        deposits[msg.sender] -= amount;  // State updated first
        SimpleERC777(token).transfer(msg.sender, amount);
    }

    function tokensReceived(
        address,
        address,
        address,
        uint256,
        bytes calldata,
        bytes calldata
    ) external override {
        // Hook is protected by nonReentrant modifier
    }
}

// SAFE: Checks-Effects-Interactions pattern
contract SafeERC777VaultCEI is IERC777Recipient {
    mapping(address => uint256) public deposits;
    address public token;

    constructor(address _token) {
        token = _token;
        SimpleERC777(_token).registerRecipient(address(this));
    }

    function withdraw(uint256 amount) public {
        // Checks
        require(deposits[msg.sender] >= amount, "Insufficient balance");

        // Effects (update state FIRST)
        deposits[msg.sender] -= amount;

        // Interactions (external calls LAST)
        SimpleERC777(token).transfer(msg.sender, amount);
    }

    function tokensReceived(
        address,
        address,
        address,
        uint256,
        bytes calldata,
        bytes calldata
    ) external override {
        // Even if reentered, state is already updated
    }
}

// VULNERABLE: DEX pool with ERC777
contract VulnerableERC777Pool is IERC777Recipient {
    SimpleERC777 public token0;  // ERC777
    address public token1;        // Regular ERC20

    uint256 public reserve0;
    uint256 public reserve1;

    constructor(address _token0, address _token1) {
        token0 = SimpleERC777(_token0);
        token1 = _token1;
        token0.registerRecipient(address(this));
    }

    function swap(uint256 amount0In, uint256 amount1Out) public {
        if (amount0In > 0) {
            token0.transfer(address(this), amount0In);
            // PROBLEM: tokensReceived hook called here
            // Attacker can reenter and manipulate reserves before they're updated!
            reserve0 += amount0In;
        }

        reserve1 -= amount1Out;
        // Transfer token1 to user
    }

    function tokensReceived(
        address,
        address,
        address,
        uint256,
        bytes calldata,
        bytes calldata
    ) external override {
        // Reentrancy point - reserves not yet updated!
    }
}
