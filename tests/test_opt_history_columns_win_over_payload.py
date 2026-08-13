"""The stored blob could silently overwrite the columns it is filed under.

``record_opt_run`` writes a run twice over: ``symbol``, ``created_at``,
``score`` and ``applied`` go into real columns, and the whole run also goes in
as a JSON blob. The columns are the authoritative copy - the retention sweep
keeps the newest 40 by ``created_at``, ``opt_history`` orders by it, and the
panel ranks candidates by ``score``.

``opt_history`` rebuilt each row as::

    {"id": ..., "symbol": ..., "score": ..., **payload}

with the blob expanded last, so any key inside it wins. A payload carrying its
own ``score`` would be reported instead of the column the ordering and the
retention sweep actually use - the panel showing one number while the database
ranks by another, with nothing anywhere saying they disagreed.

Nothing in the live database triggers it today: 83 rows, and not one payload
carries a key that collides. So this is a latent shadowing, not an active
defect - what makes it worth closing is that the payload is not written from a
fixed literal. It is assembled from the holdout blob, and ``score`` is exactly
the kind of key that ends up in one.

The fix is the expansion order. The blob still supplies everything the columns
do not, which is most of what the panel reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module


def _store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "opt.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    return store_module.Store()


# ------------------------------------------------------------- the defect

def test_a_payload_score_does_not_replace_the_column(tmp_path, monkeypatch):
    """The column is what the retention sweep and the ordering agree on."""
    st = _store(tmp_path, monkeypatch)
    st.record_opt_run("US500", 12.5, {"score": 99.9, "params": {"a": 1}}, applied=True)

    row = st.opt_history("US500")[0]
    assert row["score"] == 12.5, (
        "panel payload'un skorunu gosteriyor, siralama kolonunkini kullaniyor")
    assert row["params"] == {"a": 1}, "blob'un geri kalani hala geliyor"


def test_symbol_and_applied_survive_a_colliding_payload(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    st.record_opt_run(
        "GER40", 3.0,
        {"symbol": "BASKA", "applied": True, "created_at": 0.0},
        applied=False,
    )

    row = st.opt_history("GER40")[0]
    assert row["symbol"] == "GER40", "kayit baska bir sembole ait gorunuyor"
    assert row["applied"] is False, "uygulanmamis aday uygulanmis gorunuyor"
    assert row["created_at"] > 0.0, "sifir zaman damgasi budamayi da yanlis siralar"


# --------------------------------------------------- what must keep working

def test_the_blob_still_supplies_everything_else(tmp_path, monkeypatch):
    """Most of what the panel reads lives only in the payload."""
    st = _store(tmp_path, monkeypatch)
    st.record_opt_run(
        "NAS100", 1.0,
        {"holdout": {"net_r": 4.2}, "spread_scale": 1.05, "reject_reason": None},
        applied=True,
    )

    row = st.opt_history("NAS100")[0]
    assert row["holdout"] == {"net_r": 4.2}
    assert row["spread_scale"] == 1.05
    assert "reject_reason" in row


def test_id_is_still_reported(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    rid = st.record_opt_run("US30", 2.0, {"params": {}}, applied=False)
    assert st.opt_history("US30")[0]["id"] == rid
