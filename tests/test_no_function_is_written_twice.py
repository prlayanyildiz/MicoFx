"""No function body may exist twice, in micofx/ or scripts/.

This started as a throwaway scan and found eight duplicate groups, the largest
being four 177-line files (adx / atr_pct / body / cost_rank exec) that were one
program with a field name swapped, plus seven copies of the same apply-POST and
six of the same panel handshake. All of them are merged now.

The scan is the test because the merge only holds if something checks it. It
normalises names, attributes and constants away, so it matches on *shape*: two
functions that differ only in which field they touch still collide, which is
exactly the kind of copy that got in.

If this fails, the fix is normally to merge - not to raise the threshold. When
two functions genuinely share a shape but not a rule (msa_exec's widen-only
spread cap, trail_exec's open-ticket skip), keep the rule apart and share the
half that is identical: that is what `axis_exec.apply_axis_upgrade` and its
`propose` seam are for.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ("micofx", "scripts")

# A body has to be worth merging before a failure here is useful advice.
MIN_STATEMENTS = 4
MIN_NODES = 40


class _Blind(ast.NodeTransformer):
    """Erase every name, attribute and literal, so only structure is left."""

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id="_", ctx=node.ctx), node)

    def visit_arg(self, node):
        return ast.copy_location(ast.arg(arg="_", annotation=None), node)

    def visit_Constant(self, node):
        return ast.copy_location(ast.Constant(value=0), node)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        return ast.copy_location(
            ast.Attribute(value=node.value, attr="_", ctx=node.ctx), node)


def _shape(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, int] | None:
    body = [s for s in fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    if len(body) < MIN_STATEMENTS:
        return None
    try:
        blinded = [ast.fix_missing_locations(_Blind().visit(ast.parse(ast.unparse(s))))
                   for s in body]
    except (SyntaxError, ValueError):
        return None
    mod = ast.Module(body=blinded, type_ignores=[])
    size = sum(1 for _ in ast.walk(mod))
    if size < MIN_NODES:
        return None
    return hashlib.md5(ast.dump(mod).encode()).hexdigest(), size


def _groups() -> dict[str, list[tuple[str, str, int]]]:
    found: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for root in ROOTS:
        for path in sorted((ROOT / root).rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                shape = _shape(node)
                if shape is None:
                    continue
                digest, size = shape
                rel = path.relative_to(ROOT).as_posix()
                found[digest].append((f"{rel}:{node.lineno}", node.name, size))
    return found


def test_the_scan_sees_the_code_at_all():
    """A detector that matched nothing would pass this file forever."""
    groups = _groups()
    assert len(groups) > 150, f"yalnizca {len(groups)} fonksiyon tarandi - tarayici bozuk"


def test_no_function_body_appears_twice():
    dupes = [(v[0][2], v) for v in _groups().values() if len(v) > 1]
    if not dupes:
        return
    dupes.sort(reverse=True)
    lines = []
    for size, group in dupes:
        names = sorted({n for _, n, _ in group})
        lines.append(f"  ~{size} dugum x{len(group)}: {names}")
        lines.extend(f"      {loc}  {name}" for loc, name, _ in group)
    raise AssertionError(
        "ayni fonksiyon govdesi birden fazla yerde:\n" + "\n".join(lines))
