"""Safety guards and prompt constraints.

Three layers, in order:

1. Chain guard — ``ensure_testnet`` refuses any chain outside the
   allow-list before any read or write RPC happens.
2. Prompt guard — the agent system prompt says, in plain words, that
   mainnet is forbidden, amounts must be verified, and signing is the
   user's decision after seeing the risk summary.
3. Sign guard — the CLI re-checks the chain id at sign time and requires
   an interactive confirmation.  No path in this codebase ever signs on
   a non-allowed chain.
"""

from __future__ import annotations

from .config import ALLOWED_CHAIN_IDS, MAINNET_CHAIN_ID


class SafetyError(RuntimeError):
    """Raised when a safety guard trips.  CLI maps it to exit code 3."""


def chain_is_allowed(chain_id: int) -> bool:
    return chain_id in ALLOWED_CHAIN_IDS


def ensure_testnet(chain_id: int) -> None:
    """Raise SafetyError unless ``chain_id`` is in the allow-list.

    Mainnet (1) gets a dedicated message; unknown chains get a generic one.
    """
    if chain_id == MAINNET_CHAIN_ID:
        raise SafetyError(
            "MAINNET LOCKED: agent-wallet refuses to operate on Ethereum Mainnet "
            "(chain id 1). Testnet-only by design — real funds are never touched. "
            "Allowed chains: %s." % ", ".join(str(c) for c in sorted(ALLOWED_CHAIN_IDS))
        )
    if chain_id not in ALLOWED_CHAIN_IDS:
        raise SafetyError(
            "chain id %d is not in the allow-list (%s). "
            "agent-wallet only runs on testnets / local chains." % (chain_id, ", ".join(str(c) for c in sorted(ALLOWED_CHAIN_IDS)))
        )


AGENT_SYSTEM_PROMPT = """You are agent-wallet, a cautious on-chain assistant that only ever works on TESTNETS.

Safety constraints — follow them unconditionally:
1. You may only inspect wallets and plan transactions on Sepolia (chain id 11155111) or a local anvil chain (31337). Never propose, prepare, or sign anything for Ethereum Mainnet or any other chain.
2. Every plan must be dry-run simulated and summarized in plain English BEFORE the user is asked to sign. Risk notes come first; the unsigned transaction last.
3. You never hold or manage private keys. You produce unsigned transaction plans; signing is a separate step the user runs explicitly.
4. If a transaction would revert, say so and explain why. Never bury a failure.
5. Token addresses are community deployments — always tell the user to verify token addresses independently.
6. Be honest about what you cannot know: fees can move, allowances can be abused by the spender, and a "successful" dry-run does not guarantee a successful broadcast.
7. Amounts: never guess. Use the tools. If a balance is missing, say "not available from this RPC".

Tool use rules:
- Call at most one tool per turn, wait for its result, then continue.
- Never call a tool twice with identical arguments.
- When the user's question is answered, give a concise final answer that quotes the key numbers.
"""


def sign_confirmation_prompt(plan: dict) -> str:
    rows = [
        ("Network:", str(plan.get("network", "?"))),
        ("From:", str(plan.get("from", "?"))),
        ("To:", str(plan.get("to", "?"))),
        ("Value:", str(plan.get("value_human", "?"))),
        ("Max fee:", str(plan.get("fee_human", "?"))),
        ("Chain id:", str(plan.get("chain_id", "?"))),
    ]
    body = "\n".join("  %-12s %s" % (label, value) for label, value in rows)
    return (
        "YOU ARE ABOUT TO SIGN A REAL TESTNET TRANSACTION.\n"
        "This is fake money on a testnet, but the mechanics are the same as mainnet — "
        "check everything before you sign.\n\n"
        + body
        + "\n\nType the word  sign  to confirm, anything else aborts."
    )