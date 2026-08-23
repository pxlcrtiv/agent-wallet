# Agent & web3-safety tips of the day

> Maintained by `scripts/daily_update.py` (Daily Green automation) — one
> dated, non-empty safety tip per day, rotated from the pool in
> `scripts/tips_pool.json`. Pause by creating a `.daily-pause` file in the
> repo root, or unload the scheduler job (see README, Daily Green).


## 2026-08-23 — Agent & web3-safety tip: Read the revert reason, not the error code

A revert like 'insufficient allowance' tells you exactly what to fix; a generic 'execution reverted' without data is a smoke signal. agent-wallet decodes Error(string) reasons so failures read like English.

> `agent-wallet chat "dry run 0.01 ETH to 0x…"`

