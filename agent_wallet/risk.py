"""Human-readable risk summaries.

Turns a dry, technical transaction plan into plain-English notes a user can
actually read before signing: what is being sent, to whom, what it costs,
what could go wrong, and whether the chain is safe to use at all.
"""

from __future__ import annotations

from .config import CHAIN_NAMES, KNOWN_TOKENS


def gwei(wei: int) -> float:
    return wei / 1e9


def human_ether(wei: int) -> str:
    return "%.6f ETH" % (wei / 1e18)


def human_amount(raw: int, decimals: int, symbol: str) -> str:
    return "%.4f %s" % (raw / 10**decimals, symbol)


def risk_notes(
    *,
    chain_id: int,
    from_address: str,
    to_address: str,
    value_wei: int,
    token: str | None = None,
    gas: int,
    max_fee_per_gas: int,
    dry_run: dict,
    recipient_is_contract: bool,
    balance_wei: int,
    token_balance_raw: int | None = None,
    token_decimals: int = 6,
    symbol: str = "ETH",
    allowance: int | None = None,
) -> list[str]:
    """Return a list of plain-English risk notes for the plan."""
    notes: list[str] = []
    if chain_id == 1:
        notes.append("MAINNET LOCK: this chain is mainnet — agent-wallet will not build a plan.")
    elif chain_id not in CHAIN_NAMES:
        notes.append("Unknown chain id %d — treated as unsafe, no plan built." % chain_id)
    else:
        notes.append("Network: %s (chain id %d). Testnet — the ETH/tokens involved have no real value." % (CHAIN_NAMES[chain_id], chain_id))

    if recipient_is_contract:
        notes.append(
            "Recipient %s is a smart contract (%s). Sending to a contract executes its code — "
            "if that code rejects the transfer, your funds (tokens) may be locked or lost. "
            "Only send to a contract you understand." % (to_address, (token and "token address") or "non-token contract")
        )
    else:
        notes.append("Recipient %s is a regular account (no code) — a plain transfer address." % to_address)

    if token:
        meta = KNOWN_TOKENS.get(token.lower())
        if meta:
            notes.append(
                "Token %s is a known community deployment on Sepolia (%s). Community deployments are NOT official — "
                "verify the token address yourself before sending." % (meta["symbol"], meta["name"])
            )
        else:
            notes.append(
                "Token %s is NOT in the known-token list. It may be a scam or a stale deployment — "
                "treat as high risk and verify independently." % token
            )

    fee_wei = gas * max_fee_per_gas
    notes.append("Estimated gas: %d units at max fee %.1f gwei → worst-case fee ≈ %s." % (gas, gwei(max_fee_per_gas), human_ether(fee_wei)))

    if dry_run.get("reverted"):
        notes.append(
            "DRY-RUN FAILED: the simulated transaction reverts%s. Do not sign — this exact payload would fail on-chain."
            % ((": " + str(dry_run["reason"])) if dry_run.get("reason") else "")
        )
    else:
        notes.append("Dry-run (eth_call) succeeded — this exact payload does not revert on the current chain state.")

    if token and token_balance_raw is not None:
        if token_balance_raw < 0:
            notes.append("Insufficient %s balance — the transfer would revert at execution time." % symbol)
        else:
            notes.append("Sender %s balance is %s." % (symbol, human_amount(token_balance_raw, token_decimals, symbol)))
    elif not token:
        total_need = value_wei + fee_wei
        if balance_wei < total_need:
            notes.append(
                "INSUFFICIENT FUNDS: balance %s is below value+fee %s. Fund from a Sepolia faucet before broadcasting."
                % (human_ether(balance_wei), human_ether(total_need))
            )
        else:
            notes.append("Sender balance %s covers value + worst-case fee." % human_ether(balance_wei))

    if allowance is not None and allowance > 0:
        notes.append(
            "Allowance exposure: an address already holds approval for %s test token(s) from this wallet. "
            "Review approvals at revoke.cash before committing more." % human_amount(allowance, token_decimals or 6, symbol)
        )
    return notes


def summarize_plan(plan: dict) -> str:
    """Render a plan dict (from tools.plan_transfer) as readable console text."""
    lines = [
        "━" * 60,
        "TX PLAN — %s" % plan.get("network", "?"),
        "━" * 60,
        "  from   %s" % plan.get("from", "?"),
        "  to     %s" % plan.get("to", "?"),
        "  value  %s" % plan.get("value_human", "?"),
        "  gas    %d units (max fee %.1f gwei → ≤ %s)" % (
            int(plan.get("gas", 0)),
            gwei(int(plan.get("max_fee_per_gas_wei", 0))),
            human_ether(int(plan.get("fee_wei", 0))),
        ),
        "  nonce  %d" % int(plan.get("nonce", 0)),
        "  type   %s" % plan.get("tx_type", "?"),
        "",
        "RISK NOTES",
    ]
    notes = plan.get("risk_notes") or []
    for i, n in enumerate(notes, 1):
        lines.append("  %d. %s" % (i, n))
    lines += ["", "UNSIGNED — nothing was signed. Review, then sign with: agent-wallet sign <plan.json>"]
    return "\n".join(lines)