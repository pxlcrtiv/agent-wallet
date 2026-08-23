"""Providers/fixtures: deterministic offline RPC layer."""

from __future__ import annotations

from web3 import Web3

from agent_wallet.config import SEPOLIA_CHAIN_ID
from agent_wallet.providers import FixturesProvider, connect, parse_revert, resolve_rpc


def test_fixtures_provider_is_deterministic():
    a = FixturesProvider()
    b = FixturesProvider()
    w3a, w3b = Web3(a), Web3(b)
    assert w3a.eth.chain_id == w3b.eth.chain_id == SEPOLIA_CHAIN_ID
    assert w3a.eth.get_balance("0x1111111111111111111111111111111111111111") == 10**18


def test_fixtures_get_code_eoa_vs_contract(w3):
    assert w3.eth.get_code("0x1111111111111111111111111111111111111111") == b""
    assert len(w3.eth.get_code("0x3333333333333333333333333333333333333333")) > 0


def test_fixtures_fee_history_and_gas_price(w3):
    hist = w3.eth.fee_history(1, "latest", [])
    assert hist["baseFeePerGas"][0] == 10**9
    assert w3.eth.gas_price == 2 * 10**9


def test_parse_revert_decodes_error_string():
    # Build the exact Error(string) payload the fixture provider would emit
    # (bare hex; the RPC error path prefixes it with 0x).
    reason = "fixture: simulated revert"
    payload = FixturesProvider._encode_revert(reason)
    assert parse_revert("0x" + payload) == reason
    assert parse_revert(payload) is None  # bare hex (no 0x) is not valid input


def test_parse_revert_handles_garbage():
    assert parse_revert("0x1234") is None
    assert parse_revert("nonsense") is None
    assert parse_revert(None) is None


def test_resolve_rpc_fixtures_mode():
    w3, mode = resolve_rpc("fixtures://")
    assert mode == "fixtures"
    assert isinstance(w3.provider, FixturesProvider)


def test_resolve_rpc_defaults_to_sepolia_http():
    w3, mode = resolve_rpc(None)
    assert mode == "http"
    assert "publicnode.com" in w3.provider.endpoint_uri


def test_connect_shortcuts():
    w3, mode = connect("anvil")
    assert mode == "http" and "127.0.0.1:8545" in w3.provider.endpoint_uri
    w3b, modeb = connect("sepolia")
    assert modeb == "http" and "publicnode.com" in w3b.provider.endpoint_uri