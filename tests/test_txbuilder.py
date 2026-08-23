"""Tx builder: typed unsigned transactions + ERC-20 calldata (offline)."""

from __future__ import annotations

from web3 import Web3

from agent_wallet.providers import FIXTURE_USER
from agent_wallet.txbuilder import (
    UnsignedTxBuilder,
    decode_erc20_transfer_data,
    erc20_transfer_data,
    tx_to_signing_dict,
)

USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
RECIPIENT = "0x2222222222222222222222222222222222222222"


def test_build_eip1559_typed_tx(w3):
    builder = UnsignedTxBuilder(w3)
    tx = builder.build(from_address=FIXTURE_USER, to_address=RECIPIENT, value_wei=10**16)
    assert tx["type"] == "0x2"
    assert tx["chainId"] == 11155111
    assert tx["nonce"] == 7
    assert tx["gas"] == 21_000
    assert tx["maxFeePerGas"] == 2 * 10**9
    assert tx["maxPriorityFeePerGas"] == 10**9
    assert tx["value"] == 10**16
    assert tx["to"] == Web3.to_checksum_address(RECIPIENT)
    assert "v" not in tx and "r" not in tx and "s" not in tx  # unsigned!
    assert "from" in tx  # UI field kept for review


def test_build_legacy_when_chain_has_no_1559(w3_legacy):
    builder = UnsignedTxBuilder(w3_legacy)
    tx = builder.build(from_address=FIXTURE_USER, to_address=RECIPIENT, value_wei=10**16)
    assert tx["type"] == "0x0"
    assert "gasPrice" in tx
    assert "maxFeePerGas" not in tx


def test_build_respects_explicit_fees(w3):
    builder = UnsignedTxBuilder(w3)
    tx = builder.build(
        from_address=FIXTURE_USER, to_address=RECIPIENT, value_wei=0,
        max_fee_per_gas=5 * 10**9, max_priority_fee_per_gas=2 * 10**9,
    )
    assert tx["maxFeePerGas"] == 5 * 10**9
    assert tx["maxPriorityFeePerGas"] == 2 * 10**9


def test_erc20_transfer_data_format(w3):
    data = erc20_transfer_data(RECIPIENT, 12_500_000)  # 12.5 USDC (6 dp)
    assert data.startswith("0xa9059cbb")
    body = data[10:]
    assert body[:64].endswith(RECIPIENT.lower()[2:])  # padded address
    assert body[64:] == f"{12_500_000:064x}"  # padded amount


def test_erc20_transfer_data_roundtrip():
    data = erc20_transfer_data(RECIPIENT, 999)
    decoded = decode_erc20_transfer_data(data)
    assert decoded is not None
    assert decoded["to"] == Web3.to_checksum_address(RECIPIENT)
    assert decoded["amount_raw"] == 999


def test_decode_rejects_garbage():
    assert decode_erc20_transfer_data("0x1234") is None
    assert decode_erc20_transfer_data("0xdeadbeef") is None


def test_tx_to_signing_dict_strips_from_only():
    tx = {"from": FIXTURE_USER, "to": RECIPIENT, "value": 1, "type": "0x2", "chainId": 1}
    signable = tx_to_signing_dict(tx)
    assert "from" not in signable
    assert signable["to"] == RECIPIENT and signable["type"] == "0x2"