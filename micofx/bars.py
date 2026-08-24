"""Closed-bar window. No MT5 import — holdout replay must stay a leaf."""
from __future__ import annotations

import numpy as np


class Bars:
    """Closed-bar OHLC window plus the timestamp of the still-forming bar."""

    __slots__ = ("time", "open", "high", "low", "close", "spread", "volume", "forming_time")

    def __init__(self, rates: np.ndarray, forming_time: int) -> None:
        self.time = rates["time"].astype(np.int64)
        self.open = rates["open"].astype(np.float64)
        self.high = rates["high"].astype(np.float64)
        self.low = rates["low"].astype(np.float64)
        self.close = rates["close"].astype(np.float64)
        self.spread = rates["spread"].astype(np.float64)
        self.volume = rates["tick_volume"].astype(np.float64)
        self.forming_time = forming_time

    def __len__(self) -> int:
        return int(self.close.size)

    @property
    def last_closed_time(self) -> int:
        return int(self.time[-1]) if self.time.size else 0
