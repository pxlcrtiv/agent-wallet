"""Safety guards: the no-mainnet, testnet-only wall."""

from __future__ import annotations

import pytest

from agent_wallet.config import ANVIL_CHAIN_ID, SEPOLIA_CHAIN_ID
from agent_wallet.safety import (
    AGENT_SYSTEM_PROMPT,
    SafetyError,
    chain_is_allowed,
    ensure_testnet,
    sign_confirmation_prompt,
)


def test_chain_is_allowed_sepolia_and_anvil():
    assert chain_is_allowed(SEPOLIA_CHAIN_ID)
    assert chain_is_allowed(ANVIL_CHAIN_ID)


def test_chain_is_allowed_rejects_mainnet_and_unknown():
    assert not chain_is_allowed(1)
    assert not chain_is_allowed(10)  # Optimism
    assert not chain_is_allowed(8453)  # Base


def test_ensure_testnet_accepts_allowed_chains():
    ensure_testnet(SEPOLIA_CHAIN_ID)  # must not raise
    ensure_testnet(ANVIL_CHAIN_ID)


def test_ensure_testnet_blocks_mainnet_with_loud_message():
    with pytest.raises(SafetyError) as exc:
        ensure_testnet(1)
    assert "MAINNET LOCKED" in str(exc.value)
    assert "testnet" in str(exc.value).lower()


def test_ensure_testnet_blocks_unknown_chain():
    with pytest.raises(SafetyError):
        ensure_testnet(9999)


def test_system_prompt_forbids_mainnet_and_requires_explanation():
    assert "never propose" in AGENT_SYSTEM_PROMPT.lower()
    assert "mainnet" in AGENT_SYSTEM_PROMPT.lower()
    assert "unsigned" in AGENT_SYSTEM_PROMPT.lower()
    assert "risk" in AGENT_SYSTEM_PROMPT.lower()
    assert "dry-run" in AGENT_SYSTEM_PROMPT.lower()


def test_sign_prompt_shows_plan_facts_and_requires_word():
    prompt = sign_confirmation_prompt(
        {"network": "Sepolia", "from": "0xabc", "to": "0xdef",
         "value_human": "0.01 ETH", "fee_human": "0.0001 ETH", "chain_id": 11155111}
    )
    assert "sign" in prompt  # the exact confirmation word
    assert "0xabc" in prompt and "0xdef" in prompt
    assert "TESTNET" in prompt