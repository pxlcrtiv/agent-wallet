"""Shared fixtures: offline Web3 connection via FixturesProvider."""

from __future__ import annotations

import pytest
from web3 import Web3

from agent_wallet.providers import FIXTURE_USDC, FIXTURE_USER, FIXTURE_WETH, FixturesProvider
from agent_wallet.wallet import WalletService


@pytest.fixture()
def w3() -> Web3:
    """A Web3 instance backed by the in-memory fixture provider."""
    return Web3(FixturesProvider())


@pytest.fixture()
def svc(w3: Web3) -> WalletService:
    return WalletService(w3, owner="0x1111111111111111111111111111111111111111")


@pytest.fixture()
def svc_with_weth_allowance() -> WalletService:
    """A wallet whose fixture spender also holds a 1 WETH approval.

    WETH is an 18-decimals token, so it catches any amount that is scaled
    by a hardcoded 6.
    """
    w3 = Web3(
        FixturesProvider(
            allowances={
                FIXTURE_USDC.lower(): 1_000_000_000,
                FIXTURE_WETH.lower(): 10**18,
            }
        )
    )
    return WalletService(w3, owner=FIXTURE_USER)


class NoBaseFeeProvider(FixturesProvider):
    """Fixture variant whose latest block has no baseFeePerGas (pre-1559)."""

    def _rpc_eth_getBlockByNumber(self, params: list) -> dict:
        block = super()._rpc_eth_getBlockByNumber(params)
        block.pop("baseFeePerGas")
        return block


@pytest.fixture()
def w3_legacy() -> Web3:
    """Fixture chain without EIP-1559 support."""
    return Web3(NoBaseFeeProvider())


@pytest.fixture()
def test_key() -> str:
    return "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"