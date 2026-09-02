"""External R&D scanner — GitHub + curated web ideas for MicoFx income loop.

Runs outside the engine. Writes actionable, constitution-safe ideas only
(no LLM-in-engine, no ML score, no retired families).

Usage:
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/research_scanner.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.paths import DB_PATH, LOG_DIR  # noqa: E402

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_MD = LOG_DIR / "research_latest.md"
QUEUE_MD = ROOT / "cursor" / "RESEARCH_QUEUE.md"

# Constitution: skip ideas that violate AGENTS.md / MASTER_PROMPT constraints.
_SKIP = re.compile(
    r"(?i)(openai|gpt|claude|llm|lstm|neural|xgboost|random.?forest|"
    r"stoch_flip|dual_t3|t3_flip|parabolic|tp_atr_mult|partial_tp|"
    r"breakeven_atr|max_bars_in_trade|harvest_at_r|ensemble.?score|"
    r"autostart_mt5|orb_retest)",
)

# Topics rotated each run (deterministic by day-hour bucket).
_TOPICS = (
    "metatrader5 python walk forward optimization",
    "forex spread filter atr execution cost",
    "algorithmic trading risk position sizing drawdown",
    "indices CFD trading session filter python",
    "prop firm forex backtest reconciliation",
)

# Ideas already measured or shipped — do not re-propose.
_KNOWN_DONE = (
    "fill-next-open",
    "hard atr stop",
    "atr trail",
    "spread_calibration one-way widen",
    "holdout retention gate",
    "supervisor scale not refuse",
    "income_dev_loop",
    "holdout_live_sync",
)


def _db_symbols() -> list[str]:
    try:
        c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0)
        rows = c.execute("SELECT symbol, payload FROM symbols").fetchall()
        c.close()
    except sqlite3.Error:
        return []
    out: list[str] = []
    for sym, raw in rows:
        try:
            if json.loads(raw).get("enabled"):
                out.append(str(sym))
        except json.JSONDecodeError:
            continue
    return sorted(out)


def _github_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = urllib.parse.quote(f"{query} language:python")
    url = f"https://api.github.com/search/repositories?q={q}&sort=updated&order=desc&per_page={limit}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                              "User-Agent": "MicoFx-research-scanner"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    hits: list[dict[str, Any]] = []
    for item in data.get("items") or []:
        desc = str(item.get("description") or "")
        name = str(item.get("full_name") or "")
        blob = f"{name} {desc}"
        if _SKIP.search(blob):
            continue
        hits.append({
            "source": "github",
            "title": name,
            "url": item.get("html_url") or "",
            "stars": int(item.get("stargazers_count") or 0),
            "updated": str(item.get("updated_at") or "")[:10],
            "snippet": desc[:220],
        })
    return hits


def _curated_ideas(active: list[str]) -> list[dict[str, Any]]:
    """Ship-safe improvements aligned with current architecture."""
    sym_note = ", ".join(active) if active else "aktif sembol yok"
    return [
        {
            "source": "mico",
            "title": "Tick vs bar spread ratio auto-widen",
            "url": "micofx/engine.py _sample_spread_ratio",
            "snippet": (
                "Live tick spread often exceeds bar spread used in search. "
                f"Auto-calibrate all enabled ({sym_note}) every income tick; "
                "already in income_dev_loop apply_trust_entries."
            ),
            "action": "keep",
            "priority": 1,
        },
        {
            "source": "web",
            "title": "Walk-forward IS/OOS parameter lock (MQL5 article 22921)",
            "url": "https://www.mql5.com/en/articles/22921",
            "snippet": (
                "Pick in-sample peak by Sortino, lock params, measure exact OOS row. "
                "MicoFx holdout already gates apply; add profit_drop column to opt history UI."
            ),
            "action": "ui",
            "priority": 2,
        },
        {
            "source": "web",
            "title": "Session-aware spread ceilings",
            "url": "https://finance.trgy.co.jp/en/mql5-en/reference-en/mql5-spread-filter/",
            "snippet": (
                "Spread filter threshold by hour/session reduces false blocks on indices. "
                "Explore hour_risk_scales-style spread cap table (search axis cost only)."
            ),
            "action": "research",
            "priority": 3,
        },
        {
            "source": "github",
            "title": "FTMO Monte-Carlo pass-rate sim (ranjeet867/Metatrader pattern)",
            "url": "https://github.com/ranjeet867/Metatrader",
            "snippet": (
                "Bootstrap daily R sequences for prop-style pass rate — panel readout only, "
                "not an apply gate. Complements holdout capture column."
            ),
            "action": "research",
            "priority": 4,
        },
        {
            "source": "github",
            "title": "Regime gate before entry (Titan ADX/vol filter)",
            "url": "https://github.com/TheHaywire/titan-trading-system",
            "snippet": (
                "Enable/disable family by ADX band already in grid (adx_min/adx_max). "
                "Audit absent_regime_gates_to_zero on apply; ensure no stale adx_max blocks."
            ),
            "action": "audit",
            "priority": 2,
        },
    ]


def _score(item: dict[str, Any]) -> float:
    base = float(item.get("stars") or 0) * 0.01
    pri = float(item.get("priority") or 5)
    action = str(item.get("action") or "")
    boost = {"keep": 0.0, "audit": 1.0, "ui": 1.5, "research": 2.0, "code": 3.0}.get(action, 1.0)
    return boost + base - pri * 0.1


def scan() -> dict[str, Any]:
    active = _db_symbols()
    bucket = datetime.now().strftime("%Y%m%d%H")
    topic = _TOPICS[int(bucket) % len(_TOPICS)]
    github = _github_search(topic)
    curated = _curated_ideas(active)
    merged: list[dict[str, Any]] = curated + github
    for item in merged:
        item["score"] = round(_score(item), 2)
    merged.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
    return {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "active_symbols": active,
        "known_done": list(_KNOWN_DONE),
        "items": merged[:20],
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        f"# AR-GE taramasi — {report['ts']}",
        "",
        f"- Konu: `{report.get('topic')}`",
        f"- Aktif semboller: {', '.join(report.get('active_symbols') or []) or '(yok)'}",
        "",
        "## Oncelikli fikirler (guvenli — constitution uyumlu)",
        "",
        "| Oncelik | Kaynak | Baslik | Aksiyon |",
        "|---------|--------|--------|---------|",
    ]
    for item in report.get("items") or []:
        lines.append(
            f"| {item.get('score', '?')} | {item.get('source', '?')} | "
            f"{item.get('title', '?')[:60]} | {item.get('action', '-')} |"
        )
    lines.extend(["", "## Detay"])
    for item in report.get("items") or []:
        url = item.get("url") or ""
        lines.append(f"\n### {item.get('title', '?')} ({item.get('source')})")
        if url.startswith("http"):
            lines.append(f"- URL: {url}")
        lines.append(f"- {item.get('snippet', '')}")
        if item.get("action"):
            lines.append(f"- Onerilen adim: **{item['action']}**")
    lines.extend([
        "",
        "## Yasak (otomatik filtre)",
        "LLM/ML motor icinde, emekli aileler, TP merdiveni, harvest, ensemble.",
        "",
        "## Agent",
        "Uygula: constitution-safe `action=code|audit` maddeleri; olc + pytest + ruff.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    report = scan()
    md = render(report)
    OUT_MD.write_text(md, encoding="utf-8")
    QUEUE_MD.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_MD.write_text(md, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
