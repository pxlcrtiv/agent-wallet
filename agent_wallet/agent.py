"""The agent loop: agent-lab core + wallet tools + safety prompt.

``build_agent`` wires the pieces the same way for CLI, tests and demos:

* a ToolRegistry holding the four wallet tools;
* the safety system prompt (see safety.AGENT_SYSTEM_PROMPT);
* a model backend — MockBackend by default (deterministic, offline,
  scripted to actually call the wallet tools), OpenAICompatBackend if the
  user has an OpenAI-compatible endpoint (OPENAI_API_KEY / OPENAI_BASE_URL).

The agent never signs anything: it inspects, simulates, and explains.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable

from agentlab import Agent, AgentResult, MockBackend, OpenAICompatBackend, ToolRegistry
from web3 import Web3

from .safety import AGENT_SYSTEM_PROMPT
from .tools import bind, wallet_tools

_ALIASES = {
    "balance": "get_balances",
    "balances": "get_balances",
    "allowance": "check_allowance",
    "allowances": "check_allowance",
    "approved": "check_allowance",
    "approval": "check_allowance",
    "dry run": "dry_run_tx",
    "dry-run": "dry_run_tx",
    "simulate": "dry_run_tx",
    "revert": "dry_run_tx",
    "plan": "plan_transfer",
    "transfer": "plan_transfer",
    "send": "plan_transfer",
    "move": "plan_transfer",
    "pay": "plan_transfer",
}


def _pick_tool(text: str) -> str:
    low = text.lower()
    for key, tool_name in _ALIASES.items():
        if key in low:
            return tool_name
    return ""


def wallet_responder(messages: list, tools: list) -> dict:
    """Deterministic scripted responder for the offline demo/tests.

    Routes the latest user message to one of the wallet tools (by keyword),
    then answers with a human-safe summary quoting the numbers the tool
    returned.  Mirrors what a real LLM would do, minus the nondeterminism.
    """
    last = messages[-1] if messages else {}
    if last.get("role") == "tool":
        content = str(last.get("content") or "")
        try:
            parsed = json.loads(content)
        except ValueError:
            parsed = {}
        if isinstance(parsed, dict) and parsed.get("ok") is True:
            result = parsed.get("result", {})
            if isinstance(result, dict) and "risk_notes" in result:
                return {
                    "role": "assistant",
                    "content": (
                        "Plan ready. %s to %s. Dry-run %s. Key risk: %s. "
                        "Nothing signed — the unsigned tx is in the plan above; "
                        "sign it only after you read the notes."
                        % (
                            result.get("value_human", "?"),
                            str(result.get("to", "?"))[:12],
                            "OK" if not result.get("dry_run", {}).get("reverted") else "REVERTED",
                            (result.get("risk_notes") or ["no notes"])[0],
                        )
                    ),
                }
            if isinstance(result, dict) and "native_eth" in result:
                return {
                    "role": "assistant",
                    "content": "Balance for %s: %.4f ETH (native) and %d known token(s) tracked. Testnet only — no real value." % (
                        str(result.get("address", "?"))[:12],
                        float(result.get("native_eth", 0)),
                        len(result.get("tokens", [])),
                    ),
                }
            if isinstance(result, dict) and "exposure_note" in result:
                return {
                    "role": "assistant",
                    "content": "Allowance check: %s." % result.get("exposure_note"),
                }
            if isinstance(result, dict) and "allowances" in result:
                exposed = [a for a in result.get("allowances", []) if a.get("exposed")]
                if exposed:
                    desc = "; ".join("%s %s" % (a["symbol"], a["human"]) for a in exposed[:3])
                    return {
                        "role": "assistant",
                        "content": "Allowance check: %d exposed approval(s) — e.g. %s to spender %s. Review and revoke anything unused." % (
                            len(exposed), desc, str(result.get("spender", "?"))[:12]),
                    }
                return {
                    "role": "assistant",
                    "content": "Allowance check: no exposed approvals found for the known tokens (spender %s)." % str(result.get("spender", "?"))[:12],
                }
            if isinstance(result, dict) and "simulated" in result:
                verdict = "SUCCESS (does not revert)" if not result.get("reverted") else "REVERTED: %s" % result.get("reason")
                return {"role": "assistant", "content": "Dry-run simulation: %s." % verdict}
        if isinstance(parsed, dict) and parsed.get("ok") is False:
            return {"role": "assistant", "content": "The tool reported an error: %s" % parsed.get("error", "?")}
        return {"role": "assistant", "content": "Done. The tool returned: %s" % content[:200]}

    text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            text = str(m.get("content") or "")
            break
    tool_name = _pick_tool(text)
    if not tool_name:
        return {
            "role": "assistant",
            "content": "I can inspect balances, check allowances, dry-run a transaction, or plan a transfer on a testnet. Ask e.g. 'check the balance of 0x…' or 'plan a transfer of 0.01 ETH to 0x…'.",
        }
    schema = next((t for t in tools if t.get("name") == tool_name), None)
    if schema is None:
        return {"role": "assistant", "content": "Tool %s is not available right now." % tool_name}
    arguments = {}
    if tool_name == "plan_transfer":
        m_to = re.search(r"to\s+0x[0-9a-fA-F]{40}", text)
        m_val = re.search(r"(\d+(?:\.\d+)?)\s*(?:ETH|eth)", text)
        if m_to:
            arguments["to_address"] = m_to.group(0).split()[-1]
        if m_val:
            arguments["amount_eth"] = float(m_val.group(1))
    elif tool_name == "get_balances":
        m_addr = re.search(r"0x[0-9a-fA-F]{40}", text)
        if m_addr:
            arguments["address"] = m_addr.group(0)
    elif tool_name == "check_allowance":
        m_addr = re.search(r"0x[0-9a-fA-F]{40}", text)
        if m_addr:
            arguments["spender"] = m_addr.group(0)
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_wallet_1",
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(arguments)},
            }
        ],
    }


def build_agent(
    w3: Web3 | None = None,
    backend: str = "mock",
    responder: Callable | None = None,
    max_turns: int = 8,
) -> Agent:
    """Build an agent-lab Agent for wallet work.

    ``backend``: "mock" (deterministic, offline — default) or "openai"
    (OpenAI-compatible endpoint via env).  Connects to the fixtures RPC by
    default so the agent works with zero configuration.
    """
    bind(w3)  # tools pick up the bound connection (fixtures if w3 is None)
    registry = ToolRegistry(*wallet_tools())
    if backend == "openai":
        model_backend = OpenAICompatBackend(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
    else:
        model_backend = MockBackend(responder=responder or wallet_responder)
    return Agent(
        backend=model_backend,
        tools=registry,
        system_prompt=AGENT_SYSTEM_PROMPT,
        max_turns=max_turns,
        context_chars=16_000,
    )


def run_chat(task: str, w3: Web3 | None = None, backend: str = "mock", max_turns: int = 8) -> AgentResult:
    """One-shot convenience: run the agent on ``task`` and return the result."""
    agent = build_agent(w3=w3, backend=backend, max_turns=max_turns)
    return agent.run(task)