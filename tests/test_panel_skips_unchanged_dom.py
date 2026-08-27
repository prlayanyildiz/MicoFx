"""The 3s poll must not rebuild innerHTML when the view has not moved.

Live books still rebuild when profit/SL/cycle change. A quiet/stopped
panel should not thrash the DOM.
"""
from __future__ import annotations

from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
      / "app.js").read_text(encoding="utf-8")


def test_refresh_skips_unchanged_panel_dom():
    body = JS.split("async function refresh()", 1)[1].split("async function ", 1)[0]
    assert "viewPulse" in body
    assert "lastViewPulse" in body
    assert "renderTop()" in body


def test_opt_progress_is_part_of_the_view_pulse():
    """Frozen cycle book during a search used to skip renderOptJob.

    Positions/account do not move while snapshot reuses the last cycle, so
    Iptal stayed disabled and combo_done froze. Opt state is the thing that
    *is* moving.
    """
    pulse = JS.split("function viewPulse", 1)[1].split("async function refresh", 1)[0]
    assert "s.opt" in pulse
    assert "combo_done" in pulse


def test_opening_the_opt_tab_renders_the_job():
    tab = JS.split("function selectTab", 1)[1].split("function selectTab", 1)[0]
    tab = tab.split("\nfunction ", 1)[0]
    assert "renderOptJob()" in tab


def test_a_busy_refresh_does_not_drop_the_next_one():
    body = JS.split("async function refresh()", 1)[1].split("async function ", 1)[0]
    assert "refreshQueued" in body


def test_cancel_click_toasts_before_the_request_returns():
    assert 'toast("Iptal isteniyor' in JS
    assert "/api/opt/cancel" in JS
