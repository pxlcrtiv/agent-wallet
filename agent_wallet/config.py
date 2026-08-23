"""Network configuration and constants.

Safety rule #0 lives here: only a tiny allow-list of testnet/local chain ids
is ever accepted.  Mainnet (chain id 1) is not on it and never will be.
"""

from __future__ import annotations

# --- chains -----------------------------------------------------------------

MAINNET_CHAIN_ID = 1
SEPOLIA_CHAIN_ID = 11155111
ANVIL_CHAIN_ID = 31337

# Chains agent-wallet will operate on.  Everything else is refused.
# 11155111 = Ethereum Sepolia (public testnet, fake money)
# 31337    = anvil / Hardhat local chain (foundry dev server)
ALLOWED_CHAIN_IDS = frozenset({SEPOLIA_CHAIN_ID, ANVIL_CHAIN_ID})

CHAIN_NAMES = {
    MAINNET_CHAIN_ID: "Ethereum Mainnet",
    SEPOLIA_CHAIN_ID: "Ethereum Sepolia (testnet)",
    ANVIL_CHAIN_ID: "anvil local chain (testnet)",
}

DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
ANVIL_RPC = "http://127.0.0.1:8545"

# --- tokens (Sepolia, widely used community deployments) ----------------------
# These are convenience labels only.  the risk summary always reminds the user
# to verify token addresses themselves before sending anything of value.
KNOWN_TOKENS: dict[str, dict] = {
    # keys are lowercase on purpose: lookups normalize with .lower()
    "0x1c7d4b196cb0c7b01d743fbc6116a902379c7238": {
        "symbol": "USDC",
        "name": "USD Coin (Sepolia community deployment)",
    },
    "0xaa8e23fb1079ea71e0a56f02a2aa36d7a4c3a637": {
        "symbol": "USDT",
        "name": "Tether USD (Sepolia community deployment)",
    },
    "0xfff9976782d46cc05630d1f6ebab18b2324d6b14": {
        "symbol": "WETH",
        "name": "Wrapped Ether (Sepolia)",
    },
    "0xff34b3d4aee8ddcd6f9afffb6fe49bd371b8a357": {
        "symbol": "DAI",
        "name": "DAI Stablecoin (Sepolia community deployment)",
    },
}

# Minimal ERC-20 ABI used for read-only checks (balance/allowance/decimals).
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# Faucet hints, printed by the --sign path when the wallet is underfunded.
FAUCETS = {
    "sepolia": [
        "https://sepoliafaucet.com",
        "https://faucets.chain.link/sepolia",
        "https://cloud.google.com/application/web3/faucet/ethereum/sepolia",
    ],
}

FEE_BUFFER_MULTIPLIER = 1.1  # estimated gas x1.1 headroom on the plan
MAX_PRIORITY_FEE_WEI = 3_000_000_000  # 3 gwei cap for suggested priority fee