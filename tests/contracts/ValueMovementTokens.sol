// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IERC721 {
    function safeTransferFrom(address from, address to, uint256 tokenId) external;
}

interface IERC721Mint {
    function safeMint(address to, uint256 tokenId) external;
}

interface IERC1155 {
    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) external;
}

interface IERC1155Mint {
    function mint(address to, uint256 id, uint256 amount, bytes calldata data) external;
    function mintBatch(address to, uint256[] calldata ids, uint256[] calldata amounts, bytes calldata data) external;
}

interface IERC777 {
    function send(address to, uint256 amount, bytes calldata data) external;
}

interface IERC4626 {
    function deposit(uint256 assets, address receiver) external returns (uint256);
    function withdraw(uint256 assets, address receiver, address owner) external returns (uint256);
}

contract TokenCallbackSurface {
    IERC721 public nft;
    IERC721Mint public nftMinter;
    IERC1155 public items;
    IERC1155Mint public itemsMinter;
    IERC777 public token777;
    IERC4626 public vault;
    uint256 public counter;

    constructor(
        IERC721 _nft,
        IERC721Mint _nftMinter,
        IERC1155 _items,
        IERC1155Mint _itemsMinter,
        IERC777 _token777,
        IERC4626 _vault
    ) {
        nft = _nft;
        nftMinter = _nftMinter;
        items = _items;
        itemsMinter = _itemsMinter;
        token777 = _token777;
        vault = _vault;
    }

    function sendNft(address to, uint256 tokenId) external {
        nft.safeTransferFrom(msg.sender, to, tokenId);
        counter += 1;
    }

    function sendItems(address to, uint256[] calldata ids, uint256[] calldata amounts) external {
        items.safeBatchTransferFrom(msg.sender, to, ids, amounts, "");
        counter += 1;
    }

    function mintNft(address to, uint256 tokenId) external {
        nftMinter.safeMint(to, tokenId);
        counter += 1;
    }

    function mintItems(address to, uint256 id, uint256 amount) external {
        itemsMinter.mint(to, id, amount, "");
        counter += 1;
    }

    function mintBatchItems(address to, uint256[] calldata ids, uint256[] calldata amounts) external {
        itemsMinter.mintBatch(to, ids, amounts, "");
        counter += 1;
    }

    function send777(address to, uint256 amount) external {
        token777.send(to, amount, "");
        counter += 1;
    }

    function vaultDeposit(uint256 assets) external {
        vault.deposit(assets, msg.sender);
        counter += 1;
    }
}

contract TokenSafetyIssues {
    function unsafeTransfer(address token, address to, uint256 amount) external {
        IERC20(token).transfer(to, amount);
    }

    function safeTransfer(address token, address to, uint256 amount) external {
        require(IERC20(token).transfer(to, amount), "transfer failed");
    }

    function customGuardTransfer(address token, address to, uint256 amount) external {
        if (!IERC20(token).transfer(to, amount)) {
            revert("transfer failed");
        }
    }

    function approveSpender(address token, address spender, uint256 amount) external {
        IERC20(token).approve(spender, amount);
    }

    function feeOnTransferDeposit(address token, uint256 amount) external {
        IERC20(token).transferFrom(msg.sender, address(this), amount);
    }
}

contract DirectBalanceAccounting {
    IERC20 public token;
    uint256 public lastSpot;

    constructor(IERC20 _token) {
        token = _token;
    }

    function spotPrice() external view returns (uint256) {
        return token.balanceOf(address(this));
    }

    function recordSpot() external {
        lastSpot = token.balanceOf(address(this));
    }
}

contract ShareInflationVault {
    uint256 public totalShares;

    function deposit(uint256 amount) external {
        uint256 shares = amount + totalShares;
        totalShares = shares;
    }
}

contract SupplyAccountingToken {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    function mint(address to, uint256 amount) external {
        balances[to] += amount;
    }

    function burn(address from, uint256 amount) external {
        balances[from] -= amount;
    }
}
