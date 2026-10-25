"""Token amounts: one scale, one formatter, no hardcoded decimals."""

from __future__ import annotations

from agent_wallet.amounts import TokenAmount
from agent_wallet.providers import FIXTURE_SPENDER, FIXTURE_USDC, FIXTURE_USER, FIXTURE_WETH


def test_token_amount_scales_by_its_own_decimals():
    amount = TokenAmount(raw=1_000_000_000, decimals=6, symbol="USDC")
    assert amount.human == 1000.0
    assert amount.display == "1000.0000 USDC"


def test_token_amount_with_human_scales_into_raw_units():
    amount = TokenAmount(raw=0, decimals=18, symbol="WETH")
    scaled = amount.with_human(1.5)
    assert scaled.raw == 1_500_000_000_000_000_000
    assert scaled.human == 1.5
    assert scaled.symbol == "WETH" and scaled.decimals == 18


def test_token_amount_reads_decimals_from_the_chain(svc):
    amount = svc.token_amount(FIXTURE_WETH)
    assert amount.decimals == 18
    assert amount.symbol == "WETH"


def test_allowance_on_an_18_decimals_token_is_scaled_correctly(svc_with_weth_allowance):
    result = svc_with_weth_allowance.check_allowance(
        owner=FIXTURE_USER, spender=FIXTURE_SPENDER, token=FIXTURE_WETH
    )
    assert result["raw"] == 10**18
    assert result["decimals"] == 18
    assert result["human"] == 1.0
    assert result["display"] == "1.0000 WETH"
    assert "approved WETH 1.0 to" in result["exposure_note"]


def test_allowance_list_scales_an_18_decimals_token_correctly(svc_with_weth_allowance):
    result = svc_with_weth_allowance.check_allowance(owner=FIXTURE_USER, spender=FIXTURE_SPENDER)
    weth = next(a for a in result["allowances"] if a["symbol"] == "WETH")
    assert weth["decimals"] == 18
    assert weth["human"] == 1.0
    assert weth["exposed"] is True


def test_allowance_branches_carry_the_same_keys(svc):
    single = svc.check_allowance(owner=FIXTURE_USER, spender=FIXTURE_SPENDER, token=FIXTURE_USDC)
    listed = svc.check_allowance(owner=FIXTURE_USER, spender=FIXTURE_SPENDER)
    entry = next(a for a in listed["allowances"] if a["symbol"] == "USDC")
    token_keys = {"symbol", "raw", "decimals", "human", "display", "exposed"}
    assert token_keys <= set(entry)
    assert token_keys <= set(single)


def test_balances_carry_the_scaled_amount(svc):
    tokens = svc.get_balances(FIXTURE_USER)["tokens"]
    usdc = next(t for t in tokens if t["symbol"] == "USDC")
    weth = next(t for t in tokens if t["symbol"] == "WETH")
    assert usdc["decimals"] == 6 and usdc["human"] == 5000.0
    assert weth["decimals"] == 18 and weth["human"] == 0.0
