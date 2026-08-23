"""agent-lab tools: schemas, plan generation, chain guards (offline)."""

from __future__ import annotations

from agentlab import ToolRegistry

from agent_wallet.providers import FIXTURE_RECIPIENT, FIXTURE_USER, FixturesProvider, resolve_rpc
from agent_wallet.safety import SafetyError
from agent_wallet.tools import (
    bind,
    check_allowance,
    dry_run_tx,
    get_balances,
    plan_transfer,
    wallet_tools,
)

USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"


def _setup():
    w3, _ = resolve_rpc("fixtures://")
    bind(w3)
    return w3


def test_tool_schemas_are_openai_style():
    _setup()
    registry = ToolRegistry(*wallet_tools())
    schemas = registry.schemas()
    names = {s["name"] for s in schemas}
    assert names == {"get_balances", "check_allowance", "dry_run_tx", "plan_transfer"}
    by_name = {s["name"]: s for s in schemas}
    plan_params = by_name["plan_transfer"]["parameters"]
    assert "to_address" in plan_params["properties"]
    assert "amount_eth" in plan_params["properties"]
    assert "risk" in by_name["plan_transfer"]["description"].lower() or "plan" in by_name["plan_transfer"]["description"].lower()


def test_registry_calls_tool_and_returns_ok():
    _setup()
    registry = ToolRegistry(*wallet_tools())
    res = registry.call("get_balances", {"address": FIXTURE_USER})
    assert res["ok"] is True
    assert res["result"]["native_eth"] == 1.0


def test_registry_unknown_tool_returns_error():
    _setup()
    registry = ToolRegistry(*wallet_tools())
    res = registry.call("hack_the_planet", {})
    assert res["ok"] is False
    assert "unknown tool" in res["error"]


def test_plan_transfer_native_includes_unsigned_tx():
    _setup()
    plan = plan_transfer(from_address=FIXTURE_USER, to_address=FIXTURE_RECIPIENT, amount_eth=0.05)
    assert plan["signed"] is False
    assert plan["value_wei"] == 50_000_000_000_000_000  # 0.05 ETH
    assert plan["gas"] == 21_000
    assert plan["chain_id"] == 11155111
    assert plan["unsigned_tx"]["type"] == "0x2"
    assert any("Dry-run (eth_call) succeeded" in n for n in plan["risk_notes"])


def test_plan_transfer_token_uses_symbol_and_decimals():
    _setup()
    plan = plan_transfer(from_address=FIXTURE_USER, to_address=FIXTURE_RECIPIENT, amount_eth=12.5, token=USDC)
    assert plan["token"] == USDC
    assert plan["amount_human"] == "12.5000 USDC"
    assert plan["unsigned_tx"]["to"] == USDC
    assert plan["unsigned_tx"]["data"].startswith("0xa9059cbb")
    assert any("known community deployment" in n for n in plan["risk_notes"])


def test_dry_run_tool_reports_success():
    _setup()
    result = dry_run_tx(from_address=FIXTURE_USER, to_address=FIXTURE_RECIPIENT, value_eth=0.01)
    assert result["simulated"] is True
    assert result["ok"] is True and result["reverted"] is False


def test_get_balances_tool_shape():
    _setup()
    result = get_balances(address=FIXTURE_USER)
    assert result["native_eth"] == 1.0
    assert any(t["symbol"] == "USDC" and t["human"] == 5000.0 for t in result["tokens"])


def test_check_allowance_tool_exposure():
    _setup()
    result = check_allowance(owner=FIXTURE_USER)
    assert result["spender"] is not None
    assert any(a["exposed"] for a in result["allowances"])


def test_plan_transfer_rejects_mainnet_fixture():
    w3, _ = resolve_rpc("fixtures://")
    assert isinstance(w3.provider, FixturesProvider)
    w3.provider.chain_id = 1  # simulate a mainnet connection
    bind(w3)
    try:
        plan_transfer(from_address=FIXTURE_USER, to_address=FIXTURE_RECIPIENT, amount_eth=0.01)
        raised = False
    except SafetyError:
        raised = True
    assert raised, "plan_transfer must refuse chain id 1"