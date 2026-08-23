"""Agent loop: agent-lab core + wallet tools, fully offline."""

from __future__ import annotations

from agent_wallet.agent import build_agent
from agent_wallet.providers import FIXTURE_RECIPIENT, FIXTURE_USER, resolve_rpc


def _agent(**kwargs):
    w3, _ = resolve_rpc("fixtures://")
    return build_agent(w3=w3, **kwargs)


def test_agent_answers_balance_question_via_tool():
    agent = _agent()
    result = agent.run("what is the balance of 0x1111111111111111111111111111111111111111")
    assert any(s.kind == "tool_call" and s.name == "get_balances" for s in result.steps)
    assert "1.0000 ETH" in result.answer
    assert result.tool_calls == 1


def test_agent_plans_transfer_and_flags_risk():
    agent = _agent()
    result = agent.run("plan a transfer of 0.05 ETH to 0x2222222222222222222222222222222222222222")
    assert any(s.kind == "tool_call" and s.name == "plan_transfer" for s in result.steps)
    assert "Dry-run" in result.answer or "revert" in result.answer.lower() or "nothing signed" in result.answer
    assert any(s.name == "plan_transfer" for s in result.steps)


def test_agent_checks_allowance():
    agent = _agent()
    result = agent.run("check the allowance exposure of the demo wallet")
    assert any(s.kind == "tool_call" and s.name == "check_allowance" for s in result.steps)
    assert "Allowance" in result.answer


def test_agent_simulates_dry_run():
    agent = _agent()
    result = agent.run("dry run a send of 0.01 ETH to 0x8888888888888888888888888888888888888888")
    assert any(s.kind == "tool_call" and s.name == "dry_run_tx" for s in result.steps)
    assert "SUCCESS" in result.answer


def test_agent_answer_visible_without_tools_when_ambiguous():
    agent = _agent()
    result = agent.run("hello there")
    assert result.tool_calls == 0
    assert "balance" in result.answer.lower() or "inspect" in result.answer.lower()


def test_agent_steps_are_recorded():
    agent = _agent()
    result = agent.run("what is the balance of 0x1111111111111111111111111111111111111111")
    kinds = {s.kind for s in result.steps}
    assert "tool_call" in kinds and "tool_result" in kinds
    assert result.turns >= 2


def test_agent_system_prompt_is_safety_first():
    agent = _agent()
    assert "mainnet" in agent.system_prompt.lower()
    assert "unsigned" in agent.system_prompt.lower()