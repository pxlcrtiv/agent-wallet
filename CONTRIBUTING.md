# Contributing to agent-wallet

Thanks for wanting to help! This is a small, safety-critical project — the
bar for merging is intentional.

## Ground rules

1. **Testnet-only. Nothing here ever touches mainnet.** Any change that
   weakens `ALLOWED_CHAIN_IDS` or the chain guards will not be merged.
2. **The agent cannot sign.** Adding a tool that signs or broadcasts breaks
   the core design (see `docs/SAFETY.md`) and will be rejected.
3. **Everything must run offline.** New features need fixture coverage —
   tests run against `fixtures://`, never against a live RPC.
4. **Plain English risk notes stay plain.** No hex dumps in user-facing
   output unless the user asked for `--json`.

## Development setup

```bash
pip install -e ./agent-lab   # local agent-lab checkout, or the git+ URL
pip install -e .[dev]
```

## Checks

```bash
pytest tests -q              # 67 tests, fully offline
ruff check agent_wallet tests scripts
```

Both must pass before a PR. Add tests with your feature — the suite is the
safety net for the safety net.

## Structure

- `agent_wallet/wallet.py` — chain reads (balances, allowances, gas, dry-run)
- `agent_wallet/txbuilder.py` — unsigned typed transaction construction
- `agent_wallet/tools.py` — agent-lab tools (read/plan only)
- `agent_wallet/safety.py` — guards + prompts; **treat as sacred**
- `tests/` — offline tests using the in-memory fixture provider

## Commit style

Concise conventional commits (`feat:`, `fix:`, `docs:`, `test:`). The
Daily Green script produces its own `docs:` commits — don't fight it, it is
idempotent and skips days that already have an entry.

## Reporting issues

Include the exact command, `--rpc` mode used, and the output. If it involves
a live chain, redact addresses/keys before pasting.