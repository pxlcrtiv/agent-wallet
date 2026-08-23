"""agent-wallet: an AI agent for safe testnet transactions.

Inspects a wallet, checks allowances, dry-runs a transaction, and explains
risk in plain English before anything is signed.  Sepolia only —
mainnet is default-off and every code path guards against it.
"""

__version__ = "0.1.0"

from .config import ALLOWED_CHAIN_IDS, DEFAULT_RPC, SEPOLIA_CHAIN_ID  # noqa: F401
from .safety import SafetyError, chain_is_allowed, ensure_testnet  # noqa: F401
from .wallet import WalletService  # noqa: F401