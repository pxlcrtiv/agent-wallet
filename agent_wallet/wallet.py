"""WalletService: read-only wallet intel over a Web3 connection.

Everything here is a read or a local computation — no transaction is ever
built or signed in this module.  Methods return plain dicts so they can be
fed straight into agent-lab tools and the CLI renderers.
"""

from __future__ import annotations

from web3 import Web3

from .config import ERC20_ABI, KNOWN_TOKENS
from .providers import parse_revert
from .safety import ensure_testnet


class WalletService:
    def __init__(self, w3: Web3, owner: str | None = None) -> None:
        self.w3 = w3
        self.owner = Web3.to_checksum_address(owner) if owner else None

    # -- chain ----------------------------------------------------------------

    def chain_id(self) -> int:
        return int(self.w3.eth.chain_id)

    def describe_network(self) -> dict:
        cid = self.chain_id()
        from .config import CHAIN_NAMES

        return {
            "chain_id": cid,
            "name": CHAIN_NAMES.get(cid, "unknown chain"),
            "allowed": cid in CHAIN_NAMES,
            "mainnet": cid == 1,
        }

    # -- balances --------------------------------------------------------------

    def get_balance(self, address: str) -> int:
        return int(self.w3.eth.get_balance(Web3.to_checksum_address(address)))

    def get_balances(self, address: str | None = None) -> dict:
        addr = self._owner_or(address)
        native = self.get_balance(addr)
        tokens = []
        for token_addr, meta in KNOWN_TOKENS.items():
            try:
                raw = self.token_balance(addr, token_addr)
                tokens.append(
                    {
                        "address": Web3.to_checksum_address(token_addr),
                        "symbol": meta["symbol"],
                        "name": meta["name"],
                        "raw": raw,
                        "decimals": self.token_decimals(token_addr),
                    }
                )
            except Exception:
                continue  # a flaky token read must not sink the balance sheet
        return {
            "address": addr,
            "native_wei": native,
            "native_eth": float(Web3.from_wei(native, "ether")),
            "tokens": tokens,
        }

    def token_balance(self, address: str, token: str) -> int:
        token_c = Web3.to_checksum_address(token)
        contract = self.w3.eth.contract(address=token_c, abi=ERC20_ABI)
        return int(contract.functions.balanceOf(Web3.to_checksum_address(address)).call())

    def token_decimals(self, token: str) -> int:
        token_c = Web3.to_checksum_address(token)
        contract = self.w3.eth.contract(address=token_c, abi=ERC20_ABI)
        return int(contract.functions.decimals().call())

    def token_symbol(self, token: str) -> str:
        token_c = Web3.to_checksum_address(token)
        contract = self.w3.eth.contract(address=token_c, abi=ERC20_ABI)
        try:
            return str(contract.functions.symbol().call())
        except Exception:
            return Web3.to_checksum_address(token)[:8]

    # -- allowances -------------------------------------------------------------

    def get_allowance(self, owner: str, spender: str, token: str) -> int:
        """ERC-20 allowance owner -> spender on ``token`` (raw units)."""
        o = Web3.to_checksum_address(owner)
        s = Web3.to_checksum_address(spender)
        t = Web3.to_checksum_address(token)
        contract = self.w3.eth.contract(address=t, abi=ERC20_ABI)
        return int(contract.functions.allowance(o, s).call())

    def check_allowance(self, owner: str | None = None, spender: str | None = None, token: str | None = None) -> dict:
        """Allowance snapshot for the owner, for every known token against a
        spender, or a single (token, spender) pair."""
        owner_a = self._owner_or(owner)
        if token:
            token = Web3.to_checksum_address(token)
            spender_a = self._spender_or(spender)
            raw = self.get_allowance(owner_a, spender_a, token)
            meta = KNOWN_TOKENS.get(token.lower(), {"symbol": token[:8], "name": "unknown token"})
            return {
                "owner": owner_a,
                "spender": spender_a,
                "token": token,
                "symbol": meta["symbol"],
                "raw": raw,
                "decimals": 6,
                "human": raw / 10**6,
                "exposure_note": (
                    "%s approved %s %s to %s" % (owner_a[:10], meta["symbol"], raw / 10**6, spender_a[:10])
                    if raw > 0
                    else "no allowance found"
                ),
            }
        # spender defaults: the infamous infinite-approval drainers / common
        # DeFi routers are not present on testnets; just use a generic marker.
        spender_a = self._spender_or(spender)
        out = []
        for token_addr, meta in KNOWN_TOKENS.items():
            try:
                raw = self.get_allowance(owner_a, spender_a, token_addr)
                out.append(
                    {
                        "token": Web3.to_checksum_address(token_addr),
                        "symbol": meta["symbol"],
                        "spender": spender_a,
                        "raw": raw,
                        "human": raw / 10**6,
                        "exposed": raw > 0,
                    }
                )
            except Exception:
                continue
        return {"owner": owner_a, "spender": spender_a, "allowances": out}

    # -- nonce -------------------------------------------------------------------

    def get_nonce(self, address: str | None = None) -> int:
        return int(self.w3.eth.get_transaction_count(self._owner_or(address)))

    # -- gas ----------------------------------------------------------------------

    def suggest_fees(self) -> dict:
        """EIP-1559 fee suggestion: base fee from feeHistory, priority capped."""
        cid = self.chain_id()
        try:
            base_fee = self._base_fee()
            priority = min(self.w3.eth.max_priority_fee, 3_000_000_000)
        except Exception:
            base = int(self.w3.eth.gas_price)
            base_fee = base // 2
            priority = min(base // 10, 3_000_000_000)
        max_fee = base_fee + priority
        return {
            "chain_id": cid,
            "base_fee_wei": base_fee,
            "max_priority_fee_per_gas_wei": priority,
            "max_fee_per_gas_wei": max_fee,
            "max_fee_per_gas_gwei": max_fee / 1e9,
            "supports_1559": True,
        }

    def _base_fee(self) -> int:
        latest = self.w3.eth.get_block("latest")
        if "baseFeePerGas" in latest and latest["baseFeePerGas"] is not None:
            return int(latest["baseFeePerGas"])
        hist = self.w3.eth.fee_history(1, "latest", [])
        return int(hist["baseFeePerGas"][-1])

    def estimate_gas(self, tx: dict) -> int:
        return int(self.w3.eth.estimate_gas(tx))

    # -- dry run ------------------------------------------------------------------

    def dry_run(self, tx: dict) -> dict:
        """Simulate ``tx`` with eth_call from the owner.  Never sends anything.

        Returns a verdict dict; a revert is reported (with a decoded reason
        when possible) instead of raising, so callers can explain it.
        """
        try:
            result = self.w3.eth.call(tx)
            return {"ok": True, "reverted": False, "reason": None, "return_hex": result.hex() if isinstance(result, bytes) else str(result)}
        except Exception as exc:  # node errors carry the revert payload
            reason = None
            first = exc.args[0] if exc.args else None
            if isinstance(first, dict):
                # JSON-RPC error response: {"error": {"data": ...}} or bare
                err = first.get("error") if isinstance(first.get("error"), dict) else first
                data = err.get("data")
                if data:
                    reason = parse_revert(str(data))
                if reason is None and err.get("message"):
                    reason = str(err["message"])
            if reason is None and getattr(exc, "data", None):
                reason = parse_revert(str(exc.data))
            if reason is None:
                message = str(first) if first is not None else str(exc)
                # web3 appends "execution reverted: <reason>" to the message
                marker = "execution reverted: "
                if marker in message:
                    reason = message.split(marker, 1)[1].strip()
                else:
                    reason = message[:200]
            return {"ok": False, "reverted": True, "reason": reason, "return_hex": None}

    def has_code(self, address: str) -> bool:
        code = self.w3.eth.get_code(Web3.to_checksum_address(address))
        return code not in (b"", b"0x", "0x") and len(code) > 2 if not isinstance(code, str) else code != "0x"

    # -- helpers ------------------------------------------------------------------

    def _owner_or(self, address: str | None) -> str:
        if address:
            return Web3.to_checksum_address(address)
        if self.owner is None:
            raise ValueError("no address given and no owner configured")
        return self.owner

    def _spender_or(self, spender: str | None) -> str:
        if spender:
            return Web3.to_checksum_address(spender)
        return Web3.to_checksum_address("0x8888888888888888888888888888888888888888")

    def ensure_testnet(self) -> dict:
        """Hard guard: refuse any chain that is not in the allow-list."""
        info = self.describe_network()
        ensure_testnet(info["chain_id"])
        return info