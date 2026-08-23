# Safety by design — why mainnet is default-off

agent-wallet exists for one reason: to make **testnet** transactions boring and
safe. The project's hard rule, from the first line of code:

> **agent-wallet never operates on Ethereum Mainnet. Not by accident, not by
> flag, not by request. Mainnet is not in the allow-list, and the allow-list
> is the only path through the door.**

This document explains how that rule is enforced and why it is shaped this way.

## Threat model

What is this agent actually protecting against?

1. **Your own momentum.** The most common way people lose crypto is a fast,
   confident transaction. A plan-first workflow with a signed, explicit
   confirmation step is the antidote.
2. **LLM hallucination.** If an agent can *sign*, a prompt-injection or a
   confused model can *steal*. By design, the agent here cannot sign: it
   produces unsigned transaction plans and risk notes. Signing is a separate
   CLI command that re-checks everything.
3. **The wrong chain.** Testnet keys and mainnet keys get mixed up all the
   time. A wallet filled with "free" Sepolia ETH must never be one flag away
   from real money. The allow-list makes that structurally impossible.
4. **Reverted or misdirected transactions.** A dry-run via `eth_call` costs
   nothing and catches underfunded sends, bad calldata, and contract rejections
   before anything is signed.
5. **Scams and forgeries.** Testnets are full of fake tokens, fake faucets,
   and phishing. The agent flags unknown token addresses and refuses to treat
   community deployments as official.

## How the guard rails work (defense in depth)

There are four independent layers. Each one alone would be enough to stop a
mainnet transaction; together they make it unbuildable.

### 1. Chain allow-list (the door)

`agent_wallet/config.py` defines the only acceptable chain ids:

| chain id | name                    |
|----------|-------------------------|
| 11155111 | Ethereum Sepolia        |
| 31337    | anvil / Hardhat local   |

`ensure_testnet(chain_id)` raises `SafetyError` for anything else, with a loud
`MAINNET LOCKED` message for chain id 1. Every code path that touches the
chain calls it:

- every agent-lab tool (`get_balances`, `check_allowance`, `dry_run_tx`,
  `plan_transfer`) guards on every invocation;
- the `inspect` and `plan` CLI commands guard before any RPC read;
- the `sign` command guards the *plan's* recorded chain id *and* the live
  connected chain, and refuses if they disagree.

### 2. No signing in the agent loop

The four agent tools are all read-only or planning tools:

- `get_balances` — read
- `check_allowance` — read
- `dry_run_tx` — simulation (`eth_call`), no state change possible
- `plan_transfer` — produces an **unsigned** transaction plus risk notes

There is no `send` tool and no `sign` tool. A compromised or confused model
literally has no tool that can move funds. The worst it can do is produce a
wrong plan — which the human still has to sign.

### 3. The sign command re-verifies everything

`agent-wallet sign <plan.json>` is the only path to a signature, and it:

1. refuses if the plan's chain id is not in the allow-list;
2. connects to the chain and refuses if the live chain id differs from the
   plan's;
3. re-runs the dry-run against current state and refuses if it reverts;
4. prints the full plan again, then requires typing the word `sign` to
   proceed (anything else aborts);
5. signs locally (the private key never leaves the process) and does **not**
   broadcast unless `--broadcast` is explicitly passed.

The private key is read from a file or `AGENT_WALLET_PRIVATE_KEY` — it is
never stored, never logged, never sent anywhere.

### 4. Honest risk communication

The plan output tells the truth in plain English:

- whether the recipient is an EOA or a contract (contracts execute code);
- whether the token address is known or unknown (unknown = treat as scam);
- the worst-case fee, the gas limit, and the nonce;
- whether the dry-run succeeded or reverted, with the decoded reason;
- whether the sender's balance covers value + fee (with faucet links if not);
- that this is testnet money with no real value.

## What this does NOT protect against

Be explicit with yourself about the limits:

- **A funded testnet wallet is still a wallet.** If your private key leaks,
  the attacker gets your (worthless) testnet funds — and, worse, a rehearsed
  path toward your real keys if you reuse them. Never reuse a mainnet seed
  on a testnet.
- **The dry-run is a snapshot.** State changes between simulation and
  broadcast; a successful dry-run is evidence, not a guarantee.
- **A sign prompt on the right chain is still a sign prompt.** Read the
  recipient and amount line by line. The confirmation word is a speed bump,
  not a proof.
- **agent-wallet does not audit contracts.** It flags that a recipient is a
  contract; it does not tell you whether that contract is malicious.

## The maintenance rule

Any future change to this codebase must keep all of the following true, or it
does not merge:

1. `ALLOWED_CHAIN_IDS` stays a small, explicit allow-list; adding a chain is a
   deliberate, reviewed decision.
2. Every tool remains unable to sign or broadcast.
3. The sign path always re-checks the live chain id against the plan's.
4. Test coverage of the guards stays green (`tests/test_safety.py`,
   `tests/test_cli.py` — the mainnet-lock tests).
5. Nothing ever relies on a "safe by default" flag that a user could flip
   without noticing.