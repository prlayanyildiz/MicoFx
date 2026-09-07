"""Tests for bilingual (Turkish + English) casing, boolean parsing, and side normalization."""
from __future__ import annotations

from micofx.engine import Engine
from micofx.models import SymbolConfig, SystemConfig, _coerce
from micofx.risk import RiskManager
from micofx.sessions import refuse_block_key


def test_models_coerce_bilingual_booleans():
    """Verify boolean coercion supports both English and Turkish truthy/falsy tokens with any casing/diacritics."""
    # English falsy
    for v in ["false", "FALSE", "0", "", "no", "NO", "off", "OFF", "none", "NONE"]:
        cfg = _coerce(SymbolConfig, {"symbol": "TEST", "enabled": v})
        assert cfg.enabled is False, f"Expected False for {v!r}, got {cfg.enabled!r}"

    # Turkish falsy
    for v in [
        "hayır", "HAYIR", "hayir", "HAYİR",
        "kapalı", "KAPALI", "kapali", "KAPALİ",
        "yanlış", "YANLIŞ", "yanlis", "YANLİS",
        "pasif", "PASİF", "yok", "YOK", "kapat", "KAPAT"
    ]:
        cfg = _coerce(SymbolConfig, {"symbol": "TEST", "enabled": v})
        assert cfg.enabled is False, f"Expected False for Turkish falsy {v!r}, got {cfg.enabled!r}"

    # English truthy
    for v in ["true", "TRUE", "1", "yes", "YES", "on", "ON"]:
        cfg = _coerce(SymbolConfig, {"symbol": "TEST", "enabled": v})
        assert cfg.enabled is True, f"Expected True for {v!r}, got {cfg.enabled!r}"

    # Turkish truthy
    for v in ["evet", "EVET", "açık", "AÇIK", "acik", "aktif", "AKTİF"]:
        cfg = _coerce(SymbolConfig, {"symbol": "TEST", "enabled": v})
        assert cfg.enabled is True, f"Expected True for Turkish truthy {v!r}, got {cfg.enabled!r}"


def test_sessions_refuse_block_key_turkish_diacritics():
    """Verify refuse_block_key correctly maps reasons with or without Turkish diacritics."""
    assert refuse_block_key("saat kapali") == "saat_kapali"
    assert refuse_block_key("saat kapalı") == "saat_kapali"
    assert refuse_block_key("SAAT KAPALI") == "saat_kapali"
    assert refuse_block_key("gun kapali") == "gun_kapali"
    assert refuse_block_key("gün kapalı") == "gun_kapali"
    assert refuse_block_key("GÜN KAPALI") == "gun_kapali"
    assert refuse_block_key("hafta sonu oncesi") == "hafta_sonu_oncesi"
    assert refuse_block_key("hafta sonu öncesi") == "hafta_sonu_oncesi"
    assert refuse_block_key("HAFTA SONU ÖNCESİ") == "hafta_sonu_oncesi"
    assert refuse_block_key("hafta sonu") == "hafta_sonu"
    assert refuse_block_key("HAFTA SONU") == "hafta_sonu"


class DummyStore:
    system = SystemConfig()
    symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=990001, max_positions=3)}
    def get_setting(self, k, default=""):
        return default


def test_risk_remaining_position_risk_side_casing():
    """Verify remaining_position_risk calculates positive risk for BUY/buy/AL/al and SELL/sell/SAT/sat."""
    class DummyClient:
        def margin_for(self, *a, **kw):
            return 10.0
        def tick_value(self, *a, **kw):
            return 1.0
        def tick_size(self, *a, **kw):
            return 0.01
        def money_per_price_unit(self, symbol, volume):
            return volume * 100.0

    rm = RiskManager(client=DummyClient(), store=DummyStore())

    # Buy positions with various casings & Turkish variants
    for side_val in ["buy", "BUY", "Buy", "al", "AL"]:
        pos = {
            "symbol": "XAUUSD",
            "side": side_val,
            "volume": 1.0,
            "price_open": 2000.0,
            "sl": 1990.0,  # 10 points below entry
        }
        risk = rm.remaining_position_risk(pos)
        assert risk > 0, f"Expected risk > 0 for side {side_val!r}, got {risk}"
        assert risk == 1000.0, f"Expected 1000.0 for side {side_val!r}, got {risk}"

    # Sell positions with various casings & Turkish variants
    for side_val in ["sell", "SELL", "Sell", "sat", "SAT"]:
        pos = {
            "symbol": "XAUUSD",
            "side": side_val,
            "volume": 1.0,
            "price_open": 2000.0,
            "sl": 2010.0,  # 10 points above entry
        }
        risk = rm.remaining_position_risk(pos)
        assert risk > 0, f"Expected risk > 0 for side {side_val!r}, got {risk}"
        assert risk == 1000.0, f"Expected 1000.0 for side {side_val!r}, got {risk}"


def test_risk_can_open_opposite_side_check_casing():
    """Verify can_open does not falsely reject orders with opposite side when casing or language differs."""
    class DummyClient:
        def resolve(self, sym):
            return sym
        def margin_for(self, *a, **kw):
            return 10.0
        def tick(self, sym):
            return {"ask": 2000.0, "bid": 1999.0}
        def money_per_price_unit(self, symbol, volume):
            return volume * 100.0

    rm = RiskManager(client=DummyClient(), store=DummyStore())
    cfg = DummyStore.symbols["XAUUSD"]

    open_pos = [{
        "magic": 990001,
        "symbol": "XAUUSD",
        "side": "BUY",  # uppercase
        "volume": 0.1,
        "price_open": 1980.0,
        "sl": 1970.0,
    }]
    account = {"balance": 10000.0, "equity": 10000.0, "margin_free": 5000.0}

    # Same side (buy vs BUY) -> should NOT be rejected for opposite side
    v = rm.can_open(cfg, side="buy", lot=0.1, positions=open_pos, account=account, sl_distance=10.0, entry_price=2000.0, atr=10.0)
    assert "ters yonde" not in v.reason, f"Unexpected opposite side rejection: {v.reason}"

    # Same side with Turkish (AL vs BUY) -> should NOT be rejected for opposite side
    v2 = rm.can_open(cfg, side="al", lot=0.1, positions=open_pos, account=account, sl_distance=10.0, entry_price=2000.0, atr=10.0)
    assert "ters yonde" not in v2.reason, f"Unexpected opposite side rejection: {v2.reason}"

    # Actually opposite side (SELL vs BUY) -> MUST be rejected for opposite side
    v3 = rm.can_open(cfg, side="sell", lot=0.1, positions=open_pos, account=account, sl_distance=10.0, entry_price=2000.0, atr=10.0)
    assert not v3.ok
    assert "ters yonde" in v3.reason


def test_engine_live_open_metrics_side_casing():
    """Verify live_open_metrics accurately calculates r_open across casing and Turkish variants."""
    for s in ["buy", "BUY", "Buy", "al", "AL"]:
        pos = {
            "side": s,
            "price_open": 2000.0,
            "price_current": 2010.0,
            "sl": 1990.0,
        }
        res = Engine.live_open_metrics(pos, {})
        assert res["r_open"] == 1.0, f"Expected 1.0 R for {s!r}, got {res['r_open']}"

    for s in ["sell", "SELL", "Sell", "sat", "SAT"]:
        pos = {
            "side": s,
            "price_open": 2000.0,
            "price_current": 1990.0,
            "sl": 2010.0,
        }
        res = Engine.live_open_metrics(pos, {})
        assert res["r_open"] == 1.0, f"Expected 1.0 R for {s!r}, got {res['r_open']}"
