"""Daily Green automation: tips pool integrity + deterministic rotation."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = REPO_ROOT / "scripts" / "tips_pool.json"


def _load_daily_update():
    spec = importlib.util.spec_from_file_location(
        "aw_daily_update", REPO_ROOT / "scripts" / "daily_update.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tips_pool_has_at_least_20_entries():
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    assert len(pool) >= 20


def test_tips_pool_entries_are_well_formed():
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    titles = []
    for tip in pool:
        assert isinstance(tip, dict), "each tip must be an object"
        assert tip.get("title") and tip.get("body"), "title+body required"
        titles.append(tip["title"])
    assert len(titles) == len(set(titles)), "titles must be unique"


def test_tips_are_agent_and_web3_safety_themed():
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    joined = " ".join((t["title"] + " " + t["body"]).lower() for t in pool)
    for keyword in ("agent", "wallet", "sign", "sepolia", "testnet", "gas", "allowance", "rpc", "key", "tx"):
        assert keyword in joined, "pool should cover %r topics" % keyword


def test_rotation_is_deterministic_and_covers_pool():
    mod = _load_daily_update()
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    epoch = dt.date(1970, 1, 1)
    seen = set()
    for i in range(len(pool) * 2):
        day = epoch + dt.timedelta(days=i)
        tip = mod.pool_tip(day, pool)
        seen.add(tip["title"])
    assert len(seen) >= len(pool), "rotation should cycle the whole pool"


def test_render_entry_daily_format():
    mod = _load_daily_update()
    tip = {"title": "Test tip", "body": "Body line.", "command": "agent-wallet plan 0x…"}
    day = dt.date(2026, 8, 23)
    lines = mod.render_entry(day, tip)
    assert lines[0] == "## 2026-08-23 — %s: Test tip" % mod.KIND_LABEL
    assert "> `agent-wallet plan 0x…`" in lines


def test_plan_days_noop_when_current():
    mod = _load_daily_update()
    today = dt.date(2026, 8, 23)
    have = {today}
    assert mod.plan_days(today, have) == []


def test_plan_days_backfills_gap():
    mod = _load_daily_update()
    last = dt.date(2026, 8, 20)
    today = dt.date(2026, 8, 23)
    days = mod.plan_days(today, {last})
    assert days == [dt.date(2026, 8, 21), dt.date(2026, 8, 22), dt.date(2026, 8, 23)]