"""Tam sistem denetimi — AGENTS.md kurallarına karşı canlı konfigürasyonu doğrular.

Rapor yalnızca sorunları bildirir, otomatik düzeltme yapmaz.
Çıktı ``data/full_audit_report.json`` dosyasına yazılır.
"""
from __future__ import annotations

import json
import math
import traceback
from pathlib import Path
from typing import Any

from micofx.logbus import LOG

# ── AGENTS.md sabit kuralları ──────────────────────────────────────────────
RETIRED_SYMBOLS = frozenset({
    "US30", "JPN225", "SpotBrent", "BRENTOIL-PERP", "BTCUSD",
})
MAX_COMBOS_LIMIT = 2000
EXPECTED_CONCURRENT_RISK_PCT = 25.0
EXPECTED_SESSION_CLOCK_FIELDS = frozenset({
    "use_sessions", "sessions", "trade_days", "flat_before_close_min",
})
# Yasaklı çıkış alanları (AGENTS.md: "Do not bring back")
BANNED_EXIT_FIELDS = frozenset({
    "tp_atr_mult", "partial_tp_r", "max_bars_in_trade",
    "stale_exit_ratio", "breakeven_atr",
})
# Yasaklı yedek alanları
BANNED_BACKUP_ATTRS = (
    "backup_enabled", "backup_path", "backup_interval_hours",
    "backup_keep_count", "backup_last",
)
LIVING_FAMILIES = frozenset({
    "mtf_pullback", "burst", "channel_break", "super_trend",
    "keltner_break", "sweep_fade", "range_fade",
})


# ── Yardımcı ──────────────────────────────────────────────────────────────

def _pass(rule: str, detail: str) -> dict:
    return {"rule": rule, "status": "PASS", "details": detail}


def _fail(rule: str, detail: str) -> dict:
    return {"rule": rule, "status": "FAIL", "details": detail}


def _has_non_finite(d: dict[str, Any]) -> list[str]:
    """Bir dict içinde NaN veya Inf değer taşıyan anahtarları döndürür."""
    bad: list[str] = []
    for k, v in d.items():
        if isinstance(v, float) and not math.isfinite(v):
            bad.append(f"{k}={v!r}")
        elif isinstance(v, dict):
            for sub_k in _has_non_finite(v):
                bad.append(f"{k}.{sub_k}")
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, float) and not math.isfinite(item):
                    bad.append(f"{k}[{i}]={item!r}")
    return bad


# ── Bireysel kontroller ───────────────────────────────────────────────────

def _check_retired_symbols(symbols: dict) -> list[dict]:
    """Emekli sembollerin canlı konfigürasyonda olmamasını doğrular."""
    found = [s for s in RETIRED_SYMBOLS if s in symbols]
    if found:
        return [_fail("retired_symbols", f"Emekli sembol mevcut: {', '.join(sorted(found))}")]
    return [_pass("retired_symbols", "Emekli sembol yok.")]


def _check_max_combos(opt: dict) -> dict:
    """max_combos değerinin 2000 limitini aşmamasını doğrular."""
    val = opt.get("max_combos")
    if val is None:
        return _fail("max_combos", "max_combos opt_params'da bulunamadı.")
    if int(val) > MAX_COMBOS_LIMIT:
        return _fail("max_combos", f"max_combos={val} > {MAX_COMBOS_LIMIT} limit.")
    return _pass("max_combos", f"max_combos={val} limit dahilinde.")


def _check_concurrent_risk(sys_cfg) -> dict:
    """max_concurrent_risk_pct değerinin %25 olduğunu doğrular."""
    val = getattr(sys_cfg, "max_concurrent_risk_pct", None)
    if val is None:
        return _fail("concurrent_risk", "max_concurrent_risk_pct bulunamadı.")
    if val != EXPECTED_CONCURRENT_RISK_PCT:
        return _fail("concurrent_risk",
                      f"max_concurrent_risk_pct={val}, beklenen {EXPECTED_CONCURRENT_RISK_PCT}.")
    return _pass("concurrent_risk", f"max_concurrent_risk_pct={val}.")


def _check_banned_exit_fields(symbols: dict) -> list[dict]:
    """Yasaklı çıkış alanlarının hiçbir sembolde bulunmamasını doğrular."""
    results: list[dict] = []
    for sym_name, cfg in symbols.items():
        cfg_dict = cfg.to_dict() if hasattr(cfg, "to_dict") else vars(cfg)
        found = [f for f in BANNED_EXIT_FIELDS if f in cfg_dict and cfg_dict[f]]
        if found:
            results.append(_fail("banned_exit_fields",
                                  f"{sym_name}: yasaklı çıkış alanları mevcut: {', '.join(found)}"))
    if not results:
        results.append(_pass("banned_exit_fields", "Yasaklı çıkış alanı yok."))
    return results


def _check_backup_fields(sys_cfg) -> dict:
    """Yedek özelliğinin tamamen kaldırılmış olduğunu doğrular."""
    found = [a for a in BANNED_BACKUP_ATTRS if hasattr(sys_cfg, a)]
    if found:
        return _fail("no_backup", f"Yedek alanları hâlâ mevcut: {', '.join(found)}")
    return _pass("no_backup", "Yedek alanı bulunamadı.")


def _check_non_finite_system(sys_cfg) -> dict:
    """Sistem konfigürasyonunda NaN/Inf değer olmamasını doğrular."""
    d = sys_cfg.to_dict() if hasattr(sys_cfg, "to_dict") else vars(sys_cfg)
    bad = _has_non_finite(d)
    if bad:
        return _fail("non_finite_system", f"Sonlu olmayan değerler: {', '.join(bad)}")
    return _pass("non_finite_system", "Tüm sistem değerleri sonlu.")


def _check_non_finite_symbols(symbols: dict) -> list[dict]:
    """Sembol konfigürasyonlarında NaN/Inf değer olmamasını doğrular."""
    results: list[dict] = []
    for sym_name, cfg in symbols.items():
        d = cfg.to_dict() if hasattr(cfg, "to_dict") else vars(cfg)
        bad = _has_non_finite(d)
        if bad:
            results.append(_fail(f"non_finite:{sym_name}",
                                  f"Sonlu olmayan değerler: {', '.join(bad)}"))
    if not results:
        results.append(_pass("non_finite_symbols", "Tüm sembol değerleri sonlu."))
    return results


def _check_strategy_families(symbols: dict) -> list[dict]:
    """Canlı sembollerin yalnızca geçerli strateji aileleri kullanmasını doğrular."""
    results: list[dict] = []
    for sym_name, cfg in symbols.items():
        strat = getattr(cfg, "strategy", "")
        if strat and strat not in LIVING_FAMILIES:
            results.append(_fail("strategy_family",
                                  f"{sym_name}: bilinmeyen strateji '{strat}'"))
    if not results:
        results.append(_pass("strategy_family", "Tüm semboller geçerli strateji aileleri kullanıyor."))
    return results


def _check_session_clock_completeness() -> dict:
    """_SESSION_CLOCK_FIELDS'ın tam dört alanı içerdiğini doğrular (kod düzeyinde)."""
    try:
        from micofx.web.app import _SESSION_CLOCK_FIELDS
        if _SESSION_CLOCK_FIELDS != EXPECTED_SESSION_CLOCK_FIELDS:
            return _fail("session_clock_fields",
                          f"Beklenen: {sorted(EXPECTED_SESSION_CLOCK_FIELDS)}, "
                          f"mevcut: {sorted(_SESSION_CLOCK_FIELDS)}")
        return _pass("session_clock_fields", "Dört alan tam.")
    except ImportError:
        return _fail("session_clock_fields", "_SESSION_CLOCK_FIELDS import edilemedi.")


def _check_internal_only_fields(symbols: dict) -> list[dict]:
    """pending_exit_patch gibi dahili alanların kayıtlı konfigürasyonda olmamasını doğrular."""
    try:
        from micofx.web.app import _INTERNAL_ONLY_FIELDS
    except ImportError:
        return [_fail("internal_fields", "_INTERNAL_ONLY_FIELDS import edilemedi.")]
    results: list[dict] = []
    for sym_name, cfg in symbols.items():
        d = cfg.to_dict() if hasattr(cfg, "to_dict") else vars(cfg)
        found = [f for f in _INTERNAL_ONLY_FIELDS if f in d and d[f]]
        if found:
            results.append(_fail("internal_fields",
                                  f"{sym_name}: dahili alan aktif: {', '.join(found)}"))
    if not results:
        results.append(_pass("internal_fields", "Dahili alan aktif değil."))
    return results


def _check_exit_risk_consistency(symbols: dict) -> list[dict]:
    """EXIT_RISK_FIELDS içindeki alanların makul değerlerde olduğunu doğrular."""
    from micofx.models import EXIT_PARAM_BOUNDS
    results: list[dict] = []
    for sym_name, cfg in symbols.items():
        for field, (lo, hi) in EXIT_PARAM_BOUNDS.items():
            val = getattr(cfg, field, None)
            if val is not None and (val <= lo or val > hi):
                results.append(_fail("exit_param_bounds",
                                      f"{sym_name}.{field}={val} sınır dışı ({lo}-{hi})"))
    if not results:
        results.append(_pass("exit_param_bounds", "Tüm çıkış parametreleri sınırlar içinde."))
    return results


# ── Ana denetim ───────────────────────────────────────────────────────────

def run_full_audit(store) -> dict:
    """Canlı sistemi AGENTS.md kurallarına karşı kapsamlı bir şekilde denetler.

    ``store`` bir ``micofx.store.Store`` örneğidir.
    Sonuç: ``{"report": [...]}`` şeklinde bir dict, ayrıca ``data/full_audit_report.json`` dosyasına yazılır.
    """
    report: list[dict] = []

    sys_cfg = store.system
    symbols = store.symbols
    opt = store.opt_params()

    # 1. Emekli semboller
    report.extend(_check_retired_symbols(symbols))

    # 2. max_combos limiti
    report.append(_check_max_combos(opt))

    # 3. max_concurrent_risk_pct = %25
    report.append(_check_concurrent_risk(sys_cfg))

    # 4. Yasaklı çıkış alanları (tp_atr_mult, partial_tp_r vb.)
    report.extend(_check_banned_exit_fields(symbols))

    # 5. Yedek özelliği tamamen kaldırılmış mı
    report.append(_check_backup_fields(sys_cfg))

    # 6. NaN/Inf kontrolleri
    report.append(_check_non_finite_system(sys_cfg))
    report.extend(_check_non_finite_symbols(symbols))

    # 7. Strateji aileleri geçerli mi (7 aile)
    report.extend(_check_strategy_families(symbols))

    # 8. _SESSION_CLOCK_FIELDS tam mı (kod düzeyinde)
    report.append(_check_session_clock_completeness())

    # 9. Dahili alanlar (pending_exit_patch vb.) aktif değil mi
    report.extend(_check_internal_only_fields(symbols))

    # 10. Çıkış parametreleri sınır kontrolleri
    report.extend(_check_exit_risk_consistency(symbols))

    # Raporu dosyaya yaz
    out = {"report": report}
    path = Path("data/full_audit_report.json")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        LOG.emit(f"Tam denetim raporu yazıldı: {path}", "INFO")
    except Exception:
        LOG.emit(f"Denetim raporu yazılamadı: {traceback.format_exc()}", "ERROR")

    # Özet log
    fails = [r for r in report if r["status"] == "FAIL"]
    if fails:
        LOG.emit(f"DENETIM: {len(fails)} kural ihlali tespit edildi", "WARN")
    else:
        LOG.emit(f"DENETIM: {len(report)} kural, hepsi gecti", "INFO")

    return out
