// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ReinitializerMissing
 * @dev Demonstrates missing reinitializer vulnerability in upgraded contracts
 *
 * When upgrading a contract to add new state variables, if there's
 * no reinitializer guard, an attacker could reinitialize the contract and set
 * new variables to malicious values.
 *
 * OpenZeppelin introduced `reinitializer(version)` modifier to handle this, but
 * many contracts don't use it properly.
 */

// VULNERABLE: V1 with basic initializer
contract ImplementationV1 {
    address public owner;
    uint256 public value;
    uint8 private _initialized;

    modifier initializer() {
        require(_initialized == 0, "Already initialized");
        _initialized = 1;
        _;
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }
}

// VULNERABLE: V2 adds new variable but no reinitializer protection
contract ImplementationV2Vulnerable {
    address public owner;
    uint256 public value;
    uint8 private _initialized;
    address public feeCollector;  // New in V2

    modifier initializer() {
        require(_initialized == 0, "Already initialized");
        _initialized = 1;
        _;
    }

    // PROBLEM: After upgrade, _initialized is already 1
    // This function can never be called to set feeCollector!
    // OR if we remove the check, anyone can call it again!
    function initializeV2(address _feeCollector) public {
        // No protection - anyone can call this!
        feeCollector = _feeCollector;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }
}

// SAFE: Proper versioned initialization
contract ImplementationV1Safe {
    address public owner;
    uint256 public value;
    uint8 private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(_initialized == 0 || _initializing, "Already initialized");
        bool isTopLevelCall = !_initializing;
        if (isTopLevelCall) {
            _initializing = true;
            _initialized = 1;
        }
        _;
        if (isTopLevelCall) {
            _initializing = false;
        }
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }
}

// SAFE: V2 with proper reinitializer
contract ImplementationV2Safe {
    address public owner;
    uint256 public value;
    uint8 private _initialized;
    bool private _initializing;
    address public feeCollector;  // New in V2

    modifier initializer() {
        require(_initialized == 0 || _initializing, "Already initialized");
        bool isTopLevelCall = !_initializing;
        if (isTopLevelCall) {
            _initializing = true;
            _initialized = 1;
        }
        _;
        if (isTopLevelCall) {
            _initializing = false;
        }
    }

    // Reinitializer for version 2
    modifier reinitializer(uint8 version) {
        require(
            !_initializing && _initialized < version,
            "Already initialized to this version"
        );
        _initialized = version;
        _initializing = true;
        _;
        _initializing = false;
    }

    // Called only once during V2 upgrade
    function initializeV2(address _feeCollector) public reinitializer(2) {
        feeCollector = _feeCollector;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }
}

// VULNERABLE: Multiple initialization without protection
contract VulnerableMultiInit {
    address public owner;
    address public treasury;
    address public governance;
    bool private initialized;

    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    // PROBLEM: Can be called independently, potentially after malicious upgrade
    function setTreasury(address _treasury) public {
        // No initialization check!
        treasury = _treasury;
    }

    function setGovernance(address _governance) public {
        // No initialization check!
        governance = _governance;
    }
}

// SAFE: Single initialization function with all parameters
contract SafeSingleInit {
    address public owner;
    address public treasury;
    address public governance;
    bool private initialized;

    function initialize(
        address _owner,
        address _treasury,
        address _governance
    ) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        treasury = _treasury;
        governance = _governance;
        initialized = true;
    }

    // Only owner can update after initialization
    function setTreasury(address _treasury) public {
        require(msg.sender == owner, "Not owner");
        require(initialized, "Not initialized");
        treasury = _treasury;
    }

    function setGovernance(address _governance) public {
        require(msg.sender == owner, "Not owner");
        require(initialized, "Not initialized");
        governance = _governance;
    }
}
