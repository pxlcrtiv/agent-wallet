"""agent-lab tools: the wallet capabilities exposed to the agent loop.

Each tool is a plain typed function wrapped with agentlab's ``@tool``
decorator, so the JSON schema the LLM sees is derived from the signature
and docstring — definitions never drift from implementation.

The Web3 connection is bound at registry-build time via :func:`bind` (or
defaults to the offline ``fixtures://`` provider), so the tools stay pure
functions with clean schemas.  All tools return plain dicts and never
raise: failures come back as structured ``error`` fields the agent can
explain.
"""

from __future__ import annotations

from agentlab import tool
from web3 import Web3

from .providers import FIXTURE_RECIPIENT, FIXTURE_SPENDER, FIXTURE_USER, resolve_rpc
from .risk import human_amount, human_ether, risk_notes
from .txbuilder import UnsignedTxBuilder, erc20_transfer_data
from .wallet import WalletService

_DEFAULT_GAS = 21000

# Bound connection for the current process (CLI / tests / demo).
_bind: tuple = (None, None)


def bind(w3: Web3) -> None:
    """Point the tools at a live Web3 connection (thread-local enough for
    a CLI/demo process — there is at most one connection per run)."""
    global _bind
    _bind = (w3, None)


def _w3() -> Web3:
    w3, _ = _bind
    if w3 is None:
        w3, _ = resolve_rpc("fixtures://")  # offline default: fixtures
        bind(w3)
    return w3


def _svc() -> WalletService:
    svc = WalletService(_w3())
    svc.ensure_testnet()  # every tool is chain-guarded
    return svc


@tool
def get_balances(address: str | None = None) -> dict:
    """Read native ETH and known-test-token balances for a wallet.

    Args:
        address: wallet to inspect (defaults to the demo wallet).
    """
    svc = _svc()
    data = svc.get_balances(address or FIXTURE_USER)
    return {
        "address": data["address"],
        "native_eth": data["native_eth"],
        "native_wei": data["native_wei"],
        "tokens": [
            {"symbol": t["symbol"], "human": t["raw"] / 10 ** t["decimals"], "raw": t["raw"], "address": t["address"]}
            for t in data["tokens"]
        ],
    }


@tool
def check_allowance(
    owner: str | None = None,
    spender: str | None = None,
    token: str | None = None,
) -> dict:
    """Check ERC-20 approvals held by a wallet (exposure check).

    Args:
        owner: wallet that granted the approval (defaults to demo wallet).
        spender: address allowed to move tokens (defaults to a known fixture spender).
        token: token contract to check (defaults to all known tokens).
    """
    svc = _svc()
    return svc.check_allowance(owner or FIXTURE_USER, spender or FIXTURE_SPENDER, token)


@tool
def dry_run_tx(
    from_address: str = FIXTURE_USER,
    to_address: str = FIXTURE_RECIPIENT,
    value_eth: float = 0.01,
    data: str = "0x",
) -> dict:
    """Simulate a transaction with eth_call — never sends anything.

    Args:
        from_address: sender address for the simulation.
        to_address: recipient.
        value_eth: ETH value to send.
        data: optional calldata (e.g. an ERC-20 transfer).
    """
    svc = _svc()
    value_wei = int(Web3.to_wei(value_eth, "ether"))
    tx = {
        "from": Web3.to_checksum_address(from_address),
        "to": Web3.to_checksum_address(to_address),
        "value": value_wei,
        "data": data or "0x",
    }
    verdict = svc.dry_run(tx)
    return {"simulated": True, **verdict}


@tool
def plan_transfer(
    from_address: str = FIXTURE_USER,
    to_address: str = FIXTURE_RECIPIENT,
    amount_eth: float = 0.01,
    token: str | None = None,
) -> dict:
    """Full plan for a transfer: gas, fees, dry-run, risk notes, unsigned tx.

    Args:
        from_address: sender wallet.
        to_address: recipient.
        amount_eth: amount in ETH for native transfers; for token transfers
            this is the token amount in token units (e.g. USDC).
        token: ERC-20 token contract address (None = native ETH transfer).
    """
    svc = _svc()
    from_c = Web3.to_checksum_address(from_address)
    to_c = Web3.to_checksum_address(to_address)

    if token:
        token_c = Web3.to_checksum_address(token)
        decimals = svc.token_decimals(token_c)
        amount_raw = int(amount_eth * 10**decimals)
        data = erc20_transfer_data(to_c, amount_raw)
        value_wei = 0
        symbol = svc.token_symbol(token_c)
    else:
        token_c = None
        decimals = 18
        amount_raw = 0
        data = "0x"
        value_wei = int(Web3.to_wei(amount_eth, "ether"))
        symbol = "ETH"

    gas = svc.estimate_gas({"from": from_c, "to": token_c or to_c, "value": value_wei, "data": data}) or _DEFAULT_GAS
    fees = svc.suggest_fees()
    balance = svc.get_balance(from_c)

    builder = UnsignedTxBuilder(svc.w3)
    tx = builder.build(
        from_address=from_c,
        to_address=token_c or to_c,
        value_wei=value_wei,
        data=data,
        gas=gas,
        max_fee_per_gas=fees["max_fee_per_gas_wei"],
        max_priority_fee_per_gas=fees["max_priority_fee_per_gas_wei"],
    )
    dry = svc.dry_run({"from": from_c, "to": tx["to"], "value": value_wei, "data": data})

    from .config import CHAIN_NAMES

    cid = svc.chain_id()
    notes = risk_notes(
        chain_id=cid,
        from_address=from_c,
        to_address=to_c,
        value_wei=value_wei,
        token=token_c,
        gas=gas,
        max_fee_per_gas=fees["max_fee_per_gas_wei"],
        dry_run=dry,
        recipient_is_contract=svc.has_code(to_c),
        balance_wei=balance,
        token_balance_raw=amount_raw if token else None,
        token_decimals=decimals,
        symbol=symbol,
    )
    fee_wei = gas * fees["max_fee_per_gas_wei"]
    value_human = human_amount(amount_raw, decimals, symbol) if token else human_ether(value_wei)

    return {
        "network": CHAIN_NAMES.get(cid, "unknown chain %d" % cid),
        "chain_id": cid,
        "from": from_c,
        "to": to_c,
        "token": token_c,
        "amount_human": value_human,
        "value_wei": value_wei,
        "value_human": value_human,
        "gas": gas,
        "base_fee_gwei": fees["base_fee_wei"] / 1e9,
        "max_fee_per_gas_wei": fees["max_fee_per_gas_wei"],
        "max_priority_fee_per_gas_wei": fees["max_priority_fee_per_gas_wei"],
        "fee_wei": fee_wei,
        "fee_human": human_ether(fee_wei),
        "nonce": tx["nonce"],
        "tx_type": tx.get("type", "0x2"),
        "dry_run": dry,
        "risk_notes": notes,
        "unsigned_tx": tx,
        "signed": False,
    }


def wallet_tools() -> list:
    """The four wallet tools, ready to drop into a ToolRegistry."""
    return [
        get_balances,
        check_allowance,
        dry_run_tx,
        plan_transfer,
    ]