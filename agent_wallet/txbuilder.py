"""Unsigned typed-transaction builder.

Builds EIP-1559 (type 0x02) transactions — and falls back to legacy (0x00)
when the chain reports no base fee — with full type-awareness, so the
resulting JSON can be inspected before anything is signed.  ``sign`` is
deliberately NOT here: this module never touches a private key.

Also provides ERC-20 ``transfer(address,uint256)`` calldata construction.
"""

from __future__ import annotations

from web3 import Web3

TRANSFER_SELECTOR = "0xa9059cbb"


def erc20_transfer_data(to: str, amount_raw: int) -> str:
    """Build ERC-20 transfer calldata: selector + padded address + uint256."""
    to_c = Web3.to_checksum_address(to)
    fn = Web3.keccak(text="transfer(address,uint256)")[:4]
    payload = fn.hex() + to_c.lower()[2:].rjust(64, "0") + f"{int(amount_raw):064x}"
    return "0x" + payload


def decode_erc20_transfer_data(data: str) -> dict | None:
    """Best-effort decode of standard ERC-20 transfer calldata."""
    if not data or len(data) < 10 or data[:10].lower() != TRANSFER_SELECTOR:
        return None
    body = data[10:]
    if len(body) < 128:
        return None

    addr_hex = body[:64]
    amount_hex = body[64:128]
    return {
        "to": Web3.to_checksum_address("0x" + addr_hex[-40:]),
        "amount_raw": int(amount_hex, 16),
    }


class UnsignedTxBuilder:
    """Builds unsigned, typed transactions from a plan.

    Two flavors:

    * native transfer — ``to`` receives ``value`` ETH;
    * token transfer — ERC-20 ``transfer`` calldata to the token contract,
      amount expressed in token units (e.g. USDC's 6 decimals).
    """

    def __init__(self, w3: Web3, chain_id: int | None = None) -> None:
        self.w3 = w3
        self.chain_id = chain_id or int(w3.eth.chain_id)

    def supports_1559(self) -> bool:
        try:
            block = self.w3.eth.get_block("latest")
            return block.get("baseFeePerGas") is not None
        except Exception:
            return False

    def build(
        self,
        from_address: str,
        to_address: str,
        value_wei: int = 0,
        data: str = "0x",
        gas: int | None = None,
        max_fee_per_gas: int | None = None,
        max_priority_fee_per_gas: int | None = None,
        nonce: int | None = None,
        chain_id: int | None = None,
    ) -> dict:
        """Return the complete unsigned transaction as a JSON-able dict.

        No signing field is ever populated.  ``type`` is explicit so any
        tooling reading the JSON knows which gas model applies.
        """
        from_c = Web3.to_checksum_address(from_address)
        to_c = Web3.to_checksum_address(to_address or "0x" + "00" * 20)
        cid = chain_id or self.chain_id
        nonce = nonce if nonce is not None else int(self.w3.eth.get_transaction_count(from_c))
        gas_est = gas or self._estimate_gas(
            {"from": from_c, "to": to_c, "value": value_wei, "data": data or "0x"}
        )

        base = {
            "chainId": cid,
            "nonce": nonce,
            "from": from_c,
            "to": to_c,
            "value": value_wei,
            "data": data or "0x",
            "gas": gas_est,
        }
        if self.supports_1559():
            fees = self._fee_tips(max_fee_per_gas, max_priority_fee_per_gas)
            base.update(
                {
                    "type": "0x2",
                    "maxFeePerGas": fees["max_fee_per_gas"],
                    "maxPriorityFeePerGas": fees["max_priority_fee_per_gas"],
                }
            )
        else:
            base.update({"type": "0x0", "gasPrice": max_fee_per_gas or int(self.w3.eth.gas_price)})
        return base

    def _estimate_gas(self, tx: dict) -> int:
        return int(self.w3.eth.estimate_gas(tx))

    def _fee_tips(self, max_fee: int | None, priority: int | None) -> dict:
        if max_fee is None or priority is None:
            from .wallet import WalletService

            fees = WalletService(self.w3).suggest_fees()
            return {
                "max_fee_per_gas": max_fee or fees["max_fee_per_gas_wei"],
                "max_priority_fee_per_gas": priority or fees["max_priority_fee_per_gas_wei"],
            }
        return {"max_fee_per_gas": max_fee, "max_priority_fee_per_gas": priority}


def tx_to_signing_dict(tx: dict) -> dict:
    """Strip UI-only fields (``from`` is not part of the signed payload) and
    return the exact dict eth_account can sign."""
    out = {k: v for k, v in tx.items() if k != "from"}
    return out