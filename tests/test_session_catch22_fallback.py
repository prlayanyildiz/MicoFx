from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer, _sessions_key
from micofx.web.app import create_app


def _hold(net_r: float, pf: float, n: int = 100, dd: float = 30.0, sc: float | None = None) -> dict:
    return {
        "trades": n,
        "net_r": net_r,
        "profit_factor": pf,
        "max_dd_r": dd,
        "score": sc if sc is not None else net_r,
    }


def test_session_shortlist_falls_back_when_all_challengers_fail_strict_ok():
    """When incumbent is deeply negative, every window fails _session_holdout_ok.
    The shortlist must not freeze into only [live]; it should fan out to the
    highest-ranking liquid windows (least negative / best score).
    """
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True)
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, strategy="burst", timeframe="M15",
        sessions=[{"start": "01:00", "end": "23:59"}], use_sessions=True)
    opt.store.symbols = {"NAS100": cfg}

    def fake_costed(symbol, timeframe, strategy, params, **kwargs):
        sessions = kwargs.get("sessions") or cfg.sessions
        start = sessions[0]["start"]
        table = {
            "01:00": _hold(-60.0, 0.86, n=600, dd=68.0, sc=-60.0),  # live
            "15:00": _hold(0.0, 1.00, n=500, dd=29.0, sc=0.0),      # best alternative
            "14:00": _hold(-20.0, 0.95, n=550, dd=32.0, sc=-20.0),  # second best alternative
            "08:00": _hold(-45.0, 0.63, n=200, dd=48.0, sc=-45.0),
        }
        return table.get(start, _hold(-50.0, 0.50, n=100))

    opt._holdout_costed = fake_costed  # type: ignore[method-assign]
    short = opt._session_search_shortlist(cfg)
    keys = [_sessions_key(w) for w in short]

    # Live should be present
    assert _sessions_key([{"start": "01:00", "end": "23:59"}]) in keys
    # Fallback must include the best candidate windows even though PF < 1.10
    assert _sessions_key([{"start": "15:00", "end": "21:00"}]) in keys
    assert _sessions_key([{"start": "14:00", "end": "22:00"}]) in keys
    assert len(short) == 3


def test_blocked_entry_hours_api_allows_and_validates():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1)

    class _FakeStore:
        def __init__(self):
            self.symbols = {"XAUUSD": cfg}
            self.system = MagicMock()
            self.defaults = {"symbols": [], "group_presets": {}}

        def get_setting(self, k, d=None):
            return d

        def opt_params(self):
            return {}

        def update_symbol(self, sym, patch, **kwargs):
            for k, v in patch.items():
                setattr(self.symbols[sym], k, v)
            return self.symbols[sym]

    store = _FakeStore()
    app = create_app(store, MagicMock(), MagicMock(), MagicMock(), api_token="tok")
    tc = TestClient(app, cookies={"mico_session": "tok"}, headers={"origin": "http://testserver"})

    # Valid list of hours
    res = tc.post("/api/symbols/XAUUSD", json={"blocked_entry_hours": [14, 15, 16]})
    assert res.status_code == 200, res.text
    assert cfg.blocked_entry_hours == [14, 15, 16]

    # Empty list is allowed (clears blocks)
    res = tc.post("/api/symbols/XAUUSD", json={"blocked_entry_hours": []})
    assert res.status_code == 200, res.text
    assert cfg.blocked_entry_hours == []

    # Invalid hour (>23 or <0)
    res = tc.post("/api/symbols/XAUUSD", json={"blocked_entry_hours": [24]})
    assert res.status_code == 400

    # Non-list
    res = tc.post("/api/symbols/XAUUSD", json={"blocked_entry_hours": "14"})
    assert res.status_code == 400


def test_brst_close_pct_http_writable():
    """Burst close% is an operator income knob (peer ACK 08.09 JPN 0.60→0.50)."""
    cfg = SymbolConfig(symbol="JPN225", magic=2, strategy="burst", brst_close_pct=0.6)

    class _FakeStore:
        def __init__(self):
            self.symbols = {"JPN225": cfg}
            self.system = MagicMock()
            self.defaults = {"symbols": [], "group_presets": {}}

        def get_setting(self, k, d=None):
            return d

        def opt_params(self):
            return {}

        def update_symbol(self, sym, patch, **kwargs):
            for k, v in patch.items():
                setattr(self.symbols[sym], k, v)
            return self.symbols[sym]

    store = _FakeStore()
    app = create_app(store, MagicMock(), MagicMock(), MagicMock(), api_token="tok")
    tc = TestClient(app, cookies={"mico_session": "tok"}, headers={"origin": "http://testserver"})
    res = tc.post("/api/symbols/JPN225", json={"brst_close_pct": 0.5})
    assert res.status_code == 200, res.text
    assert cfg.brst_close_pct == 0.5

