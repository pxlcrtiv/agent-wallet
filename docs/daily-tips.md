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


## 2026-08-28 — Agent & web3-safety tip: Automation should pause, not improvise

The Daily Green script honors a .daily-pause marker and skips cleanly when the day is already covered. Automation you cannot pause is automation you do not control.

> `touch .daily-pause`


## 2026-08-29 — Agent & web3-safety tip: Your agent is only as safe as its tools

Tool schemas limit what an LLM can even attempt. agent-wallet exposes four read-only/planning tools — there is no 'send' tool that broadcasts without the explicit sign path. Fewer tools, fewer surprises.

> `agent-wallet chat --help`


## 2026-08-30 — Agent & web3-safety tip: The plan file is your receipt

Save plans with --save before signing. The JSON contains the exact unsigned payload — a permanent, inspectable record of what you agreed to broadcast.

> `agent-wallet plan 0x… --save tx-2026-08-23.json`


## 2026-08-31 — Agent & web3-safety tip: Testnets are for learning — mainnet is for money

agent-wallet only touches Sepolia or a local anvil chain. On a testnet a mistake costs you a faucet refill; on mainnet it costs you real money. Keep the two worlds strictly separate: use a separate wallet and a separate browser profile for testnet activity.

> `agent-wallet chain`


## 2026-09-01 — Agent & web3-safety tip: Dry-run before you sign, always

eth_call simulation is free and instant. agent-wallet runs a dry-run of your exact payload before you ever see a 'sign' prompt. If the simulation reverts, the real transaction would too — do not sign it.

> `agent-wallet plan 0x… --save plan.json`


## 2026-09-02 — Agent & web3-safety tip: An unsigned transaction is just a plan

A transaction only becomes real when it carries a signature. Review the plan JSON — recipient, amount, fee, nonce — like you would review a contract clause. agent-wallet never attaches a signature automatically.

> `cat plan.json`


## 2026-09-03 — Agent & web3-safety tip: EIP-1559: max fee is a ceiling, not a promise

With type-0x2 transactions, maxFeePerGas is the most you will pay per gas unit; you usually pay less (base fee + priority fee). The risk summary shows worst-case fee so the ceiling is visible before signing.

> `agent-wallet plan 0x… --json | grep maxFeePerGas`


## 2026-09-04 — Agent & web3-safety tip: Check what your wallet approved

An ERC-20 allowance lets another address move your tokens up to the approved amount — even without your signature on each transfer. Run the allowance check to see exposure before you send more tokens anywhere.

> `agent-wallet inspect 0x…`


## 2026-09-05 — Agent & web3-safety tip: Infinite approvals are a standing risk

Approving max uint256 to a DEX or bridge means that contract could drain your tokens at any time if it is compromised. Revoke unused approvals, and never grant them to testnet tokens you care about.

> `agent-wallet chat "check allowance exposure"`

