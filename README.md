# agent-wallet

> An AI agent for **safe testnet transactions** — built on
> [agent-lab](https://github.com/pxlcrtiv/agent-lab). It inspects a wallet,
> checks allowances, dry-runs a transaction, and explains risk in plain
> English **before anything is signed**. Sepolia only. Safety by design.
>
> **Mainnet is default-off and structurally impossible.** See
> [docs/SAFETY.md](docs/SAFETY.md) for the full threat model.

## Badges

| CI | Quality | Ecosystem |
|----|---------|-----------|
| [![CI](https://github.com/pxlcrtiv/agent-wallet/actions/workflows/ci.yml/badge.svg)](https://github.com/pxlcrtiv/agent-wallet/actions/workflows/ci.yml) | [![tests](https://img.shields.io/badge/tests-67%20passed-brightgreen)](https://github.com/pxlcrtiv/agent-wallet) | [![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/) |
| [![Daily Green](https://github.com/pxlcrtiv/agent-wallet/actions/workflows/daily.yml/badge.svg)](https://github.com/pxlcrtiv/agent-wallet/actions/workflows/daily.yml) | [![ruff](https://img.shields.io/badge/lint-ruff-00A86B?logo=ruff)](https://github.com/astral-sh/ruff) | [![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE) |
| [![Web3](https://img.shields.io/badge/web3.py-7.x-4b8bbe)](https://web3py.readthedocs.io/) | [![agent-lab](https://img.shields.io/badge/agent--core-agent--lab-8A2BE2)](https://github.com/pxlcrtiv/agent-lab) | [![testnet](https://img.shields.io/badge/network-Sepolia%20%7C%20anvil-yellow)](docs/SAFETY.md) |

## The problem

Sending crypto is the scariest 10 seconds in web3. You paste an address, a
defi app asks for approval *first* ("sign this — it's safe"), you click… and
the money is gone. Humans sign too fast: the wrong chain, the wrong amount,
an infinite approval, a contract that was never going to accept the payment.

AI agents make it worse. An agent shell attached to a hot wallet is a
one-line prompt-injection away from being a drainer. The tools it can call
*are* the attack surface.

## The solution

`agent-wallet` treats the wallet as **read-only** and the transaction as a
**document**:

1. **Inspect** — native + known-token balances, allowance exposure, nonce.
2. **Plan** — build an unsigned typed transaction (EIP-1559), estimate real
   gas and fees from the live chain.
3. **Dry-run** — simulate the exact payload with `eth_call`; a revert is
   caught and *explained* before you sign.
4. **Explain** — a plain-English risk summary: contract vs EOA recipient,
   known vs unknown token, worst-case fee, coverage check, faucet hints.
5. **Sign (separately)** — a dedicated command that re-checks the chain,
   re-dry-runs, prints everything again, and requires you to type `sign`.

And the agent itself **cannot sign**. The four agent-lab tools are read-only
or planning-only. There is no "send" tool an LLM could be tricked into
calling.

## Features

- **agent-lab agent core** — a real agent loop (tools, schema-derived
  function calling, memory, turn budget) on top of
  [pxlcrtiv/agent-lab](https://github.com/pxlcrtiv/agent-lab)
- **4 wallet tools** — `get_balances`, `check_allowance`, `dry_run_tx`,
  `plan_transfer`, each chain-guarded on every call
- **deterministic offline mode** — `--rpc fixtures://` runs the whole thing
  keyless and networkless; tests and demos never touch the internet
- **typed unsigned transactions** — EIP-1559 (type `0x2`) with automatic
  legacy fallback, ERC-20 transfer calldata builder + decoder
- **human-readable risk notes** — the thing you actually want to read
  before signing
- **one `--sign` path** — confirmation word, chain re-check, dry-run
  re-check, faucet instructions; never signs on mainnet, never broadcasts
  unless you say `--broadcast`
- **67 offline tests**, ruff-clean, CI-ready
- **Daily Green automation** — one dated, meaningful commit per day (see
  below)

## Quickstart

### 1. Install

```bash
git clone https://github.com/pxlcrtiv/agent-wallet.git
cd agent-wallet

# agent-lab is the agent core — install it first (local checkout or pip):
pip install -e ./agent-lab 2>/dev/null || pip install "agent-lab @ git+https://github.com/pxlcrtiv/agent-lab@main"

pip install -e .
```

### 2. Run it — zero setup, zero funds, zero network

```bash
agent-wallet --rpc fixtures:// plan 0x2222222222222222222222222222222222222222 --amount 0.05
```

`fixtures://` is an in-memory deterministic RPC. It works offline, on a
train, in CI. The output is a real transcript of the tool — sample data, but
the exact same code paths (this very output was captured by running it):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TX PLAN — Ethereum Sepolia (testnet)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  from   0x1111111111111111111111111111111111111111
  to     0x2222222222222222222222222222222222222222
  value  0.050000 ETH
  gas    21000 units (max fee 2.0 gwei → ≤ 0.000042 ETH)
  nonce  7
  type   0x2

RISK NOTES
  1. Network: Ethereum Sepolia (testnet) (chain id 11155111). Testnet — the ETH/tokens involved have no real value.
  2. Recipient 0x2222222222222222222222222222222222222222 is a regular account (no code) — a plain transfer address.
  3. Estimated gas: 21000 units at max fee 2.0 gwei → worst-case fee ≈ 0.000042 ETH.
  4. Dry-run (eth_call) succeeded — this exact payload does not revert on the current chain state.
  5. Sender balance 1.000000 ETH covers value + worst-case fee.

UNSIGNED — nothing was signed. Review, then sign with: agent-wallet sign <plan.json>
```

### 3. Live demo — local anvil chain (funded accounts, real blocks)

```bash
anvil --port 8545        # foundry's dev chain: pre-funded accounts, chain id 31337
```

In another terminal:

```bash
agent-wallet --rpc anvil inspect 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

```
network   anvil local chain (testnet) (chain id 31337) — ALLOWED
address   0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
balance   9999.988018 ETH
nonce     15
allowances
```

```bash
agent-wallet --rpc anvil plan 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  --amount 0.1 --from 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --save plan.json
```

```
plan saved to plan.json (unsigned — inspect before signing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TX PLAN — anvil local chain (testnet)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  from   0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
  to     0x70997970C51812dc3A010C7d01b50e0d17dc79C8
  value  0.100000 ETH
  gas    21000 units (max fee 1.2 gwei → ≤ 0.000024 ETH)
  nonce  15
  type   0x2

RISK NOTES
  1. Network: anvil local chain (testnet) (chain id 31337). Testnet — the ETH/tokens involved have no real value.
  2. Recipient 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 is a regular account (no code) — a plain transfer address.
  3. Estimated gas: 21000 units at max fee 1.2 gwei → worst-case fee ≈ 0.000024 ETH.
  4. Dry-run (eth_call) succeeded — this exact payload does not revert on the current chain state.
  5. Sender balance 9999.988018 ETH covers value + worst-case fee.

UNSIGNED — nothing was signed. Review, then sign with: agent-wallet sign <plan.json>
```

Now sign — and, because this is a throwaway local chain, broadcast it too:

```bash
printf 'sign\n' | agent-wallet --rpc anvil sign plan.json --keyfile anvil.key --broadcast
```

```
  Network:     anvil local chain (testnet)
  From:        0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
  To:          0x70997970C51812dc3A010C7d01b50e0d17dc79C8
  Value:       0.100000 ETH
  Max fee:     0.000024 ETH
  Chain id:    31337

Type the word  sign  to confirm, anything else aborts.
confirm> signed tx  cf68fa98a20111f4646648129a6de709a7724ab3397b759121a1d8ee1ede4d4f
raw tx     02f874827a690f843b9aca008445840ebc8252089470997970c51812dc3a010c7d01b50e0d17dc79c888016345785d8a000080c080a0ab43c9f9aebfad626b3bcbf3df82b57f0cf841cbafddfcd0a5ec2519febdf914a0109ead99f772ffbea3a5409c2a04b9d50f0bec7156dc2df5a91db27a61eb8a16
broadcast  cf68fa98a20111f4646648129a6de709a7724ab3397b759121a1d8ee1ede4d4f

# the recipient really got the 0.1 ETH:
$ agent-wallet --rpc anvil inspect 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
balance   10000.100000 ETH
```

`anvil.key` here is anvil's public demo key
(`ac0974…ff80`, printed on anvil startup) — on a real testnet you would use
a key you generated yourself.

### 4. Ask the agent (offline by default)

```bash
agent-wallet chat "check the balance of 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
```

```
[tool_call] get_balances {"address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"}
[tool_result] get_balances {'address': '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266', 'native_eth': 9999.88799416716, ...}
Balance for 0xf39Fd6e51a: 9999.8880 ETH (native) and 0 known token(s) tracked. Testnet only — no real value.
```

The default `mock` backend is a deterministic scripted agent that actually
calls the wallet tools — it demos the full loop without an LLM API key. For
a real LLM: `--backend openai` with `OPENAI_API_KEY` set (any
OpenAI-compatible endpoint via `OPENAI_BASE_URL`).

### 5. Live Sepolia (read-only — no wallet needed)

```bash
agent-wallet --rpc sepolia inspect 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

```
network   Ethereum Sepolia (testnet) (chain id 11155111) — ALLOWED
address   0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
balance   60.168394 ETH
nonce     0
  token   USDC  1010.511382
  token   WETH  0.08142189550119822
```

Everything above is a live read against `https://ethereum-sepolia-rpc.publicnode.com`.

## The `--sign` path, in full

```bash
agent-wallet plan 0x… --amount 0.01 --save plan.json     # inspect → plan → dry-run → risk notes
agent-wallet sign plan.json --keyfile ./testnet.key      # re-checks chain + dry-run, asks for the word "sign"
```

- refuses mainnet **and any chain outside the allow-list**;
- refuses if the connected chain differs from the plan's chain;
- refuses if the dry-run reverts;
- prints faucet links when the sender is underfunded;
- never broadcasts unless `--broadcast` is passed;
- the key comes from `--keyfile` or `AGENT_WALLET_PRIVATE_KEY` and never
  leaves your machine.

## Honest caveats

- **Testnet only.** There is no real money in any of this. When the demo
  "sends 0.1 ETH" it sends pretend ETH on a pretend chain.
- **Community token deployments.** The known-token list in
  `agent_wallet/config.py` is community knowledge, not an endorsement.
  Always verify token addresses on a block explorer.
- **Dry-run ≠ guarantee.** Simulation happens against a snapshot of chain
  state; fees and balances move. Re-run `plan` (or `sign`, which
  re-simulates) right before broadcasting.
- **The agent is a planner, not a guardian angel.** It flags contract
  recipients and unknown tokens; it does not audit contract code. If you
  sign something malicious, it was still you who typed `sign`.
- **No funded live testnet wallet ships with this repo.** For the live
  `--broadcast` demo you provide your own Sepolia wallet (faucets listed
  in the sign output). Everything else works keyless: `fixtures://` for
  zero-setup, `anvil` for a real local chain.

## Tech stack

| Piece | Choice | Why |
|-------|--------|-----|
| Agent core | [agent-lab](https://github.com/pxlcrtiv/agent-lab) | own zero-dep framework: tool schemas from signatures, memory, loop guards |
| Chain access | [web3.py](https://web3py.readthedocs.io/) 7.x | the standard Ethereum Python client |
| Account/signing | [eth-account](https://eth-account.readthedocs.io/) | typed tx signing, EIP-1559 |
| CLI | [click](https://click.palletsprojects.com/) | composable command groups, `--rpc` tiers |
| Tests | pytest (67, offline) + ruff | the safety rails deserve a real test suite |
| Local chain | [Foundry anvil](https://book.getfoundry.sh/anvil/) | pre-funded, deterministic, chain id 31337 |
| CI | GitHub Actions | `ci.yml` (tests/lint/smoke) + `daily.yml` (Daily Green fallback) |

## Daily Green automation

`scripts/daily_update.py` appends one dated, hand-curated agent/web3-safety
tip (from `scripts/tips_pool.json`, 26 entries, rotated deterministically by
calendar day) to `docs/daily-tips.md` and creates a **non-empty, dated
commit** every day — so the contribution graph stays green with real
content, not empty commits.

- **Scheduler:** macOS launchd (`com.pxlcrtiv.daily-green` at 12:07/18:07)
  with this repo auto-discovered by the wrapper; GitHub Actions
  `daily.yml` (12:00 UTC) is the cloud fallback. Whichever runs first wins
  the day — the other sees the entry and exits cleanly (idempotent).
- **Missed days:** the next run backfills one dated commit per missed day
  (max 14), preserving the graph.
- **Pause:** `touch .daily-pause` in the repo root, or unload the launchd
  job.
- **Customize:** edit `scripts/tips_pool.json` (title/body/command).

Log: [docs/daily-tips.md](docs/daily-tips.md)

## Project layout

```
agent_wallet/
├── config.py      # chain allow-list, known tokens, ERC-20 ABI, faucets
├── providers.py   # RPC resolution + deterministic in-memory fixture provider
├── safety.py      # mainnet guard rails + safety system prompt
├── wallet.py      # WalletService: balances, allowances, nonce, gas, dry-run
├── txbuilder.py   # unsigned typed tx builder + ERC-20 calldata
├── risk.py        # plain-English risk summary renderer
├── tools.py       # the four agent-lab tools (chain-guarded)
├── agent.py       # agent-lab loop wiring (Mock/openai backends)
└── cli.py         # click CLI: plan / inspect / sign / chat / chain
tests/             # 67 offline tests (fixtures:// — no network)
scripts/           # Daily Green automation
docs/SAFETY.md     # why mainnet is default-off
```

## Related

- [agent-lab](https://github.com/pxlcrtiv/agent-lab) — the agent framework
  this project is built on (tool use, memory, workflow automation)
- [model-ledger](https://github.com/pxlcrtiv/model-ledger) — Solidity
  registry + Foundry test suite + Python/ethers tools
- [slither-chat](https://github.com/pxlcrtiv/slither-chat) — smart-contract
  audit copilot (Slither findings explained in plain English)

## License

MIT — see [LICENSE](LICENSE). Contributions welcome: [CONTRIBUTING.md](CONTRIBUTING.md), changelog in [CHANGELOG.md](CHANGELOG.md).