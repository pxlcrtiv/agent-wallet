"""WalletService: balances, allowances, nonce, gas, dry-run (offline)."""

from __future__ import annotations

import pytest
from web3 import Web3

from agent_wallet.config import KNOWN_TOKENS, SEPOLIA_CHAIN_ID
from agent_wallet.providers import FIXTURE_SPENDER, FIXTURE_USER, FixturesProvider
from agent_wallet.wallet import WalletService


def test_get_balances_native_and_tokens(svc):
    data = svc.get_balances(FIXTURE_USER)
    assert data["address"] == Web3.to_checksum_address(FIXTURE_USER)
    assert data["native_wei"] == 10**18
    assert data["native_eth"] == 1.0
    symbols = {t["symbol"] for t in data["tokens"]}
    assert symbols == {"USDC", "USDT", "WETH", "DAI"}
    usdc = next(t for t in data["tokens"] if t["symbol"] == "USDC")
    assert usdc["raw"] == 5_000_000_000 and usdc["decimals"] == 6


def test_token_balance_unknown_wallet_is_zero(svc):
    assert svc.token_balance(FIXTURE_SPENDER, "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238") == 0


def test_check_allowance_exposes_usdc_approval(svc):
    result = svc.check_allowance(owner=FIXTURE_USER, spender=FIXTURE_SPENDER)
    assert result["spender"] == Web3.to_checksum_address(FIXTURE_SPENDER)
    exposed = [a for a in result["allowances"] if a["exposed"]]
    assert len(exposed) == 1 and exposed[0]["symbol"] == "USDC"
    assert exposed[0]["raw"] == 1_000_000_000
    assert exposed[0]["human"] == 1000.0


def test_single_token_allowance_has_exposure_note(svc):
    result = svc.check_allowance(owner=FIXTURE_USER, spender=FIXTURE_SPENDER, token="0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    assert result["raw"] == 1_000_000_000
    assert "1000.0" in result["exposure_note"]


def test_nonce(svc):
    assert svc.get_nonce(FIXTURE_USER) == 7


def test_suggest_fees_eip1559(svc):
    fees = svc.suggest_fees()
    assert fees["base_fee_wei"] == 10**9  # 1 gwei from fixture
    assert fees["max_priority_fee_per_gas_wei"] == 10**9
    assert fees["max_fee_per_gas_wei"] == 2 * 10**9
    assert fees["supports_1559"] is True


def test_dry_run_native_send_succeeds(svc):
    verd = svc.dry_run({"from": FIXTURE_USER, "to": FIXTURE_SPENDER, "value": 10**16, "data": "0x"})
    assert verd["ok"] is True and verd["reverted"] is False


def test_dry_run_revert_is_parsed(svc):
    # Call a function the fixture does not model -> simulated revert string.
    verd = svc.dry_run({"from": FIXTURE_USER, "to": FIXTURE_SPENDER, "value": 0, "data": "0x12345678"})
    assert verd["ok"] is False and verd["reverted"] is True
    assert "simulated revert" in verd["reason"]


def test_has_code_detects_contract_vs_eoa(svc):
    assert svc.has_code("0x3333333333333333333333333333333333333333") is True
    assert svc.has_code(FIXTURE_USER) is False


def test_chain_id_from_fixtures(w3):
    svc_ = WalletService(w3)
    assert svc_.chain_id() == SEPOLIA_CHAIN_ID
    info = svc_.describe_network()
    assert info["allowed"] is True and info["mainnet"] is False