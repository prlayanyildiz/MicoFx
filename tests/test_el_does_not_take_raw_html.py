"""el() must not offer an innerHTML backdoor.

The helper used to assign node.innerHTML when attrs.html was set. No
caller used it; the next one would skip esc() on the same page that
embeds the API token in a meta tag.
"""
from __future__ import annotations

from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
      / "app.js").read_text(encoding="utf-8")


def test_el_does_not_assign_innerhtml_from_an_html_key():
    helper = JS.split("function el(", 1)[1].split("function ", 1)[0]
    assert 'k === "html"' not in helper
    assert "innerHTML = v" not in helper
