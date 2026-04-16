// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title StorageLayoutIncompatible
 * @dev Demonstrates storage layout incompatibility during upgrades
 *
 * When upgrading, if new implementation changes the order or types
 * of state variables, it can corrupt the proxy's storage causing critical failures
 * or security vulnerabilities.
 *
 * This is one of the most dangerous upgrade vulnerabilities as it can:
 * 1. Corrupt critical state (ownership, balances)
 * 2. Be difficult to detect
 * 3. Be irreversible once executed
 */

// V1: Original implementation
contract ImplementationV1 {
    address public owner;        // slot 0
    uint256 public totalSupply;  // slot 1
    mapping(address => uint256) public balances;  // slot 2
}

// VULNERABLE: V2 changes variable order
contract ImplementationV2Vulnerable_Reorder {
    uint256 public totalSupply;  // slot 0 - WAS slot 1!
    address public owner;        // slot 1 - WAS slot 0!
    mapping(address => uint256) public balances;  // slot 2

    // After upgrade:
    // - totalSupply reads owner address (cast to uint256)
    // - owner reads totalSupply (cast to address)
    // - This is catastrophic!
}

// VULNERABLE: V2 changes variable type
contract ImplementationV2Vulnerable_TypeChange {
    address public owner;        // slot 0
    address public totalSupply;  // slot 1 - WAS uint256!
    mapping(address => uint256) public balances;  // slot 2

    // After upgrade:
    // - totalSupply (now address) reads old uint256 value
    // - Can cause unexpected behavior
}

// VULNERABLE: V2 inserts variable in middle
contract ImplementationV2Vulnerable_Insert {
    address public owner;        // slot 0
    uint256 public newVariable;  // slot 1 - NEW!
    uint256 public totalSupply;  // slot 2 - WAS slot 1!
    mapping(address => uint256) public balances;  // slot 3 - WAS slot 2!

    // After upgrade:
    // - newVariable reads old totalSupply
    // - totalSupply reads old balances mapping slot
    // - All mappings are corrupted!
}

// VULNERABLE: V2 removes variable
contract ImplementationV2Vulnerable_Remove {
    address public owner;        // slot 0
    // totalSupply removed!
    mapping(address => uint256) public balances;  // slot 1 - WAS slot 2!

    // After upgrade:
    // - balances mapping now starts at slot 1 instead of 2
    // - All balance data is lost/corrupted!
}

// SAFE: V2 only appends new variables
contract ImplementationV2Safe_Append {
    address public owner;        // slot 0 - unchanged
    uint256 public totalSupply;  // slot 1 - unchanged
    mapping(address => uint256) public balances;  // slot 2 - unchanged
    address public feeCollector; // slot 3 - NEW, appended at end
    uint256 public feeRate;      // slot 4 - NEW, appended at end
}

// SAFE: Using storage gaps for future upgrades
contract ImplementationV1WithGap {
    address public owner;        // slot 0
    uint256 public totalSupply;  // slot 1
    mapping(address => uint256) public balances;  // slot 2

    // Reserve 50 slots for future variables
    uint256[50] private __gap;   // slots 3-52
}

// SAFE: V2 uses gap storage
contract ImplementationV2Safe_WithGap {
    address public owner;        // slot 0 - unchanged
    uint256 public totalSupply;  // slot 1 - unchanged
    mapping(address => uint256) public balances;  // slot 2 - unchanged

    // Use 2 slots from gap
    address public feeCollector; // slot 3 - from gap
    uint256 public feeRate;      // slot 4 - from gap

    // Reduce gap by 2
    uint256[48] private __gap;   // slots 5-52
}

// VULNERABLE: Inheritance order change
contract BaseA {
    uint256 public valueA;  // slot 0
}

contract BaseB {
    uint256 public valueB;  // slot 1
}

contract ImplementationV1Inherited is BaseA, BaseB {
    uint256 public ownValue;  // slot 2
}

// VULNERABLE: Changing inheritance order corrupts storage!
contract ImplementationV2Vulnerable_InheritanceChange is BaseB, BaseA {
    uint256 public ownValue;  // slots are now different!
    // BaseB.valueB is now in slot 0
    // BaseA.valueA is now in slot 1
    // Data is swapped!
}

// VULNERABLE: Struct modification
contract ImplementationWithStruct {
    struct User {
        address addr;   // slot n
        uint256 balance;  // slot n+1
    }

    mapping(address => User) public users;
}

contract ImplementationV2Vulnerable_StructChange {
    struct User {
        uint256 balance;  // slot n - WAS n+1!
        address addr;   // slot n+1 - WAS n!
        bool active;    // slot n+2 - NEW!
    }

    mapping(address => User) public users;
    // All user data is corrupted!
}

// SAFE: Add to struct end only
contract ImplementationV2Safe_StructAppend {
    struct User {
        address addr;   // slot n - unchanged
        uint256 balance;  // slot n+1 - unchanged
        bool active;    // slot n+2 - NEW, safe
    }

    mapping(address => User) public users;
}

// VULNERABLE: Namespaced storage collision
contract ImplementationWithNamespace {
    struct MainStorage {
        address owner;
        uint256 value;
    }

    // keccak256("main.storage") - 1
    bytes32 private constant MAIN_STORAGE_LOCATION = 0x1234567890123456789012345678901234567890123456789012345678901234;

    function _getMainStorage() private pure returns (MainStorage storage $) {
        assembly {
            $.slot := MAIN_STORAGE_LOCATION
        }
    }
}

contract ImplementationV2Vulnerable_NamespaceCollision {
    struct MainStorage {
        address owner;
        uint256 value;
        address newField;  // Added to struct
    }

    struct AnotherStorage {
        uint256 data;
    }

    // Same location!
    bytes32 private constant MAIN_STORAGE_LOCATION = 0x1234567890123456789012345678901234567890123456789012345678901234;
    // Different namespace but could collide with MAIN_STORAGE_LOCATION + n
    bytes32 private constant ANOTHER_STORAGE_LOCATION = 0x1235567890123456789012345678901234567890123456789012345678901234;

    // If ANOTHER_STORAGE_LOCATION overlaps with extended MainStorage, corruption!
}
