"""agent-wallet CLI (click).

Commands:

    agent-wallet plan   TO        plan + dry-run + risk notes + unsigned tx
    agent-wallet inspect ADDRESS  balances, nonce, allowances
    agent-wallet sign    PLAN     confirm + sign a saved plan (testnet only)
    agent-wallet chat    QUERY    run the agent loop (mock backend by default)
    agent-wallet chain             network guard status

Every network-touching command accepts ``--rpc`` with three tiers:
    fixtures://                 offline, deterministic (default)
    anvil                       http://127.0.0.1:8545
    sepolia | http(s)://…       public testnet RPC
"""

from __future__ import annotations

import json
import os
import sys

import click
from web3 import Web3

from . import __version__
from .agent import build_agent
from .config import FAUCETS
from .providers import FIXTURE_USER, connect
from .risk import human_ether, summarize_plan
from .safety import SafetyError, ensure_testnet, sign_confirmation_prompt
from .tools import bind, plan_transfer
from .txbuilder import tx_to_signing_dict
from .wallet import WalletService

EXIT_SAFETY = 3
EXIT_NO_KEY = 4


def _w3(ctx: click.Context) -> Web3:
    rpc = ctx.obj.get("rpc") if ctx.obj else None
    w3, mode = connect(rpc)
    ctx.obj = {"rpc": rpc, "mode": mode}
    return w3


@click.group()
@click.version_option(__version__, prog_name="agent-wallet")
@click.option("--rpc", default="fixtures://", show_default=True,
              help="RPC source: fixtures:// | anvil | sepolia | http(s) URL")
@click.pass_context
def main(ctx: click.Context, rpc: str) -> None:
    """agent-wallet — inspect wallets, plan testnet transactions, explain risk.

    Sepolia-only by design.  Nothing is ever signed or broadcast unless you
    explicitly run `agent-wallet sign` and confirm.
    """
    ctx.obj = {"rpc": rpc}


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


@main.command()
@click.argument("to")
@click.option("--amount", "-a", default="0.01", show_default=True,
              help="Amount to send: ETH for native, token units for --token")
@click.option("--token", "-t", default=None,
              help="ERC-20 token address (default: native ETH transfer)")
@click.option("--from", "from_addr", default=None,
              help="Sender wallet (default: demo wallet)")
@click.option("--json", "as_json", is_flag=True, help="Print raw plan JSON")
@click.option("--save", "out_path", default=None, metavar="FILE",
              help="Also write the plan (unsigned tx) to FILE for `sign`")
@click.pass_context
def plan(ctx: click.Context, to: str, amount: str, token: str | None,
         from_addr: str | None, as_json: bool, out_path: str | None) -> None:
    """Plan a transfer: balances, fees, dry-run, risk notes, unsigned tx.

    TO is the recipient address.  Nothing is signed or broadcast.
    """
    w3 = _w3(ctx)
    mode = ctx.obj.get("mode", "http")
    try:
        bind(w3)
        result = plan_transfer(
            from_address=from_addr or FIXTURE_USER,
            to_address=to,
            amount_eth=float(amount),
            token=token,
        )
    except SafetyError as exc:
        click.echo("SAFETY: %s" % exc, err=True)
        sys.exit(EXIT_SAFETY)
    except Exception as exc:
        click.echo("error: %s: %s" % (type(exc).__name__, exc), err=True)
        sys.exit(1)

    result["_rpc_mode"] = mode
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        click.echo("plan saved to %s (unsigned — inspect before signing)" % out_path)

    if as_json:
        click.echo(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        click.echo(summarize_plan(result))
        if mode == "fixtures":
            click.echo("\n[note] offline RPC (fixtures://) — numbers are sample data. "
                       "Use --rpc anvil or --rpc sepolia for live values.")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@main.command()
@click.argument("address", required=False)
@click.pass_context
def inspect(ctx: click.Context, address: str | None) -> None:
    """Show balances, nonce and allowance exposure for an address."""
    w3 = _w3(ctx)
    addr = address or FIXTURE_USER
    try:
        bind(w3)
        svc = WalletService(w3)
        info = svc.ensure_testnet()
        owner = Web3.to_checksum_address(addr)
        balances = svc.get_balances(owner)
        nonce = svc.get_nonce(owner)
        allowances = svc.check_allowance(owner=owner)
    except SafetyError as exc:
        click.echo("SAFETY: %s" % exc, err=True)
        sys.exit(EXIT_SAFETY)
    except Exception as exc:
        click.echo("error: %s: %s" % (type(exc).__name__, exc), err=True)
        sys.exit(1)

    click.echo("network   %s (chain id %d) — %s" % (
        info["name"], info["chain_id"],
        "ALLOWED" if info["allowed"] else "FORBIDDEN"))
    click.echo("address   %s" % owner)
    click.echo("balance   %s" % human_ether(balances["native_wei"]))
    click.echo("nonce     %d" % nonce)
    for t in balances.get("tokens", []):
        click.echo("  token   %-5s %s" % (t["symbol"], t["raw"] / 10 ** t["decimals"]))
    click.echo("allowances")
    for a in allowances.get("allowances", []):
        flag = "EXPOSED" if a["exposed"] else "clean"
        click.echo("  %-5s %s (spender %s) %s" % (a["symbol"], a["human"], a["spender"][:12], flag))


# ---------------------------------------------------------------------------
# chain
# ---------------------------------------------------------------------------


@main.command("chain")
@click.pass_context
def chain_cmd(ctx: click.Context) -> None:
    """Show the guard status of the connected chain."""
    w3 = _w3(ctx)
    svc = WalletService(w3)
    try:
        info = svc.ensure_testnet()
        click.echo("chain id  %d" % info["chain_id"])
        click.echo("name     %s" % info["name"])
        click.echo("status   allowed (testnet — safe to plan)")
    except SafetyError as exc:
        click.echo("chain id  %d" % svc.chain_id())
        click.echo("status   FORBIDDEN")
        click.echo("SAFETY: %s" % exc, err=True)
        sys.exit(EXIT_SAFETY)


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


@main.command()
@click.argument("query")
@click.option("--backend", type=click.Choice(["mock", "openai"]), default="mock",
              show_default=True, help="mock = deterministic offline agent")
@click.option("--steps", is_flag=True, default=True, show_default=True,
              help="Show every tool step of the agent loop")
@click.pass_context
def chat(ctx: click.Context, query: str, backend: str, steps: bool) -> None:
    """Ask the agent (natural language) about balances, allowances, dry-runs."""
    w3 = _w3(ctx)
    bind(w3)
    agent = build_agent(w3=w3, backend=backend)
    result = agent.run(query)
    if steps:
        for s in result.steps:
            if s.kind in ("tool_call", "tool_result"):
                click.echo("[%s] %s %s" % (s.kind, s.name, s.detail[:140]))
    click.echo(result.answer)


# ---------------------------------------------------------------------------
# sign
# ---------------------------------------------------------------------------


def _load_key(keyfile: str | None) -> str:
    """Private key from --keyfile or AGENT_WALLET_PRIVATE_KEY env."""
    if keyfile:
        with open(keyfile, encoding="utf-8") as fh:
            raw = fh.read().strip()
        return raw.removeprefix("0x")
    env = os.environ.get("AGENT_WALLET_PRIVATE_KEY")
    if env:
        return env.removeprefix("0x")
    return ""


@main.command()
@click.argument("planfile")
@click.option("--keyfile", default=None, metavar="FILE",
              help="File containing the private key hex (or set AGENT_WALLET_PRIVATE_KEY)")
@click.option("--broadcast", is_flag=True, default=False,
              help="After signing, submit the tx to the network")
@click.pass_context
def sign(ctx: click.Context, planfile: str, keyfile: str | None, broadcast: bool) -> None:
    """Sign a saved plan (created by `agent-wallet plan --save`).

    Re-checks the chain, re-runs the dry-run, shows the risk summary again,
    and refuses anything that is not a testnet.  The private key never
    leaves this process.
    """
    try:
        with open(planfile, encoding="utf-8") as fh:
            plan = json.load(fh)
    except (OSError, ValueError) as exc:
        click.echo("cannot read plan %s: %s" % (planfile, exc), err=True)
        sys.exit(1)

    plan_chain = int(plan.get("chain_id", 0))
    w3 = _w3(ctx)
    try:
        ensure_testnet(plan_chain)
        svc = WalletService(w3)
        svc.ensure_testnet()
        live_chain = svc.chain_id()
        if live_chain != plan_chain:
            click.echo(
                "SAFETY: plan was built for chain %d but the connected chain is %d. "
                "Refusing to sign." % (plan_chain, live_chain), err=True)
            sys.exit(EXIT_SAFETY)
    except SafetyError as exc:
        click.echo("SAFETY: %s" % exc, err=True)
        sys.exit(EXIT_SAFETY)

    key = _load_key(keyfile)
    if not key:
        click.echo(
            "no private key: pass --keyfile FILE or set AGENT_WALLET_PRIVATE_KEY. "
            "agent-wallet never stores keys.", err=True)
        sys.exit(EXIT_NO_KEY)

    from eth_account import Account

    tx = dict(plan.get("unsigned_tx") or {})
    from_addr = tx.get("from") or plan.get("from")
    if not from_addr:
        click.echo("plan has no sender address", err=True)
        sys.exit(1)

    # Re-dry-run the exact payload against the live chain before signing.
    dry = svc.dry_run({
        "from": Web3.to_checksum_address(from_addr),
        "to": tx["to"],
        "value": int(tx.get("value", 0)),
        "data": tx.get("data", "0x"),
    })
    if dry.get("reverted"):
        click.echo("SAFETY: dry-run reverted on the live chain (%s). Not signing." % dry.get("reason"), err=True)
        sys.exit(EXIT_SAFETY)

    balance = svc.get_balance(from_addr)
    fee = int(tx.get("gas", 0)) * int(tx.get("maxFeePerGas", tx.get("gasPrice", 0)))
    total = int(tx.get("value", 0)) + fee
    if balance < total:
        click.echo("NOTE: wallet balance %s is below value+fee %s." % (
            human_ether(balance), human_ether(total)))
        click.echo("Faucet funding (Sepolia):", err=False)
        for f in FAUCETS.get("sepolia", []):
            click.echo("  - %s" % f)

    click.echo(summarize_plan({**plan, "risk_notes": plan.get("risk_notes", [])}))
    click.echo("")
    click.echo(sign_confirmation_prompt(plan))
    reply = input("confirm> ").strip().lower()
    if reply != "sign":
        click.echo("aborted — nothing was signed.")
        sys.exit(1)

    signable = tx_to_signing_dict(tx)
    signed = Account.sign_transaction(signable, key)
    click.echo("signed tx  %s" % signed.hash.hex())
    click.echo("raw tx     %s" % signed.raw_transaction.hex())

    if broadcast:
        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            click.echo("broadcast  %s" % (tx_hash.hex() if hasattr(tx_hash, "hex") else tx_hash))
        except Exception as exc:
            click.echo("broadcast failed: %s" % exc, err=True)
            sys.exit(1)
    else:
        click.echo("not broadcast. To send it yourself:")
        click.echo("  cast publish <raw-hex> --rpc-url %s" % _rpc_url(ctx.obj.get("rpc")))


def _rpc_url(rpc: str | None) -> str:
    if rpc in ("anvil", None):
        return "http://127.0.0.1:8545"
    if rpc == "sepolia":
        return "https://ethereum-sepolia-rpc.publicnode.com"
    return rpc or "https://ethereum-sepolia-rpc.publicnode.com"


if __name__ == "__main__":
    main()