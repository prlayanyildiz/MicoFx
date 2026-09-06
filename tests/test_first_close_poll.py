"""first_close_poll covers first-close without exiting on silence."""
from __future__ import annotations

import ast
from pathlib import Path


def test_first_close_poll_not_capped_at_60_ticks():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "first_close_poll.py").read_text(
        encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Call) and getattr(node.iter.func, "id", "") == "range":
                args = node.iter.args
                if args and isinstance(args[0], ast.Constant) and args[0].value == 60:
                    raise AssertionError("first_close_poll still capped at range(60)")
    assert "deadline" in src
    # Must NOT exit solely on silence_fire (baseline owns that once/day).
    assert "if sil.get(\"fire\")" not in src
    assert "AGENT_LOOP_WAKE_first_close_poll" in src