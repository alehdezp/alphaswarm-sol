// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TestDiamondProxy
 * @notice Test contract for EIP-2535 Diamond Proxy pattern detection.
 * @dev Implements core Diamond functionality: facet routing and management.
 */
contract TestDiamondProxy {
    // Facet cut actions
    enum FacetCutAction { Add, Replace, Remove }

    // Facet cut struct for diamondCut
    struct FacetCut {
        address facetAddress;
        FacetCutAction action;
        bytes4[] functionSelectors;
    }

    // Facet info for loupe
    struct Facet {
        address facetAddress;
        bytes4[] functionSelectors;
    }

    // Storage for selector -> facet mapping
    mapping(bytes4 => address) internal _selectorToFacet;

    // Array of facet addresses for enumeration
    address[] internal _facetAddresses;

    // Mapping to track selectors per facet
    mapping(address => bytes4[]) internal _facetSelectors;

    // Owner for access control
    address public owner;

    event DiamondCut(FacetCut[] _diamondCut, address _init, bytes _calldata);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /**
     * @notice Add/replace/remove facets and optionally call init function.
     * @param _diamondCut Array of facet cuts
     * @param _init Address to call after cuts (address(0) for none)
     * @param _calldata Data to call _init with
     */
    function diamondCut(
        FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata
    ) external onlyOwner {
        for (uint256 i = 0; i < _diamondCut.length; i++) {
            FacetCutAction action = _diamondCut[i].action;
            address facet = _diamondCut[i].facetAddress;
            bytes4[] memory selectors = _diamondCut[i].functionSelectors;

            if (action == FacetCutAction.Add) {
                _addFacet(facet, selectors);
            } else if (action == FacetCutAction.Replace) {
                _replaceFacet(facet, selectors);
            } else if (action == FacetCutAction.Remove) {
                _removeFacet(selectors);
            }
        }

        emit DiamondCut(_diamondCut, _init, _calldata);

        if (_init != address(0)) {
            (bool success,) = _init.delegatecall(_calldata);
            require(success, "Init failed");
        }
    }

    /**
     * @notice Get all facet addresses.
     * @return addresses Array of facet contract addresses
     */
    function facetAddresses() external view returns (address[] memory addresses) {
        return _facetAddresses;
    }

    /**
     * @notice Get function selectors for a facet.
     * @param _facet Address of the facet
     * @return selectors Array of function selectors
     */
    function facetFunctionSelectors(address _facet) external view returns (bytes4[] memory selectors) {
        return _facetSelectors[_facet];
    }

    /**
     * @notice Get facet address for a selector.
     * @param _selector The function selector
     * @return facetAddress_ The facet address
     */
    function facetAddress(bytes4 _selector) external view returns (address facetAddress_) {
        return _selectorToFacet[_selector];
    }

    /**
     * @notice Get all facets with their selectors.
     * @return facets_ Array of Facet structs
     */
    function facets() external view returns (Facet[] memory facets_) {
        facets_ = new Facet[](_facetAddresses.length);
        for (uint256 i = 0; i < _facetAddresses.length; i++) {
            facets_[i].facetAddress = _facetAddresses[i];
            facets_[i].functionSelectors = _facetSelectors[_facetAddresses[i]];
        }
    }

    /**
     * @dev Internal: add a new facet with selectors.
     */
    function _addFacet(address _facet, bytes4[] memory _selectors) internal {
        require(_facet != address(0), "Zero address");
        require(_selectors.length > 0, "No selectors");

        bool isNewFacet = _facetSelectors[_facet].length == 0;
        if (isNewFacet) {
            _facetAddresses.push(_facet);
        }

        for (uint256 i = 0; i < _selectors.length; i++) {
            bytes4 selector = _selectors[i];
            require(_selectorToFacet[selector] == address(0), "Selector exists");
            _selectorToFacet[selector] = _facet;
            _facetSelectors[_facet].push(selector);
        }
    }

    /**
     * @dev Internal: replace selectors with new facet.
     */
    function _replaceFacet(address _facet, bytes4[] memory _selectors) internal {
        require(_facet != address(0), "Zero address");
        require(_selectors.length > 0, "No selectors");

        bool isNewFacet = _facetSelectors[_facet].length == 0;
        if (isNewFacet) {
            _facetAddresses.push(_facet);
        }

        for (uint256 i = 0; i < _selectors.length; i++) {
            bytes4 selector = _selectors[i];
            address oldFacet = _selectorToFacet[selector];
            require(oldFacet != address(0), "Selector not found");
            require(oldFacet != _facet, "Same facet");

            _selectorToFacet[selector] = _facet;
            _facetSelectors[_facet].push(selector);
            // Note: not removing from old facet's array for simplicity
        }
    }

    /**
     * @dev Internal: remove selectors.
     */
    function _removeFacet(bytes4[] memory _selectors) internal {
        for (uint256 i = 0; i < _selectors.length; i++) {
            bytes4 selector = _selectors[i];
            require(_selectorToFacet[selector] != address(0), "Selector not found");
            delete _selectorToFacet[selector];
        }
    }

    /**
     * @dev Fallback routes calls to appropriate facet.
     */
    fallback() external payable {
        address facet = _selectorToFacet[msg.sig];
        require(facet != address(0), "Diamond: Function does not exist");

        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), facet, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}

/**
 * @title TestFacet1
 * @notice Example facet for testing Diamond pattern.
 */
contract TestFacet1 {
    uint256 internal _value;

    function setValue(uint256 val) external {
        _value = val;
    }

    function getValue() external view returns (uint256) {
        return _value;
    }
}

/**
 * @title TestFacet2
 * @notice Another example facet for testing Diamond pattern.
 */
contract TestFacet2 {
    event MessageSent(string message);

    function sendMessage(string calldata message) external {
        emit MessageSent(message);
    }
}
