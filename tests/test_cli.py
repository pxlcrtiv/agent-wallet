"""CLI end-to-end tests — all offline via the fixtures:// RPC."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from agent_wallet.cli import EXIT_NO_KEY, EXIT_SAFETY, main
from agent_wallet.providers import FIXTURE_RECIPIENT, FIXTURE_USER

RUNNER = CliRunner()
TEST_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def test_plan_json_output():
    result = RUNNER.invoke(main, ["plan", FIXTURE_RECIPIENT, "--amount", "0.01", "--json"])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["chain_id"] == 11155111
    assert plan["unsigned_tx"]["type"] == "0x2"
    assert plan["signed"] is False
    assert plan["gas"] == 21_000


def test_plan_render_contains_risk_and_unsigned_note():
    result = RUNNER.invoke(main, ["plan", FIXTURE_RECIPIENT, "--amount", "0.25"])
    assert result.exit_code == 0
    assert "RISK NOTES" in result.output
    assert "UNSIGNED" in result.output
    assert "Sepolia" in result.output


def test_plan_token_transfer_json():
    result = RUNNER.invoke(
        main,
        ["plan", FIXTURE_RECIPIENT, "--amount", "12.5",
         "--token", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238", "--json"],
    )
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["amount_human"] == "12.5000 USDC"
    assert plan["unsigned_tx"]["data"].startswith("0xa9059cbb")


def test_inspect_shows_balances_and_allowances():
    result = RUNNER.invoke(main, ["inspect", FIXTURE_USER])
    assert result.exit_code == 0, result.output
    assert "balance" in result.output.lower()
    assert "USDC" in result.output
    assert "EXPOSED" in result.output


def test_chain_command_allows_testnet():
    result = RUNNER.invoke(main, ["chain"])
    assert result.exit_code == 0
    assert "allowed" in result.output


def test_sign_refuses_mainnet_plan(tmp_path):
    plan = {
        "chain_id": 1, "network": "Ethereum Mainnet", "from": FIXTURE_USER,
        "to": FIXTURE_RECIPIENT, "value_human": "0.01 ETH", "fee_human": "0.0001 ETH",
        "unsigned_tx": {"from": FIXTURE_USER, "to": FIXTURE_RECIPIENT, "value": 1,
                        "gas": 21000, "maxFeePerGas": 2 * 10**9, "type": "0x2",
                        "chainId": 1, "nonce": 0, "data": "0x"},
    }
    path = tmp_path / "mainnet.json"
    path.write_text(json.dumps(plan))
    result = RUNNER.invoke(main, ["sign", str(path), "--keyfile", "/dev/null"])
    assert result.exit_code == EXIT_SAFETY
    assert "MAINNET LOCKED" in result.output


def test_sign_without_key_exits_no_key(tmp_path):
    plan = {
        "chain_id": 11155111, "network": "Sepolia", "from": FIXTURE_USER,
        "to": FIXTURE_RECIPIENT, "value_human": "0.01 ETH", "fee_human": "0.0001 ETH",
        "unsigned_tx": {"from": FIXTURE_USER, "to": FIXTURE_RECIPIENT, "value": 1,
                        "gas": 21000, "maxFeePerGas": 2 * 10**9, "type": "0x2",
                        "chainId": 11155111, "nonce": 0, "data": "0x"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    result = RUNNER.invoke(main, ["--rpc", "fixtures://", "sign", str(path)])
    assert result.exit_code == EXIT_NO_KEY
    assert "no private key" in result.output


def test_sign_full_flow_produces_raw_tx(tmp_path, monkeypatch):
    keyfile = tmp_path / "key.txt"
    keyfile.write_text(TEST_KEY)
    plan = {
        "chain_id": 11155111, "network": "Ethereum Sepolia (testnet)",
        "from": FIXTURE_USER, "to": FIXTURE_RECIPIENT,
        "value_human": "0.010000 ETH", "fee_human": "0.000042 ETH",
        "risk_notes": ["test"], "dry_run": {"ok": True, "reverted": False},
        "unsigned_tx": {"from": FIXTURE_USER, "to": FIXTURE_RECIPIENT,
                        "value": 10**16, "gas": 21000,
                        "maxFeePerGas": 2 * 10**9, "maxPriorityFeePerGas": 10**9,
                        "type": "0x2", "chainId": 11155111, "nonce": 7, "data": "0x"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr("builtins.input", lambda _prompt="": "sign")
    result = RUNNER.invoke(main, ["--rpc", "fixtures://", "sign", str(path), "--keyfile", str(keyfile)])
    assert result.exit_code == 0, result.output
    assert "signed tx" in result.output
    assert "raw tx     02f8" in result.output  # EIP-1559 envelope (0x02 + RLP)
    assert "not broadcast" in result.output


def test_sign_aborts_without_confirmation(tmp_path, monkeypatch):
    keyfile = tmp_path / "key.txt"
    keyfile.write_text(TEST_KEY)
    plan = {
        "chain_id": 11155111, "network": "Sepolia", "from": FIXTURE_USER,
        "to": FIXTURE_RECIPIENT, "value_human": "0.01 ETH", "fee_human": "0.0001 ETH",
        "risk_notes": [], "dry_run": {"ok": True, "reverted": False},
        "unsigned_tx": {"from": FIXTURE_USER, "to": FIXTURE_RECIPIENT, "value": 1,
                        "gas": 21000, "maxFeePerGas": 2 * 10**9, "type": "0x2",
                        "chainId": 11155111, "nonce": 0, "data": "0x"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr("builtins.input", lambda _prompt="": "nope")
    result = RUNNER.invoke(main, ["--rpc", "fixtures://", "sign", str(path), "--keyfile", str(keyfile)])
    assert result.exit_code == 1
    assert "aborted" in result.output
    assert "signed tx" not in result.output


def test_sign_detects_chain_mismatch_between_plan_and_rpc(tmp_path, monkeypatch):
    keyfile = tmp_path / "key.txt"
    keyfile.write_text(TEST_KEY)
    plan = {
        "chain_id": 31337, "network": "anvil local chain (testnet)", "from": FIXTURE_USER,
        "to": FIXTURE_RECIPIENT, "value_human": "0.01 ETH", "fee_human": "0.0001 ETH",
        "risk_notes": [], "dry_run": {"ok": True, "reverted": False},
        "unsigned_tx": {"from": FIXTURE_USER, "to": FIXTURE_RECIPIENT, "value": 1,
                        "gas": 21000, "maxFeePerGas": 2 * 10**9, "type": "0x2",
                        "chainId": 31337, "nonce": 0, "data": "0x"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr("builtins.input", lambda _prompt="": "sign")
    # plan says anvil (31337) but fixtures RPC is Sepolia (11155111) -> refuse
    result = RUNNER.invoke(main, ["--rpc", "fixtures://", "sign", str(path), "--keyfile", str(keyfile)])
    assert result.exit_code == EXIT_SAFETY
    assert "Refusing to sign" in result.output


def test_chat_shows_agent_steps():
    result = RUNNER.invoke(main, ["chat", "balance of 0x1111111111111111111111111111111111111111"])
    assert result.exit_code == 0
    assert "[tool_call]" in result.output
    assert "get_balances" in result.output
    assert "1.0000 ETH" in result.output


def test_chat_help_lists_commands():
    result = RUNNER.invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in ("plan", "inspect", "sign", "chat", "chain"):
        assert cmd in result.output