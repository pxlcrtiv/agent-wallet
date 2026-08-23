"""RPC resolution and an in-memory fixture provider.

Two connection modes exist:

* a real RPC endpoint (http/https) — anvil http://127.0.0.1:8545 or the
  public Sepolia endpoint (https://ethereum-sepolia-rpc.publicnode.com);
* the special URI ``fixtures://`` — an in-memory provider that answers the
  RPC calls agent-wallet makes with deterministic fixture data.  Zero
  network, zero keys, zero funds: everything is demoable and testable
  offline with ``--rpc fixtures://``.
"""

from __future__ import annotations

import json
from typing import Any

from web3 import Web3
from web3.providers.base import BaseProvider

from .config import ANVIL_RPC, DEFAULT_RPC, SEPOLIA_CHAIN_ID

# Well-known test addresses used by the fixture provider:
# 0x1111...1111 is "the user's" wallet (rich in ETH, holds some USDC),
# 0x2222...2222 is a plain EOA recipient,
# 0x3333...3333 holds contract code (token / converter style contract),
# 0x8888...8888 is the USDC whitelabel holder with a large allowance out.
FIXTURE_USER = "0x1111111111111111111111111111111111111111"
FIXTURE_RECIPIENT = "0x2222222222222222222222222222222222222222"
FIXTURE_CONTRACT = "0x3333333333333333333333333333333333333333"
FIXTURE_SPENDER = "0x8888888888888888888888888888888888888888"

FIXTURE_USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
FIXTURE_USDT = "0xaA8E23Fb1079EA71e0a56F02a2aA36D7a4C3a637"

_H160 = "0x" + "00" * 20
_EMPTY_CODE = "0x"
_CONTRACT_CODE = "0x6080604052"  # anything non-empty reads as "has code"


def _hex_quantity(value: int) -> str:
    return hex(value)


class RpcError(Exception):
    """Raised by fixture handlers to simulate a JSON-RPC error response."""

    def __init__(self, code: int, message: str, data: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class FixturesProvider(BaseProvider):
    """Deterministic, in-memory JSON-RPC provider for offline demos/tests.

    Implements exactly the methods WalletService needs.  Values are
    hard-coded fixtures (see module docstring) so output is stable — the
    README transcript can be reproduced verbatim on any machine.
    """

    name = "fixtures"

    def __init__(
        self,
        chain_id: int = SEPOLIA_CHAIN_ID,
        user_balance_wei: int = 10**18,  # 1 ETH
        usdc_balance: int = 5_000_000_000,  # 5000 USDC (6 decimals)
        allowance_out: int = 1_000_000_000,  # 1000 USDC approved to spender
        nonce: int = 7,
        gas_estimate: int = 52_000,
        base_fee_gwei: int = 1,
    ) -> None:
        super().__init__()
        self.chain_id = chain_id
        self.user_balance_wei = user_balance_wei
        self.usdc_balance = usdc_balance
        self.allowance_out = allowance_out
        self.nonce = nonce
        self.gas_estimate = gas_estimate
        self.base_fee_wei = base_fee_gwei * 10**9

    # -- BaseProvider ---------------------------------------------------------

    def make_request(self, method: str, params: list) -> dict:
        try:
            handler = getattr(self, "_rpc_" + method, None)
            if handler is None:
                return {"jsonrpc": "2.0", "id": 1, "result": None}
            return {"jsonrpc": "2.0", "id": 1, "result": handler(params)}
        except RpcError as exc:
            error: dict = {"code": exc.code, "message": exc.message}
            if exc.data:
                error["data"] = exc.data
            return {"jsonrpc": "2.0", "id": 1, "error": error}

    def is_connected(self, show_traceback: bool = False) -> bool:
        return True

    # -- handlers -------------------------------------------------------------

    def _rpc_eth_chainId(self, params: list) -> str:
        return _hex_quantity(self.chain_id)

    def _rpc_eth_blockNumber(self, params: list) -> str:
        return _hex_quantity(6_500_000)

    def _rpc_eth_getBlockByNumber(self, params: list) -> dict:
        return {
            "number": _hex_quantity(6_500_000),
            "hash": "0x" + "ab" * 32,
            "parentHash": "0x" + "00" * 32,
            "nonce": "0x0000000000000000",
            "sha3Uncles": "0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",
            "logsBloom": "0x" + "00" * 256,
            "transactionsRoot": "0x" + "00" * 32,
            "stateRoot": "0x" + "00" * 32,
            "receiptsRoot": "0x" + "00" * 32,
            "miner": "0x0000000000000000000000000000000000000000",
            "difficulty": _hex_quantity(0),
            "totalDifficulty": _hex_quantity(0),
            "extraData": "0x",
            "size": _hex_quantity(1000),
            "gasLimit": _hex_quantity(30_000_000),
            "gasUsed": _hex_quantity(12_000_000),
            "timestamp": _hex_quantity(1_700_000_000),
            "transactions": [],
            "uncles": [],
            "baseFeePerGas": _hex_quantity(self.base_fee_wei),
        }

    def _rpc_eth_gasPrice(self, params: list) -> str:
        return _hex_quantity(self.base_fee_wei * 2)

    def _rpc_eth_maxPriorityFeePerGas(self, params: list) -> str:
        return _hex_quantity(min(2 * 10**9, self.base_fee_wei))

    def _rpc_eth_feeHistory(self, params: list) -> dict:
        count = int(params[0], 16) if isinstance(params[0], str) else int(params[0])
        base = [self.base_fee_wei] * (count + 1)
        return {
            "oldestBlock": _hex_quantity(6_490_000),
            "baseFeePerGas": [_hex_quantity(b) for b in base],
            "gasUsedRatio": [0.5] * count,
            "reward": [[_hex_quantity(10**9)] for _ in range(count)],
        }

    def _rpc_eth_getBalance(self, params: list) -> str:
        addr = str(params[0]).lower()
        if addr == FIXTURE_USER.lower():
            return _hex_quantity(self.user_balance_wei)
        if addr == FIXTURE_SPENDER.lower():
            return _hex_quantity(42 * 10**18)
        return _hex_quantity(0)

    def _rpc_eth_getTransactionCount(self, params: list) -> str:
        return _hex_quantity(self.nonce)

    def _rpc_eth_getCode(self, params: list) -> str:
        addr = str(params[0]).lower()
        if addr in (FIXTURE_CONTRACT.lower(), FIXTURE_USDC.lower(), FIXTURE_USDT.lower()):
            return _CONTRACT_CODE
        return _EMPTY_CODE

    def _rpc_eth_call(self, params: list) -> str:
        tx = params[0] if params else {}
        to = str(tx.get("to", "")).lower()
        data = str(tx.get("data") or "0x")
        selector = data[:10].lower() if len(data) >= 10 else ""
        padded = lambda v: f"{int(v):064x}"

        # balanceOf(address) -> 0x70a08231 (only the demo user holds USDC)
        if selector == "0x70a08231":
            owner_arg = data[10:74].rjust(64, "0")[-40:]
            owner_addr = "0x" + owner_arg
            has_funds = owner_addr == FIXTURE_USER.lower() and to == FIXTURE_USDC.lower()
            return "0x" + padded(self.usdc_balance if has_funds else 0)
        # allowance(address,address) -> 0xdd62ed3e (USDC has exposure)
        if selector == "0xdd62ed3e":
            return "0x" + padded(self.allowance_out if to == FIXTURE_USDC.lower() else 0)
        # decimals() -> 0x313ce567 (USDC/USDT 6; WETH/DAI 18)
        if selector == "0x313ce567":
            return "0x" + padded(6 if to in (FIXTURE_USDC.lower(), FIXTURE_USDT.lower()) else 18)
        # symbol() -> 0x95d89b41 (ABI string: offset, length, padded bytes)
        if selector == "0x95d89b41":
            sym = "USDC" if to == FIXTURE_USDC.lower() else "USDT"
            payload = sym.encode().hex()
            return "0x" + padded(32) + padded(len(sym)) + payload + "00" * (32 - (len(payload) // 2) % 32)
        # transfer(address,uint256) -> 0xa9059cbb : dry-run "succeeds"
        if selector == "0xa9059cbb":
            return "0x" + padded(1)
        # native sends with no data succeed; everything else reverts with
        # a recognizable reason so the dry-run path is exercised honestly.
        if tx.get("value", "0x0") != "0x0" or not data or data == "0x":
            return "0x"
        raise RpcError(3, "execution reverted", "0x" + self._encode_revert("fixture: simulated revert"))

    def _rpc_eth_estimateGas(self, params: list) -> str:
        tx = params[0] if params else {}
        data = str(tx.get("data") or "0x")
        # native sends cost 21k; token calldata ~52k; anything else 100k
        if data in ("0x", "") and tx.get("value", "0x0") != "0x0":
            return _hex_quantity(21_000)
        if data[:10].lower() == "0xa9059cbb":
            return _hex_quantity(self.gas_estimate)
        return _hex_quantity(100_000)

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _encode_revert(reason: str) -> str:
        """ABI-encode Error(string): selector + offset + length + padded data."""
        payload = reason.encode("utf-8")
        padded = payload.hex() + "00" * ((32 - len(payload) % 32) % 32)
        return "08c379a0" + "00" * 31 + "20" + f"{len(payload):064x}" + padded


def resolve_rpc(rpc: str | None = None) -> tuple[Web3, str]:
    """Build a Web3 instance and return (w3, mode) where mode is
    ``"fixtures"`` | ``"http"``.

    ``rpc=None`` -> public Sepolia endpoint; ``rpc="fixtures://"`` -> the
    in-memory provider; anything else is treated as an http(s) URL.
    """
    if rpc is None:
        rpc = DEFAULT_RPC
    if rpc == "fixtures://" or rpc == "fixtures":
        w3 = Web3(FixturesProvider())
        return w3, "fixtures"
    provider = Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20})
    w3 = Web3(provider)
    return w3, "http"


def connect(target: str | None = None) -> tuple[Web3, str]:
    """Alias used by the CLI: accepts a URL, fixtures://, or the shortcuts
    ``"anvil"`` (local anvil) and ``"sepolia"`` (public RPC)."""
    if target == "anvil":
        return resolve_rpc(ANVIL_RPC)
    if target == "sepolia":
        return resolve_rpc(DEFAULT_RPC)
    return resolve_rpc(target)


def parse_revert(revert_hex: str) -> str | None:
    """Try to decode an Error(string) revert payload to a readable reason."""
    if not isinstance(revert_hex, str) or not revert_hex.startswith("0x"):
        return None
    body = bytes.fromhex(revert_hex[2:])
    if len(body) > 4 and body[:4] == b"\x08\xc3y\xa0":
        try:
            # layout: selector(4) | offset(32) | length(32) | data(32..)
            offset = int.from_bytes(body[4:36], "big")
            length = int.from_bytes(body[36:68], "big")
            start = 36 + offset
            raw = body[start : start + length]
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None


def provider_fixture_state(w3: Web3) -> dict:
    """Snapshot of fixture values, for tests/docs."""
    prov = getattr(w3, "provider", None)
    if not isinstance(prov, FixturesProvider):
        return {}
    return {
        "chain_id": prov.chain_id,
        "user_balance_wei": prov.user_balance_wei,
        "usdc_balance": prov.usdc_balance,
        "allowance_out": prov.allowance_out,
        "nonce": prov.nonce,
        "gas_estimate": prov.gas_estimate,
        "base_fee_wei": prov.base_fee_wei,
    }


def dumps_clean(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)