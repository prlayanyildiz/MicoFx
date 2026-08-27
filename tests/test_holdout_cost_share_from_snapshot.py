"""File-only holdout cost path: no client, no live histogram."""
from __future__ import annotations

import inspect
import subprocess
import sys

from micofx.holdout_cost import charged_holdout
from micofx.optimizer import Optimizer


def test_importing_holdout_cost_does_not_load_metatrader5():
    script = (
        "import sys\n"
        "assert 'MetaTrader5' not in sys.modules\n"
        "import micofx.holdout_cost\n"
        "loaded = [k for k in sys.modules if k == 'MetaTrader5' "
        "or k.startswith('MetaTrader5.') or k == 'micofx.engine' "
        "or k == 'micofx.mt5client']\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_apply_uses_the_shared_charged_slice():
    apply_src = inspect.getsource(Optimizer._holdout_costed)
    charged = inspect.getsource(charged_holdout)
    assert "charged_holdout(" in apply_src
    assert "imputed_spread_pts" not in apply_src
    assert "backtest.simulate" not in apply_src
    assert "backtest.simulate" in charged
