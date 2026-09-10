"""One way to open a panel session, for the eight scripts that each had one.

Six watch scripts carried an identical five-line ``_session`` /
``_panel_opener`` (cookie jar, opener, GET ``/`` to take the session cookie),
and two more carried the header-dict variant of the same handshake. The panel
refuses every write without both an ``Origin`` and that cookie, so this
handshake is a *contract with the app*, not boilerplate - and a contract
written eight times is eight places to miss when it changes.

Two shapes, because the callers genuinely need two: an opener (keeps the jar,
for scripts that make several calls) and a header dict (for scripts that pass
headers into a helper). Both perform the same GET.
"""
from __future__ import annotations

import http.cookiejar
import urllib.request
from typing import Any

from micofx.paths import PANEL


def opener(panel: str = PANEL, *, timeout: float = 10.0) -> Any:
    """A urllib opener holding the panel's session cookie."""
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(panel + "/", timeout=timeout)
    return op


def headers(panel: str = PANEL, *, timeout: float = 10.0) -> dict[str, str]:
    """``Origin`` + ``Cookie`` for callers that pass a dict around.

    Every POST/PUT/PATCH/DELETE needs the Origin header (AGENTS.md); a GET
    needs only the cookie, and sending Origin on it costs nothing.
    """
    req = urllib.request.Request(f"{panel}/", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cookies = resp.headers.get_all("Set-Cookie") or []
    out = {"Origin": panel}
    if cookies:
        out["Cookie"] = "; ".join(c.split(";")[0] for c in cookies)
    return out
