# Changelog

All notable changes to agent-wallet are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/) (more or less — the "API" here is
a CLI and a demo).

## [0.1.0] — 2026-08-23

Initial release. Sepolia-only, safety-by-design AI agent for testnet
transactions, built on agent-lab.

### Added

- **Wallet service** (`agent_wallet/wallet.py`): balances (native +
  known tokens), ERC-20 allowances, nonce, EIP-1559 fee suggestion, gas
  estimates, `eth_call` dry-run with decoded revert reasons.
- **Unsigned typed transaction builder** (`agent_wallet/txbuilder.py`):
  EIP-1559 (type `0x2`) with automatic legacy fallback, ERC-20
  `transfer` calldata builder + decoder.
- **Safety guards** (`agent_wallet/safety.py`): chain allow-list
  (Sepolia 11155111, anvil 31337), `MAINNET LOCKED` guard, safety-first
  agent system prompt, `sign` confirmation flow.
- **agent-lab tools** (`agent_wallet/tools.py`): `get_balances`,
  `check_allowance`, `dry_run_tx`, `plan_transfer` — every call
  chain-guarded; the agent loop cannot sign.
- **Agent loop** (`agent_wallet/agent.py`): agent-lab `Agent` with
  deterministic offline `MockBackend` (wallet-aware responder) or
  OpenAI-compatible backend.
- **CLI** (`agent_wallet/cli.py`): `plan`, `inspect`, `sign`, `chat`,
  `chain` with three RPC tiers (`fixtures://` offline · `anvil` ·
  `sepolia`/URL).
- **Offline fixture provider** (`agent_wallet/providers.py`): in-memory
  JSON-RPC provider — full functionality without network or keys.
- **Tests**: 67 offline pytest tests (safety, wallet, tx builder,
  tools, agent loop, CLI, providers, Daily Green pool).
- **Daily Green automation**: `scripts/daily_update.py` +
  `scripts/tips_pool.json` (26 curated tips); one dated, meaningful
  commit per day, idempotent, pause-able, backfills missed days.
- **Docs**: README with live demo transcripts (fixtures + anvil +
  Sepolia), `docs/SAFETY.md` (threat model + why mainnet is default-off),
  CONTRIBUTING, LICENSE (MIT), `ci.yml` + `daily.yml` workflows.

### Fixed

- agent-lab `pyproject.toml` author `url` field rejected by modern
  setuptools — dropped (upstreamed to agent-lab).

[0.1.0]: https://github.com/pxlcrtiv/agent-wallet/releases/tag/v0.1.0