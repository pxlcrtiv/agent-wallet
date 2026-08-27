# Agent & web3-safety tips of the day

> Maintained by `scripts/daily_update.py` (Daily Green automation) — one
> dated, non-empty safety tip per day, rotated from the pool in
> `scripts/tips_pool.json`. Pause by creating a `.daily-pause` file in the
> repo root, or unload the scheduler job (see README, Daily Green).


## 2026-08-23 — Agent & web3-safety tip: Read the revert reason, not the error code

A revert like 'insufficient allowance' tells you exactly what to fix; a generic 'execution reverted' without data is a smoke signal. agent-wallet decodes Error(string) reasons so failures read like English.

> `agent-wallet chat "dry run 0.01 ETH to 0x…"`


## 2026-08-24 — Agent & web3-safety tip: Keystores beat copy-paste

If you sign often, store test keys in an encrypted keystore file (cast wallet import) instead of shell history. agent-wallet accepts --keyfile for exactly that workflow.

> `cast wallet import testwallet --interactive`


## 2026-08-25 — Agent & web3-safety tip: The confirmation word exists for a reason

agent-wallet requires typing the word 'sign' before it applies a signature. That deliberate pause is the cheapest insurance in web3: one moment to re-read recipient, amount, and fee.

> `agent-wallet sign plan.json`


## 2026-08-26 — Agent & web3-safety tip: Balance checks are reads; sends are writes

Reading a balance can never harm you. Signing and broadcasting change state forever. Keep the two verbs straight, and treat every 'send' as a permanent action even on a testnet.

> `agent-wallet inspect 0x…`


## 2026-08-27 — Agent & web3-safety tip: Beware the copy-paste address swap

Clipboard malware swaps pasted addresses for attacker-owned ones. Compare the first and last 6 characters of every address you paste, and use the checksummed form — it fails loudly if corrupted.

> `agent-wallet plan 0xDeadBeef… --amount 0.01`

